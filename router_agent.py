from __future__ import annotations

import asyncio
import json
import os
import re
import unicodedata
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from a2a.utils import new_agent_text_message, new_task
from dotenv import load_dotenv

from common import (
    AgentAppMixin,
    build_parser,
    call_a2a_agent,
    call_a2a_agent_detailed,
    env_int,
    env_str,
    looks_like_math,
    maybe_load_env,
    run_a2a_server,
)


KNOWN_AGENT_NAMES = ("MathAgent", "WeatherAgent", "ResearchAgent", "GemmaAgent")


def summarize_trace(trace_text: str) -> dict[str, list[str]]:
    used: list[str] = []
    missing: list[str] = []

    trace_lower = (trace_text or "").lower()

    for name in KNOWN_AGENT_NAMES:
        if name.lower() in trace_lower:
            used.append(name)
        else:
            missing.append(name)

    return {"used": used, "missing": missing}


class RouterBeeAI:
    def __init__(self) -> None:
        load_dotenv()
        self._load_config()

    def _load_config(self) -> None:
        self.math_url = os.getenv("MATH_AGENT_URL", "http://127.0.0.1:9101").rstrip("/")
        self.weather_url = os.getenv("WEATHER_AGENT_URL", "http://127.0.0.1:9102").rstrip("/")
        self.research_url = os.getenv("RESEARCH_AGENT_URL", "http://127.0.0.1:9103").rstrip("/")
        self.gemma_url = os.getenv("GEMMA_AGENT_URL", "http://127.0.0.1:9104").rstrip("/")
        self.agent_timeout = env_int("ROUTER_AGENT_TIMEOUT", 90)

    def _ascii_fold(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text or "")
        stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        return stripped.replace("đ", "d").replace("Đ", "D")

    def _fallback_route(self, prompt: str) -> dict[str, str]:
        lowered = self._ascii_fold((prompt or "").strip()).lower()

        weather_keywords = [
            "thoi tiet",
            "nhiet do",
            "mua",
            "nang",
            "gio",
            "forecast",
            "weather",
        ]
        math_keywords = [
            "tinh",
            "cong",
            "tru",
            "nhan",
            "chia",
            "%",
            "+",
            "-",
            "*",
            "/",
        ]

        if looks_like_math(prompt) or any(keyword in lowered for keyword in math_keywords):
            return {"agent": "math", "reason": "fallback_math"}
        if any(keyword in lowered for keyword in weather_keywords):
            return {"agent": "weather", "reason": "fallback_weather"}
        return {"agent": "research", "reason": "fallback_research"}

    def _parse_route_result(self, text: str) -> dict[str, str] | None:
        cleaned = (text or "").strip()
        if not cleaned:
            return None

        cleaned = re.sub(r"^```(?:json|text)?\s*", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        json_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                agent = str(data.get("agent", "")).strip().lower()
                reason = str(data.get("reason", "")).strip()
                if agent in {"math", "weather", "research"}:
                    return {"agent": agent, "reason": reason or "gemma_json"}
            except json.JSONDecodeError:
                pass

        lowered = cleaned.lower()
        compact = re.sub(r"\s+", " ", lowered).strip()
        direct_patterns = [
            (r"^(math|weather|research)$", "gemma_direct"),
            (r"^agent\s*[:=]\s*(math|weather|research)$", "gemma_agent_field"),
            (r"^(math|weather|research)\b", "gemma_prefix"),
        ]
        for pattern, reason in direct_patterns:
            match = re.match(pattern, compact)
            if match:
                return {"agent": match.group(1), "reason": reason}

        return None

    def _route_with_gemma(self, prompt: str) -> dict[str, str]:
        routing_prompt = f"""
Ban la router chon 1 agent phu hop nhat.

Chi duoc chon 1 trong 3 agent:
- math: cho toan, tinh toan, phep tinh
- weather: cho thoi tiet, nhiet do, du bao
- research: cho kien thuc chung, giai thich, tong hop

Tra ve DUY NHAT JSON mot dong theo mau:
{{"agent":"math|weather|research","reason":"ngan gon"}}

Cau hoi:
{prompt}
""".strip()

        result = call_a2a_agent(self.gemma_url, routing_prompt, timeout=self.agent_timeout)
        parsed = self._parse_route_result(result)
        return parsed or self._fallback_route(prompt)

    def _call_selected_agent(self, route: dict[str, str], prompt: str) -> dict[str, Any]:
        agent = route["agent"]
        if agent == "math":
            return call_a2a_agent_detailed(self.math_url, prompt, timeout=self.agent_timeout)
        if agent == "weather":
            return call_a2a_agent_detailed(self.weather_url, prompt, timeout=self.agent_timeout)
        return call_a2a_agent_detailed(self.research_url, prompt, timeout=self.agent_timeout)

    def _needs_passthrough(self, agent_result: dict[str, Any]) -> bool:
        states = [str(s).lower() for s in agent_result.get("states", [])]
        return "input_required" in states

    def _is_failed_state(self, agent_result: dict[str, Any]) -> bool:
        states = [str(s).lower() for s in agent_result.get("states", [])]
        return "failed" in states

    def _looks_like_agent_error(self, text: str) -> bool:
        lowered = (text or "").strip().lower()
        if not lowered:
            return True
        error_markers = [
            "chat model error",
            "khong goi duoc",
            "không gọi được",
            "api connection error",
            "service unavailable",
            "error:",
            "traceback",
            "exception",
            "ssl:",
            "certificate verify failed",
        ]
        return any(marker in lowered for marker in error_markers)

    def _looks_like_prompt_echo(self, prompt: str, text: str) -> bool:
        cleaned = (text or "").strip()
        if not cleaned:
            return True
        lowered = self._ascii_fold(cleaned).lower()
        prompt_folded = self._ascii_fold((prompt or "").strip()).lower()

        echo_markers = [
            "ban la router tong hop cau tra loi cuoi cung",
            "cau hoi goc:",
            "ket qua tu agent:",
            "tra loi cuoi:",
            "nguoi dung:",
        ]
        if any(marker in lowered for marker in echo_markers):
            return True

        normalized_answer = re.sub(r"[?!.\s]+$", "", lowered).strip()
        normalized_prompt = re.sub(r"[?!.\s]+$", "", prompt_folded).strip()
        if normalized_answer == normalized_prompt:
            return True

        if len(normalized_answer) <= len(normalized_prompt) + 2 and normalized_answer.startswith(normalized_prompt):
            return True

        return False

    def _friendly_error(self, route: dict[str, str], agent_text: str) -> str:
        agent = route["agent"]
        if agent == "research":
            return (
                "ResearchAgent dang gap loi ket noi model nen chua the tra loi luc nay. "
                "Ban thu lai sau hoac kiem tra cau hinh Gemini."
            )
        if agent == "weather":
            return (
                "WeatherAgent dang gap loi nen chua lay duoc du lieu thoi tiet. "
                "Ban thu lai sau."
            )
        if agent == "math":
            return (
                "MathAgent dang gap loi khi xu ly phep tinh. "
                "Ban thu lai voi bieu thuc ngan hon."
            )
        return agent_text or "Sub-agent dang gap loi nen chua the tra loi."

    def _synthesize_with_gemma(self, user_prompt: str, route: dict[str, str], agent_text: str) -> str:
        synthesis_prompt = f"""
Ban la router tong hop cau tra loi cuoi cung bang tieng Viet.

Yeu cau:
- Khong nhac den noi bo nhu agent, tool, route
- Tra loi ro rang, ngan gon
- Neu ket qua da la cau hoi bo sung cho nguoi dung thi giu nguyen y nghia

Loai xu ly da chon: {route["agent"]}
Cau hoi goc: {user_prompt}
Ket qua tu agent:
{agent_text}

Tra loi cuoi:
""".strip()

        try:
            result = call_a2a_agent(self.gemma_url, synthesis_prompt, timeout=self.agent_timeout)
            return (result or "").strip() or agent_text
        except Exception:
            return agent_text

    def answer_sync(self, prompt: str) -> tuple[str, str]:
        prompt = (prompt or "").strip()
        if not prompt:
            return "Hoi gi do di.", "TASK_STATUS: input_required"

        trace_lines: list[str] = [
            f"USER: {prompt}",
            "TASK_STATUS: running",
        ]

        try:
            route = self._route_with_gemma(prompt)
            trace_lines.append("ROUTER: GemmaAgent")
            trace_lines.append(f"ROUTE: {route['agent']} ({route.get('reason', '')})")
        except Exception as exc:
            route = self._fallback_route(prompt)
            trace_lines.append(f"ROUTER_FALLBACK: {route['agent']} ({exc})")

        try:
            agent_result = self._call_selected_agent(route, prompt)
        except Exception as exc:
            trace_lines.append("TASK_STATUS: failed")
            trace_lines.append(f"AGENT_ERROR: {exc}")
            final_answer = self._friendly_error(route, str(exc))
            trace_lines.append(f"FINAL: {final_answer}")
            return final_answer, "\n".join(trace_lines)
        agent_text = str(agent_result.get("text", "")).strip()

        selected_name = {
            "math": "MathAgent",
            "weather": "WeatherAgent",
            "research": "ResearchAgent",
        }[route["agent"]]
        trace_lines.append(f"CALLED: {selected_name}")
        trace_lines.append(f"AGENT_TEXT: {agent_text}")

        if self._needs_passthrough(agent_result):
            trace_lines.append("TASK_STATUS: input_required")
            trace_lines.append("FINAL: passthrough_input_required")
            return agent_text, "\n".join(trace_lines)

        if self._is_failed_state(agent_result):
            final_answer = self._friendly_error(route, agent_text)
            trace_lines.append("TASK_STATUS: failed")
            trace_lines.append("SYNTHESIZED_BY: bypass_due_to_failed_state")
            trace_lines.append(f"FINAL: {final_answer}")
            return final_answer, "\n".join(trace_lines)

        if self._looks_like_agent_error(agent_text):
            final_answer = self._friendly_error(route, agent_text)
            trace_lines.append("SYNTHESIZED_BY: bypass_due_to_agent_error")
            trace_lines.append("TASK_STATUS: failed")
            trace_lines.append(f"FINAL: {final_answer}")
            return final_answer, "\n".join(trace_lines)

        final_answer = self._synthesize_with_gemma(prompt, route, agent_text)
        if self._looks_like_agent_error(final_answer) or self._looks_like_prompt_echo(prompt, final_answer):
            final_answer = agent_text
        trace_lines.append("SYNTHESIZED_BY: GemmaAgent")
        trace_lines.append("TASK_STATUS: completed")
        trace_lines.append(f"FINAL: {final_answer}")
        return final_answer, "\n".join(trace_lines)

    async def answer(self, prompt: str) -> tuple[str, str]:
        return await asyncio.to_thread(self.answer_sync, prompt)


class RouterAgentExecutor(AgentExecutor, AgentAppMixin):
    agent_name = "RouterAgent"
    agent_description = "Custom A2A router using GemmaAgent for routing and synthesis."
    skill_id = "router_orchestrator"
    skill_name = "Router Orchestrator"
    skill_description = "Routes requests to math, weather, research, then synthesizes the final answer."
    skill_tags = ["router", "orchestration", "multi-agent"]
    skill_examples = [
        "Tinh 10 nhan 10 roi cong 100",
        "Thoi tiet Da Nang hom nay",
        "Giai thich machine learning la gi",
    ]

    def __init__(self) -> None:
        self.router = RouterBeeAI()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        prompt = (context.get_user_input() or "").strip()
        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        if not prompt:
            await updater.requires_input(
                new_agent_text_message("Ban muon hoi gi?", task.context_id, task.id),
            )
            return

        try:
            await updater.start_work()
            answer, _trace = await self.router.answer(prompt)
        except Exception as exc:
            await updater.failed(
                new_agent_text_message(
                    f"RouterAgent gap loi: {exc}",
                    task.context_id,
                    task.id,
                )
            )
            return

        await updater.complete(new_agent_text_message(answer, task.context_id, task.id))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None


async def run_cli() -> None:
    router = RouterBeeAI()
    print("RouterAgent CLI")

    while True:
        try:
            prompt = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if prompt.lower() in {"exit", "quit"}:
            break

        answer, trace = await router.answer(prompt)
        print("===== ANSWER =====")
        print(answer)
        print("\n===== TRACE =====")
        print(trace)


def run_expr(expr: str, show_trace: bool) -> None:
    answer, trace = asyncio.run(RouterBeeAI().answer(expr))
    print(answer)
    if show_trace:
        print("\n===== TRACE =====")
        print(trace)


def main() -> None:
    maybe_load_env()
    parser = build_parser("Router Agent")
    args = parser.parse_args()

    if args.cli:
        asyncio.run(run_cli())
        return

    if args.expr:
        run_expr(args.expr, args.show_trace)
        return

    host = env_str("AGENT_HOST", "127.0.0.1")
    port = env_int("ROUTER_AGENT_PORT", 9100)
    run_a2a_server(RouterAgentExecutor(), RouterAgentExecutor(), host, port)


if __name__ == "__main__":
    main()

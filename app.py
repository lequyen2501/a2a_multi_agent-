from __future__ import annotations
import io
import asyncio
import os
from dotenv import load_dotenv

from beeai_framework.middleware.trajectory import GlobalTrajectoryMiddleware
from beeai_framework.backend import ChatModel
from beeai_framework.memory.unconstrained_memory import UnconstrainedMemory
from beeai_framework.tools import Tool
from beeai_framework.tools.handoff import HandoffTool
from beeai_framework.tools.think import ThinkTool

from beeai_framework.adapters.a2a.serve.server import A2AServer, A2AServerConfig
from beeai_framework.adapters.a2a.agents import A2AAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement
from beeai_framework.serve.utils import LRUMemoryManager

from common import build_parser, env_int, env_str, maybe_load_env


# =============================
# 🔍 TRACE SUMMARY (fix lỗi app)
# =============================
KNOWN_AGENT_NAMES = ("MathAgent", "WeatherAgent", "ResearchAgent")


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


# =============================
# 🚀 ROUTER
# =============================
class RouterBeeAI:
    def __init__(self) -> None:
        load_dotenv()
        self._load_config()

    def _load_config(self) -> None:
        # 👇 multi-model fallback
        self.models = [
            os.getenv("GEMINI_CHAT_MODEL", "gemini-3.1-flash-lite-preview").strip(),
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ]

        self.math_url = os.getenv("MATH_AGENT_URL", "http://127.0.0.1:9101").rstrip("/")
        self.weather_url = os.getenv("WEATHER_AGENT_URL", "http://127.0.0.1:9102").rstrip("/")
        self.research_url = os.getenv("RESEARCH_AGENT_URL", "http://127.0.0.1:9103").rstrip("/")

        print("Router models:", self.models)

    async def _create_agents(self):
        math_agent = A2AAgent(url=self.math_url, memory=UnconstrainedMemory())
        weather_agent = A2AAgent(url=self.weather_url, memory=UnconstrainedMemory())
        research_agent = A2AAgent(url=self.research_url, memory=UnconstrainedMemory())

        await asyncio.gather(
            math_agent.check_agent_exists(),
            weather_agent.check_agent_exists(),
            research_agent.check_agent_exists(),
        )

        return math_agent, weather_agent, research_agent

    def _create_tools(self, math_agent, weather_agent, research_agent):
        return [
            ThinkTool(),
            HandoffTool(
                target=math_agent,
                name=math_agent.name,
                description=math_agent.agent_card.description or "Giải toán",
            ),
            HandoffTool(
                target=weather_agent,
                name=weather_agent.name,
                description=weather_agent.agent_card.description or "Thời tiết",
            ),
            HandoffTool(
                target=research_agent,
                name=research_agent.name,
                description=research_agent.agent_card.description or "Research",
            ),
        ]

    def _get_instructions(self, math, weather, research):
        return f"""
Bạn là Router Agent.

BẮT BUỘC:
1. ThinkTool
2. Gọi HandoffTool
3. ThinkTool
4. Trả lời

Chọn:
- toán → {math}
- thời tiết → {weather}
- kiến thức → {research}

Không được trả lời trực tiếp.
""".strip()

    async def _build_agent(self, model_name: str):
        math_agent, weather_agent, research_agent = await self._create_agents()
        tools = self._create_tools(math_agent, weather_agent, research_agent)

        return RequirementAgent(
            name="RouterAgent",
            description="Router multi-agent",
            llm=ChatModel.from_name(f"gemini:{model_name}"),
            tools=tools,
            requirements=[
                ConditionalRequirement(
                    ThinkTool,
                    force_at_step=1,
                    force_after=[Tool],
                    consecutive_allowed=False,
                )
            ],
            memory=UnconstrainedMemory(),
            role="A2A Router",
            instructions=self._get_instructions(
                math_agent.name,
                weather_agent.name,
                research_agent.name,
            ),
        )

    async def answer(self, prompt: str):
        prompt = (prompt or "").strip()
        if not prompt:
            return "Hỏi gì đó đi.", ""

        last_error = None

        for model_name in self.models:
            try:
                print(f"👉 Trying model: {model_name}")

                agent = await self._build_agent(model_name)

                trace_buffer = io.StringIO()

                result = await agent.run(prompt).middleware(
                    GlobalTrajectoryMiddleware(
                        included=[Tool],
                        pretty=True,
                        target=trace_buffer,
                    )
                )

                self.model_name = model_name
                return result.last_message.text, trace_buffer.getvalue()

            except Exception as exc:
                print(f"❌ Model failed: {model_name} -> {exc}")
                last_error = exc
                await asyncio.sleep(1)

        return f"Tất cả model lỗi: {last_error}", ""


# =============================
# CLI
# =============================
async def run_cli():
    router = RouterBeeAI()
    print("Router CLI")

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


# =============================
# SERVER
# =============================
def serve():
    router = RouterBeeAI()
    agent = asyncio.run(router._build_agent(router.models[0]))

    host = env_str("AGENT_HOST", "127.0.0.1")
    port = env_int("ROUTER_AGENT_PORT", 9100)

    A2AServer(
        config=A2AServerConfig(host=host, port=port, protocol="jsonrpc"),
        memory_manager=LRUMemoryManager(maxsize=100),
    ).register(agent, send_trajectory=True).serve()


def main():
    maybe_load_env()
    parser = build_parser("Router Agent")
    args = parser.parse_args()

    if args.cli:
        asyncio.run(run_cli())
    else:
        serve()


if __name__ == "__main__":
    main()
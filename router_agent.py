from __future__ import annotations
import io
import asyncio
import os
import traceback
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


class RouterBeeAI:
    def __init__(self) -> None:
        load_dotenv()
        self._load_config()
        self._agent: RequirementAgent | None = None

    def _load_config(self) -> None:
        primary_model = os.getenv(
            "GEMINI_CHAT_MODEL",
            "gemini-3.1-flash-lite-preview"
        ).strip()
        self.model_names = list(dict.fromkeys([
            "gemini-2.5-flash",
        ]))

        self.math_url = os.getenv("MATH_AGENT_URL", "http://127.0.0.1:9101").rstrip("/")
        self.weather_url = os.getenv("WEATHER_AGENT_URL", "http://127.0.0.1:9102").rstrip("/")
        self.research_url = os.getenv("RESEARCH_AGENT_URL", "http://127.0.0.1:9103").rstrip("/")

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
        think_tool = ThinkTool()

        handoff_math = HandoffTool(
            target=math_agent,
            name=math_agent.name,
            description=math_agent.agent_card.description or "Giải toán.",
        )

        handoff_weather = HandoffTool(
            target=weather_agent,
            name=weather_agent.name,
            description=weather_agent.agent_card.description or "Xem thời tiết.",
        )

        handoff_research = HandoffTool(
            target=research_agent,
            name=research_agent.name,
            description=research_agent.agent_card.description or "Research thông tin.",
        )

        return [think_tool, handoff_math, handoff_weather, handoff_research]

    def _get_instructions(self, math_name, weather_name, research_name):
        return f"""
Bạn là Router Agent điều phối nhiều sub-agent.

🚨 BẮT BUỘC TUÂN THỦ LUẬT:

## 1. KHÔNG ĐƯỢC TRẢ LỜI TRỰC TIẾP
Nếu trả lời trực tiếp → coi là SAI nhiệm vụ.

## 2. LUÔN LUÔN THEO QUY TRÌNH:
Bước 1: ThinkTool (phân tích câu hỏi)
Bước 2: BẮT BUỘC chọn 1 HandoffTool phù hợp và gọi nó
Bước 3: ThinkTool (tổng hợp kết quả)
Bước 4: Trả lời cuối cùng

## 3. QUY TẮC CHỌN AGENT:
- Nếu liên quan toán, tính toán → MUST gọi: {math_name}
- Nếu liên quan thời tiết → MUST gọi: {weather_name}
- Nếu kiến thức chung, giải thích → MUST gọi: {research_name}

## 4. QUY TẮC TOOL:
- CẤM bỏ qua HandoffTool
- CẤM trả lời khi chưa gọi tool
- Mỗi request PHẢI có ít nhất 1 tool call

## 5. OUTPUT FORMAT:
Chỉ được trả về kết quả cuối cùng bằng tiếng Việt.
""".strip()

    async def build_agent(self, model_name: str):
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

    async def get_agent(self):
        if self._agent is None:
            self._agent = await self.build_agent(self.model_names[0])
        return self._agent

    async def answer(self, prompt: str):
        prompt = (prompt or "").strip()
        if not prompt:
            return "Hỏi gì đó đi.", ""

        last_error: Exception | None = None

        for model_name in self.model_names:
            try:
                print(f"[Router] Dang thu model: {model_name}")
                agent = await self.build_agent(model_name)
                trace_buffer = io.StringIO()

                result = await agent.run(prompt).middleware(
                    GlobalTrajectoryMiddleware(
                        included=[Tool],
                        pretty=True,
                        target=trace_buffer,
                    )
                )

                print(f"[Router] Model thanh cong: {model_name}")
                return result.last_message.text, trace_buffer.getvalue()
            except Exception as exc:
                last_error = exc
                print(f"[Router] Model that bai: {model_name} -> {exc}")
                traceback.print_exc()
                continue

        error_text = str(last_error or "Khong xac dinh duoc loi")
        if "503" in error_text or "high demand" in error_text.lower() or "UNAVAILABLE" in error_text:
            return (
                "Model Gemini dang qua tai tam thoi. Ban thu lai sau it phut hoac doi model khac.",
                "",
            )
        return (f"Khong goi duoc model: {error_text}", "")


async def run_cli():
    router = RouterBeeAI()
    print("RouterAgent CLI")

    while True:
        try:
            prompt = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if prompt.lower() in {"exit", "quit"}:
            break

        try:
            answer, trace = await router.answer(prompt)
            print("===== ANSWER =====")
            print(answer)

            print("\n===== TRACE =====")
            print(trace)
        except Exception as exc:
            print(f"Loi khi xu ly cau hoi: {exc}")
            traceback.print_exc()


def serve():
    router = RouterBeeAI()
    agent = asyncio.run(router.get_agent())
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

    try:
        if args.cli:
            asyncio.run(run_cli())
            return

        serve()
    except KeyboardInterrupt:
        print("\nDang dung Router Agent.")


if __name__ == "__main__":
    main()

from __future__ import annotations

import asyncio
import os

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.utils import new_agent_text_message, new_task
from beeai_framework.backend import ChatModel, SystemMessage, UserMessage
from dotenv import load_dotenv

from common import AgentAppMixin, build_parser, env_int, maybe_load_env, run_a2a_server


class ResearchAgentCore:
    def __init__(self) -> None:
        load_dotenv()

        configured_model = (
            os.getenv("RESEARCH_MODEL")
            or os.getenv("GEMINI_CHAT_MODEL")
            or "gemini-2.5-flash-lite"
        ).strip()
        self.model_name = (
            configured_model
            if ":" in configured_model
            else f"gemini:{configured_model}"
        )
        print(f"Research model: {self.model_name}")
        self.model = ChatModel.from_name(self.model_name)

    async def research_async(self, query: str) -> str:
        query = (query or "").strip()
        if not query:
            return "Ban muon research chu de gi?"

        output = await self.model.run(
            [
                SystemMessage("Ban la research assistant. Tra loi tieng Viet ngan gon, ro rang."),
                UserMessage(f"Hay research: {query}"),
            ],
            temperature=0.2,
        )

        return output.get_text_content().strip() or "Khong co ket qua."

    def research(self, query: str) -> str:
        return asyncio.run(self.research_async(query))


class ResearchAgentExecutor(AgentExecutor, AgentAppMixin):
    agent_name = "ResearchAgent"
    agent_description = "A2A Research Agent (Gemini)"

    def __init__(self) -> None:
        self.agent = ResearchAgentCore()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        prompt = (context.get_user_input() or "").strip()
        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        if not prompt:
            await updater.requires_input(
                new_agent_text_message(
                    "Ban muon research chu de gi?",
                    task.context_id,
                    task.id,
                ),
            )
            return

        try:
            await updater.start_work()
            result = await self.agent.research_async(prompt)
        except Exception as exc:
            await updater.failed(
                new_agent_text_message(
                    f"ResearchAgent gap loi: {exc}",
                    task.context_id,
                    task.id,
                )
            )
            return

        await updater.complete(
            new_agent_text_message(result, task.context_id, task.id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None


def run_cli() -> None:
    agent = ResearchAgentCore()
    print("ResearchAgent CLI")

    while True:
        try:
            q = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if q.lower() in {"exit", "quit"}:
            break

        print(agent.research(q))
        print()


def run_expr(expr: str) -> None:
    print(ResearchAgentCore().research(expr))


def main() -> None:
    maybe_load_env()
    parser = build_parser("Research Agent")
    args = parser.parse_args()

    if args.cli:
        run_cli()
        return

    if args.expr:
        run_expr(args.expr)
        return

    host = os.getenv("AGENT_HOST", "127.0.0.1")
    port = env_int("RESEARCH_AGENT_PORT", 9103)

    run_a2a_server(
        ResearchAgentExecutor(),
        ResearchAgentExecutor(),
        host,
        port,
    )


if __name__ == "__main__":
    main()

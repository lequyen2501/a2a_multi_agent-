from __future__ import annotations
import asyncio
import os
from dotenv import load_dotenv

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from a2a.utils import new_agent_text_message, new_task

from beeai_framework.backend import ChatModel, SystemMessage, UserMessage

from common import AgentAppMixin, build_parser, env_int, maybe_load_env, run_a2a_server


class ResearchAgentCore:
    def __init__(self) -> None:
        load_dotenv()

        self.model_name = os.getenv(
            "GEMINI_CHAT_MODEL",
            "gemini-2.5-flash"
        ).strip()
        print(f"Model string: 'gemini:{self.model_name}'")
        self.model = ChatModel.from_name(
            f"gemini:{self.model_name}"
)

    async def research_async(self, query: str) -> str:
        query = (query or "").strip()
        if not query:
            return "Bạn muốn research chủ đề gì?"

        output = await self.model.run(
            [
                SystemMessage("Bạn là research assistant. Trả lời tiếng Việt ngắn gọn."),
                UserMessage(f"Hãy research: {query}")
            ],
            temperature=0.2
        )

        return output.get_text_content().strip() or "Không có kết quả"

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
            await updater.update_status(
                TaskState.input_required,
                new_agent_text_message(
                    "Bạn muốn research chủ đề gì?",
                    task.context_id,
                    task.id
                ),
                final=True,
            )
            return

        result = await self.agent.research_async(prompt)

        await updater.complete(
            new_agent_text_message(result, task.context_id, task.id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None


def run_cli() -> None:
    agent = ResearchAgentCore()
    print("ResearchAgent CLI (Gemini)")

    while True:
        try:
            q = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if q.lower() in {"exit", "quit"}:
            break
    print(agent.research(q))
    print()


def main() -> None:
    maybe_load_env()
    parser = build_parser("Research Agent")
    args = parser.parse_args()

    if args.cli:
        run_cli()
        return

    host = os.getenv("AGENT_HOST", "127.0.0.1")
    port = env_int("RESEARCH_AGENT_PORT", 9103)

    run_a2a_server(
        ResearchAgentExecutor(),
        ResearchAgentExecutor(),
        host,
        port
    )


if __name__ == "__main__":
    main()

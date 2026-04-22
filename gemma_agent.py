from __future__ import annotations

import os

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from a2a.utils import new_agent_text_message, new_task
from dotenv import load_dotenv

from common import AgentAppMixin, build_parser, env_int, env_str, maybe_load_env, run_a2a_server

try:
    from gradio_client import Client
except ImportError:  # pragma: no cover - handled at runtime
    Client = None  # type: ignore[assignment]


class GemmaAgentCore:
    def __init__(self) -> None:
        load_dotenv()
        self.base_url = os.getenv("GEMMA_GRADIO_URL", "").strip().rstrip("/")
        self.api_name = os.getenv("GEMMA_GRADIO_API_NAME", "/predict").strip() or "/predict"
        self.system_prompt = (
            os.getenv("GEMMA_AGENT_SYSTEM_PROMPT")
            or "Ban la Gemma Agent. Tra loi tieng Viet ro rang, ngan gon, huu ich."
        ).strip()
        self._client: Client | None = None

    def _get_client(self) -> Client:
        if Client is None:
            raise RuntimeError(
                "Chua cai gradio_client. Hay cai dependency bang `pip install gradio_client`."
            )
        if not self.base_url:
            raise RuntimeError(
                "Chua cau hinh GEMMA_GRADIO_URL trong env. "
                "Gia tri nay la share URL cua Gradio host Gemma tren Colab."
            )
        if self._client is None:
            self._client = Client(self.base_url)
        return self._client

    def _build_prompt(self, prompt: str) -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            return ""
        return f"{self.system_prompt}\n\nNguoi dung: {prompt}\n\nTra loi:"

    def answer(self, prompt: str) -> str:
        cleaned = (prompt or "").strip()
        if not cleaned:
            return "Ban muon hoi Gemma dieu gi?"

        client = self._get_client()
        final_prompt = self._build_prompt(cleaned)

        try:
            result = client.predict(final_prompt, api_name=self.api_name)
        except Exception as exc:
            raise RuntimeError(f"Khong goi duoc Gemma host: {exc}") from exc

        if isinstance(result, tuple):
            result = result[0]
        if isinstance(result, list):
            result = "\n".join(str(item) for item in result if str(item).strip())

        text = str(result).strip()
        return text or "Gemma khong tra ve noi dung."


class GemmaAgentExecutor(AgentExecutor, AgentAppMixin):
    agent_name = "GemmaAgent"
    agent_description = "A2A Gemma Agent goi toi Gradio host Gemma tren Colab."
    skill_id = "gemma_reasoning"
    skill_name = "Gemma Reasoning"
    skill_description = "Tra loi, tom tat, va tong hop bang Gemma host tu xa."
    skill_tags = ["gemma", "llm", "reasoning", "summary"]
    skill_examples = [
        "Tom tat doan van nay",
        "Giai thich su khac nhau giua CPU va GPU",
        "Tong hop ket qua tu cac agent",
    ]

    def __init__(self) -> None:
        self.agent = GemmaAgentCore()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        prompt = (context.get_user_input() or "").strip()
        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        if not prompt:
            await updater.requires_input(
                new_agent_text_message("Ban muon Gemma xu ly noi dung gi?", task.context_id, task.id),
            )
            return

        try:
            await updater.start_work()
            result = self.agent.answer(prompt)
        except Exception as exc:
            await updater.failed(
                new_agent_text_message(f"Khong goi duoc Gemma Agent: {exc}", task.context_id, task.id)
            )
            return

        await updater.complete(new_agent_text_message(result, task.context_id, task.id))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None


def run_cli() -> None:
    agent = GemmaAgentCore()
    print("GemmaAgent CLI")
    print("Go 'exit' de thoat.\n")

    while True:
        try:
            prompt = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThoat.")
            break

        if prompt.lower() in {"exit", "quit"}:
            print("Thoat.")
            break

        try:
            print(agent.answer(prompt))
        except Exception as exc:
            print(f"Loi: {exc}")
        print()


def main() -> None:
    maybe_load_env()
    parser = build_parser("Gemma A2A Agent")
    args = parser.parse_args()

    if args.expr is not None:
        print(GemmaAgentCore().answer(args.expr))
        return

    if args.cli:
        run_cli()
        return

    host = env_str("AGENT_HOST", "127.0.0.1")
    port = env_int("GEMMA_AGENT_PORT", 9104)
    run_a2a_server(GemmaAgentExecutor(), GemmaAgentExecutor(), host, port)


if __name__ == "__main__":
    main()

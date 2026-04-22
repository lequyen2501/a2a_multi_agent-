from __future__ import annotations

import ast
import operator
import re

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.utils import new_agent_text_message, new_task

from common import AgentAppMixin, build_parser, env_int, env_str, maybe_load_env, run_a2a_server


class SafeMathEvaluator:
    _bin_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    _unary_ops = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(self, expression: str) -> float:
        tree = ast.parse(expression, mode="eval")
        return float(self._eval_node(tree.body))

    def _eval_node(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)

        if isinstance(node, ast.BinOp) and type(node.op) in self._bin_ops:
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)

            if isinstance(node.op, ast.Div) and right == 0:
                raise ZeroDivisionError("division by zero")

            if isinstance(node.op, ast.Pow) and (abs(left) > 1_000_000 or abs(right) > 12):
                raise ValueError("Exponent too large")

            return self._bin_ops[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp) and type(node.op) in self._unary_ops:
            return self._unary_ops[type(node.op)](self._eval_node(node.operand))

        raise ValueError("Only safe arithmetic expressions are allowed.")


class MathNormalizer:
    _phrase_replacements = [
        (r"\btinh\s+tong\s+cua\b", ""),
        (r"\btinh\s+tong\b", ""),
        (r"\btong\s+cua\b", ""),
        (r"\btinh\s+hieu\b", ""),
        (r"\btinh\s+tich\b", ""),
        (r"\btinh\s+thuong\b", ""),
        (r"\btinh\b", ""),
        (r"\bket\s+qua\s+cua\b", ""),
        (r"\bla\s+bao\s+nhieu\b", ""),
        (r"\bbang\s+bao\s+nhieu\b", ""),
    ]

    _word_replacements = [
        (r"\bcong\b", "+"),
        (r"\btru\b", "-"),
        (r"\bnhan\b", "*"),
        (r"\bchia\b", "/"),
        (r"\bmod\b", "%"),
        (r"\bphan\s+du\b", "%"),
        (r"\bmu\b", "**"),
        (r"\bluy\s+thua\b", "**"),
        (r"\bbinh\s+phuong\s+cua\s*(\d+(?:\.\d+)?)\b", r"\1 ** 2"),
        (r"\bgap\s+(\d+(?:\.\d+)?)\s+lan\b", r"* \1"),
    ]

    def normalize(self, text: str) -> str:
        s = text.strip().lower()
        if not s:
            return s

        for pattern, replacement in self._phrase_replacements:
            s = re.sub(pattern, replacement, s)

        for pattern, replacement in self._word_replacements:
            s = re.sub(pattern, replacement, s)

        s = re.sub(r"\bmay\b", "", s)
        s = re.sub(r"\bbao\s+nhieu\b", "", s)
        s = re.sub(r"\bgiup\s+minh\b", "", s)
        s = re.sub(r"\bcho\s+minh\b", "", s)
        s = re.sub(r"\bgium\s+minh\b", "", s)

        nums = re.findall(r"\d+(?:\.\d+)?", s)
        if len(nums) == 2:
            if any(k in text.lower() for k in ["tong", "cong"]):
                s = re.sub(r"\b(va|voi)\b", "+", s)
            elif any(k in text.lower() for k in ["hieu", "tru"]):
                s = re.sub(r"\b(va|voi)\b", "-", s)
            elif any(k in text.lower() for k in ["tich", "nhan"]):
                s = re.sub(r"\b(va|voi)\b", "*", s)
            elif any(k in text.lower() for k in ["thuong", "chia"]):
                s = re.sub(r"\b(va|voi)\b", "/", s)

        s = re.sub(r"\b(voi|va)\b", " ", s)
        s = re.sub(r"[^0-9+\-*/%().\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        s = s.replace("( ", "(").replace(" )", ")")
        return s


class MathAgentCore:
    def __init__(self) -> None:
        self.evaluator = SafeMathEvaluator()
        self.normalizer = MathNormalizer()

    def answer(self, prompt: str) -> str:
        cleaned = prompt.strip()
        if not cleaned:
            return "Bieu thuc khong hop le."

        normalized = self.normalizer.normalize(cleaned)
        if not normalized:
            return "Bieu thuc khong hop le. Chua trich xuat duoc phep tinh tu cau hoi."

        try:
            result = self.evaluator.evaluate(normalized)
        except ZeroDivisionError:
            return "Khong the chia cho 0."
        except Exception:
            return (
                "Bieu thuc khong hop le. Chi ho tro +, -, *, /, %, ** va ngoac (). "
                f"Bieu thuc da chuan hoa: `{normalized}`"
            )

        expr_label = normalized if normalized != cleaned else cleaned
        if result.is_integer():
            return f"Ket qua cua `{expr_label}` la {int(result)}."
        return f"Ket qua cua `{expr_label}` la {result}."


class MathAgentExecutor(AgentExecutor, AgentAppMixin):
    agent_name = "MathAgent"
    agent_description = (
        "Deterministic A2A math agent for safe arithmetic calculations. "
        "Co the hieu mot so cau tieng Viet don gian nhu 'tinh tong 3 va 3'."
    )
    skill_id = "math_compute"
    skill_name = "Math Compute"
    skill_description = "Computes arithmetic expressions using +, -, *, /, %, ** and parentheses."
    skill_tags = ["math", "calculator", "arithmetic"]
    skill_examples = ["12 + 7", "(20 / 5) * 3", "2 ** 5 + 1", "tinh tong 3 va 3"]

    def __init__(self) -> None:
        self.agent = MathAgentCore()

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
                    "Ban muon tinh phep toan nao?",
                    task.context_id,
                    task.id,
                )
            )
            return

        try:
            await updater.start_work()
            response = self.agent.answer(prompt)
        except Exception as exc:
            await updater.failed(
                new_agent_text_message(
                    f"MathAgent gap loi: {exc}",
                    task.context_id,
                    task.id,
                )
            )
            return

        await updater.complete(
            new_agent_text_message(response, task.context_id, task.id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None


def run_cli() -> None:
    agent = MathAgentCore()
    print("MathAgent CLI")
    print("Nhap bieu thuc hoac cau tieng Viet don gian. Go 'exit' de thoat.\n")
    while True:
        try:
            prompt = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThoat.")
            break

        if prompt.lower() in {"exit", "quit"}:
            print("Thoat.")
            break

        print(agent.answer(prompt))


def main() -> None:
    maybe_load_env()
    parser = build_parser("Math A2A Agent")
    args = parser.parse_args()

    if args.expr is not None:
        print(MathAgentCore().answer(args.expr))
        return

    if args.cli:
        run_cli()
        return

    host = env_str("AGENT_HOST", "127.0.0.1")
    port = env_int("MATH_AGENT_PORT", 9101)
    run_a2a_server(MathAgentExecutor(), MathAgentExecutor(), host, port)


if __name__ == "__main__":
    main()

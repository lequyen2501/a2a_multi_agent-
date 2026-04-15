from __future__ import annotations

import ast
import operator
import re

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from common import AgentAppMixin, build_parser, env_int, env_str, maybe_load_env, run_a2a_server


class SafeMathEvaluator:
    """Safe evaluator cho arithmetic expressions sử dụng AST."""

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
        """Evaluate biểu thức an toàn."""
        tree = ast.parse(expression, mode="eval")
        return float(self._eval_node(tree.body))

    def _eval_node(self, node: ast.AST) -> float:
        """Evaluate AST node."""
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
    """Normalizer cho math expressions từ tiếng Việt."""

    _phrase_replacements = [
        (r"\btính\s+tổng\s+của\b", ""),
        (r"\btính\s+tổng\b", ""),
        (r"\btổng\s+của\b", ""),
        (r"\btính\s+hiệu\b", ""),
        (r"\btính\s+tích\b", ""),
        (r"\btính\s+thương\b", ""),
        (r"\btính\b", ""),
        (r"\bkết\s+quả\s+của\b", ""),
        (r"\blà\s+bao\s+nhiêu\b", ""),
        (r"\bbằng\s+bao\s+nhiêu\b", ""),
    ]

    _word_replacements = [
        (r"\bcộng\b", "+"),
        (r"\btrừ\b", "-"),
        (r"\bnhân\b", "*"),
        (r"\bchia\b", "/"),
        (r"\bmod\b", "%"),
        (r"\bphần\s+dư\b", "%"),
        (r"\bmũ\b", "**"),
        (r"\blũy\s+thừa\b", "**"),
        (r"\bbình\s+phương\s+của\s*(\d+(?:\.\d+)?)\b", r"\1 ** 2"),
        (r"\bgấp\s+(\d+(?:\.\d+)?)\s+lần\b", r"* \1"),
    ]

    def normalize(self, text: str) -> str:
        """Chuẩn hóa text thành biểu thức math."""
        s = text.strip().lower()
        if not s:
            return s

        for pattern, replacement in self._phrase_replacements:
            s = re.sub(pattern, replacement, s)

        for pattern, replacement in self._word_replacements:
            s = re.sub(pattern, replacement, s)

        s = re.sub(r"\bmấy\b", "", s)
        s = re.sub(r"\bbao\s+nhiêu\b", "", s)
        s = re.sub(r"\bgiúp\s+mình\b", "", s)
        s = re.sub(r"\bcho\s+mình\b", "", s)
        s = re.sub(r"\bgiùm\s+mình\b", "", s)

        # Xử lý 'và'/'với' dựa trên operation
        nums = re.findall(r"\d+(?:\.\d+)?", s)
        if len(nums) == 2:
            if any(k in text.lower() for k in ["tổng", "cộng"]):
                s = re.sub(r"\b(và|với)\b", "+", s)
            elif any(k in text.lower() for k in ["hiệu", "trừ"]):
                s = re.sub(r"\b(và|với)\b", "-", s)
            elif any(k in text.lower() for k in ["tích", "nhân"]):
                s = re.sub(r"\b(và|với)\b", "*", s)
            elif any(k in text.lower() for k in ["thương", "chia"]):
                s = re.sub(r"\b(và|với)\b", "/", s)

        s = re.sub(r"\b(với|và)\b", " ", s)
        s = re.sub(r"[^0-9+\-*/%().\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        s = s.replace("( ", "(").replace(" )", ")")
        return s


class MathAgentCore:
    """Core logic cho math agent."""

    def __init__(self) -> None:
        self.evaluator = SafeMathEvaluator()
        self.normalizer = MathNormalizer()

    def answer(self, prompt: str) -> str:
        """Tính toán biểu thức từ prompt."""
        cleaned = prompt.strip()
        if not cleaned:
            return "Biểu thức không hợp lệ."

        normalized = self.normalizer.normalize(cleaned)
        if not normalized:
            return "Biểu thức không hợp lệ. Chưa trích xuất được phép tính từ câu hỏi."

        try:
            result = self.evaluator.evaluate(normalized)
        except ZeroDivisionError:
            return "Không thể chia cho 0."
        except Exception:
            return (
                "Biểu thức không hợp lệ. Chỉ hỗ trợ +, -, *, /, %, ** và ngoặc (). "
                f"Biểu thức đã chuẩn hóa: `{normalized}`"
            )

        expr_label = normalized if normalized != cleaned else cleaned
        if result.is_integer():
            return f"Kết quả của `{expr_label}` là {int(result)}."
        return f"Kết quả của `{expr_label}` là {result}."


class MathAgentExecutor(AgentExecutor, AgentAppMixin):
    """Executor cho math agent."""
    agent_name = "MathAgent"
    agent_description = (
        "Deterministic A2A math agent for safe arithmetic calculations. "
        "Có thể hiểu một số câu tiếng Việt đơn giản như 'tính tổng 3 và 3'."
    )
    skill_id = "math_compute"
    skill_name = "Math Compute"
    skill_description = "Computes arithmetic expressions using +, -, *, /, %, ** and parentheses."
    skill_tags = ["math", "calculator", "arithmetic"]
    skill_examples = ["12 + 7", "(20 / 5) * 3", "2 ** 5 + 1", "tính tổng 3 và 3"]

    def __init__(self) -> None:
        self.agent = MathAgentCore()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        prompt = context.get_user_input()
        response = self.agent.answer(prompt)
        await event_queue.enqueue_event(new_agent_text_message(response))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None


def run_cli() -> None:
    """Chạy CLI interface."""
    agent = MathAgentCore()
    print("MathAgent CLI")
    print("Nhập biểu thức hoặc câu tiếng Việt đơn giản. Gõ 'exit' để thoát.\n")
    while True:
        try:
            prompt = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThoát.")
            break

        if prompt.lower() in {"exit", "quit"}:
            print("Thoát.")
            break

        print(agent.answer(prompt))


def main() -> None:
    """Main entry point."""
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

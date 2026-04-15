from __future__ import annotations

import re
import unicodedata
from typing import Any

import requests
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from a2a.utils import new_agent_text_message, new_task

from common import AgentAppMixin, build_parser, env_int, env_str, maybe_load_env, run_a2a_server


WEATHER_CODE_MAP = {
    0: "troi quang",
    1: "kha quang",
    2: "it may",
    3: "u am",
    45: "suong mu",
    48: "suong mu dong bang",
    51: "mua phun nhe",
    53: "mua phun vua",
    55: "mua phun day",
    61: "mua nhe",
    63: "mua vua",
    65: "mua to",
    71: "tuyet nhe",
    73: "tuyet vua",
    75: "tuyet day",
    80: "mua rao nhe",
    81: "mua rao vua",
    82: "mua rao manh",
    95: "dong",
    96: "dong co mua da nhe",
    99: "dong co mua da manh",
}


class WeatherAgentCore:
    def ask_for_location(self) -> str:
        return "Ban muon xem thoi tiet o dau?"

    def _ascii_fold(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text or "")
        stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        return stripped.replace("đ", "d").replace("Đ", "D")

    def _clean_location_candidate(self, text: str) -> str:
        location = (text or "").strip(" .?!,;:")
        location = self._ascii_fold(location)
        location = re.sub(
            r"\b(hom nay|hom qua|ngay mai|nhu the nao|ra sao|bao nhieu do|co mua khong|mua khong|nang khong|today)\b",
            "",
            location,
            flags=re.IGNORECASE,
        )
        location = re.sub(r"\s+", " ", location).strip(" .?!,;:")
        return location

    def needs_location(self, prompt: str) -> bool:
        cleaned = self._ascii_fold((prompt or "").strip()).lower()
        if not cleaned:
            return True

        generic_phrases = {
            "thoi tiet",
            "thoi tiet hom nay",
            "thoi tiet nhu nao",
            "thoi tiet the nao",
            "hom nay thoi tiet the nao",
            "nhiet do",
            "weather",
            "weather today",
            "forecast",
        }
        if cleaned in generic_phrases:
            return True

        weather_keywords = ["thoi tiet", "nhiet do", "weather", "forecast", "mua", "nang"]
        location_hints = [" o ", " tai ", " in "]

        has_weather_keyword = any(k in cleaned for k in weather_keywords)
        has_location_hint = any(h in f" {cleaned} " for h in location_hints)

        return bool(has_weather_keyword and not has_location_hint)

    def normalize_location(self, prompt: str) -> str:
        cleaned = (prompt or "").strip()
        lowered = self._ascii_fold(cleaned).lower()

        prefixes = [
            "thoi tiet o ",
            "thoi tiet tai ",
            "nhiet do o ",
            "nhiet do tai ",
            "weather in ",
            "forecast in ",
            "o ",
            "tai ",
        ]
        for prefix in prefixes:
            if lowered.startswith(prefix):
                location = self._clean_location_candidate(cleaned[len(prefix):])
                if location:
                    return location

        match = re.search(r"\b(?:o|tai|in)\s+(.+)$", lowered, flags=re.IGNORECASE)
        if match:
            location = self._clean_location_candidate(cleaned[match.start(1):])
            if location:
                return location

        folded = self._ascii_fold(cleaned)
        removable_patterns = [
            r"\bthoi tiet\b",
            r"\bnhiet do\b",
            r"\bweather\b",
            r"\bforecast\b",
            r"\bhom nay\b",
            r"\bhom qua\b",
            r"\bngay mai\b",
            r"\bnhu the nao\b",
            r"\bra sao\b",
            r"\bco mua khong\b",
            r"\bmua khong\b",
            r"\bnang khong\b",
            r"\btoday\b",
            r"\bo\b",
            r"\btai\b",
        ]
        for pattern in removable_patterns:
            folded = re.sub(pattern, " ", folded, flags=re.IGNORECASE)
        location = self._clean_location_candidate(folded)
        return location or self._ascii_fold(cleaned)

    def _geocode(self, location: str) -> dict[str, Any]:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1, "language": "vi", "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results") or []
        if not results:
            raise ValueError("Khong tim thay dia diem phu hop.")

        item = results[0]
        admin1 = item.get("admin1") or item.get("country") or ""
        display_name = ", ".join(x for x in [item.get("name"), admin1, item.get("country")] if x)
        return {
            "display_name": display_name,
            "latitude": item["latitude"],
            "longitude": item["longitude"],
        }

    def _forecast(self, latitude: float, longitude: float) -> dict[str, Any]:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_weather(self, location: str) -> str:
        geo = self._geocode(location)
        forecast = self._forecast(geo["latitude"], geo["longitude"])

        current = forecast.get("current", {})
        daily = forecast.get("daily", {})
        desc = WEATHER_CODE_MAP.get(current.get("weather_code", -1), "khong ro trang thai")

        t_now = current.get("temperature_2m")
        wind = current.get("wind_speed_10m")
        max_today = (daily.get("temperature_2m_max") or [None])[0]
        min_today = (daily.get("temperature_2m_min") or [None])[0]

        name = geo["display_name"]
        return (
            f"Thoi tiet tai {name}: hien tai {t_now}°C, {desc}, gio {wind} km/h. "
            f"Hom nay thap nhat {min_today}°C, cao nhat {max_today}°C."
        )


class WeatherAgentExecutor(AgentExecutor, AgentAppMixin):
    agent_name = "WeatherAgent"
    agent_description = "A2A weather agent with input-required behavior when location is missing."
    skill_id = "weather_lookup"
    skill_name = "Weather Lookup"
    skill_description = "Checks current weather and today's min/max temperature for a location."
    skill_tags = ["weather", "forecast", "open-meteo"]
    skill_examples = ["thoi tiet Ha Noi", "weather in Da Nang", "nhiet do Quy Nhon hom nay"]

    def __init__(self) -> None:
        self.agent = WeatherAgentCore()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        prompt = (context.get_user_input() or "").strip()
        task = context.current_task

        if not task:
            task = new_task(context.message)  # type: ignore[arg-type]
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        if self.agent.needs_location(prompt):
            await updater.update_status(
                TaskState.input_required,
                new_agent_text_message(self.agent.ask_for_location(), task.context_id, task.id),
                final=True,
            )
            return

        try:
            location = self.agent.normalize_location(prompt)
            content = self.agent.get_weather(location)
            await updater.complete(new_agent_text_message(content, task.context_id, task.id))
        except Exception as exc:
            message = f"Khong lay duoc thoi tiet: {exc}"
            await updater.complete(new_agent_text_message(message, task.context_id, task.id))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None


def run_cli() -> None:
    agent = WeatherAgentCore()
    print("WeatherAgent CLI")
    print("Nhap cau hoi thoi tiet. Neu thieu dia diem, agent se hoi lai. Go 'exit' de thoat.\n")

    waiting_for_location = False

    while True:
        try:
            prompt = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThoat.")
            break

        if prompt.lower() in {"exit", "quit"}:
            print("Thoat.")
            break

        if waiting_for_location:
            try:
                print(agent.get_weather(prompt))
            except Exception as exc:
                print(f"Khong lay duoc thoi tiet: {exc}")
            waiting_for_location = False
            continue

        if agent.needs_location(prompt):
            print(agent.ask_for_location())
            waiting_for_location = True
            continue

        try:
            location = agent.normalize_location(prompt)
            print(agent.get_weather(location))
        except Exception as exc:
            print(f"Khong lay duoc thoi tiet: {exc}")


def main() -> None:
    maybe_load_env()
    parser = build_parser("Weather A2A Agent")
    args = parser.parse_args()

    if args.expr is not None:
        core = WeatherAgentCore()
        if core.needs_location(args.expr):
            print(core.ask_for_location())
        else:
            try:
                print(core.get_weather(core.normalize_location(args.expr)))
            except Exception as exc:
                print(f"Khong lay duoc thoi tiet: {exc}")
        return

    if args.cli:
        run_cli()
        return

    host = env_str("AGENT_HOST", "127.0.0.1")
    port = env_int("WEATHER_AGENT_PORT", 9102)
    run_a2a_server(WeatherAgentExecutor(), WeatherAgentExecutor(), host, port)


if __name__ == "__main__":
    main()

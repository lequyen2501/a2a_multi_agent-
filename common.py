from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from typing import Any

import requests
import uvicorn
from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


class AgentAppMixin:
    agent_name: str = "Agent"
    agent_description: str = "A2A agent"
    skill_id: str = "general"
    skill_name: str = "General"
    skill_description: str = "General skill"
    skill_tags: list[str] = ["general"]
    skill_examples: list[str] = []

    def build_agent_card(self, host: str, port: int) -> AgentCard:
        skill = AgentSkill(
            id=self.skill_id,
            name=self.skill_name,
            description=self.skill_description,
            tags=self.skill_tags,
            examples=self.skill_examples,
        )
        return AgentCard(
            name=self.agent_name,
            description=self.agent_description,
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=["text"],
            default_output_modes=["text"],
            capabilities=AgentCapabilities(streaming=False),
            skills=[skill],
        )


def run_a2a_server(executor: AgentExecutor, app_mixin: AgentAppMixin, host: str, port: int) -> None:
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=app_mixin.build_agent_card(host, port),
        http_handler=request_handler,
    )
    uvicorn.run(server.build(), host=host, port=port)



def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--cli", action="store_true", help="Run local interactive CLI mode")
    parser.add_argument("--expr", type=str, help="Run a single local query and exit")
    parser.add_argument(
        "--show-trace",
        action="store_true",
        help="When used with --expr, include orchestrator trace in the output if available.",
    )
    return parser



def maybe_load_env() -> None:
    load_dotenv()



def normalize_base_url(url: str) -> str:
    return url.rstrip("/") or url



def recursive_find_texts(node: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "text" and isinstance(value, str):
                texts.append(value)
            else:
                texts.extend(recursive_find_texts(value))
    elif isinstance(node, list):
        for item in node:
            texts.extend(recursive_find_texts(item))
    return texts


def _collect_non_user_texts(node: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(node, dict):
        role = node.get("role")
        if role == "user":
            return texts
        for key, value in node.items():
            if key == "text" and isinstance(value, str):
                texts.append(value)
            else:
                texts.extend(_collect_non_user_texts(value))
    elif isinstance(node, list):
        for item in node:
            texts.extend(_collect_non_user_texts(item))
    return texts



def _recursive_find_task_state(node: Any) -> list[str]:
    states: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"state", "status"} and isinstance(value, str):
                states.append(value)
            else:
                states.extend(_recursive_find_task_state(value))
    elif isinstance(node, list):
        for item in node:
            states.extend(_recursive_find_task_state(item))
    return states



def call_a2a_agent_detailed(base_url: str, prompt: str, timeout: int = 45) -> dict[str, Any]:
    url = normalize_base_url(base_url) + "/"
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": prompt,
                    }
                ],
                "messageId": str(uuid.uuid4()),
            }
        },
    }
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        error_message = str(data["error"].get("message", "Unknown A2A error")).strip()
        return {
            "url": url,
            "prompt": prompt,
            "texts": [error_message] if error_message else [],
            "text": error_message or json.dumps(data, ensure_ascii=False, indent=2),
            "states": [],
            "raw": data,
        }

    texts = [t.strip() for t in _collect_non_user_texts(data) if isinstance(t, str) and t.strip()]
    if not texts:
        texts = [t.strip() for t in recursive_find_texts(data) if isinstance(t, str) and t.strip()]

    states = [s.strip() for s in _recursive_find_task_state(data) if isinstance(s, str) and s.strip()]
    deduped_texts = [t for t in dict.fromkeys(texts) if t != prompt]
    deduped_states = list(dict.fromkeys(states))
    return {
        "url": url,
        "prompt": prompt,
        "texts": deduped_texts,
        "text": "\n".join(deduped_texts) if deduped_texts else json.dumps(data, ensure_ascii=False, indent=2),
        "states": deduped_states,
        "raw": data,
    }



def call_a2a_agent(base_url: str, prompt: str, timeout: int = 45) -> str:
    return call_a2a_agent_detailed(base_url=base_url, prompt=prompt, timeout=timeout)["text"]


_MATH_PATTERN = re.compile(r"^[\d\s\+\-\*\/\%\(\)\.\*]+$")


def looks_like_math(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    has_digit = any(ch.isdigit() for ch in cleaned)
    has_operator = any(op in cleaned for op in ["+", "-", "*", "/", "%", "(", ")"])
    return bool(has_digit and has_operator and _MATH_PATTERN.match(cleaned))

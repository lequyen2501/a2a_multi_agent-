from __future__ import annotations

from typing import Any

import requests


class GemmaGradioError(RuntimeError):
    pass


class GemmaGradioAgent:
    def __init__(self, gradio_url: str):
        self.gradio_url = gradio_url.rstrip("/")
        self.model_name = "Gemma-4B (Gradio)"
        self.timeout = 30
        self._candidate_endpoints = [
            f"{self.gradio_url}/gradio_api/call/predict",
            f"{self.gradio_url}/call/predict",
            f"{self.gradio_url}/api/predict",
            f"{self.gradio_url}/api/predict/",
        ]
        self._poll_timeout = 60

    def _extract_text(self, payload: Any) -> str | None:
        if isinstance(payload, str):
            text = payload.strip()
            return text or None

        if isinstance(payload, list):
            for item in payload:
                text = self._extract_text(item)
                if text:
                    return text
            return None

        if isinstance(payload, dict):
            for key in ("text", "value", "label", "output", "response"):
                value = payload.get(key)
                text = self._extract_text(value)
                if text:
                    return text
            for value in payload.values():
                text = self._extract_text(value)
                if text:
                    return text

        return None

    def _extract_event_id(self, data: Any) -> str | None:
        if isinstance(data, dict):
            for key in ("event_id", "id"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _read_queued_result(self, url: str, event_id: str) -> str:
        result_url = f"{url.rstrip('/')}/{event_id}"
        response = requests.get(result_url, stream=True, timeout=self._poll_timeout)
        response.raise_for_status()

        for raw_line in response.iter_lines(decode_unicode=True):
            line = (raw_line or "").strip()
            if not line.startswith("data:"):
                continue

            payload = line[5:].strip()
            if not payload:
                continue

            if payload == "[DONE]":
                break

            try:
                json_payload = requests.models.complexjson.loads(payload)
            except Exception:
                text = self._extract_text(payload)
                if text and text != event_id:
                    return text
                continue

            text = self._extract_text(json_payload)
            if text and text != event_id:
                return text

        raise GemmaGradioError(f"No queued result returned from {result_url}")

    def _post_json(self, url: str, payload: dict[str, Any]) -> str:
        response = requests.post(url, json=payload, timeout=self.timeout)
        if response.status_code == 404:
            raise GemmaGradioError(f"Endpoint not found: {url}")
        response.raise_for_status()

        data = response.json()
        event_id = self._extract_event_id(data)
        if event_id:
            return self._read_queued_result(url, event_id)

        text = self._extract_text(data.get("data", data))
        if not text:
            raise GemmaGradioError(f"Unexpected Gradio response shape from {url}: {data}")
        return text

    def chat(self, prompt: str) -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            raise GemmaGradioError("Prompt is empty")

        errors: list[str] = []
        payloads = [
            {"data": [prompt, []]},
            {"data": [prompt]},
            {"input": prompt},
        ]

        for endpoint in self._candidate_endpoints:
            for payload in payloads:
                try:
                    return self._post_json(endpoint, payload)
                except Exception as exc:
                    errors.append(f"{endpoint} -> {exc}")

        raise GemmaGradioError(" ; ".join(errors))

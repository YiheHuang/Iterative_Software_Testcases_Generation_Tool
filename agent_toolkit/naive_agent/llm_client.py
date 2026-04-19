from __future__ import annotations

import json
import time
from urllib import error, request

from .models import LLMConfig


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._usage = {
            "request_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "usage_reporting_available": False,
        }

    def _record_usage(self, body: dict[str, object]) -> None:
        self._usage["request_count"] += 1
        usage = body.get("usage")
        if not isinstance(usage, dict):
            return
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")

        if isinstance(prompt_tokens, int):
            self._usage["prompt_tokens"] += prompt_tokens
        if isinstance(completion_tokens, int):
            self._usage["completion_tokens"] += completion_tokens
        if isinstance(total_tokens, int):
            self._usage["total_tokens"] += total_tokens

        self._usage["usage_reporting_available"] = True

    def usage_summary(self) -> dict[str, int | bool | str]:
        return {
            "request_count": int(self._usage["request_count"]),
            "prompt_tokens": int(self._usage["prompt_tokens"]),
            "completion_tokens": int(self._usage["completion_tokens"]),
            "total_tokens": int(self._usage["total_tokens"]),
            "usage_reporting_available": bool(self._usage["usage_reporting_available"]),
            "model": self.config.model,
            "api_url": self.config.api_url,
        }

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        req = request.Request(
            self.config.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                    body = json.loads(response.read().decode("utf-8"))
                self._record_usage(body)
                break
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"LLM request failed with HTTP {exc.code}: {detail}") from exc
            except error.URLError as exc:
                last_error = exc
                if attempt == 2:
                    raise RuntimeError(f"LLM request failed: {exc.reason}") from exc
                time.sleep(2 ** attempt)
        else:
            raise RuntimeError(f"LLM request failed: {last_error}")

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected LLM response shape: {body}") from exc

from __future__ import annotations

import json
import time
from urllib import error, request

from .models import LLMConfig


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

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

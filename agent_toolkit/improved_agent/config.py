from __future__ import annotations

import os
from pathlib import Path

from .models import LLMConfig, ProjectPaths


DEFAULT_API_URL = "https://yunwu.ai/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o"


def _load_dotenv_values(workspace_root: str | Path | None = None) -> dict[str, str]:
    root = Path(workspace_root or Path(__file__).resolve().parents[2]).resolve()
    dotenv_path = root / "agent_toolkit" / ".env"
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_paths(workspace_root: str | Path | None = None) -> ProjectPaths:
    root = Path(workspace_root or Path(__file__).resolve().parents[2]).resolve()
    validator_root = root / "source_code" / "validator_js"
    outputs_root = root / "agent_toolkit" / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    return ProjectPaths(
        workspace_root=root,
        validator_root=validator_root,
        outputs_root=outputs_root,
    )


def load_llm_config(
    api_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    timeout_seconds: int = 240,
    workspace_root: str | Path | None = None,
) -> LLMConfig:
    dotenv_values = _load_dotenv_values(workspace_root)
    resolved_api_url = (
        api_url
        or os.environ.get("AGENT_API_URL")
        or dotenv_values.get("AGENT_API_URL")
        or os.environ.get("EMAIL_AGENT_API_URL")
        or dotenv_values.get("EMAIL_AGENT_API_URL")
        or DEFAULT_API_URL
    )
    resolved_api_key = (
        api_key
        or os.environ.get("AGENT_API_KEY")
        or dotenv_values.get("AGENT_API_KEY")
        or os.environ.get("EMAIL_AGENT_API_KEY")
        or dotenv_values.get("EMAIL_AGENT_API_KEY")
        or ""
    )
    resolved_model = (
        model
        or os.environ.get("AGENT_MODEL")
        or dotenv_values.get("AGENT_MODEL")
        or os.environ.get("EMAIL_AGENT_MODEL")
        or dotenv_values.get("EMAIL_AGENT_MODEL")
        or DEFAULT_MODEL
    )
    if not resolved_api_key:
        raise ValueError(
            "Missing API key. Provide --api-key or configure AGENT_API_KEY in agent_toolkit/.env."
        )
    return LLMConfig(
        api_url=resolved_api_url,
        api_key=resolved_api_key,
        model=resolved_model,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
    )

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LLMConfig:
    api_url: str
    api_key: str
    model: str
    temperature: float = 0.2
    timeout_seconds: int = 240


@dataclass
class ProjectPaths:
    workspace_root: Path
    validator_root: Path
    outputs_root: Path


@dataclass
class TestGroup:
    validator: str
    args: list[dict[str, Any]] = field(default_factory=list)
    valid: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)
    title: str | None = None
    rationale: str | None = None
    obligations: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    validator_name: str
    mode: str
    approach: str
    raw_response: str
    obligations: list[dict[str, Any]] = field(default_factory=list)
    test_groups: list[TestGroup] = field(default_factory=list)
    prompt_path: Path | None = None
    response_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationCase:
    validator: str
    args: list[dict[str, Any]]
    input_value: Any
    expected_kind: str
    expected: bool | str
    title: str | None = None
    obligations: list[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    total_cases: int
    correct_cases: int
    incorrect_cases: int
    exact_match_rate: float
    summary: dict[str, Any]
    details: dict[str, Any] = field(default_factory=dict)
    output_json_path: Path | None = None
    coverage_dir: Path | None = None

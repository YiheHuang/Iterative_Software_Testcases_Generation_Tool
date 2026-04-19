from __future__ import annotations

import json
from typing import Any

from .io_utils import read_text, write_json, write_text
from .llm_client import LLMClient
from .models import GenerationResult, ProjectPaths, TestGroup
from .prompts import (
    SYSTEM_PROMPT,
    build_blackbox_prompt,
    build_whitebox_code_only_prompt,
    build_whitebox_prompt,
)
from .target_context import (
    resolve_requirement_spec,
    run_output_root,
    validator_source_path,
)


def sanitize_group(group: dict[str, Any], validator_name: str) -> TestGroup:
    args = group.get("args") or []
    if isinstance(args, dict):
        args = [args]
    return TestGroup(
        title=group.get("title"),
        validator=group.get("validator", validator_name),
        args=args,
        valid=[str(v) for v in group.get("valid", [])],
        invalid=[str(v) for v in group.get("invalid", [])],
        rationale=group.get("rationale"),
        obligations=[],
    )


def parse_response(content: str, validator_name: str) -> tuple[list[dict[str, Any]], list[TestGroup]]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(content[start : end + 1])
    obligations: list[dict[str, Any]] = []
    groups = [sanitize_group(group, validator_name) for group in payload.get("test_groups", [])]
    return obligations, groups


def build_repair_prompt(raw_response: str) -> str:
    return (
        "Repair the following invalid JSON into strict valid JSON.\n"
        "Keep the same schema with top-level keys obligations and test_groups.\n"
        "Remove duplicated keys, remove obviously repeated corrupted fragments, and preserve as much valid content as possible.\n"
        "Return JSON only.\n\n"
        f"{raw_response}"
    )


def build_group_completion_prompt(
    validator_name: str,
    mode: str,
    obligations: list[dict[str, Any]],
    original_prompt: str,
) -> str:
    return (
        f"The previous {mode} generation for {validator_name} produced no usable test_groups.\n"
        "Generate a small non-empty validator.js-style test suite now.\n"
        "Return strict JSON with top-level keys obligations and test_groups.\n"
        "Use an empty obligations list unless a single obvious rule is unavoidable.\n"
        "test_groups must be non-empty.\n"
        "Each group must contain validator, args, valid, invalid, title, rationale, obligations.\n"
        "Group obligations should usually be empty.\n\n"
        f"Original task:\n{original_prompt}\n\n"
        "Return a concise baseline answer."
    )


class NaiveAgentService:
    def __init__(self, paths: ProjectPaths, client: LLMClient) -> None:
        self.paths = paths
        self.client = client

    def generate(self, mode: str, validator_name: str, approach: str = "naive") -> GenerationResult:
        if mode not in {"blackbox", "whitebox", "whitebox_code_only"}:
            raise ValueError(f"Unsupported mode: {mode}")

        if mode == "blackbox":
            requirement_spec, requirement_source = resolve_requirement_spec(self.paths, validator_name)
            user_prompt = build_blackbox_prompt(validator_name, requirement_spec)
        elif mode == "whitebox":
            requirement_spec, requirement_source = resolve_requirement_spec(self.paths, validator_name)
            source_code = read_text(validator_source_path(self.paths, validator_name))
            user_prompt = build_whitebox_prompt(validator_name, requirement_spec, source_code)
        else:
            source_code = read_text(validator_source_path(self.paths, validator_name))
            requirement_source = "not_used_code_only_mode"
            user_prompt = build_whitebox_code_only_prompt(validator_name, source_code)

        run_root = run_output_root(self.paths, validator_name, approach, mode)
        prompt_path = run_root / "prompt.txt"
        response_path = run_root / "response.json"
        raw_response_path = run_root / "response_raw.txt"
        normalized_path = run_root / "normalized_generation.json"

        write_text(prompt_path, user_prompt)
        raw_response = self.client.chat(SYSTEM_PROMPT, user_prompt)
        write_text(raw_response_path, raw_response)
        try:
            obligations, groups = parse_response(raw_response, validator_name)
        except json.JSONDecodeError:
            repaired_response = self.client.chat(
                SYSTEM_PROMPT,
                build_repair_prompt(raw_response),
            )
            write_text(run_root / "response_repaired.json", repaired_response)
            obligations, groups = parse_response(repaired_response, validator_name)
            raw_response = repaired_response

        if not groups:
            completion_response = self.client.chat(
                SYSTEM_PROMPT,
                build_group_completion_prompt(validator_name, mode, obligations, user_prompt),
            )
            write_text(run_root / "response_completed.json", completion_response)
            try:
                completed_obligations, completed_groups = parse_response(completion_response, validator_name)
            except json.JSONDecodeError:
                repaired_completion = self.client.chat(
                    SYSTEM_PROMPT,
                    build_repair_prompt(completion_response),
                )
                write_text(run_root / "response_completed_repaired.json", repaired_completion)
                completed_obligations, completed_groups = parse_response(
                    repaired_completion, validator_name
                )
                completion_response = repaired_completion
            if completed_obligations:
                obligations = completed_obligations
            groups = completed_groups
            raw_response = completion_response

        if not groups:
            raise RuntimeError("Model response contained no usable test_groups after retry.")

        write_text(response_path, raw_response)
        write_json(
            normalized_path,
            {
                "mode": mode,
                "approach": approach,
                "obligations": obligations,
                "test_groups": groups,
                "metadata": {
                    "requirement_source": requirement_source,
                    "generation_style": "single_pass_with_repair",
                },
            },
        )

        return GenerationResult(
            validator_name=validator_name,
            mode=mode,
            approach=approach,
            raw_response=raw_response,
            obligations=obligations,
            test_groups=groups,
            prompt_path=prompt_path,
            response_path=response_path,
            metadata={
                "requirement_source": requirement_source,
                "generation_style": "single_pass_with_repair",
            },
        )

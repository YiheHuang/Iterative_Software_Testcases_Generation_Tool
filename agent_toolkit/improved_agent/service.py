from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .evaluation import EvaluationService, load_evaluation_payload
from .io_utils import read_text, write_json, write_text
from .llm_client import LLMClient
from .models import GenerationResult, ProjectPaths, TestGroup
from .prompts import (
    SYSTEM_PROMPT,
    build_group_completion_prompt,
    build_improvement_prompt,
    build_repair_prompt,
    build_whitebox_code_only_prompt,
)
from .target_context import resolve_requirement_spec, run_output_root, validator_source_path


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2)


def group_signature(group: TestGroup) -> str:
    return stable_json(
        {
            "title": group.title,
            "validator": group.validator,
            "args": group.args,
            "valid": group.valid,
            "invalid": group.invalid,
            "rationale": group.rationale,
            "obligations": group.obligations,
        }
    )


def merge_groups(base_groups: list[TestGroup], patch_groups: list[TestGroup]) -> list[TestGroup]:
    merged: list[TestGroup] = []
    seen: set[str] = set()
    for group in [*base_groups, *patch_groups]:
        signature = group_signature(group)
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(group)
    return merged


def merge_obligations(
    base_obligations: list[dict[str, Any]],
    patch_obligations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_signatures: set[str] = set()
    for obligation in [*base_obligations, *patch_obligations]:
        if not isinstance(obligation, dict):
            continue
        obligation_id = obligation.get("id")
        if isinstance(obligation_id, str) and obligation_id:
            if obligation_id in seen_ids:
                continue
            seen_ids.add(obligation_id)
            merged.append(obligation)
            continue

        signature = json.dumps(obligation, ensure_ascii=True, sort_keys=True)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        merged.append(obligation)
    return merged


def serialize_groups(groups: list[TestGroup]) -> list[dict[str, Any]]:
    return [
        {
            "title": group.title,
            "validator": group.validator,
            "args": group.args,
            "valid": group.valid,
            "invalid": group.invalid,
            "rationale": group.rationale,
            "obligations": group.obligations,
        }
        for group in groups
    ]


def coverage_score(details: dict[str, Any]) -> tuple[float, float, float, float]:
    coverage_total = details.get("coverage_total") or {}
    lines_pct = float((coverage_total.get("lines") or {}).get("pct", 0.0))
    statements_pct = float((coverage_total.get("statements") or {}).get("pct", 0.0))
    functions_pct = float((coverage_total.get("functions") or {}).get("pct", 0.0))
    branch_pct = float((coverage_total.get("branches") or {}).get("pct", 0.0))
    return (lines_pct, statements_pct, functions_pct, branch_pct)


def feedback_sources_for_mode(mode: str) -> list[str]:
    if mode in {"whitebox", "whitebox_code_only"}:
        return ["coverage"]
    return []


def is_full_coverage(score: tuple[float, float, float, float]) -> bool:
    return all(metric >= 100.0 for metric in score)


def better_or_equal_coverage(
    new_score: tuple[float, float, float, float],
    old_score: tuple[float, float, float, float],
) -> bool:
    return new_score >= old_score


def strictly_better_coverage(
    new_score: tuple[float, float, float, float],
    old_score: tuple[float, float, float, float],
) -> bool:
    return new_score > old_score


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
        obligations=[str(v) for v in group.get("obligations", [])],
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
    obligations = payload.get("obligations", [])
    groups = [sanitize_group(group, validator_name) for group in payload.get("test_groups", [])]
    return obligations, groups


def try_parse_patch_response(
    client: LLMClient,
    validator_name: str,
    mode: str,
    raw_content: str,
    run_root,
    attempt_index: int,
    improvement_prompt: str,
) -> tuple[list[dict[str, Any]], list[TestGroup], str]:
    patch_obligations: list[dict[str, Any]] = []
    patch_groups: list[TestGroup] = []
    patch_raw = raw_content
    try:
        patch_obligations, patch_groups = parse_response(patch_raw, validator_name)
        return patch_obligations, patch_groups, patch_raw
    except json.JSONDecodeError:
        pass

    repaired_patch = client.chat(
        SYSTEM_PROMPT,
        build_repair_prompt(patch_raw),
    )
    write_text(
        run_root / f"improvement_response_repaired_{attempt_index}.json",
        repaired_patch,
    )
    try:
        patch_obligations, patch_groups = parse_response(repaired_patch, validator_name)
        return patch_obligations, patch_groups, repaired_patch
    except json.JSONDecodeError:
        pass

    completion_patch = client.chat(
        SYSTEM_PROMPT,
        build_group_completion_prompt(validator_name, mode, patch_obligations, improvement_prompt),
    )
    write_text(
        run_root / f"improvement_response_completed_{attempt_index}.json",
        completion_patch,
    )
    patch_obligations, patch_groups = parse_response(completion_patch, validator_name)
    return patch_obligations, patch_groups, completion_patch


class ImprovedAgentService:
    def __init__(self, paths: ProjectPaths, client: LLMClient) -> None:
        self.paths = paths
        self.client = client
        self.evaluator = EvaluationService(paths)

    def _generate_initial(self, mode: str, validator_name: str, approach: str) -> GenerationResult:
        if mode == "blackbox":
            from .prompts import build_blackbox_prompt

            requirement_spec, requirement_source = resolve_requirement_spec(self.paths, validator_name)
            user_prompt = build_blackbox_prompt(validator_name, requirement_spec)
        elif mode == "whitebox":
            from .prompts import build_whitebox_prompt

            requirement_spec, requirement_source = resolve_requirement_spec(self.paths, validator_name)
            source_code = read_text(validator_source_path(self.paths, validator_name))
            user_prompt = build_whitebox_prompt(validator_name, requirement_spec, source_code)
        elif mode == "whitebox_code_only":
            requirement_source = "not_used_code_only_mode"
            source_code = read_text(validator_source_path(self.paths, validator_name))
            user_prompt = build_whitebox_code_only_prompt(validator_name, source_code)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

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
                completed_obligations, completed_groups = parse_response(
                    completion_response, validator_name
                )
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

        result = GenerationResult(
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
                "generation_style": "improved_initial_pass",
            },
        )
        write_text(response_path, raw_response)
        write_json(
            normalized_path,
            {
                "mode": mode,
                "approach": approach,
                "obligations": obligations,
                "test_groups": groups,
                "metadata": result.metadata,
            },
        )
        return result

    def generate(self, mode: str, validator_name: str, approach: str = "improved") -> GenerationResult:
        baseline_result = self._generate_initial(mode, validator_name, approach=approach)
        run_root = run_output_root(self.paths, validator_name, approach, mode)
        evaluation = self.evaluator.evaluate(baseline_result)
        evaluation_payload = {}
        if evaluation.output_json_path:
            evaluation_payload = load_evaluation_payload(evaluation.output_json_path)

        if mode == "blackbox":
            baseline_result.metadata.update(
                {
                    "iteration_count": 1,
                    "improvement_applied": False,
                    "feedback_sources": ["runtime_correctness"],
                    "decision": "keep_initial_blackbox_no_patch",
                }
            )
            write_json(
                run_output_root(self.paths, validator_name, approach, mode) / "agent_iterations.json",
                {
                    "iteration_count": 1,
                    "feedback_sources": ["runtime_correctness"],
                    "golden_feedback_used": False,
                    "decision": "keep_initial_blackbox_no_patch",
                    "initial_summary": evaluation.summary,
                },
            )
            return baseline_result

        requirement_spec: str | None = None
        if mode == "whitebox":
            requirement_spec, _requirement_source = resolve_requirement_spec(self.paths, validator_name)

        current_result = baseline_result
        current_evaluation = evaluation
        current_payload = evaluation_payload
        current_score = coverage_score(current_evaluation.details)
        revert_count = 0
        accepted_iterations = 1
        total_attempts = 0
        max_attempts = 6
        iteration_log: list[dict[str, Any]] = [
            {
                "iteration": 1,
                "decision": "initial",
                "coverage_score": {
                    "lines": current_score[0],
                    "statements": current_score[1],
                    "functions": current_score[2],
                    "branches": current_score[3],
                },
            }
        ]

        while not is_full_coverage(current_score) and revert_count < 3 and total_attempts < max_attempts:
            total_attempts += 1
            attempt_index = total_attempts
            generated_groups = serialize_groups(current_result.test_groups)
            coverage_details = current_payload.get("details", {})
            compact_feedback = {
                "coverage_total": coverage_details.get("coverage_total", {}),
                "coverage_files": coverage_details.get("coverage_files", {}),
                "uncovered_details": coverage_details.get("uncovered_details", {}),
            }
            improvement_prompt = build_improvement_prompt(
                validator_name,
                mode,
                requirement_spec,
                generated_groups,
                compact_feedback,
            )
            write_text(run_root / f"improvement_prompt_{attempt_index}.txt", improvement_prompt)
            patch_raw = self.client.chat(SYSTEM_PROMPT, improvement_prompt)
            write_text(
                run_root / f"improvement_response_raw_{attempt_index}.txt",
                patch_raw,
            )
            try:
                patch_obligations, patch_groups, patch_raw = try_parse_patch_response(
                    self.client,
                    validator_name,
                    mode,
                    patch_raw,
                    run_root,
                    attempt_index,
                    improvement_prompt,
                )
            except json.JSONDecodeError:
                revert_count += 1
                iteration_log.append(
                    {
                        "iteration": attempt_index + 1,
                        "decision": "revert_patch_parse_failure",
                    }
                )
                continue

            candidate_groups = merge_groups(current_result.test_groups, patch_groups)
            candidate_obligations = merge_obligations(
                current_result.obligations,
                patch_obligations,
            )

            candidate_result = GenerationResult(
                validator_name=validator_name,
                mode=mode,
                approach=approach,
                raw_response=patch_raw,
                obligations=candidate_obligations,
                test_groups=candidate_groups,
                prompt_path=run_root / "prompt.txt",
                response_path=run_root / "response.json",
                metadata=deepcopy(current_result.metadata),
            )
            candidate_evaluation = self.evaluator.evaluate(candidate_result)
            candidate_payload = {}
            if candidate_evaluation.output_json_path:
                candidate_payload = load_evaluation_payload(candidate_evaluation.output_json_path)
            candidate_score = coverage_score(candidate_evaluation.details)

            if strictly_better_coverage(candidate_score, current_score):
                current_result = candidate_result
                current_evaluation = candidate_evaluation
                current_payload = candidate_payload
                current_score = candidate_score
                accepted_iterations += 1
                iteration_log.append(
                    {
                        "iteration": attempt_index + 1,
                        "decision": "accept_patch",
                        "candidate_group_count": len(candidate_groups),
                        "coverage_score": {
                            "lines": current_score[0],
                            "statements": current_score[1],
                            "functions": current_score[2],
                            "branches": current_score[3],
                        },
                    }
                )
            else:
                revert_count += 1
                iteration_log.append(
                    {
                        "iteration": attempt_index + 1,
                        "decision": "revert_patch",
                        "candidate_group_count": len(candidate_groups),
                        "candidate_coverage_score": {
                            "lines": candidate_score[0],
                            "statements": candidate_score[1],
                            "functions": candidate_score[2],
                            "branches": candidate_score[3],
                        },
                        "current_coverage_score": {
                            "lines": current_score[0],
                            "statements": current_score[1],
                            "functions": current_score[2],
                            "branches": current_score[3],
                        },
                    }
                )

        current_result.metadata.update(
            {
                "iteration_count": accepted_iterations,
                "improvement_applied": accepted_iterations > 1,
                "feedback_sources": feedback_sources_for_mode(mode),
                "decision": "stop_full_coverage" if is_full_coverage(current_score) else "stop_after_reverts",
            }
        )
        write_json(
            run_root / "normalized_generation.json",
            {
                "mode": mode,
                "approach": approach,
                "obligations": current_result.obligations,
                "test_groups": current_result.test_groups,
                "metadata": current_result.metadata,
            },
        )
        write_json(
            run_root / "agent_iterations.json",
            {
                "iteration_count": accepted_iterations,
                "revert_count": revert_count,
                "total_attempts": total_attempts,
                "max_attempts": max_attempts,
                "feedback_sources": feedback_sources_for_mode(mode),
                "golden_feedback_used": False,
                "final_decision": (
                    current_result.metadata["decision"]
                    if is_full_coverage(current_score)
                    else (
                        "stop_after_reverts"
                        if revert_count >= 3
                        else "stop_after_attempt_limit"
                    )
                ),
                "coverage_score": {
                    "lines": current_score[0],
                    "statements": current_score[1],
                    "functions": current_score[2],
                    "branches": current_score[3],
                },
                "iterations": iteration_log,
            },
        )
        return current_result

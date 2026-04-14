from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .io_utils import write_json
from .models import EvaluationCase, EvaluationResult, GenerationResult, ProjectPaths, TestGroup
from .target_context import run_output_root


def target_source_files(groups: list[TestGroup]) -> list[str]:
    validators = sorted({group.validator for group in groups if group.validator})
    return [f"src/lib/{validator}.js" for validator in validators]


def flatten_groups(groups: list[TestGroup]) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for group in groups:
        for value in group.valid:
            cases.append(
                EvaluationCase(
                    validator=group.validator,
                    args=group.args,
                    input_value=value,
                    expected_kind="return",
                    expected=True,
                    title=group.title,
                    obligations=group.obligations,
                )
            )
        for value in group.invalid:
            cases.append(
                EvaluationCase(
                    validator=group.validator,
                    args=group.args,
                    input_value=value,
                    expected_kind="return",
                    expected=False,
                    title=group.title,
                    obligations=group.obligations,
                )
            )
        for value in group.error:
            cases.append(
                EvaluationCase(
                    validator=group.validator,
                    args=group.args,
                    input_value=value,
                    expected_kind="throw",
                    expected="TypeError",
                    title=group.title,
                    obligations=group.obligations,
                )
            )
    return cases


def _load_source_lines(file_path: str) -> list[str]:
    path = Path(file_path)
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _line_text(source_lines: list[str], line_number: int | None) -> str | None:
    if line_number is None or line_number < 1 or line_number > len(source_lines):
        return None
    return source_lines[line_number - 1].rstrip()


def _excerpt_from_location(source_lines: list[str], location: dict[str, Any]) -> str | None:
    start = location.get("start", {})
    end = location.get("end", {})
    start_line = start.get("line")
    end_line = end.get("line") or start_line
    start_col = start.get("column")
    end_col = end.get("column")
    if start_line is None or end_line is None:
        return None
    if start_line < 1 or end_line > len(source_lines):
        return None

    excerpt_lines = source_lines[start_line - 1 : end_line]
    if not excerpt_lines:
        return None
    if len(excerpt_lines) == 1 and start_col is not None and end_col is not None:
        snippet = excerpt_lines[0][start_col:end_col].strip()
        if snippet:
            return snippet
    return "\n".join(line.rstrip() for line in excerpt_lines).strip() or None


def _condition_excerpt(line_text: str | None) -> str | None:
    if not line_text:
        return None
    stripped = line_text.strip()
    if stripped.startswith("if ") or stripped.startswith("if(") or stripped.startswith("if ("):
        open_idx = stripped.find("(")
        close_idx = stripped.rfind(")")
        if open_idx != -1 and close_idx != -1 and close_idx > open_idx:
            return stripped[open_idx + 1 : close_idx].strip() or None
    return None


def _branch_side_summary(branch_type: str | None, path_index: int, source_excerpt: str | None) -> str:
    if branch_type == "if":
        return "condition_true_branch" if path_index == 0 else "condition_false_branch"
    if branch_type == "cond-expr":
        return "ternary_true_branch" if path_index == 0 else "ternary_false_branch"
    if branch_type == "binary-expr":
        excerpt = source_excerpt or ""
        if "&&" in excerpt:
            return "binary_short_circuit_or_rhs" if path_index == 0 else "binary_rhs_path"
        if "||" in excerpt:
            return "binary_short_circuit_or_rhs" if path_index == 0 else "binary_rhs_path"
    return f"path_{path_index}"


def _describe_statement(statement_id: str, location: dict[str, Any], source_lines: list[str]) -> dict[str, Any]:
    line_number = location.get("start", {}).get("line")
    line_text = _line_text(source_lines, line_number)
    source_excerpt = _excerpt_from_location(source_lines, location)
    return {
        "statement_id": statement_id,
        "line": line_number,
        "column": location.get("start", {}).get("column"),
        "line_text": line_text,
        "source_excerpt": source_excerpt,
        "summary": f"Uncovered statement at line {line_number}: {source_excerpt or line_text or 'unknown snippet'}",
    }


def _describe_branch(
    branch_id: str,
    branch_info: dict[str, Any],
    path_index: int,
    location: dict[str, Any],
    source_lines: list[str],
) -> dict[str, Any]:
    line_number = location.get("start", {}).get("line")
    line_text = _line_text(source_lines, line_number)
    source_excerpt = _excerpt_from_location(source_lines, location)
    condition_excerpt = _condition_excerpt(line_text)
    branch_type = branch_info.get("type")
    branch_side = _branch_side_summary(branch_type, path_index, source_excerpt)
    summary_parts = [f"Uncovered {branch_type or 'branch'} path `{branch_side}` at line {line_number}"]
    if condition_excerpt:
        summary_parts.append(f"condition: {condition_excerpt}")
    elif source_excerpt:
        summary_parts.append(f"snippet: {source_excerpt}")
    return {
        "branch_id": branch_id,
        "branch_type": branch_type,
        "path_index": path_index,
        "branch_side": branch_side,
        "line": line_number,
        "column": location.get("start", {}).get("column"),
        "line_text": line_text,
        "source_excerpt": source_excerpt,
        "condition_excerpt": condition_excerpt,
        "summary": "; ".join(summary_parts),
    }


def _describe_function(fn_id: str, fn_info: dict[str, Any], source_lines: list[str]) -> dict[str, Any]:
    declaration = fn_info.get("decl", {})
    line_number = declaration.get("start", {}).get("line")
    line_text = _line_text(source_lines, line_number)
    source_excerpt = _excerpt_from_location(source_lines, declaration)
    function_name = fn_info.get("name")
    return {
        "function_id": fn_id,
        "name": function_name,
        "line": line_number,
        "column": declaration.get("start", {}).get("column"),
        "line_text": line_text,
        "source_excerpt": source_excerpt,
        "summary": f"Uncovered function `{function_name}` declared at line {line_number}",
    }


def _extract_uncovered_details(coverage_final_path: Path) -> dict[str, Any]:
    if not coverage_final_path.exists():
        return {}

    payload = json.loads(coverage_final_path.read_text(encoding="utf-8"))
    result: dict[str, Any] = {}
    for file_path, file_payload in payload.items():
        source_lines = _load_source_lines(file_path)
        statement_map = file_payload.get("statementMap", {})
        statement_hits = file_payload.get("s", {})
        branch_map = file_payload.get("branchMap", {})
        branch_hits = file_payload.get("b", {})
        fn_map = file_payload.get("fnMap", {})
        fn_hits = file_payload.get("f", {})

        uncovered_statements = []
        for statement_id, location in statement_map.items():
            if statement_hits.get(statement_id, 0) == 0:
                uncovered_statements.append(_describe_statement(statement_id, location, source_lines))

        uncovered_branches = []
        for branch_id, branch_info in branch_map.items():
            hits = branch_hits.get(branch_id, [])
            locations = branch_info.get("locations", [])
            for idx, hit_count in enumerate(hits):
                if hit_count == 0:
                    location = locations[idx] if idx < len(locations) else {}
                    uncovered_branches.append(
                        _describe_branch(branch_id, branch_info, idx, location, source_lines)
                    )

        uncovered_functions = []
        for fn_id, fn_info in fn_map.items():
            if fn_hits.get(fn_id, 0) == 0:
                uncovered_functions.append(_describe_function(fn_id, fn_info, source_lines))

        result[file_path] = {
            "uncovered_statements": uncovered_statements,
            "uncovered_branches": uncovered_branches,
            "uncovered_functions": uncovered_functions,
        }
    return result


class EvaluationService:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths

    def evaluate(self, generation: GenerationResult) -> EvaluationResult:
        run_root = run_output_root(
            self.paths,
            generation.validator_name,
            generation.approach,
            generation.mode,
        )
        input_json_path = run_root / "evaluation_input.json"
        output_json_path = run_root / "evaluation_output.json"
        coverage_dir = run_root / "coverage"
        coverage_dir.mkdir(parents=True, exist_ok=True)

        cases = flatten_groups(generation.test_groups)
        write_json(
            input_json_path,
            {
                "cases": cases,
                "mode": generation.mode,
                "approach": generation.approach,
                "target_source_files": target_source_files(generation.test_groups),
            },
        )

        script_path = self.paths.workspace_root / "agent_toolkit" / "run_validator_eval.js"
        npx_executable = shutil.which("npx.cmd") or shutil.which("npx")
        if not npx_executable:
            raise RuntimeError("Could not find npx or npx.cmd in PATH.")
        command = [
            npx_executable,
            "nyc",
            "--reporter=json",
            "--reporter=json-summary",
            "--reporter=text-summary",
            "--report-dir",
            str(coverage_dir),
        ]
        for source_file in target_source_files(generation.test_groups):
            command.extend(["--include", source_file])
        command.extend([
            "node",
            str(script_path),
            str(input_json_path),
            str(output_json_path),
        ])
        completed = subprocess.run(
            command,
            cwd=self.paths.validator_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Validator evaluation failed.\n"
                f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}"
            )

        payload: dict[str, Any] = json.loads(output_json_path.read_text(encoding="utf-8"))
        total_cases = int(payload["summary"]["total_cases"])
        correct_cases = int(payload["summary"]["correct_cases"])
        incorrect_cases = int(payload["summary"]["incorrect_cases"])
        exact_match_rate = float(payload["summary"]["exact_match_rate"])
        details = payload.get("details", {})
        coverage_summary_path = coverage_dir / "coverage-summary.json"
        coverage_final_path = coverage_dir / "coverage-final.json"
        coverage_payload = {}
        if coverage_summary_path.exists():
            coverage_payload = json.loads(coverage_summary_path.read_text(encoding="utf-8"))
        uncovered_details = _extract_uncovered_details(coverage_final_path)

        write_json(run_root / "failed_cases.json", details.get("failed_results", []))
        write_json(run_root / "passed_cases.json", details.get("passed_results", []))
        write_json(
            run_root / "coverage_details.json",
            {
                "coverage_total": coverage_payload.get("total"),
                "coverage_files": {
                    key: value for key, value in coverage_payload.items() if key != "total"
                },
                "uncovered_details": uncovered_details,
                "coverage_summary_path": str(coverage_summary_path) if coverage_summary_path.exists() else None,
                "coverage_final_path": str(coverage_final_path) if coverage_final_path.exists() else None,
            },
        )
        details["coverage_total"] = coverage_payload.get("total")
        details["coverage_files"] = {
            key: value for key, value in coverage_payload.items() if key != "total"
        }
        details["uncovered_details"] = uncovered_details

        return EvaluationResult(
            total_cases=total_cases,
            correct_cases=correct_cases,
            incorrect_cases=incorrect_cases,
            exact_match_rate=exact_match_rate,
            summary=payload["summary"],
            details=details,
            output_json_path=output_json_path,
            coverage_dir=coverage_dir,
        )


def load_evaluation_payload(output_json_path: Path) -> dict[str, Any]:
    return json.loads(output_json_path.read_text(encoding="utf-8"))

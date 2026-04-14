from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import write_json, write_text
from .llm_client import LLMClient
from .models import GenerationResult, ProjectPaths
from .target_context import golden_output_root, run_output_root


GOLDEN_CATEGORY_SYSTEM_PROMPT = """
You are an expert software test taxonomy analyst.
Partition fixed golden test groups into stable semantic golden categories.

Return JSON only with this schema:
{
  "golden_categories": [
    {
      "name": "string",
      "description": "string",
      "golden_group_ids": ["GOLDEN-1", "GOLDEN-2"]
    }
  ]
}

Rules:
- Every golden_group_id must appear exactly once across all categories.
- Do not drop, duplicate, merge away, or invent golden_group_ids.
- Prefer stable behavior families, option families, or coherent validation themes.
- Keep categories semantically meaningful and not overly granular.
""".strip()


GENERATED_CATEGORY_SYSTEM_PROMPT = """
You are an expert software test taxonomy analyst.
Group generated test groups into generated categories.

Return JSON only with this schema:
{
  "generated_categories": [
    {
      "name": "string",
      "description": "string",
      "generated_group_ids": ["GENERATED-1", "GENERATED-2"]
    }
  ]
}

Rules:
- Every generated_group_id must appear exactly once across all categories.
- Do not drop, duplicate, split, or invent generated_group_ids.
- Merge groups that target the same underlying behavior family or option family.
- Keep distinct groups separate when they cover materially different behaviors or paths.
""".strip()


BIDIRECTIONAL_MATCH_SYSTEM_PROMPT = """
You are an expert software test analyst.
Compare fixed golden categories against generated categories using bidirectional semantic matching.

Return JSON only with this schema:
{
  "golden_to_generated": [
    {
      "golden_category_id": "GC-1",
      "matched_generated_category_ids": ["GENC-1"],
      "match_type": "strong|partial|none",
      "reason": "string"
    }
  ],
  "generated_to_golden": [
    {
      "generated_category_id": "GENC-1",
      "matched_golden_category_ids": ["GC-1"],
      "match_type": "strong|partial|none",
      "reason": "string"
    }
  ],
  "novel_generated_categories": [
    {
      "generated_category_id": "GENC-9",
      "reason": "string"
    }
  ]
}

Rules:
- Include one row for every golden category in golden_to_generated.
- Include one row for every generated category in generated_to_golden.
- A golden category may be matched by multiple generated categories if fragmented generated evidence jointly covers it.
- A generated category may map to multiple golden categories if it spans multiple fixed golden behaviors.
- Use match_type none when there is no meaningful semantic match.
- Only mark a generated category as novel when it does not meaningfully map to any golden category.
- Do not invent ids that are not present in the prompt.
""".strip()


def _stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2)


def _parse_json_payload(raw_response: str) -> dict[str, Any]:
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(raw_response[start : end + 1])


def _extract_numeric_suffix(identifier: str) -> int:
    try:
        return int(identifier.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 10**9


@dataclass
class GoldenSuite:
    test_groups: list[dict[str, Any]]
    path: Path


class GoldenTestService:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths

    def extract_suite(self, validator_name: str) -> GoldenSuite:
        output_path = golden_output_root(self.paths, validator_name) / f"{validator_name}_golden_tests.json"
        if output_path.exists():
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            return GoldenSuite(test_groups=payload["test_groups"], path=output_path)
        script_path = self.paths.workspace_root / "agent_toolkit" / "extract_golden_tests.js"
        validators_test_path = self.paths.validator_root / "test" / "validators.test.js"
        command = [
            "node",
            str(script_path),
            str(validators_test_path),
            validator_name,
            str(output_path),
        ]
        completed = subprocess.run(
            command,
            cwd=self.paths.workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Golden test extraction failed.\n"
                f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}"
            )
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        return GoldenSuite(test_groups=payload["test_groups"], path=output_path)


def _index_groups(prefix: str, groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed: list[dict[str, Any]] = []
    for idx, group in enumerate(groups, start=1):
        item = dict(group)
        item[f"{prefix}_id"] = f"{prefix.upper()}-{idx}"
        indexed.append(item)
    return indexed


def _normalize_categories(
    raw_categories: list[dict[str, Any]] | None,
    indexed_groups: list[dict[str, Any]],
    *,
    item_id_key: str,
    category_id_key: str,
    group_ids_key: str,
    category_prefix: str,
) -> list[dict[str, Any]]:
    groups_by_id = {group[item_id_key]: group for group in indexed_groups}
    claimed_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for raw_category in raw_categories or []:
        raw_group_ids = raw_category.get(group_ids_key, [])
        if not isinstance(raw_group_ids, list):
            continue
        category_group_ids: list[str] = []
        for item_id in raw_group_ids:
            if item_id in groups_by_id and item_id not in claimed_ids:
                claimed_ids.add(item_id)
                category_group_ids.append(item_id)
        if not category_group_ids:
            continue
        first_group = groups_by_id[category_group_ids[0]]
        normalized.append(
            {
                "name": str(raw_category.get("name") or first_group.get("title") or "unnamed_category"),
                "description": str(raw_category.get("description") or ""),
                group_ids_key: category_group_ids,
            }
        )

    for group in indexed_groups:
        if group[item_id_key] in claimed_ids:
            continue
        normalized.append(
            {
                "name": str(group.get("title") or group[item_id_key]),
                "description": "fallback_singleton_category",
                group_ids_key: [group[item_id_key]],
            }
        )

    normalized.sort(key=lambda category: min(_extract_numeric_suffix(item_id) for item_id in category[group_ids_key]))
    result: list[dict[str, Any]] = []
    for idx, category in enumerate(normalized, start=1):
        result.append(
            {
                category_id_key: f"{category_prefix}-{idx}",
                "name": category["name"],
                "description": category["description"],
                group_ids_key: category[group_ids_key],
            }
        )
    return result


def _normalize_direction_rows(
    raw_rows: list[dict[str, Any]] | None,
    *,
    source_categories: list[dict[str, Any]],
    source_id_key: str,
    target_categories: list[dict[str, Any]],
    target_id_key: str,
    matched_ids_key: str,
) -> list[dict[str, Any]]:
    source_ids = [category[source_id_key] for category in source_categories]
    valid_target_ids = {category[target_id_key] for category in target_categories}
    rows_by_id: dict[str, dict[str, Any]] = {}

    for raw_row in raw_rows or []:
        source_id = raw_row.get(source_id_key)
        if source_id not in source_ids or source_id in rows_by_id:
            continue
        raw_matched_ids = raw_row.get(matched_ids_key, [])
        if not isinstance(raw_matched_ids, list):
            raw_matched_ids = []
        matched_ids: list[str] = []
        seen: set[str] = set()
        for matched_id in raw_matched_ids:
            if matched_id in valid_target_ids and matched_id not in seen:
                seen.add(matched_id)
                matched_ids.append(matched_id)
        match_type = raw_row.get("match_type")
        if match_type not in {"strong", "partial"} or not matched_ids:
            match_type = "none"
            matched_ids = []
        rows_by_id[source_id] = {
            source_id_key: source_id,
            matched_ids_key: matched_ids,
            "match_type": match_type,
            "reason": str(raw_row.get("reason") or ""),
        }

    normalized_rows: list[dict[str, Any]] = []
    for source_id in source_ids:
        normalized_rows.append(
            rows_by_id.get(
                source_id,
                {
                    source_id_key: source_id,
                    matched_ids_key: [],
                    "match_type": "none",
                    "reason": "",
                },
            )
        )
    return normalized_rows


def _normalize_novel_rows(
    raw_rows: list[dict[str, Any]] | None,
    generated_to_golden: list[dict[str, Any]],
    generated_categories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    allowed_generated_ids = {
        row["generated_category_id"]
        for row in generated_to_golden
        if row["match_type"] == "none"
    }
    generated_by_id = {category["generated_category_id"]: category for category in generated_categories}
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_row in raw_rows or []:
        generated_id = raw_row.get("generated_category_id")
        if generated_id not in allowed_generated_ids or generated_id in seen:
            continue
        seen.add(generated_id)
        normalized.append(
            {
                "generated_category_id": generated_id,
                "generated_category_name": generated_by_id[generated_id]["name"],
                "reason": str(raw_row.get("reason") or ""),
            }
        )
    return normalized


def _build_summary(
    golden_categories: list[dict[str, Any]],
    generated_categories: list[dict[str, Any]],
    golden_to_generated: list[dict[str, Any]],
    generated_to_golden: list[dict[str, Any]],
    novel_generated_categories: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    matched_golden_category_ids = {
        row["golden_category_id"]
        for row in golden_to_generated
        if row["match_type"] in {"strong", "partial"} and row["matched_generated_category_ids"]
    }
    matched_generated_category_ids = {
        row["generated_category_id"]
        for row in generated_to_golden
        if row["match_type"] in {"strong", "partial"} and row["matched_golden_category_ids"]
    }
    missing_golden_categories = [
        {
            "golden_category_id": category["golden_category_id"],
            "golden_category_name": category["name"],
            "reason": "No generated categories achieved strong or partial semantic overlap with this fixed golden category.",
        }
        for category in golden_categories
        if category["golden_category_id"] not in matched_golden_category_ids
    ]
    strong_matches = sum(1 for row in golden_to_generated if row["match_type"] == "strong")
    partial_matches = sum(1 for row in golden_to_generated if row["match_type"] == "partial")
    fragmented_matches = sum(
        1
        for row in golden_to_generated
        if row["match_type"] in {"strong", "partial"} and len(row["matched_generated_category_ids"]) > 1
    )
    summary = {
        "total_golden_categories": len(golden_categories),
        "total_generated_categories": len(generated_categories),
        "overlap_golden_categories": len(matched_golden_category_ids),
        "missing_golden_categories": len(missing_golden_categories),
        "matched_generated_categories": len(matched_generated_category_ids),
        "novel_generated_categories": len(novel_generated_categories),
        "strong_golden_category_matches": strong_matches,
        "partial_golden_category_matches": partial_matches,
        "fragmented_golden_matches": fragmented_matches,
        "matched_golden_ratio": (
            len(matched_golden_category_ids) / len(golden_categories) if golden_categories else 0.0
        ),
        # Backward-compatible aliases used by existing summaries and tables.
        "total_golden_groups": len(golden_categories),
        "total_generated_groups": len(generated_categories),
        "overlap_golden_groups": len(matched_golden_category_ids),
        "missing_golden_groups": len(missing_golden_categories),
        "novel_valid_groups": len(novel_generated_categories),
        "exact_or_near_overlap_groups": len(matched_golden_category_ids),
        "golden_groups_with_semantic_match": len(matched_golden_category_ids),
        "generated_groups_with_semantic_match": len(matched_generated_category_ids),
        "novel_valid_categories": len(novel_generated_categories),
    }
    return summary, missing_golden_categories


@dataclass
class GoldenCategoryBundle:
    categories: list[dict[str, Any]]
    path: Path


class GoldenCategoryService:
    def __init__(self, paths: ProjectPaths, client: LLMClient) -> None:
        self.paths = paths
        self.client = client

    def load_or_create(self, validator_name: str, indexed_golden_groups: list[dict[str, Any]]) -> GoldenCategoryBundle:
        output_path = golden_output_root(self.paths, validator_name) / f"{validator_name}_golden_categories.json"
        if output_path.exists():
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            categories = _normalize_categories(
                payload.get("golden_categories", []),
                indexed_golden_groups,
                item_id_key="golden_id",
                category_id_key="golden_category_id",
                group_ids_key="golden_group_ids",
                category_prefix="GC",
            )
            write_json(output_path, {"validator_name": validator_name, "golden_categories": categories})
            return GoldenCategoryBundle(categories=categories, path=output_path)

        prompt = (
            f"Create stable golden categories for validator {validator_name}.\n\n"
            "Fixed golden groups:\n"
            f"{_stable_json(indexed_golden_groups)}\n"
        )
        root = golden_output_root(self.paths, validator_name)
        write_text(root / "golden_categories_prompt.txt", prompt)
        raw_response = self.client.chat(GOLDEN_CATEGORY_SYSTEM_PROMPT, prompt)
        write_text(root / "golden_categories_raw.txt", raw_response)
        payload = _parse_json_payload(raw_response)
        categories = _normalize_categories(
            payload.get("golden_categories", []),
            indexed_golden_groups,
            item_id_key="golden_id",
            category_id_key="golden_category_id",
            group_ids_key="golden_group_ids",
            category_prefix="GC",
        )
        write_json(output_path, {"validator_name": validator_name, "golden_categories": categories})
        return GoldenCategoryBundle(categories=categories, path=output_path)


def _build_generated_categories(
    client: LLMClient,
    run_root: Path,
    validator_name: str,
    indexed_generated_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prompt = (
        f"Group generated tests into generated categories for validator {validator_name}.\n\n"
        "Generated groups:\n"
        f"{_stable_json(indexed_generated_groups)}\n"
    )
    write_text(run_root / "generated_categories_prompt.txt", prompt)
    raw_response = client.chat(GENERATED_CATEGORY_SYSTEM_PROMPT, prompt)
    write_text(run_root / "generated_categories_raw.txt", raw_response)
    payload = _parse_json_payload(raw_response)
    categories = _normalize_categories(
        payload.get("generated_categories", []),
        indexed_generated_groups,
        item_id_key="generated_id",
        category_id_key="generated_category_id",
        group_ids_key="generated_group_ids",
        category_prefix="GENC",
    )
    write_json(run_root / "generated_categories.json", {"generated_categories": categories})
    return categories


class GoldenAnalysisService:
    def __init__(self, paths: ProjectPaths, client: LLMClient) -> None:
        self.paths = paths
        self.client = client
        self.golden_service = GoldenTestService(paths)
        self.golden_category_service = GoldenCategoryService(paths, client)

    def analyze(self, generation: GenerationResult, evaluation_payload: dict[str, Any] | None) -> dict[str, Any]:
        golden_suite = self.golden_service.extract_suite(generation.validator_name)
        run_root = run_output_root(
            self.paths,
            generation.validator_name,
            generation.approach,
            generation.mode,
        )
        generated_groups = [
            {
                "title": group.title,
                "validator": group.validator,
                "args": group.args,
                "valid": group.valid,
                "invalid": group.invalid,
                "error": group.error,
                "rationale": group.rationale,
                "obligations": group.obligations,
            }
            for group in generation.test_groups
        ]
        indexed_golden_groups = _index_groups("golden", golden_suite.test_groups)
        indexed_generated_groups = _index_groups("generated", generated_groups)
        golden_category_bundle = self.golden_category_service.load_or_create(
            generation.validator_name,
            indexed_golden_groups,
        )
        generated_categories = _build_generated_categories(
            self.client,
            run_root,
            generation.validator_name,
            indexed_generated_groups,
        )
        compact_evaluation = {
            "summary": (evaluation_payload or {}).get("summary", {}),
            "details": {
                "failed_results": (evaluation_payload or {}).get("details", {}).get("failed_results", []),
                "coverage_total": (evaluation_payload or {}).get("details", {}).get("coverage_total"),
                "coverage_files": (evaluation_payload or {}).get("details", {}).get("coverage_files", {}),
            },
        }
        analysis_prompt = (
            f"Perform bidirectional category matching for {generation.validator_name}.\n\n"
            "Fixed golden categories:\n"
            f"{_stable_json(golden_category_bundle.categories)}\n\n"
            "Indexed golden groups:\n"
            f"{_stable_json(indexed_golden_groups)}\n\n"
            "Generated categories:\n"
            f"{_stable_json(generated_categories)}\n\n"
            "Indexed generated groups:\n"
            f"{_stable_json(indexed_generated_groups)}\n\n"
            "Runtime evaluation details:\n"
            f"{_stable_json(compact_evaluation)}\n"
        )
        prompt_path = run_root / "golden_comparison_prompt.txt"
        response_raw_path = run_root / "golden_comparison_raw.txt"
        response_json_path = run_root / "golden_comparison.json"
        write_text(prompt_path, analysis_prompt)
        raw_response = self.client.chat(BIDIRECTIONAL_MATCH_SYSTEM_PROMPT, analysis_prompt)
        write_text(response_raw_path, raw_response)
        payload = _parse_json_payload(raw_response)

        golden_to_generated = _normalize_direction_rows(
            payload.get("golden_to_generated", []),
            source_categories=golden_category_bundle.categories,
            source_id_key="golden_category_id",
            target_categories=generated_categories,
            target_id_key="generated_category_id",
            matched_ids_key="matched_generated_category_ids",
        )
        generated_to_golden = _normalize_direction_rows(
            payload.get("generated_to_golden", []),
            source_categories=generated_categories,
            source_id_key="generated_category_id",
            target_categories=golden_category_bundle.categories,
            target_id_key="golden_category_id",
            matched_ids_key="matched_golden_category_ids",
        )
        novel_generated_categories = _normalize_novel_rows(
            payload.get("novel_generated_categories", []),
            generated_to_golden,
            generated_categories,
        )
        summary, missing_golden_categories = _build_summary(
            golden_category_bundle.categories,
            generated_categories,
            golden_to_generated,
            generated_to_golden,
            novel_generated_categories,
        )

        final_payload = {
            "golden_categories": golden_category_bundle.categories,
            "generated_categories": generated_categories,
            "golden_to_generated": golden_to_generated,
            "generated_to_golden": generated_to_golden,
            "novel_generated_categories": novel_generated_categories,
            "missing_golden_categories": missing_golden_categories,
            "summary": summary,
            "golden_source_path": str(golden_suite.path),
            "golden_categories_path": str(golden_category_bundle.path),
            "generated_categories_path": str(run_root / "generated_categories.json"),
        }
        write_json(response_json_path, final_payload)
        return final_payload

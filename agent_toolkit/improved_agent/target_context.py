from __future__ import annotations

import re
from pathlib import Path

from .io_utils import read_text
from .models import ProjectPaths


def run_output_root(paths: ProjectPaths, validator_name: str, approach: str, mode: str) -> Path:
    root = paths.outputs_root / approach / validator_name / mode
    root.mkdir(parents=True, exist_ok=True)
    return root


def golden_output_root(paths: ProjectPaths, validator_name: str) -> Path:
    root = paths.outputs_root / "golden" / validator_name
    root.mkdir(parents=True, exist_ok=True)
    return root


def validator_source_path(paths: ProjectPaths, validator_name: str) -> Path:
    return paths.validator_root / "src" / "lib" / f"{validator_name}.js"


def requirement_spec_candidates(paths: ProjectPaths, validator_name: str) -> list[Path]:
    lower_name = validator_name.lower()
    return [
        paths.workspace_root / f"{lower_name}_requirement_spec.md",
        paths.workspace_root / f"{validator_name}_requirement_spec.md",
    ]


def resolve_requirement_spec(paths: ProjectPaths, validator_name: str) -> tuple[str, str]:
    readme_requirement = build_requirement_from_readme(paths, validator_name)
    if readme_requirement is not None:
        return readme_requirement, str(paths.validator_root / "README.md")
    for candidate in requirement_spec_candidates(paths, validator_name):
        if candidate.exists():
            return read_text(candidate), str(candidate)
    return (
        (
            f"Function name: {validator_name}\n"
            "No README entry or dedicated requirement spec file was found.\n"
            "Infer the function's external behavior conservatively from the source code.\n"
        ),
        "source fallback",
    )


def _clean_readme_description(description: str) -> str:
    cleaned = description.strip()
    cleaned = cleaned.replace("<br/><br/>", "\n\n")
    cleaned = cleaned.replace("<br />", "\n")
    cleaned = cleaned.replace("<br/>", "\n")
    cleaned = re.sub(r"\[([^\]]+)\]\[[^\]]+\]", r"\1", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def build_requirement_from_readme(paths: ProjectPaths, validator_name: str) -> str | None:
    readme_path = paths.validator_root / "README.md"
    readme_text = read_text(readme_path)
    pattern = re.compile(rf"^\*\*{re.escape(validator_name)}\((.*?)\)\*\*(.*)$", re.MULTILINE)
    match = pattern.search(readme_text)
    if not match:
        return None

    signature_args = match.group(1)
    description = _clean_readme_description(match.group(2))
    return (
        f"Function name: {validator_name}\n"
        "Black-box requirement source: validator_js README function entry\n"
        f"Signature summary: {validator_name}({signature_args})\n"
        f"README behavior summary:\n{description}\n\n"
        "Treat the README entry as the authoritative black-box behavior description.\n"
        "Infer valid inputs, invalid inputs, option-sensitive behaviors, and edge cases from this description.\n"
    )

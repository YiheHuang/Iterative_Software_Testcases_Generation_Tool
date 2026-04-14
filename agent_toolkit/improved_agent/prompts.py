from __future__ import annotations

import json
from textwrap import dedent
from typing import Any


SYSTEM_PROMPT = dedent(
    """
    You are an expert software testing agent.
    You generate high-quality black-box and white-box tests for validator-style functions.
    You must reason conservatively, preserve correctness, and improve coverage with small precise patches.

    Always return valid JSON only.
    JSON schema:
    {
      "obligations": [
        {
          "id": "string",
          "kind": "blackbox|whitebox",
          "rule": "string",
          "why": "string",
          "minimal_valid": "string or null",
          "minimal_invalid": "string or null"
        }
      ],
      "test_groups": [
        {
          "title": "string",
          "validator": "target validator name",
          "args": [ { } ],
          "valid": ["..."],
          "invalid": ["..."],
          "error": ["..."],
          "rationale": "string",
          "obligations": ["OB-1", "OB-2"]
        }
      ]
    }

    Requirements:
    - Group tests by option profile.
    - For broad black-box APIs with many documented options, expand into multiple semantically distinct groups instead of collapsing everything into one default group.
    - Keep each group narrow: a group should usually cover one baseline partition family or one closely related option-sensitive behavior.
    - Prefer more distinct categories when the requirement clearly documents many switches, constraints, or acceptance/rejection modes.
    - Keep patches minimal and avoid redundant duplicates.
    - Include error cases for non-string inputs when relevant.
    - Prefer minimally different cases that flip one rule at a time.
    - Never repeat the same JSON key within one object.
    - Keep the response concise enough to remain valid JSON.
    - Do not output markdown.
    """
).strip()


def build_blackbox_prompt(validator_name: str, requirement_spec: str) -> str:
    return dedent(
        f"""
        Task: generate black-box tests for {validator_name}.

        Apply standard black-box testing methods aggressively:
        - equivalence partitioning
        - boundary value analysis
        - option-combination testing
        - negative/error-input testing
        - special-case and rare-option exploration

        Step 1: extract explicit black-box obligations from the requirement.
        Step 2: cluster the obligations into semantically distinct black-box categories.
        Step 3: expand each category into grouped validator.js-style tests.
        Step 4: self-check whether rare options, boundary-adjacent cases, invalid partitions, and documented option flips were skipped.

        Requirement specification:
        {requirement_spec}

        Output guidance:
        - first identify the major requirement-visible categories before writing any examples
        - keep one coherent option profile or one closely related rule family per group
        - do not collapse many unrelated options into one catch-all "default" group
        - if the requirement documents many independent switches or acceptance/rejection rules, reflect them in multiple groups
        - cover both baseline behavior and option-sensitive deviations
        - prefer broad category exploration, but keep each example requirement-grounded and likely correct
        - for every option-sensitive group, choose examples whose validity actually changes because of that option profile
        - if a documented option effect is only observable together with another option value, configure both so the distinction is real
        - do not claim an example is invalid for an option if the requirement text still permits it under the provided args
        - prefer paired examples that differ by one rule or one option flip when demonstrating requirement changes
        - when a default already allows a behavior, do not present enabling the same behavior as a meaningful new category unless another argument makes the contrast observable
        - when uncertain, choose fewer examples inside a group rather than merging unrelated categories
        - include multiple concrete valid and invalid examples only when they cover meaningfully different cases
        - include non-string error cases when relevant
        - try to ensure most obligations are represented by at least one dedicated or clearly focused group

        Self-audit before finalizing:
        - Did you create separate groups for materially different option families instead of one oversized group?
        - Did you include default behavior, strictness-raising options, permissive options, whitelist/blacklist style filters, and length/error-related behavior when documented?
        - For each option-focused group, would at least one valid/invalid pair change outcome if that option were flipped back?
        - Did you accidentally use examples whose expected result depends on undocumented implementation details rather than the visible requirement?
        - Are your expectations aligned with the requirement text rather than guessed from hidden implementation details?
        """
    ).strip()


def build_whitebox_prompt(
    validator_name: str,
    requirement_spec: str,
    source_code: str,
) -> str:
    return dedent(
        f"""
        Task: generate white-box tests for {validator_name}.

        Treat this as requirement-constrained white-box testing.
        Use both the intended external behavior and the implementation structure.

        Apply standard white-box testing methods aggressively:
        - statement coverage
        - branch coverage
        - condition-oriented reasoning
        - early-return triggering
        - helper-sensitive path exploration
        - requirement-grounded partition checking

        Step 1: derive black-box obligations from the requirement.
        Step 2: enumerate structural white-box obligations directly from the code.
        Step 3: merge overlaps and contradictions.
        Step 4: expand them into many grouped validator.js-style tests.
        Step 5: self-check whether early returns, helper-dependent checks, option flips, boundary-triggered branches, and requirement-visible edge cases were skipped.

        Requirement specification:
        {requirement_spec}

        Source code:
        {source_code}

        Output limits:
        - each group should focus on one option profile or one branch family
        - explore broadly when requirement-visible behavior and source-level branches genuinely justify it
        - do not inflate obligations or groups just to reach a target count
        - prefer a compact suite that still covers materially different paths and edge cases
        """
    ).strip()


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
        f"The previous {mode} generation for {validator_name} produced obligations but no usable test_groups.\n"
        "Using the obligations below, generate non-empty validator.js-style test_groups now.\n"
        "Return strict JSON with top-level keys obligations and test_groups.\n"
        "Keep the obligations unchanged unless a tiny correction is necessary.\n"
        "test_groups must be non-empty.\n"
        "Each group must contain validator, args, valid, invalid, error, title, rationale, obligations.\n\n"
        f"Original task:\n{original_prompt}\n\n"
        f"Existing obligations:\n{json.dumps(obligations, ensure_ascii=False, indent=2)}"
    )


def build_improvement_prompt(
    validator_name: str,
    mode: str,
    requirement_spec: str,
    source_code: str,
    generated_groups: list[dict[str, Any]],
    evaluation_feedback: dict[str, Any],
) -> str:
    feedback_uses_coverage = "uncovered_details" in evaluation_feedback
    feedback_policy = (
        "You are given the raw source code and fine-grained uncovered white-box coverage details.\n"
        "You must map the uncovered positions back to the source code and design patch tests that target those exact uncovered statements, branches, or functions.\n"
        if feedback_uses_coverage
        else "You may use ONLY runtime correctness feedback from concrete failed test cases.\n"
    )
    return (
        f"You are improving an existing {mode} test suite for {validator_name}.\n"
        f"{feedback_policy}"
        "You must NOT use any golden tests, repository test overlap analysis, or external oracle hints.\n\n"
        "Goal:\n"
        "- fix incorrect expectations or malformed test cases\n"
        "- add only a very small number of new groups to improve runtime correctness and coverage\n"
        "- keep the suite conservative and low-redundancy\n\n"
        "Return strict JSON with top-level keys obligations and test_groups.\n"
        "The returned test_groups should be patch groups only, not a full rewritten suite.\n\n"
        "Black-box requirement source:\n"
        f"{requirement_spec}\n\n"
        "Source code:\n"
        f"{source_code}\n\n"
        "Current generated suite:\n"
        f"{json.dumps(generated_groups, ensure_ascii=True, indent=2)}\n\n"
        "Runtime feedback allowed for improvement:\n"
        f"{json.dumps(evaluation_feedback, ensure_ascii=True, indent=2)}\n\n"
        "Instructions:\n"
        "- Read the raw source code together with uncovered_details before proposing any patch.\n"
        "- Treat uncovered_details as exact white-box targets, not as vague hints.\n"
        "- If an uncovered branch or statement cannot be linked back to the provided source code, do not guess.\n"
        "- Only propose at most 3 patch groups.\n"
        "- Each patch group should contain at most 3 valid values, 3 invalid values, and 1 error value.\n"
        "- If uncovered_details are provided, use them only as white-box targets.\n"
        "- If uncovered_details are not provided, do not infer any hidden coverage gap.\n"
        "- Prefer minimal option-profile-specific groups.\n"
        "- Avoid broad extrapolation; every patch should point to a concrete uncovered position or condition in the code.\n"
        "- Do not mention or infer any golden test information.\n"
    )

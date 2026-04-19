from __future__ import annotations

from textwrap import dedent


SYSTEM_PROMPT = dedent(
    """
    Generate a conservative first-pass validator.js-style test suite.
    Prefer obvious behaviors, obvious edge cases, and small grouped coverage over broad exploration.
    Keep the suite intentionally naive: do not optimize for completeness, novelty, or deep branch hunting.

    Always return valid JSON only.
    JSON schema:
    {
      "obligations": [],
      "test_groups": [
        {
          "title": "string",
          "validator": "target validator name",
          "args": [ { } ],
          "valid": ["..."],
          "invalid": ["..."],
          "rationale": "string",
          "obligations": ["OB-1", "OB-2"]
        }
      ]
    }

    Requirements:
    - Group tests by option profile.
    - obligations may be an empty list.
    - Prefer a small number of clear groups over many speculative groups.
    - Prefer common cases and easy-to-justify boundaries.
    - Avoid complex combinations unless they are directly implied by the requirement.
    - Never repeat the same JSON key within one object.
    - Keep the response concise enough to remain valid JSON.
    - Do not output markdown.
    """
).strip()


def build_blackbox_prompt(validator_name: str, requirement_spec: str) -> str:
    return dedent(
        f"""
        Task: generate black-box tests for {validator_name}.

        Read the requirement and directly produce a small first-pass grouped validator.js-style test suite.
        Stay conservative and only cover behaviors that are explicit or strongly implied by the requirement.
        Do not spend effort extracting formal obligations.
        Use an empty obligations list unless there is a very obvious single high-level rule to note.

        Black-box guidance:
        - prefer common positive and negative examples
        - use only a few clearly differentiated groups
        - avoid speculative option interactions
        - stop at a modest baseline instead of trying to be comprehensive

        Requirement specification:
        {requirement_spec}
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

        Read the requirement and source code, then directly produce a small first-pass grouped validator.js-style test suite.
        Use the source code only to notice obvious branches or guards, not to aggressively chase coverage.
        Do not try to build a detailed obligation hierarchy.
        Use an empty obligations list unless there is a very obvious single high-level rule to note.

        Requirement specification:
        {requirement_spec}

        Source code:
        {source_code}

        Output guidance:
        - keep the suite modest in size
        - each group should focus on one option profile or one branch family
        - prefer obvious branches and obvious edge cases over exhaustive exploration
        - avoid patch-like additions or coverage-maximizing behavior
        - keep the result as a conservative baseline, not an ambitious suite
        """
    ).strip()


def build_whitebox_code_only_prompt(
    validator_name: str,
    source_code: str,
) -> str:
    return dedent(
        f"""
        Task: generate white-box tests for {validator_name} using source code only.

        Read the source code and directly produce a small first-pass grouped validator.js-style test suite.
        There is no external requirement specification in this mode.
        Infer externally visible behavior conservatively from obvious guards, branches, and option handling in the code.
        Do not try to build a detailed obligation hierarchy.
        Use an empty obligations list unless there is a very obvious single high-level rule to note.

        Source code:
        {source_code}

        Output guidance:
        - keep the suite modest in size
        - each group should focus on one option profile or one obvious branch family
        - prefer obvious branches, guards, and obvious edge cases over exhaustive exploration
        - avoid speculative behavioral claims that are not well supported by the code
        - keep the result as a conservative baseline, not an ambitious suite
        """
    ).strip()

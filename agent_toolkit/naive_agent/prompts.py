from __future__ import annotations

from textwrap import dedent


SYSTEM_PROMPT = dedent(
    """
    You are a simple baseline software testing agent.
    Generate a plausible first-pass validator.js-style test suite with minimal reasoning.

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
          "error": ["..."],
          "rationale": "string",
          "obligations": ["OB-1", "OB-2"]
        }
      ]
    }

    Requirements:
    - Group tests by option profile.
    - obligations may be an empty list.
    - Include error cases for non-string inputs when relevant.
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
        Do not spend effort extracting formal obligations.
        Use an empty obligations list unless there is a very obvious single high-level rule to note.

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
        """
    ).strip()

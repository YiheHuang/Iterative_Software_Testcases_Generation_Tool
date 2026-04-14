from __future__ import annotations

import argparse
import json


def normalize_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized == "hybrid":
        return "whitebox"
    if normalized in {"blackbox", "whitebox"}:
        return normalized
    raise ValueError(f"Unsupported mode: {mode}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LLM-driven black-box and white-box test generation for validator.js"
    )
    parser.add_argument(
        "--mode",
        required=True,
        help="Generation mode: blackbox or whitebox. Legacy alias: hybrid",
    )
    parser.add_argument(
        "--workspace-root",
        default=None,
        help="Workspace root. Defaults to repository root inferred from this script.",
    )
    parser.add_argument(
        "--validator",
        default="isEmail",
        help="Target validator function name, for example isEmail or isFQDN.",
    )
    parser.add_argument(
        "--approach",
        choices=["naive", "improved"],
        default="improved",
        help="Generation approach. naive preserves the current single-pass flow; improved adds runtime-feedback refinement.",
    )
    parser.add_argument("--api-url", default=None, help="Chat Completions API URL")
    parser.add_argument("--api-key", default=None, help="Chat Completions API key")
    parser.add_argument("--model", default=None, help="Model name")
    parser.add_argument(
        "--temperature", type=float, default=0.2, help="Sampling temperature"
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=240,
        help="HTTP timeout for LLM responses",
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help="Generate only. Skip execution and coverage collection.",
    )
    parser.add_argument(
        "--analyze-golden",
        action="store_true",
        help="Use LLM to compare generated tests against validators.test.js golden tests.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.mode = normalize_mode(args.mode)
    except ValueError as exc:
        parser.error(str(exc))

    if args.approach == "naive":
        from agent_toolkit.naive_agent.config import load_llm_config, resolve_paths
        from agent_toolkit.naive_agent.evaluation import EvaluationService, load_evaluation_payload
        from agent_toolkit.naive_agent.golden_analysis import GoldenAnalysisService
        from agent_toolkit.naive_agent.io_utils import write_json
        from agent_toolkit.naive_agent.llm_client import LLMClient
        from agent_toolkit.naive_agent.service import NaiveAgentService
        from agent_toolkit.naive_agent.target_context import run_output_root

        paths = resolve_paths(args.workspace_root)
        llm_config = load_llm_config(
            api_url=args.api_url,
            api_key=args.api_key,
            model=args.model,
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
            workspace_root=args.workspace_root,
        )
        client = LLMClient(llm_config)
        generator = NaiveAgentService(paths, client)
    else:
        from agent_toolkit.improved_agent.config import load_llm_config, resolve_paths
        from agent_toolkit.improved_agent.evaluation import EvaluationService, load_evaluation_payload
        from agent_toolkit.improved_agent.golden_analysis import GoldenAnalysisService
        from agent_toolkit.improved_agent.io_utils import write_json
        from agent_toolkit.improved_agent.llm_client import LLMClient
        from agent_toolkit.improved_agent.service import ImprovedAgentService
        from agent_toolkit.improved_agent.target_context import run_output_root

        paths = resolve_paths(args.workspace_root)
        llm_config = load_llm_config(
            api_url=args.api_url,
            api_key=args.api_key,
            model=args.model,
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
            workspace_root=args.workspace_root,
        )
        client = LLMClient(llm_config)
        generator = ImprovedAgentService(paths, client)

    result = generator.generate(args.mode, args.validator, args.approach)

    summary = {
        "validator_name": result.validator_name,
        "mode": result.mode,
        "approach": result.approach,
        "obligation_count": len(result.obligations),
        "group_count": len(result.test_groups),
        "prompt_path": str(result.prompt_path) if result.prompt_path else None,
        "response_path": str(result.response_path) if result.response_path else None,
    }

    evaluation_payload = None
    if not args.skip_eval:
        evaluator = EvaluationService(paths)
        evaluation = evaluator.evaluate(result)
        if evaluation.output_json_path:
            evaluation_payload = load_evaluation_payload(evaluation.output_json_path)
        summary["evaluation"] = {
            "total_cases": evaluation.total_cases,
            "correct_cases": evaluation.correct_cases,
            "incorrect_cases": evaluation.incorrect_cases,
            "exact_match_rate": evaluation.exact_match_rate,
            "output_json_path": str(evaluation.output_json_path)
            if evaluation.output_json_path
            else None,
            "coverage_dir": str(evaluation.coverage_dir)
            if evaluation.coverage_dir
            else None,
        }

    if args.analyze_golden:
        analyzer = GoldenAnalysisService(paths, client)
        comparison = analyzer.analyze(result, evaluation_payload)
        summary["golden_analysis"] = {
            "summary": comparison.get("summary", {}),
            "comparison_path": str(
                run_output_root(paths, result.validator_name, result.approach, result.mode)
                / "golden_comparison.json"
            ),
        }

    final_summary_path = (
        run_output_root(paths, result.validator_name, result.approach, result.mode)
        / "run_summary.json"
    )
    write_json(final_summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import threading
import time
from pathlib import Path


# Curated default set for batch experiments:
# - present in source_code/validator_js/test/validators.test.js
# - avoids validators whose golden tests currently live only in split test files
# - avoids validators known to break the current golden extractor
# - prefers validators with relatively rich golden test groups
DEFAULT_VALIDATORS = [
    "isEmail",
    "isURL",
    "isFQDN",
    "isCurrency",
    "isCreditCard",
]

APPROACHES = ["naive", "improved"]
MODES = ["blackbox", "whitebox", "whitebox_code_only"]
PRINT_LOCK = threading.Lock()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run curated validator.js experiments across 2 approaches x 3 modes."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="Repository root. Defaults to the directory containing this script.",
    )
    parser.add_argument(
        "--validators",
        nargs="*",
        default=DEFAULT_VALIDATORS,
        help="Validator names to run. Defaults to the built-in curated validator list.",
    )
    parser.add_argument(
        "--skip-golden",
        action="store_true",
        help="Skip golden analysis to reduce runtime and token usage.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Maximum number of experiments to run in parallel. Defaults to 5.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retry count after a failed run. Defaults to 3.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop scheduling new work after the first permanently failed experiment.",
    )
    parser.add_argument(
        "--summary-path",
        default=None,
        help="Optional output path for the batch summary JSON.",
    )
    return parser.parse_args()


def load_run_summary(
    workspace_root: Path,
    validator_name: str,
    approach: str,
    mode: str,
) -> dict | None:
    summary_path = (
        workspace_root
        / "agent_toolkit"
        / "outputs"
        / approach
        / validator_name
        / mode
        / "run_summary.json"
    )
    if not summary_path.exists():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def build_run_summary_path(
    workspace_root: Path,
    validator_name: str,
    approach: str,
    mode: str,
) -> Path:
    return (
        workspace_root
        / "agent_toolkit"
        / "outputs"
        / approach
        / validator_name
        / mode
        / "run_summary.json"
    )


def build_command(
    validator_name: str,
    approach: str,
    mode: str,
    skip_golden: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "agent_toolkit.cli",
        "--approach",
        approach,
        "--mode",
        mode,
        "--validator",
        validator_name,
    ]
    if not skip_golden:
        command.append("--analyze-golden")
    return command


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def run_single_experiment(
    workspace_root: Path,
    validator_name: str,
    approach: str,
    mode: str,
    skip_golden: bool,
    max_retries: int,
    run_index: int,
    total_runs: int,
) -> dict:
    command = build_command(validator_name, approach, mode, skip_golden)
    summary_path = build_run_summary_path(workspace_root, validator_name, approach, mode)
    started_at = time.time()
    attempt_records: list[dict] = []
    last_return_code: int | None = None

    for attempt in range(1, max_retries + 2):
        log(
            f"[{run_index}/{total_runs}] attempt {attempt}/{max_retries + 1} "
            f"{validator_name} | {approach} | {mode}"
        )
        attempt_started_at = time.time()
        completed = subprocess.run(command, cwd=workspace_root)
        elapsed_seconds = round(time.time() - attempt_started_at, 2)
        last_return_code = completed.returncode
        attempt_record = {
            "attempt": attempt,
            "return_code": completed.returncode,
            "elapsed_seconds": elapsed_seconds,
        }
        attempt_records.append(attempt_record)

        if completed.returncode == 0:
            run_summary = load_run_summary(workspace_root, validator_name, approach, mode)
            record = {
                "validator_name": validator_name,
                "approach": approach,
                "mode": mode,
                "command": command,
                "return_code": 0,
                "status": "success",
                "attempt_count": attempt,
                "attempts": attempt_records,
                "elapsed_seconds": round(time.time() - started_at, 2),
                "run_summary_path": str(summary_path),
                "llm_usage": (
                    run_summary.get("llm_usage", {})
                    if isinstance(run_summary, dict)
                    else {}
                ),
            }
            log(
                f"[{run_index}/{total_runs}] OK "
                f"{validator_name} | {approach} | {mode} "
                f"(attempts={attempt}, elapsed={record['elapsed_seconds']}s, "
                f"total_tokens={record['llm_usage'].get('total_tokens')})"
            )
            return record

        if attempt <= max_retries:
            log(
                f"[{run_index}/{total_runs}] RETRY "
                f"{validator_name} | {approach} | {mode} "
                f"(return_code={completed.returncode}, elapsed={elapsed_seconds}s)"
            )

    run_summary = load_run_summary(workspace_root, validator_name, approach, mode)
    record = {
        "validator_name": validator_name,
        "approach": approach,
        "mode": mode,
        "command": command,
        "return_code": last_return_code,
        "status": "failed",
        "attempt_count": len(attempt_records),
        "attempts": attempt_records,
        "elapsed_seconds": round(time.time() - started_at, 2),
        "run_summary_path": str(summary_path),
        "llm_usage": (
            run_summary.get("llm_usage", {})
            if isinstance(run_summary, dict)
            else {}
        ),
    }
    log(
        f"[{run_index}/{total_runs}] FAILED "
        f"{validator_name} | {approach} | {mode} "
        f"(attempts={record['attempt_count']}, return_code={last_return_code})"
    )
    return record


def aggregate_llm_usage(results: list[dict]) -> dict[str, int]:
    aggregate = {
        "request_count": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    for result in results:
        usage = result.get("llm_usage", {})
        if not isinstance(usage, dict):
            continue
        for key in aggregate:
            value = usage.get(key)
            if isinstance(value, int):
                aggregate[key] += value
    return aggregate


def main() -> int:
    args = parse_args()
    workspace_root = args.workspace_root.resolve()
    validators = list(args.validators)
    total_runs = len(validators) * len(APPROACHES) * len(MODES)
    batch_started_at = time.time()
    workers = max(1, args.workers)

    jobs: list[tuple[int, str, str, str]] = []
    run_index = 0
    for validator_name in validators:
        for approach in APPROACHES:
            for mode in MODES:
                run_index += 1
                jobs.append((run_index, validator_name, approach, mode))

    indexed_results: dict[int, dict] = {}
    failures = 0
    permanent_failure_detected = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(
                run_single_experiment,
                workspace_root,
                validator_name,
                approach,
                mode,
                args.skip_golden,
                args.max_retries,
                current_index,
                total_runs,
            ): current_index
            for current_index, validator_name, approach, mode in jobs
        }

        for future in concurrent.futures.as_completed(future_to_index):
            current_index = future_to_index[future]
            record = future.result()
            indexed_results[current_index] = record

            if record["status"] != "success":
                failures += 1
                permanent_failure_detected = True
                if args.stop_on_error:
                    for pending_future in future_to_index:
                        pending_future.cancel()
                    break

    results = [indexed_results[index] for index in sorted(indexed_results)]

    batch_summary = {
        "workspace_root": str(workspace_root),
        "validators": validators,
        "approaches": APPROACHES,
        "modes": MODES,
        "workers": workers,
        "max_retries": args.max_retries,
        "total_runs": total_runs,
        "completed_runs": len(results),
        "failed_runs": failures,
        "stopped_early": bool(args.stop_on_error and permanent_failure_detected),
        "elapsed_seconds": round(time.time() - batch_started_at, 2),
        "aggregate_llm_usage": aggregate_llm_usage(results),
        "results": results,
    }
    summary_path = Path(args.summary_path) if args.summary_path else (
        workspace_root / "experiment_10_batch_summary.json"
    )
    summary_path.write_text(
        json.dumps(batch_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"batch summary written to: {summary_path}")
    print(f"failed runs: {failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

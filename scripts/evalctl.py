import argparse
import json
import sys
from pathlib import Path

# Allow running this script directly from the repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evals.runner import run_cases, run_suite


def _print_summary(summary: dict) -> None:
    """Print a compact run summary to stdout."""

    print(json.dumps(summary["metrics"], indent=2))
    if summary["failed_cases"]:
        print("\nFailed cases:", file=sys.stderr)
        for failed_case in summary["failed_cases"]:
            print(
                f"- {failed_case['case_id']} "
                f"(status={failed_case['execution_status']}, "
                f"failed_judges={failed_case['failed_judges']})",
                file=sys.stderr,
            )


def main() -> None:
    """Run one eval case or an entire suite."""

    parser = argparse.ArgumentParser(description="Minimal evaluation runner for agent-eval-lab.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a suite or a single case")
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--suite", help="Path to a suite YAML file")
    run_group.add_argument("--case", help="Path to a case YAML file")

    args = parser.parse_args()

    if args.suite:
        summary = run_suite(args.suite)
    else:
        case_path = Path(args.case).resolve()
        summary = run_cases([case_path], case_path.stem)

    print(f"Run ID: {summary['run_id']}", file=sys.stderr)
    print(f"Suite: {summary['suite_name']}", file=sys.stderr)
    _print_summary(summary)


if __name__ == "__main__":
    main()

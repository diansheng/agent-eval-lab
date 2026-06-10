import argparse
import json
import sys
from pathlib import Path

# Allow running this script directly from the repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent import ReviewRunError, ReviewRunResult, review_pull_request
from app.config import load_settings
from app.review_schema import ReviewFormatError
from app.tools.github_tools import GitHubToolError


def write_json(payload: dict, output_file: str | None) -> None:
    """Print JSON to stdout and optionally save it to a file."""

    rendered = json.dumps(payload, indent=2)

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)


def save_trace(trace: dict, trace_file: str | None) -> None:
    """Persist trace metadata if the caller asked for it."""

    if not trace_file:
        return

    trace_path = Path(trace_file)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Review a GitHub PR by letting the model use the Week 2 tools."""

    parser = argparse.ArgumentParser(
        description="Review a GitHub pull request with the Week 2 MiniMax tool loop."
    )
    parser.add_argument("--owner", required=True, help="GitHub owner or organization")
    parser.add_argument("--repo", required=True, help="GitHub repository name")
    parser.add_argument("--pr-number", type=int, required=True, help="Pull request number")
    parser.add_argument(
        "--output-file",
        help="Optional path to save the final parsed review JSON.",
    )
    parser.add_argument(
        "--trace-file",
        help="Optional path to save basic run trace metadata.",
    )
    args = parser.parse_args()

    settings = load_settings()

    try:
        result: ReviewRunResult = review_pull_request(
            settings=settings,
            owner=args.owner,
            repo=args.repo,
            pr_number=args.pr_number,
        )
    except ReviewRunError as error:
        save_trace(error.trace, args.trace_file)
        print(f"Error: {error}", file=sys.stderr)
        if args.trace_file:
            print(f"Trace file: {args.trace_file}", file=sys.stderr)
        raise SystemExit(1) from error
    except (ValueError, RuntimeError, GitHubToolError, ReviewFormatError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(f"Model: {settings.anthropic_model}", file=sys.stderr)
    print(f"PR: {args.owner}/{args.repo}#{args.pr_number}", file=sys.stderr)
    if args.trace_file:
        print(f"Trace file: {args.trace_file}", file=sys.stderr)
    if args.output_file:
        print(f"Output file: {args.output_file}", file=sys.stderr)

    save_trace(result.trace, args.trace_file)
    write_json(result.review, args.output_file)


if __name__ == "__main__":
    main()

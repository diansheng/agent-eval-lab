import argparse
import json
import sys
from pathlib import Path

# Allow running this script directly from the repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_settings
from app.tools.github_tools import GitHubToolError, fetch_files, fetch_pr


def main() -> None:
    """Run a simple manual test for the GitHub tool functions."""

    parser = argparse.ArgumentParser(description="Manual smoke test for GitHub Week 2 tools.")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    args = parser.parse_args()

    settings = load_settings()

    try:
        pr_data = fetch_pr(settings, args.owner, args.repo, args.pr_number)
        file_data = fetch_files(settings, args.owner, args.repo, args.pr_number)
    except GitHubToolError as error:
        raise SystemExit(f"Tool error: {error}") from error

    print("PR:")
    print(json.dumps(pr_data, indent=2))
    print("\nFiles:")
    print(json.dumps(file_data, indent=2))


if __name__ == "__main__":
    main()

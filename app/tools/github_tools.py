from __future__ import annotations

from typing import Any, Optional

import requests

from app.config import Settings


class GitHubToolError(RuntimeError):
    """Raised when a GitHub API request fails or returns unusable data."""


def _build_headers(settings: Settings) -> dict[str, str]:
    """Build the headers needed for authenticated GitHub API requests."""

    if not settings.github_token:
        raise GitHubToolError("Missing GITHUB_TOKEN. Set it in your .env before running tools.")

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agent-eval-lab",
    }


def _get_json(
    settings: Settings, path: str, params: Optional[dict[str, Any]] = None
) -> Any:
    """Send a GET request to GitHub and return the parsed JSON response."""

    url = f"{settings.github_api_base}{path}"
    response = requests.get(url, headers=_build_headers(settings), params=params, timeout=30)

    if response.status_code == 404:
        raise GitHubToolError(f"GitHub resource not found: {path}")

    if response.status_code in {401, 403}:
        raise GitHubToolError(
            f"GitHub API auth/access failure ({response.status_code}). "
            "Check GITHUB_TOKEN permissions and repo visibility."
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise GitHubToolError(
            f"GitHub API request failed for {path}: "
            f"{response.status_code} {response.text[:300]}"
        ) from error

    return response.json()


def _truncate_patch(patch: Optional[str], max_chars: int) -> Optional[str]:
    """Shorten large patch text so it stays small enough for model input."""

    if patch is None:
        return None
    if len(patch) <= max_chars:
        return patch
    return patch[:max_chars] + "\n... [truncated]"


def fetch_pr(settings: Settings, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
    """Fetch basic pull request metadata and return only the fields the model needs."""

    payload = _get_json(settings, f"/repos/{owner}/{repo}/pulls/{pr_number}")

    return {
        "number": payload["number"],
        "title": payload.get("title", ""),
        "body": payload.get("body") or "",
        "state": payload.get("state", ""),
        "base_branch": payload.get("base", {}).get("ref", ""),
        "head_branch": payload.get("head", {}).get("ref", ""),
        "author": (payload.get("user") or {}).get("login", ""),
        "url": payload.get("html_url", ""),
    }


def fetch_files(
    settings: Settings, owner: str, repo: str, pr_number: int
) -> list[dict[str, Any]]:
    """Fetch changed files for a pull request and keep the response small and clean."""

    files: list[dict[str, Any]] = []
    page = 1

    while len(files) < settings.max_pr_files:
        payload = _get_json(
            settings,
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
            params={"per_page": min(100, settings.max_pr_files), "page": page},
        )

        if not payload:
            break

        for item in payload:
            files.append(
                {
                    "filename": item.get("filename", ""),
                    "status": item.get("status", ""),
                    "additions": item.get("additions", 0),
                    "deletions": item.get("deletions", 0),
                    "changes": item.get("changes", 0),
                    "patch": _truncate_patch(
                        item.get("patch"), settings.max_patch_chars
                    ),
                }
            )
            if len(files) >= settings.max_pr_files:
                break

        page += 1

    return files

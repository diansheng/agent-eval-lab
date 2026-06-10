import json
from dataclasses import dataclass
from time import time
from typing import Any

import anthropic

from app.config import Settings
from app.review_schema import parse_review_json
from app.tools.github_tools import GitHubToolError, fetch_files, fetch_pr


SYSTEM_PROMPT = """You are a careful code reviewer.
Review the requested GitHub pull request by calling tools before making claims.

Focus on:
- likely bugs
- correctness issues
- risky changes
- missing edge cases

Rules:
- Call tools to inspect the PR metadata and changed files before producing the final answer.
- Use only information returned by tools.
- Do not invent files or code not present in tool results.
- Be concise and practical.
- Return only valid JSON that matches the requested schema.
"""


USER_PROMPT_TEMPLATE = """Review GitHub pull request {owner}/{repo}#{pr_number}.

First gather the PR metadata and changed files with tools.

Return a JSON object with this exact shape:
{{
  "summary": "short overall summary",
  "findings": [
    {{
      "severity": "low | medium | high",
      "title": "short finding title",
      "file": "path/to/file.ext",
      "comment": "concise review comment"
    }}
  ],
  "confidence": "low | medium | high",
  "needs_manual_review": true
}}

Rules:
- Return JSON only.
- If there are no strong findings, return an empty "findings" array.
- Do not include markdown fences.
- Sort findings by severity (high first medium second low last).
"""


MAX_TOOL_ROUNDS = 6


@dataclass(frozen=True)
class ReviewRunResult:
    """Bundle the final review output together with basic run metadata."""

    review: dict[str, Any]
    trace: dict[str, Any]


def build_tools() -> list[dict[str, Any]]:
    """Define the GitHub tools exposed to the model."""

    shared_properties = {
        "owner": {
            "type": "string",
            "description": "GitHub repository owner or organization name.",
        },
        "repo": {
            "type": "string",
            "description": "GitHub repository name.",
        },
        "pr_number": {
            "type": "integer",
            "description": "Pull request number.",
        },
    }

    return [
        {
            "name": "fetch_pr",
            "description": "Fetch basic pull request metadata before reviewing code.",
            "input_schema": {
                "type": "object",
                "properties": shared_properties,
                "required": ["owner", "repo", "pr_number"],
            },
        },
        {
            "name": "fetch_files",
            "description": "Fetch changed files and patches for the pull request.",
            "input_schema": {
                "type": "object",
                "properties": shared_properties,
                "required": ["owner", "repo", "pr_number"],
            },
        },
    ]


def _extract_text_blocks(content_blocks: list[Any]) -> str:
    """Collect plain text blocks from an Anthropic-style message response."""

    return "\n".join(
        block.text for block in content_blocks if getattr(block, "type", None) == "text"
    ).strip()


def _assistant_blocks_to_dicts(content_blocks: list[Any]) -> list[dict[str, Any]]:
    """Convert SDK content blocks into plain dictionaries for conversation history."""

    serialized_blocks: list[dict[str, Any]] = []
    for block in content_blocks:
        block_type = getattr(block, "type", None)

        if block_type == "text":
            serialized_blocks.append({"type": "text", "text": block.text})
            continue

        if block_type == "tool_use":
            serialized_blocks.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
            )

    return serialized_blocks


def _run_tool(
    settings: Settings, tool_name: str, tool_input: dict[str, Any]
) -> dict[str, Any] | list[dict[str, Any]]:
    """Execute one tool call requested by the model."""

    owner = tool_input["owner"]
    repo = tool_input["repo"]
    pr_number = tool_input["pr_number"]

    if tool_name == "fetch_pr":
        return fetch_pr(settings, owner=owner, repo=repo, pr_number=pr_number)
    if tool_name == "fetch_files":
        return fetch_files(settings, owner=owner, repo=repo, pr_number=pr_number)

    raise GitHubToolError(f"Unsupported tool requested by model: {tool_name}")


def review_pull_request(
    settings: Settings, owner: str, repo: str, pr_number: int
) -> ReviewRunResult:
    """Review a pull request by letting the model call GitHub tools first."""

    if not settings.anthropic_api_key:
        raise ValueError(
            "Missing MINIMAX_API_KEY. Set it in your .env before running the PR reviewer."
        )

    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url,
    )

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                owner=owner,
                repo=repo,
                pr_number=pr_number,
            ),
        }
    ]

    trace: dict[str, Any] = {
        "owner": owner,
        "repo": repo,
        "pr_number": pr_number,
        "model": settings.anthropic_model,
        "tool_calls": [],
    }

    started_at = time()

    for round_index in range(1, MAX_TOOL_ROUNDS + 1):
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1600,
            system=SYSTEM_PROMPT,
            tools=build_tools(),
            messages=messages,
        )

        assistant_blocks = _assistant_blocks_to_dicts(message.content)
        messages.append({"role": "assistant", "content": assistant_blocks})

        tool_uses = [block for block in message.content if getattr(block, "type", None) == "tool_use"]
        if not tool_uses:
            final_text = _extract_text_blocks(message.content)
            review = parse_review_json(final_text)
            trace["rounds"] = round_index
            trace["latency_seconds"] = round(time() - started_at, 2)
            return ReviewRunResult(review=review, trace=trace)

        tool_results_content: list[dict[str, Any]] = []
        for block in tool_uses:
            result = _run_tool(settings, block.name, block.input)
            trace["tool_calls"].append(
                {
                    "name": block.name,
                    "input": block.input,
                    "result_summary": _summarize_tool_result(result),
                }
            )
            tool_results_content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results_content})

    raise RuntimeError(
        "Tool loop exceeded the maximum number of rounds. "
        "Inspect the prompt or tool-call trace."
    )


def _summarize_tool_result(result: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    """Create a compact summary for trace logs without duplicating full payloads."""

    if isinstance(result, dict):
        return {"type": "object", "keys": sorted(result.keys())}

    filenames = [item.get("filename", "") for item in result[:3]]
    return {"type": "list", "count": len(result), "sample_filenames": filenames}

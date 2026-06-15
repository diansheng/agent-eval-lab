import json
from dataclasses import dataclass
from datetime import datetime, timezone
from time import time
from typing import Any, Union
from uuid import uuid4

import anthropic

from app.config import Settings
from app.review_schema import parse_review_json, render_review_output_example
from app.tools.github_tools import GitHubToolError, fetch_files, fetch_pr


SYSTEM_PROMPT = """You are a careful code reviewer.
Review the requested GitHub pull request. Call tools before making claims.

Focus on:
- likely bugs
- correctness issues
- risky changes
- missing edge cases

Rules:
- Call tools to inspect the PR metadata and changed files before producing the final answer.
- Never claim that a tool failed, that a PR is inaccessible, or that a diff is unavailable unless you actually called the tool and observed that result.
- Use only information returned by tools.
- Do not invent files or code not present in tool results.
- Be concise and practical.
- Return only valid JSON that matches the requested schema.
"""


USER_PROMPT_TEMPLATE = """Review GitHub pull request {owner}/{repo}#{pr_number}.

First gather the PR metadata and changed files with tools.

Return a JSON object with this exact shape:
{review_output_example}

Rules:
- Use the available tools to inspect the real PR, not a guessed or remembered one, before writing findings.
- Return JSON only.
- If there are no strong findings, return an empty "findings" array.
- Return at most 5 findings.
- Do not include markdown fences.
- Sort findings by severity (high first medium second low last).
"""


MAX_TOOL_ROUNDS = 12
MAX_VALIDATION_REPAIRS = 3


@dataclass(frozen=True)
class ReviewRunResult:
    """Bundle the final review output together with basic run metadata."""

    review: dict[str, Any]
    trace: dict[str, Any]


class ReviewRunError(RuntimeError):
    """Raised when a review run fails after trace data has already been collected."""

    def __init__(self, message: str, trace: dict[str, Any]):
        super().__init__(message)
        self.trace = trace


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
            "description": "Fetch basic metadata of a git hub pull request given repo owner, repo name, and pr number.",
            "input_schema": {
                "type": "object",
                "properties": shared_properties,
                "required": ["owner", "repo", "pr_number"],
            },
        },
        {
            "name": "fetch_files",
            "description": "Fetch changed files of a git hub pull request given repo owner, repo name, and pr number.",
            "input_schema": {
                "type": "object",
                "properties": shared_properties,
                "required": ["owner", "repo", "pr_number"],
            },
        },
        {
            "name": "search_knowledge_base",
            "description": "Search the project documentation to answer questions about architecture, past bugs, or setup.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up in the knowledge base.",
                    }
                },
                "required": ["query"],
            },
        },
    ]


def _utc_timestamp() -> str:
    """Return an ISO timestamp in UTC for trace events."""

    return datetime.now(timezone.utc).isoformat()


def _extract_text_blocks(content_blocks: list[Any]) -> str:
    """Collect plain text blocks from an Anthropic-style message response."""

    return "\n".join(
        block.text for block in content_blocks if getattr(block, "type", None) == "text"
    ).strip()


def _serialize_content_block(block: Any) -> dict[str, Any]:
    """Convert one SDK content block into a plain dictionary for traces and history."""

    block_type = getattr(block, "type", None)

    if block_type == "text":
        return {"type": "text", "text": block.text}

    if block_type == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }

    if hasattr(block, "model_dump"):
        return block.model_dump()

    raw_dict = getattr(block, "__dict__", None)
    if isinstance(raw_dict, dict):
        return {
            key: value
            for key, value in raw_dict.items()
            if not key.startswith("_")
        }

    return {"type": block_type or "unknown", "repr": repr(block)}


def _assistant_blocks_to_dicts(content_blocks: list[Any]) -> list[dict[str, Any]]:
    """Convert SDK content blocks into plain dictionaries for conversation history."""

    return [_serialize_content_block(block) for block in content_blocks]


def _extract_changed_files(
    result: Union[dict[str, Any], list[dict[str, Any]]]
) -> list[str]:
    """Collect changed file paths from a tool result when available."""

    if not isinstance(result, list):
        return []

    changed_files: list[str] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename")
        if isinstance(filename, str) and filename and filename not in changed_files:
            changed_files.append(filename)
    return changed_files





def _extract_usage(message: Any) -> dict[str, Any]:
    """Collect token-usage metadata when the provider returns it."""

    usage = getattr(message, "usage", None)
    if usage is None:
        return {}

    usage_fields = {}
    for field in (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        value = getattr(usage, field, None)
        if value is not None:
            usage_fields[field] = value

    return usage_fields


def _build_trace(
    settings: Settings, owner: str, repo: str, pr_number: int, user_prompt: str
) -> dict[str, Any]:
    """Create the initial trace object for a review run."""

    return {
        "run_id": str(uuid4()),
        "status": "running",
        "provider": "minimax_anthropic",
        "model": settings.anthropic_model,
        "started_at": _utc_timestamp(),
        "completed_at": None,
        "latency_seconds": None,
        "input": {
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
        },
        "config": {
            "max_pr_files": settings.max_pr_files,
            "max_patch_chars": settings.max_patch_chars,
            "max_tool_rounds": MAX_TOOL_ROUNDS,
        },
        "system_prompt": SYSTEM_PROMPT,
        "initial_user_message": user_prompt,
        "tools": build_tools(),
        "tool_calls": [],
        "events": [
            {
                "timestamp": _utc_timestamp(),
                "role": "system",
                "type": "system_prompt",
                "content": SYSTEM_PROMPT,
            },
            {
                "timestamp": _utc_timestamp(),
                "role": "user",
                "type": "user_message",
                "content": user_prompt,
            },
        ],
        "final_output": None,
        "error": None,
    }


_rag_retriever = None

def _get_retriever():
    global _rag_retriever
    if _rag_retriever is None:
        from app.rag.retriever import Retriever
        _rag_retriever = Retriever()
    return _rag_retriever

def _run_tool(
    settings: Settings, tool_name: str, tool_input: dict[str, Any]
) -> Union[dict[str, Any], list[dict[str, Any]]]:
    """Execute one tool call requested by the model."""

    if tool_name == "search_knowledge_base":
        query = tool_input.get("query")
        if not query:
            raise ValueError("search_knowledge_base requires a 'query' parameter.")
        retriever = _get_retriever()
        results = retriever.search(query)
        return {"results": results}

    # Note: If tools don't use owner/repo/pr_number in the future,
    # this function should just pass **tool_input directly.
    owner = tool_input.get("owner")
    repo = tool_input.get("repo")
    pr_number = tool_input.get("pr_number")

    if tool_name == "fetch_pr":
        return fetch_pr(settings, owner=owner, repo=repo, pr_number=pr_number)
    if tool_name == "fetch_files":
        return fetch_files(settings, owner=owner, repo=repo, pr_number=pr_number)

    raise GitHubToolError(f"Unsupported tool requested by model: {tool_name}")


def _validate_and_parse_review(
    final_text: str,
    changed_files_seen: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    """Parse the JSON output, validate files, and return (parsed_review, repair_events, error_message)."""
    repair_events = []
    
    try:
        review = parse_review_json(final_text)
    except Exception as error:
        repair_message = (
            "Your previous response was invalid. "
            f"Issue: {error}. "
            "Return only one JSON object matching the requested schema. "
            "Do not include prose or markdown fences."
        )
        return {}, repair_events, repair_message

    invalid_finding_files = [
        finding["file"]
        for finding in review["findings"]
        if changed_files_seen and finding["file"] not in changed_files_seen
    ]
    
    if invalid_finding_files:
        repair_message = (
            "Your previous response used finding.file values that do not "
            "exactly match the changed files returned by tools. "
            f"Invalid files: {sorted(set(invalid_finding_files))}. "
            f"Use only these exact changed paths in finding.file: {changed_files_seen}. "
            "If a concern is about PR metadata rather than a changed file, put it in "
            "the summary instead of a finding."
        )
        return review, repair_events, repair_message
        
    if len(review["findings"]) > 5:
        repair_message = (
            "Your previous response returned too many findings. "
            "Return at most 5 findings, keeping only the strongest evidence-backed "
            "issues from the tool output."
        )
        return review, repair_events, repair_message
        
    return review, repair_events, None

def _process_tool_calls(
    tool_uses: list[Any],
    settings: Settings,
    trace: dict[str, Any],
    round_index: int,
    changed_files_seen: list[str],
) -> list[dict[str, Any]]:
    """Execute all tools requested by the model and record results in the trace."""
    tool_results_content: list[dict[str, Any]] = []
    
    for block in tool_uses:
        trace["events"].append(
            {
                "timestamp": _utc_timestamp(),
                "round": round_index,
                "role": "assistant",
                "type": "tool_use",
                "tool_name": block.name,
                "tool_use_id": block.id,
                "tool_input": block.input,
            }
        )

        result = _run_tool(settings, block.name, block.input)
        result_summary = _summarize_tool_result(result)

        for filename in _extract_changed_files(result):
            if filename not in changed_files_seen:
                changed_files_seen.append(filename)
                
        trace["tool_calls"].append(
            {
                "round": round_index,
                "name": block.name,
                "input": block.input,
                "result_summary": result_summary,
            }
        )
        trace["events"].append(
            {
                "timestamp": _utc_timestamp(),
                "round": round_index,
                "role": "tool",
                "type": "tool_result",
                "tool_name": block.name,
                "tool_use_id": block.id,
                "tool_input": block.input,
                "result_summary": result_summary,
                "result": result,
            }
        )
        tool_results_content.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            }
        )
        
    return tool_results_content

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

    user_prompt = USER_PROMPT_TEMPLATE.format(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        review_output_example=render_review_output_example(),
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]
    trace = _build_trace(settings, owner, repo, pr_number, user_prompt)

    started_at = time()
    repair_attempts = 0
    changed_files_seen: list[str] = []

    try:
        for round_index in range(1, MAX_TOOL_ROUNDS + 1):
            request_kwargs: dict[str, Any] = {
                "model": settings.anthropic_model,
                "max_tokens": settings.anthropic_max_tokens,
                "temperature": settings.anthropic_temperature,
                "system": SYSTEM_PROMPT,
                "tools": build_tools(),
                "messages": messages,
            }

            message = client.messages.create(**request_kwargs)

            assistant_blocks = _assistant_blocks_to_dicts(message.content)
            messages.append({"role": "assistant", "content": assistant_blocks})
            trace["events"].append(
                {
                    "timestamp": _utc_timestamp(),
                    "round": round_index,
                    "role": "assistant",
                    "type": "assistant_message",
                    "content_blocks": assistant_blocks,
                    "usage": _extract_usage(message),
                }
            )

            tool_uses = [
                block for block in message.content if getattr(block, "type", None) == "tool_use"
            ]
            if not tool_uses:
                final_text = _extract_text_blocks(message.content)

                try:
                    review, _, repair_message = _validate_and_parse_review(final_text, changed_files_seen)
                    if repair_message and repair_attempts < MAX_VALIDATION_REPAIRS:
                        repair_attempts += 1
                        messages.append({"role": "user", "content": repair_message})
                        trace["events"].append(
                            {
                                "timestamp": _utc_timestamp(),
                                "round": round_index,
                                "role": "system",
                                "type": "validation_repair",
                                "reason": "validation_failed",
                                "content": repair_message,
                            }
                        )
                        continue
                    elif repair_message:
                        raise ValueError(repair_message)
                except Exception as error:
                    if repair_attempts < MAX_VALIDATION_REPAIRS:
                        repair_attempts += 1
                        repair_message = (
                            "Your previous response was invalid. "
                            f"Issue: {error}. "
                            "Return only one JSON object matching the requested schema. "
                            "Do not include prose or markdown fences."
                        )
                        messages.append({"role": "user", "content": repair_message})
                        trace["events"].append(
                            {
                                "timestamp": _utc_timestamp(),
                                "round": round_index,
                                "role": "system",
                                "type": "validation_repair",
                                "reason": "invalid_final_output",
                                "content": repair_message,
                            }
                        )
                        continue
                    raise

                trace["rounds"] = round_index
                trace["status"] = "success"
                trace["latency_seconds"] = round(time() - started_at, 2)
                trace["completed_at"] = _utc_timestamp()
                trace["final_output"] = review
                trace["events"].append(
                    {
                        "timestamp": _utc_timestamp(),
                        "round": round_index,
                        "role": "assistant",
                        "type": "final_output",
                        "raw_text": final_text,
                        "parsed_output": review,
                    }
                )
                return ReviewRunResult(review=review, trace=trace)

            tool_results_content = _process_tool_calls(
                tool_uses, settings, trace, round_index, changed_files_seen
            )

            messages.append({"role": "user", "content": tool_results_content})
            trace["events"].append(
                {
                    "timestamp": _utc_timestamp(),
                    "round": round_index,
                    "role": "user",
                    "type": "tool_results_message",
                    "content": tool_results_content,
                }
            )

        raise RuntimeError(
            "Tool loop exceeded the maximum number of rounds. "
            "Inspect the prompt or tool-call trace."
        )
    except Exception as error:
        trace["status"] = "error"
        trace["latency_seconds"] = round(time() - started_at, 2)
        trace["completed_at"] = _utc_timestamp()
        trace["error"] = {
            "type": error.__class__.__name__,
            "message": str(error),
        }
        raise ReviewRunError(str(error), trace) from error


def _summarize_tool_result(
    result: Union[dict[str, Any], list[dict[str, Any]]]
) -> dict[str, Any]:
    """Create a compact summary for trace logs without duplicating full payloads."""

    if isinstance(result, dict):
        return {"type": "object", "keys": sorted(result.keys())}

    filenames = [item.get("filename", "") for item in result[:3]]
    return {"type": "list", "count": len(result), "sample_filenames": filenames}

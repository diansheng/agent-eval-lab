# Architecture v1

## Goal

Build a Week 2 PR reviewer that uses MiniMax CN API plus GitHub tools to review a pull request from repository context instead of a pasted diff only.

## Problem Statement

Week 1 relied on a single LLM call over direct diff input.

That approach is limited because:

* the reviewer cannot fetch missing PR context
* the reviewer cannot choose what information to inspect
* large PRs are hard to pass in one prompt
* debugging model behavior is difficult without run logs

## Week 2 Scope

This version adds:

* GitHub PR metadata retrieval
* GitHub changed-file retrieval
* MiniMax tool calling loop
* structured JSON review output
* simple tracing

This version does not yet add:

* RAG
* persistent memory
* multi-step verification
* benchmark automation

## Components

### 1. User Input Layer

Accepts:

* `owner`
* `repo`
* `pr_number`

Optional future inputs:

* review policy
* severity threshold
* max files to inspect

### 2. Agent

The agent is responsible for:

* reading the user request
* deciding when to call tools
* consuming tool outputs
* producing the final structured review

Recommended model setup:

* MiniMax compatible API or native MiniMax API
* tool calling enabled
* JSON-first prompting

### 3. GitHub Tool Layer

The tool layer isolates external API calls from model logic.

Functions:

```python
fetch_pr(owner: str, repo: str, pr_number: int) -> dict
fetch_files(owner: str, repo: str, pr_number: int) -> list[dict]
```

Tool responsibilities:

* authenticate to GitHub
* fetch only required fields
* normalize responses
* cap payload size
* return deterministic JSON-friendly objects

### 4. Output Schema

The final review should use a stable schema, for example:

```json
{
  "summary": "short overall assessment",
  "findings": [
    {
      "severity": "high",
      "file": "src/example.py",
      "title": "Short finding title",
      "explanation": "Why this matters",
      "suggested_fix": "What to change"
    }
  ],
  "confidence": "medium"
}
```

### 5. Tracing

Tracing captures:

* run id
* prompt start
* tool call sequence
* tool arguments
* tool result summaries
* final output
* latency and token usage if available

## Data Flow

1. User submits `owner`, `repo`, and `pr_number`
2. Agent receives system prompt plus user request
3. Agent decides to call `fetch_pr()`
4. Application executes the tool and appends the result to history
5. Agent decides to call `fetch_files()`
6. Application executes the tool and appends the result to history
7. Agent analyzes the gathered context
8. Agent returns structured review JSON
9. Application stores a trace/log for the run

## Message Loop Design

The application must preserve the full assistant response between turns during tool use.

That means:

* append the entire assistant tool-call message back into history
* append tool results in the format expected by the MiniMax API mode you selected
* continue until the model emits the final answer without more tool calls

## Tool Contracts

### `fetch_pr()`

Expected return shape:

```json
{
  "number": 123,
  "title": "Fix auth edge case",
  "body": "PR description",
  "state": "open",
  "base_branch": "main",
  "head_branch": "fix/auth-edge-case",
  "author": "alice",
  "url": "https://github.com/org/repo/pull/123"
}
```

### `fetch_files()`

Expected return shape:

```json
[
  {
    "filename": "src/auth.py",
    "status": "modified",
    "additions": 12,
    "deletions": 3,
    "changes": 15,
    "patch": "@@ -10,6 +10,8 @@ ..."
  }
]
```

## Guardrails

Add these guardrails in Week 2:

* limit number of files returned
* truncate oversized patch content
* handle missing patch fields
* fail clearly on missing GitHub token
* fail clearly on nonexistent PRs
* instruct the model not to invent unseen code

## Known Limitations

Current limitations:

* no verification step for findings
* no retrieval over historical docs
* no task memory across runs
* large PRs may still be partially truncated
* review quality depends on prompt and returned patch quality

## Testing Plan

Run at least:

* 1 small PR
* 1 medium PR
* 1 awkward PR with partial or missing patch data

Validate:

* tools are actually called
* final JSON is valid
* file references are real
* traces are saved

## Next Step

Week 3 should add:

* explicit multi-step workflow
* state object
* verification pass before final report

## Completion Checklist

Mark complete before ending Week 2:

* [ ] `fetch_pr()` works
* [ ] `fetch_files()` works
* [ ] MiniMax tool call loop works
* [ ] final JSON schema is stable
* [ ] traces are saved locally
* [ ] 3 test PR runs completed
* [ ] architecture note reviewed and updated

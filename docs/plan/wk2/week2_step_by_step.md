# Week 2 Step-by-Step Guide

## Objective

Turn the Week 1 single-call reviewer into a MiniMax-powered agent that can call GitHub tools, inspect PR context, and return a structured review.

## This Week's Scope

Build only these pieces:

* `fetch_pr(owner, repo, pr_number)`
* `fetch_files(owner, repo, pr_number)`
* agent loop with MiniMax tool calling
* basic tracing / run logging
* `wk2/architecture_v1.md`

Do not add RAG, persistent memory, or a full planner this week.

## End-of-Week Done Criteria

You are done when all of these are true:

* agent accepts `owner`, `repo`, and `pr_number`
* MiniMax chooses or is allowed to call the GitHub tools
* tool outputs are fed back into the model correctly
* final review is valid JSON
* at least 3 PRs have been tested end to end
* `wk2/architecture_v1.md` is filled in

## Recommended Folder Shape

Inside `agent-eval-lab/`, keep the layout simple:

```text
agent-eval-lab/
  app/
    main.py
    agent.py
    config.py
    schemas.py
    tools/
      github_tools.py
    tracing.py
  tests/
  docs/
  README.md
```

If your Week 1 files already exist elsewhere, keep them and only add the missing pieces.

## Session 1 - Read And Frame The Problem

Time budget: `1.5h`

Read:

* MiniMax quick start
* MiniMax compatible API docs
* MiniMax tool use / interleaved thinking docs

Write a short scratch note with answers to:

* how tools are defined
* what tool call arguments look like
* how tool responses are appended back into conversation history
* what full assistant response must be preserved between turns

Deliverable for this session:

* a `10` line note in your local notebook or scratch file

## Session 2 - Build The Tool Layer First

Time budget: `2h`

Create plain Python functions before wiring the model:

```python
def fetch_pr(owner: str, repo: str, pr_number: int) -> dict:
    ...

def fetch_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    ...
```

Return only model-useful fields.

For `fetch_pr()`:

* `number`
* `title`
* `body`
* `state`
* `base_branch`
* `head_branch`
* `author`
* `url`

For `fetch_files()`:

* `filename`
* `status`
* `additions`
* `deletions`
* `changes`
* `patch`

Rules:

* cap returned files to a safe number, for example `20`
* truncate oversized patches
* return clean dictionaries, not raw HTTP payloads

Deliverable for this session:

* GitHub tool module with manual test calls working

## Session 3 - Wire MiniMax Tool Calling

Time budget: `2h`

Add:

* MiniMax client setup
* tool schema definitions
* tool execution loop
* final review generation

Minimal loop:

1. send user request plus system instruction
2. if the model asks for a tool, execute it
3. append the full assistant response to history
4. append the tool result to history
5. repeat until the model returns the final review

Important implementation note:

* preserve the full assistant response object across turns, especially tool call metadata and any reasoning fields required by the MiniMax format you choose

System prompt goals:

* inspect PR metadata first
* inspect changed files before judging
* cite filenames in findings
* do not invent files or code not returned by tools
* output valid JSON only

Deliverable for this session:

* one end-to-end run from PR reference to JSON review

## Session 4 - Add Tracing And Run Logs

Time budget: `1.5h`

You do not need a heavyweight tracing product this week.

At minimum, log:

* run id
* model name
* tool call order
* tool arguments
* tool result summary
* final latency
* token usage if available

Save traces as JSON or markdown under a local folder such as:

```text
agent-eval-lab/logs/
```

Check after each run:

* did the model call the right tool first
* did it retry unnecessarily
* did it misuse arguments
* did it mention files that were never fetched

Deliverable for this session:

* trace artifact for at least one successful run

## Session 5 - Test, Tighten, And Write The Deliverable

Time budget: `3h`

Run 3 focused scenarios:

* small PR with `1-3` files
* medium PR with `5-15` files
* awkward PR with missing patch content or large diffs

For each run, record:

* whether tool calls succeeded
* whether output schema was valid
* whether findings referenced real files
* whether there were hallucinations or repeated calls

Then complete:

* `wk2/architecture_v1.md`

Deliverable for this session:

* architecture note completed
* code cleaned up
* week ready to commit

## Suggested Commit Sequence

Keep the same commit names from the learning plan:

1. `tool layer`
2. `github integration`
3. `tracing`

## Implementation Checklist

Use this checklist while working:

* env vars load correctly
* GitHub auth works
* `fetch_pr()` returns stable keys
* `fetch_files()` handles missing patch values
* tool schema matches function parameters
* full assistant message is appended back into history
* final output matches your JSON schema
* traces are saved for at least 3 runs

## Common Failure Modes

Watch for these first:

* tool arguments are malformed JSON
* assistant message history is incomplete between turns
* file patches are too large and blow up context
* final answer ignores tool outputs and hallucinates
* review output breaks JSON format

## What To Ignore This Week

Do not expand scope into:

* retrieval
* memory persistence
* planner abstractions
* benchmark suite
* prompt tuning rabbit holes

## Final Output For Week 2

By the end of the week, you should have:

* working MiniMax-based tool-calling reviewer
* GitHub tool layer
* simple trace logs
* `wk2/architecture_v1.md`
* 3 clean commits

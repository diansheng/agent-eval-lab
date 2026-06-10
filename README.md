# agent-eval-lab

Week 1 baseline project: a CLI that reviews a GitHub PR diff with one LLM call and returns structured JSON.

Week 2 adds a tool layer that can fetch GitHub PR metadata and changed files, then let MiniMax review a real pull request through the Anthropic-compatible API.

## Why This Version Exists

This is intentionally not a full agent yet.

- One CLI
- One diff input
- One model call
- One structured JSON output
- No tools
- No retrieval
- No orchestration loop

That gives you a clean baseline before you add agentic behavior later.

## Setup

```bash
cd "/home/alchemist/code/agent learning/agent-eval-lab"

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
```

Then edit `.env` and set one provider.

### Option A: MiniMax Token Plan via Anthropic-compatible API

```env
LLM_PROVIDER=minimax_anthropic
MINIMAX_API_KEY=your_minimax_key_here
MINIMAX_ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
MINIMAX_ANTHROPIC_MODEL=MiniMax-M3
```

### Option B: MiniMax via OpenAI-compatible API

```env
LLM_PROVIDER=minimax_openai
MINIMAX_API_KEY=your_minimax_key_here
MINIMAX_OPENAI_BASE_URL=https://api.minimaxi.io/v1
MINIMAX_OPENAI_MODEL=MiniMax-M3
```

### Option C: OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
```

## Run

With the default provider from `.env`:

```bash
python main.py --diff-file sample_diff.patch
```

Override the provider on the command line:

```bash
python main.py --provider minimax_anthropic --diff-file sample_diff.patch
python main.py --provider minimax_openai --diff-file sample_diff.patch
python main.py --provider openai --diff-file sample_diff.patch
```

Pipe a diff through stdin:

```bash
cat sample_diff.patch | python main.py --provider minimax_anthropic
```

Override the model:

```bash
python main.py --provider minimax_openai --model MiniMax-M2.1 --diff-file sample_diff.patch
python main.py --provider minimax_anthropic --model MiniMax-M3 --diff-file sample_diff.patch
```

Save the parsed JSON to a file:

```bash
python main.py --diff-file sample_diff.patch --output-file outputs/review.json
```

## Week 2 Setup

Add GitHub settings to `.env`:

```env
GITHUB_TOKEN=your_github_token_here
GITHUB_API_BASE=https://api.github.com
MAX_PR_FILES=20
MAX_PATCH_CHARS=4000
```

Smoke test the GitHub tool layer first:

```bash
python3 scripts/test_github_tools.py --owner microsoft --repo vscode --pr-number 320628
```

Review a real GitHub PR with the Week 2 tool loop:

```bash
python3 scripts/review_github_pr.py --owner microsoft --repo vscode --pr-number 320628
```

Save the review JSON and basic trace metadata:

```bash
python3 scripts/review_github_pr.py \
  --owner microsoft \
  --repo vscode \
  --pr-number 320628 \
  --output-file outputs/pr_review.json \
  --trace-file logs/pr_review_trace.json
```

The Week 2 path currently uses the MiniMax Anthropic-compatible setup from `.env`.

## Output Shape

The CLI prints a JSON object with:

- `summary`
- `findings`
- `confidence`
- `needs_manual_review`

Each finding contains:

- `severity`
- `title`
- `file`
- `comment`

If the model returns invalid JSON or misses required keys, the CLI exits with a clear error instead of printing partial output.

## Week 1 Evaluation

Use the sample diffs in `samples/` to probe different failure modes:

- `samples/01_obvious_bug.patch`: should catch a clear correctness regression
- `samples/02_no_issue_refactor.patch`: should ideally return few or no findings
- `samples/03_auth_edge_case.patch`: tests whether the reviewer notices permission changes
- `samples/04_off_by_one.patch`: tests whether it catches a pagination bug
- `samples/05_swallowed_error.patch`: tests whether it notices swallowed exceptions and false success states

Run them one by one:

```bash
python main.py --diff-file samples/01_obvious_bug.patch --output-file outputs/01.json
python main.py --diff-file samples/02_no_issue_refactor.patch --output-file outputs/02.json
python main.py --diff-file samples/03_auth_edge_case.patch --output-file outputs/03.json
python main.py --diff-file samples/04_off_by_one.patch --output-file outputs/04.json
python main.py --diff-file samples/05_swallowed_error.patch --output-file outputs/05.json
```

For each run, note:

- Did it miss an obvious bug?
- Did it hallucinate a problem on the refactor-only patch?
- Did the finding titles and comments stay specific instead of generic?
- Did the JSON shape remain stable and parseable?
- Did `needs_manual_review` feel justified?

## MiniMax Notes

MiniMax exposes more than one compatibility layer, and your account or product may prefer one over the other.

- `minimax_anthropic`
- SDK: `anthropic`
- Base URL: `https://api.minimaxi.com/anthropic`
- Good default for Token Plan docs: `MiniMax-M3`

- `minimax_openai`
- SDK: `openai`
- Base URL: `https://api.minimaxi.io/v1`
- Good default model: `MiniMax-M3`

Useful docs:

- [MiniMax Token Plan Quickstart](https://platform.minimaxi.com/docs/token-plan/quickstart)
- [MiniMax Compatible OpenAI API](https://platform.minimax.io/docs/api-reference/text-openai-api)
- [MiniMax Text Chat Guide](https://platform.minimax.io/docs/guides/text-chat)

## Week 1 Goal

Get this working end to end, then observe:

- Does the model hallucinate?
- Does it miss obvious bugs?
- Does it overfocus on style instead of correctness?
- What output shape would be easier to evaluate later?
- What single prompt change improves the worst failure you saw?

## Week 2 Goal

Get the tool-calling reviewer working end to end, then observe:

- Does the model call `fetch_pr` and `fetch_files` in a sensible order?
- Does it cite real files from the tool output?
- Does it get stuck in repeated tool calls?
- Does the final JSON stay stable after tool use?
- What failures should be traced and fixed in Week 3?

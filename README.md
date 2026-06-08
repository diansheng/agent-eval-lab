# agent-eval-lab

Week 1 baseline project: a CLI that reviews a GitHub PR diff with one LLM call and returns structured JSON.

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

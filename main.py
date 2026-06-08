import argparse
import json
import os
import sys

import anthropic
from dotenv import load_dotenv
from openai import OpenAI


SYSTEM_PROMPT = """You are a careful code reviewer.
Review the provided GitHub PR diff.
Focus on:
- likely bugs
- correctness issues
- risky changes
- missing edge cases

Rules:
- Be concise.
- Do not invent context not present in the diff.
- If you are unsure, say so.
- Return only valid JSON that matches the requested schema.
"""


USER_PROMPT_TEMPLATE = """Review this GitHub PR diff and produce review comments.

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
- Use only information present in the diff.
- Sort findings by severity (high first medium second low last).

PR diff:
```diff
{diff_text}
```
"""


PROVIDER_CHOICES = ("openai", "minimax_openai", "minimax_anthropic")


def read_diff(diff_file: str | None) -> str:
    if diff_file:
        with open(diff_file, "r", encoding="utf-8") as file:
            return file.read()

    if not sys.stdin.isatty():
        return sys.stdin.read()

    raise ValueError("Provide --diff-file or pipe a diff through stdin.")


def get_provider_config(provider: str) -> tuple[str, str, str]:
    normalized = provider.lower()

    if normalized == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        return api_key, base_url, model

    if normalized == "minimax_openai":
        api_key = os.getenv("MINIMAX_API_KEY", "")
        base_url = os.getenv(
            "MINIMAX_OPENAI_BASE_URL", "https://api.minimaxi.io/v1"
        )
        model = os.getenv("MINIMAX_OPENAI_MODEL", "MiniMax-M3")
        return api_key, base_url, model

    if normalized == "minimax_anthropic":
        api_key = os.getenv("MINIMAX_API_KEY", "")
        base_url = os.getenv(
            "MINIMAX_ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic"
        )
        model = os.getenv("MINIMAX_ANTHROPIC_MODEL", "MiniMax-M3")
        return api_key, base_url, model

    raise ValueError(
        "Unsupported provider. Use one of: "
        + ", ".join(f"'{choice}'" for choice in PROVIDER_CHOICES)
    )


def validate_api_key(provider: str, api_key: str) -> None:
    if not api_key:
        raise ValueError(
            f"Missing API key for provider '{provider}'. Check your .env configuration."
        )


def parse_review_json(review_text: str) -> dict:
    cleaned = review_text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    return json.loads(cleaned)


def review_with_openai_client(
    api_key: str, base_url: str, model: str, diff_text: str
) -> dict:
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(diff_text=diff_text),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    review_text = response.choices[0].message.content or "{}"
    return parse_review_json(review_text)


def review_with_anthropic_client(
    api_key: str, base_url: str, model: str, diff_text: str
) -> dict:
    client = anthropic.Anthropic(api_key=api_key, base_url=base_url)

    message = client.messages.create(
        model=model,
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(diff_text=diff_text),
            }
        ],
    )

    text_blocks = [
        block.text for block in message.content if getattr(block, "type", None) == "text"
    ]
    return parse_review_json("\n".join(text_blocks))


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Review a GitHub PR diff with one LLM call."
    )
    parser.add_argument("--diff-file", help="Path to a diff/patch file")
    parser.add_argument(
        "--provider",
        default=os.getenv("LLM_PROVIDER", "minimax_anthropic"),
        help=(
            "LLM provider to use: "
            + ", ".join(PROVIDER_CHOICES)
        ),
    )
    parser.add_argument(
        "--model",
        help="Optional model override. If omitted, uses the provider default from .env.",
    )
    args = parser.parse_args()

    diff_text = read_diff(args.diff_file)

    api_key, base_url, default_model = get_provider_config(args.provider)
    model = args.model or default_model
    validate_api_key(args.provider, api_key)

    if args.provider == "minimax_anthropic":
        review_json = review_with_anthropic_client(
            api_key=api_key,
            base_url=base_url,
            model=model,
            diff_text=diff_text,
        )
    else:
        review_json = review_with_openai_client(
            api_key=api_key,
            base_url=base_url,
            model=model,
            diff_text=diff_text,
        )

    print("\n=== Provider ===")
    print(args.provider)
    print("\n=== Model ===")
    print(model)
    print("\n=== Review JSON ===\n")
    print(json.dumps(review_json, indent=2))


if __name__ == "__main__":
    main()

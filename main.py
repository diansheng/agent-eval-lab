import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv
from openai import OpenAI

from app.review_schema import (
    ReviewFormatError,
    parse_review_json,
    render_review_output_example,
)


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
{review_output_example}

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


def read_diff(diff_file: Optional[str]) -> str:
    if diff_file:
        path = Path(diff_file)
        if not path.exists():
            raise ValueError(f"Diff file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Diff path is not a file: {path}")

        diff_text = path.read_text(encoding="utf-8")
        if not diff_text.strip():
            raise ValueError(f"Diff file is empty: {path}")
        return diff_text

    if not sys.stdin.isatty():
        diff_text = sys.stdin.read()
        if not diff_text.strip():
            raise ValueError("Received empty stdin input. Pipe a non-empty diff instead.")
        return diff_text

    raise ValueError(
        "No diff provided. Use --diff-file PATH or pipe a diff through stdin."
    )


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
            f"Missing API key for provider '{provider}'. "
            "Set it in your shell or .env before running the CLI."
        )


def write_output(review_json: dict, output_file: Optional[str]) -> None:
    rendered = json.dumps(review_json, indent=2)

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)

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
                "content": USER_PROMPT_TEMPLATE.format(
                    diff_text=diff_text,
                    review_output_example=render_review_output_example(),
                ),
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
                "content": USER_PROMPT_TEMPLATE.format(
                    diff_text=diff_text,
                    review_output_example=render_review_output_example(),
                ),
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
    parser.add_argument(
        "--output-file",
        help="Optional path to save the parsed JSON review output.",
    )
    args = parser.parse_args()

    try:
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

        print(f"Provider: {args.provider}", file=sys.stderr)
        print(f"Model: {model}", file=sys.stderr)
        if args.output_file:
            print(f"Output file: {args.output_file}", file=sys.stderr)

        write_output(review_json, args.output_file)
    except (ValueError, ReviewFormatError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Simple container for app configuration loaded from environment variables."""

    github_token: str
    github_api_base: str
    anthropic_api_key: str
    anthropic_base_url: str
    anthropic_model: str
    anthropic_max_tokens: int
    anthropic_temperature: float
    max_pr_files: int
    max_patch_chars: int


def load_settings() -> Settings:
    """Load settings from `.env` and return them as one object."""

    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    return Settings(
        github_token=os.getenv("GITHUB_TOKEN", "").strip(),
        github_api_base=os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/"),
        anthropic_api_key=os.getenv("MINIMAX_API_KEY", "").strip(),
        anthropic_base_url=os.getenv(
            "MINIMAX_ANTHROPIC_BASE_URL",
            "https://api.minimaxi.com/anthropic",
        ).rstrip("/"),
        anthropic_model=os.getenv("MINIMAX_ANTHROPIC_MODEL", "MiniMax-M3").strip(),
        anthropic_max_tokens=int(os.getenv("MINIMAX_ANTHROPIC_MAX_TOKENS", "1600")),
        anthropic_temperature=float(os.getenv("MINIMAX_ANTHROPIC_TEMPERATURE", "0.0")),
        max_pr_files=int(os.getenv("MAX_PR_FILES", "20")),
        max_patch_chars=int(os.getenv("MAX_PATCH_CHARS", "4000")),
    )

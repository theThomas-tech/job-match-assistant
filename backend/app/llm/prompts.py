"""Prompts live as versioned files in app/prompts/, so every change is visible in git history."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def load_prompt(version: str) -> str:
    """Load a prompt by version name, e.g. "profile_v1" -> app/prompts/profile_v1.md"""
    return (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8").strip()

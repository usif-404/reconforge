"""
Thin LLM client wrapper. Swap providers by changing env vars — same idea as
Strix's provider abstraction (STRIX_LLM / LLM_API_KEY / LLM_API_BASE), but
here it's just calling the Anthropic Messages API directly since that's
the AI you'll be running this against.
"""
from __future__ import annotations

import json
import os

import anthropic

DEFAULT_MODEL = os.environ.get("RECONFORGE_MODEL", "claude-sonnet-4-6")


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    def complete(self, system_prompt: str, user_content: str, max_tokens: int = 2000) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    def complete_json(self, system_prompt: str, user_content: str, max_tokens: int = 2000) -> dict:
        """Appends a strict JSON-only instruction; caller should still try/except the parse."""
        strict_system = system_prompt + "\n\nRespond ONLY with valid JSON. No markdown fences, no preamble."
        raw = self.complete(strict_system, user_content, max_tokens=max_tokens)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)

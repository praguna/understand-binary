"""LLM client for Understand-Binary. Defaults to Gemini via OpenAI-compatible API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from openai import OpenAI


_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "model": "gpt-4o",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "env_key": "",
        "model": "llama3",
    },
}


@dataclass
class LLMClient:
    provider: str = "gemini"
    model: str = ""
    api_key: str = ""
    base_url: str = ""

    def __post_init__(self) -> None:
        defaults = _PROVIDER_DEFAULTS.get(self.provider, _PROVIDER_DEFAULTS["gemini"])
        if not self.model:
            self.model = defaults["model"]
        if not self.base_url:
            self.base_url = defaults["base_url"]
        if not self.api_key:
            env_key = defaults.get("env_key", "")
            self.api_key = os.environ.get(env_key, "not-needed") if env_key else "not-needed"

        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def chat(self, messages: list[dict[str, str]], json_mode: bool = False) -> str:
        """Send a chat completion request and return the response text."""
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

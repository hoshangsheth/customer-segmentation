"""
The contract every LLM provider implements: a system prompt and a user message in, a JSON object
matching a schema out. Nothing outside llm/providers/ imports a vendor SDK, so switching provider
is a settings change.

To add a provider: write a class with `name` and `complete_json`, then register it in
llm/providers/__init__.py.
"""

from typing import Any, Protocol


class LLMError(RuntimeError):
    """The provider failed or returned something unusable. Callers fall back to rule-based text."""


class LLMNotConfigured(LLMError):
    """No API key, unknown provider or missing SDK."""


class LLMProvider(Protocol):
    name: str
    model: str

    def complete_json(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]: ...

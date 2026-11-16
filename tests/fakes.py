"""Test doubles for the LLM provider."""

from typing import Any

from customer_segmentation.llm.contracts import LLMError


class FakeLLM:
    name = "fake"
    model = "fake-model"

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def complete_json(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"system": system, "user": user, "schema": schema})
        if "actions" in schema["properties"]:
            return {
                "headline": "Fake headline.",
                "summary": "Fake brief.",
                "actions": [{"segment": "S", "audience": "10", "channel": "email", "message": "M", "why": "W"}],
                "budget_note": "Fake budget.",
                "watch_outs": [],
            }
        if "campaigns" in schema["properties"]:
            return {
                "persona": "Fake persona.",
                "motivations": ["quality"],
                "campaigns": [{"title": "T", "channel": "email", "offer": "O", "rationale": "R"}],
                "watch_outs": [],
            }
        return {"summary": "Fake summary.", "next_best_action": "Fake action."}


class FailingLLM:
    name = "failing"
    model = "broken"

    def complete_json(self, **_: Any) -> dict[str, Any]:
        raise LLMError("boom")

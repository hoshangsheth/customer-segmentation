"""Google Gemini adapter (`google-genai` SDK). Config: GEMINI_API_KEY, LLM_MODEL."""

import json
from typing import Any

from customer_segmentation.llm.contracts import LLMError, LLMNotConfigured

DEFAULT_MODEL = "gemini-3.8-flash"


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "", timeout_s: float = 30.0):
        if not api_key:
            raise LLMNotConfigured("set GEMINI_API_KEY to enable AI insights")
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:  # pragma: no cover - the SDK is a declared dependency
            raise LLMNotConfigured("install google-genai") from e
        self._types = types
        self.model = model or DEFAULT_MODEL
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))

    def complete_json(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        config = self._types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.4,
        )
        try:
            resp = self.client.models.generate_content(model=self.model, contents=user, config=config)
            return json.loads(resp.text or "")
        except json.JSONDecodeError as e:
            raise LLMError("Gemini returned invalid JSON") from e
        except Exception as e:  # SDK and network errors all degrade the same way
            raise LLMError(f"Gemini request failed: {type(e).__name__}") from e

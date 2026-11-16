"""
Google Gemini adapter (`google-genai` SDK). Config: GEMINI_API_KEY, LLM_MODEL, LLM_FALLBACK_MODEL.

If the main model fails (timeout, overload, server error), the request is retried once on the
fallback model before the caller drops back to rule-based text.
"""

import json
import logging
from typing import Any

from customer_segmentation.llm.contracts import LLMError, LLMNotConfigured

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_FALLBACK = "gemini-3.5-flash"


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "", timeout_s: float = 30.0, fallback_model: str | None = None):
        if not api_key:
            raise LLMNotConfigured("set GEMINI_API_KEY to enable AI insights")
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:  # pragma: no cover - the SDK is a declared dependency
            raise LLMNotConfigured("install google-genai") from e
        self._types = types
        self.model = model or DEFAULT_MODEL
        fallback = DEFAULT_FALLBACK if fallback_model is None else fallback_model
        self.fallback_model = fallback if fallback and fallback != self.model else ""
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))

    def _call(self, model: str, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        config = self._types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.4,
        )
        try:
            resp = self.client.models.generate_content(model=model, contents=user, config=config)
            return json.loads(resp.text or "")
        except json.JSONDecodeError as e:
            raise LLMError(f"{model} returned invalid JSON") from e
        except Exception as e:  # SDK and network errors all degrade the same way
            raise LLMError(f"{model} request failed: {type(e).__name__}") from e

    def complete_json(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.last_model = self.model
        try:
            return self._call(self.model, system, user, schema)
        except LLMError as first:
            if not self.fallback_model:
                raise
            log.warning("%s; retrying on %s", first, self.fallback_model)
            self.last_model = self.fallback_model
            return self._call(self.fallback_model, system, user, schema)

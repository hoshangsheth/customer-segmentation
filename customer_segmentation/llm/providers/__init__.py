"""Registry of provider names to factories. Add a provider here to make it selectable."""

from collections.abc import Callable

from customer_segmentation.config import Settings
from customer_segmentation.llm.contracts import LLMProvider
from customer_segmentation.llm.providers.gemini import GeminiProvider

PROVIDERS: dict[str, Callable[[Settings], LLMProvider]] = {
    "gemini": lambda s: GeminiProvider(s.gemini_api_key, s.llm_model, s.llm_timeout_s),
}

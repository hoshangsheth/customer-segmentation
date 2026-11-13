"""Builds the configured provider, or returns None so the app runs without AI features."""

import logging

from customer_segmentation.config import Settings
from customer_segmentation.llm.contracts import LLMNotConfigured, LLMProvider
from customer_segmentation.llm.providers import PROVIDERS

log = logging.getLogger(__name__)


def build_provider(settings: Settings) -> LLMProvider | None:
    name = settings.llm_provider.strip().lower()
    factory = PROVIDERS.get(name)
    if factory is None:
        log.warning("unknown LLM_PROVIDER %r; AI insights disabled", name)
        return None
    try:
        return factory(settings)
    except LLMNotConfigured as e:
        log.info("AI insights disabled: %s", e)
        return None

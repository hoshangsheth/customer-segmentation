from customer_segmentation.config import Settings
from customer_segmentation.llm.factory import build_provider
from customer_segmentation.llm.insights import InsightsService
from tests.fakes import FailingLLM, FakeLLM

SEGMENT = {"segment_id": 0, "name": "High-value loyalists", "tagline": "Top spenders.", "traits": ["2.0x spend"]}
SCORE = {
    "probability": 0.42,
    "base_rate": 0.15,
    "reasons": [
        {"label": "Earlier campaigns accepted", "shap": 1.2},
        {"label": "Days since last purchase", "shap": -0.4},
    ],
}


def test_no_key_means_no_provider():
    assert build_provider(Settings(_env_file=None, gemini_api_key="")) is None
    assert build_provider(Settings(_env_file=None, llm_provider="nope")) is None


def test_gemini_provider_is_built_with_a_key():
    provider = build_provider(Settings(_env_file=None, gemini_api_key="test-key", llm_model="m"))
    assert provider is not None and provider.name == "gemini" and provider.model == "m"


def test_persona_from_llm_is_cached():
    llm = FakeLLM()
    svc = InsightsService(llm, "v1")
    first = svc.segment_persona(SEGMENT, {"monetary": 600})
    second = svc.segment_persona(SEGMENT, {"monetary": 600})
    assert first["source"] == "llm" and first == second
    assert len(llm.calls) == 1
    assert "High-value loyalists" in llm.calls[0]["user"]  # the computed profile is in the prompt


def test_fallbacks_when_llm_missing_or_failing():
    for provider in (None, FailingLLM()):
        svc = InsightsService(provider, "v1")
        persona = svc.segment_persona(SEGMENT, {})
        assert persona["source"] == "rule-based" and persona["campaigns"]
        assert "Top spenders." in persona["persona"]
        explanation = svc.explain_score(SCORE)
        assert explanation["source"] == "rule-based"
        assert "42%" in explanation["summary"] and "earlier campaigns accepted" in explanation["summary"]
        assert "Include" in explanation["next_best_action"]


class _StubModels:
    def __init__(self, text=None, error=None):
        self.text, self.error, self.kwargs = text, error, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return type("Resp", (), {"text": self.text})()


def _gemini_with(models):
    provider = build_provider(Settings(_env_file=None, gemini_api_key="test-key"))
    provider.client = type("Client", (), {"models": models})()
    return provider


def test_gemini_parses_json_and_sends_schema():
    models = _StubModels(text='{"summary": "s", "next_best_action": "a"}')
    out = _gemini_with(models).complete_json(system="sys", user="u", schema={"type": "object"})
    assert out == {"summary": "s", "next_best_action": "a"}
    assert models.kwargs["contents"] == "u"
    assert models.kwargs["config"].response_json_schema == {"type": "object"}


def test_gemini_errors_become_llm_errors():
    import pytest

    from customer_segmentation.llm.contracts import LLMError

    for models in (_StubModels(text="not json"), _StubModels(error=OSError("offline"))):
        with pytest.raises(LLMError):
            _gemini_with(models).complete_json(system="s", user="u", schema={})

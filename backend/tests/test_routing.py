from types import SimpleNamespace

import pytest

from backend.app.router import router
from backend.app.router.model_registry import get_model_for_tier
from backend.app.providers import provider_registry
from backend.app.services.pipeline import PromptGuardPipeline


class FakeClassifier:
    classes_ = ["HIGH", "LOW", "MEDIUM"]

    def __init__(self, probabilities):
        self.probabilities = probabilities

    def predict_proba(self, _texts):
        return [self.probabilities]


@pytest.mark.parametrize("text,tier", [
    ("What is the capital of France?", "LOW"),
    ("Calculate 12 times 8", "MEDIUM"),
    ("Summarize this short document", "MEDIUM"),
    ("Analyze the multi-step tradeoffs and debug this distributed system", "HIGH"),
])
def test_classifier_tier_selection(monkeypatch, text, tier):
    probabilities = {"LOW": [0.05, 0.9, 0.05], "MEDIUM": [0.05, 0.05, 0.9], "HIGH": [0.9, 0.05, 0.05]}[tier]
    monkeypatch.setattr(router, "_load_classifier", lambda: FakeClassifier(probabilities))
    result = router.select_tier({"routing_text": text})
    assert result["tier"] == tier
    assert result["model"] == get_model_for_tier(tier)
    assert result["confidence"] == pytest.approx(0.9)


def test_large_document_forces_high(monkeypatch):
    monkeypatch.setattr(router, "_load_classifier", lambda: FakeClassifier([0.01, 0.98, 0.01]))
    assert router.select_tier({"routing_text": "simple"}, 1_048_576)["tier"] == "HIGH"


def test_uncertain_or_missing_model_falls_back_high(monkeypatch):
    monkeypatch.setattr(router, "_load_classifier", lambda: FakeClassifier([0.4, 0.3, 0.3]))
    assert router.select_tier({"routing_text": "unclear"})["tier"] == "HIGH"
    monkeypatch.setattr(router, "_load_classifier", lambda: None)
    assert router.select_tier({"routing_text": "simple"})["tier"] == "HIGH"


@pytest.mark.parametrize("tier,klass", [
    ("LOW", provider_registry.GroqProvider),
    ("MEDIUM", provider_registry.GeminiProvider),
    ("HIGH", provider_registry.OpenAIProvider),
])
def test_provider_selected_by_tier(tier, klass):
    assert isinstance(provider_registry.provider_for_tier(tier), klass)


def test_missing_provider_key_errors_without_fallback(monkeypatch):
    monkeypatch.setattr(provider_registry, "GROQ_API_KEY", None)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        provider_registry.GroqProvider().generate("m", "p", "")
    monkeypatch.setattr(provider_registry, "GEMINI_API_KEY", None)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        provider_registry.GeminiProvider().generate("m", "p", "")
    monkeypatch.setattr("backend.app.providers.openai_provider.OPENAI_API_KEY", None)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        provider_registry.OpenAIProvider().generate("m", "p", "")


def test_security_block_bypasses_cache_and_generation():
    pipeline = PromptGuardPipeline.__new__(PromptGuardPipeline)
    pipeline.security = SimpleNamespace(scan=lambda _text: {"blocked": True, "status": "blocked"})
    pipeline.cache = SimpleNamespace(lookup=lambda _text: pytest.fail("cache should not run"))
    pipeline.analyzer = SimpleNamespace(analyze=lambda _text: pytest.fail("analyzer should not run"))
    result = pipeline.process("unsafe", "", lambda *_: None)
    assert result["status"] == "blocked"


def test_cache_hit_bypasses_analysis_routing_and_generation():
    pipeline = PromptGuardPipeline.__new__(PromptGuardPipeline)
    pipeline.security = SimpleNamespace(scan=lambda _text: {"blocked": False, "status": "safe"})
    pipeline.cache = SimpleNamespace(lookup=lambda _text: {"similarity": 1.0, "response": "cached"})
    pipeline.analyzer = SimpleNamespace(analyze=lambda _text: pytest.fail("analysis should not run"))
    result = pipeline.process("question", "", lambda *_: None)
    assert result["response"] == "cached"
    assert result["cache"]["status"] == "hit"


def test_provider_error_surfaces_without_switching(monkeypatch):
    class Failed:
        def generate(self, **_kwargs):
            raise RuntimeError("provider unavailable")
    monkeypatch.setattr(provider_registry, "provider_for_tier", lambda _tier: Failed())
    with pytest.raises(RuntimeError, match="provider unavailable"):
        provider_registry.provider_for_tier("LOW").generate(model="m", user_prompt="p", content="")

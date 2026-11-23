import pytest
from app.modules.ai.providers import AIProvider, MockProvider, get_provider
from app.modules.ai.schemas import SummaryResult
from app.shared.config import settings


def test_mock_return_the_shape():
    result = MockProvider().summarize("clean water project in Lagos")

    #same shape as every provider, and honest about being fake
    assert isinstance(result, SummaryResult)
    assert result.is_mock is True

def test_mock_truncates_long_text():
    result = MockProvider().summarize("x" * 300)
    assert result.summary == "[DEMO WORK] " + "x" * 100

def test_incomplete_provider():
    #forgot to write summarize()
    class Broken(AIProvider):
        pass
    with pytest.raises(TypeError):
        Broken()

def test_get_provider_mock_when_no_key(monkeypatch):
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    assert isinstance(get_provider(), MockProvider)

import pytest
from app.modules.ai.providers import AIProvider, MockProvider, RealProvider, get_provider
from app.modules.ai.schemas import SummaryResult
from app.shared.config import settings


def test_mock_return_the_shape():
    result = MockProvider().summarize("clean water project in Lagos")

    #same shape as every provider, and honest about being fake
    assert isinstance(result, SummaryResult)
    assert result.is_mock is True

def test_incomplete_provider():
    #forgot to write summarize()
    class Broken(AIProvider):
        pass
    with pytest.raises(TypeError):
        Broken()

def test_real_provider_not_implemented_yet():
    #arrange

    provider = RealProvider(api_key="test-key", model="test-model")

    # Act plus Assert calling it must raise, not silently return junk
    with pytest.raises(NotImplementedError):
        provider.summarize("sample text")

def test_get_provider_mock_when_no_key(monkeypatch):
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    assert isinstance(get_provider(), MockProvider)

def test_get_provider_returns_real_when_keys_exist(monkeypatch):
    monkeypatch.setattr(settings, "AI_API_KEY", "fake-key-for-test")
    assert isinstance(get_provider(), RealProvider)
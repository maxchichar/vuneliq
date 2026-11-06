import pytest

from app.modules.ai.providers import AIProvider
from app.modules.ai.schemas import SummaryResult
from app.modules.ai.services import AIIinputError, summarize_impact
from app.shared.config import settings



class spyProvider(AIProvider):
    """ A fake provider that records whether it was called"""
    def __init__(self):
        self.called = False
    def summarize(self, text: str) -> SummaryResult:
        self.called = True
        return SummaryResult(summary="ok", is_mock=True)
    
@pytest.fixture
def spy(monkeypatch):
    provider = spyProvider()
    monkeypatch.setattr("app.modules.ai.services.get_provider", lambda: provider)
    return provider
@pytest.mark.parametrize("bad_text", ["", "   ", "\n\n\t"])
def test_empty_text_is_rejected_before_calling_ai(spy, bad_text):
    with pytest.raises(AIIinputError):
        summarize_impact(bad_text)
    assert spy.called is False

def test_too_long(spy, monkeypatch):
    monkeypatch.setattr(settings, "AI_MAX_INPUT_CHARS", 10)
    with pytest.raises(AIIinputError):
        summarize_impact("x" * 11)
    assert spy.called is False

def test_valid_test(spy):
    result = summarize_impact("Wells built in three villages")
    assert spy.called is True
    assert result.summary == "ok"

def test_text_at_exact_max_length_is_accepted(spy, monkeypatch):
    monkeypatch.setattr(settings, "AI_MAX_INPUT_CHARS", 10)
    result = summarize_impact("x" * 10)
    assert spy.called is True
    assert result.summary == "ok"
from abc import ABC, abstractmethod
from app.modules.ai.schemas import SummaryResult
from app.shared.config import settings

class AIProviderError(Exception):
    """The AI company failed (down, timeout, bad key). Server-side problem."""

class AIProvider(ABC):
    @abstractmethod
    def summarize(self, text: str) -> SummaryResult:
        #the shape every ai provider(mock, gemini, openai) must follow
        ...

class MockProvider(AIProvider):
    def summarize(self, text: str) -> SummaryResult:
        # Not real ai, we just cut the text short and label it clearly.
        return SummaryResult(summary=f"[DEMO WORK] {text:100}", is_mock=True)
class RealProvider(AIProvider):
    """ empty for now """
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        
    def summarize(self, text: str) -> SummaryResult:
        raise NotImplementedError

def get_provider() -> AIProvider:
    if settings.AI_API_KEY:
        return RealProvider(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)
    return MockProvider()
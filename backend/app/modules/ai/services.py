from app.modules.ai.providers import get_provider
from app.modules.ai.schemas import SummaryResult
from app.shared.config import settings

class AIInputError(ValueError):
    """Raised when the text is not acceptable; nothing is sent to the AI."""
def summarize_impact(text: str) -> SummaryResult:
    """ Validate the text first, then call the provider"""

    cleaned = text.strip()

    if not cleaned:
        raise AIInputError("Text is empty; there is nothing to summarize.")

    if len(cleaned) > settings.AI_MAX_INPUT_CHARS:
        raise AIInputError(
            f"Text is too long ({len(cleaned)} characters). "
            f"Maximum allowed is {settings.AI_MAX_INPUT_CHARS}."
        )
    return get_provider().summarize(cleaned)
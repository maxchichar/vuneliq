import re

from app.modules.ai.providers import AIProviderError, get_provider
from app.modules.ai.schemas import SummaryResult
from app.shared.config import settings
from app.shared.logging import get_module_logger

logger = get_module_logger("ai")

# Matches numbers such as 3, 1,200, 45.5 or 10%. Commas are stripped before comparing.
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


class AIInputError(ValueError):
    """Raised when the text is not acceptable; nothing is sent to the AI."""


def _numbers(text: str) -> set[str]:
    return {m.group().replace(",", "").rstrip(".") for m in _NUMBER.finditer(text)}


def check_grounded(summary: str, source: str) -> None:
    """Reject output that is empty, too long, or contains numbers missing from the source.

    On a donation platform an invented amount or beneficiary count is worse than no summary.
    """
    if not summary.strip():
        raise AIProviderError("Provider returned an empty summary")
    if len(summary) > settings.AI_MAX_OUTPUT_CHARS:
        raise AIProviderError("Provider summary exceeded AI_MAX_OUTPUT_CHARS")
    invented = _numbers(summary) - _numbers(source)
    if invented:
        logger.warning("Rejected AI summary with %d number(s) not found in the source", len(invented))
        raise AIProviderError("Provider summary contained numbers not present in the source")


def summarize_impact(text: str) -> SummaryResult:
    """Validate the text first, then call the provider, then check the output."""

    cleaned = text.strip()

    if not cleaned:
        raise AIInputError("Text is empty; there is nothing to summarize.")

    if len(cleaned) > settings.AI_MAX_INPUT_CHARS:
        raise AIInputError(
            f"Text is too long ({len(cleaned)} characters). "
            f"Maximum allowed is {settings.AI_MAX_INPUT_CHARS}."
        )

    result = get_provider().summarize(cleaned)
    result.summary = result.summary.strip()
    if not result.is_mock:
        check_grounded(result.summary, cleaned)
    return result

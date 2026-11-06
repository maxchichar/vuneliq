from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.ai.providers import AIProviderError
from app.modules.ai.schemas import SummarizeRequest, SummaryResult
from app.modules.ai.services import AIIinputError, summarize_impact
from app.modules.identity.models import User
from app.shared.dependencies import get_current_user
from app.modules.ai.rate_limit import AIRateLimitError, limiter
from app.shared.config import settings

router = APIRouter(prefix="/ai", tags=["AI"])


def enforce_rate_limit(current_user: User = Depends(get_current_user)) -> User:
    try:
        limiter.check(
            str(current_user.id),
            per_minute=settings.AI_RATE_LIMIT_PER_MINUTE,
            per_day=settings.AI_RATE_LIMIT_PER_DAY,
        )
    except AIRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Too many AI requests. Please wait and try again.",
            headers={"Retry-After": str(exc.retry_after)},
        )
    return current_user

@router.post("/summarize", response_model=SummaryResult)
def summarize(
    req: SummarizeRequest,

    current_user: User = Depends(enforce_rate_limit),
):
    try:
        return summarize_impact(req.text)
    except AIIinputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AIProviderError:
        raise HTTPException(
             status_code=status.HTTP_502_BAD_GATEWAY,
             detail="The AI service is unavailable. Please try again.",
        )


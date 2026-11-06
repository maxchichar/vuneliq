import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

MIN = 60
DAY = 24 * 60 * 60


class AIRateLimitError(Exception):
    """The user made too many calls. retry_after = seconds to wait."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry in {retry_after}s.")


class RateLimiter:
    """Sliding window limiter: remembers when each user made calls."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock  # injectable so tests can fake time
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()  # sync routes run in several threads

    def check(self, key: str, per_minute: int, per_day: int) -> None:
        """Record one call for key, or raise AIRateLimitError."""
        now = self._clock()
        with self._lock:
            calls = self._calls[key]

            # forget calls older than a day, they no longer count
            while calls and calls[0] <= now - DAY:
                calls.popleft()

            # short window calls in the last 60 seconds
            recent = [t for t in calls if t > now - MIN]
            if len(recent) >= per_minute:
                raise AIRateLimitError(int(recent[0] + MIN - now) + 1)

            # long window today's budget
            if len(calls) >= per_day:
                raise AIRateLimitError(int(calls[0] + DAY - now) + 1)

            calls.append(now)

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()


limiter = RateLimiter()
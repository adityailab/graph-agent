"""Keeping knowledge ingestion's model use in check."""

from __future__ import annotations

from collections import deque

HOUR_MS = 60 * 60_000
MAX_BACKOFF_SECONDS = 30 * 60


class Pacer:
    """An hourly cap on ingested items, and a growing pause after consecutive failures."""

    def __init__(self, *, max_per_hour: int) -> None:
        self._max = max_per_hour
        self._recent: deque[int] = deque()
        self._failures = 0

    def allows(self, now: int) -> bool:
        while self._recent and self._recent[0] <= now - HOUR_MS:
            self._recent.popleft()
        return len(self._recent) < self._max

    def ingested(self, now: int) -> None:
        self._recent.append(now)
        self._failures = 0

    def failed(self) -> None:
        self._failures += 1

    def pause_seconds(self, idle: float) -> float:
        """How long to rest: `idle` normally, doubling with each consecutive failure."""
        pause: float = idle * 2.0**self._failures
        return min(pause, float(MAX_BACKOFF_SECONDS))

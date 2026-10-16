"""Hook logging, and telling a database outage apart from other errors."""

from __future__ import annotations

import logging

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from handoff.config import Config

OUTAGE = (RedisConnectionError, RedisTimeoutError)


def is_outage(exc: BaseException) -> bool:
    """True when the database could not be reached, as opposed to a bad query or event."""
    return isinstance(exc, OUTAGE)


def setup_logging(config: Config) -> None:
    """Send hook logs to ~/.handoff/logs/hooks.log."""
    logs = config.home / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=logs / "hooks.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

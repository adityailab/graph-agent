"""One long-lived event loop per GraphRAG instance.

GraphRAG-SDK is async and keeps an async connection pool bound to the loop that made it.
Calling its *_sync wrappers from different threads creates and closes loops ("Event loop
is closed"). Every call for one instance goes through its own loop thread instead.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


class AsyncRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def run(self, coro: Coroutine[Any, Any, T], timeout: float | None = None) -> T:
        """Run `coro` on this runner's loop and wait for its result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout)
        except TimeoutError:
            future.cancel()  # otherwise it keeps running and shares state with the next call
            raise

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

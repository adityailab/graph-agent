from __future__ import annotations

import asyncio
import time

import pytest

pytest.importorskip("graphrag_sdk")

from handoff.knowledge.runner import AsyncRunner


def test_a_call_that_times_out_is_cancelled_not_left_running() -> None:
    runner = AsyncRunner()
    state = {"cancelled": False}

    async def slow() -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            state["cancelled"] = True
            raise

    try:
        with pytest.raises(TimeoutError):
            runner.run(slow(), timeout=0.1)
        deadline = time.monotonic() + 3
        while not state["cancelled"] and time.monotonic() < deadline:
            time.sleep(0.02)
        assert state["cancelled"]
    finally:
        runner.close()

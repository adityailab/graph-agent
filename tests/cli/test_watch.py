from __future__ import annotations

from collections.abc import Iterator

from redis.exceptions import ConnectionError as RedisConnectionError

from handoff.cli.watch import Frame, render_frame, watch_loop
from handoff.graph.feed import FeedEvent
from handoff.graph.records import InsightView, SessionInfo


def _frame() -> Frame:
    return Frame(
        graph="shop",
        sessions=[SessionInfo("s1", "frontend", "/w", 0, 1_792_000_000_000)],
        events=[FeedEvent(1_792_000_000_000, "frontend", "DECIDED", "keep money in paise " * 20)],
        insights=[InsightView("collision", 2, "backend and deploy both changed x.yml", ())],
    )


def test_a_frame_shows_sessions_events_and_insights_within_the_width() -> None:
    text = render_frame(_frame(), width=80)
    assert "shop" in text
    assert "DECIDED" in text
    assert "What matters now" in text
    assert "\x1b[36mfrontend" in text  # frontend's colour
    visible = next(line for line in text.splitlines() if "DECIDED" in line)
    assert len(_strip(visible)) <= 80


def _strip(line: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", line)


def test_the_loop_keeps_going_when_the_database_goes_away() -> None:
    written: list[str] = []
    calls: Iterator[Frame | Exception] = iter([_frame(), RedisConnectionError("down"), _frame()])

    def fetch() -> Frame:
        item = next(calls)
        if isinstance(item, Exception):
            raise item
        return item

    assert watch_loop(fetch, written.append, sleep=lambda _: None, frames=3, width=80) == 0
    assert "database unreachable" in written[1]
    assert "DECIDED" in written[2]


def test_control_c_ends_the_loop_cleanly() -> None:
    def interrupted(_: float) -> None:
        raise KeyboardInterrupt

    assert watch_loop(_frame, lambda _: None, sleep=interrupted, frames=None, width=80) == 0


def test_escape_sequences_in_event_text_are_not_passed_to_the_terminal() -> None:
    frame = Frame(
        graph="shop",
        sessions=[],
        events=[
            FeedEvent(1_792_000_000_000, "frontend", "asked", "hi \x1b]0;pwned\x07\x1b[2J there")
        ],
        insights=[],
    )
    line = next(x for x in render_frame(frame, width=120).splitlines() if "asked" in x)
    assert "\x1b]0" not in line
    assert "\x1b[2J" not in line
    assert "\x07" not in line

from __future__ import annotations

import io

import pytest

from handoff.cli.banner import animated, show_banner, step


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


TERM = {"TERM": "xterm-256color"}


def test_the_show_only_runs_on_a_real_terminal() -> None:
    assert animated(_Tty(), TERM)
    assert not animated(io.StringIO(), TERM)  # a pipe gets the plain text, as before
    assert not animated(_Tty(), {**TERM, "NO_COLOR": "1"})
    assert not animated(_Tty(), {"TERM": "dumb"})
    assert not animated(_Tty(), {**TERM, "CI": "true"})


def test_a_pipe_gets_no_banner_and_no_step_lines() -> None:
    out = io.StringIO()
    show_banner(out, animate=False)
    with step("checking prerequisites", out, enabled=False):
        pass
    assert out.getvalue() == ""


def test_the_banner_names_the_tool() -> None:
    out = io.StringIO()
    show_banner(out, animate=True, pause=0)
    assert "handoff" in out.getvalue()
    assert "\x1b[" in out.getvalue()  # coloured


def test_a_finished_step_ends_with_a_tick_and_its_label() -> None:
    out = _Tty()
    with step("starting FalkorDB", out, enabled=True, interval=0.001):
        pass
    last = out.getvalue().splitlines()[-1]
    assert "✓" in last
    assert "starting FalkorDB" in last


def test_a_failed_step_shows_a_cross_and_still_raises() -> None:
    out = _Tty()
    with pytest.raises(RuntimeError), step("installing hooks", out, enabled=True, interval=0.001):
        raise RuntimeError("boom")
    assert "✗" in out.getvalue()
    assert "✓" not in out.getvalue()


def test_a_step_can_be_marked_failed_without_an_exception() -> None:
    out = _Tty()
    with step("checking prerequisites", out, enabled=True, interval=0.001) as s:
        s.fail()
    assert "✗" in out.getvalue()


def test_the_checklist_never_moves_the_cursor() -> None:
    """Some terminals mangle text printed after a rewritten line, so a step only appends."""
    out = _Tty()
    with step("starting FalkorDB", out, enabled=True, interval=0.001, hold=0.02):
        pass
    show_banner(out, animate=True, pause=0)
    assert "\r" not in out.getvalue()
    assert "\x1b[K" not in out.getvalue()
    assert "\x1b[2K" not in out.getvalue()

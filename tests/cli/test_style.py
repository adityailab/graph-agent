from __future__ import annotations

import io

from handoff.cli.style import Palette, colour_enabled


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_colour_is_on_for_a_terminal_and_off_for_a_pipe() -> None:
    assert colour_enabled(_Tty(), {"TERM": "xterm-256color"})
    assert not colour_enabled(io.StringIO(), {"TERM": "xterm-256color"})


def test_no_color_and_dumb_terminals_turn_colour_off() -> None:
    assert not colour_enabled(_Tty(), {"NO_COLOR": "1", "TERM": "xterm"})
    assert not colour_enabled(_Tty(), {"TERM": "dumb"})


def test_force_color_turns_it_on_for_a_pipe() -> None:
    assert colour_enabled(io.StringIO(), {"FORCE_COLOR": "1", "TERM": "xterm"})


def test_a_palette_paints_with_escape_codes_or_leaves_text_alone() -> None:
    assert Palette(True).green("ok") == "\x1b[32mok\x1b[0m"
    assert Palette(True).bold("x") == "\x1b[1mx\x1b[0m"
    assert Palette(False).green("ok") == "ok"

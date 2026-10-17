"""Terminal colour for the CLI: on for a terminal, off for pipes, NO_COLOR and dumb terminals."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import TextIO

_CODES = {
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "amber": "33",
    "blue": "34",
    "purple": "35",
    "teal": "36",
}


def colour_enabled(stream: TextIO, environ: Mapping[str, str]) -> bool:
    """Whether to colour what is written to `stream` (see no-color.org for NO_COLOR)."""
    if environ.get("NO_COLOR"):
        return False
    if environ.get("FORCE_COLOR"):
        return True
    return environ.get("TERM", "") != "dumb" and stream.isatty()


class Palette:
    """Paints text with ANSI codes, or returns it unchanged when colour is off."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _paint(self, code: str, text: str) -> str:
        return f"\x1b[{code}m{text}\x1b[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return self._paint(_CODES["bold"], text)

    def dim(self, text: str) -> str:
        return self._paint(_CODES["dim"], text)

    def red(self, text: str) -> str:
        return self._paint(_CODES["red"], text)

    def green(self, text: str) -> str:
        return self._paint(_CODES["green"], text)

    def amber(self, text: str) -> str:
        return self._paint(_CODES["amber"], text)

    def blue(self, text: str) -> str:
        return self._paint(_CODES["blue"], text)

    def purple(self, text: str) -> str:
        return self._paint(_CODES["purple"], text)

    def teal(self, text: str) -> str:
        return self._paint(_CODES["teal"], text)


def stdout_palette() -> Palette:
    """The palette for this process's standard output."""
    return Palette(colour_enabled(sys.stdout, os.environ))

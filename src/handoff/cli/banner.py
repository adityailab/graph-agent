"""The first thing a person sees after installing: the logo and a live checklist for `init`.

Only for a real terminal. A pipe, NO_COLOR, a dumb terminal or CI gets the plain text it always
did, so scripts never see escape codes or spinner frames."""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import TextIO

from handoff.cli.style import Palette, colour_enabled

_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_TAGLINE = "sessions that know what each other are doing, and why"


def animated(stream: TextIO, environ: Mapping[str, str] | None = None) -> bool:
    """Whether to draw the logo and spinners on `stream`."""
    env = os.environ if environ is None else environ
    return colour_enabled(stream, env) and not env.get("CI") and not env.get("FORCE_COLOR")


def _logo(p: Palette) -> list[str]:
    macs = (p.blue, p.purple, p.amber)

    def row(cells: tuple[str, str, str], link: str) -> str:
        return " " + p.teal(link).join(m(c) for m, c in zip(macs, cells, strict=True))

    return [
        row(("┌────┐", "┌────┐", "┌────┐"), " "),
        row(("│ ▮▮ │", "│ ▮▮ │", "│ ▮▮ │"), "─") + "   " + p.bold("handoff"),
        row(("└─┬┬─┘", "└─┬┬─┘", "└─┬┬─┘"), " ") + "   " + p.dim(_TAGLINE),
    ]


def show_banner(stream: TextIO, *, animate: bool, pause: float = 0.07) -> None:
    """The three small Macs and the name, revealed line by line. Silent when `animate` is off."""
    if not animate:
        return
    stream.write("\n")
    for line in _logo(Palette(True)):
        stream.write(line + "\n")
        stream.flush()
        time.sleep(pause)
    stream.write("\n")
    stream.flush()


class Step:
    """One line of the checklist; `fail()` turns its tick into a cross."""

    def __init__(self) -> None:
        self.failed = False

    def fail(self) -> None:
        self.failed = True


@contextmanager
def step(label: str, stream: TextIO, *, enabled: bool, interval: float = 0.08) -> Iterator[Step]:
    """Show `label` with a spinner while the block runs, then a tick (or a cross). A raised error
    still propagates; the cross is drawn first."""
    state = Step()  # `hold`: a quick step still shows its spinner long enough to read
    if not enabled:
        yield state
        return
    p = Palette(True)
    done = threading.Event()

    def spin() -> None:
        i = 0
        while not done.is_set():
            stream.write(f"\r {p.teal(_FRAMES[i % len(_FRAMES)])} {label}")
            stream.flush()
            i += 1
            done.wait(interval)

    worker = threading.Thread(target=spin, daemon=True)
    worker.start()
    started = time.monotonic()
    try:
        yield state
    except BaseException:
        state.fail()
        raise
    finally:
        time.sleep(max(0.0, hold - (time.monotonic() - started)))
        done.set()
        worker.join()
        mark = p.red("✗") if state.failed else p.green("✓")
        stream.write(f"\r {mark} {label}\x1b[K\n")
        stream.flush()


def stdout_animated() -> bool:
    """Whether this process's standard output gets the show."""
    return animated(sys.stdout)

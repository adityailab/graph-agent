"""The demo's scratch folder: reset only a folder the demo itself made, never a real one."""

from __future__ import annotations

import shutil
from pathlib import Path

MARKER = ".handoff-demo"


class NotAScratchFolder(Exception):  # noqa: N818 - names the situation
    """The folder exists, holds files, and was not made by the demo."""


def prepare_scratch(folder: Path) -> None:
    """Make `folder` an empty, marked demo folder. A folder with the marker is wiped; an
    empty or missing one is used; anything else is refused and left untouched."""
    if folder.exists() and any(folder.iterdir()):
        if not (folder / MARKER).exists():
            raise NotAScratchFolder(
                f"{folder} has files and was not made by the demo, so it was not touched. "
                "Pass an empty or new folder to --workspace."
            )
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / MARKER).write_text("created by handoff demo; safe to delete\n")

"""File paths as stored in the graph: relative to the project folder when inside it."""

from __future__ import annotations

from pathlib import Path


def relative_path(file_path: str, project_dir: str) -> str:
    """Return the path relative to the project, or unchanged if it lies outside it.

    Both sides are resolved first, so a symlinked project folder (or macOS's
    /tmp -> /private/tmp) still gives one File node per file.
    """
    path, root = Path(file_path).resolve(), Path(project_dir).resolve()
    return str(path.relative_to(root)) if path.is_relative_to(root) else file_path

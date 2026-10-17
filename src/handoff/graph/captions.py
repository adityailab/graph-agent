"""Short display names for nodes, so a graph browser shows words rather than node ids."""

from __future__ import annotations

CAPTION_CHARS = 40


def caption(text: str, limit: int = CAPTION_CHARS) -> str:
    """The first line of `text` with spaces collapsed, cut to `limit` characters."""
    first = " ".join((text.strip().splitlines() or [""])[0].split())
    return first if len(first) <= limit else first[: limit - 1] + "…"

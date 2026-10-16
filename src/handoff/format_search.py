"""Turning search results into text a session can read."""

from __future__ import annotations

from collections.abc import Sequence

from handoff.format import shorten
from handoff.graph.records import DecisionHit


def _sentence(text: str, limit: int) -> str:
    return shorten(text, limit).rstrip(" .")


def _render_hit(hit: DecisionHit) -> str:
    line = (
        f'{hit.id} {hit.role}, request "{shorten(hit.request_text, 120)}": '
        f"{_sentence(hit.text, 200)}. Why: {_sentence(hit.reason, 200)}."
    )
    if hit.files:
        line += f" Files: {', '.join(hit.files)}"
        if hit.related_roles:
            line += f"; also changed by {', '.join(hit.related_roles)}"
        line += "."
    return line


def render_search(query: str, hits: Sequence[DecisionHit]) -> str:
    """Render decision hits, best first, one per line, with their graph context."""
    lines = [f'Decisions matching "{shorten(query, 80)}", best first:']
    lines.extend(_render_hit(h) for h in hits)
    return "\n".join(lines)

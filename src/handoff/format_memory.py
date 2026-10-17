"""The memory overview as text: the six kinds of memory, then what each role's session holds."""

from __future__ import annotations

from collections.abc import Sequence

from handoff.format import Paint, _unpainted, shorten
from handoff.graph.memory_view import MemoryType, RoleContext


def render_memory(
    types: Sequence[MemoryType],
    contexts: Sequence[RoleContext],
    paint: Paint = _unpainted,
) -> str:
    """Plain text by default (what a session reads); `paint` adds colour for a terminal."""
    lines = [paint("head", "# memory, by kind")]
    for t in types:
        lines.append(f"  {paint('memory', f'{t.name:<11}')} {t.count:>4}  {t.what}")
        lines.append(f"  {'':<11} {'':>4}  {paint('dim', t.detail)}")
    lines += ["", paint("head", "# what each session holds")]
    if not contexts:
        lines.append("  no session has been active recently")
    for c in contexts:
        lines.append(
            f"  {paint('role', c.role)}  {paint('dim', 'working on:')} {shorten(c.working_on, 120)}"
        )
        for author, text in c.learned[:5]:
            lines.append(
                f"    {paint('dim', 'learned from')} {paint('role', author)}: {shorten(text, 110)}"
            )
        if len(c.learned) > 5:
            lines.append(f"    {paint('dim', f'... and {len(c.learned) - 5} more decisions')}")
        facts = f"inbox {c.inbox} · open needs {c.open_needs} · rules in force {c.rules}"
        lines.append(f"    {paint('dim', facts)}")
    return "\n".join(lines)

"""The 'What matters now' part of a handoff, refreshed at most every few minutes."""

from __future__ import annotations

from handoff.format import render_insights
from handoff.graph.insights import current_insights, refresh_insights
from handoff.mcp.context import ToolContext

REFRESH_MS = 5 * 60_000
SHOWN = 3


def insights_section(ctx: ToolContext) -> str:
    """The top insights, recomputed when this server has not done so recently."""
    now = ctx.now()
    if ctx.insights_checked_at is None or now - ctx.insights_checked_at > REFRESH_MS:
        kg = getattr(ctx.knowledge, "kg", None)  # themes need the knowledge graph
        refresh_insights(ctx.graph, kg, at=now)
        ctx.insights_checked_at = now
    return render_insights(current_insights(ctx.graph, limit=SHOWN))

"""The 'What matters now' part of a handoff, refreshed at most every few minutes."""

from __future__ import annotations

from redis.exceptions import ResponseError

from handoff.format import render_insights
from handoff.graph.insights import current_insights, refresh_insights
from handoff.mcp.context import ToolContext

REFRESH_MS = 5 * 60_000
RECENT_MS = 7 * 24 * 60 * 60_000  # collisions older than a week no longer matter
SHOWN = 3


def insights_section(ctx: ToolContext) -> str:
    """The top insights, recomputed when this server has not done so recently. Empty when
    they cannot be computed: insights must never break the handoff itself."""
    now = ctx.now()
    try:
        if ctx.insights_checked_at is None or now - ctx.insights_checked_at > REFRESH_MS:
            kg = getattr(ctx.knowledge, "kg", None)  # None: stored themes are kept
            refresh_insights(ctx.graph, kg, at=now, since=now - RECENT_MS)
            ctx.insights_checked_at = now
        return render_insights(current_insights(ctx.graph, limit=SHOWN))
    except ResponseError:  # e.g. a graph deleted under a running server; handoff still works
        return ""

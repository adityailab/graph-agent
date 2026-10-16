"""Choosing a decision's topic: reuse an existing subject when it is the same one.

Distances measured on short topic names with the real model: same subject 0.10-0.23,
related 0.28-0.44, unrelated 0.44-0.51.
"""

from __future__ import annotations

from handoff.graph.decisions import normalise_topic
from handoff.graph.topics import ensure_topic, nearest_topics, topic_shares_files
from handoff.mcp.context import ToolContext

SAME = 0.15  # close enough on wording alone
RELATED = 0.30  # close enough only if the work behind both touched the same files


def choose_topic(ctx: ToolContext, topic: str, *, request_id: str) -> str:
    """Return the topic name to record: an existing one, or this one, normalised."""
    name = normalise_topic(topic)
    if ctx.embedder is None or not name:
        return name
    vector = ctx.embedder.embed([name])[0]
    for other, distance in nearest_topics(ctx.graph, vector, k=5):
        if distance <= SAME:
            return other
        if distance <= RELATED and topic_shares_files(ctx.graph, other, request_id):
            return other
    ensure_topic(ctx.graph, name, vector)
    return name

"""What the stand-in may use: one role's recent requests, decisions, needs and messages."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from falkordb import Graph

from handoff.format import select_requests
from handoff.graph.history import handoff_requests
from handoff.graph.messages import role_messages
from handoff.graph.records import MessageView, RequestView


@dataclass(frozen=True)
class StandinContext:
    role: str
    requests: tuple[RequestView, ...]
    messages: tuple[MessageView, ...]


def gather_context(
    graph: Graph,
    *,
    role: str,
    since: int,
    limit: int,
    relevant: Sequence[RequestView] = (),
) -> StandinContext:
    """Collect a role's history without delivering or changing anything.

    `relevant` adds requests found by searching for the question, however old they are.
    """
    recent = select_requests(handoff_requests(graph, role=role, since=since), limit)
    by_id = {r.id: r for r in [*relevant, *recent]}
    requests = sorted(by_id.values(), key=lambda r: r.at)
    messages = role_messages(graph, role=role, since=since, limit=limit)
    return StandinContext(role=role, requests=tuple(requests), messages=tuple(messages))


def context_ids(ctx: StandinContext) -> set[str]:
    """Every id the stand-in may cite."""
    ids = {m.id for m in ctx.messages}
    for r in ctx.requests:
        ids.add(r.id)
        ids.update(d.id for d in r.decisions)
        ids.update(n.id for n in r.needs)
    return ids

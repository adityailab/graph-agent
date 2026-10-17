"""One JSON-ready picture of the graph for the browser to draw, rebuilt on every poll."""

from __future__ import annotations

import zlib
from dataclasses import asdict
from typing import Any

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

from handoff.config import Config, knowledge_graph_name
from handoff.dashboard.tracks import track_summary
from handoff.graph.connection import connect, graph_exists
from handoff.graph.context_view import GraphView, concept_graph, work_graph
from handoff.graph.feed import recent_events
from handoff.graph.insights import current_insights
from handoff.graph.memory_view import concept_total, memory_types, role_contexts
from handoff.graph.overview import handoffs, message_flows, role_stats

EVENTS = 80
WORK_EDGES = 250
CONCEPT_EDGES = 200


def _view(view: GraphView) -> dict[str, Any]:
    return {"nodes": [asdict(n) for n in view.nodes], "edges": [asdict(e) for e in view.edges]}


def _empty(error: str | None) -> dict[str, Any]:
    nothing: dict[str, Any] = {"nodes": [], "edges": []}
    return {
        "error": error, "graph": "", "now": 0, "roles": [], "events": [], "flows": [],
        "handoffs": [], "work": nothing, "concepts": nothing, "tracks": [],
        "memory": {"types": [], "contexts": []},
    }  # fmt: skip


def _counts(
    roles: list[Any], flows: list[Any], insights: list[Any], work: GraphView, n: int
) -> dict[str, int]:
    def total(kind: str) -> int:
        return sum(f.count for f in flows if f.kind == kind)

    return {
        "decisions": sum(r.decisions for r in roles),
        "reads": total("read"),
        "messages": sum(f.count for f in flows if f.kind not in ("read", "need")),
        "open_needs": sum(r.open_needs for r in roles),
        "collisions": sum(1 for i in insights if i.kind == "collision"),
        "edges": len(work.edges),
        "concepts": n,
        "insights": len(insights),
    }


def snapshot(config: Config, *, now: int, window_ms: int) -> dict[str, Any]:
    """Everything the four views draw. A database that is down or has no graph yet gives an
    empty snapshot (with the reason) instead of an error, so the page keeps polling."""
    try:
        if not graph_exists(config):
            return {**_empty(None), "graph": config.graph_name, "now": now}
        graph = connect(config)
        roles = role_stats(graph, since=now - window_ms)
        flows = message_flows(graph)
        insights = current_insights(graph, limit=20)
        work = work_graph(graph, limit=WORK_EDGES)
        kg_config = Config(config.host, config.port, knowledge_graph_name(config), config.home)
        concepts = (
            concept_graph(connect(kg_config), limit=CONCEPT_EDGES)
            if graph_exists(kg_config)
            else GraphView((), ())
        )
        events = recent_events(graph, limit=EVENTS)
        found = handoffs(graph, limit=20)
        kinds = memory_types(graph, concepts=concept_total(config), since=now - window_ms)
        contexts = role_contexts(graph, since=now - window_ms)
    except (RedisConnectionError, RedisTimeoutError, OSError) as exc:  # keep the page alive
        return {**_empty(f"database unreachable: {exc}"), "graph": config.graph_name, "now": now}
    except RedisError as exc:  # the database answered, but a query failed
        return {**_empty(f"graph query failed: {exc}"), "graph": config.graph_name, "now": now}
    return {
        "error": None,
        "graph": config.graph_name,
        "now": now,
        "roles": [asdict(r) for r in roles],
        "events": [
            {**asdict(e), "key": f"{e.at}:{e.role}:{e.kind}:{zlib.crc32(e.text.encode())}"}
            for e in events
        ],
        "flows": [asdict(f) for f in flows],
        "handoffs": [
            {**asdict(h), "decisions": [{"text": t, "reason": r} for t, r in h.decisions]}
            for h in found
        ],
        "work": _view(work),
        "concepts": _view(concepts),
        "memory": {"types": [asdict(t) for t in kinds], "contexts": [asdict(c) for c in contexts]},
        "tracks": track_summary(_counts(roles, flows, insights, work, len(concepts.nodes))),
    }

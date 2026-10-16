"""How two pieces of work connect: FalkorDB's algo.SPpaths over the work graph."""

from __future__ import annotations

from typing import Any

from falkordb import Graph

from handoff.graph.records import PathStep

# Relationships that carry meaning between pieces of work. Session links are left out:
# every request is one hop from its session, which would make everything "connected".
_WORK_LINKS = ["CAUSED", "TOUCHED", "LED_TO", "ABOUT", "RAISED", "RESOLVED_BY", "CITES", "REPLY_TO"]
_MAX_HOPS = 10

# FalkorDB's shortestPath() is directed only; algo.SPpaths walks both directions.
_CONNECTION = (
    "MATCH (a:Request {id: $rid}), (:Session {role: $role})-[:RECEIVED]->(b:Request) "
    "WHERE a <> b "
    "CALL algo.SPpaths({sourceNode: a, targetNode: b, relTypes: $links, "
    "relDirection: 'both', maxLen: $hops, pathCount: 1}) YIELD path "
    "RETURN path ORDER BY length(path) LIMIT 1"
)

_TEXT_PROPERTY = {"File": "path", "Topic": "name", "Edit": "tool"}


def _node_text(node: Any) -> tuple[str, str]:
    label = node.labels[0] if node.labels else "?"
    value = node.properties.get(_TEXT_PROPERTY.get(label, "text"), "")
    return str(label), str(value)


def connection_path(graph: Graph, *, from_request: str, to_role: str) -> list[PathStep] | None:
    """The shortest chain of work linking a request to any request of `to_role`."""
    rows = graph.ro_query(
        _CONNECTION,
        {"rid": from_request, "role": to_role, "links": _WORK_LINKS, "hops": _MAX_HOPS},
    ).result_set
    if not rows:
        return None
    path = rows[0][0]
    nodes, edges = path.nodes(), path.edges()
    steps = []
    for i, node in enumerate(nodes):
        label, text = _node_text(node)
        via = str(edges[i - 1].relation) if i > 0 else ""
        steps.append(PathStep(label=label, text=text, via=via))
    return steps

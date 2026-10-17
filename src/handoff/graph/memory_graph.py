"""One kind of memory drawn as a graph: the nodes and relationships that make it up."""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.context_view import GraphView, ViewEdge, ViewNode, work_graph
from handoff.graph.conventions import ALL, all_conventions

# kind of memory -> (node labels, relationship types) of the part of the graph that is it
_PARTS: dict[str, tuple[list[str], list[str]]] = {
    "working": (["Session", "Request"], ["RECEIVED"]),
    "episodic": (
        ["Session", "Request", "Edit", "File", "Message"],
        ["RECEIVED", "CAUSED", "TOUCHED", "NEXT", "SENT"],
    ),
    "semantic": (["Session", "Request", "Decision", "Topic"], ["RECEIVED", "LED_TO", "ABOUT"]),
    "temporal": (
        ["Request", "Decision", "Message"],
        ["NEXT", "LED_TO", "SUPERSEDES", "REPLY_TO", "AGREES_WITH"],
    ),
    "social": (["Session", "Request", "Message"], ["SENT", "DELIVERED_TO", "CONSULTED"]),
}
WORKING_EDGES = 12  # working memory is what is recent, so only the newest links


def _rules(graph: Graph) -> GraphView:
    """Procedural memory has no edges of its own: join each rule to who it applies to."""
    nodes: dict[str, ViewNode] = {}
    edges: list[ViewEdge] = []
    for c in all_conventions(graph):
        rule = f"Convention:{c.id}"
        nodes[rule] = ViewNode(rule, "Convention", f"{c.text} (why: {c.reason})", "")
        who = f"Role:{c.scope}"
        label = "everyone" if c.scope == ALL else c.scope
        nodes.setdefault(who, ViewNode(who, "Session", label, "" if c.scope == ALL else c.scope))
        edges.append(ViewEdge(rule, who, "applies_to"))
    return GraphView(tuple(nodes.values()), tuple(edges))


def memory_graph(graph: Graph, kind: str, *, limit: int) -> GraphView:
    """The graph for one kind of memory. Raises ValueError for an unknown kind."""
    if kind == "procedural":
        return _rules(graph)
    if kind not in _PARTS:
        raise ValueError(f"unknown kind of memory: {kind}")
    labels, rels = _PARTS[kind]
    return work_graph(
        graph, limit=WORKING_EDGES if kind == "working" else limit, kinds=labels, rels=rels
    )

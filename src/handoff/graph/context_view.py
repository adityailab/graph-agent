"""The graph as nodes and edges ready to draw: the work graph (sessions, requests, decisions...)
and the concept graph the knowledge worker builds from it."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

SHARED = "shared"  # a file changed by more than one role


@dataclass(frozen=True)
class ViewNode:
    id: str
    kind: str
    text: str
    role: str


@dataclass(frozen=True)
class ViewEdge:
    source: str
    target: str
    kind: str


@dataclass(frozen=True)
class GraphView:
    nodes: tuple[ViewNode, ...]
    edges: tuple[ViewEdge, ...]


KINDS = ["Session", "Request", "Decision", "Need", "Edit", "File", "Message"]

_EDGES = """
MATCH (a)-[r]->(b) WHERE labels(a)[0] IN $kinds AND labels(b)[0] IN $kinds
  AND (size($rels) = 0 OR type(r) IN $rels)
RETURN id(a), labels(a)[0], coalesce(a.role, a.text, a.path, a.name),
       id(b), labels(b)[0], coalesce(b.role, b.text, b.path, b.name),
       type(r), coalesce(r.at, b.at, a.at, 0) AS ts
ORDER BY ts DESC LIMIT $limit
"""
# Which role's session each node belongs to; two small queries beat one clever one.
_OWNERS = (
    "MATCH (s:Session)-[:RECEIVED]->(x:Request) RETURN id(x), s.role",
    "MATCH (s:Session)-[:RECEIVED]->(:Request)-[]->(x) "
    "WHERE labels(x)[0] IN ['Decision', 'Need', 'Edit'] RETURN id(x), s.role",
    "MATCH (s:Session)-[:SENT]->(x:Message) RETURN id(x), s.role",
    "MATCH (s:Session) RETURN id(s), s.role",
)
_FILE_ROLES = (
    "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:CAUSED]->(:Edit)-[:TOUCHED]->(f:File) "
    "RETURN id(f), collect(DISTINCT s.role)"
)
_CONCEPTS = """
MATCH (a:__Entity__)-[r:RELATES]->(b:__Entity__)
RETURN a.name, a.type, b.name, b.type, coalesce(r.rel_type, r.type, 'relates')
LIMIT $limit
"""


def _short(text: object, width: int = 400) -> str:
    if text is None:
        return ""
    one_line = " ".join(str(text).split())
    return one_line if len(one_line) <= width else one_line[: width - 1] + "…"


def _owners(graph: Graph) -> dict[int, str]:
    owners = {int(i): str(r) for q in _OWNERS for i, r in graph.ro_query(q).result_set}
    for node_id, roles in graph.ro_query(_FILE_ROLES).result_set:
        owners[int(node_id)] = str(roles[0]) if len(roles) == 1 else SHARED
    return owners


def work_graph(
    graph: Graph,
    *,
    limit: int,
    kinds: list[str] | None = None,
    rels: list[str] | None = None,
) -> GraphView:
    """The newest `limit` relationships of the work graph and the nodes they join. `kinds` and
    `rels` narrow it to some node labels and relationship types (all of them by default)."""
    owners = _owners(graph)
    nodes: dict[str, ViewNode] = {}
    edges: list[ViewEdge] = []
    for a, a_kind, a_text, b, b_kind, b_text, kind, _ts in graph.ro_query(
        _EDGES, {"kinds": kinds or KINDS, "rels": rels or [], "limit": limit}
    ).result_set:
        for node_id, node_kind, text in ((a, a_kind, a_text), (b, b_kind, b_text)):
            key = f"{node_kind}:{node_id}"
            role = owners.get(int(node_id), "") if node_kind != "Session" else str(text)
            nodes.setdefault(key, ViewNode(key, str(node_kind), _short(text), role))
        edges.append(ViewEdge(f"{a_kind}:{a}", f"{b_kind}:{b}", str(kind)))
    return GraphView(tuple(nodes.values()), tuple(edges))


def concept_graph(kg: Graph, *, limit: int) -> GraphView:
    """The knowledge graph's concepts and how they relate (empty before it is built)."""
    nodes: dict[str, ViewNode] = {}
    edges: list[ViewEdge] = []
    for a, a_type, b, b_type, kind in kg.ro_query(_CONCEPTS, {"limit": limit}).result_set:
        for name, concept_type in ((a, a_type), (b, b_type)):
            nodes.setdefault(str(name), ViewNode(str(name), str(concept_type), str(name), ""))
        edges.append(ViewEdge(str(a), str(b), str(kind)))
    return GraphView(tuple(nodes.values()), tuple(edges))

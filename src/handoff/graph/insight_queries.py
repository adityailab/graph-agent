"""The four insight finders, each one FalkorDB algorithm plus the context to explain it."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph


@dataclass(frozen=True)
class Insight:
    kind: str
    score: float
    text: str
    about: tuple[int, ...]  # internal node ids in the work graph, used at once to link


def _roles(roles: list[str]) -> str:
    names = sorted(roles)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


_COLLISIONS = """
CALL algo.WCC({nodeLabels: ['Edit', 'File'], relationshipTypes: ['TOUCHED']})
YIELD node, componentId
WITH componentId, collect(node) AS members
UNWIND members AS m
MATCH (s:Session)-[:RECEIVED]->(:Request)-[:CAUSED]->(m)
WITH members, collect(DISTINCT s.role) AS roles WHERE size(roles) >= 2
RETURN [n IN members WHERE n:File | n.path], roles, [n IN members WHERE n:File | ID(n)]
ORDER BY size(roles) DESC, size(members) DESC LIMIT 5
"""


def collisions(graph: Graph) -> list[Insight]:
    """Files changed by more than one role (connected components of edits and files)."""
    rows = graph.ro_query(_COLLISIONS).result_set
    return [
        Insight(
            "collision",
            float(len(roles)),
            f"{_roles(roles)} {'both' if len(roles) == 2 else 'all'} changed {', '.join(files)}",
            tuple(ids),
        )
        for files, roles, ids in rows
    ]


_LOAD_BEARING = """
CALL algo.pageRank('Request', 'CONSULTED') YIELD node, score
MATCH (author:Session)-[:RECEIVED]->(node)<-[:CONSULTED]-(:Request)<-[:RECEIVED]-(reader:Session)
WHERE reader.role <> author.role
WITH node, score, collect(DISTINCT reader.role) AS readers WHERE size(readers) >= 2
RETURN ID(node), node.name, readers, score ORDER BY score DESC LIMIT 3
"""


def load_bearing(graph: Graph) -> list[Insight]:
    """Work other roles rely on: read by two or more of them, ranked by PageRank."""
    return [
        Insight("load_bearing", float(score), f"{name} was read by {_roles(readers)}", (nid,))
        for nid, name, readers, score in graph.ro_query(_LOAD_BEARING).result_set
    ]


# Exact, not algo.betweenness: FalkorDB 4.22 estimates betweenness by sampling, and on
# graphs with other labels a 3-request chain scored right 0 times in 20.
_BRIDGES = """
MATCH (src:Session)-[:RECEIVED]->(:Request)<-[:CONSULTED]-(node:Request)
      <-[:CONSULTED]-(:Request)<-[:RECEIVED]-(dst:Session),
      (me:Session)-[:RECEIVED]->(node)
WHERE src.role <> me.role AND dst.role <> me.role
WITH node, collect(DISTINCT src.role) AS read_from, collect(DISTINCT dst.role) AS read_by
RETURN ID(node), node.name, read_from, read_by, size(read_from) * size(read_by) AS score
ORDER BY score DESC LIMIT 3
"""


def bridges(graph: Graph) -> list[Insight]:
    """Work that passes information on: it read another role's work and a third role read it."""
    return [
        Insight(
            "bridge",
            float(score),
            f"{name} passes work on: it read {_roles(src)}'s work and was read by {_roles(dst)}",
            (nid,),
        )
        for nid, name, src, dst, score in graph.ro_query(_BRIDGES).result_set
    ]


_THEMES = """
CALL algo.labelPropagation({nodeLabels: ['__Entity__'], relationshipTypes: ['RELATES']})
YIELD node, communityId
WITH communityId, collect(node) AS members WHERE size(members) >= 3
UNWIND members AS e
OPTIONAL MATCH (e)-[:MENTIONED_IN]->(:Chunk)<-[:PART_OF]-(d:Document)
WITH members, collect(DISTINCT d.id) AS docs
UNWIND members AS m
WITH members, docs, m, size([(m)-[:RELATES]-() | 1]) AS degree ORDER BY degree DESC
WITH members, docs, collect(m.name) AS ranked
RETURN ranked, docs ORDER BY size(members) DESC LIMIT 3
"""


def themes(graph: Graph, kg: Graph) -> list[Insight]:
    """Clusters of related concepts in the knowledge graph (label propagation), linked to
    the requests and decisions that mention them."""
    found = []
    for names, docs in kg.ro_query(_THEMES).result_set:
        ids = graph.ro_query(
            "MATCH (n) WHERE (n:Request OR n:Decision) AND n.id IN $docs RETURN ID(n)",
            {"docs": docs},
        ).result_set
        # Most connected concepts first: they name the theme.
        shown = ", ".join(names[:6]) + (f" (+{len(names) - 6})" if len(names) > 6 else "")
        found.append(
            Insight("theme", float(len(names)), f"theme: {shown}", tuple(r[0] for r in ids))
        )
    return found

"""Small facts the drawn graph needs about some nodes: a decision's topic, who a need asks."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph


@dataclass(frozen=True)
class NeedFacts:
    for_role: str
    status: str


def decision_topics(graph: Graph) -> dict[int, str]:
    """Topic name by the decision's internal id."""
    rows = graph.ro_query("MATCH (d:Decision)-[:ABOUT]->(t:Topic) RETURN id(d), t.name").result_set
    return {int(i): str(name) for i, name in rows}


def need_facts(graph: Graph) -> dict[int, NeedFacts]:
    """The role each need asks and whether it is still open, by the need's internal id."""
    rows = graph.ro_query("MATCH (n:Need) RETURN id(n), n.for_role, n.status").result_set
    return {int(i): NeedFacts(str(role or ""), str(status or "")) for i, role, status in rows}

"""Procedural memory: standing rules the team follows, handed to every session they apply to."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

ALL = "all"  # the scope of a rule that applies to every role


@dataclass(frozen=True)
class Convention:
    id: str
    text: str
    reason: str
    scope: str  # "all" or one role
    author: str
    at: int


_ADD = """
MERGE (c:Convention {id: $id})
ON CREATE SET c.text = $text, c.reason = $reason, c.scope = $scope, c.author = $author,
              c.at = $at, c.name = $text, c.active = true
RETURN c.id
"""
_FOR_ROLE = """
MATCH (c:Convention) WHERE c.active = true AND (c.scope = 'all' OR c.scope = $role)
RETURN c.id, c.text, c.reason, c.scope, c.author, c.at ORDER BY c.at, c.id
"""
_ALL_ACTIVE = """
MATCH (c:Convention) WHERE c.active = true
RETURN c.id, c.text, c.reason, c.scope, c.author, c.at ORDER BY c.at, c.id
"""
_RETIRE = "MATCH (c:Convention {id: $id}) SET c.active = false, c.retired_at = $at RETURN c.id"


def add_convention(
    graph: Graph, *, convention_id: str, text: str, reason: str, scope: str, author: str, at: int
) -> None:
    """Record a rule. Calling again with the same id changes nothing."""
    graph.query(
        _ADD,
        {
            "id": convention_id,
            "text": text,
            "reason": reason,
            "scope": scope,
            "author": author,
            "at": at,
        },
    )


def conventions_for(graph: Graph, role: str) -> list[Convention]:
    """The rules in force for `role`: those for everyone and those for this role."""
    rows = graph.ro_query(_FOR_ROLE, {"role": role}).result_set
    return [
        Convention(str(i), str(t), str(w), str(s), str(a), int(at)) for i, t, w, s, a, at in rows
    ]


def all_conventions(graph: Graph) -> list[Convention]:
    """Every rule in force, whoever it is for."""
    rows = graph.ro_query(_ALL_ACTIVE).result_set
    return [
        Convention(str(i), str(t), str(w), str(s), str(a), int(at)) for i, t, w, s, a, at in rows
    ]


def retire_convention(graph: Graph, convention_id: str, *, at: int) -> bool:
    """Stop a rule applying. False if there is no such rule."""
    return bool(graph.query(_RETIRE, {"id": convention_id, "at": at}).result_set)

"""What the graph remembers, by kind of memory, and what each role's session holds right now."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

from handoff.config import Config, knowledge_graph_name
from handoff.graph.connection import connect, graph_exists
from handoff.graph.conventions import conventions_for
from handoff.graph.memory_timeline import span_ms
from handoff.graph.overview import handoffs, role_stats
from handoff.graph.requests import latest_request_id, request_text
from handoff.graph.sessions import active_sessions


@dataclass(frozen=True)
class MemoryType:
    key: str
    name: str
    what: str  # one line a newcomer can read
    count: int
    detail: str


@dataclass(frozen=True)
class RoleContext:
    """What one role's session holds: its task, what it learned from others, what reached it."""

    role: str
    working_on: str
    learned: tuple[tuple[str, str], ...]  # (author role, decision text)
    inbox: int  # messages delivered to this role's sessions
    open_needs: int
    rules: int


def _count(graph: Graph, query: str) -> int:
    rows = graph.ro_query(query).result_set
    return int(rows[0][0]) if rows else 0


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _span_text(graph: Graph) -> str:
    first, last = span_ms(graph)
    minutes = (last - first) // 60_000
    return f"spanning {minutes} min" if minutes < 120 else f"spanning {minutes // 60} h"


def memory_types(graph: Graph, *, concepts: int, since: int) -> list[MemoryType]:
    """The six kinds of memory with how much of each the graph holds. `concepts` is the size of
    the knowledge graph (0 when it has not been built); `since` bounds working memory."""
    live = len(active_sessions(graph, since=since))
    requests = _count(graph, "MATCH (x:Request) RETURN count(x)")
    edits = _count(graph, "MATCH (x:Edit) RETURN count(x)")
    messages = _count(graph, "MATCH (x:Message) RETURN count(x)")
    decisions = _count(graph, "MATCH (x:Decision) RETURN count(x)")
    topics = _count(graph, "MATCH (x:Topic) RETURN count(x)")
    rules = _count(graph, "MATCH (x:Convention) WHERE x.active = true RETURN count(x)")
    replaced = _count(graph, "MATCH (x:Decision) WHERE x.superseded_at IS NOT NULL RETURN count(x)")
    reads = _count(graph, "MATCH ()-[k:CONSULTED]->() RETURN count(k)")
    agreed = _count(graph, "MATCH ()-[r:AGREES_WITH]->() RETURN count(r)")
    events = requests + edits + decisions + messages + replaced + agreed  # the whole timeline
    return [
        MemoryType(
            "working",
            "working",
            "what each live session holds right now",
            live,
            f"{_plural(live, 'live session')}",
        ),
        MemoryType(
            "episodic",
            "episodic",
            "what happened, in order, with who and when",
            requests + edits + messages,
            f"{_plural(requests, 'request')}, {_plural(edits, 'edit')}, "
            f"{_plural(messages, 'message')}",
        ),
        MemoryType(
            "semantic",
            "semantic",
            "what things mean: decisions, topics and concepts",
            decisions + topics,
            f"{_plural(decisions, 'decision')}, {_plural(topics, 'topic')} · "
            f"{_plural(concepts, 'concept')} in the concept graph",
        ),
        MemoryType(
            "procedural",
            "procedural",
            "how the team does things: standing rules",
            rules,
            f"{_plural(rules, 'rule')} in force",
        ),
        MemoryType(
            "temporal",
            "temporal",
            "when things happened, in order, and what replaced what",
            events,
            f"{_plural(events, 'event')} {_span_text(graph)} · "
            f"{_plural(replaced, 'decision')} replaced by a later one · "
            f"{_plural(agreed, 'agreement')} between roles",
        ),
        MemoryType(
            "social",
            "social",
            "who knows what from whom: reads and messages",
            reads + messages,
            f"{_plural(reads, 'read')}, {_plural(messages, 'message')}",
        ),
    ]


def role_contexts(graph: Graph, *, since: int) -> list[RoleContext]:
    """One entry per role with a session active since `since`."""
    learned: dict[str, list[tuple[str, str]]] = {}
    for h in handoffs(graph, limit=200):
        learned.setdefault(h.reader, []).extend((h.author, text) for text, _why in h.decisions)
    rows = graph.ro_query(
        "MATCH (m:Message)-[:DELIVERED_TO]->(s:Session) RETURN s.role, count(m)"
    ).result_set
    inbox = {str(role): int(n) for role, n in rows}
    stats = {s.role: s for s in role_stats(graph, since=since)}
    newest: dict[str, str] = {}
    for session in sorted(active_sessions(graph, since=since), key=lambda s: s.last_seen_at):
        request_id = latest_request_id(graph, session.id)
        text = request_text(graph, request_id) if request_id else None
        newest[session.role] = text or "no request yet"
    return [
        RoleContext(
            role=role,
            working_on=newest.get(role, "no request yet"),
            learned=tuple(dict.fromkeys(learned.get(role, []))),
            inbox=inbox.get(role, 0),
            open_needs=stats[role].open_needs,
            rules=len(conventions_for(graph, role)),
        )
        for role in stats
    ]


def concept_total(config: Config) -> int:
    """How many concepts the knowledge graph holds (0 before `handoff knowledge` has run)."""
    kg = Config(config.host, config.port, knowledge_graph_name(config), config.home)
    if not graph_exists(kg):
        return 0
    return _count(connect(kg), "MATCH (x:__Entity__) RETURN count(x)")

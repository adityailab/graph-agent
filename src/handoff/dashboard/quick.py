"""Answers to the common questions straight from the graph, with no model: instant, free, and
the same every time. Anything it does not recognise goes to the model instead."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from falkordb import Graph

from handoff.graph.conventions import all_conventions
from handoff.graph.memory_timeline import timeline
from handoff.graph.memory_view import role_contexts
from handoff.graph.overview import message_flows

MAX_WORDS = 12  # longer questions are real questions: the model answers those


@dataclass(frozen=True)
class QuickAnswer:
    answer: str  # markdown
    source: str  # where in the graph it came from


def _at(ms: int) -> str:
    return time.strftime("%H:%M", time.localtime(ms / 1000))


def _working(graph: Graph, since: int) -> QuickAnswer:
    lines = [f"- **{c.role}**: {c.working_on}" for c in role_contexts(graph, since=since)]
    return QuickAnswer("\n".join(lines) or "No session is active.", "each session's latest request")


def _rules(graph: Graph, since: int) -> QuickAnswer:
    rules = all_conventions(graph)
    if not rules:
        return QuickAnswer("No standing rules are in force.", "the standing rules (procedural)")
    lines = [
        f"- **{'everyone' if r.scope == 'all' else r.scope}**: {r.text} (why: {r.reason})"
        for r in rules
    ]
    return QuickAnswer("\n".join(lines), "the standing rules (procedural memory)")


def _replaced(graph: Graph, since: int) -> QuickAnswer:
    found = [e for e in timeline(graph) if e[0] == "replaced"]
    if not found:
        return QuickAnswer("No decision has been replaced yet.", "SUPERSEDES links (temporal)")
    lines = [f"- {_at(at)} **{role}** replaced: {text}" for _, text, role, at in found]
    return QuickAnswer("\n".join(lines), "SUPERSEDES links (temporal memory)")


def _agreed(graph: Graph, since: int) -> QuickAnswer:
    found = [e for e in timeline(graph) if e[0] == "agrees"]
    if not found:
        return QuickAnswer("No two roles have made the same decision yet.", "AGREES_WITH links")
    lines = [f"- {_at(at)} **{role}** {text}" for _, text, role, at in found]
    return QuickAnswer("\n".join(lines), "AGREES_WITH links (temporal memory)")


def _reads(graph: Graph, since: int) -> QuickAnswer:
    # for a read, the work flows from the author to the reader
    found = [f for f in message_flows(graph) if f.kind == "read"]
    if not found:
        return QuickAnswer("No session has read another's work yet.", "read links (social)")
    lines = [
        f"- **{f.target}** read **{f.source}**'s work {f.count} time{'' if f.count == 1 else 's'}"
        for f in found
    ]
    return QuickAnswer("\n".join(lines), "who read whose work (social memory)")


# (words that must all appear, any one of which may stand in) -> answer; first match wins
_INTENTS: list[tuple[list[set[str]], Callable[[Graph, int], QuickAnswer]]] = [
    ([{"replaced", "superseded"}], _replaced),
    ([{"agree", "agrees", "agreed", "agreement", "agreements"}], _agreed),
    ([{"rule", "rules", "convention", "conventions", "standing"}], _rules),
    ([{"read"}, {"whose", "who", "other", "another"}], _reads),
    ([{"working", "doing", "on"}, {"session", "sessions", "each", "everyone"}], _working),
]


def quick_answer(graph: Graph, question: str, *, since: int) -> QuickAnswer | None:
    """The answer when `question` is one of the common ones, else None."""
    words = {w.strip("?.,!").lower() for w in question.split()}
    if not words or len(question.split()) > MAX_WORDS:
        return None
    for needs, build in _INTENTS:
        if all(words & options for options in needs):
            return build(graph, since)
    return None

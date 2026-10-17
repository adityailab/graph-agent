"""How handoff answers each competition track, with numbers from the live graph."""

from __future__ import annotations

from typing import Any


def _evidence(**counts: int) -> list[dict[str, Any]]:
    return [{"label": label.replace("_", " "), "value": value} for label, value in counts.items()]


def track_summary(counts: dict[str, int]) -> list[dict[str, Any]]:
    """The two tracks, each with what it asks for, what handoff does, and live evidence."""
    return [
        {
            "id": "track-02",
            "title": "Track 02: agent memory and coordination",
            "asks": "Agents that remember across sessions and work together.",
            "how": [
                "Every request, decision and its reason is kept in one shared graph.",
                "A session reads another's work and learns the decisions behind it.",
                "Sessions message each other, wake idle ones, and a coordinator nudges.",
            ],
            "evidence": [
                {"label": "decisions with reasons", "value": counts["decisions"]},
                {"label": "reads of another session's work", "value": counts["reads"]},
                {"label": "messages between sessions", "value": counts["messages"]},
                {"label": "needs still open", "value": counts["open_needs"]},
                {"label": "file collisions found", "value": counts["collisions"]},
            ],
        },
        {
            "id": "track-01",
            "title": "Track 01: agents that act on connected data",
            "asks": "Agents that query and reason over live, connected data.",
            "how": [
                "Claude writes its own read-only Cypher over the graph to answer questions.",
                "FalkorDB's graph algorithms find load-bearing work and bridges.",
                "GraphRAG turns the work into a concept graph with citations.",
            ],
            "evidence": _evidence(
                relationships_in_the_work_graph=counts["edges"],
                concepts_extracted=counts["concepts"],
                insights_from_algorithms=counts["insights"],
            ),
        },
    ]

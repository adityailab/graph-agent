from __future__ import annotations

import json

from falkordb import Graph

from handoff.config import Config
from handoff.dashboard.state import snapshot
from handoff.graph.consultations import add_consultations
from handoff.graph.messages import add_message


def _busy(g: Graph) -> Graph:
    add_message(
        g,
        message_id="m1",
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text="avatarUrl is live",
        reply_to=None,
        at=220,
    )
    add_consultations(g, request_id="p3", consulted_ids=["p1"], at=230)
    return g


def test_the_snapshot_has_everything_the_views_draw(config: Config, two_sessions: Graph) -> None:
    _busy(two_sessions)
    state = snapshot(config, now=300, window_ms=1_000)
    assert {r["role"] for r in state["roles"]} == {"frontend", "backend"}
    assert {"asked", "DECIDED", "READ", "MESSAGE"} <= {e["kind"] for e in state["events"]}
    assert state["handoffs"][0]["decisions"][0]["reason"] == "server owns urls"
    assert state["work"]["nodes"]
    assert state["work"]["edges"]
    assert state["concepts"] == {"nodes": [], "edges": []}  # no knowledge graph yet
    json.dumps(state)  # the browser gets plain JSON


def test_the_tracks_carry_live_evidence(config: Config, two_sessions: Graph) -> None:
    _busy(two_sessions)
    tracks = {t["id"]: t for t in snapshot(config, now=300, window_ms=1_000)["tracks"]}
    assert set(tracks) == {"track-02", "track-01"}
    evidence = {e["label"]: e["value"] for e in tracks["track-02"]["evidence"]}
    assert evidence["decisions with reasons"] == 1
    assert evidence["reads of another session's work"] == 1
    assert evidence["messages between sessions"] == 1


def test_a_missing_graph_gives_an_empty_snapshot_not_an_error(config: Config) -> None:
    state = snapshot(config, now=1, window_ms=1_000)
    assert state["roles"] == []
    assert state["events"] == []
    assert state["error"] is None

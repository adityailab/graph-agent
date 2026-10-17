from __future__ import annotations

from falkordb import Graph

from handoff.graph.captions import caption
from handoff.graph.decisions import add_decision
from handoff.graph.edits import add_edit
from handoff.graph.messages import add_message
from handoff.graph.needs import add_need
from handoff.graph.requests import add_request


def test_caption_takes_the_first_line_and_shortens_it() -> None:
    assert caption("Fix the login\nsecond line") == "Fix the login"
    assert caption("  many   spaces  ") == "many spaces"
    long = caption("word " * 30, limit=20)
    assert len(long) == 20
    assert long.endswith("…")


def test_every_node_gets_a_readable_name(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="r1", text="Create Checkout.tsx", at=1)
    add_decision(
        ready,
        request_id="r1",
        decision_id="d1",
        text="Keep money in paise",
        reason="floats round",
        topic="money",
        at=2,
    )
    add_need(
        ready, request_id="r1", need_id="n1", text="return totalPaise", for_role="backend", at=3
    )
    add_edit(
        ready,
        request_id="r1",
        edit_id="e1",
        tool="Write",
        path="src/Checkout.tsx",
        summary="wrote 3 lines",
        at=4,
    )
    add_message(
        ready,
        message_id="m1",
        from_session_id="s1",
        to_role="backend",
        kind="message",
        text="Prices are in paise now",
        reply_to=None,
        at=5,
    )
    names = dict(ready.query("MATCH (n) RETURN labels(n)[0], n.name").result_set)
    assert names == {
        "Session": "frontend",
        "Request": "frontend #1: Create Checkout.tsx",
        "Decision": "Keep money in paise",
        "Topic": "money",
        "Need": "needs from backend: return totalPaise",
        "Edit": "Write src/Checkout.tsx",
        "File": "src/Checkout.tsx",
        "Message": "message: Prices are in paise now",
    }

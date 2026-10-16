from __future__ import annotations

import json
import os

import pytest
from falkordb import Graph

from handoff.standin.answer import StandinUnavailable, answer, parse_answer
from handoff.standin.claude_code import ClaudeCodeClient
from handoff.standin.context import gather_context


class FakeClient:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.seen: tuple[str, str] | None = None

    def complete(self, system: str, user: str) -> str:
        self.seen = (system, user)
        return self.reply


def test_grounded_answer_keeps_its_citations(history: Graph) -> None:
    client = FakeClient(
        json.dumps(
            {"answer": "Yes, null is fine; initials show.", "cited_ids": ["d1"], "found": True}
        )
    )
    result = answer(
        client,
        gather_context(history, role="frontend", since=0, limit=10),
        "Can avatarUrl be null?",
    )
    assert (result.text, result.cited_ids, result.found) == (
        "Yes, null is fine; initials show.",
        ("d1",),
        True,
    )
    assert client.seen is not None
    assert "[decision d1]" in client.seen[1]
    assert "Can avatarUrl be null?" in client.seen[1]


def test_invented_citations_are_dropped() -> None:
    raw = json.dumps({"answer": "x", "cited_ids": ["d1", "made-up"], "found": True})
    assert parse_answer(raw, allowed={"d1"}).cited_ids == ("d1",)


def test_json_wrapped_in_a_code_fence_is_accepted() -> None:
    raw = '```json\n{"answer": "x", "cited_ids": [], "found": false}\n```'
    assert parse_answer(raw, allowed=set()).text == "x"


def test_unusable_output_becomes_a_plain_not_found() -> None:
    result = parse_answer("I think maybe yes?", allowed={"d1"})
    assert (result.found, result.cited_ids) == (False, ())
    assert "could not" in result.text


def test_missing_claude_binary_is_reported_as_unavailable() -> None:
    with pytest.raises(StandinUnavailable):
        ClaudeCodeClient(binary="/no/such/claude").complete("system", "user")


def test_failing_claude_command_is_reported_as_unavailable() -> None:
    with pytest.raises(StandinUnavailable):
        ClaudeCodeClient(binary="false").complete("system", "user")


@pytest.mark.skipif(os.environ.get("HANDOFF_LIVE_TESTS") != "1", reason="calls Claude Code")
def test_live_stand_in_answers_from_history(history: Graph) -> None:
    result = answer(
        ClaudeCodeClient(),
        gather_context(history, role="frontend", since=0, limit=10),
        "Can avatarUrl be null?",
    )
    assert result.found
    assert "d1" in result.cited_ids

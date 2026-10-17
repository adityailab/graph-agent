from __future__ import annotations

import re

from handoff.mcp.context import ToolContext
from handoff.mcp.memory_tools import (
    conventions,
    record_convention,
    retire_convention,
    supersede_decision,
    timeline,
)
from handoff.mcp.record_tools import record_decision


def _id(reply: str) -> str:
    found = re.search(r"decision (\w+)", reply)
    assert found is not None
    return found.group(1)


def test_a_new_decision_on_a_topic_lists_the_earlier_ones_still_in_force(
    frontend: ToolContext, backend: ToolContext
) -> None:
    record_decision(frontend, "urls come from the server", "server owns urls", "profile")
    reply = record_decision(backend, "urls come from a CDN", "cheaper", "profile")
    assert "Earlier decisions on this topic still stand" in reply
    assert "(frontend): urls come from the server" in reply
    assert "supersede_decision" in reply


def test_a_decision_on_a_new_topic_has_no_such_note(frontend: ToolContext) -> None:
    assert "Earlier decisions" not in record_decision(frontend, "x", "y", "brand new topic")


def test_superseding_shows_in_the_timeline_and_stops_the_note(
    frontend: ToolContext, backend: ToolContext
) -> None:
    old = _id(record_decision(frontend, "urls come from the server", "server owns urls", "profile"))
    new = _id(record_decision(backend, "urls come from a CDN", "cheaper", "profile"))
    assert supersede_decision(backend, new, old).startswith("Decision")
    shown = timeline(backend, "profile")
    assert "replaced by" in shown
    assert "urls come from a CDN" in shown
    third = record_decision(frontend, "avatars are square", "design", "profile")
    assert "urls come from the server" not in third


def test_the_timeline_of_an_unknown_topic_says_so(frontend: ToolContext) -> None:
    assert timeline(frontend, "nothing here") == "No decisions recorded about nothing here."


def test_conventions_are_recorded_listed_and_retired(
    frontend: ToolContext, backend: ToolContext
) -> None:
    reply = record_convention(frontend, "money is integer paise", "floats round wrongly", "all")
    assert reply.startswith("Recorded convention")
    assert "money is integer paise" in conventions(backend)
    rule_id = re.search(r"convention (\w+)", reply)
    assert rule_id is not None
    assert retire_convention(frontend, rule_id.group(1)).startswith("Convention")
    assert conventions(backend) == "No conventions are in force for backend."


def test_a_convention_for_one_role_is_hidden_from_the_others(
    frontend: ToolContext, backend: ToolContext
) -> None:
    record_convention(frontend, "run the linter", "keeps diffs small", "backend")
    assert "run the linter" in conventions(backend)
    assert "run the linter" not in conventions(frontend)

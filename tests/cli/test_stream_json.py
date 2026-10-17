from __future__ import annotations

from pathlib import Path

from handoff.cli.stream_json import ToolCall, parse_stream

CAPTURE = Path(__file__).parent / "data" / "ask_stream.jsonl"  # a real run, trimmed


def test_a_real_run_gives_the_answer_and_the_cypher_it_ran() -> None:
    answer, calls = parse_stream(CAPTURE.read_text().splitlines())
    assert answer.startswith("The **frontend** session's work was read most")
    queries = [c.input["query"] for c in calls if c.name == "mcp__falkordb__query_graph_readonly"]
    assert len(queries) == 1
    assert "CONSULTED" in queries[0]
    assert [c.name for c in calls][:2] == ["ToolSearch", "mcp__handoff__graph_guide"]


def test_junk_lines_are_skipped() -> None:
    answer, calls = parse_stream(["not json", "", '{"type": "result", "result": "ok"}'])
    assert (answer, calls) == ("ok", [])


def test_a_query_less_call_is_not_listed_as_cypher() -> None:
    from handoff.cli.ask import cypher_run

    calls = [
        ToolCall("mcp__falkordb__query_graph_readonly", {}),
        ToolCall("mcp__falkordb__query_graph_readonly", {"query": "MATCH (n) RETURN n"}),
    ]
    assert cypher_run(calls) == ["MATCH (n) RETURN n"]


def test_a_call_repeated_in_the_stream_is_listed_once() -> None:
    import json

    call = {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "mcp__falkordb__query_graph_readonly",
        "input": {"query": "MATCH (n) RETURN n"},
    }
    other = {
        "type": "tool_use",
        "id": "toolu_2",
        "name": "mcp__falkordb__query_graph_readonly",
        "input": {"query": "MATCH (m) RETURN m"},
    }
    lines = [
        json.dumps({"type": "assistant", "message": {"content": [call, other]}}),
        json.dumps({"type": "assistant", "message": {"content": [call, other]}}),
        json.dumps({"type": "result", "result": "done"}),
    ]
    _, calls = parse_stream(lines)
    assert [c.input["query"] for c in calls] == ["MATCH (n) RETURN n", "MATCH (m) RETURN m"]

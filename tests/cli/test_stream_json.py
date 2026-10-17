from __future__ import annotations

from pathlib import Path

from handoff.cli.stream_json import parse_stream

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

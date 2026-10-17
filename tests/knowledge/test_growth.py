from __future__ import annotations

from pathlib import Path

import pytest
from falkordb import Graph

pytest.importorskip("graphrag_sdk")

from handoff.graph.requests import add_request
from handoff.knowledge.extractor import HANDOFF_ENTITY_TYPES, handoff_ontology
from handoff.knowledge.growth import MAX_LEARNED, Grower, accept_new_types
from handoff.knowledge.ontology_store import load_learned, save_learned
from handoff.knowledge.worker import KnowledgeWorker


def test_only_sound_new_names_are_accepted() -> None:
    proposed = [
        ("Table", "a db table"),
        ("my type", "x"),
        ("Queue", "a queue"),
        ("table", "dup"),
        ("Component", "known"),
        ("Unknown", "reserved"),
        ("X", "too short"),
        ("Pipeline", "ci"),
    ]
    got = accept_new_types(proposed, known=set(HANDOFF_ENTITY_TYPES), learned=0)
    assert [label for label, _ in got] == ["Table", "Queue", "Pipeline"]


def test_the_total_of_learned_types_is_capped() -> None:
    proposed = [(f"Kind{chr(65 + i)}{chr(97 + i)}x", "d") for i in range(10)]
    got = accept_new_types(proposed, known=set(), learned=MAX_LEARNED - 3)
    assert len(got) == 3


def test_learned_types_are_saved_per_graph_and_survive_bad_files(tmp_path: Path) -> None:
    save_learned(tmp_path, "g1", [("Table", "a table")])
    assert load_learned(tmp_path, "g1") == [("Table", "a table")]
    assert load_learned(tmp_path, "g2") == []
    (tmp_path / "ontology-g3.json").write_text("{not json")
    assert load_learned(tmp_path, "g3") == []


def test_the_ontology_includes_learned_types() -> None:
    labels = [e.label for e in handoff_ontology([("Table", "a table")]).entities]
    assert labels[-1] == "Table"
    assert len(labels) == len(HANDOFF_ENTITY_TYPES) + 1


class FakeClient:
    def __init__(self) -> None:
        self.asked: list[list[str]] = []
        self.added: list[tuple[str, str]] = []

    def suggest_types(self, texts: list[str]) -> list[tuple[str, str]]:
        self.asked.append(texts)
        return [("Table", "a db table"), ("bad name", "x")]

    def add_types(self, types: list[tuple[str, str]]) -> None:
        self.added += types


def test_after_enough_items_new_types_are_asked_for_applied_and_saved(tmp_path: Path) -> None:
    client = FakeClient()
    grower = Grower(client, tmp_path, "g", every=3)
    for n in range(2):
        grower.note(f"text {n}")
    assert client.asked == []
    grower.note("text 2")
    assert client.asked == [["text 0", "text 1", "text 2"]]
    assert client.added == [("Table", "a db table")]
    assert load_learned(tmp_path, "g") == [("Table", "a db table")]
    grower.note("text 3")  # the buffer was cleared: no second ask yet
    assert len(client.asked) == 1


def test_growth_trouble_never_stops_ingestion(ready: Graph, tmp_path: Path) -> None:
    from tests.knowledge.test_worker import FakeRag

    def boom(text: str) -> None:
        raise RuntimeError("suggest failed")

    add_request(ready, session_id="s1", request_id="p1", text="show the avatar on cards", at=10)
    rag = FakeRag()
    worker = KnowledgeWorker(graph=ready, rag=rag, home=tmp_path, grow=boom)
    assert worker.step() is True
    assert [d for d, _ in rag.ingested] == ["p1"]

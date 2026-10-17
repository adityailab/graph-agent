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
        self.labels: list[str] = []  # what the SDK's committed ontology holds
        self.asked: list[list[str]] = []
        self.added: list[tuple[str, str]] = []

    def known_labels(self) -> list[str]:
        return list(self.labels)

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


def test_at_the_cap_the_model_is_not_asked(tmp_path: Path) -> None:
    save_learned(
        tmp_path, "g", [(f"Kind{chr(65 + i)}{chr(97 + i)}x", "d") for i in range(MAX_LEARNED)]
    )
    client = FakeClient()
    grower = Grower(client, tmp_path, "g", every=2)
    grower.note("a")
    grower.note("b")
    assert client.asked == []


def test_the_cap_counts_types_the_sdk_already_holds_even_without_the_saved_file(
    tmp_path: Path,
) -> None:
    client = FakeClient()
    client.labels = [
        *HANDOFF_ENTITY_TYPES,
        *[f"Kind{chr(65 + i)}{chr(97 + i)}x" for i in range(MAX_LEARNED)],
    ]
    grower = Grower(client, tmp_path, "g", every=2)
    grower.note("a")
    grower.note("b")
    assert client.asked == []


def test_a_type_the_sdk_already_holds_is_not_proposed_again(tmp_path: Path) -> None:
    client = FakeClient()
    client.labels = [*HANDOFF_ENTITY_TYPES, "Table"]
    grower = Grower(client, tmp_path, "g", every=2)
    grower.note("a")
    grower.note("b")
    assert client.added == []  # the only acceptable proposal, Table, is already there


def test_saving_leaves_no_partial_file(tmp_path: Path) -> None:
    save_learned(tmp_path, "g", [("Table", "x")])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["ontology-g.json"]


def test_items_waiting_for_the_next_ask_survive_a_restart(tmp_path: Path) -> None:
    first = Grower(FakeClient(), tmp_path, "g", every=3)
    first.note("text 0")
    first.note("text 1")
    client = FakeClient()
    second = Grower(client, tmp_path, "g", every=3)  # a new process
    second.note("text 2")
    assert client.asked == [["text 0", "text 1", "text 2"]]
    third = Grower(FakeClient(), tmp_path, "g", every=3)
    assert third.pending == 0

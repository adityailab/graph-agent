from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from falkordb import Graph

pytest.importorskip("graphrag_sdk")

from handoff.graph.requests import add_request
from handoff.knowledge.worker import KnowledgeWorker
from handoff.models.base import ModelUnavailable


class FakeRag:
    def __init__(self, fail: bool = False) -> None:
        self.ingested: list[tuple[str, str]] = []
        self.finalized = 0
        self.fail = fail

    def ingest_sync(self, *, text: str, document_id: str, **kwargs: Any) -> None:
        if self.fail:
            raise ModelUnavailable("down")
        self.ingested.append((document_id, text))

    def finalize_sync(self) -> None:
        self.finalized += 1


def _worker(graph: Graph, rag: FakeRag, home: Path) -> KnowledgeWorker:
    clock = iter(range(1_000, 10**9, 1_000))
    return KnowledgeWorker(
        graph=graph, rag=rag, home=home, now=lambda: next(clock), finalize_every=2
    )


def test_one_step_ingests_one_item_under_our_id(ready: Graph, tmp_path: Path) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="show avatar", at=10)
    rag = FakeRag()
    worker = _worker(ready, rag, tmp_path)
    assert worker.step() is True
    assert rag.ingested == [("p1", "show avatar")]
    assert worker.step() is False  # nothing left


def test_knowledge_graph_is_finalized_after_a_batch(ready: Graph, tmp_path: Path) -> None:
    for i in range(2):
        add_request(
            ready, session_id="s1", request_id=f"p{i}", text=f"real work item {i}", at=10 + i
        )
    rag = FakeRag()
    worker = _worker(ready, rag, tmp_path)
    worker.step()
    worker.step()
    assert rag.finalized == 1


def test_a_failed_ingest_leaves_the_item_for_later(ready: Graph, tmp_path: Path) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="add the avatarUrl field", at=10)
    worker = _worker(ready, FakeRag(fail=True), tmp_path)
    assert worker.step() is False
    rows = ready.query("MATCH (r:Request {id: 'p1'}) RETURN r.kg_at").result_set
    assert rows == [[None]]


def test_only_one_worker_runs_per_machine(ready: Graph, tmp_path: Path) -> None:
    first = _worker(ready, FakeRag(), tmp_path)
    second = _worker(ready, FakeRag(), tmp_path)
    assert first.try_lead() is True
    assert second.try_lead() is False
    first.stand_down()
    assert second.try_lead() is True


def test_draining_ingests_everything_then_finalizes(ready: Graph, tmp_path: Path) -> None:
    for i in range(3):
        add_request(
            ready, session_id="s1", request_id=f"p{i}", text=f"real work item {i}", at=10 + i
        )
    rag = FakeRag()
    assert _worker(ready, rag, tmp_path).drain() == 3
    assert [d for d, _ in rag.ingested] == ["p0", "p1", "p2"]
    assert rag.finalized >= 1


def test_each_graph_has_its_own_lead(ready: Graph, tmp_path: Path) -> None:
    first = KnowledgeWorker(graph=ready, rag=FakeRag(), home=tmp_path, lock_name="graph_a")
    second = KnowledgeWorker(graph=ready, rag=FakeRag(), home=tmp_path, lock_name="graph_b")
    assert first.try_lead() is True
    assert second.try_lead() is True


def test_trivial_prompts_are_skipped_without_a_model_call(ready: Graph, tmp_path: Path) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="yes", at=10)
    rag = FakeRag()
    assert _worker(ready, rag, tmp_path).step() is True
    assert rag.ingested == []
    assert ready.query("MATCH (r:Request {id: 'p1'}) RETURN r.kg_at IS NOT NULL").result_set == [
        [True]
    ]


def test_hourly_cap_stops_ingestion(ready: Graph, tmp_path: Path) -> None:
    for i in range(3):
        add_request(
            ready, session_id="s1", request_id=f"p{i}", text=f"real work item {i}", at=10 + i
        )
    rag = FakeRag()
    worker = KnowledgeWorker(graph=ready, rag=rag, home=tmp_path, max_per_hour=2, now=lambda: 5_000)
    assert worker.drain() == 2
    assert len(rag.ingested) == 2

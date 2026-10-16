from __future__ import annotations

from collections.abc import Sequence

import pytest

pytest.importorskip("graphrag_sdk")

from handoff.config import Config
from handoff.knowledge.startup import knowledge_graph_name, start_knowledge


class NoModel:
    def complete(self, system: str, user: str) -> str:
        return "{}"


class NoEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 384


def test_knowledge_graph_sits_beside_ours(config: Config) -> None:
    assert knowledge_graph_name(config) == f"{config.graph_name}_kg"


def test_worker_can_be_switched_off(config: Config) -> None:
    worker = start_knowledge(config, NoModel(), NoEmbedder(), env={"HANDOFF_KNOWLEDGE": "off"})
    assert worker is None


def test_unreachable_database_means_no_worker_not_a_crash(config: Config) -> None:
    down = Config(host="localhost", port=1, graph_name=config.graph_name, home=config.home)
    assert start_knowledge(down, NoModel(), NoEmbedder(), env={}) is None

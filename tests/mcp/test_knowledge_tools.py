from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from falkordb import Graph

from handoff.mcp.context import ToolContext
from handoff.mcp.knowledge_tools import ask_graph, concepts
from handoff.models.base import ModelUnavailable


class FakeRag:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def completion_sync(self, question: str, **kwargs: Any) -> Any:
        if self.fail:
            raise ModelUnavailable("claude is not logged in")
        items = [
            SimpleNamespace(
                content="## Key Entities\n- avatarUrl: x", metadata={"section": "entities"}
            )
        ]
        return SimpleNamespace(
            answer="Both roles touch avatarUrl.", retriever_result=SimpleNamespace(items=items)
        )


def _ctx(graph: Graph, knowledge: Any) -> ToolContext:
    return ToolContext(graph=graph, role="backend", cwd="/w", now=lambda: 1, knowledge=knowledge)


def test_without_the_knowledge_layer_the_tools_say_how_to_enable_it(ready: Graph) -> None:
    for reply in (ask_graph(_ctx(ready, None), "q?"), concepts(_ctx(ready, None), "x")):
        assert "uv sync --extra knowledge" in reply


def test_ask_graph_answers_with_sources(kg: Graph, backend_with_decision: Graph) -> None:
    knowledge = SimpleNamespace(rag=FakeRag(), kg=kg)
    reply = ask_graph(_ctx(backend_with_decision, knowledge), "Who touches avatarUrl?")
    assert reply.startswith("Both roles touch avatarUrl.")
    assert "frontend decision d1" in reply


def test_concepts_tool_lists_linked_work(kg: Graph, backend_with_decision: Graph) -> None:
    knowledge = SimpleNamespace(rag=FakeRag(), kg=kg)
    assert "backend request p9" in concepts(_ctx(backend_with_decision, knowledge), "avatarUrl")


def test_model_failure_is_a_plain_sentence(kg: Graph, backend_with_decision: Graph) -> None:
    knowledge = SimpleNamespace(rag=FakeRag(fail=True), kg=kg)
    reply = ask_graph(_ctx(backend_with_decision, knowledge), "q?")
    assert reply.startswith("No answer from the knowledge graph:")

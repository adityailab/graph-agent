"""Answering from the knowledge graph, with the sessions' work it rests on."""

from __future__ import annotations

import re
from typing import Any

from falkordb import Graph

from handoff.format import shorten
from handoff.graph.knowledge import describe_items, entity_documents, find_entities
from handoff.graph.records import ItemRef

# "- name: description", or "- name" when the entity has no description.
_ENTITY_LINE = re.compile(r"^- (.+?)(?:: |$)", re.MULTILINE)


def _key_entities(result: Any) -> list[str]:
    """Entity names GraphRAG put in the answer's context ('## Key Entities')."""
    names: list[str] = []
    for item in getattr(result.retriever_result, "items", None) or []:
        if dict(getattr(item, "metadata", {}) or {}).get("section") == "entities":
            names.extend(m.strip() for m in _ENTITY_LINE.findall(str(item.content)))
    return names


def _ref_line(ref: ItemRef) -> str:
    return f'{ref.role} {ref.kind} {ref.id}: "{shorten(ref.text, 120)}"'


def answer_question(rag: Any, kg: Graph, graph: Graph, question: str) -> str:
    """GraphRAG's answer, followed by the requests and decisions behind its entities."""
    result = rag.completion_sync(question, return_context=True)
    docs = entity_documents(kg, _key_entities(result))
    ids = sorted({i for doc_ids in docs.values() for i in doc_ids})
    refs = describe_items(graph, ids)
    lines = [str(result.answer).strip()]
    if refs:
        lines.append("\nFrom the sessions' work:")
        lines.extend(f"- {_ref_line(r)}" for r in refs)
    return "\n".join(lines)


def find_concepts(kg: Graph, graph: Graph, query: str, *, k: int = 5) -> str:
    """Concepts matching `query`, each with the sessions' work that mentions it."""
    entities = find_entities(kg, query, k=k)
    docs = entity_documents(kg, [e.name for e in entities])
    lines = []
    for entity in entities:
        refs = describe_items(graph, docs.get(entity.name, []))
        if refs:
            kind = f" ({entity.type})" if entity.type else ""
            lines.append(f"{entity.name}{kind}: " + "; ".join(_ref_line(r) for r in refs))
    if not lines:
        return "No concepts in the knowledge graph match."
    return f'Concepts matching "{shorten(query, 60)}":\n' + "\n".join(lines)

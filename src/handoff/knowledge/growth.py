"""Letting the knowledge graph's entity types grow from the work it sees.

Every few ingested items, GraphRAG-SDK is asked which kinds of things the recent text
mentions that the current types do not cover. Sound proposals are added for future
extraction; existing entities are never re-typed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from handoff.knowledge.extractor import HANDOFF_ENTITY_TYPES
from handoff.knowledge.ontology_store import (
    load_learned,
    load_pending,
    save_learned,
    save_pending,
)

MAX_LEARNED = 20
EVERY = 10
_NAME = re.compile(r"^[A-Z][A-Za-z0-9]{2,29}$")  # CamelCase, 3 to 30 characters
_RESERVED = {"unknown", "entity", "chunk", "document", "concept"}


class TypeLearner(Protocol):
    def known_labels(self) -> list[str]: ...

    def suggest_types(self, texts: list[str]) -> list[tuple[str, str]]: ...

    def add_types(self, types: list[tuple[str, str]]) -> None: ...


def accept_new_types(
    proposed: list[tuple[str, str]], *, known: set[str], learned: int
) -> list[tuple[str, str]]:
    """The sound proposals: CamelCase, not already known (any case), not reserved, and
    within the cap on learned types."""
    seen = {k.lower() for k in known} | _RESERVED
    room = MAX_LEARNED - learned
    accepted: list[tuple[str, str]] = []
    for label, description in proposed:
        if len(accepted) >= room:
            break
        if _NAME.match(label) and label.lower() not in seen:
            seen.add(label.lower())
            accepted.append((label, description))
    return accepted


class Grower:
    def __init__(
        self, client: TypeLearner, home: Path, graph_name: str, *, every: int = EVERY
    ) -> None:
        self._client, self._home, self._graph = client, home, graph_name
        self._every = every
        self._texts: list[str] = load_pending(home, graph_name)

    @property
    def pending(self) -> int:
        """How many ingested items are waiting for the next round of learning."""
        return len(self._texts)

    def note(self, text: str) -> None:
        """Remember an ingested item; every `every` items, learn new types from them."""
        self._texts.append(text)
        if len(self._texts) < self._every:
            save_pending(self._home, self._graph, self._texts)
            return
        texts, self._texts = self._texts, []
        save_pending(self._home, self._graph, [])
        self._learn(texts)

    def _learn(self, texts: list[str]) -> None:
        saved = load_learned(self._home, self._graph)
        # The SDK's own ontology is the truth for what is learned; the saved file is a copy
        # that may be missing or stale.
        held = {k for k in self._client.known_labels() if k.lower() not in _RESERVED}
        learned_labels = {label for label, _ in saved} | (held - set(HANDOFF_ENTITY_TYPES))
        if len(learned_labels) >= MAX_LEARNED:
            return  # nothing more can be accepted, so do not pay for the model call
        known = set(HANDOFF_ENTITY_TYPES) | held | learned_labels
        new = accept_new_types(
            self._client.suggest_types(texts), known=known, learned=len(learned_labels)
        )
        if new:
            self._client.add_types(new)
            sdk_only = [(label, "") for label in sorted(learned_labels - {n for n, _ in saved})]
            save_learned(self._home, self._graph, saved + sdk_only + new)

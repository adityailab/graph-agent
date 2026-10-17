"""What the knowledge graph extracts: kinds of software work, not the assistant's mechanics.

GraphRAG-SDK's default ontology is eleven general types (Person, Location, Law, ...) and
its pipeline drops anything else. These types fit a codebase; relationship types stay
open, so the model still names whatever links it finds.
"""

from __future__ import annotations

from graphrag_sdk import Entity, Ontology
from graphrag_sdk.core.models import ExtractedEntity
from graphrag_sdk.ingestion.extraction_strategies.entity_extractors import (
    NER_PROMPT,
    LLMExtractor,
)

HANDOFF_ENTITY_TYPES = {
    "Component": "a UI component, page, module or class in the code",
    "File": "a file or folder in the project",
    "Function": "a function, method or command",
    "API": "an endpoint, route, query or other interface between parts",
    "DataField": "a field, column, key, parameter or other piece of data",
    "Service": "a running service, database, queue or deployment target",
    "Library": "a framework, library, language or external tool the project uses",
    "Setting": "a configuration value, environment variable or feature flag",
    "Concept": "a design idea, rule, unit, requirement or domain term",
}

_GUIDANCE = (
    "\n## About this text\n"
    "It is a person's request to an AI coding assistant, or a decision recorded while "
    "doing it. Extract only things about the software being built.\n"
    "- Do NOT extract the AI assistant's own tools, sessions or roles (e.g. 'handoff "
    "tool', 'ask tool', 'deploy session'), or instructions about how to reply.\n"
    "- Do NOT extract generic programming words (dict, int, string, function, file).\n"
)


def handoff_ontology() -> Ontology:
    """The entity types for a software project's knowledge graph."""
    return Ontology(
        entities=[Entity(label=k, description=v) for k, v in HANDOFF_ENTITY_TYPES.items()]
    )


class WorkExtractor(LLMExtractor):
    """GraphRAG-SDK's LLM entity extractor, told what to leave out."""

    async def extract_entities(
        self, text: str, entity_types: list[str], source_chunk_id: str
    ) -> list[ExtractedEntity]:
        prompt = NER_PROMPT.format(entity_types=", ".join(entity_types), text=text).replace(
            "## Instructions\n", _GUIDANCE + "\n## Instructions\n", 1
        )
        response = await self._llm.ainvoke(prompt)
        return self._parse_response(
            response.content, entity_types, source_chunk_id, self._threshold
        )

"""Starting the knowledge layer inside the MCP server, when it is installed and wanted."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from falkordb import Graph
from graphrag_sdk import ConnectionConfig, GraphExtraction, GraphRAG, LLMExtractor
from redis.exceptions import RedisError

from handoff.config import Config
from handoff.embed import Embedder
from handoff.graph.connection import connect
from handoff.graph.schema import EMBED_DIM
from handoff.knowledge.adapters import EmbedderAdapter, ModelLLM
from handoff.knowledge.worker import KnowledgeWorker
from handoff.models.base import ModelClient

log = logging.getLogger(__name__)


def knowledge_graph_name(config: Config) -> str:
    """The knowledge graph lives beside ours, never inside it: GraphRAG-SDK writes its own
    node types and can delete its whole graph."""
    return f"{config.graph_name}_kg"


def build_rag(
    config: Config, model: ModelClient, embedder: Embedder
) -> tuple[GraphRAG, GraphExtraction]:
    """GraphRAG over `<graph>_kg` with our model and embedder, and no fixed ontology:
    the model extracts whatever kinds of things the text is about."""
    llm = ModelLLM(model, name=type(model).__name__, max_concurrency=2)
    rag = GraphRAG(
        connection=ConnectionConfig(
            host=config.host, port=config.port, graph_name=knowledge_graph_name(config)
        ),
        llm=llm,
        embedder=EmbedderAdapter(embedder),
        embedding_dimension=EMBED_DIM,
    )
    # The LLM extractor avoids GLiNER's separate model download.
    return rag, GraphExtraction(llm, entity_extractor=LLMExtractor(llm))


@dataclass(frozen=True)
class Knowledge:
    """What the knowledge tools need: GraphRAG for answers, the knowledge graph for links."""

    rag: GraphRAG
    kg: Graph
    worker: KnowledgeWorker


def start_knowledge(
    config: Config,
    model: ModelClient,
    embedder: Embedder,
    *,
    env: Mapping[str, str],
    background: bool = True,
) -> Knowledge | None:
    """Start the knowledge layer and its ingestion worker, or return None when it is
    switched off (HANDOFF_KNOWLEDGE=off) or the database cannot be reached."""
    if env.get("HANDOFF_KNOWLEDGE", "on").strip().lower() == "off":
        return None
    try:
        graph = connect(config)
        graph.ro_query("RETURN 1")
        rag, extractor = build_rag(config, model, embedder)
    except RedisError as exc:
        log.warning("knowledge worker not started: %s", exc)
        return None
    worker = KnowledgeWorker(graph=graph, rag=rag, home=config.home, extractor=extractor)
    if background:
        worker.start()
    kg = connect(Config(config.host, config.port, knowledge_graph_name(config), config.home))
    return Knowledge(rag=rag, kg=kg, worker=worker)

"""Starting the knowledge layer inside the MCP server, when it is installed and wanted."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from falkordb import Graph
from graphrag_sdk import ConnectionConfig, GraphExtraction, GraphRAG
from redis.exceptions import RedisError

from handoff.config import Config
from handoff.embed import Embedder
from handoff.graph.connection import connect, ping
from handoff.graph.schema import EMBED_DIM
from handoff.knowledge.adapters import EmbedderAdapter, ModelLLM
from handoff.knowledge.client import KnowledgeClient
from handoff.knowledge.extractor import WorkExtractor, handoff_ontology
from handoff.knowledge.worker import KnowledgeWorker
from handoff.models.base import ModelClient

log = logging.getLogger(__name__)


def knowledge_graph_name(config: Config) -> str:
    """The knowledge graph lives beside ours, never inside it: GraphRAG-SDK writes its own
    node types and can delete its whole graph."""
    return f"{config.graph_name}_kg"


def build_knowledge_client(
    config: Config, model: ModelClient, embedder: Embedder
) -> KnowledgeClient:
    """GraphRAG over `<graph>_kg` with our model and embedder. Entity types are kinds of
    software work (see extractor.py); relationship types are left to the model."""
    llm = ModelLLM(model, name=type(model).__name__, max_concurrency=2)
    kg_name = knowledge_graph_name(config)
    rag = GraphRAG(
        connection=ConnectionConfig(host=config.host, port=config.port, graph_name=kg_name),
        llm=llm,
        embedder=EmbedderAdapter(embedder),
        embedding_dimension=EMBED_DIM,
        ontology=handoff_ontology(),
    )
    # An LLM extractor avoids GLiNER's separate model download.
    extractor = GraphExtraction(llm, entity_extractor=WorkExtractor(llm))
    kg = connect(Config(config.host, config.port, kg_name, config.home))
    return KnowledgeClient(rag=rag, llm=llm, extractor=extractor, kg=kg)


@dataclass(frozen=True)
class Knowledge:
    """What the knowledge tools need. The worker has a client of its own, so tool calls and
    ingestion never share an event loop or a connection."""

    client: KnowledgeClient
    kg: Graph
    worker: KnowledgeWorker


def start_knowledge(
    config: Config,
    model: ModelClient,
    embedder: Embedder,
    *,
    env: Mapping[str, str],
    background: bool = True,
    ingest_model: ModelClient | None = None,
) -> Knowledge | None:
    """Start the knowledge layer and its ingestion worker, or return None when it is
    switched off (HANDOFF_KNOWLEDGE=off) or the database cannot be reached."""
    if env.get("HANDOFF_KNOWLEDGE", "on").strip().lower() == "off":
        return None
    try:
        graph = connect(config)
        ping(graph)
        tools = build_knowledge_client(config, model, embedder)
        ingest = build_knowledge_client(config, ingest_model or model, embedder)
    except RedisError as exc:
        log.warning("knowledge layer not started: %s", exc)
        return None
    worker = KnowledgeWorker(
        graph=graph,
        rag=ingest,
        home=config.home,
        lock_name=f"{config.host}-{config.port}-{config.graph_name}",
        max_per_hour=int(env.get("HANDOFF_KNOWLEDGE_MAX_PER_HOUR", "60")),
    )
    if background:
        worker.start()
    return Knowledge(client=tools, kg=tools.kg, worker=worker)

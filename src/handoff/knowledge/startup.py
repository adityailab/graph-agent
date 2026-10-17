"""Starting the knowledge layer inside the MCP server, when it is installed and wanted."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from falkordb import Graph
from graphrag_sdk import ConnectionConfig, GraphExtraction, GraphRAG
from redis.exceptions import RedisError

from handoff.config import Config, knowledge_graph_name
from handoff.embed import Embedder
from handoff.graph.connection import connect, ping
from handoff.graph.insights import refresh_insights
from handoff.graph.schema import EMBED_DIM
from handoff.ids import now_ms
from handoff.knowledge.adapters import EmbedderAdapter, ModelLLM
from handoff.knowledge.client import KnowledgeClient
from handoff.knowledge.extractor import WorkExtractor, handoff_ontology
from handoff.knowledge.growth import Grower
from handoff.knowledge.lead import lock_name
from handoff.knowledge.ontology_store import load_learned
from handoff.knowledge.worker import KnowledgeWorker
from handoff.models.base import ModelClient

log = logging.getLogger(__name__)


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
        ontology=handoff_ontology(load_learned(config.home, config.graph_name)),
    )
    # An LLM extractor avoids GLiNER's separate model download.
    # Two at a time: each model call may start a `claude -p` process.
    extractor = GraphExtraction(llm, entity_extractor=WorkExtractor(llm), max_concurrency=2)
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
        lock_name=lock_name(config),
        max_per_hour=int(env.get("HANDOFF_KNOWLEDGE_MAX_PER_HOUR", "60")),
        grow=Grower(ingest, config.home, config.graph_name).note,
        refresh=lambda: refresh_insights(
            graph, ingest.kg, at=now_ms(), since=now_ms() - 7 * 24 * 60 * 60_000
        ),
    )
    if background:
        worker.start()
    return Knowledge(client=tools, kg=tools.kg, worker=worker)

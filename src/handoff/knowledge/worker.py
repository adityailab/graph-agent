"""The background worker that feeds requests and decisions into the knowledge graph.

It runs inside the MCP server. One worker per machine holds the lead (a file lock), so
several sessions never run model calls for the same work.
"""

from __future__ import annotations

import fcntl
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

from falkordb import Graph

from handoff.graph.knowledge_queue import claim_next, mark_ingested
from handoff.ids import now_ms

log = logging.getLogger(__name__)

STALE_CLAIM_MS = 10 * 60_000
IDLE_SECONDS = 5.0


class KnowledgeWorker:
    def __init__(
        self,
        *,
        graph: Graph,
        rag: Any,
        home: Path,
        extractor: Any = None,
        now: Callable[[], int] = now_ms,
        finalize_every: int = 10,
    ) -> None:
        self._graph, self._rag, self._extractor = graph, rag, extractor
        self._lock_path = home / "locks" / "knowledge-worker.lock"
        self._now, self._finalize_every = now, finalize_every
        self._since_finalize = 0
        self._lock_file: IO[str] | None = None
        self._stop = threading.Event()

    def try_lead(self) -> bool:
        """Become this machine's worker, unless another server already is."""
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._lock_path.open("a")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False
        self._lock_file = handle
        return True

    def stand_down(self) -> None:
        if self._lock_file is not None:
            fcntl.flock(self._lock_file, fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_file = None

    def step(self) -> bool:
        """Ingest one item. True if one was ingested; False if none, or it failed."""
        item = claim_next(self._graph, now=self._now(), stale_ms=STALE_CLAIM_MS)
        if item is None:
            return False
        kwargs = {"extractor": self._extractor} if self._extractor is not None else {}
        try:
            self._rag.ingest_sync(text=item.text, document_id=item.id, **kwargs)
        except Exception:
            # Model or extraction failures of any kind: the claim goes stale and the item
            # is tried again later; the backbone graph is unaffected.
            log.exception("knowledge ingest failed for %s", item.id)
            return False
        mark_ingested(self._graph, item.id, at=self._now())
        self._since_finalize += 1
        if self._since_finalize >= self._finalize_every:
            self._rag.finalize_sync()
            self._since_finalize = 0
        return True

    def drain(self) -> int:
        """Ingest everything pending, finalize, and return how many items went in."""
        count = 0
        while self.step():
            count += 1
        if self._since_finalize:
            self._rag.finalize_sync()
            self._since_finalize = 0
        return count

    def run(self) -> None:
        """Loop until stopped: lead if possible, ingest, rest when there is nothing to do."""
        while not self._stop.is_set():
            if self._lock_file is None and not self.try_lead():
                self._stop.wait(60)
                continue
            try:
                worked = self.step()
            except Exception:
                log.exception("knowledge worker step failed")  # e.g. database down
                worked = False
            if not worked:
                if self._since_finalize:
                    self._rag.finalize_sync()
                    self._since_finalize = 0
                self._stop.wait(IDLE_SECONDS)
        self.stand_down()

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, name="knowledge-worker", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

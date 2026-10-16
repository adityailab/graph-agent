"""The background worker that feeds requests and decisions into the knowledge graph.

It runs inside the MCP server, or alone as `handoff-knowledge`. One worker per graph per
machine holds the lead (a file lock), so sessions never run model calls for the same work.
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
from handoff.knowledge.pacing import Pacer

log = logging.getLogger(__name__)

STALE_CLAIM_MS = 10 * 60_000
IDLE_SECONDS = 5.0
MIN_REQUEST_CHARS = 10  # "yes", "continue", "go ahead" carry no knowledge worth a model call


class KnowledgeWorker:
    def __init__(
        self,
        *,
        graph: Graph,
        rag: Any,
        home: Path,
        lock_name: str = "default",
        now: Callable[[], int] = now_ms,
        finalize_every: int = 10,
        max_per_hour: int = 60,
    ) -> None:
        self._graph, self._rag, self._now = graph, rag, now
        self._lock_path = home / "locks" / f"knowledge-{lock_name}.lock"
        self._finalize_every, self._since_finalize = finalize_every, 0
        self._pacer = Pacer(max_per_hour=max_per_hour)
        self._lock_file: IO[str] | None = None
        self._stop = threading.Event()

    def try_lead(self) -> bool:
        """Become this graph's worker on this machine, unless another one already is."""
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
        """Handle one item. True if one was ingested or skipped; False if none was
        available, the hourly cap is reached, or the ingest failed."""
        now = self._now()
        if not self._pacer.allows(now):
            return False
        item = claim_next(self._graph, now=now, stale_ms=STALE_CLAIM_MS)
        if item is None:
            return False
        if item.label == "Request" and item.size < MIN_REQUEST_CHARS:
            mark_ingested(self._graph, item, at=now)
            return True
        try:
            self._rag.ingest_sync(text=item.text, document_id=item.id)
        except Exception:
            # Model, extraction or database trouble of any kind: the item is retried later
            # with backoff (see knowledge_queue); the backbone graph is unaffected.
            log.exception("knowledge ingest failed for %s", item.id)
            self._pacer.failed()
            return False
        mark_ingested(self._graph, item, at=self._now())
        self._pacer.ingested(now)
        self._since_finalize += 1
        if self._since_finalize >= self._finalize_every:
            self._finalize()
        return True

    def _finalize(self) -> None:
        if self._since_finalize:
            self._rag.finalize_sync()
            self._since_finalize = 0

    def drain(self) -> int:
        """Handle everything pending (within the cap), finalize, and return the count."""
        count = 0
        while self.step():
            count += 1
        self._finalize()
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
                self._pacer.failed()
                worked = False
            if not worked:
                self._finalize()
                self._stop.wait(self._pacer.pause_seconds(IDLE_SECONDS))
        self.stand_down()

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, name="knowledge-worker", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

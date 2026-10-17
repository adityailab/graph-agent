"""The background worker that feeds requests and decisions into the knowledge graph.

It runs inside the MCP server, or alone as `handoff-knowledge`. One worker per graph per
machine holds the lead (a file lock), so sessions never run model calls for the same work.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from falkordb import Graph

from handoff.graph.knowledge_queue import claim_next, mark_ingested
from handoff.ids import now_ms
from handoff.knowledge.pacing import Pacer
from handoff.leader import LeaderLock

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
        refresh: Callable[[], None] | None = None,
        grow: Callable[[str], None] | None = None,
    ) -> None:
        self._graph, self._rag, self._now = graph, rag, now
        self._lock = LeaderLock(home / "locks" / f"knowledge-{lock_name}.lock")
        self._finalize_every, self._since_finalize = finalize_every, 0
        self._pacer = Pacer(max_per_hour=max_per_hour)
        self._stop = threading.Event()
        self._refresh = refresh  # e.g. recompute insights once new concepts are in
        self._grow = grow  # told each ingested text, so entity types can grow

    def try_lead(self) -> bool:
        """Become this graph's worker on this machine, unless another one already is."""
        return self._lock.acquire()

    def stand_down(self) -> None:
        """Give up the lead."""
        self._lock.release()

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
        self._note_growth(item.text)
        self._since_finalize += 1
        if self._since_finalize >= self._finalize_every:
            self._finalize()
        return True

    def _note_growth(self, text: str) -> None:
        if self._grow is None:
            return
        try:
            self._grow(text)
        except Exception:
            # Learning new types is optional: whatever goes wrong (model, database, bad
            # proposal) must never stop ingestion.
            log.exception("learning new entity types failed")

    def _finalize(self) -> None:
        if self._since_finalize:
            self._rag.finalize_sync()
            self._since_finalize = 0
            if self._refresh is not None:
                self._refresh()

    def drain(self) -> int:
        """Handle everything pending (within the cap), finalize, and return the count."""
        count = 0
        while self.step():
            count += 1
        self._finalize()
        return count

    def run(self) -> None:
        """Loop until stopped: lead if possible, ingest, rest when there is nothing to do."""
        try:
            while not self._stop.is_set():
                if not self._lock.held and not self.try_lead():
                    self._stop.wait(60)
                    continue
                if not self._guarded(self.step):
                    self._guarded(self._finalize)
                    self._stop.wait(self._pacer.pause_seconds(IDLE_SECONDS))
        finally:
            self.stand_down()

    def _guarded(self, work: Callable[[], object]) -> bool:
        """Run one piece of the loop. A failure of any kind (database down, model or
        query error) is logged and paced, never allowed to end the worker's thread."""
        try:
            return bool(work())
        except Exception:
            log.exception("knowledge worker: %s failed", getattr(work, "__name__", "work"))
            self._pacer.failed()
            return False

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, name="knowledge-worker", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

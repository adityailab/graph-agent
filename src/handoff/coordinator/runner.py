"""The coordinator's loop: one per graph on this machine, applying the rules every so often."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from falkordb import Graph

from handoff.coordinator.rules import Thresholds, run_rules
from handoff.ids import now_ms
from handoff.leader import LeaderLock

log = logging.getLogger(__name__)

INTERVAL_SECONDS = 30.0


class Coordinator:
    def __init__(
        self,
        *,
        graph: Graph,
        home: Path,
        lock_name: str,
        thresholds: Thresholds,
        interval: float = INTERVAL_SECONDS,
        rules: Callable[..., list[Any]] = run_rules,
        dry_run: bool = False,
    ) -> None:
        self._graph, self._thresholds, self._interval = graph, thresholds, interval
        self._rules, self._dry_run = rules, dry_run
        self._lock = LeaderLock(home / "locks" / f"coordinator-{lock_name}.lock")
        self._stop = threading.Event()

    def try_lead(self) -> bool:
        """Become this graph's coordinator unless another one already is."""
        return self._lock.acquire()

    def stand_down(self) -> None:
        self._lock.release()

    def run(self) -> None:
        """Apply the rules until stopped. A failed pass (database down, query error) is
        logged and retried on the next one; it never ends the loop."""
        try:
            while not self._stop.is_set():
                if self._lock.acquire():
                    try:
                        self._rules(
                            self._graph,
                            now=now_ms(),
                            thresholds=self._thresholds,
                            dry_run=self._dry_run,
                        )
                    except Exception:
                        log.exception("coordinator pass failed")
                self._stop.wait(self._interval)
        finally:
            self.stand_down()

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, name="coordinator", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

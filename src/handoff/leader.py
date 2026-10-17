"""One holder at a time for a background job, using a lock file the OS releases on exit."""

from __future__ import annotations

import fcntl
from pathlib import Path
from typing import IO


class LeaderLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle: IO[str] | None = None

    @property
    def held(self) -> bool:
        """True while this object holds the lock."""
        return self._handle is not None

    def acquire(self) -> bool:
        """Become the holder unless another process already is (true if already ours)."""
        if self.held:
            return True
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._path.open("a")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False
        self._handle = handle
        return True

    def release(self) -> None:
        """Give the lock up (does nothing if not held)."""
        if self._handle is not None:
            fcntl.flock(self._handle, fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None

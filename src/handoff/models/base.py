"""What every model backend provides."""

from __future__ import annotations

from typing import Protocol


class ModelUnavailable(Exception):  # noqa: N818 - reads as a state, matching how it is used
    """The model could not be reached, refused, or failed."""


class ModelClient(Protocol):
    def complete(self, system: str, user: str) -> str:
        """Return the model's reply text. Raises ModelUnavailable on any failure."""
        ...

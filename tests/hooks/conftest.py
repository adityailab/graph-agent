from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def hook_json() -> Callable[[str], dict[str, Any]]:
    """Load a captured hook input by name, e.g. hook_json("post_edit")."""

    def load(name: str) -> dict[str, Any]:
        data: dict[str, Any] = json.loads((_FIXTURES / f"{name}.json").read_text())
        return data

    return load

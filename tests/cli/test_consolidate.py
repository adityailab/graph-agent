from __future__ import annotations

from pathlib import Path

import pytest

from handoff.cli.app import main
from handoff.config import Config


def test_consolidate_reports_when_there_is_nothing_yet(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    config: Config,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANDOFF_GRAPH", config.graph_name)
    monkeypatch.setenv("HANDOFF_HOME", str(config.home))
    assert main(["consolidate"]) == 0
    assert "No work recorded yet" in capsys.readouterr().out

from __future__ import annotations

import pytest

from handoff.cli.app import main


def test_demo_needs_claude_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("handoff.cli.demo.shutil.which", lambda name: None)
    assert main(["demo"]) == 1
    assert "Claude Code" in capsys.readouterr().err


def test_live_demo_needs_tmux(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("handoff.cli.demo.shutil.which", lambda n: None if n == "tmux" else "/b")
    assert main(["demo", "--live"]) == 1
    assert "brew install tmux" in capsys.readouterr().err

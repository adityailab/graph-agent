from __future__ import annotations

from pathlib import Path

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


def test_demo_refuses_a_real_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("handoff.cli.demo.shutil.which", lambda name: "/bin/" + name)
    (tmp_path / "main.py").write_text("my real project")
    assert main(["demo", "--workspace", str(tmp_path)]) == 1
    assert (tmp_path / "main.py").exists()
    assert "not touched" in capsys.readouterr().err


def test_the_demo_graph_name_is_namespaced() -> None:
    from handoff.cli import demo

    assert demo.DEFAULT_GRAPH == "handoff_demo"

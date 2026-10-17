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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("handoff.cli.demo.shutil.which", lambda n: None if n == "tmux" else "/b")
    assert main(["demo", "--live", "--workspace", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "brew install tmux" in err
    assert "handoff demo" in err  # the headless demo needs no tmux


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


def test_a_missing_prerequisite_leaves_the_workspace_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from handoff.demo.scratch import MARKER

    (tmp_path / MARKER).write_text("made by the demo")
    (tmp_path / "keep.txt").write_text("a previous run's file")
    monkeypatch.setattr("handoff.cli.demo.shutil.which", lambda n: None if n == "tmux" else "/b")
    assert main(["demo", "--live", "--workspace", str(tmp_path)]) == 1
    assert (tmp_path / "keep.txt").exists()  # nothing was reset before the check failed


def _spy(monkeypatch: pytest.MonkeyPatch, *, tmux: bool, interactive: bool) -> list[str]:
    """Pretend tmux and a terminal are (not) there; record which mode starts."""
    started: list[str] = []
    monkeypatch.setattr(
        "handoff.cli.demo.shutil.which", lambda n: None if n == "tmux" and not tmux else "/b"
    )
    monkeypatch.setattr("handoff.cli.demo._interactive", lambda: interactive)

    def live(*args: object, **kwargs: object) -> int:
        started.append("live")
        return 0

    def headless(*args: object, **kwargs: object) -> int:
        started.append("headless")
        return 0

    monkeypatch.setattr("handoff.cli.demo._live", live)
    monkeypatch.setattr("handoff.cli.demo._headless", headless)
    return started


def test_the_grid_is_the_default_with_tmux_at_a_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = _spy(monkeypatch, tmux=True, interactive=True)
    assert main(["demo", "--workspace", str(tmp_path / "d")]) == 0
    assert started == ["live"]


def test_headless_can_be_asked_for(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = _spy(monkeypatch, tmux=True, interactive=True)
    assert main(["demo", "--headless", "--workspace", str(tmp_path / "d")]) == 0
    assert started == ["headless"]


def test_without_tmux_the_default_falls_back_to_headless(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    started = _spy(monkeypatch, tmux=False, interactive=True)
    assert main(["demo", "--workspace", str(tmp_path / "d")]) == 0
    assert started == ["headless"]
    assert "tmux" in capsys.readouterr().out


def test_without_a_terminal_the_default_is_headless(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = _spy(monkeypatch, tmux=True, interactive=False)
    assert main(["demo", "--workspace", str(tmp_path / "d")]) == 0
    assert started == ["headless"]


def test_the_grid_runs_on_haiku_unless_told_otherwise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def fake_launch(
        session: str, folder: Path, config: object, runner: object, **kw: object
    ) -> str:
        seen.append(str(kw["model"]))
        return "launched"

    monkeypatch.setattr("handoff.cli.demo.shutil.which", lambda n: "/b")
    monkeypatch.setattr("handoff.cli.demo._interactive", lambda: False)  # no attach
    monkeypatch.setattr("handoff.cli.demo.launch", fake_launch)
    monkeypatch.setattr("handoff.cli.demo.start_mission_control", lambda *a, **k: "http://x/")
    monkeypatch.setattr("handoff.cli.demo.reset_graphs", lambda config: None)
    assert main(["demo", "--live", "--workspace", str(tmp_path / "d")]) == 0
    assert main(["demo", "--live", "--model", "sonnet", "--workspace", str(tmp_path / "e")]) == 0
    assert seen == ["haiku", "sonnet"]


def test_the_grid_comes_with_mission_control_in_the_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[str] = []
    started: list[Path] = []

    def fake_mission(folder: Path, state: Path, *, port: int) -> str:
        started.append(folder)
        return f"http://127.0.0.1:{port}/"

    monkeypatch.setattr("handoff.cli.demo.shutil.which", lambda n: "/b")
    monkeypatch.setattr("handoff.cli.demo._interactive", lambda: True)
    monkeypatch.setattr("handoff.cli.demo.launch", lambda *a, **k: "launched")
    monkeypatch.setattr("handoff.cli.demo.reset_graphs", lambda config: None)
    monkeypatch.setattr("handoff.cli.demo.start_mission_control", fake_mission)
    monkeypatch.setattr("handoff.cli.demo.webbrowser.open", opened.append)
    monkeypatch.setattr("handoff.cli.demo.os.execvp", lambda *a: None)  # do not attach
    assert main(["demo", "--live", "--workspace", str(tmp_path / "d")]) == 0
    assert started == [(tmp_path / "d").resolve()]
    assert opened == ["http://127.0.0.1:8765/#orchestration"]

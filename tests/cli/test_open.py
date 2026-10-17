from __future__ import annotations

from pathlib import Path

import pytest

from handoff.cli.app import main


@pytest.fixture(autouse=True)
def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANDOFF_GRAPH", "handoff_demo")


def test_print_gives_the_mission_control_address(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["open", "--print"]) == 0
    assert capsys.readouterr().out.strip() == "http://127.0.0.1:8765/"


def test_print_honours_a_port(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["open", "dashboard", "--port", "9000", "--print"]) == 0
    assert capsys.readouterr().out.strip() == "http://127.0.0.1:9000/"


def test_graph_opens_the_falkordb_browser_on_this_projects_graph(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["open", "graph", "--print"]) == 0
    assert capsys.readouterr().out.strip() == "http://localhost:3000/graph?graph=handoff_demo"


def test_guide_opens_the_published_guide(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["open", "guide", "--print"]) == 0
    assert "github.com/adityailab/graph-agent" in capsys.readouterr().out


def test_a_dashboard_that_is_not_running_says_how_to_start_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("handoff.cli.open_cmd.is_listening", lambda host, port: False)
    assert main(["open"]) == 1
    assert "handoff dashboard" in capsys.readouterr().err


def test_a_running_dashboard_is_opened_in_the_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []
    monkeypatch.setattr("handoff.cli.open_cmd.is_listening", lambda host, port: True)
    monkeypatch.setattr("handoff.cli.open_cmd.webbrowser.open", lambda url: opened.append(url))
    assert main(["open"]) == 0
    assert opened == ["http://127.0.0.1:8765/"]

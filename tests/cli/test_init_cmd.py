from __future__ import annotations

import json
from pathlib import Path

import pytest

from handoff.cli.app import main
from tests.cli.fakes import fake_runner


def test_init_installs_into_the_folder_using_the_running_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr("handoff.cli.init_cmd.run_command", fake_runner(calls))
    monkeypatch.setattr("handoff.cli.init_cmd.shutil.which", lambda n: f"/usr/bin/{n}")
    assert main(["init", str(tmp_path)]) == 0
    assert (tmp_path / ".mcp.json").exists()
    assert "already running" in capsys.readouterr().out
    assert not any(c[:2] == ["docker", "run"] for c in calls)


def test_init_stops_with_the_fix_when_claude_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("handoff.cli.init_cmd.run_command", fake_runner([]))
    monkeypatch.setattr(
        "handoff.cli.init_cmd.shutil.which", lambda n: None if n == "claude" else f"/b/{n}"
    )
    assert main(["init", str(tmp_path)]) == 1
    assert "Claude Code" in capsys.readouterr().err
    assert not (tmp_path / ".mcp.json").exists()


def test_without_npx_init_installs_without_falkordbs_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("handoff.cli.init_cmd.run_command", fake_runner([]))
    monkeypatch.setattr(
        "handoff.cli.init_cmd.shutil.which", lambda n: None if n == "npx" else f"/b/{n}"
    )
    assert main(["init", str(tmp_path)]) == 0
    servers = json.loads((tmp_path / ".mcp.json").read_text())["mcpServers"]
    assert "falkordb" not in servers


def test_malformed_settings_are_one_sentence_not_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("handoff.cli.init_cmd.run_command", fake_runner([]))
    monkeypatch.setattr("handoff.cli.init_cmd.shutil.which", lambda n: f"/b/{n}")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text("{broken")
    assert main(["init", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "settings.local.json" in err
    assert "Traceback" not in err


def test_an_unreachable_remote_database_is_not_blamed_on_docker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HANDOFF_DB_HOST", "db.example.invalid")
    monkeypatch.setattr("handoff.cli.init_cmd.run_command", fake_runner([], code=1))
    monkeypatch.setattr("handoff.cli.init_cmd.shutil.which", lambda n: f"/b/{n}")
    assert main(["init", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "db.example.invalid" in err
    assert "Docker is not running" not in err

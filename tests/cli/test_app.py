from __future__ import annotations

from pathlib import Path

import pytest

from handoff.cli.app import main

# Each task adds the commands it builds.
BUILT = ("init", "install", "status", "log", "knowledge", "doctor")


def test_every_built_command_is_listed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for name in BUILT:
        assert name in out


def test_install_refuses_a_missing_folder(tmp_path: Path) -> None:
    assert main(["install", str(tmp_path / "nope")]) == 1


def test_install_sets_up_a_folder(tmp_path: Path) -> None:
    assert main(["install", str(tmp_path)]) == 0
    assert (tmp_path / ".mcp.json").exists()

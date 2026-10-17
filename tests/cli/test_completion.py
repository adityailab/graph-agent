from __future__ import annotations

import pytest

from handoff.cli.app import main


def test_the_zsh_script_lists_the_commands(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["completion", "zsh"]) == 0
    out = capsys.readouterr().out
    assert "compdef" in out
    assert "dashboard" in out


def test_the_bash_script_lists_the_commands(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["completion", "bash"]) == 0
    out = capsys.readouterr().out
    assert "complete -F" in out
    assert "status" in out

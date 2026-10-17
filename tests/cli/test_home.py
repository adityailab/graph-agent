from __future__ import annotations

import pytest

from handoff.cli.app import main
from handoff.cli.home import HomeState, render_home
from handoff.cli.style import Palette


def test_the_home_screen_groups_every_command() -> None:
    text = render_home(Palette(False), HomeState(database=True, sessions=2, open_needs=1))
    for command in ("init", "demo", "dashboard", "status", "send", "ask", "doctor", "completion"):
        assert command in text
    assert "2 sessions" in text
    assert "1 open need" in text


def test_without_a_database_the_next_step_is_init() -> None:
    text = render_home(Palette(False), HomeState(database=False, sessions=0, open_needs=0))
    assert "handoff init" in text.split("next:")[1]


def test_with_sessions_the_next_step_is_the_dashboard() -> None:
    text = render_home(Palette(False), HomeState(database=True, sessions=1, open_needs=0))
    assert "handoff dashboard" in text.split("next:")[1]


def test_running_handoff_alone_shows_the_home_screen_not_an_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 0
    assert "commands" in capsys.readouterr().out


def test_a_mistyped_command_suggests_the_closest_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_:
        main(["stat"])
    assert exit_.value.code == 2
    assert "Did you mean 'status'?" in capsys.readouterr().err


def test_version_is_printed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_:
        main(["--version"])
    assert exit_.value.code == 0
    assert "handoff 0." in capsys.readouterr().out

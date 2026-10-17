from __future__ import annotations

from handoff.demo.tmux import done_line, layout_commands, pane_ready, panes_by_role, trust_pending


def test_the_grid_has_three_sessions_and_the_live_feed() -> None:
    cmds = layout_commands(
        "hd",
        "/w",
        path="/opt/bin:/usr/bin",
        home="/Users/me",
        user="me",
        handoff_bin="/opt/h/bin/handoff",
        model="sonnet",
    )
    assert cmds[0][:4] == ["tmux", "new-session", "-d", "-s"]
    started = [c[-1] for c in cmds if c[1] in ("new-session", "split-window")]
    assert len(started) == 4
    for role in ("frontend", "deploy", "backend"):
        line = next(s for s in started if f"HANDOFF_ROLE={role}" in s)
        assert line.startswith("env -i HOME=/Users/me USER=me")  # nothing else leaks in
        assert "PATH=/opt/bin:/usr/bin" in line
        assert line.endswith("claude --model sonnet --permission-mode acceptEdits")
    assert started[-1].endswith("/opt/h/bin/handoff watch")
    assert ["tmux", "select-layout", "-t", "hd:demo", "tiled"] in cmds


def test_the_newest_done_line_is_found() -> None:
    screen = "✻ Brewed for 8s · done 12:26 PM\nlater\n✻ Cooked for 1m 3s · done 12:29 PM\n> "
    assert done_line(screen) == "for 1m 3s · done 12:29 PM"
    assert done_line("> ") == ""


def test_the_folder_trust_prompt_is_noticed() -> None:
    assert trust_pending(" > No, exit\n   Yes, I trust this folder")
    assert not trust_pending("> ")


def test_panes_are_found_by_the_role_they_were_started_with() -> None:
    listing = (
        "0 env -i HOME=/h HANDOFF_ROLE=frontend claude --model sonnet\n"
        "1 env -i HOME=/h HANDOFF_ROLE=deploy claude --model sonnet\n"
        "3 env -i HOME=/h /opt/h/bin/handoff watch\n"
    )
    assert panes_by_role(listing, "hd") == {"frontend": "hd:demo.0", "deploy": "hd:demo.1"}


def test_a_pane_is_ready_once_claude_shows_its_input_and_no_trust_prompt() -> None:
    assert not pane_ready("")  # still starting
    assert not pane_ready(" > No, exit\n   Yes, I trust this folder")
    assert pane_ready("> \n  accept edits on (shift+tab to cycle)")


def test_a_working_spinner_is_recognised() -> None:
    from handoff.demo.tmux import working

    assert working("\u2722 Crunching\u2026 (9s \u00b7 \u2193 1.4k tokens)")
    assert working("* Cogitating\u2026 (1m 3s \u00b7 thinking)")
    assert not working("Cooked for 3s \u00b7 done 1:40 PM\n> ")

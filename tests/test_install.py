from __future__ import annotations

import json
from pathlib import Path

from handoff.config import Config
from handoff.install import install


def _read(path: Path) -> dict:  # type: ignore[type-arg]
    data: dict = json.loads(path.read_text())  # type: ignore[type-arg]
    return data


def test_fresh_workspace_gets_hooks_and_both_servers(tmp_path: Path, config: Config) -> None:
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    hooks = _read(tmp_path / ".claude" / "settings.local.json")["hooks"]
    assert set(hooks) == {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"}
    stop_commands = [h for group in hooks["Stop"] for h in group["hooks"]]
    assert {"type": "command", "command": "/opt/h/bin/handoff-hook"} in stop_commands
    waiter = next(h for h in stop_commands if h["command"].endswith("handoff-hook wait"))
    assert waiter["asyncRewake"] is True
    servers = _read(tmp_path / ".mcp.json")["mcpServers"]
    assert servers["handoff"]["command"] == "/opt/h/bin/handoff-mcp"
    assert servers["falkordb"]["env"]["FALKORDB_STRICT_READONLY"] == "true"


def test_existing_settings_and_servers_are_kept(tmp_path: Path, config: Config) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text(
        json.dumps(
            {
                "permissions": {"allow": ["Bash(ls)"]},
                "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "say done"}]}]},
            }
        )
    )
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    settings = _read(tmp_path / ".claude" / "settings.local.json")
    assert settings["permissions"] == {"allow": ["Bash(ls)"]}
    stop = [h["command"] for g in settings["hooks"]["Stop"] for h in g["hooks"]]
    assert "say done" in stop
    assert "other" in _read(tmp_path / ".mcp.json")["mcpServers"]


def test_installing_twice_changes_nothing(tmp_path: Path, config: Config) -> None:
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    first = (tmp_path / ".claude" / "settings.local.json").read_text()
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    assert (tmp_path / ".claude" / "settings.local.json").read_text() == first


def test_falkordb_server_can_be_left_out(tmp_path: Path, config: Config) -> None:
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config, falkordb_mcp=False)
    assert "falkordb" not in _read(tmp_path / ".mcp.json")["mcpServers"]


def test_install_explains_how_to_start_each_role(tmp_path: Path, config: Config) -> None:
    text = install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    assert "HANDOFF_ROLE=frontend claude" in text
    assert "handoff init" in text  # how to get the database running
    assert "handoff knowledge" in text
    assert "docker compose" not in text


def test_command_refuses_a_missing_folder(tmp_path: Path) -> None:
    from handoff.main import main

    assert main(["install", str(tmp_path / "nope")]) == 1


def test_command_installs_into_a_folder(tmp_path: Path) -> None:
    from handoff.main import main

    assert main(["install", str(tmp_path)]) == 0
    assert (tmp_path / ".mcp.json").exists()


def test_each_workspace_gets_its_own_graph(tmp_path: Path, config: Config) -> None:
    first, second = tmp_path / "a" / "shop", tmp_path / "b" / "shop"
    for workspace in (first, second):
        workspace.mkdir(parents=True)
        install(workspace, bin_dir=Path("/opt/h/bin"), config=config)
    names = [
        _read(w / ".claude" / "settings.local.json")["env"]["HANDOFF_GRAPH"]
        for w in (first, second)
    ]
    assert names[0] != names[1]
    assert all(name.startswith("handoff_shop_") for name in names)


def test_a_graph_already_chosen_is_kept(tmp_path: Path, config: Config) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text(
        json.dumps({"env": {"HANDOFF_GRAPH": "team", "OTHER": "1"}})
    )
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    env = _read(tmp_path / ".claude" / "settings.local.json")["env"]
    assert env == {"HANDOFF_GRAPH": "team", "OTHER": "1"}


def test_graph_can_be_named_explicitly(tmp_path: Path, config: Config) -> None:
    text = install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config, graph="demo")
    assert _read(tmp_path / ".claude" / "settings.local.json")["env"]["HANDOFF_GRAPH"] == "demo"
    assert "demo" in text


def test_our_server_gets_the_workspace_graph_literally(tmp_path: Path, config: Config) -> None:
    """Claude Code expands ${VAR} in .mcp.json from the shell, not from settings env, so a
    graph chosen in settings would otherwise never reach the MCP server."""
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    graph = _read(tmp_path / ".claude" / "settings.local.json")["env"]["HANDOFF_GRAPH"]
    server_env = _read(tmp_path / ".mcp.json")["mcpServers"]["handoff"]["env"]
    assert server_env["HANDOFF_GRAPH"] == graph
    assert server_env["HANDOFF_ROLE"] == "${HANDOFF_ROLE:-}"  # still per terminal


def test_a_custom_database_address_reaches_sessions_and_the_server(tmp_path: Path) -> None:
    custom = Config("db.local", 6390, "g", tmp_path / "home")
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=custom)
    env = _read(tmp_path / ".claude" / "settings.local.json")["env"]
    assert (env["HANDOFF_DB_HOST"], env["HANDOFF_DB_PORT"]) == ("db.local", "6390")
    server = _read(tmp_path / ".mcp.json")["mcpServers"]["handoff"]["env"]
    assert (server["HANDOFF_DB_HOST"], server["HANDOFF_DB_PORT"]) == ("db.local", "6390")


def test_the_default_address_is_not_written(tmp_path: Path, config: Config) -> None:
    default = Config("localhost", 6379, "g", config.home)
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=default)
    assert "HANDOFF_DB_PORT" not in _read(tmp_path / ".claude" / "settings.local.json")["env"]


def test_a_graph_exported_in_the_shell_is_used_when_nothing_else_chooses(
    tmp_path: Path, config: Config
) -> None:
    text = install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config, default_graph="team")
    assert _read(tmp_path / ".claude" / "settings.local.json")["env"]["HANDOFF_GRAPH"] == "team"
    assert "team" in text


def test_settings_that_already_choose_a_graph_beat_the_exported_one(
    tmp_path: Path, config: Config
) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text(
        json.dumps({"env": {"HANDOFF_GRAPH": "shop"}})
    )
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config, default_graph="team")
    assert _read(tmp_path / ".claude" / "settings.local.json")["env"]["HANDOFF_GRAPH"] == "shop"


def test_the_setup_message_says_how_to_open_mission_control(tmp_path: Path, config: Config) -> None:
    text = install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    assert "handoff dashboard" in text
    assert "http://127.0.0.1:8765/" in text

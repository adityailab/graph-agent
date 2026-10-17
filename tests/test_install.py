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
    assert "docker compose up -d" in text


def test_command_refuses_a_missing_folder(tmp_path: Path) -> None:
    from handoff.main import main

    assert main(["install", str(tmp_path / "nope")]) == 1


def test_command_installs_into_a_folder(tmp_path: Path) -> None:
    from handoff.main import main

    assert main(["install", str(tmp_path)]) == 0
    assert (tmp_path / ".mcp.json").exists()

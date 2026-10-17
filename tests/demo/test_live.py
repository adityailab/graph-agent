from __future__ import annotations

import json
from pathlib import Path

from handoff.config import Config
from handoff.demo.live import prepare_workspace


def test_the_live_workspace_needs_no_permission_prompts_for_our_tools(tmp_path: Path) -> None:
    config = Config("localhost", 6379, "live", tmp_path / "home")
    prepare_workspace(tmp_path, config, bin_dir=Path("/opt/h/bin"))
    settings = json.loads((tmp_path / ".claude" / "settings.local.json").read_text())
    assert settings["permissions"]["allow"] == ["mcp__handoff"]
    assert settings["enableAllProjectMcpServers"] is True
    assert settings["env"]["HANDOFF_GRAPH"] == "live"
    assert settings["env"]["HANDOFF_HOME"] == str(tmp_path / "home")
    assert settings["env"]["HANDOFF_MODEL_NAME"] == "haiku"


def test_a_new_driver_stops_the_previous_one(tmp_path: Path) -> None:
    import subprocess
    import sys

    from handoff.demo.live import stop_previous_driver

    old = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    (tmp_path / "driver.pid").write_text(str(old.pid))
    try:
        stop_previous_driver(tmp_path)
        assert old.wait(timeout=5) is not None
        assert not (tmp_path / "driver.pid").exists()
        stop_previous_driver(tmp_path)  # nothing left to stop: harmless
    finally:
        old.kill()

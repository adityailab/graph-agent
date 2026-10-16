from __future__ import annotations

import handoff


def test_package_reports_its_version() -> None:
    assert handoff.__version__ == "0.1.0"


def test_test_modules_live_under_the_tests_package() -> None:
    # Without tests/__init__.py, tests/mcp/ would shadow the MCP SDK as a top-level `mcp`.
    assert __name__ == "tests.test_smoke"

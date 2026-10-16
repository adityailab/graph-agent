from __future__ import annotations

import handoff


def test_package_reports_its_version() -> None:
    assert handoff.__version__ == "0.1.0"

from __future__ import annotations

import tomllib
from pathlib import Path

from p2p_engine import __version__
from p2p_engine.mcp import server


def test_source_package_and_mcp_versions_are_consistent() -> None:
    root = Path(__file__).resolve().parents[1]
    package = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert package["project"]["version"] == __version__
    assert server.__version__ == __version__
    assert __version__ == "0.3.0"

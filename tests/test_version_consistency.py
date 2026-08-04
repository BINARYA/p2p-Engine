from __future__ import annotations

import re
import tomllib
from pathlib import Path

from p2p_engine import __version__
from p2p_engine.mcp import server
from p2p_engine.services.runtime_contract import RuntimeContractService


def test_source_package_and_mcp_versions_are_consistent(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    package = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    assert package["project"]["version"] == __version__
    assert server.__version__ == __version__
    assert __version__ == "0.4.7"
    assert runtime.default_contract_payload()["runtime"]["p2p"] == {
        "requires": f"=={__version__}",
        "recommended": __version__,
    }


def test_current_release_documentation_uses_package_version() -> None:
    root = Path(__file__).resolve().parents[1]
    wheel_name = f"p2p_engine-{__version__}-py3-none-any.whl"
    release_url = f"/releases/download/v{__version__}/{wheel_name}"

    readme = (root / "README.md").read_text(encoding="utf-8")
    install = (root / "docs" / "INSTALL.md").read_text(encoding="utf-8")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    cli_contract = (root / "docs" / "CLI-CONTRACT.md").read_text(encoding="utf-8")
    workspace_contract = (root / "docs" / "WORKSPACE-SCHEMA.md").read_text(encoding="utf-8")

    assert release_url in readme
    assert release_url in install
    release_heading = re.compile(
        rf"^## {re.escape(__version__)} - (?:Unreleased|\d{{4}}-\d{{2}}-\d{{2}})$",
        re.MULTILINE,
    )
    assert release_heading.search(changelog)
    assert f"P2P Engine {__version__} exposes" in cli_contract
    assert f"P2P Engine {__version__} supports workspace schema 3 only" in workspace_contract

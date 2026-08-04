from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.cli_contract import CLI_CONTRACT_VERSION
from p2p_engine.services.vertical_registry import (
    VerticalRegistryConfigurationService,
    vertical_user_paths,
)


runner = CliRunner()


@pytest.mark.unit
def test_vertical_user_paths_use_explicit_p2p_home(tmp_path: Path) -> None:
    paths = vertical_user_paths({"P2P_HOME": str(tmp_path / "p2p-home")})

    assert paths.data_root == (tmp_path / "p2p-home").resolve()
    assert paths.cache_root == (tmp_path / "p2p-home" / "cache").resolve()
    assert paths.registry_config_path == paths.data_root / "registries.yml"
    assert paths.vertical_cache_root == paths.cache_root / "verticals"


@pytest.mark.service
def test_registry_configuration_is_atomic_idempotent_and_project_external(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "user-data"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("P2P_HOME", str(home))
    service = VerticalRegistryConfigurationService()

    first = service.add("wavekit", "https://registry.example.test/", make_default=True)
    second = service.add("wavekit", "https://registry.example.test")

    assert first == second
    assert first.default_registry == "wavekit"
    assert first.registries[0].url == "https://registry.example.test"
    assert first.path == home / "registries.yml"
    assert not (project / ".p2p").exists()
    assert "wavekit" in first.path.read_text(encoding="utf-8")

    removed = service.remove("wavekit")
    assert removed.registries == ()
    assert removed.default_registry == ""


@pytest.mark.parametrize(
    "url",
    [
        "http://registry.example.test",
        "https://user:secret@registry.example.test",
        "https://registry.example.test?token=secret",
    ],
)
def test_registry_configuration_rejects_unsafe_urls(tmp_path: Path, url: str) -> None:
    service = VerticalRegistryConfigurationService(
        paths=vertical_user_paths({"P2P_HOME": str(tmp_path)})
    )

    with pytest.raises(ValueError, match="P2P_REGISTRY_INVALID_URL"):
        service.add("unsafe", url)


@pytest.mark.service
def test_registry_configuration_allows_loopback_http_for_development(tmp_path: Path) -> None:
    service = VerticalRegistryConfigurationService(
        paths=vertical_user_paths({"P2P_HOME": str(tmp_path)})
    )

    result = service.add("dev", "http://127.0.0.1:8080/api")

    assert result.registries[0].url == "http://127.0.0.1:8080/api"


@pytest.mark.cli
def test_vertical_registry_cli_and_local_catalog_use_versioned_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_HOME", str(tmp_path / "p2p-home"))

    added = runner.invoke(
        app,
        [
            "vertical",
            "registry",
            "add",
            "wavekit",
            "https://registry.example.test",
            "--format",
            "json",
        ],
    )
    listed = runner.invoke(app, ["vertical", "registry", "list", "--format", "json"])
    catalog = runner.invoke(
        app,
        ["vertical", "list", "--root", str(tmp_path / "project"), "--format", "json"],
    )

    assert added.exit_code == listed.exit_code == catalog.exit_code == 0
    for result in (added, listed, catalog):
        assert json.loads(result.stdout)["contract_version"] == CLI_CONTRACT_VERSION
    registry_payload = json.loads(listed.stdout)
    assert registry_payload["data"]["default_registry"] == "wavekit"
    coordinates = {
        item["coordinate"]
        for item in json.loads(catalog.stdout)["data"]["verticals"]
    }
    assert "binarya/base_project@2.0.0" in coordinates
    assert "binarya/software_project@2.0.0" in coordinates

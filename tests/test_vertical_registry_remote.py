from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
from typing import Mapping

import pytest
from typer.testing import CliRunner

from p2p_engine.adapters.credential_store import MemoryCredentialStore, redact_secret
from p2p_engine.adapters.vertical_registry_http import HTTPSVerticalRegistryTransport
from p2p_engine.cli import app
from p2p_engine.core.vertical_registry import (
    ArtifactDownload,
    DeviceAuthorization,
    RegistryCredential,
    VerticalPullResult,
)
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.vertical_catalog import VerticalCacheService, VerticalPullService
from p2p_engine.services.vertical_registry import (
    VerticalRegistryClient,
    VerticalRegistryConfigurationService,
    vertical_user_paths,
)
from p2p_engine.storage.filesystem import P2PWorkspace


runner = CliRunner()
PROTOCOL = "p2p-vertical-registry/v2"
REGISTRY_URL = "https://registry.example.test"


class FakeRegistryTransport:
    def __init__(self) -> None:
        self.responses: dict[tuple[str, str], object] = {}
        self.artifacts: dict[str, bytes] = {}
        self.requests: list[tuple[str, str, str]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str = "",
        form: Mapping[str, str] | None = None,
        max_bytes: int = 1_048_576,
    ) -> object:
        self.requests.append((method, url, token))
        response = self.responses.get((method, url))
        if isinstance(response, Exception):
            raise response
        if response is None:
            raise ValueError(f"P2P_REGISTRY_RELEASE_NOT_FOUND: no fake response for {url}")
        return response

    def download(
        self,
        url: str,
        destination: Path,
        *,
        token: str = "",
        max_bytes: int,
    ) -> ArtifactDownload:
        self.requests.append(("DOWNLOAD", url, token))
        payload = self.artifacts[url]
        if len(payload) > max_bytes:
            raise ValueError("P2P_REGISTRY_ARTIFACT_TOO_LARGE: fake overflow")
        destination.write_bytes(payload)
        return ArtifactDownload(
            path=destination,
            sha256=hashlib.sha256(payload).hexdigest(),
            size=len(payload),
        )


def _client(
    tmp_path: Path,
    transport: FakeRegistryTransport,
    *,
    credentials: MemoryCredentialStore | None = None,
) -> tuple[VerticalRegistryClient, VerticalRegistryConfigurationService]:
    configuration = VerticalRegistryConfigurationService(
        paths=vertical_user_paths({"P2P_HOME": str(tmp_path / "p2p-home")})
    )
    configuration.add("wavekit", REGISTRY_URL, make_default=True)
    transport.responses[("GET", f"{REGISTRY_URL}/.well-known/p2p-vertical-registry")] = {
        "vertical_registry": {
            "protocol_version": PROTOCOL,
            "api_base": "/api/vertical-registry/v2",
            "max_artifact_bytes": 8_388_608,
            "endpoints": {
                "domains": "domains",
                "domain": "domains/{domain_id}",
                "search": "releases/search",
                "releases": "releases",
                "release": "releases/{publisher}/{vertical_id}/{version}",
            },
            "oauth_device": {
                "device_authorization_endpoint": "/oauth/device",
                "token_endpoint": "/oauth/token",
                "client_id": "p2p-engine",
                "scopes": ["vertical:read"],
            },
        }
    }
    return (
        VerticalRegistryClient(
            configuration=configuration,
            transport=transport,
            credentials=credentials or MemoryCredentialStore(),
            now=lambda: 1_000,
            sleep=lambda _seconds: None,
        ),
        configuration,
    )


def _portable_releases(tmp_path: Path) -> tuple[dict[str, object], dict[str, object], dict[str, bytes]]:
    authoring = P2PWorkspace(tmp_path / "authoring")
    authoring.init_project("Registry authoring")

    base_source = tmp_path / "base-source"
    authoring.scaffold_portable_vertical(
        base_source,
        publisher="test",
        vertical_id="registry-base",
        version="1.0.0",
        name="Registry Base",
        license_id="MIT",
    )
    base_archive = tmp_path / "registry-base.p2pv"
    base_package = authoring.package_portable_vertical(base_source, output=base_archive)
    preview = authoring.preview_portable_vertical_install(
        base_archive,
        expected_checksum=base_package.artifact_checksum,
        actor="owner",
    )
    authoring.apply_portable_vertical_install(
        base_archive,
        expected_checksum=base_package.artifact_checksum,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key="install-registry-base",
    )

    derived_source = tmp_path / "derived-source"
    authoring.scaffold_portable_vertical(
        derived_source,
        publisher="test",
        vertical_id="registry-derived",
        version="1.0.0",
        name="Registry Derived",
        license_id="MIT",
        extends=base_package.coordinate,
    )
    derived_archive = tmp_path / "registry-derived.p2pv"
    derived_package = authoring.package_portable_vertical(
        derived_source,
        output=derived_archive,
    )

    def release(package, *, name: str, dependencies: list[dict[str, str]]) -> dict[str, object]:
        return {
            "coordinate": package.coordinate,
            "name": name,
            "description": f"{name} description",
            "visibility": "public",
            "semantic_checksum": package.semantic_checksum,
            "schema_version": 3,
            "artifact": {
                "url": f"/artifacts/{package.artifact_checksum}.p2pv",
                "sha256": package.artifact_checksum,
                "size": package.size,
            },
            "dependencies": dependencies,
        }

    base = release(base_package, name="Registry Base", dependencies=[])
    derived = release(
        derived_package,
        name="Registry Derived",
        dependencies=[
            {
                "coordinate": base_package.coordinate,
                "semantic_checksum": base_package.semantic_checksum,
            }
        ],
    )
    artifacts = {
        str(base["artifact"]["url"]): base_archive.read_bytes(),
        str(derived["artifact"]["url"]): derived_archive.read_bytes(),
    }
    return base, derived, artifacts


def _serve_release(transport: FakeRegistryTransport, release: dict[str, object]) -> None:
    publisher_and_id, version = str(release["coordinate"]).split("@", 1)
    publisher, vertical_id = publisher_and_id.split("/", 1)
    transport.responses[
        (
            "GET",
            f"{REGISTRY_URL}/api/vertical-registry/v2/releases/"
            f"{publisher}/{vertical_id}/{version}",
        )
    ] = {
        "vertical_release": {
            "protocol_version": PROTOCOL,
            "release": release,
        }
    }
    artifact = release["artifact"]
    relative_url = str(artifact["url"])
    if relative_url in transport.artifacts:
        transport.artifacts[f"{REGISTRY_URL}{relative_url}"] = transport.artifacts.pop(
            relative_url
        )


def _domain_payload(
    external_id: str = "dom-software",
    *,
    key: str = "software",
    visibility: str = "public",
    lifecycle: str = "active",
) -> dict[str, object]:
    return {
        "external_id": external_id,
        "key": key,
        "name": key.title(),
        "description": f"{key} projects",
        "visibility": visibility,
        "lifecycle": lifecycle,
        "publisher": "wavekit",
        "recommended_release": {
            "coordinate": "test/demo@1.0.0",
            "semantic_checksum": "1" * 64,
            "artifact_sha256": "2" * 64,
        },
        "unknown_display_metadata": {"accent": "blue"},
    }


def _release_payload(
    coordinate: str = "test/demo@1.0.0",
    *,
    primary_domain: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "coordinate": coordinate,
        "name": "Demo",
        "description": "Search result",
        "visibility": "public",
        "semantic_checksum": "1" * 64,
        "schema_version": 3,
        "artifact": {
            "url": "/artifacts/demo.p2pv",
            "sha256": "2" * 64,
            "size": 10,
        },
        "dependencies": [],
        "primary_domain": primary_domain,
    }


def _page(items: list[dict[str, object]], *, next_cursor: str | None = None) -> dict[str, object]:
    return {
        "returned": len(items),
        "next_cursor": next_cursor,
        "truncated": bool(next_cursor),
    }


@pytest.mark.service
def test_capabilities_are_negotiated_and_cached_without_credentials(tmp_path: Path) -> None:
    transport = FakeRegistryTransport()
    client, configuration = _client(tmp_path, transport)
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/releases?limit=100")
    ] = {
        "vertical_releases": {
            "protocol_version": PROTOCOL,
            "items": [],
            "page": {"returned": 0, "next_cursor": None, "truncated": False},
        }
    }

    assert client.list_releases() == ()
    assert client.list_releases() == ()

    capability_requests = [
        item for item in transport.requests if item[1].endswith("/.well-known/p2p-vertical-registry")
    ]
    assert len(capability_requests) == 1
    configured = configuration.read().registries[0]
    assert configured.capabilities is not None
    assert configured.capabilities.protocol_version == PROTOCOL


@pytest.mark.service
def test_private_listing_uses_secure_store_and_never_returns_token(tmp_path: Path) -> None:
    transport = FakeRegistryTransport()
    credentials = MemoryCredentialStore()
    credentials.set(
        "wavekit",
        RegistryCredential(access_token="super-secret", expires_at=2_000),
    )
    client, _configuration = _client(tmp_path, transport, credentials=credentials)
    url = f"{REGISTRY_URL}/api/vertical-registry/v2/releases?include_private=true&limit=100"
    transport.responses[("GET", url)] = {
        "vertical_releases": {
            "protocol_version": PROTOCOL,
            "items": [],
            "page": {"returned": 0, "next_cursor": None, "truncated": False},
        }
    }

    assert client.list_releases(include_private=True) == ()
    assert transport.requests[-1] == ("GET", url, "super-secret")
    assert "super-secret" not in repr(client.list_releases(include_private=True))
    assert redact_secret("Bearer super-secret failed", "super-secret") == "Bearer [REDACTED] failed"


@pytest.mark.service
def test_domain_catalog_list_search_inspect_and_paginate_without_structure_payload(
    tmp_path: Path,
) -> None:
    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    first = [_domain_payload("dom-software", key="software")]
    second = [_domain_payload("dom-grants", key="grants", visibility="private")]
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/domains?limit=100")
    ] = {
        "vertical_domains": {
            "protocol_version": PROTOCOL,
            "items": first,
            "page": _page(first, next_cursor="cursor-2"),
        }
    }
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/domains?limit=100&cursor=cursor-2")
    ] = {
        "vertical_domains": {
            "protocol_version": PROTOCOL,
            "items": second,
            "page": _page(second),
        }
    }
    searched = [_domain_payload("dom-software", key="software")]
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/domains?q=soft&limit=100")
    ] = {
        "vertical_domains": {
            "protocol_version": PROTOCOL,
            "items": searched,
            "page": _page(searched),
        }
    }
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/domains/dom-software")
    ] = {
        "vertical_domain": {
            "protocol_version": PROTOCOL,
            "domain": _domain_payload("dom-software", key="software"),
        }
    }

    listed = client.list_domains()
    domains, page = client.list_domains_with_page(query="soft")
    inspected = client.domain("dom-software")

    assert [item.external_id for item in listed] == ["dom-software", "dom-grants"]
    assert page.returned == 1
    assert domains[0].recommended_release is not None
    assert domains[0].recommended_release.coordinate == "test/demo@1.0.0"
    assert inspected.key == "software"
    assert "sections" not in inspected.to_dict()


@pytest.mark.service
def test_domain_catalog_fails_closed_for_v1_cross_origin_and_malformed_payloads(
    tmp_path: Path,
) -> None:
    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    transport.responses[
        ("GET", f"{REGISTRY_URL}/.well-known/p2p-vertical-registry")
    ]["vertical_registry"]["protocol_version"] = "p2p-vertical-registry/v1"

    with pytest.raises(ValueError, match="P2P_REGISTRY_PROTOCOL_UNSUPPORTED"):
        client.list_domains()

    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path / "cross", transport)
    transport.responses[
        ("GET", f"{REGISTRY_URL}/.well-known/p2p-vertical-registry")
    ]["vertical_registry"]["endpoints"]["domains"] = "https://evil.example.test/domains"

    with pytest.raises(ValueError, match="P2P_REGISTRY_INVALID_URL"):
        client.list_domains()

    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path / "bad-domain", transport)
    bad_domain = [_domain_payload("dom-software") | {"sections": []}]
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/domains?limit=100")
    ] = {
        "vertical_domains": {
            "protocol_version": PROTOCOL,
            "items": bad_domain,
            "page": _page(bad_domain),
        }
    }

    with pytest.raises(ValueError, match="P2P_REGISTRY_RESPONSE_INVALID"):
        client.list_domains()

    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path / "cursor", transport)
    page_items: list[dict[str, object]] = []
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/domains?limit=100")
    ] = {
        "vertical_domains": {
            "protocol_version": PROTOCOL,
            "items": page_items,
            "page": {"returned": 1, "next_cursor": None, "truncated": False},
        }
    }

    with pytest.raises(ValueError, match="P2P_REGISTRY_PAGINATION_INVALID"):
        client.list_domains()


@pytest.mark.service
def test_domain_filtered_vertical_search_encodes_filter_and_performs_no_cache_or_project_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import p2p_engine.cli_commands.verticals as vertical_commands

    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    release = _release_payload(
        primary_domain={
            "external_id": "dom/encoded",
            "key": "software",
            "name": "Software",
        }
    )
    url = (
        f"{REGISTRY_URL}/api/vertical-registry/v2/releases/search"
        "?q=demo&domain=dom%2Fencoded&limit=100"
    )
    transport.responses[("GET", url)] = {
        "vertical_releases": {
            "protocol_version": PROTOCOL,
            "items": [release],
            "page": _page([release]),
        }
    }
    monkeypatch.setattr(vertical_commands, "VerticalRegistryClient", lambda: client)

    project_root = tmp_path / "project"
    result = runner.invoke(
        app,
        [
            "vertical",
            "search",
            "demo",
            "--domain",
            "dom/encoded",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    item = payload["data"]["vertical_releases"]["items"][0]
    assert item["coordinate"] == "test/demo@1.0.0"
    assert item["primary_domain"]["external_id"] == "dom/encoded"
    assert transport.requests[-1][1] == url
    assert "dom/encoded" not in transport.requests[-1][1].split("?", 1)[0]
    assert not (project_root / ".p2p").exists()
    assert not (client.configuration.paths.vertical_cache_root).exists()
    assert all(method != "DOWNLOAD" for method, _url, _token in transport.requests)


@pytest.mark.service
def test_domain_reads_fail_without_configured_registry(tmp_path: Path) -> None:
    configuration = VerticalRegistryConfigurationService(
        paths=vertical_user_paths({"P2P_HOME": str(tmp_path / "p2p-home")})
    )
    client = VerticalRegistryClient(
        configuration=configuration,
        transport=FakeRegistryTransport(),
        credentials=MemoryCredentialStore(),
    )

    with pytest.raises(ValueError, match="P2P_REGISTRY_NOT_CONFIGURED"):
        client.list_domains()


@pytest.mark.service
def test_private_domain_read_refreshes_existing_credential_without_secret_output(
    tmp_path: Path,
) -> None:
    transport = FakeRegistryTransport()
    credentials = MemoryCredentialStore()
    credentials.set(
        "wavekit",
        RegistryCredential(
            access_token="expired-access",
            refresh_token="refresh-secret",
            expires_at=900,
        ),
    )
    client, _configuration = _client(tmp_path, transport, credentials=credentials)
    transport.responses[("POST", f"{REGISTRY_URL}/oauth/token")] = {
        "access_token": "fresh-access",
        "refresh_token": "fresh-refresh",
        "expires_in": 3600,
        "scope": "vertical:read",
    }
    domains = [_domain_payload("dom-private", key="private", visibility="private")]
    url = f"{REGISTRY_URL}/api/vertical-registry/v2/domains?include_private=true&limit=100"
    transport.responses[("GET", url)] = {
        "vertical_domains": {
            "protocol_version": PROTOCOL,
            "items": domains,
            "page": _page(domains),
        }
    }

    result = client.list_domains(include_private=True)

    assert result[0].external_id == "dom-private"
    assert transport.requests[-1] == ("GET", url, "fresh-access")
    stored = credentials.get("wavekit")
    assert stored is not None
    assert stored.access_token == "fresh-access"
    assert "refresh-secret" not in repr(result)


@pytest.mark.service
def test_uncategorized_vertical_filter_requires_provider_capability(
    tmp_path: Path,
) -> None:
    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)

    with pytest.raises(ValueError, match="P2P_REGISTRY_DOMAIN_FILTER_UNSUPPORTED"):
        client.list_releases(domain="uncategorized")

    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path / "supported", transport)
    transport.responses[
        ("GET", f"{REGISTRY_URL}/.well-known/p2p-vertical-registry")
    ]["vertical_registry"]["supports_uncategorized_filter"] = True
    transport.responses[
        (
            "GET",
            f"{REGISTRY_URL}/api/vertical-registry/v2/releases"
            "?domain=uncategorized&limit=100",
        )
    ] = {
        "vertical_releases": {
            "protocol_version": PROTOCOL,
            "items": [],
            "page": _page([]),
        }
    }

    assert client.list_releases(domain="uncategorized") == ()


@pytest.mark.smoke
@pytest.mark.mcp
def test_mcp_remote_registry_domain_and_release_reads_match_cli_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import p2p_engine.cli_commands.verticals as vertical_commands
    import p2p_engine.mcp.handlers.vertical_registry as mcp_vertical_registry

    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    domains = [_domain_payload("dom-software", key="software")]
    release = _release_payload(
        primary_domain={
            "external_id": "dom-software",
            "key": "software",
            "name": "Software",
        }
    )
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/domains?limit=100")
    ] = {
        "vertical_domains": {
            "protocol_version": PROTOCOL,
            "items": domains,
            "page": _page(domains),
        }
    }
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v2/domains/dom-software")
    ] = {
        "vertical_domain": {
            "protocol_version": PROTOCOL,
            "domain": domains[0],
        }
    }
    transport.responses[
        (
            "GET",
            f"{REGISTRY_URL}/api/vertical-registry/v2/releases/search"
            "?q=demo&domain=dom-software&limit=100",
        )
    ] = {
        "vertical_releases": {
            "protocol_version": PROTOCOL,
            "items": [release],
            "page": _page([release]),
        }
    }
    monkeypatch.setattr(vertical_commands, "VerticalRegistryClient", lambda: client)
    monkeypatch.setattr(mcp_vertical_registry, "VerticalRegistryClient", lambda: client)

    cli_domains = runner.invoke(
        app,
        ["vertical", "domain", "list", "--format", "json"],
    )
    mcp_domains = call_tool("p2p_vertical_domain_list", {"root": str(tmp_path)})
    mcp_domain = call_tool(
        "p2p_vertical_domain_inspect",
        {"root": str(tmp_path), "domain_id": "dom-software"},
    )
    mcp_releases = call_tool(
        "p2p_vertical_release_search",
        {"root": str(tmp_path), "query": "demo", "domain": "dom-software"},
    )

    assert cli_domains.exit_code == 0, cli_domains.stdout
    cli_payload = json.loads(cli_domains.stdout)
    assert cli_payload["data"]["vertical_domains"] == mcp_domains["vertical_domains"]
    assert mcp_domain["vertical_domain"]["domain"]["external_id"] == "dom-software"
    assert mcp_releases["vertical_releases"]["items"][0]["coordinate"] == "test/demo@1.0.0"
    assert mcp_releases["mutation_performed"] is False
    assert mcp_releases["network_access"] == "remote_read"
    assert not (tmp_path / ".p2p").exists()


@pytest.mark.integration
def test_pull_dependency_closure_is_atomic_idempotent_and_initializes_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_HOME", str(tmp_path / "p2p-home"))
    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    base, derived, artifacts = _portable_releases(tmp_path)
    transport.artifacts.update(artifacts)
    _serve_release(transport, base)
    _serve_release(transport, derived)
    cache = VerticalCacheService(paths=client.configuration.paths)
    service = VerticalPullService(client=client, cache=cache)

    first = service.pull(str(derived["coordinate"]))
    second = service.pull(str(derived["coordinate"]))

    assert first.status == "pulled"
    assert second.status == "already_present"
    assert [item.release.coordinate for item in first.releases] == [
        base["coordinate"],
        derived["coordinate"],
    ]
    assert len(cache.closure("wavekit", str(derived["coordinate"]))) == 2

    inspected = runner.invoke(
        app,
        [
            "vertical",
            "inspect",
            str(derived["coordinate"]),
            "--root",
            str(tmp_path / "inspection-root"),
            "--format",
            "json",
        ],
    )
    assert inspected.exit_code == 0, inspected.stdout

    request_count = len(transport.requests)
    project_root = tmp_path / "initialized"
    result = runner.invoke(
        app,
        [
            "init",
            "Cached registry project",
            "--vertical",
            str(derived["coordinate"]),
            "--root",
            str(project_root),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert len(transport.requests) == request_count
    project = P2PWorkspace(project_root)
    assert project.active_project_vertical().coordinate == derived["coordinate"]
    assert project.project_vertical_lock_status().status == "valid"


@pytest.mark.cli
def test_init_missing_exact_release_is_offline_and_leaves_no_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_HOME", str(tmp_path / "empty-home"))
    project_root = tmp_path / "offline-project"

    result = runner.invoke(
        app,
        [
            "init",
            "Offline project",
            "--vertical",
            "test/not-cached@1.0.0",
            "--root",
            str(project_root),
        ],
    )

    assert result.exit_code != 0
    assert "P2P_VERTICAL_NOT_FOUND" in result.stdout
    assert not (project_root / ".p2p").exists()


@pytest.mark.service
def test_immutable_coordinate_metadata_change_fails_closed(tmp_path: Path) -> None:
    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    base, _derived, artifacts = _portable_releases(tmp_path)
    transport.artifacts.update(artifacts)
    _serve_release(transport, base)
    cache = VerticalCacheService(paths=client.configuration.paths)
    service = VerticalPullService(client=client, cache=cache)
    service.pull(str(base["coordinate"]))

    changed = {**base, "semantic_checksum": "f" * 64}
    _serve_release(transport, changed)

    with pytest.raises(ValueError, match="P2P_REGISTRY_IMMUTABILITY_VIOLATION"):
        service.pull(str(base["coordinate"]))

    cached = cache.read("wavekit", str(base["coordinate"]))
    assert cached is not None
    assert cached.release.semantic_checksum == base["semantic_checksum"]


@pytest.mark.service
def test_device_login_persists_only_in_credential_adapter_and_logout_removes_it(
    tmp_path: Path,
) -> None:
    transport = FakeRegistryTransport()
    credentials = MemoryCredentialStore()
    client, configuration = _client(tmp_path, transport, credentials=credentials)
    transport.responses[("POST", f"{REGISTRY_URL}/oauth/device")] = {
        "device_code": "internal-device-code",
        "user_code": "ABCD-EFGH",
        "verification_uri": "https://registry.example.test/activate",
        "expires_in": 600,
        "interval": 1,
    }
    transport.responses[("POST", f"{REGISTRY_URL}/oauth/token")] = {
        "access_token": "private-access-token",
        "refresh_token": "private-refresh-token",
        "expires_in": 3600,
        "scope": "vertical:read",
    }

    registry, authorization = client.start_login()
    credential = client.complete_login(registry, authorization)

    assert credential.access_token == "private-access-token"
    assert credentials.get("wavekit") == credential
    assert "private-access-token" not in configuration.path.read_text(encoding="utf-8")
    assert "internal-device-code" not in repr(authorization.public_dict())
    assert client.logout() == ("wavekit", True)
    assert credentials.get("wavekit") is None


@pytest.mark.cli
def test_search_pull_and_login_commands_use_versioned_json_without_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import p2p_engine.cli_commands.verticals as vertical_commands

    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    query_url = f"{REGISTRY_URL}/api/vertical-registry/v2/releases/search?q=demo&limit=100"
    transport.responses[("GET", query_url)] = {
        "vertical_releases": {
            "protocol_version": PROTOCOL,
            "items": [
                {
                    "coordinate": "test/demo@1.0.0",
                    "name": "Demo",
                    "description": "Search result",
                    "visibility": "public",
                    "semantic_checksum": "1" * 64,
                    "schema_version": 3,
                    "artifact": {
                        "url": "/artifacts/demo.p2pv",
                        "sha256": "2" * 64,
                        "size": 10,
                    },
                    "dependencies": [],
                }
            ],
            "page": {"returned": 1, "next_cursor": None, "truncated": False},
        }
    }
    monkeypatch.setattr(vertical_commands, "VerticalRegistryClient", lambda: client)

    searched = runner.invoke(
        app,
        [
            "vertical",
            "search",
            "demo",
            "--root",
            str(tmp_path / "project"),
            "--format",
            "json",
        ],
    )

    assert searched.exit_code == 0
    search_payload = json.loads(searched.stdout)
    assert search_payload["operation"] == "vertical.search"
    assert search_payload["data"]["verticals"][0]["coordinate"] == "test/demo@1.0.0"

    class PullStub:
        def pull(self, coordinate: str, *, registry: str = "") -> VerticalPullResult:
            return VerticalPullResult(
                registry=registry or "wavekit",
                requested_coordinate=coordinate,
                status="already_present",
            )

    monkeypatch.setattr(vertical_commands, "VerticalPullService", lambda: PullStub())
    pulled = runner.invoke(
        app,
        ["vertical", "pull", "test/demo@1.0.0", "--format", "json"],
    )
    assert pulled.exit_code == 0
    assert json.loads(pulled.stdout)["data"]["status"] == "already_present"

    class LoginStub:
        def start_login(self, registry: str = ""):
            return "wavekit", DeviceAuthorization(
                device_code="private-device-code",
                user_code="ABCD",
                verification_uri="https://registry.example.test/activate",
            )

        def complete_login(self, registry: str, authorization: DeviceAuthorization):
            return RegistryCredential(access_token="private-access-token", expires_at=2_000)

    monkeypatch.setattr(vertical_commands, "VerticalRegistryClient", lambda: LoginStub())
    logged_in = runner.invoke(app, ["vertical", "login", "wavekit", "--format", "json"])
    assert logged_in.exit_code == 0
    assert "private-access-token" not in logged_in.stdout
    assert "private-device-code" not in logged_in.stdout
    assert json.loads(logged_in.stdout)["operation"] == "vertical.login"


@pytest.mark.service
def test_malformed_artifact_leaves_no_partial_cache_closure(tmp_path: Path) -> None:
    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    payload = b"not-a-portable-package"
    checksum = hashlib.sha256(payload).hexdigest()
    release = {
        "coordinate": "test/malformed@1.0.0",
        "name": "Malformed",
        "description": "",
        "visibility": "public",
        "semantic_checksum": "1" * 64,
        "schema_version": 3,
        "artifact": {
            "url": f"/artifacts/{checksum}.p2pv",
            "sha256": checksum,
            "size": len(payload),
        },
        "dependencies": [],
    }
    transport.artifacts[str(release["artifact"]["url"])] = payload
    _serve_release(transport, release)
    cache = VerticalCacheService(paths=client.configuration.paths)

    with pytest.raises(ValueError, match="P2P_VERTICAL|P2P_REGISTRY_ARTIFACT"):
        VerticalPullService(client=client, cache=cache).pull(str(release["coordinate"]))

    assert cache.list("wavekit") == ()
    assert not cache.release_directory("wavekit", str(release["coordinate"])).exists()


@pytest.mark.service
def test_checksum_mismatch_leaves_cache_empty(tmp_path: Path) -> None:
    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    base, _derived, artifacts = _portable_releases(tmp_path)
    transport.artifacts.update(artifacts)
    mismatched = {
        **base,
        "artifact": {**base["artifact"], "sha256": "e" * 64},
    }
    _serve_release(transport, mismatched)
    cache = VerticalCacheService(paths=client.configuration.paths)

    with pytest.raises(ValueError, match="P2P_REGISTRY_ARTIFACT_MISMATCH"):
        VerticalPullService(client=client, cache=cache).pull(str(base["coordinate"]))

    assert cache.list("wavekit") == ()


@pytest.mark.service
def test_dependency_metadata_conflict_commits_no_partial_closure(tmp_path: Path) -> None:
    transport = FakeRegistryTransport()
    client, _configuration = _client(tmp_path, transport)
    base, derived, artifacts = _portable_releases(tmp_path)
    transport.artifacts.update(artifacts)
    broken_dependency = {
        **derived,
        "dependencies": [
            {
                "coordinate": base["coordinate"],
                "semantic_checksum": "a" * 64,
            }
        ],
    }
    _serve_release(transport, base)
    _serve_release(transport, broken_dependency)
    cache = VerticalCacheService(paths=client.configuration.paths)

    with pytest.raises(ValueError, match="P2P_REGISTRY_METADATA_MISMATCH"):
        VerticalPullService(client=client, cache=cache).pull(str(derived["coordinate"]))

    assert cache.list("wavekit") == ()


class _Response:
    status = 200

    def __init__(self, chunks: list[bytes], *, content_length: str | None = None) -> None:
        self.chunks = list(chunks)
        self.content_length = content_length

    def getheader(self, name: str) -> str | None:
        return self.content_length if name == "Content-Length" else None

    def read(self, _size: int = -1) -> bytes:
        if not self.chunks:
            return b""
        return self.chunks.pop(0)


class _Connection:
    sock = None

    def __init__(self, response: _Response) -> None:
        self.response = response

    def request(self, *args, **kwargs) -> None:
        return None

    def getresponse(self) -> _Response:
        return self.response

    def close(self) -> None:
        return None


@pytest.mark.adapter
def test_http_adapter_bounds_stream_and_cleans_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = HTTPSVerticalRegistryTransport()
    connection = _Connection(_Response([b"1234", b"5"]))
    monkeypatch.setattr(transport, "_connection", lambda _url: (connection, "/artifact"))
    destination = tmp_path / "download.p2pv"

    with pytest.raises(ValueError, match="P2P_REGISTRY_ARTIFACT_TOO_LARGE"):
        transport.download(
            "https://registry.example.test/artifact",
            destination,
            max_bytes=4,
        )

    assert not destination.exists()


@pytest.mark.adapter
def test_http_adapter_maps_read_timeout_without_leaking_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TimeoutResponse(_Response):
        def read(self, _size: int = -1) -> bytes:
            raise socket.timeout("bearer-secret")

    transport = HTTPSVerticalRegistryTransport()
    connection = _Connection(TimeoutResponse([]))
    monkeypatch.setattr(transport, "_connection", lambda _url: (connection, "/artifact"))

    with pytest.raises(ValueError, match="P2P_REGISTRY_TIMEOUT") as error:
        transport.download(
            "https://registry.example.test/artifact",
            tmp_path / "timeout.p2pv",
            token="bearer-secret",
            max_bytes=10,
        )

    assert "bearer-secret" not in str(error.value)


@pytest.mark.adapter
def test_http_adapter_maps_throttling_to_stable_registry_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ThrottledResponse(_Response):
        status = 429

    transport = HTTPSVerticalRegistryTransport()
    connection = _Connection(ThrottledResponse([b"{}"]))
    monkeypatch.setattr(transport, "_connection", lambda _url: (connection, "/domains"))

    with pytest.raises(ValueError, match="P2P_REGISTRY_THROTTLED"):
        transport.request_json("GET", "https://registry.example.test/domains")

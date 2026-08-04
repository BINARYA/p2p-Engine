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
from p2p_engine.services.vertical_catalog import VerticalCacheService, VerticalPullService
from p2p_engine.services.vertical_registry import (
    VerticalRegistryClient,
    VerticalRegistryConfigurationService,
    vertical_user_paths,
)
from p2p_engine.storage.filesystem import P2PWorkspace


runner = CliRunner()
PROTOCOL = "p2p-vertical-registry/v1"
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
            "api_base": "/api/vertical-registry/v1",
            "max_artifact_bytes": 8_388_608,
            "endpoints": {
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
            "schema_version": 2,
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
            f"{REGISTRY_URL}/api/vertical-registry/v1/releases/"
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


@pytest.mark.service
def test_capabilities_are_negotiated_and_cached_without_credentials(tmp_path: Path) -> None:
    transport = FakeRegistryTransport()
    client, configuration = _client(tmp_path, transport)
    transport.responses[
        ("GET", f"{REGISTRY_URL}/api/vertical-registry/v1/releases")
    ] = {"vertical_releases": {"protocol_version": PROTOCOL, "items": []}}

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
    url = f"{REGISTRY_URL}/api/vertical-registry/v1/releases?include_private=true"
    transport.responses[("GET", url)] = {
        "vertical_releases": {"protocol_version": PROTOCOL, "items": []}
    }

    assert client.list_releases(include_private=True) == ()
    assert transport.requests[-1] == ("GET", url, "super-secret")
    assert "super-secret" not in repr(client.list_releases(include_private=True))
    assert redact_secret("Bearer super-secret failed", "super-secret") == "Bearer [REDACTED] failed"


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
    query_url = f"{REGISTRY_URL}/api/vertical-registry/v1/releases/search?q=demo"
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
                    "schema_version": 2,
                    "artifact": {
                        "url": "/artifacts/demo.p2pv",
                        "sha256": "2" * 64,
                        "size": 10,
                    },
                    "dependencies": [],
                }
            ],
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
        "schema_version": 2,
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

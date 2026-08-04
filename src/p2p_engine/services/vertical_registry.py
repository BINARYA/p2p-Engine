from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import time
from typing import Callable
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit

from p2p_engine.adapters.credential_store import CredentialStore, KeyringCredentialStore
from p2p_engine.adapters.vertical_registry_http import (
    HTTPSVerticalRegistryTransport,
    VerticalRegistryTransport,
)
from p2p_engine.core.portable_verticals import PORTABLE_VERTICAL_SCHEMA_VERSION, VerticalCoordinate

from p2p_engine.core.vertical_registry import (
    VERTICAL_REGISTRY_CAPABILITY_PATH,
    VERTICAL_REGISTRY_CONFIG_SCHEMA_VERSION,
    VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES,
    VERTICAL_REGISTRY_PROTOCOL_VERSION,
    DeviceAuthorization,
    OAuthDeviceConfiguration,
    RegistryCapabilities,
    RegistryCredential,
    RegistryEndpoints,
    VerticalRegistryConfiguration,
    VerticalRegistryRecord,
    VerticalPublicationReceipt,
    VerticalRelease,
    VerticalReleaseArtifact,
    VerticalReleaseDependency,
    VerticalUserPaths,
)
from p2p_engine.foundation.files import write_yaml_atomic
from p2p_engine.foundation.yaml_loaders import load_yaml


_REGISTRY_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?$")
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def vertical_user_paths(environment: dict[str, str] | None = None) -> VerticalUserPaths:
    env = os.environ if environment is None else environment
    explicit = str(env.get("P2P_HOME") or "").strip()
    if explicit:
        root = Path(explicit).expanduser().resolve()
        return VerticalUserPaths(data_root=root, cache_root=root / "cache")

    home = Path(str(env.get("HOME") or Path.home())).expanduser().resolve()
    data_root = Path(str(env.get("XDG_DATA_HOME") or home / ".local" / "share"))
    cache_root = Path(str(env.get("XDG_CACHE_HOME") or home / ".cache"))
    return VerticalUserPaths(
        data_root=data_root.expanduser().resolve() / "p2p-engine",
        cache_root=cache_root.expanduser().resolve() / "p2p-engine",
    )


class VerticalRegistryConfigurationService:
    def __init__(self, *, paths: VerticalUserPaths | None = None) -> None:
        self.paths = paths or vertical_user_paths()
        self.path = self.paths.registry_config_path

    def read(self) -> VerticalRegistryConfiguration:
        if not self.path.exists():
            return VerticalRegistryConfiguration(
                default_registry="",
                registries=(),
                path=self.path,
            )
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError(f"P2P_REGISTRY_CONFIG_INVALID: unsafe registry config path: {self.path}")
        try:
            raw = load_yaml(self.path.read_bytes())
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"P2P_REGISTRY_CONFIG_INVALID: {exc}") from exc
        root = raw.get("vertical_registries") if isinstance(raw, dict) else None
        if not isinstance(root, dict):
            raise ValueError("P2P_REGISTRY_CONFIG_INVALID: expected vertical_registries mapping")
        if root.get("schema_version") != VERTICAL_REGISTRY_CONFIG_SCHEMA_VERSION:
            raise ValueError(
                "P2P_REGISTRY_CONFIG_UNSUPPORTED_SCHEMA: expected registry config schema 1"
            )
        entries = root.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError("P2P_REGISTRY_CONFIG_INVALID: entries must be a list")
        records: list[VerticalRegistryRecord] = []
        seen: set[str] = set()
        for index, value in enumerate(entries):
            if not isinstance(value, dict):
                raise ValueError(f"P2P_REGISTRY_CONFIG_INVALID: entries[{index}] must be a mapping")
            unknown = set(value) - {"name", "url", "protocol_version", "capabilities"}
            if unknown:
                raise ValueError(
                    f"P2P_REGISTRY_CONFIG_INVALID: entries[{index}] has unknown fields {sorted(unknown)}"
                )
            name = _validate_name(value.get("name"))
            if name in seen:
                raise ValueError(f"P2P_REGISTRY_CONFIG_INVALID: duplicate registry `{name}`")
            seen.add(name)
            protocol = str(value.get("protocol_version") or VERTICAL_REGISTRY_PROTOCOL_VERSION)
            if protocol != VERTICAL_REGISTRY_PROTOCOL_VERSION:
                raise ValueError(
                    f"P2P_REGISTRY_PROTOCOL_UNSUPPORTED: registry `{name}` uses `{protocol}`"
                )
            records.append(
                VerticalRegistryRecord(
                    name=name,
                    url=_normalize_url(value.get("url")),
                    protocol_version=protocol,
                    capabilities=(
                        _parse_capabilities(value["capabilities"])
                        if value.get("capabilities") is not None
                        else None
                    ),
                )
            )
        default = str(root.get("default") or "")
        if default and default not in seen:
            raise ValueError(
                f"P2P_REGISTRY_CONFIG_INVALID: default registry `{default}` is not configured"
            )
        return VerticalRegistryConfiguration(
            default_registry=default,
            registries=tuple(records),
            path=self.path,
        )

    def add(self, name: str, url: str, *, make_default: bool = False) -> VerticalRegistryConfiguration:
        normalized_name = _validate_name(name)
        normalized_url = _normalize_url(url)
        current = self.read()
        by_name = {item.name: item for item in current.registries}
        existing = by_name.get(normalized_name)
        if existing is not None and existing.url != normalized_url:
            raise ValueError(
                f"P2P_REGISTRY_CONFIG_CONFLICT: registry `{normalized_name}` already uses {existing.url}"
            )
        by_name[normalized_name] = VerticalRegistryRecord(
            name=normalized_name,
            url=normalized_url,
            capabilities=existing.capabilities if existing is not None else None,
        )
        default = normalized_name if make_default or not current.default_registry else current.default_registry
        self._write(default, tuple(sorted(by_name.values(), key=lambda item: item.name)))
        return self.read()

    def update_capabilities(
        self,
        name: str,
        capabilities: RegistryCapabilities,
    ) -> VerticalRegistryConfiguration:
        normalized_name = _validate_name(name)
        current = self.read()
        found = False
        records: list[VerticalRegistryRecord] = []
        for record in current.registries:
            if record.name != normalized_name:
                records.append(record)
                continue
            found = True
            records.append(
                VerticalRegistryRecord(
                    name=record.name,
                    url=record.url,
                    protocol_version=record.protocol_version,
                    capabilities=capabilities,
                )
            )
        if not found:
            raise ValueError(
                f"P2P_REGISTRY_NOT_FOUND: registry `{normalized_name}` is not configured"
            )
        self._write(current.default_registry, tuple(records))
        return self.read()

    def resolve(self, name: str = "") -> VerticalRegistryRecord:
        current = self.read()
        selected = _validate_name(name) if name else current.default_registry
        if not selected:
            raise ValueError(
                "P2P_REGISTRY_NOT_CONFIGURED: configure a registry or pass --registry"
            )
        for record in current.registries:
            if record.name == selected:
                return record
        raise ValueError(f"P2P_REGISTRY_NOT_FOUND: registry `{selected}` is not configured")

    def remove(self, name: str) -> VerticalRegistryConfiguration:
        normalized_name = _validate_name(name)
        current = self.read()
        records = tuple(item for item in current.registries if item.name != normalized_name)
        if len(records) == len(current.registries):
            raise ValueError(f"P2P_REGISTRY_NOT_FOUND: registry `{normalized_name}` is not configured")
        default = current.default_registry
        if default == normalized_name:
            default = records[0].name if records else ""
        self._write(default, records)
        return self.read()

    def _write(self, default: str, records: tuple[VerticalRegistryRecord, ...]) -> None:
        payload = {
            "vertical_registries": {
                "schema_version": VERTICAL_REGISTRY_CONFIG_SCHEMA_VERSION,
                "default": default or None,
                "entries": [
                    {
                        "name": item.name,
                        "url": item.url,
                        "protocol_version": item.protocol_version,
                        "capabilities": (
                            item.capabilities.to_dict() if item.capabilities else None
                        ),
                    }
                    for item in records
                ],
            }
        }
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_yaml_atomic(self.path, payload)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass


class VerticalRegistryClient:
    def __init__(
        self,
        *,
        configuration: VerticalRegistryConfigurationService | None = None,
        transport: VerticalRegistryTransport | None = None,
        credentials: CredentialStore | None = None,
        now: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.configuration = configuration or VerticalRegistryConfigurationService()
        self.transport = transport or HTTPSVerticalRegistryTransport()
        self.credentials = credentials or KeyringCredentialStore()
        self.now = now
        self.sleep = sleep

    def capabilities(self, registry: str = "", *, refresh: bool = False) -> RegistryCapabilities:
        record = self.configuration.resolve(registry)
        if record.capabilities is not None and not refresh:
            return record.capabilities
        url = _same_origin_url(record.url, VERTICAL_REGISTRY_CAPABILITY_PATH)
        raw = self.transport.request_json(
            "GET",
            url,
            max_bytes=VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES,
        )
        capabilities = _parse_capabilities(_unwrap(raw, "vertical_registry"))
        self.configuration.update_capabilities(record.name, capabilities)
        return capabilities

    def list_releases(
        self,
        registry: str = "",
        *,
        query: str = "",
        include_private: bool = False,
    ) -> tuple[VerticalRelease, ...]:
        record = self.configuration.resolve(registry)
        capabilities = self.capabilities(record.name)
        endpoint = capabilities.endpoints.search if query else capabilities.endpoints.releases
        url = self._api_url(record, capabilities, endpoint)
        parameters: dict[str, str] = {}
        if query:
            parameters["q"] = query
        if include_private:
            parameters["include_private"] = "true"
        if parameters:
            url += ("&" if "?" in url else "?") + urlencode(parameters)
        token = self._access_token(record.name, required=include_private)
        raw = self.transport.request_json(
            "GET",
            url,
            token=token,
            max_bytes=VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES,
        )
        payload = _unwrap(raw, "vertical_releases")
        if not isinstance(payload, dict):
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: expected vertical_releases mapping")
        _validate_protocol(payload.get("protocol_version"))
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: items must be a list")
        return tuple(_parse_release(item, registry=record.name) for item in items)

    def release(self, coordinate: str, registry: str = "") -> VerticalRelease:
        parsed = VerticalCoordinate.parse(coordinate)
        record = self.configuration.resolve(registry)
        capabilities = self.capabilities(record.name)
        endpoint = capabilities.endpoints.release.format(
            publisher=quote(parsed.publisher, safe=""),
            vertical_id=quote(parsed.vertical_id, safe=""),
            version=quote(parsed.version, safe=""),
        )
        token = self._access_token(record.name, required=False)
        raw = self.transport.request_json(
            "GET",
            self._api_url(record, capabilities, endpoint),
            token=token,
            max_bytes=VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES,
        )
        payload = _unwrap(raw, "vertical_release")
        if not isinstance(payload, dict):
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: expected vertical_release mapping")
        _validate_protocol(payload.get("protocol_version"))
        release_payload = payload.get("release", payload)
        release = _parse_release(release_payload, registry=record.name)
        if release.coordinate != str(parsed):
            raise ValueError(
                "P2P_REGISTRY_METADATA_MISMATCH: requested and returned coordinates differ"
            )
        if release.artifact.size > capabilities.max_artifact_bytes:
            raise ValueError(
                "P2P_REGISTRY_ARTIFACT_TOO_LARGE: release exceeds registry capability limit"
            )
        return release

    def artifact_url(self, release: VerticalRelease) -> str:
        record = self.configuration.resolve(release.registry)
        return _same_origin_url(record.url, release.artifact.url)

    def publish(
        self,
        release: VerticalRelease,
        artifact: Path,
        *,
        registry: str = "",
        lineage: dict[str, object] | None = None,
        idempotency_key: str,
    ) -> VerticalPublicationReceipt:
        record = self.configuration.resolve(registry)
        capabilities = self.capabilities(record.name)
        if not capabilities.endpoints.publish:
            raise ValueError(
                "P2P_REGISTRY_PUBLISH_UNSUPPORTED: registry does not advertise publication"
            )
        if not idempotency_key.strip():
            raise ValueError(
                "P2P_REGISTRY_IDEMPOTENCY_REQUIRED: publication requires an idempotency key"
            )
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError("P2P_REGISTRY_ARTIFACT_INVALID: publication artifact is unsafe")
        digest = hashlib.sha256()
        size = 0
        with artifact.open("rb") as handle:
            while chunk := handle.read(64 * 1024):
                digest.update(chunk)
                size += len(chunk)
        if size != release.artifact.size or digest.hexdigest() != release.artifact.sha256:
            raise ValueError(
                "P2P_REGISTRY_ARTIFACT_MISMATCH: publication artifact differs from release metadata"
            )
        if size > capabilities.max_artifact_bytes:
            raise ValueError(
                "P2P_REGISTRY_ARTIFACT_TOO_LARGE: release exceeds registry capability limit"
            )
        token = self._access_token(record.name, required=True)
        raw = self.transport.publish_artifact(
            self._api_url(record, capabilities, capabilities.endpoints.publish),
            artifact,
            metadata={
                "protocol_version": VERTICAL_REGISTRY_PROTOCOL_VERSION,
                "release": release.to_dict(),
                "lineage": dict(lineage or {}),
            },
            token=token,
            idempotency_key=idempotency_key.strip(),
            max_artifact_bytes=capabilities.max_artifact_bytes,
            max_response_bytes=VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES,
        )
        payload = _unwrap(raw, "vertical_publication")
        if not isinstance(payload, dict):
            raise ValueError(
                "P2P_REGISTRY_RESPONSE_INVALID: expected vertical_publication mapping"
            )
        _validate_protocol(payload.get("protocol_version"))
        receipt = payload.get("receipt", payload)
        if not isinstance(receipt, dict):
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: receipt must be a mapping")
        status = str(receipt.get("status") or "")
        if status not in {"published", "already_present", "pending_review"}:
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: invalid publication status")
        coordinate = str(VerticalCoordinate.parse(_required_text(receipt, "coordinate")))
        artifact_checksum = _checksum(
            receipt.get("artifact_checksum"),
            field="receipt artifact_checksum",
        )
        visibility = str(receipt.get("visibility") or release.visibility)
        if visibility not in {"public", "private"}:
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: invalid receipt visibility")
        if coordinate != release.coordinate or artifact_checksum != release.artifact.sha256:
            raise ValueError(
                "P2P_REGISTRY_METADATA_MISMATCH: publication receipt differs from submitted release"
            )
        return VerticalPublicationReceipt(
            registry=record.name,
            receipt_id=_required_text(receipt, "receipt_id"),
            status=status,
            coordinate=coordinate,
            artifact_checksum=artifact_checksum,
            visibility=visibility,
        )

    def access_token(self, registry: str, *, required: bool = False) -> str:
        record = self.configuration.resolve(registry)
        return self._access_token(record.name, required=required)

    def start_login(self, registry: str = "") -> tuple[str, DeviceAuthorization]:
        record = self.configuration.resolve(registry)
        capabilities = self.capabilities(record.name, refresh=True)
        oauth = capabilities.oauth_device
        if oauth is None:
            raise ValueError(
                "P2P_REGISTRY_AUTH_UNSUPPORTED: registry does not advertise OAuth device flow"
            )
        raw = self.transport.request_json(
            "POST",
            _same_origin_url(record.url, oauth.device_authorization_endpoint),
            form={
                "client_id": oauth.client_id,
                "scope": " ".join(oauth.scopes),
            },
            max_bytes=VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES,
        )
        if not isinstance(raw, dict):
            raise ValueError("P2P_REGISTRY_AUTH_INVALID: invalid device authorization response")
        try:
            authorization = DeviceAuthorization(
                device_code=_required_text(raw, "device_code"),
                user_code=_required_text(raw, "user_code"),
                verification_uri=_required_text(raw, "verification_uri"),
                verification_uri_complete=str(raw.get("verification_uri_complete") or ""),
                expires_in=max(1, int(raw.get("expires_in") or 600)),
                interval=max(1, int(raw.get("interval") or 5)),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("P2P_REGISTRY_AUTH_INVALID: invalid device authorization response") from exc
        return record.name, authorization

    def complete_login(self, registry: str, authorization: DeviceAuthorization) -> RegistryCredential:
        record = self.configuration.resolve(registry)
        capabilities = self.capabilities(record.name)
        oauth = capabilities.oauth_device
        if oauth is None:
            raise ValueError("P2P_REGISTRY_AUTH_UNSUPPORTED: OAuth device flow is unavailable")
        deadline = self.now() + authorization.expires_in
        interval = authorization.interval
        while self.now() < deadline:
            raw = self.transport.request_json(
                "POST",
                _same_origin_url(record.url, oauth.token_endpoint),
                form={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": authorization.device_code,
                    "client_id": oauth.client_id,
                },
                max_bytes=VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES,
            )
            if not isinstance(raw, dict):
                raise ValueError("P2P_REGISTRY_AUTH_INVALID: invalid token response")
            error = str(raw.get("error") or "")
            if error == "authorization_pending":
                self.sleep(interval)
                continue
            if error == "slow_down":
                interval += 5
                self.sleep(interval)
                continue
            if error:
                raise ValueError(f"P2P_REGISTRY_AUTH_FAILED: OAuth device flow returned {error}")
            credential = _parse_credential(raw, now=int(self.now()))
            self.credentials.set(record.name, credential)
            return credential
        raise ValueError("P2P_REGISTRY_AUTH_EXPIRED: device authorization expired")

    def logout(self, registry: str = "") -> tuple[str, bool]:
        record = self.configuration.resolve(registry)
        return record.name, self.credentials.delete(record.name)

    def _access_token(self, registry: str, *, required: bool) -> str:
        try:
            credential = self.credentials.get(registry)
        except ValueError as exc:
            if str(exc).startswith("P2P_REGISTRY_CREDENTIAL_STORE_UNAVAILABLE:"):
                if required:
                    raise ValueError(
                        "P2P_REGISTRY_AUTH_REQUIRED: no usable secure registry credential"
                    ) from exc
                return ""
            raise
        if credential is not None and (
            not credential.expires_at or credential.expires_at > int(self.now()) + 15
        ):
            return credential.access_token
        if credential is not None and credential.refresh_token:
            credential = self._refresh(registry, credential)
            return credential.access_token
        if required:
            raise ValueError(
                f"P2P_REGISTRY_AUTH_REQUIRED: login to registry `{registry}` before this operation"
            )
        return ""

    def _refresh(self, registry: str, credential: RegistryCredential) -> RegistryCredential:
        record = self.configuration.resolve(registry)
        capabilities = self.capabilities(record.name)
        oauth = capabilities.oauth_device
        if oauth is None:
            raise ValueError("P2P_REGISTRY_AUTH_REQUIRED: stored credential has expired")
        raw = self.transport.request_json(
            "POST",
            _same_origin_url(record.url, oauth.token_endpoint),
            form={
                "grant_type": "refresh_token",
                "refresh_token": credential.refresh_token,
                "client_id": oauth.client_id,
            },
            max_bytes=VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES,
        )
        if not isinstance(raw, dict) or raw.get("error"):
            raise ValueError("P2P_REGISTRY_AUTH_REQUIRED: stored credential could not be refreshed")
        refreshed = _parse_credential(raw, now=int(self.now()), previous=credential)
        self.credentials.set(record.name, refreshed)
        return refreshed

    @staticmethod
    def _api_url(
        record: VerticalRegistryRecord,
        capabilities: RegistryCapabilities,
        endpoint: str,
    ) -> str:
        api_base = _same_origin_url(record.url, capabilities.api_base)
        return _same_origin_url(record.url, urljoin(api_base.rstrip("/") + "/", endpoint))


def _validate_name(value: object) -> str:
    name = str(value or "").strip().lower()
    if not _REGISTRY_NAME.fullmatch(name):
        raise ValueError(
            "P2P_REGISTRY_INVALID_NAME: use 1-64 lowercase letters, digits, hyphens or underscores"
        )
    return name


def _normalize_url(value: object) -> str:
    text = str(value or "").strip()
    parsed = urlsplit(text)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("P2P_REGISTRY_INVALID_URL: embedded credentials are not allowed")
    if parsed.fragment or parsed.query:
        raise ValueError("P2P_REGISTRY_INVALID_URL: query and fragment are not allowed")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("P2P_REGISTRY_INVALID_URL: an absolute registry URL is required")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("P2P_REGISTRY_INVALID_URL: invalid registry port") from exc
    if parsed.scheme != "https" and not (parsed.scheme == "http" and hostname in _LOOPBACK_HOSTS):
        raise ValueError("P2P_REGISTRY_INVALID_URL: HTTPS is required outside loopback development")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _parse_capabilities(value: object) -> RegistryCapabilities:
    if not isinstance(value, dict):
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: capabilities must be a mapping")
    _validate_protocol(value.get("protocol_version"))
    endpoints = value.get("endpoints")
    if not isinstance(endpoints, dict):
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: endpoints must be a mapping")
    try:
        parsed_endpoints = RegistryEndpoints(
            search=_required_text(endpoints, "search"),
            releases=_required_text(endpoints, "releases"),
            release=_required_text(endpoints, "release"),
            publish=str(endpoints.get("publish") or "").strip(),
        )
        api_base = _required_text(value, "api_base")
        max_artifact_bytes = int(value.get("max_artifact_bytes") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: incomplete capabilities") from exc
    if max_artifact_bytes <= 0:
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: max_artifact_bytes must be positive")
    required_template_fields = {"{publisher}", "{vertical_id}", "{version}"}
    if any(token not in parsed_endpoints.release for token in required_template_fields):
        raise ValueError(
            "P2P_REGISTRY_RESPONSE_INVALID: release endpoint must contain "
            "publisher, vertical_id and version placeholders"
        )
    oauth_payload = value.get("oauth_device")
    oauth: OAuthDeviceConfiguration | None = None
    if oauth_payload is not None:
        if not isinstance(oauth_payload, dict):
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: oauth_device must be a mapping")
        scopes = oauth_payload.get("scopes", [])
        if not isinstance(scopes, list):
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: OAuth scopes must be a list")
        oauth = OAuthDeviceConfiguration(
            device_authorization_endpoint=_required_text(
                oauth_payload, "device_authorization_endpoint"
            ),
            token_endpoint=_required_text(oauth_payload, "token_endpoint"),
            client_id=_required_text(oauth_payload, "client_id"),
            scopes=tuple(str(item) for item in scopes if str(item)),
        )
    return RegistryCapabilities(
        protocol_version=VERTICAL_REGISTRY_PROTOCOL_VERSION,
        api_base=api_base,
        max_artifact_bytes=max_artifact_bytes,
        endpoints=parsed_endpoints,
        oauth_device=oauth,
    )


def _parse_release(value: object, *, registry: str) -> VerticalRelease:
    if not isinstance(value, dict):
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: release must be a mapping")
    coordinate = str(VerticalCoordinate.parse(_required_text(value, "coordinate")))
    visibility = str(value.get("visibility") or "public")
    if visibility not in {"public", "private"}:
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: visibility must be public or private")
    semantic_checksum = _checksum(value.get("semantic_checksum"), field="semantic_checksum")
    try:
        schema_version = int(value.get("schema_version") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: schema_version must be an integer") from exc
    if schema_version != PORTABLE_VERTICAL_SCHEMA_VERSION:
        raise ValueError(
            "P2P_REGISTRY_SCHEMA_UNSUPPORTED: release does not use portable schema version 2"
        )
    artifact = value.get("artifact")
    if not isinstance(artifact, dict):
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: artifact must be a mapping")
    try:
        size = int(artifact.get("size") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: artifact size must be an integer") from exc
    if size <= 0:
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: artifact size must be positive")
    dependencies_payload = value.get("dependencies", [])
    if not isinstance(dependencies_payload, list):
        raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: dependencies must be a list")
    dependencies: list[VerticalReleaseDependency] = []
    seen: set[str] = set()
    for dependency in dependencies_payload:
        if not isinstance(dependency, dict):
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: dependency must be a mapping")
        dependency_coordinate = str(
            VerticalCoordinate.parse(_required_text(dependency, "coordinate"))
        )
        if dependency_coordinate in seen:
            raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: duplicate release dependency")
        seen.add(dependency_coordinate)
        dependencies.append(
            VerticalReleaseDependency(
                coordinate=dependency_coordinate,
                semantic_checksum=_checksum(
                    dependency.get("semantic_checksum"),
                    field="dependency semantic_checksum",
                ),
            )
        )
    return VerticalRelease(
        coordinate=coordinate,
        name=str(value.get("name") or VerticalCoordinate.parse(coordinate).vertical_id),
        description=str(value.get("description") or ""),
        visibility=visibility,
        semantic_checksum=semantic_checksum,
        schema_version=schema_version,
        artifact=VerticalReleaseArtifact(
            url=_required_text(artifact, "url"),
            sha256=_checksum(artifact.get("sha256"), field="artifact sha256"),
            size=size,
        ),
        dependencies=tuple(dependencies),
        registry=registry,
    )


def parse_vertical_release(value: object, *, registry: str) -> VerticalRelease:
    """Parse one provider-neutral protocol-v1 release document."""
    return _parse_release(value, registry=registry)


def _parse_credential(
    value: dict[object, object],
    *,
    now: int,
    previous: RegistryCredential | None = None,
) -> RegistryCredential:
    access_token = _required_text(value, "access_token")
    try:
        expires_in = max(0, int(value.get("expires_in") or 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("P2P_REGISTRY_AUTH_INVALID: expires_in must be an integer") from exc
    scope = value.get("scope", "")
    scopes = tuple(str(scope).split()) if scope else (previous.scopes if previous else ())
    return RegistryCredential(
        access_token=access_token,
        refresh_token=str(value.get("refresh_token") or (previous.refresh_token if previous else "")),
        token_type=str(value.get("token_type") or "Bearer"),
        expires_at=now + expires_in if expires_in else 0,
        scopes=scopes,
    )


def _validate_protocol(value: object) -> None:
    if str(value or "") != VERTICAL_REGISTRY_PROTOCOL_VERSION:
        raise ValueError(
            "P2P_REGISTRY_PROTOCOL_UNSUPPORTED: expected p2p-vertical-registry/v1"
        )


def _unwrap(value: object, key: str) -> object:
    if isinstance(value, dict) and key in value:
        return value[key]
    return value


def _required_text(value: dict[object, object], field: str) -> str:
    text = str(value.get(field) or "").strip()
    if not text:
        raise ValueError(f"missing {field}")
    return text


def _checksum(value: object, *, field: str) -> str:
    checksum = str(value or "").strip().lower()
    if checksum.startswith("sha256:"):
        checksum = checksum.removeprefix("sha256:")
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError(f"P2P_REGISTRY_RESPONSE_INVALID: {field} must be a SHA-256 checksum")
    return checksum


def _same_origin_url(base: str, value: str) -> str:
    target = urljoin(base.rstrip("/") + "/", str(value))
    base_parts = urlsplit(base)
    target_parts = urlsplit(target)
    try:
        base_port = base_parts.port
        target_port = target_parts.port
    except ValueError as exc:
        raise ValueError("P2P_REGISTRY_INVALID_URL: invalid advertised port") from exc
    if (
        target_parts.scheme != base_parts.scheme
        or target_parts.hostname != base_parts.hostname
        or target_port != base_port
        or target_parts.username is not None
        or target_parts.password is not None
        or target_parts.fragment
        or target_parts.query
    ):
        raise ValueError("P2P_REGISTRY_INVALID_URL: registry URL must remain on the configured origin")
    return target

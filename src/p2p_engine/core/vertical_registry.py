from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


VERTICAL_REGISTRY_CONFIG_SCHEMA_VERSION = 1
VERTICAL_REGISTRY_PROTOCOL_VERSION = "p2p-vertical-registry/v2"
VERTICAL_REGISTRY_CAPABILITY_PATH = "/.well-known/p2p-vertical-registry"
VERTICAL_REGISTRY_MAX_DOCUMENT_BYTES = 1_048_576
VERTICAL_REGISTRY_MAX_ARTIFACT_BYTES = 8_388_608
VERTICAL_REGISTRY_MAX_PAGE_SIZE = 100
VERTICAL_REGISTRY_MAX_PAGES = 10
VERTICAL_REGISTRY_MAX_CURSOR_LENGTH = 1024
VERTICAL_REGISTRY_UNCATEGORIZED_DOMAIN = "uncategorized"


@dataclass(frozen=True)
class VerticalUserPaths:
    data_root: Path
    cache_root: Path

    @property
    def registry_config_path(self) -> Path:
        return self.data_root / "registries.yml"

    @property
    def vertical_cache_root(self) -> Path:
        return self.cache_root / "verticals"

    @property
    def vertical_drafts_root(self) -> Path:
        return self.data_root / "vertical-drafts"


@dataclass(frozen=True)
class VerticalRegistryRecord:
    name: str
    url: str
    protocol_version: str = VERTICAL_REGISTRY_PROTOCOL_VERSION
    capabilities: "RegistryCapabilities | None" = None


@dataclass(frozen=True)
class VerticalRegistryConfiguration:
    default_registry: str
    registries: tuple[VerticalRegistryRecord, ...]
    path: Path


@dataclass(frozen=True)
class RegistryEndpoints:
    domains: str
    domain: str
    search: str
    releases: str
    release: str
    publish: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "domains": self.domains,
            "domain": self.domain,
            "search": self.search,
            "releases": self.releases,
            "release": self.release,
            "publish": self.publish,
        }


@dataclass(frozen=True)
class OAuthDeviceConfiguration:
    device_authorization_endpoint: str
    token_endpoint: str
    client_id: str
    scopes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "device_authorization_endpoint": self.device_authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "client_id": self.client_id,
            "scopes": list(self.scopes),
        }


@dataclass(frozen=True)
class RegistryCapabilities:
    protocol_version: str
    api_base: str
    max_artifact_bytes: int
    endpoints: RegistryEndpoints
    oauth_device: OAuthDeviceConfiguration | None = None
    supports_uncategorized_filter: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "protocol_version": self.protocol_version,
            "api_base": self.api_base,
            "max_artifact_bytes": self.max_artifact_bytes,
            "endpoints": self.endpoints.to_dict(),
            "oauth_device": self.oauth_device.to_dict() if self.oauth_device else None,
            "supports_uncategorized_filter": self.supports_uncategorized_filter,
        }


@dataclass(frozen=True)
class RegistryCredential:
    access_token: str
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_at: int = 0
    scopes: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, object]:
        return {
            "authenticated": bool(self.access_token),
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "scopes": list(self.scopes),
        }


@dataclass(frozen=True)
class DeviceAuthorization:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str = ""
    expires_in: int = 600
    interval: int = 5

    def public_dict(self) -> dict[str, object]:
        return {
            "user_code": self.user_code,
            "verification_uri": self.verification_uri,
            "verification_uri_complete": self.verification_uri_complete,
            "expires_in": self.expires_in,
            "interval": self.interval,
        }


@dataclass(frozen=True)
class RegistryPage:
    returned: int
    next_cursor: str = ""
    truncated: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "returned": self.returned,
            "next_cursor": self.next_cursor,
            "truncated": self.truncated,
        }


@dataclass(frozen=True)
class RecommendedVerticalRelease:
    coordinate: str
    semantic_checksum: str
    artifact_sha256: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "coordinate": self.coordinate,
            "semantic_checksum": self.semantic_checksum,
            "artifact_sha256": self.artifact_sha256,
        }


@dataclass(frozen=True)
class RegistryDomainReference:
    external_id: str
    key: str
    name: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "external_id": self.external_id,
            "key": self.key,
            "name": self.name,
        }


@dataclass(frozen=True)
class RegistryDomain:
    external_id: str
    key: str
    name: str
    description: str
    visibility: str
    lifecycle: str
    publisher: str = ""
    recommended_release: RecommendedVerticalRelease | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "external_id": self.external_id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "visibility": self.visibility,
            "lifecycle": self.lifecycle,
            "publisher": self.publisher,
            "recommended_release": (
                self.recommended_release.to_dict()
                if self.recommended_release is not None
                else None
            ),
        }


@dataclass(frozen=True)
class VerticalReleaseDependency:
    coordinate: str
    semantic_checksum: str

    def to_dict(self) -> dict[str, str]:
        return {
            "coordinate": self.coordinate,
            "semantic_checksum": self.semantic_checksum,
        }


@dataclass(frozen=True)
class VerticalReleaseArtifact:
    url: str
    sha256: str
    size: int

    def to_dict(self) -> dict[str, object]:
        return {"url": self.url, "sha256": self.sha256, "size": self.size}


@dataclass(frozen=True)
class VerticalRelease:
    coordinate: str
    name: str
    description: str
    visibility: str
    semantic_checksum: str
    schema_version: int
    artifact: VerticalReleaseArtifact
    dependencies: tuple[VerticalReleaseDependency, ...] = ()
    primary_domain: RegistryDomainReference | None = None
    registry: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "coordinate": self.coordinate,
            "name": self.name,
            "description": self.description,
            "visibility": self.visibility,
            "semantic_checksum": self.semantic_checksum,
            "schema_version": self.schema_version,
            "artifact": self.artifact.to_dict(),
            "dependencies": [item.to_dict() for item in self.dependencies],
            "primary_domain": (
                self.primary_domain.to_dict()
                if self.primary_domain is not None
                else None
            ),
            "registry": self.registry,
        }


@dataclass(frozen=True)
class ArtifactDownload:
    path: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class VerticalCatalogItem:
    coordinate: str
    name: str
    description: str = ""
    source: str = "local"
    visibility: str = "local"
    registry: str = ""
    semantic_checksum: str = ""
    artifact_checksum: str = ""
    artifact_path: Path | None = None
    local_available: bool = True
    primary_domain: RegistryDomainReference | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "coordinate": self.coordinate,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "visibility": self.visibility,
            "registry": self.registry,
            "semantic_checksum": self.semantic_checksum,
            "artifact_checksum": self.artifact_checksum,
            "artifact_path": str(self.artifact_path) if self.artifact_path else None,
            "local_available": self.local_available,
            "primary_domain": (
                self.primary_domain.to_dict()
                if self.primary_domain is not None
                else None
            ),
        }


@dataclass(frozen=True)
class CachedVerticalRelease:
    release: VerticalRelease
    artifact_path: Path
    metadata_path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "release": self.release.to_dict(),
            "artifact_path": str(self.artifact_path),
            "metadata_path": str(self.metadata_path),
        }


@dataclass(frozen=True)
class VerticalPullResult:
    registry: str
    requested_coordinate: str
    status: str
    releases: tuple[CachedVerticalRelease, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "registry": self.registry,
            "requested_coordinate": self.requested_coordinate,
            "status": self.status,
            "releases": [item.to_dict() for item in self.releases],
        }


@dataclass(frozen=True)
class VerticalPublicationReceipt:
    registry: str
    receipt_id: str
    status: str
    coordinate: str
    artifact_checksum: str
    visibility: str

    def to_dict(self) -> dict[str, str]:
        return {
            "registry": self.registry,
            "receipt_id": self.receipt_id,
            "status": self.status,
            "coordinate": self.coordinate,
            "artifact_checksum": self.artifact_checksum,
            "visibility": self.visibility,
        }

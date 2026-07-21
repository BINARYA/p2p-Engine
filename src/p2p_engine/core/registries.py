from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Mapping


REGISTRY_MANIFEST_VERSION = 1
REGISTRY_GENERATOR_CONTRACT_VERSION = "registry-bundle-v1"
REGISTRY_SOURCE_CATALOG_POLICY_VERSION = "registry-sources-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RegistryOutputManifest:
    sha256: str
    records: int

    def to_dict(self) -> dict[str, object]:
        return {"sha256": self.sha256, "records": self.records}


@dataclass(frozen=True)
class RegistryBundleManifest:
    manifest_version: int
    generator_contract_version: str
    source_catalog_policy_version: str
    source_fingerprint_sha256: str
    source_scopes: Mapping[str, str]
    outputs: Mapping[str, RegistryOutputManifest]
    owned_paths: tuple[str, ...]

    def validate(self) -> None:
        if self.manifest_version != REGISTRY_MANIFEST_VERSION:
            raise ValueError(
                f"Unsupported registry manifest version: {self.manifest_version}"
            )
        if self.generator_contract_version != REGISTRY_GENERATOR_CONTRACT_VERSION:
            raise ValueError("Unsupported registry generator contract")
        if self.source_catalog_policy_version != REGISTRY_SOURCE_CATALOG_POLICY_VERSION:
            raise ValueError("Unsupported registry source catalog policy")
        hashes = [self.source_fingerprint_sha256, *self.source_scopes.values()]
        hashes.extend(item.sha256 for item in self.outputs.values())
        if any(not _SHA256.fullmatch(value) for value in hashes):
            raise ValueError("Registry manifest contains an invalid SHA-256 value")
        if any(item.records < 0 for item in self.outputs.values()):
            raise ValueError("Registry manifest contains a negative record count")
        if len(set(self.owned_paths)) != len(self.owned_paths):
            raise ValueError("Registry manifest contains duplicate owned paths")
        for path in self.owned_paths:
            if not path.startswith(".p2p/registries/") or ".." in path.split("/"):
                raise ValueError(f"Unsafe registry owned path: {path}")

    def to_dict(self) -> dict[str, object]:
        return {
            "registry_bundle": {
                "manifest_version": self.manifest_version,
                "generator_contract_version": self.generator_contract_version,
                "source_catalog_policy_version": self.source_catalog_policy_version,
                "source_fingerprint": {
                    "algorithm": "sha256",
                    "value": self.source_fingerprint_sha256,
                },
                "source_scopes": dict(sorted(self.source_scopes.items())),
                "outputs": {
                    name: value.to_dict()
                    for name, value in sorted(self.outputs.items())
                },
                "owned_paths": list(self.owned_paths),
            }
        }


@dataclass(frozen=True)
class RegistryStatus:
    registries_dir: Path
    files: tuple[Mapping[str, object], ...]
    proposals_count: int
    changes_count: int
    stale: bool
    state: str = "unknown"
    reason: str = ""
    manifest_version: int | None = None
    source_fingerprint_sha256: str = ""
    current_source_fingerprint_sha256: str = ""
    verification: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "registries_dir": str(self.registries_dir),
            "files": [dict(item) for item in self.files],
            "proposals_count": self.proposals_count,
            "changes_count": self.changes_count,
            "stale": self.stale,
            "state": self.state,
            "reason": self.reason,
            "manifest_version": self.manifest_version,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "current_source_fingerprint_sha256": self.current_source_fingerprint_sha256,
            "verification": dict(self.verification),
        }

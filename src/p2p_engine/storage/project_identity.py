from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

import yaml

from p2p_engine.core.project_identity import (
    PROJECT_IDENTITY_CONTRACT,
    PROJECT_IDENTITY_POLICY_VERSION,
    PROJECT_REPLICA_CONTRACT,
    ProjectIdentity,
    ProjectMode,
    ProjectUuid,
    ReplicaId,
    SourceMemoryRevision,
    lineage_from_mapping,
    remote_binding_from_mapping,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml

PROJECT_IDENTITY_PATH = ".p2p/project/identity.yml"
PROJECT_REPLICA_PATH = ".p2p/local/replica.yml"
PROJECT_MANIFEST_PATH = ".p2p/project.yml"
PROJECT_IDENTITY_MAX_BYTES = 65_536
PROJECT_REPLICA_MAX_BYTES = 16_384

_CANONICAL_KEYS = frozenset(
    {"contract", "policy_version", "project_uuid", "display_name", "lineage"}
)
_REPLICA_KEYS = frozenset({"contract", "project_uuid", "mode", "replica_id", "remote_binding"})


class FilesystemProjectIdentityStore:
    """Filesystem adapter for the storage-neutral project identity aggregate."""

    def __init__(self, *, root: Path, p2p_dir: Path | None = None) -> None:
        self.root = root.resolve()
        self.p2p_dir = (p2p_dir or self.root / ".p2p").resolve()

    @property
    def identity_path(self) -> Path:
        return self.root / PROJECT_IDENTITY_PATH

    @property
    def replica_path(self) -> Path:
        return self.root / PROJECT_REPLICA_PATH

    @property
    def manifest_path(self) -> Path:
        return self.root / PROJECT_MANIFEST_PATH

    def exists(self) -> bool:
        return self.identity_path.exists() or self.replica_path.exists()

    def complete(self) -> bool:
        return self.identity_path.is_file() and self.replica_path.is_file()

    def load(self) -> ProjectIdentity:
        canonical = self._read_document(
            self.identity_path,
            max_bytes=PROJECT_IDENTITY_MAX_BYTES,
            root_key="project_identity",
            missing_code="P2P_PROJECT_IDENTITY_ADOPTION_REQUIRED",
        )
        if set(canonical) != _CANONICAL_KEYS:
            raise ValueError(
                "P2P_PROJECT_IDENTITY_INVALID: canonical identity fields are not exact"
            )
        if canonical.get("contract") != PROJECT_IDENTITY_CONTRACT:
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: unsupported project identity contract")
        policy_version = canonical.get("policy_version")
        if (
            isinstance(policy_version, bool)
            or not isinstance(policy_version, int)
            or policy_version != PROJECT_IDENTITY_POLICY_VERSION
        ):
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: unsupported identity policy version")
        raw_lineage = canonical.get("lineage")
        if not isinstance(raw_lineage, list):
            raise ValueError("P2P_PROJECT_LINEAGE_INVALID: lineage must be a sequence")
        replica = self._read_document(
            self.replica_path,
            max_bytes=PROJECT_REPLICA_MAX_BYTES,
            root_key="project_replica",
            missing_code="P2P_PROJECT_REPLICA_MISSING",
        )
        if set(replica) != _REPLICA_KEYS:
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: local replica fields are not exact")
        if replica.get("contract") != PROJECT_REPLICA_CONTRACT:
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: unsupported project replica contract")
        project_uuid = ProjectUuid(str(canonical.get("project_uuid") or ""))
        replica_project_uuid = ProjectUuid(str(replica.get("project_uuid") or ""))
        if project_uuid != replica_project_uuid:
            raise ValueError("P2P_PROJECT_IDENTITY_MISMATCH: canonical and replica UUIDs differ")
        manifest = self.manifest()
        project = manifest.get("project")
        if not isinstance(project, Mapping):
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: project manifest lacks project mapping")
        hint = project.get("uuid")
        if hint is None:
            raise ValueError("P2P_PROJECT_IDENTITY_MISMATCH: project manifest UUID hint is missing")
        if ProjectUuid(str(hint)) != project_uuid:
            raise ValueError("P2P_PROJECT_IDENTITY_MISMATCH: manifest and canonical UUIDs differ")
        manifest_name = str(project.get("name") or "").strip()
        canonical_name = str(canonical.get("display_name") or "").strip()
        if not manifest_name or manifest_name != canonical_name:
            raise ValueError(
                "P2P_PROJECT_IDENTITY_MISMATCH: manifest and canonical display names differ"
            )
        try:
            mode = ProjectMode(str(replica.get("mode") or ""))
        except ValueError as exc:
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: project mode is unsupported") from exc
        raw_replica_id = replica.get("replica_id")
        replica_id = ReplicaId(str(raw_replica_id)) if raw_replica_id is not None else None
        return ProjectIdentity(
            project_uuid=project_uuid,
            display_name=canonical_name,
            mode=mode,
            replica_id=replica_id,
            remote_binding=remote_binding_from_mapping(replica.get("remote_binding")),
            lineage=tuple(
                lineage_from_mapping(item)
                if isinstance(item, Mapping)
                else _invalid_lineage_entry()
                for item in raw_lineage
            ),
        )

    def manifest(self) -> dict[str, object]:
        return self._read_root_mapping(
            self.manifest_path,
            max_bytes=PROJECT_IDENTITY_MAX_BYTES,
            missing_code="P2P_PROJECT_IDENTITY_ADOPTION_REQUIRED",
        )

    def manifest_name(self) -> str:
        project = self.manifest().get("project")
        if not isinstance(project, Mapping) or not str(project.get("name") or "").strip():
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: project manifest name is missing")
        return str(project["name"]).strip()

    def candidate_documents(
        self,
        identity: ProjectIdentity,
        *,
        allow_project_uuid_change: bool = False,
    ) -> dict[str, bytes]:
        manifest = self.manifest()
        project = manifest.get("project")
        if not isinstance(project, dict):
            raise ValueError(
                "P2P_PROJECT_IDENTITY_INVALID: project manifest lacks mutable project mapping"
            )
        existing_hint = project.get("uuid")
        if (
            existing_hint is not None
            and ProjectUuid(str(existing_hint)) != identity.project_uuid
            and not allow_project_uuid_change
        ):
            raise ValueError(
                "P2P_PROJECT_IDENTITY_MISMATCH: refusing to overwrite a different manifest UUID"
            )
        project["uuid"] = identity.project_uuid.value
        project["name"] = identity.display_name
        return {
            PROJECT_IDENTITY_PATH: self.identity_bytes(identity),
            PROJECT_REPLICA_PATH: self.replica_bytes(identity),
            PROJECT_MANIFEST_PATH: yaml_dump(manifest).encode("ascii"),
        }

    def initialization_documents(self, identity: ProjectIdentity) -> dict[Path, str]:
        return {
            self.identity_path: self.identity_bytes(identity).decode("ascii"),
            self.replica_path: self.replica_bytes(identity).decode("ascii"),
        }

    def identity_bytes(self, identity: ProjectIdentity) -> bytes:
        return yaml_dump({"project_identity": identity.canonical_project_dict()}).encode("ascii")

    def replica_bytes(self, identity: ProjectIdentity) -> bytes:
        return yaml_dump({"project_replica": identity.local_replica_dict()}).encode("ascii")

    def source_revision(self) -> SourceMemoryRevision:
        if not self.p2p_dir.is_dir() or self.p2p_dir.is_symlink():
            raise ValueError(
                "P2P_PROJECT_IDENTITY_INVALID: project memory root is missing or unsafe"
            )
        digest = hashlib.sha256()
        included = 0
        for path in sorted(self.p2p_dir.rglob("*")):
            if path.is_symlink():
                raise ValueError("P2P_PROJECT_IDENTITY_INVALID: project memory contains a symlink")
            if not path.is_file():
                continue
            relative = path.relative_to(self.p2p_dir).as_posix()
            if (
                relative.startswith(".internal/")
                or relative.startswith("consents/")
                or relative.startswith("local/")
            ):
                continue
            content = path.read_bytes()
            encoded = relative.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
            included += 1
        if not included:
            raise ValueError(
                "P2P_PROJECT_IDENTITY_INVALID: project memory has no canonical documents"
            )
        return SourceMemoryRevision(digest.hexdigest())

    def _read_document(
        self,
        path: Path,
        *,
        max_bytes: int,
        root_key: str,
        missing_code: str,
    ) -> Mapping[str, object]:
        payload = self._read_root_mapping(
            path,
            max_bytes=max_bytes,
            missing_code=missing_code,
        )
        if set(payload) != {root_key} or not isinstance(payload.get(root_key), Mapping):
            raise ValueError(f"P2P_PROJECT_IDENTITY_INVALID: {root_key} document root is invalid")
        value = payload[root_key]
        assert isinstance(value, Mapping)
        return value

    @staticmethod
    def _read_root_mapping(
        path: Path,
        *,
        max_bytes: int,
        missing_code: str,
    ) -> dict[str, object]:
        if not path.exists():
            raise ValueError(f"{missing_code}: {path.name} is missing")
        if path.is_symlink() or not path.is_file():
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: identity path is not a regular file")
        if path.stat().st_size > max_bytes:
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: identity document exceeds size limit")
        try:
            payload = load_yaml(path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT)
        except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
            raise ValueError(
                f"P2P_PROJECT_IDENTITY_INVALID: cannot parse {path.name}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError("P2P_PROJECT_IDENTITY_INVALID: identity document must be a mapping")
        return payload


def _invalid_lineage_entry():
    raise ValueError("P2P_PROJECT_LINEAGE_INVALID: lineage entry must be a mapping")

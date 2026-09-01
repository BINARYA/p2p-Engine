from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Protocol

from p2p_engine.core.canonical_memory import (
    BACKUP_ARCHIVE_ROOT,
    BUNDLE_ARCHIVE_ROOT,
    CANONICAL_MEMORY_CONTRACT,
    DOMAIN_CONTRACT,
    MEMORY_SCHEMA_VERSION,
    PHYSICAL_BACKUP_SCHEMA,
    PROJECT_BUNDLE_SCHEMA,
    BundleExportResult,
    BundleValidationResult,
    CanonicalEntity,
    CanonicalMemoryInventory,
    CanonicalMemorySnapshot,
    CanonicalRelation,
    ManagedBlob,
    MemoryRecoveryStatus,
    MemoryRestorePreview,
    MemoryRestoreResult,
    PhysicalBackupResult,
    ProjectBundleManifest,
    canonical_json_bytes,
    normalize_semantic_value,
    semantic_sha256,
)
from p2p_engine.core.project_identity import ProjectIdentity, ProjectUuid
from p2p_engine.foundation.files import sync_directory, write_bytes_atomic, write_yaml_atomic
from p2p_engine.services.mutation_receipts import idempotency_key_sha256, validate_idempotency_key
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
from p2p_engine.storage.canonical_memory import (
    FilesystemCanonicalMemoryStore,
    managed_blob_references,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BUNDLE_CORE_ENTRIES = frozenset(
    {
        f"{BUNDLE_ARCHIVE_ROOT}/manifest.json",
        f"{BUNDLE_ARCHIVE_ROOT}/entities.jsonl",
        f"{BUNDLE_ARCHIVE_ROOT}/relations.jsonl",
        f"{BUNDLE_ARCHIVE_ROOT}/lineage.jsonl",
        f"{BUNDLE_ARCHIVE_ROOT}/blob-manifest.jsonl",
        f"{BUNDLE_ARCHIVE_ROOT}/checksums.json",
    }
)
_BACKUP_MANIFEST_ENTRY = f"{BACKUP_ARCHIVE_ROOT}/manifest.json"
_CANONICAL_NAMESPACES = frozenset(
    {
        "project",
        "changes",
        "choices",
        "config",
        "governance",
        "intake",
        "proposals",
        "templates",
        "verticals",
        "work",
    }
)
_PROJECT_SINGLETON_COORDINATES = frozenset(
    {
        "authority-events",
        "authority",
        "conflicts",
        "definition",
        "domain",
        "identity",
        "interaction-style",
        "manifest",
        "next-actions-log",
        "next-actions",
        "operational-brief",
        "permissions",
        "questions",
        "rubrics",
        "runtime",
        "structure-events",
        "structure-snapshots",
        "structure-source",
        "structure",
        "vertical.lock",
        "vertical",
        "workspace-schema",
    }
)
_CANONICAL_MEDIA_TYPES = frozenset({"application/json", "application/yaml", "text/markdown"})


class CanonicalMemoryPort(Protocol):
    def inventory(self) -> CanonicalMemoryInventory: ...

    def project_identity(self) -> ProjectIdentity: ...

    def read_entities(self, inventory: CanonicalMemoryInventory) -> tuple[CanonicalEntity, ...]: ...

    def read_relations(
        self, entities: Iterable[CanonicalEntity]
    ) -> tuple[CanonicalRelation, ...]: ...

    def read_blobs(self, inventory: CanonicalMemoryInventory) -> tuple[ManagedBlob, ...]: ...

    def read_blob_bytes(self, blob: ManagedBlob) -> bytes: ...


@dataclass(frozen=True)
class BundleLimits:
    max_archive_bytes: int = 1024 * 1024 * 1024
    max_entries: int = 100_000
    max_entities: int = 250_000
    max_relations: int = 500_000
    max_blobs: int = 50_000
    max_entry_bytes: int = 256 * 1024 * 1024
    max_total_uncompressed_bytes: int = 2 * 1024 * 1024 * 1024
    max_compression_ratio: int = 200


@dataclass(frozen=True)
class DecodedBundle:
    manifest: ProjectBundleManifest
    snapshot: CanonicalMemorySnapshot
    blob_bytes: Mapping[str, bytes]
    archive_sha256: str


@dataclass(frozen=True)
class DecodedPhysicalBackup:
    manifest: Mapping[str, object]
    files: Mapping[str, bytes]
    archive_sha256: str

    @property
    def project_uuid(self) -> str:
        return str(self.manifest.get("project_uuid") or "")

    @property
    def semantic_state_digest(self) -> str:
        return str(self.manifest.get("semantic_state_digest") or "")


class CanonicalBundleCodec:
    def __init__(self, *, limits: BundleLimits | None = None) -> None:
        self.limits = limits or BundleLimits()

    def snapshot(self, store: CanonicalMemoryPort) -> CanonicalMemorySnapshot:
        inventory = store.inventory()
        if inventory.blockers:
            raise ValueError(
                "P2P_CANONICAL_MEMORY_UNCLASSIFIED: "
                + ", ".join(item.locator for item in inventory.blockers[:20])
            )
        identity = store.project_identity()
        entities = store.read_entities(inventory)
        relations = store.read_relations(entities)
        blobs = store.read_blobs(inventory)
        lineage_items: list[Mapping[str, object]] = []
        for item in identity.lineage:
            normalized_lineage = normalize_semantic_value(item.to_dict())
            if not isinstance(normalized_lineage, Mapping):
                raise ValueError("P2P_PROJECT_LINEAGE_INVALID: lineage normalization failed")
            lineage_items.append(normalized_lineage)
        lineage = tuple(sorted(lineage_items, key=canonical_json_bytes))
        self._validate_snapshot_members(
            project_uuid=identity.project_uuid.value,
            entities=entities,
            relations=relations,
            lineage=lineage,
            blobs=blobs,
        )
        blob_manifest_digest = semantic_sha256([item.to_dict() for item in blobs])
        state_payload = {
            "contract": CANONICAL_MEMORY_CONTRACT,
            "project_uuid": identity.project_uuid.value,
            "memory_schema": MEMORY_SCHEMA_VERSION,
            "domain_contract": DOMAIN_CONTRACT,
            "entities": [item.to_dict() for item in entities],
            "relations": [item.to_dict() for item in relations],
            "lineage": list(lineage),
            "blobs": [item.to_dict() for item in blobs],
        }
        digest = semantic_sha256(state_payload)
        return CanonicalMemorySnapshot(
            project_uuid=identity.project_uuid.value,
            entities=entities,
            relations=relations,
            lineage=lineage,
            blobs=blobs,
            semantic_state_digest=digest,
            blob_manifest_digest=blob_manifest_digest,
            source_revision={"kind": "local", "value": digest},
        )

    def manifest(self, snapshot: CanonicalMemorySnapshot) -> ProjectBundleManifest:
        return ProjectBundleManifest(
            project_uuid=snapshot.project_uuid,
            source_revision=snapshot.source_revision,
            semantic_state_digest=snapshot.semantic_state_digest,
            blob_manifest_digest=snapshot.blob_manifest_digest,
            entity_count=len(snapshot.entities),
            relation_count=len(snapshot.relations),
            lineage_count=len(snapshot.lineage),
            blob_count=len(snapshot.blobs),
            blob_bytes=sum(item.size for item in snapshot.blobs),
        )

    def encode_bundle(
        self,
        store: CanonicalMemoryPort,
        snapshot: CanonicalMemorySnapshot,
    ) -> tuple[bytes, ProjectBundleManifest]:
        self._validate_snapshot_limits(snapshot)
        manifest = self.manifest(snapshot)
        entries: dict[str, bytes] = {
            f"{BUNDLE_ARCHIVE_ROOT}/manifest.json": canonical_json_bytes(manifest.to_dict()),
            f"{BUNDLE_ARCHIVE_ROOT}/entities.jsonl": _json_lines(
                item.to_dict() for item in snapshot.entities
            ),
            f"{BUNDLE_ARCHIVE_ROOT}/relations.jsonl": _json_lines(
                item.to_dict() for item in snapshot.relations
            ),
            f"{BUNDLE_ARCHIVE_ROOT}/lineage.jsonl": _json_lines(snapshot.lineage),
            f"{BUNDLE_ARCHIVE_ROOT}/blob-manifest.jsonl": _json_lines(
                item.to_dict() for item in snapshot.blobs
            ),
        }
        for blob in snapshot.blobs:
            digest = blob.digest.removeprefix("sha256:")
            content = store.read_blob_bytes(blob)
            entries[f"{BUNDLE_ARCHIVE_ROOT}/blobs/sha256/{digest[:2]}/{digest}"] = content
        checksums = {
            "contract": "p2p-project-bundle-checksums/v1",
            "entries": {
                name: {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
                for name, content in sorted(entries.items())
            },
        }
        entries[f"{BUNDLE_ARCHIVE_ROOT}/checksums.json"] = canonical_json_bytes(checksums)
        self._validate_encoded_entries(entries)
        archive = _deterministic_zip(entries)
        if len(archive) > self.limits.max_archive_bytes:
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: encoded archive is too large")
        return archive, manifest

    def decode_bundle(self, archive: Path | bytes) -> DecodedBundle:
        raw = _archive_bytes(archive, self.limits.max_archive_bytes)
        entries = self._read_archive(raw)
        if not _BUNDLE_CORE_ENTRIES <= set(entries):
            missing = sorted(_BUNDLE_CORE_ENTRIES - set(entries))
            raise ValueError(f"P2P_BUNDLE_ENTRY_MISSING: {', '.join(missing)}")
        unexpected = [
            name
            for name in entries
            if name not in _BUNDLE_CORE_ENTRIES
            and not re.fullmatch(
                rf"{re.escape(BUNDLE_ARCHIVE_ROOT)}/blobs/sha256/[0-9a-f]{{2}}/[0-9a-f]{{64}}",
                name,
            )
        ]
        if unexpected:
            raise ValueError(f"P2P_BUNDLE_ENTRY_UNEXPECTED: {unexpected[0]}")
        self._verify_checksums(entries)
        manifest = _manifest_from_mapping(
            _json_mapping(entries[f"{BUNDLE_ARCHIVE_ROOT}/manifest.json"], "manifest")
        )
        entities = tuple(
            _entity_from_mapping(item)
            for item in _json_lines_decode(
                entries[f"{BUNDLE_ARCHIVE_ROOT}/entities.jsonl"],
                "entities",
                self.limits.max_entities,
            )
        )
        relations = tuple(
            _relation_from_mapping(item)
            for item in _json_lines_decode(
                entries[f"{BUNDLE_ARCHIVE_ROOT}/relations.jsonl"],
                "relations",
                self.limits.max_relations,
            )
        )
        lineage = tuple(
            _mapping(item, "lineage entry")
            for item in _json_lines_decode(
                entries[f"{BUNDLE_ARCHIVE_ROOT}/lineage.jsonl"],
                "lineage",
                32,
            )
        )
        blobs = tuple(
            _blob_from_mapping(item)
            for item in _json_lines_decode(
                entries[f"{BUNDLE_ARCHIVE_ROOT}/blob-manifest.jsonl"],
                "blob manifest",
                self.limits.max_blobs,
            )
        )
        self._validate_snapshot_members(
            project_uuid=manifest.project_uuid,
            entities=entities,
            relations=relations,
            lineage=lineage,
            blobs=blobs,
        )
        blob_bytes: dict[str, bytes] = {}
        for blob in blobs:
            digest = blob.digest.removeprefix("sha256:")
            name = f"{BUNDLE_ARCHIVE_ROOT}/blobs/sha256/{digest[:2]}/{digest}"
            content = entries.get(name)
            if content is None:
                raise ValueError(f"P2P_MANAGED_BLOB_MISSING: {blob.digest}")
            if len(content) != blob.size or hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f"P2P_MANAGED_BLOB_DIGEST_MISMATCH: {blob.digest}")
            blob_bytes[blob.digest] = content
        encoded_blob_names = {
            name for name in entries if name.startswith(f"{BUNDLE_ARCHIVE_ROOT}/blobs/sha256/")
        }
        expected_blob_names = {
            f"{BUNDLE_ARCHIVE_ROOT}/blobs/sha256/{item.digest[7:9]}/{item.digest[7:]}"
            for item in blobs
        }
        if encoded_blob_names != expected_blob_names:
            raise ValueError("P2P_MANAGED_BLOB_EXTRA: archive contains an unmanifested blob")
        blob_manifest_digest = semantic_sha256([item.to_dict() for item in blobs])
        if blob_manifest_digest != manifest.blob_manifest_digest:
            raise ValueError("P2P_BUNDLE_BLOB_MANIFEST_DIGEST_MISMATCH: manifest changed")
        state_payload = {
            "contract": CANONICAL_MEMORY_CONTRACT,
            "project_uuid": manifest.project_uuid,
            "memory_schema": manifest.memory_schema,
            "domain_contract": manifest.domain_contract,
            "entities": [item.to_dict() for item in entities],
            "relations": [item.to_dict() for item in relations],
            "lineage": list(lineage),
            "blobs": [item.to_dict() for item in blobs],
        }
        digest = semantic_sha256(state_payload)
        if digest != manifest.semantic_state_digest:
            raise ValueError("P2P_BUNDLE_SEMANTIC_DIGEST_MISMATCH: canonical state changed")
        if (
            manifest.source_revision.get("kind") == "local"
            and manifest.source_revision.get("value") != digest
        ):
            raise ValueError("P2P_BUNDLE_SOURCE_REVISION_INVALID: source revision is not canonical")
        counts = (len(entities), len(relations), len(lineage), len(blobs))
        expected_counts = (
            manifest.entity_count,
            manifest.relation_count,
            manifest.lineage_count,
            manifest.blob_count,
        )
        if counts != expected_counts or sum(item.size for item in blobs) != manifest.blob_bytes:
            raise ValueError("P2P_BUNDLE_COUNT_MISMATCH: manifest counts changed")
        snapshot = CanonicalMemorySnapshot(
            project_uuid=manifest.project_uuid,
            entities=entities,
            relations=relations,
            lineage=lineage,
            blobs=blobs,
            semantic_state_digest=digest,
            blob_manifest_digest=blob_manifest_digest,
            source_revision=manifest.source_revision,
            memory_schema=manifest.memory_schema,
            domain_contract=manifest.domain_contract,
        )
        return DecodedBundle(
            manifest=manifest,
            snapshot=snapshot,
            blob_bytes=blob_bytes,
            archive_sha256=hashlib.sha256(raw).hexdigest(),
        )

    def encode_physical_backup(
        self,
        *,
        store: FilesystemCanonicalMemoryStore,
        files: Mapping[str, bytes],
        directories: Iterable[str],
        semantic_state_digest: str,
        source_revision: str,
    ) -> bytes:
        identity = store.project_identity()
        file_manifest = [
            {
                "path": path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
            for path, content in sorted(files.items())
        ]
        manifest = {
            "backup_schema": PHYSICAL_BACKUP_SCHEMA,
            "project_uuid": identity.project_uuid.value,
            "source_revision": source_revision,
            "semantic_state_digest": semantic_state_digest,
            "file_count": len(file_manifest),
            "files": file_manifest,
            "directories": sorted(directories),
            "excluded": [
                ".p2p/.internal/workspace-transactions/**",
                ".p2p/backups/**",
            ],
        }
        entries = {_BACKUP_MANIFEST_ENTRY: canonical_json_bytes(manifest)}
        for relative, content in sorted(files.items()):
            entries[f"{BACKUP_ARCHIVE_ROOT}/files/{relative}"] = content
        self._validate_encoded_entries(entries)
        archive = _deterministic_zip(entries)
        if len(archive) > self.limits.max_archive_bytes:
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: encoded backup is too large")
        return archive

    def decode_physical_backup(self, archive: Path | bytes) -> DecodedPhysicalBackup:
        raw = _archive_bytes(archive, self.limits.max_archive_bytes)
        entries = self._read_archive(raw)
        if _BACKUP_MANIFEST_ENTRY not in entries:
            raise ValueError("P2P_BACKUP_MANIFEST_MISSING: physical backup has no manifest")
        manifest = _json_mapping(entries[_BACKUP_MANIFEST_ENTRY], "physical backup manifest")
        expected_fields = {
            "backup_schema",
            "project_uuid",
            "source_revision",
            "semantic_state_digest",
            "file_count",
            "files",
            "directories",
            "excluded",
        }
        if (
            set(manifest) != expected_fields
            or manifest.get("backup_schema") != PHYSICAL_BACKUP_SCHEMA
        ):
            raise ValueError("P2P_BACKUP_MANIFEST_INVALID: unsupported physical backup contract")
        ProjectUuid(str(manifest.get("project_uuid") or ""))
        _require_sha256(manifest.get("source_revision"), "backup source revision")
        _require_sha256(manifest.get("semantic_state_digest"), "backup semantic digest")
        raw_files = manifest.get("files")
        if not isinstance(raw_files, list) or len(raw_files) > self.limits.max_entries:
            raise ValueError("P2P_BACKUP_MANIFEST_INVALID: file manifest is invalid")
        if manifest.get("file_count") != len(raw_files):
            raise ValueError("P2P_BACKUP_COUNT_MISMATCH: manifest file count changed")
        files: dict[str, bytes] = {}
        raw_directories = manifest.get("directories")
        if not isinstance(raw_directories, list):
            raise ValueError("P2P_BACKUP_MANIFEST_INVALID: directories must be a sequence")
        directories = [_safe_project_path(str(item)) for item in raw_directories]
        if directories != sorted(set(directories)):
            raise ValueError("P2P_BACKUP_MANIFEST_INVALID: directories must be unique and sorted")
        for raw_file in raw_files:
            item = _mapping(raw_file, "backup file")
            if set(item) != {"path", "sha256", "size"}:
                raise ValueError("P2P_BACKUP_MANIFEST_INVALID: backup file fields are not exact")
            path = _safe_project_path(str(item.get("path") or ""))
            entry = f"{BACKUP_ARCHIVE_ROOT}/files/{path}"
            content = entries.get(entry)
            if content is None:
                raise ValueError(f"P2P_BACKUP_ENTRY_MISSING: {path}")
            digest = _require_sha256(item.get("sha256"), "backup file digest")
            if item.get("size") != len(content) or hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f"P2P_BACKUP_CHECKSUM_MISMATCH: {path}")
            if path in files:
                raise ValueError(f"P2P_BACKUP_ENTRY_DUPLICATE: {path}")
            files[path] = content
        expected_entries = {_BACKUP_MANIFEST_ENTRY} | {
            f"{BACKUP_ARCHIVE_ROOT}/files/{path}" for path in files
        }
        if set(entries) != expected_entries:
            raise ValueError("P2P_BACKUP_ENTRY_UNEXPECTED: archive contains an unmanifested entry")
        return DecodedPhysicalBackup(
            manifest=manifest,
            files=files,
            archive_sha256=hashlib.sha256(raw).hexdigest(),
        )

    def _read_archive(self, raw: bytes) -> dict[str, bytes]:
        try:
            archive = zipfile.ZipFile(BytesIO(raw), "r")
        except (zipfile.BadZipFile, OSError) as exc:
            raise ValueError(f"P2P_BUNDLE_ARCHIVE_INVALID: {exc}") from exc
        with archive:
            infos = archive.infolist()
            if len(infos) > self.limits.max_entries:
                raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: archive has too many entries")
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                raise ValueError("P2P_BUNDLE_DUPLICATE_ENTRY: archive names must be unique")
            total = 0
            entries: dict[str, bytes] = {}
            for info in infos:
                name = _safe_archive_name(info.filename)
                if info.is_dir():
                    raise ValueError("P2P_BUNDLE_ENTRY_INVALID: directory entries are forbidden")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise ValueError("P2P_BUNDLE_ENTRY_INVALID: symlink entries are forbidden")
                if info.file_size > self.limits.max_entry_bytes:
                    raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: archive entry is too large")
                total += info.file_size
                if total > self.limits.max_total_uncompressed_bytes:
                    raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: archive expands beyond its limit")
                if (
                    info.file_size > 0
                    and info.compress_size > 0
                    and info.file_size / info.compress_size > self.limits.max_compression_ratio
                ):
                    raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: suspicious compression ratio")
                content = archive.read(info)
                if len(content) != info.file_size:
                    raise ValueError("P2P_BUNDLE_ENTRY_INVALID: decoded size mismatch")
                entries[name] = content
            return entries

    def _verify_checksums(self, entries: Mapping[str, bytes]) -> None:
        checksum_name = f"{BUNDLE_ARCHIVE_ROOT}/checksums.json"
        payload = _json_mapping(entries[checksum_name], "checksums")
        if set(payload) != {"contract", "entries"} or payload.get("contract") != (
            "p2p-project-bundle-checksums/v1"
        ):
            raise ValueError("P2P_BUNDLE_CHECKSUMS_INVALID: unsupported checksum contract")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, Mapping):
            raise ValueError("P2P_BUNDLE_CHECKSUMS_INVALID: entries must be a mapping")
        expected_names = set(entries) - {checksum_name}
        if set(raw_entries) != expected_names:
            raise ValueError("P2P_BUNDLE_CHECKSUMS_INVALID: checksum coverage is not exact")
        for name in sorted(expected_names):
            item = _mapping(raw_entries[name], "checksum entry")
            if set(item) != {"sha256", "size"}:
                raise ValueError("P2P_BUNDLE_CHECKSUMS_INVALID: checksum fields are not exact")
            content = entries[name]
            if (
                item.get("size") != len(content)
                or item.get("sha256") != hashlib.sha256(content).hexdigest()
            ):
                raise ValueError(f"P2P_BUNDLE_CHECKSUM_MISMATCH: {name}")

    def _validate_snapshot_limits(self, snapshot: CanonicalMemorySnapshot) -> None:
        if len(snapshot.entities) > self.limits.max_entities:
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: too many canonical entities")
        if len(snapshot.relations) > self.limits.max_relations:
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: too many canonical relations")
        if len(snapshot.blobs) > self.limits.max_blobs:
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: too many managed blobs")
        if any(item.size > self.limits.max_entry_bytes for item in snapshot.blobs):
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: managed blob is too large")
        if sum(item.size for item in snapshot.blobs) > self.limits.max_total_uncompressed_bytes:
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: managed blobs exceed total size limit")

    def _validate_encoded_entries(self, entries: Mapping[str, bytes]) -> None:
        if len(entries) > self.limits.max_entries:
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: too many archive entries")
        total = 0
        for content in entries.values():
            if len(content) > self.limits.max_entry_bytes:
                raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: archive entry is too large")
            total += len(content)
            if total > self.limits.max_total_uncompressed_bytes:
                raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: archive expands beyond its limit")

    def _validate_snapshot_members(
        self,
        *,
        project_uuid: str,
        entities: Iterable[CanonicalEntity],
        relations: Iterable[CanonicalRelation],
        lineage: Iterable[Mapping[str, object]],
        blobs: Iterable[ManagedBlob],
    ) -> None:
        ProjectUuid(project_uuid)
        entity_list = list(entities)
        entity_ids = [item.technical_id for item in entity_list]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("P2P_CANONICAL_ENTITY_DUPLICATE: technical IDs must be unique")
        identity_records = [item for item in entity_list if item.technical_id == "project:identity"]
        manifest_records = [item for item in entity_list if item.technical_id == "project:manifest"]
        if len(identity_records) != 1 or len(manifest_records) != 1:
            raise ValueError("P2P_BUNDLE_IDENTITY_MISSING: identity and manifest are required")
        identity_uuid = _project_uuid_from_entity(identity_records[0], "project_identity")
        manifest_uuid = _project_uuid_from_entity(manifest_records[0], "project")
        if project_uuid != identity_uuid or project_uuid != manifest_uuid:
            raise ValueError("P2P_BUNDLE_IDENTITY_MISMATCH: manifest and records disagree")
        for entity in entity_list:
            _validate_canonical_entity(entity)
        relation_list = list(relations)
        relation_ids = [item.relation_id for item in relation_list]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("P2P_CANONICAL_RELATION_DUPLICATE: relation IDs must be unique")
        known = set(entity_ids)
        for relation in relation_list:
            if relation.source_entity not in known or relation.target_entity not in known:
                raise ValueError(
                    f"P2P_CANONICAL_RELATION_BROKEN: {relation.relation_id} has an unknown endpoint"
                )
        lineage_list = list(lineage)
        lineage_keys: set[tuple[str, str, str]] = set()
        for raw in lineage_list:
            if set(raw) != {
                "relation",
                "source_project_uuid",
                "source_revision",
                "visibility",
            }:
                raise ValueError("P2P_PROJECT_LINEAGE_INVALID: lineage fields are not exact")
            source_uuid = ProjectUuid(str(raw.get("source_project_uuid") or ""))
            if source_uuid.value == project_uuid:
                raise ValueError("P2P_PROJECT_LINEAGE_CYCLE: lineage cannot reference the project")
            revision = _mapping(raw.get("source_revision"), "lineage source revision")
            if set(revision) != {"namespace", "sha256"} or revision.get("namespace") != (
                "source_memory"
            ):
                raise ValueError("P2P_PROJECT_LINEAGE_INVALID: source revision is invalid")
            digest = _require_sha256(revision.get("sha256"), "lineage source revision")
            key = (str(raw.get("relation")), source_uuid.value, digest)
            if key in lineage_keys:
                raise ValueError("P2P_PROJECT_LINEAGE_INVALID: duplicate lineage entry")
            lineage_keys.add(key)
        expected_lineage = _identity_lineage(identity_records[0])
        if lineage_list != expected_lineage:
            raise ValueError(
                "P2P_PROJECT_LINEAGE_INVALID: identity entity and lineage stream disagree"
            )
        blob_list = list(blobs)
        blob_digests = [item.digest for item in blob_list]
        if len(blob_digests) != len(set(blob_digests)):
            raise ValueError("P2P_MANAGED_BLOB_DUPLICATE: blob digests must be unique")
        references: set[str] = set()
        for entity in entity_list:
            references.update(managed_blob_references(entity.payload))
        if references != set(blob_digests):
            missing = sorted(references - set(blob_digests))
            extra = sorted(set(blob_digests) - references)
            detail = (missing or extra)[0] if missing or extra else "unknown"
            code = "P2P_MANAGED_BLOB_MISSING" if missing else "P2P_MANAGED_BLOB_EXTRA"
            raise ValueError(f"{code}: {detail}")


class CanonicalMemoryService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path | None = None,
        store: FilesystemCanonicalMemoryStore | None = None,
        codec: CanonicalBundleCodec | None = None,
        failure_injector=None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = (p2p_dir or self.root / ".p2p").resolve()
        self.store = store or FilesystemCanonicalMemoryStore(root=self.root, p2p_dir=self.p2p_dir)
        self.codec = codec or CanonicalBundleCodec()
        self.permissions = PermissionsService(root=self.root, p2p_dir=self.p2p_dir)
        self.lock_service = WorkspaceTransactionLockService(root=self.root, p2p_dir=self.p2p_dir)
        self.failure_injector = failure_injector

    def inspect(self) -> CanonicalMemoryInventory:
        return self.store.inventory()

    def snapshot(self) -> CanonicalMemorySnapshot:
        return self.codec.snapshot(self.store)

    def verify_current(self) -> BundleValidationResult:
        try:
            snapshot = self.snapshot()
        except ValueError as exc:
            return BundleValidationResult(
                status="invalid", archive_kind="current", issues=(str(exc),)
            )
        return BundleValidationResult(
            status="valid",
            archive_kind="current",
            project_uuid=snapshot.project_uuid,
            semantic_state_digest=snapshot.semantic_state_digest,
            entity_count=len(snapshot.entities),
            relation_count=len(snapshot.relations),
            lineage_count=len(snapshot.lineage),
            blob_count=len(snapshot.blobs),
        )

    def bundle_metadata(self) -> BundleExportResult:
        snapshot = self.snapshot()
        archive, manifest = self.codec.encode_bundle(self.store, snapshot)
        return BundleExportResult(
            status="ready",
            output="",
            manifest=manifest,
            archive_sha256=hashlib.sha256(archive).hexdigest(),
            archive_size=len(archive),
        )

    def export_bundle(self, output: Path) -> BundleExportResult:
        target = self._safe_output(output)
        if target.exists():
            raise ValueError("P2P_BUNDLE_OUTPUT_EXISTS: refusing to overwrite bundle output")
        snapshot = self.snapshot()
        archive, manifest = self.codec.encode_bundle(self.store, snapshot)
        write_bytes_atomic(target, archive, mode=0o600)
        return BundleExportResult(
            status="exported",
            output=str(target),
            manifest=manifest,
            archive_sha256=hashlib.sha256(archive).hexdigest(),
            archive_size=len(archive),
        )

    def verify_archive(self, source: Path) -> BundleValidationResult:
        path = source.resolve()
        try:
            kind = _archive_kind(path, self.codec.limits)
            if kind == "bundle":
                decoded = self.codec.decode_bundle(path)
                snapshot = decoded.snapshot
                return BundleValidationResult(
                    status="valid",
                    archive_kind="bundle",
                    project_uuid=snapshot.project_uuid,
                    semantic_state_digest=snapshot.semantic_state_digest,
                    archive_sha256=decoded.archive_sha256,
                    entity_count=len(snapshot.entities),
                    relation_count=len(snapshot.relations),
                    lineage_count=len(snapshot.lineage),
                    blob_count=len(snapshot.blobs),
                )
            decoded_backup = self.codec.decode_physical_backup(path)
            return BundleValidationResult(
                status="valid",
                archive_kind="physical_backup",
                project_uuid=decoded_backup.project_uuid,
                semantic_state_digest=decoded_backup.semantic_state_digest,
                archive_sha256=decoded_backup.archive_sha256,
                entity_count=_non_negative_int(
                    decoded_backup.manifest.get("file_count"), "backup file count"
                ),
            )
        except (OSError, ValueError) as exc:
            return BundleValidationResult(
                status="invalid",
                archive_kind="unknown",
                issues=(str(exc),),
            )

    def backup(self, output: Path, *, coordinated: bool = True) -> PhysicalBackupResult:
        target = self._safe_output(output)
        if target.exists():
            raise ValueError("P2P_BACKUP_OUTPUT_EXISTS: refusing to overwrite backup output")
        transaction_id = (
            f"memory-backup-{os.getpid()}-{hashlib.sha256(str(target).encode()).hexdigest()[:12]}"
        )
        acquired = False
        try:
            if coordinated:
                self.lock_service.acquire(transaction_id, owner="backup")
                acquired = True
            elif self.lock_service.status().state != "absent":
                raise ValueError(
                    "P2P_BACKUP_STORE_ACTIVE: closed-store backup requires no active lock"
                )
            return self._backup_locked(target, coordinated=coordinated)
        finally:
            if acquired:
                self.lock_service.release(transaction_id)

    def restore_preview(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
    ) -> MemoryRestorePreview:
        validate_idempotency_key(operation_key)
        self.permissions.require_role(actor, "owner", operation="project_memory_restore")
        current = self.snapshot()
        kind = _archive_kind(source, self.codec.limits)
        if kind == "bundle":
            decoded = self.codec.decode_bundle(source)
            project_uuid = decoded.snapshot.project_uuid
            target_digest = decoded.snapshot.semantic_state_digest
            archive_sha256 = decoded.archive_sha256
            changed = _changed_entity_count(current, decoded.snapshot)
        else:
            decoded_backup = self.codec.decode_physical_backup(source)
            project_uuid = decoded_backup.project_uuid
            target_digest = decoded_backup.semantic_state_digest
            archive_sha256 = decoded_backup.archive_sha256
            changed = _non_negative_int(
                decoded_backup.manifest.get("file_count"), "backup file count"
            )
        if project_uuid != current.project_uuid:
            raise ValueError(
                "P2P_BUNDLE_IDENTITY_MISMATCH: restore preserves project_uuid; use a governed clone/derive workflow"
            )
        preview_token = semantic_sha256(
            {
                "contract": "p2p-memory-restore-preview/v1",
                "operation_key": operation_key,
                "actor": actor,
                "archive_kind": kind,
                "archive_sha256": archive_sha256,
                "project_uuid": project_uuid,
                "current_semantic_digest": current.semantic_state_digest,
                "target_semantic_digest": target_digest,
            }
        )
        return MemoryRestorePreview(
            status="ready",
            operation_key=operation_key,
            archive_kind=kind,
            archive_sha256=archive_sha256,
            project_uuid=project_uuid,
            current_semantic_digest=current.semantic_state_digest,
            target_semantic_digest=target_digest,
            preview_token=preview_token,
            changed_entity_count=changed,
        )

    def restore_apply(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
        preview_token: str,
        confirm: bool,
    ) -> MemoryRestoreResult:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: restore apply requires --confirm")
        validate_idempotency_key(operation_key)
        self.permissions.require_role(actor, "owner", operation="project_memory_restore")
        replay = self._restore_replay(operation_key, actor=actor)
        if replay is not None:
            source_bytes = _archive_bytes(source, self.codec.limits.max_archive_bytes)
            if replay.archive_sha256 != hashlib.sha256(source_bytes).hexdigest():
                raise ValueError(
                    "P2P_IDEMPOTENCY_CONFLICT: restore key was used for another archive"
                )
            return replay
        preview = self.restore_preview(
            source=source,
            operation_key=operation_key,
            actor=actor,
        )
        if preview.preview_token != preview_token:
            raise ValueError("P2P_STALE_PREVIEW: restore preview no longer matches")
        transaction_id = f"memory-restore-{idempotency_key_sha256(operation_key)[:24]}"
        self.lock_service.acquire(transaction_id, owner=actor)
        marker = self.root / ".p2p-restore-recovery.yml"
        staging_root = self.root / ".p2p-restore-staging" / preview.preview_token[:24]
        recovery_root = self.root / ".p2p-recovery" / preview.preview_token[:24]
        recovery_p2p = recovery_root / ".p2p"
        activated = False
        moved_active = False
        try:
            if marker.exists() or staging_root.exists() or recovery_root.exists():
                raise ValueError(
                    "P2P_RESTORE_RECOVERY_REQUIRED: restore staging or recovery state already exists"
                )
            backup_path = (
                self.root / ".p2p-backups" / (f"pre-restore-{preview.preview_token[:24]}.p2pbackup")
            )
            if not backup_path.exists():
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                self._backup_locked(backup_path, coordinated=True)
            else:
                verification = self.verify_archive(backup_path)
                if not verification.valid:
                    raise ValueError(
                        "P2P_BACKUP_INVALID: existing pre-restore backup does not verify"
                    )
            staging_p2p = staging_root / ".p2p"
            self._stage_restore(source, preview.archive_kind, staging_p2p)
            target_snapshot = self._validate_staging(
                staging_root,
                expected_project_uuid=preview.project_uuid,
                expected_semantic_digest=preview.target_semantic_digest,
            )
            result = MemoryRestoreResult(
                status="applied",
                operation_key=operation_key,
                archive_kind=preview.archive_kind,
                project_uuid=preview.project_uuid,
                semantic_state_digest=target_snapshot.semantic_state_digest,
                archive_sha256=preview.archive_sha256,
                preview_token=preview.preview_token,
                backup_path=str(backup_path),
                recovery_path=str(recovery_p2p),
                changed_entity_count=preview.changed_entity_count,
                message="Restore activated after staged validation; previous state remains recoverable.",
            )
            self._write_restore_receipt(
                staging_p2p,
                result,
                preview.archive_sha256,
                actor=actor,
            )
            recovery_root.mkdir(parents=True, exist_ok=False)
            write_yaml_atomic(
                marker,
                {
                    "restore_recovery": {
                        "contract": "p2p-memory-restore-recovery/v1",
                        "state": "staged",
                        "staging_path": str(staging_p2p),
                        "recovery_path": str(recovery_p2p),
                        "preview_token": preview.preview_token,
                        "backup_path": str(backup_path),
                    }
                },
            )
            self._inject("before_active_move")
            self.p2p_dir.replace(recovery_p2p)
            moved_active = True
            sync_directory(self.root)
            self._inject("after_active_move")
            staging_p2p.replace(self.p2p_dir)
            activated = True
            sync_directory(self.root)
            self._inject("after_activation")
            old_lock = recovery_p2p / ".internal" / "workspace-transactions" / "apply.lock"
            old_lock.unlink(missing_ok=True)
            marker.unlink(missing_ok=True)
            sync_directory(self.root)
            shutil.rmtree(staging_root, ignore_errors=True)
            return result
        except Exception:
            if moved_active:
                try:
                    failed = staging_root / ".failed-activation"
                    if activated and self.p2p_dir.exists():
                        failed.parent.mkdir(parents=True, exist_ok=True)
                        self.p2p_dir.replace(failed)
                    if not self.p2p_dir.exists() and recovery_p2p.exists():
                        recovery_p2p.replace(self.p2p_dir)
                    old_lock = self.p2p_dir / ".internal" / "workspace-transactions" / "apply.lock"
                    old_lock.unlink(missing_ok=True)
                    sync_directory(self.root)
                except Exception:
                    # Keep the marker and both trees for explicit owner recovery.
                    raise
            marker.unlink(missing_ok=True)
            shutil.rmtree(staging_root, ignore_errors=True)
            shutil.rmtree(recovery_root, ignore_errors=True)
            raise
        finally:
            self.lock_service.release(transaction_id)

    def recovery_status(self) -> MemoryRecoveryStatus:
        marker = self.root / ".p2p-restore-recovery.yml"
        if not marker.exists():
            return MemoryRecoveryStatus(
                state="clean", message="No interrupted canonical-memory restore is recorded."
            )
        try:
            from p2p_engine.foundation.yaml_loaders import load_yaml

            raw = load_yaml(marker.read_bytes())
            payload = _mapping(
                _mapping(raw, "restore recovery").get("restore_recovery"), "restore recovery"
            )
            if payload.get("contract") != "p2p-memory-restore-recovery/v1":
                raise ValueError("unsupported recovery marker")
            staging = _safe_recovery_path(self.root, str(payload.get("staging_path") or ""))
            recovery = _safe_recovery_path(self.root, str(payload.get("recovery_path") or ""))
            return MemoryRecoveryStatus(
                state="recovery_required",
                marker=str(marker),
                staging_path=str(staging),
                recovery_path=str(recovery),
                message="An interrupted restore requires owner inspection before another mutation.",
            )
        except (OSError, ValueError) as exc:
            return MemoryRecoveryStatus(
                state="invalid_marker",
                marker=str(marker),
                message=f"Restore recovery marker is invalid: {exc}",
            )

    def _backup_locked(self, target: Path, *, coordinated: bool) -> PhysicalBackupResult:
        inventory = self.store.inventory()
        files = self.store.physical_backup_files(inventory)
        snapshot = self.snapshot()
        source_revision = self.store.identity_store.source_revision().sha256
        archive = self.codec.encode_physical_backup(
            store=self.store,
            files=files,
            directories=self.store.physical_backup_directories(),
            semantic_state_digest=snapshot.semantic_state_digest,
            source_revision=source_revision,
        )
        write_bytes_atomic(target, archive, mode=0o600)
        return PhysicalBackupResult(
            status="created",
            output=str(target),
            project_uuid=snapshot.project_uuid,
            source_revision=source_revision,
            archive_sha256=hashlib.sha256(archive).hexdigest(),
            archive_size=len(archive),
            file_count=len(files),
            coordinated=coordinated,
        )

    def _stage_restore(self, source: Path, kind: str, staging_p2p: Path) -> None:
        staging_p2p.parent.mkdir(parents=True, exist_ok=False)
        if kind == "physical_backup":
            decoded = self.codec.decode_physical_backup(source)
            staging_p2p.mkdir(mode=0o700)
            raw_directories = decoded.manifest.get("directories")
            assert isinstance(raw_directories, list)
            for relative in raw_directories:
                target = _safe_staged_target(staging_p2p, str(relative))
                target.mkdir(parents=True, exist_ok=True, mode=0o700)
            for relative, content in decoded.files.items():
                target = _safe_staged_target(staging_p2p, relative)
                write_bytes_atomic(target, content, mode=0o600)
            return
        shutil.copytree(
            self.p2p_dir,
            staging_p2p,
            ignore=lambda _directory, names: {
                name for name in names if name == "workspace-transactions" or name == "backups"
            },
        )
        staged_store = FilesystemCanonicalMemoryStore(root=staging_p2p.parent, p2p_dir=staging_p2p)
        staged_inventory = staged_store.inventory()
        for artifact in staged_inventory.artifacts:
            if artifact.portable or artifact.classification == "derived_projection":
                target = staging_p2p.parent / artifact.locator
                target.unlink(missing_ok=True)
        decoded_bundle = self.codec.decode_bundle(source)
        documents = staged_store.activation_documents(decoded_bundle.snapshot.entities)
        documents.update(
            staged_store.blob_documents(decoded_bundle.snapshot.blobs, decoded_bundle.blob_bytes)
        )
        for relative, content in documents.items():
            target = _safe_staged_target(staging_p2p, relative)
            write_bytes_atomic(target, content, mode=0o600)

    def _validate_staging(
        self,
        staging_root: Path,
        *,
        expected_project_uuid: str,
        expected_semantic_digest: str,
    ) -> CanonicalMemorySnapshot:
        staging_p2p = staging_root / ".p2p"
        staged_store = FilesystemCanonicalMemoryStore(root=staging_root, p2p_dir=staging_p2p)
        snapshot = self.codec.snapshot(staged_store)
        if snapshot.project_uuid != expected_project_uuid:
            raise ValueError("P2P_BUNDLE_IDENTITY_MISMATCH: staged identity changed")
        if snapshot.semantic_state_digest != expected_semantic_digest:
            raise ValueError("P2P_BUNDLE_SEMANTIC_DIGEST_MISMATCH: staging changed")
        self._copy_validation_context(staging_root)
        from p2p_engine.storage.filesystem import P2PWorkspace

        validation = P2PWorkspace(staging_root).validate()
        if not validation.ok:
            failures = [
                f"{item.code}:{item.path}"
                for item in validation.findings
                if item.severity == "error"
            ]
            raise ValueError("P2P_BUNDLE_DOMAIN_VALIDATION_FAILED: " + ", ".join(failures[:20]))
        return snapshot

    def _copy_validation_context(self, staging_root: Path) -> None:
        """Mirror generated files only for candidate validation, never activation."""
        from p2p_engine.foundation.yaml_loaders import load_yaml

        registry = staging_root / ".p2p" / "agent-integrations.yml"
        paths: set[str] = {"P2P-SETUP.md"}
        if registry.is_file() and not registry.is_symlink():
            raw = load_yaml(registry.read_bytes())
            root = _mapping(raw, "agent integrations")
            adapters = root.get("adapters")
            if isinstance(adapters, Mapping):
                for adapter in adapters.values():
                    if not isinstance(adapter, Mapping):
                        continue
                    files = adapter.get("files")
                    if not isinstance(files, list):
                        continue
                    for item in files:
                        if isinstance(item, Mapping) and isinstance(item.get("path"), str):
                            paths.add(str(item["path"]))
        for relative in sorted(paths):
            pure = PurePosixPath(relative.replace("\\", "/"))
            if pure.as_posix().startswith(".p2p/"):
                continue
            if pure.is_absolute() or ".." in pure.parts or not pure.parts:
                raise ValueError("P2P_BUNDLE_DOMAIN_VALIDATION_FAILED: unsafe integration path")
            source = self.root / pure.as_posix()
            if not source.exists():
                continue
            if source.is_symlink() or not source.is_file():
                raise ValueError("P2P_BUNDLE_DOMAIN_VALIDATION_FAILED: integration path is unsafe")
            target = staging_root / pure.as_posix()
            write_bytes_atomic(target, source.read_bytes(), mode=0o600)

    def _restore_replay(self, operation_key: str, *, actor: str) -> MemoryRestoreResult | None:
        path = self._restore_receipt_path(self.p2p_dir, operation_key)
        if not path.exists():
            return None
        try:
            payload = _json_mapping(path.read_bytes(), "restore receipt")
            if set(payload) != {"contract", "actor", "archive_sha256", "result"}:
                raise ValueError("restore receipt fields are not exact")
            if payload.get("contract") != "p2p-memory-restore-receipt/v1":
                raise ValueError("restore receipt contract is unsupported")
            if payload.get("actor") != actor:
                raise ValueError("restore receipt actor mismatch")
            result = _mapping(payload.get("result"), "restore receipt result")
            restored = MemoryRestoreResult(
                status="applied",
                operation_key=str(result.get("operation_key") or ""),
                archive_kind=str(result.get("archive_kind") or ""),
                project_uuid=str(result.get("project_uuid") or ""),
                semantic_state_digest=_require_sha256(
                    result.get("semantic_state_digest"), "restore receipt semantic digest"
                ),
                archive_sha256=_require_sha256(
                    result.get("archive_sha256"), "restore receipt archive digest"
                ),
                preview_token=_require_sha256(
                    result.get("preview_token"), "restore receipt preview token"
                ),
                backup_path=str(result.get("backup_path") or ""),
                recovery_path=str(result.get("recovery_path") or ""),
                changed_entity_count=_non_negative_int(
                    result.get("changed_entity_count"), "restore changed entity count"
                ),
                replayed=True,
                message="Restore result replayed from its idempotent receipt.",
            )
            if restored.operation_key != operation_key:
                raise ValueError("restore receipt operation key mismatch")
            current = self.snapshot()
            if current.semantic_state_digest != restored.semantic_state_digest:
                raise ValueError("restore receipt postcondition drift")
            return restored
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(f"P2P_RESTORE_RECEIPT_CORRUPT: {exc}") from exc

    def _write_restore_receipt(
        self,
        staging_p2p: Path,
        result: MemoryRestoreResult,
        archive_sha256: str,
        *,
        actor: str,
    ) -> None:
        path = self._restore_receipt_path(staging_p2p, result.operation_key)
        payload = {
            "contract": "p2p-memory-restore-receipt/v1",
            "actor": actor,
            "archive_sha256": archive_sha256,
            "result": result.to_dict(),
        }
        write_bytes_atomic(path, canonical_json_bytes(payload), mode=0o600)

    @staticmethod
    def _restore_receipt_path(p2p_dir: Path, operation_key: str) -> Path:
        return (
            p2p_dir
            / ".internal"
            / "bundle-restores"
            / f"{idempotency_key_sha256(operation_key)}.json"
        )

    def _safe_output(self, output: Path) -> Path:
        target = output.expanduser().resolve(strict=False)
        if target.is_relative_to(self.p2p_dir):
            raise ValueError("P2P_ARCHIVE_OUTPUT_INVALID: archives must be outside .p2p")
        if target.is_symlink() or any(
            parent.is_symlink() for parent in target.parents if parent.exists()
        ):
            raise ValueError("P2P_ARCHIVE_OUTPUT_INVALID: output path contains a symlink")
        return target

    def _inject(self, stage: str) -> None:
        if self.failure_injector is not None:
            self.failure_injector(stage)


def _deterministic_zip(entries: Mapping[str, bytes]) -> bytes:
    stream = BytesIO()
    with zipfile.ZipFile(
        stream,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return stream.getvalue()


def _archive_bytes(archive: Path | bytes, maximum: int) -> bytes:
    raw = archive if isinstance(archive, bytes) else archive.read_bytes()
    if len(raw) > maximum:
        raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: archive exceeds its compressed-size limit")
    return raw


def _json_lines(values: Iterable[object]) -> bytes:
    return b"".join(canonical_json_bytes(value) for value in values)


def _json_lines_decode(content: bytes, label: str, maximum: int) -> list[object]:
    values: list[object] = []
    for number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"P2P_BUNDLE_RECORD_INVALID: blank {label} line {number}")
        if len(values) >= maximum:
            raise ValueError(f"P2P_BUNDLE_LIMIT_EXCEEDED: too many {label} records")
        try:
            values.append(json.loads(line.decode("utf-8"), object_pairs_hook=_unique_json_object))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"P2P_BUNDLE_RECORD_INVALID: {label} line {number}: {exc}") from exc
    return values


def _json_mapping(content: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"P2P_BUNDLE_RECORD_INVALID: {label}: {exc}") from exc
    return _mapping(value, label)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"P2P_BUNDLE_RECORD_INVALID: {label} must be a mapping")
    return dict(value)


def _manifest_from_mapping(value: Mapping[str, object]) -> ProjectBundleManifest:
    expected = {
        "bundle_schema",
        "project_uuid",
        "source_revision",
        "memory_schema",
        "domain_contract",
        "semantic_state_digest",
        "blob_manifest_digest",
        "entity_count",
        "relation_count",
        "lineage_count",
        "blob_count",
        "blob_bytes",
        "capabilities",
    }
    if set(value) != expected or value.get("bundle_schema") != PROJECT_BUNDLE_SCHEMA:
        raise ValueError("P2P_BUNDLE_SCHEMA_UNSUPPORTED: manifest contract is unsupported")
    if value.get("memory_schema") != MEMORY_SCHEMA_VERSION or value.get("domain_contract") != (
        DOMAIN_CONTRACT
    ):
        raise ValueError("P2P_BUNDLE_SCHEMA_UNSUPPORTED: logical schema is unsupported")
    project_uuid = ProjectUuid(str(value.get("project_uuid") or "")).value
    raw_source_revision = _mapping(value.get("source_revision"), "source revision")
    if set(raw_source_revision) != {"kind", "value"} or raw_source_revision.get("kind") not in {
        "local",
        "wavekit",
    }:
        raise ValueError("P2P_BUNDLE_SOURCE_REVISION_INVALID: source revision is invalid")
    source_revision = {
        "kind": str(raw_source_revision["kind"]),
        "value": _require_sha256(raw_source_revision.get("value"), "source revision"),
    }
    counts: list[int] = []
    for field in ("entity_count", "relation_count", "lineage_count", "blob_count", "blob_bytes"):
        raw = value.get(field)
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise ValueError(f"P2P_BUNDLE_MANIFEST_INVALID: {field} must be non-negative")
        counts.append(raw)
    capabilities = value.get("capabilities")
    if capabilities != [
        "complete-managed-blobs",
        "deterministic-jsonl",
        "staged-activation",
    ]:
        raise ValueError("P2P_BUNDLE_CAPABILITY_UNSUPPORTED: capabilities are unsupported")
    return ProjectBundleManifest(
        project_uuid=project_uuid,
        source_revision=source_revision,
        semantic_state_digest=_require_sha256(
            value.get("semantic_state_digest"), "semantic state digest"
        ),
        blob_manifest_digest=_require_sha256(
            value.get("blob_manifest_digest"), "blob manifest digest"
        ),
        entity_count=counts[0],
        relation_count=counts[1],
        lineage_count=counts[2],
        blob_count=counts[3],
        blob_bytes=counts[4],
    )


def _validate_canonical_entity(entity: CanonicalEntity) -> None:
    if entity.tombstone:
        raise ValueError(
            "P2P_BUNDLE_CAPABILITY_UNSUPPORTED: tombstone records are reserved for a later schema"
        )
    payload = entity.payload
    if set(payload) != {"namespace", "coordinates", "media_type", "document"}:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: payload fields are not exact")
    namespace = payload.get("namespace")
    coordinates = payload.get("coordinates")
    media_type = payload.get("media_type")
    if not isinstance(namespace, str) or namespace not in _CANONICAL_NAMESPACES:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: namespace is unsupported")
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: coordinates must be a non-empty sequence")
    for coordinate in coordinates:
        if (
            not isinstance(coordinate, str)
            or coordinate in {"", ".", ".."}
            or any(marker in coordinate for marker in ("/", "\\", ":", "\x00"))
        ):
            raise ValueError("P2P_CANONICAL_ENTITY_INVALID: coordinate is unsafe")
    if media_type not in _CANONICAL_MEDIA_TYPES:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: media type is unsupported")
    if namespace == "project":
        if len(coordinates) != 1 or coordinates[0] not in _PROJECT_SINGLETON_COORDINATES:
            raise ValueError("P2P_CANONICAL_ENTITY_INVALID: project coordinate is unsupported")
        expected_type = f"p2p.project.{coordinates[0].replace('.', '_')}"
    else:
        expected_type = f"p2p.{namespace}.document"
    expected_id = f"{namespace}:{':'.join(coordinates)}"
    if entity.technical_id != expected_id or entity.entity_type != expected_type:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: envelope disagrees with coordinates")


def _identity_lineage(entity: CanonicalEntity) -> list[Mapping[str, object]]:
    document = entity.payload.get("document")
    if not isinstance(document, Mapping):
        raise ValueError("P2P_PROJECT_LINEAGE_INVALID: identity document is invalid")
    identity = document.get("project_identity")
    if not isinstance(identity, Mapping):
        raise ValueError("P2P_PROJECT_LINEAGE_INVALID: identity payload is invalid")
    raw_lineage = identity.get("lineage")
    if not isinstance(raw_lineage, list):
        raise ValueError("P2P_PROJECT_LINEAGE_INVALID: identity lineage is not a sequence")
    normalized: list[Mapping[str, object]] = []
    for item in raw_lineage:
        value = normalize_semantic_value(item)
        if not isinstance(value, Mapping):
            raise ValueError("P2P_PROJECT_LINEAGE_INVALID: lineage item is invalid")
        normalized.append(value)
    if normalized != sorted(normalized, key=canonical_json_bytes):
        raise ValueError("P2P_PROJECT_LINEAGE_INVALID: lineage is not in canonical order")
    return normalized


def _entity_from_mapping(value: object) -> CanonicalEntity:
    item = _mapping(value, "entity")
    if set(item) != {
        "entity_type",
        "technical_id",
        "human_key",
        "entity_version",
        "payload",
        "tombstone",
    }:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: entity fields are not exact")
    payload = _mapping(item.get("payload"), "entity payload")
    human_key = item.get("human_key")
    if human_key is not None and not isinstance(human_key, str):
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: human key must be text or null")
    entity_version = _positive_int(item.get("entity_version"), "entity version")
    tombstone = item.get("tombstone")
    if not isinstance(tombstone, bool):
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: tombstone must be boolean")
    if tombstone:
        raise ValueError(
            "P2P_BUNDLE_CAPABILITY_UNSUPPORTED: tombstone records are reserved for a later schema"
        )
    normalized_payload = normalize_semantic_value(payload)
    if not isinstance(normalized_payload, Mapping):
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: payload normalization failed")
    return CanonicalEntity(
        entity_type=str(item.get("entity_type") or ""),
        technical_id=str(item.get("technical_id") or ""),
        human_key=human_key,
        entity_version=entity_version,
        payload=normalized_payload,
        tombstone=tombstone,
    )


def _relation_from_mapping(value: object) -> CanonicalRelation:
    item = _mapping(value, "relation")
    if set(item) != {
        "relation_type",
        "relation_id",
        "source_entity",
        "target_entity",
        "payload",
    }:
        raise ValueError("P2P_CANONICAL_RELATION_INVALID: relation fields are not exact")
    normalized_payload = normalize_semantic_value(_mapping(item.get("payload"), "relation payload"))
    if not isinstance(normalized_payload, Mapping):
        raise ValueError("P2P_CANONICAL_RELATION_INVALID: payload normalization failed")
    return CanonicalRelation(
        relation_type=str(item.get("relation_type") or ""),
        relation_id=str(item.get("relation_id") or ""),
        source_entity=str(item.get("source_entity") or ""),
        target_entity=str(item.get("target_entity") or ""),
        payload=normalized_payload,
    )


def _blob_from_mapping(value: object) -> ManagedBlob:
    item = _mapping(value, "managed blob")
    if set(item) != {"digest", "size", "media_type"}:
        raise ValueError("P2P_MANAGED_BLOB_INVALID: blob fields are not exact")
    digest = str(item.get("digest") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("P2P_MANAGED_BLOB_DIGEST_INVALID: digest must be SHA-256")
    size = item.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("P2P_MANAGED_BLOB_INVALID: size must be non-negative")
    media_type = item.get("media_type")
    if not isinstance(media_type, str) or not media_type:
        raise ValueError("P2P_MANAGED_BLOB_INVALID: media type is required")
    return ManagedBlob(digest=digest, size=size, media_type=media_type)


def _project_uuid_from_entity(entity: CanonicalEntity, root_key: str) -> str:
    document = entity.payload.get("document")
    root = document.get(root_key) if isinstance(document, Mapping) else None
    if not isinstance(root, Mapping):
        raise ValueError(f"P2P_BUNDLE_IDENTITY_INVALID: {root_key} record is invalid")
    return ProjectUuid(
        str(root.get("project_uuid" if root_key == "project_identity" else "uuid") or "")
    ).value


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"P2P_BUNDLE_DIGEST_INVALID: {label} must be lowercase SHA-256")
    return value


def _non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"P2P_BUNDLE_MANIFEST_INVALID: {label} must be non-negative")
    return value


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"P2P_CANONICAL_ENTITY_INVALID: {label} must be positive")
    return value


def _safe_archive_name(value: str) -> str:
    normalized = value.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if (
        not normalized
        or pure.is_absolute()
        or ".." in pure.parts
        or normalized.startswith("./")
        or ":" in pure.parts[0]
        or "\x00" in normalized
    ):
        raise ValueError(f"P2P_BUNDLE_UNSAFE_ENTRY: {value}")
    return pure.as_posix()


def _safe_project_path(value: str) -> str:
    normalized = _safe_archive_name(value)
    if not normalized.startswith(".p2p/") or normalized.startswith(
        ".p2p/.internal/workspace-transactions/"
    ):
        raise ValueError(f"P2P_BACKUP_PATH_INVALID: {value}")
    return normalized


def _safe_staged_target(staging_p2p: Path, project_path: str) -> Path:
    normalized = _safe_project_path(project_path)
    target = staging_p2p.parent / normalized
    if not target.resolve(strict=False).is_relative_to(staging_p2p.resolve()):
        raise ValueError("P2P_BUNDLE_UNSAFE_ENTRY: staged target escapes .p2p")
    current = target.parent
    while current != staging_p2p.parent:
        if current.exists() and current.is_symlink():
            raise ValueError("P2P_BUNDLE_UNSAFE_ENTRY: staged target parent is a symlink")
        if current == staging_p2p:
            break
        current = current.parent
    return target


def _archive_kind(source: Path, limits: BundleLimits) -> str:
    try:
        path = source.resolve()
        if path.stat().st_size > limits.max_archive_bytes:
            raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: archive exceeds its compressed-size limit")
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            if len(infos) > limits.max_entries:
                raise ValueError("P2P_BUNDLE_LIMIT_EXCEEDED: archive has too many entries")
            names = {item.filename for item in infos}
    except ValueError:
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"P2P_BUNDLE_ARCHIVE_INVALID: {exc}") from exc
    if f"{BUNDLE_ARCHIVE_ROOT}/manifest.json" in names:
        return "bundle"
    if _BACKUP_MANIFEST_ENTRY in names:
        return "physical_backup"
    raise ValueError("P2P_BUNDLE_ARCHIVE_INVALID: archive kind is unknown")


def _changed_entity_count(current: CanonicalMemorySnapshot, target: CanonicalMemorySnapshot) -> int:
    current_map = {item.technical_id: semantic_sha256(item.to_dict()) for item in current.entities}
    target_map = {item.technical_id: semantic_sha256(item.to_dict()) for item in target.entities}
    return sum(
        1
        for key in set(current_map) | set(target_map)
        if current_map.get(key) != target_map.get(key)
    )


def _safe_recovery_path(root: Path, value: str) -> Path:
    path = Path(value)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root.resolve()) or resolved == root.resolve():
        raise ValueError("recovery path escapes project root")
    return resolved

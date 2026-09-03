from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from p2p_engine.core.canonical_memory import (
    CanonicalEntity,
    CanonicalMemoryInventory,
    CanonicalRelation,
    ManagedBlob,
    MemoryArtifact,
    normalize_semantic_value,
)
from p2p_engine.core.project_identity import ProjectIdentity
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.storage.project_identity import FilesystemProjectIdentityStore

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BLOB_PATH = re.compile(r"^blobs/sha256/([0-9a-f]{2})/([0-9a-f]{64})$")
_SECRET_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "client_secret",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "token",
    }
)

_CANONICAL_PROJECT_FILES = frozenset(
    {
        "authority-events.yml",
        "authority.yml",
        "conflicts.yml",
        "definition.yml",
        "domain.yml",
        "identity.yml",
        "interaction-style.yml",
        "next-actions-log.yml",
        "next-actions.yml",
        "operational-brief.md",
        "permissions.yml",
        "questions.yml",
        "rubrics.yml",
        "runtime.yml",
        "structure-events.yml",
        "structure-snapshots.yml",
        "structure-source.yml",
        "structure.yml",
        "vertical.lock.yml",
        "vertical.yml",
        "workspace-schema.yml",
    }
)
_DERIVED_PROJECT_FILES = frozenset(
    {
        "assessment.yml",
        "brief-context.md",
        "brief.prompt.md",
        "decisions-map.yml",
        "maturity-assessment.yml",
        "overview.md",
        "problem.md",
        "projection-manifest.yml",
        "project-swot.md",
        "scope.md",
    }
)
_CANONICAL_COLLECTIONS = frozenset(
    {
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
_DERIVED_PREFIXES = ("outputs/", "prompts/", "registries/")
_INTEGRATION_EXACT = frozenset({"agent-integrations.yml", "agent-policy.yml"})
_SUPPORTED_DOCUMENT_SUFFIXES = frozenset({".json", ".md", ".yaml", ".yml"})


@dataclass(frozen=True)
class FilesystemCanonicalMemoryStore:
    """Filesystem adapter for the backend-neutral canonical-memory port."""

    root: Path
    p2p_dir: Path | None = None
    max_document_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        resolved_root = self.root.resolve()
        object.__setattr__(self, "root", resolved_root)
        object.__setattr__(
            self,
            "p2p_dir",
            (self.p2p_dir or resolved_root / ".p2p").resolve(),
        )

    @property
    def identity_store(self) -> FilesystemProjectIdentityStore:
        assert self.p2p_dir is not None
        return FilesystemProjectIdentityStore(root=self.root, p2p_dir=self.p2p_dir)

    def project_identity(self) -> ProjectIdentity:
        return self.identity_store.load()

    def inventory(self) -> CanonicalMemoryInventory:
        assert self.p2p_dir is not None
        if not self.p2p_dir.is_dir() or self.p2p_dir.is_symlink():
            raise ValueError("P2P_CANONICAL_MEMORY_MISSING: .p2p is missing or unsafe")
        artifacts: list[MemoryArtifact] = []
        for path in sorted(self.p2p_dir.rglob("*")):
            relative = path.relative_to(self.p2p_dir).as_posix()
            if path.is_symlink():
                artifacts.append(
                    MemoryArtifact(
                        locator=f".p2p/{relative}",
                        classification="unknown",
                        semantic_kind="symlink",
                        portable=False,
                        reconstructible=False,
                        size=0,
                        physical_sha256="",
                        reason="Symlinks are never valid durable project-memory artifacts.",
                        blocking=True,
                    )
                )
                continue
            if not path.is_file():
                continue
            classification, semantic_kind, reason = classify_memory_path(relative)
            content = path.read_bytes()
            blocking = classification == "unknown"
            if len(content) > self.max_document_bytes and classification != "managed_blob":
                blocking = True
                reason = (
                    f"Artifact exceeds the {self.max_document_bytes}-byte canonical document limit."
                )
            if classification in {"canonical_project", "replica_local"}:
                try:
                    parsed = _parse_document(path, content)
                    if _contains_secret_key(parsed):
                        blocking = True
                        reason = "A secret-shaped field is forbidden inside .p2p durable state."
                except ValueError as exc:
                    blocking = True
                    reason = str(exc)
            artifacts.append(
                MemoryArtifact(
                    locator=f".p2p/{relative}",
                    classification=classification,
                    semantic_kind=semantic_kind,
                    portable=classification in {"canonical_project", "managed_blob"},
                    reconstructible=classification
                    in {
                        "derived_projection",
                        "integration_artifact",
                        "runtime_transient",
                    },
                    size=len(content),
                    physical_sha256=hashlib.sha256(content).hexdigest(),
                    reason=reason,
                    blocking=blocking,
                )
            )
        return CanonicalMemoryInventory(tuple(artifacts))

    def read_entities(self, inventory: CanonicalMemoryInventory) -> tuple[CanonicalEntity, ...]:
        entities: list[CanonicalEntity] = []
        for artifact in inventory.portable:
            if artifact.classification != "canonical_project":
                continue
            relative = artifact.locator.removeprefix(".p2p/")
            path = self._safe_path(relative)
            content = path.read_bytes()
            entities.append(canonical_entity_from_document(relative, content))
        return tuple(sorted(entities, key=lambda item: (item.entity_type, item.technical_id)))

    def read_relations(
        self,
        entities: Iterable[CanonicalEntity],
    ) -> tuple[CanonicalRelation, ...]:
        relations: list[CanonicalRelation] = []
        for entity in entities:
            document = entity.payload.get("document")
            if not isinstance(document, Mapping):
                continue
            raw_relations = document.get("canonical_relations")
            if raw_relations is None:
                continue
            if not isinstance(raw_relations, list):
                raise ValueError(
                    f"P2P_CANONICAL_RELATION_INVALID: {entity.technical_id} relations must be a sequence"
                )
            for index, raw in enumerate(raw_relations):
                if not isinstance(raw, Mapping):
                    raise ValueError("P2P_CANONICAL_RELATION_INVALID: relation must be a mapping")
                relation_type = str(raw.get("type") or "").strip()
                target = str(raw.get("target") or "").strip()
                relation_id = str(raw.get("id") or f"{entity.technical_id}:{index + 1}").strip()
                payload = raw.get("payload") or {}
                if not isinstance(payload, Mapping):
                    raise ValueError("P2P_CANONICAL_RELATION_INVALID: payload must be a mapping")
                normalized_payload = normalize_semantic_value(payload)
                if not isinstance(normalized_payload, Mapping):
                    raise ValueError("P2P_CANONICAL_RELATION_INVALID: payload normalization failed")
                relations.append(
                    CanonicalRelation(
                        relation_type=relation_type,
                        relation_id=relation_id,
                        source_entity=entity.technical_id,
                        target_entity=target,
                        payload=normalized_payload,
                    )
                )
        return tuple(sorted(relations, key=lambda item: (item.relation_type, item.relation_id)))

    def read_blobs(self, inventory: CanonicalMemoryInventory) -> tuple[ManagedBlob, ...]:
        blobs: list[ManagedBlob] = []
        for artifact in inventory.portable:
            if artifact.classification != "managed_blob":
                continue
            relative = artifact.locator.removeprefix(".p2p/")
            match = _BLOB_PATH.fullmatch(relative)
            if match is None or match.group(1) != match.group(2)[:2]:
                raise ValueError("P2P_MANAGED_BLOB_PATH_INVALID: invalid content-addressed path")
            digest = match.group(2)
            if artifact.physical_sha256 != digest:
                raise ValueError(
                    f"P2P_MANAGED_BLOB_DIGEST_MISMATCH: {artifact.locator} does not match its digest"
                )
            blobs.append(
                ManagedBlob(
                    digest=f"sha256:{digest}",
                    size=artifact.size,
                    storage_locator=artifact.locator,
                )
            )
        return tuple(sorted(blobs, key=lambda item: item.digest))

    def read_blob_bytes(self, blob: ManagedBlob) -> bytes:
        digest = blob.digest.removeprefix("sha256:")
        if not _SHA256.fullmatch(digest):
            raise ValueError("P2P_MANAGED_BLOB_DIGEST_INVALID: blob digest must be SHA-256")
        path = self._safe_path(f"blobs/sha256/{digest[:2]}/{digest}")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("P2P_MANAGED_BLOB_DIGEST_MISMATCH: managed blob bytes changed")
        return content

    def activation_documents(
        self,
        entities: Iterable[CanonicalEntity],
    ) -> dict[str, bytes]:
        documents: dict[str, bytes] = {}
        for entity in entities:
            payload = entity.payload
            if set(payload) != {"namespace", "coordinates", "media_type", "document"}:
                raise ValueError(
                    "P2P_CANONICAL_ENTITY_INVALID: document payload fields are not exact"
                )
            namespace = payload.get("namespace")
            coordinates = payload.get("coordinates")
            media_type = payload.get("media_type")
            if not isinstance(namespace, str) or not isinstance(coordinates, list):
                raise ValueError("P2P_CANONICAL_ENTITY_INVALID: logical coordinates are invalid")
            if not all(isinstance(item, str) and item for item in coordinates):
                raise ValueError("P2P_CANONICAL_ENTITY_INVALID: coordinate components are invalid")
            relative = _relative_for_coordinates(namespace, coordinates, str(media_type))
            expected_id = _technical_id(namespace, coordinates)
            if expected_id != entity.technical_id:
                raise ValueError(
                    "P2P_CANONICAL_ENTITY_INVALID: technical ID disagrees with coordinates"
                )
            if relative in documents:
                raise ValueError(
                    "P2P_CANONICAL_ENTITY_DUPLICATE: logical records map to one target"
                )
            documents[f".p2p/{relative}"] = _encode_document(
                str(media_type), payload.get("document")
            )
        return dict(sorted(documents.items()))

    def blob_documents(
        self,
        blobs: Iterable[ManagedBlob],
        blob_bytes: Mapping[str, bytes],
    ) -> dict[str, bytes]:
        documents: dict[str, bytes] = {}
        for blob in blobs:
            digest = blob.digest.removeprefix("sha256:")
            content = blob_bytes.get(blob.digest)
            if content is None:
                raise ValueError(f"P2P_MANAGED_BLOB_MISSING: {blob.digest}")
            if len(content) != blob.size or hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f"P2P_MANAGED_BLOB_DIGEST_MISMATCH: {blob.digest}")
            documents[f".p2p/blobs/sha256/{digest[:2]}/{digest}"] = content
        return documents

    def current_portable_paths(self, inventory: CanonicalMemoryInventory) -> tuple[str, ...]:
        return tuple(sorted(item.locator for item in inventory.portable))

    def physical_backup_files(self, inventory: CanonicalMemoryInventory) -> dict[str, bytes]:
        blockers = inventory.blockers
        if blockers:
            raise ValueError(
                "P2P_CANONICAL_MEMORY_UNCLASSIFIED: "
                + ", ".join(item.locator for item in blockers[:20])
            )
        files: dict[str, bytes] = {}
        for artifact in inventory.artifacts:
            relative = artifact.locator.removeprefix(".p2p/")
            if relative.startswith(".internal/workspace-transactions/"):
                continue
            if relative.startswith("backups/"):
                continue
            files[artifact.locator] = self._safe_path(relative).read_bytes()
        return dict(sorted(files.items()))

    def physical_backup_directories(self) -> tuple[str, ...]:
        assert self.p2p_dir is not None
        directories: list[str] = []
        for path in sorted(self.p2p_dir.rglob("*")):
            if path.is_symlink() or not path.is_dir():
                continue
            relative = path.relative_to(self.p2p_dir).as_posix()
            if relative.startswith(".internal/workspace-transactions") or relative.startswith(
                "backups"
            ):
                continue
            directories.append(f".p2p/{relative}")
        return tuple(directories)

    def _safe_path(self, relative: str) -> Path:
        assert self.p2p_dir is not None
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise ValueError("P2P_CANONICAL_MEMORY_PATH_UNSAFE: unsafe .p2p path")
        path = self.p2p_dir / pure.as_posix()
        if path.is_symlink() or not path.resolve(strict=False).is_relative_to(self.p2p_dir):
            raise ValueError("P2P_CANONICAL_MEMORY_PATH_UNSAFE: path escapes .p2p")
        return path


def classify_memory_path(relative: str) -> tuple[str, str, str]:
    normalized = PurePosixPath(relative).as_posix()
    if normalized == "project.yml":
        return "canonical_project", "project.manifest", "Portable project manifest."
    if normalized in _INTEGRATION_EXACT:
        return (
            "integration_artifact",
            "agent.integration",
            "Generated agent integration state is recreated by the installed runtime.",
        )
    blob = _BLOB_PATH.fullmatch(normalized)
    if blob is not None:
        return "managed_blob", "managed_blob", "Content-addressed managed blob."
    if normalized.startswith("blobs/"):
        return "unknown", "invalid_blob", "Unrecognized managed-blob layout."
    if normalized.startswith("local/"):
        return "replica_local", "replica.state", "State belongs to one physical replica."
    if normalized.startswith("consents/"):
        return "replica_local", "consent.receipt", "Consent is local execution authority state."
    if normalized.startswith("backups/"):
        return "backup", "physical.backup", "Backup copies are not live canonical state."
    if normalized.startswith(".internal/workspace-transactions/"):
        return "runtime_transient", "workspace.transaction", "Crash-recovery transaction state."
    if normalized.startswith(".internal/mutation-receipts/"):
        return (
            "replica_local",
            "mutation.receipt",
            "Physical postcondition receipts are replica-local.",
        )
    if normalized.startswith(".internal/identity-adoption-backups/"):
        return "backup", "identity.backup", "Protected pre-adoption physical backup."
    if normalized.startswith(".internal/project-structure-exports/"):
        return "replica_local", "export.receipt", "Local export idempotency marker."
    if normalized.startswith(".internal/bundle-restores/"):
        return "replica_local", "restore.receipt", "Local restore idempotency receipt."
    if normalized.startswith(".internal/bundle-materializations/"):
        return (
            "replica_local",
            "materialization.receipt",
            "Server-root materialization idempotency receipt.",
        )
    if normalized.startswith(".internal/"):
        return "unknown", "internal.unknown", "Unknown internal artifact requires classification."
    if normalized.startswith(_DERIVED_PREFIXES):
        return "derived_projection", "derived.output", "Reconstructible generated projection."
    if normalized.startswith("project/vertical-memory/") or normalized.startswith(
        "project/features/"
    ):
        return "derived_projection", "derived.project_view", "Reconstructible project read model."
    if normalized.startswith("project/verticals/"):
        return "integration_artifact", "vertical.cache", "Installed vertical package cache."
    if normalized.startswith("project/"):
        name = normalized.removeprefix("project/")
        if "/" not in name and name in _CANONICAL_PROJECT_FILES:
            return (
                "canonical_project",
                f"project.{_stem(name)}",
                "Portable project aggregate state.",
            )
        if "/" not in name and name in _DERIVED_PROJECT_FILES:
            return "derived_projection", f"project.{_stem(name)}", "Reconstructible project view."
        return "unknown", "project.unknown", "Unknown project artifact may affect semantics."
    first = normalized.split("/", 1)[0]
    if first in _CANONICAL_COLLECTIONS:
        if Path(normalized).suffix.lower() not in _SUPPORTED_DOCUMENT_SUFFIXES:
            return (
                "unknown",
                f"{first}.unknown",
                "Canonical collections require a supported document type.",
            )
        return "canonical_project", f"{first}.document", "Portable canonical collection document."
    if normalized.startswith("personal/"):
        return (
            "personal_configuration",
            "personal.configuration",
            "Personal settings are not project state.",
        )
    if normalized.startswith("external/"):
        return (
            "external_material",
            "external.reference",
            "External content is not imported implicitly.",
        )
    return "unknown", "unknown", "Artifact has no frozen memory classification rule."


def canonical_entity_from_document(relative: str, content: bytes) -> CanonicalEntity:
    """Decode one portable document without exposing its path in replication payloads."""
    normalized = PurePosixPath(relative).as_posix()
    classification, _, _ = classify_memory_path(normalized)
    if classification != "canonical_project":
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: document is not canonical project state")
    path = Path(normalized)
    namespace, coordinates = _logical_coordinates(normalized)
    media_type = _media_type(path)
    document = _parse_document(path, content)
    if normalized == "project/identity.yml":
        document = _canonical_identity_document(document)
    payload = {
        "namespace": namespace,
        "coordinates": coordinates,
        "media_type": media_type,
        "document": normalize_semantic_value(document),
    }
    return CanonicalEntity(
        entity_type=_entity_type(namespace, coordinates),
        technical_id=_technical_id(namespace, coordinates),
        human_key=_human_key(namespace, coordinates),
        entity_version=_entity_version(document),
        payload=payload,
        storage_locator=f".p2p/{normalized}",
    )


def managed_blob_from_document(relative: str, content: bytes) -> ManagedBlob:
    normalized = PurePosixPath(relative).as_posix()
    match = _BLOB_PATH.fullmatch(normalized)
    digest = hashlib.sha256(content).hexdigest()
    if match is None or match.group(1) != match.group(2)[:2] or match.group(2) != digest:
        raise ValueError("P2P_MANAGED_BLOB_DIGEST_MISMATCH: managed blob path or bytes differ")
    return ManagedBlob(
        digest=f"sha256:{digest}",
        size=len(content),
        storage_locator=f".p2p/{normalized}",
    )


def managed_blob_references(value: object) -> tuple[str, ...]:
    references: set[str] = set()

    def visit(item: object) -> None:
        if isinstance(item, Mapping):
            if item.get("kind") == "managed_blob":
                digest = item.get("digest")
                if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                    raise ValueError("P2P_MANAGED_BLOB_REFERENCE_INVALID: digest is invalid")
                references.add(digest)
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return tuple(sorted(references))


def _parse_document(path: Path, content: bytes) -> object:
    suffix = path.suffix.lower()
    try:
        if suffix in {".yml", ".yaml"}:
            value = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
            return {} if value is None else value
        if suffix == ".json":
            return json.loads(content.decode("utf-8"), object_pairs_hook=_unique_json_object)
        if suffix == ".md":
            return content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"P2P_CANONICAL_DOCUMENT_INVALID: {path.name}: {exc}") from exc
    raise ValueError(f"P2P_CANONICAL_DOCUMENT_INVALID: unsupported type for {path.name}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _contains_secret_key(
    value: object,
    *,
    _active: set[int] | None = None,
    _depth: int = 0,
) -> bool:
    if _depth > 128:
        raise ValueError("P2P_CANONICAL_DOCUMENT_INVALID: document nesting is too deep")
    active = _active if _active is not None else set()
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in active:
            raise ValueError("P2P_CANONICAL_DOCUMENT_INVALID: cyclic mappings are forbidden")
        active.add(marker)
        try:
            for key, child in value.items():
                normalized = str(key).strip().lower().replace("-", "_")
                if (
                    normalized in _SECRET_KEYS
                    and child is not None
                    and child != ""
                    and child is not False
                ):
                    return True
                if _contains_secret_key(child, _active=active, _depth=_depth + 1):
                    return True
        finally:
            active.remove(marker)
    elif isinstance(value, list):
        marker = id(value)
        if marker in active:
            raise ValueError("P2P_CANONICAL_DOCUMENT_INVALID: cyclic sequences are forbidden")
        active.add(marker)
        try:
            return any(
                _contains_secret_key(item, _active=active, _depth=_depth + 1) for item in value
            )
        finally:
            active.remove(marker)
    return False


def _canonical_identity_document(value: object) -> object:
    if not isinstance(value, Mapping):
        return value
    root = value.get("project_identity")
    if not isinstance(root, Mapping):
        return value
    lineage = root.get("lineage")
    if not isinstance(lineage, list):
        return value
    normalized_lineage = [normalize_semantic_value(item) for item in lineage]
    normalized_lineage.sort(key=canonical_json_sort_key)
    identity = dict(root)
    identity["lineage"] = normalized_lineage
    document = dict(value)
    document["project_identity"] = identity
    return document


def canonical_json_sort_key(value: object) -> str:
    return json.dumps(
        normalize_semantic_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _logical_coordinates(relative: str) -> tuple[str, list[str]]:
    path = PurePosixPath(relative)
    if relative == "project.yml":
        return "project", ["manifest"]
    namespace = path.parts[0]
    components = list(path.parts[1:])
    if namespace == "project":
        components = [_stem(path.name)]
    elif components:
        components[-1] = _stem(components[-1])
    if not components:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: missing logical coordinates")
    return namespace, components


def _relative_for_coordinates(namespace: str, coordinates: list[str], media_type: str) -> str:
    if namespace == "project" and coordinates == ["manifest"]:
        return "project.yml"
    if namespace not in _CANONICAL_COLLECTIONS | {"project"}:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: unsupported logical namespace")
    if namespace == "project":
        if len(coordinates) != 1:
            raise ValueError(
                "P2P_CANONICAL_ENTITY_INVALID: project singleton coordinate is invalid"
            )
        filename = _filename(coordinates[0], media_type)
        if filename not in _CANONICAL_PROJECT_FILES:
            raise ValueError("P2P_CANONICAL_ENTITY_INVALID: unknown project singleton")
        return f"project/{filename}"
    safe = [_safe_coordinate(item) for item in coordinates]
    safe[-1] = _filename(safe[-1], media_type)
    relative = PurePosixPath(namespace, *safe).as_posix()
    classification, _, _ = classify_memory_path(relative)
    if classification != "canonical_project":
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: logical coordinates are not portable")
    return relative


def _safe_coordinate(value: str) -> str:
    if value in {"", ".", ".."} or "/" in value or "\\" in value or "\x00" in value:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: unsafe logical coordinate")
    return value


def _filename(stem: str, media_type: str) -> str:
    suffix = {
        "application/json": ".json",
        "application/yaml": ".yml",
        "text/markdown": ".md",
    }.get(media_type)
    if suffix is None:
        raise ValueError("P2P_CANONICAL_ENTITY_INVALID: unsupported media type")
    return f"{_safe_coordinate(stem)}{suffix}"


def _encode_document(media_type: str, document: object) -> bytes:
    normalized = normalize_semantic_value(document)
    if media_type == "application/yaml":
        return yaml_dump(normalized).encode("ascii")
    if media_type == "application/json":
        return (json.dumps(normalized, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
            "utf-8"
        )
    if media_type == "text/markdown":
        if not isinstance(normalized, str):
            raise ValueError("P2P_CANONICAL_ENTITY_INVALID: Markdown payload must be text")
        return normalized.encode("utf-8")
    raise ValueError("P2P_CANONICAL_ENTITY_INVALID: unsupported media type")


def _media_type(path: Path) -> str:
    return {
        ".json": "application/json",
        ".md": "text/markdown",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
    }[path.suffix.lower()]


def _stem(filename: str) -> str:
    for suffix in (".yaml", ".json", ".yml", ".md"):
        if filename.endswith(suffix):
            return filename[: -len(suffix)]
    return filename


def _technical_id(namespace: str, coordinates: list[str]) -> str:
    return f"{namespace}:{':'.join(coordinates)}"


def _entity_type(namespace: str, coordinates: list[str]) -> str:
    if namespace == "project":
        return f"p2p.project.{coordinates[0].replace('.', '_')}"
    return f"p2p.{namespace}.document"


def _human_key(namespace: str, coordinates: list[str]) -> str | None:
    if namespace in {"changes", "choices", "intake", "proposals", "verticals", "work"}:
        return coordinates[0]
    return None


def _entity_version(document: object) -> int:
    if not isinstance(document, Mapping):
        return 1
    for key in ("entity_version", "revision", "schema_version", "version"):
        value = document.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
            return value
    return 1

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from p2p_engine.core.canonical_memory import (
    CANONICAL_MEMORY_CONTRACT,
    CanonicalEntity,
    CanonicalMemoryInventory,
    CanonicalMemorySnapshot,
    CanonicalRelation,
    ManagedBlob,
    MemoryArtifact,
    canonical_json_bytes,
    semantic_sha256,
)
from p2p_engine.core.mutation_receipts import MutationReceipt
from p2p_engine.core.project_identity import (
    ProjectIdentity,
    project_identity_from_mapping,
)
from p2p_engine.core.project_state_storage import (
    ProjectEntityRecord,
    ProjectEntityRef,
    ProjectStateCommitResult,
    ProjectStateMutation,
    ProjectStateQuery,
    ProjectStateRevision,
    ProjectStorageError,
    ProjectStorageErrorCode,
)
from p2p_engine.foundation.files import sync_directory
from p2p_engine.ports.project_state import ProjectStateRepository
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.mutation_receipts import parse_mutation_receipt_payload
from p2p_engine.storage.canonical_memory import managed_blob_references
from p2p_engine.storage.path_safety import is_link_or_reparse_point
from p2p_engine.storage.sqlite_driver import (
    DEFAULT_BUSY_TIMEOUT_MS,
    SQLiteConnectionFactory,
    validate_sqlite_header,
)
from p2p_engine.storage.sqlite_schema import (
    SQLITE_APPLICATION_ID,
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
    SQLITE_SCHEMA_CONTRACT,
    SQLITE_SCHEMA_V1,
    SQLITE_SCHEMA_V1_SHA256,
    SQLITE_SCHEMA_VERSION,
)

FailureInjector = Callable[[str], None]
SQLITE_PUBLIC_RECEIPT_OPERATION_PREFIX = "sqlite-public-mutation-"
SQLITE_PUBLIC_RECEIPT_DOCUMENT_MAX_BYTES = 1_048_576
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SQLITE_RESTORE_OPERATION = re.compile(r"^sqlite-restore-[0-9a-f]{64}$")
_DURABLE_PUBLIC_RECEIPT_PATHS = (
    re.compile(
        r"^\.p2p/\.internal/project-structure-exports/[0-9a-f]{64}\.yml$"
    ),
    re.compile(
        r"^\.p2p/\.internal/identity-adoption-backups/"
        r"[0-9a-f]{64}/project\.yml$"
    ),
)


def _maintenance_marker_present(root: Path) -> bool:
    marker = root / SQLITE_MAINTENANCE_MARKER
    return marker.exists() or is_link_or_reparse_point(marker)


@dataclass(frozen=True)
class SQLitePublicMutationRecord:
    """One public receipt and DB-owned replica-local postconditions."""

    receipt: MutationReceipt
    durable_documents: tuple[tuple[str, bytes], ...] = ()

    def __post_init__(self) -> None:
        paths = [path for path, _content in self.durable_documents]
        if paths != sorted(set(paths)):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public receipt documents are not unique and ordered",
            )
        expected = {
            item.path: item.physical_sha256
            for item in self.receipt.postconditions
            if sqlite_public_receipt_document_path(item.path)
        }
        if set(paths) != set(expected):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public receipt has incomplete durable postconditions",
            )
        for path, content in self.durable_documents:
            if len(content) > SQLITE_PUBLIC_RECEIPT_DOCUMENT_MAX_BYTES:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite public receipt document exceeds the size limit",
                    diagnostic=path,
                )
            if hashlib.sha256(content).hexdigest() != expected[path]:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite public receipt document digest is inconsistent",
                    diagnostic=path,
                )

    def document_map(self) -> dict[str, bytes]:
        return dict(self.durable_documents)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_text(value: object) -> str:
    return canonical_json_bytes(value).decode("utf-8").rstrip("\n")


def sqlite_public_receipt_operation_id(key_sha256: str) -> str:
    if not _SHA256.fullmatch(key_sha256):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "public mutation receipt key is not a SHA-256 digest",
        )
    return f"{SQLITE_PUBLIC_RECEIPT_OPERATION_PREFIX}{key_sha256}"


def sqlite_public_receipt_document_path(path: str) -> bool:
    return any(pattern.fullmatch(path) is not None for pattern in _DURABLE_PUBLIC_RECEIPT_PATHS)


def sqlite_public_mutation_record(
    receipt: MutationReceipt,
    documents: Mapping[str, bytes] | None = None,
) -> SQLitePublicMutationRecord:
    return SQLitePublicMutationRecord(
        receipt=receipt,
        durable_documents=tuple(sorted((documents or {}).items())),
    )


def _encode_public_receipt_documents(
    record: SQLitePublicMutationRecord,
) -> list[dict[str, str]]:
    return [
        {
            "path": path,
            "physical_sha256": hashlib.sha256(content).hexdigest(),
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
        for path, content in record.durable_documents
    ]


def _decode_public_receipt_documents(value: object) -> dict[str, bytes]:
    if not isinstance(value, list):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite public receipt documents are not a sequence",
        )
    documents: dict[str, bytes] = {}
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {
            "path",
            "physical_sha256",
            "content_base64",
        }:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public receipt document metadata is invalid",
            )
        path = str(item["path"])
        digest = str(item["physical_sha256"])
        encoded = item["content_base64"]
        if not sqlite_public_receipt_document_path(path) or not _SHA256.fullmatch(
            digest
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public receipt document identity is invalid",
                diagnostic=path,
            )
        if not isinstance(encoded, str):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public receipt document content is invalid",
                diagnostic=path,
            )
        try:
            content = base64.b64decode(encoded.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error) as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public receipt document content is not canonical base64",
                diagnostic=path,
            ) from exc
        if path in documents or hashlib.sha256(content).hexdigest() != digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public receipt document is duplicate or corrupt",
                diagnostic=path,
            )
        documents[path] = content
    return documents


def _validated_replay_result(
    row: sqlite3.Row,
    *,
    mutation: ProjectStateMutation,
    public_record: SQLitePublicMutationRecord | None,
) -> ProjectStateCommitResult:
    try:
        payload = json.loads(str(row["result_json"]))
    except json.JSONDecodeError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite operation receipt contains invalid JSON",
            diagnostic=str(exc),
        ) from exc
    if not isinstance(payload, Mapping):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite operation receipt result is not an object",
        )
    stored_revision = str(row["result_revision_sha256"])
    stored_receipt_id = str(row["receipt_id"])
    if (
        str(row["status"]) != "applied"
        or str(row["project_uuid"]) != mutation.target.project_uuid
        or payload.get("revision") != stored_revision
        or str(payload.get("receipt_id") or "") != stored_receipt_id
    ):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite operation receipt columns and result payload disagree",
        )
    request_matches = (
        str(row["actor"]) == mutation.actor
        and stored_receipt_id == mutation.receipt_id
    )
    if public_record is not None:
        try:
            stored_public_receipt = parse_mutation_receipt_payload(
                payload.get("public_receipt")
            )
            sqlite_public_mutation_record(
                stored_public_receipt,
                _decode_public_receipt_documents(
                    payload.get("public_receipt_documents", [])
                ),
            )
        except (ValueError, ProjectStorageError) as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public operation receipt failed replay validation",
                diagnostic=str(exc),
            ) from exc
        candidate = public_record.receipt
        request_matches = request_matches and (
            stored_public_receipt.key_sha256 == candidate.key_sha256
            and stored_public_receipt.operation == candidate.operation
            and stored_public_receipt.actor == candidate.actor
            and stored_public_receipt.request_fingerprint_sha256
            == candidate.request_fingerprint_sha256
            and stored_public_receipt.preview_token_sha256
            == candidate.preview_token_sha256
        )
    elif payload.get("public_receipt") is not None:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite generic operation receipt contains public mutation state",
        )
    else:
        request_matches = request_matches and (
            stored_revision == mutation.target.semantic_state_digest
        )
    if not request_matches:
        raise ProjectStorageError(
            ProjectStorageErrorCode.idempotency_conflict,
            "operation ID was already used for a different SQLite mutation",
        )
    changed_payload = payload.get("changed_entities", [])
    if not isinstance(changed_payload, list):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite operation receipt changed entities are invalid",
        )
    try:
        changed = tuple(
            ProjectEntityRef(
                str(item["entity_type"]),
                str(item["technical_id"]),
            )
            for item in changed_payload
            if isinstance(item, Mapping)
            and set(item) == {"entity_type", "technical_id"}
        )
    except (KeyError, ValueError) as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite operation receipt changed entity is invalid",
            diagnostic=str(exc),
        ) from exc
    if len(changed) != len(changed_payload):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite operation receipt changed entity fields are invalid",
        )
    return ProjectStateCommitResult(
        status="applied",
        operation_id=mutation.operation_id,
        revision=ProjectStateRevision(stored_revision),
        changed_entities=changed,
        receipt_id=stored_receipt_id,
        replayed=True,
    )


def _record(entity: CanonicalEntity) -> ProjectEntityRecord:
    return ProjectEntityRecord(
        ref=ProjectEntityRef(entity.entity_type, entity.technical_id),
        human_key=entity.human_key,
        entity_version=entity.entity_version,
        payload=entity.payload,
    )


def sqlite_blob_path(root: Path, digest: str) -> Path:
    raw = digest.removeprefix("sha256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob digest is invalid",
        )
    return root / ".p2p/blobs/sha256" / raw[:2] / raw


def _is_link_or_reparse_point(path: Path) -> bool:
    """Return whether *path* is an unsafe indirection on this platform."""
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction) and is_junction():
            return True
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob path metadata cannot be inspected safely",
            diagnostic=str(exc),
        ) from exc
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def _blob_path_state(root: Path, digest: str) -> tuple[Path, bool]:
    """Validate the complete blob path without following unsafe components."""
    anchor = root.resolve()
    if _is_link_or_reparse_point(anchor) or not anchor.is_dir():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob project root is unsafe",
        )
    path = sqlite_blob_path(anchor, digest)
    try:
        relative = path.relative_to(anchor)
    except ValueError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob path escapes the project root",
        ) from exc

    current = anchor
    missing_component = False
    for index, part in enumerate(relative.parts):
        current /= part
        if _is_link_or_reparse_point(current):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob path contains a symlink, junction, or reparse point",
                diagnostic=relative.as_posix(),
            )
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            missing_component = True
            continue
        except OSError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob path metadata cannot be inspected safely",
                diagnostic=str(exc),
            ) from exc
        try:
            if not current.resolve(strict=False).is_relative_to(anchor):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "managed blob path escapes the project root",
                    diagnostic=relative.as_posix(),
                )
        except OSError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob path cannot be resolved safely",
                diagnostic=str(exc),
            ) from exc
        is_leaf = index == len(relative.parts) - 1
        expected_type = stat.S_ISREG if is_leaf else stat.S_ISDIR
        if missing_component or not expected_type(metadata.st_mode):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob path has an unexpected filesystem object",
                diagnostic=relative.as_posix(),
            )
    return path, not missing_component


def _ensure_blob_parent(root: Path, digest: str) -> Path:
    """Create missing blob directories one-by-one and durably link each parent."""
    anchor = root.resolve()
    path = sqlite_blob_path(anchor, digest)
    relative_parent = path.parent.relative_to(anchor)
    current = anchor
    for part in relative_parent.parts:
        current /= part
        if _is_link_or_reparse_point(current):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob parent contains a symlink, junction, or reparse point",
                diagnostic=relative_parent.as_posix(),
            )
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                pass
            except OSError as exc:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "managed blob parent cannot be created safely",
                    diagnostic=str(exc),
                ) from exc
            if _is_link_or_reparse_point(current):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "managed blob parent became an unsafe filesystem indirection",
                    diagnostic=relative_parent.as_posix(),
                )
            try:
                metadata = current.lstat()
            except OSError as exc:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "managed blob parent cannot be inspected after creation",
                    diagnostic=str(exc),
                ) from exc
            sync_directory(current.parent)
        except OSError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob parent cannot be inspected safely",
                diagnostic=str(exc),
            ) from exc
        if not stat.S_ISDIR(metadata.st_mode):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob parent is not a directory",
                diagnostic=relative_parent.as_posix(),
            )
        try:
            if not current.resolve(strict=False).is_relative_to(anchor):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "managed blob parent escapes the project root",
                    diagnostic=relative_parent.as_posix(),
                )
        except OSError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob parent cannot be resolved safely",
                diagnostic=str(exc),
            ) from exc
    return path


def read_sqlite_blob_bytes(root: Path, digest: str) -> bytes:
    """Read one blob only after path and opened-file identity checks."""
    path, exists = _blob_path_state(root, digest)
    if not exists:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob bytes are missing",
        )
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        before = path.lstat()
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(before, opened):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob changed while it was being opened",
            )
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            content = stream.read()
    except ProjectStorageError:
        raise
    except OSError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob bytes cannot be read safely",
            diagnostic=str(exc),
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    _path, still_exists = _blob_path_state(root, digest)
    try:
        after = path.lstat()
    except OSError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob cannot be revalidated after reading",
            diagnostic=str(exc),
        ) from exc
    if not still_exists or not os.path.samestat(opened, after):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob changed while it was being read",
        )
    return content


def install_sqlite_blob_bytes(root: Path, digest: str, content: bytes) -> bool:
    """Publish verified content atomically without replacing an existing path."""
    raw = digest.removeprefix("sha256:")
    if hashlib.sha256(content).hexdigest() != raw:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob payload does not match its digest",
        )
    path, exists = _blob_path_state(root, digest)
    if exists:
        if read_sqlite_blob_bytes(root, digest) != content:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "content-addressed blob path contains different bytes",
            )
        return False

    path = _ensure_blob_parent(root, digest)
    _path, exists = _blob_path_state(root, digest)
    if exists:
        if read_sqlite_blob_bytes(root, digest) != content:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "content-addressed blob path contains different bytes",
            )
        return False

    descriptor: int | None = None
    temporary: Path | None = None
    created = False
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("managed blob staging write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        os.close(descriptor)
        descriptor = None
        try:
            os.link(temporary, path)
            created = True
        except FileExistsError:
            if read_sqlite_blob_bytes(root, digest) != content:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "content-addressed blob path contains different bytes",
                )
        sync_directory(path.parent)
    except ProjectStorageError:
        raise
    except OSError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob cannot be published safely",
            diagnostic=str(exc),
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
                sync_directory(temporary.parent)
            except OSError:
                pass

    if read_sqlite_blob_bytes(root, digest) != content:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "published managed blob failed verification",
        )
    return created


def snapshot_digest(snapshot: CanonicalMemorySnapshot) -> str:
    return semantic_sha256(
        {
            "contract": CANONICAL_MEMORY_CONTRACT,
            "project_uuid": snapshot.project_uuid,
            "memory_schema": snapshot.memory_schema,
            "domain_contract": snapshot.domain_contract,
            "entities": [item.to_dict() for item in snapshot.entities],
            "relations": [item.to_dict() for item in snapshot.relations],
            "lineage": list(snapshot.lineage),
            "blobs": [item.to_dict() for item in snapshot.blobs],
        }
    )


class SQLiteProjectStateRepository:
    def __init__(
        self,
        root: Path,
        *,
        database_path: Path | None = None,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        self.root = root.resolve()
        self.database_path = database_path or self.root / SQLITE_DATABASE_PATH
        self.connections = SQLiteConnectionFactory(
            self.database_path,
            project_root=self.root if database_path is None else None,
            busy_timeout_ms=busy_timeout_ms,
        )
        self.codec = CanonicalBundleCodec()
        self.failure_injector = failure_injector

    def identity(self) -> ProjectIdentity:
        with self.connections.connect(writable=False) as connection:
            validate_sqlite_header(connection)
            project = connection.execute("SELECT * FROM projects").fetchone()
            if project is None:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite project identity is missing",
                )
            lineage = [
                {
                    "relation": str(row["relation"]),
                    "source_project_uuid": str(row["source_project_uuid"]),
                    "source_revision": {
                        "namespace": "source_memory",
                        "sha256": str(row["source_revision_sha256"]),
                    },
                    "visibility": str(row["visibility"]),
                }
                for row in connection.execute(
                    "SELECT relation, source_project_uuid, source_revision_sha256, visibility "
                    "FROM project_lineage WHERE project_uuid = ? ORDER BY ordinal",
                    (str(project["project_uuid"]),),
                )
            ]
            return project_identity_from_mapping(
                {
                    "contract": "p2p-project-identity/v1",
                    "policy_version": int(project["policy_version"]),
                    "project_uuid": str(project["project_uuid"]),
                    "display_name": str(project["display_name"]),
                    "mode": str(project["mode"]),
                    "replica_id": project["replica_id"],
                    "remote_binding": (
                        {
                            "server_instance_id": str(project["remote_server_id"]),
                            "remote_project_id": str(project["remote_project_id"]),
                        }
                        if project["remote_server_id"] is not None
                        else None
                    ),
                    "lineage": lineage,
                }
            )

    def current_revision(self) -> ProjectStateRevision:
        with self.connections.connect(writable=False) as connection:
            row = connection.execute(
                "SELECT semantic_state_digest FROM storage_metadata WHERE singleton = 1"
            ).fetchone()
        if row is None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite project revision is missing",
            )
        return ProjectStateRevision(str(row["semantic_state_digest"]))

    def snapshot(self) -> CanonicalMemorySnapshot:
        with self.connections.connect(writable=False) as connection:
            validate_sqlite_header(connection)
            connection.execute("BEGIN")
            try:
                snapshot = _snapshot_from_connection(connection)
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return snapshot

    def get(self, ref: ProjectEntityRef) -> ProjectEntityRecord | None:
        with self.connections.connect(writable=False) as connection:
            row = connection.execute(
                "SELECT entity_type, technical_id, human_key, entity_version, "
                "payload_json, tombstone FROM entities "
                "WHERE entity_type = ? AND technical_id = ?",
                (ref.entity_type, ref.technical_id),
            ).fetchone()
        return _record(_entity_from_row(row)) if row is not None else None

    def query(self, query: ProjectStateQuery) -> tuple[ProjectEntityRecord, ...]:
        clauses: list[str] = []
        parameters: list[object] = []
        if query.entity_types:
            clauses.append(f"entity_type IN ({','.join('?' for _ in query.entity_types)})")
            parameters.extend(query.entity_types)
        if query.technical_ids:
            clauses.append(f"technical_id IN ({','.join('?' for _ in query.technical_ids)})")
            parameters.extend(query.technical_ids)
        if query.human_key:
            clauses.append("human_key = ?")
            parameters.append(query.human_key)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(query.limit)
        sql = (
            "SELECT entity_type, technical_id, human_key, entity_version, "
            f"payload_json, tombstone FROM entities{where} "
            "ORDER BY entity_type, technical_id LIMIT ?"
        )
        with self.connections.connect(writable=False) as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return tuple(_record(_entity_from_row(row)) for row in rows)

    def public_mutation_records(self) -> tuple[SQLitePublicMutationRecord, ...]:
        """Read public receipts and DB-owned replica-local postconditions."""
        with self.connections.connect(writable=False) as connection:
            rows = connection.execute(
                "SELECT operation_id, receipt_id, project_uuid, actor, "
                "result_revision_sha256, status, result_json FROM receipts "
                "WHERE operation_id LIKE ? ORDER BY operation_id",
                (f"{SQLITE_PUBLIC_RECEIPT_OPERATION_PREFIX}%",),
            ).fetchall()
            project = connection.execute(
                "SELECT project_uuid FROM storage_metadata WHERE singleton = 1"
            ).fetchone()
        if project is None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite public mutation receipts have no project metadata",
            )
        project_uuid = str(project["project_uuid"])
        records: list[SQLitePublicMutationRecord] = []
        for row in rows:
            try:
                result = json.loads(str(row["result_json"]))
            except json.JSONDecodeError as exc:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite public mutation receipt contains invalid JSON",
                    diagnostic=str(exc),
                ) from exc
            if not isinstance(result, Mapping):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite public mutation receipt result is not an object",
                )
            payload = result.get("public_receipt")
            try:
                receipt = parse_mutation_receipt_payload(payload)
            except ValueError as exc:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite public mutation receipt failed validation",
                    diagnostic=str(exc),
                ) from exc
            if (
                str(row["operation_id"])
                != sqlite_public_receipt_operation_id(receipt.key_sha256)
                or str(row["receipt_id"]) != receipt.key_sha256
                or str(row["project_uuid"]) != project_uuid
                or str(row["actor"]) != receipt.actor
                or str(row["status"]) != "applied"
                or result.get("revision") != str(row["result_revision_sha256"])
                or str(result.get("receipt_id") or "") != receipt.key_sha256
            ):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite public mutation receipt identity is inconsistent",
                )
            documents = _decode_public_receipt_documents(
                result.get("public_receipt_documents", []),
            )
            records.append(sqlite_public_mutation_record(receipt, documents))
        return tuple(records)

    def public_mutation_receipts(self) -> tuple[MutationReceipt, ...]:
        """Read public idempotency receipts committed with SQLite state."""
        return tuple(record.receipt for record in self.public_mutation_records())

    def public_mutation_documents(self) -> dict[str, bytes]:
        """Return the replica-local receipt postconditions owned by SQLite."""
        documents: dict[str, bytes] = {}
        for record in self.public_mutation_records():
            for path, content in record.durable_documents:
                if path in documents and documents[path] != content:
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.integrity_failure,
                        "SQLite public receipts disagree on a durable document",
                        diagnostic=path,
                    )
                documents[path] = content
        return documents

    def integrity_check(self, *, verify_blobs: bool = True) -> tuple[str, ...]:
        issues: list[str] = []
        try:
            with self.connections.connect(writable=False) as connection:
                validate_sqlite_header(connection)
                integrity = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
                if integrity != ["ok"]:
                    issues.extend(integrity)
                foreign_keys = list(connection.execute("PRAGMA foreign_key_check"))
                issues.extend(f"foreign-key:{tuple(row)}" for row in foreign_keys)
            snapshot = self.snapshot()
            self.public_mutation_records()
            if verify_blobs:
                issues.extend(f"blob:{item}" for item in SQLiteBlobStore(self).verify(
                    blob.digest for blob in snapshot.blobs
                ))
        except (ProjectStorageError, ValueError) as exc:
            issues.append(str(exc))
        return tuple(issues)


class SQLiteCanonicalStore:
    """Canonical codec source backed by semantic SQLite rows and external blobs."""

    def __init__(self, repository: SQLiteProjectStateRepository) -> None:
        self.repository = repository

    def inventory(self) -> CanonicalMemoryInventory:
        snapshot = self.repository.snapshot()
        artifacts = tuple(
            MemoryArtifact(
                locator=f"sqlite://entity/{item.technical_id}",
                classification="canonical_project",
                semantic_kind=item.entity_type,
                portable=True,
                reconstructible=False,
                size=len(canonical_json_bytes(item.payload)),
                physical_sha256=semantic_sha256(item.payload),
                reason="Canonical entity stored by the SQLite adapter.",
            )
            for item in snapshot.entities
        )
        return CanonicalMemoryInventory(artifacts)

    def project_identity(self) -> ProjectIdentity:
        return self.repository.identity()

    def read_entities(self, inventory: CanonicalMemoryInventory) -> tuple[CanonicalEntity, ...]:
        del inventory
        return self.repository.snapshot().entities

    def read_relations(
        self, entities: Iterable[CanonicalEntity]
    ) -> tuple[CanonicalRelation, ...]:
        del entities
        return self.repository.snapshot().relations

    def read_blobs(self, inventory: CanonicalMemoryInventory) -> tuple[ManagedBlob, ...]:
        del inventory
        return self.repository.snapshot().blobs

    def read_blob_bytes(self, blob: ManagedBlob) -> bytes:
        return SQLiteBlobStore(self.repository).read(blob.digest)


class SQLiteBlobStore:
    def __init__(self, repository: SQLiteProjectStateRepository) -> None:
        self.repository = repository

    def has(self, digest: str) -> bool:
        with self.repository.connections.connect(writable=False) as connection:
            row = connection.execute(
                "SELECT 1 FROM blobs WHERE digest = ?", (digest,)
            ).fetchone()
        if row is None:
            return False
        _path, exists = _blob_path_state(self.repository.root, digest)
        return exists

    def read(self, digest: str) -> bytes:
        with self.repository.connections.connect(writable=False) as connection:
            row = connection.execute(
                "SELECT size FROM blobs WHERE digest = ?", (digest,)
            ).fetchone()
        if row is None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob metadata is missing",
            )
        content = read_sqlite_blob_bytes(self.repository.root, digest)
        raw = digest.removeprefix("sha256:")
        if len(content) != int(row["size"]) or hashlib.sha256(content).hexdigest() != raw:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob bytes failed integrity verification",
            )
        return content

    def verify(self, digests: Iterable[str]) -> tuple[str, ...]:
        failed: list[str] = []
        for digest in digests:
            try:
                self.read(digest)
            except ProjectStorageError:
                failed.append(digest)
        return tuple(sorted(failed))


class SQLiteProjectUnitOfWork:
    def __init__(
        self,
        repository: SQLiteProjectStateRepository,
        *,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        self._repository = repository
        self._mutation: ProjectStateMutation | None = None
        self._public_mutation: SQLitePublicMutationRecord | None = None
        self._closed = False
        self.failure_injector = failure_injector or repository.failure_injector

    @property
    def repository(self) -> ProjectStateRepository:
        return self._repository

    def stage(self, mutation: ProjectStateMutation) -> None:
        if self._closed or self._mutation is not None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.internal,
                "unit of work already has a staged command",
            )
        current = self._repository.snapshot()
        if mutation.expected_revision.sha256 != current.semantic_state_digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.stale_revision,
                "project state changed before the command was staged",
            )
        if mutation.target.project_uuid != current.project_uuid:
            raise ProjectStorageError(
                ProjectStorageErrorCode.identity_mismatch,
                "command target project UUID disagrees with active project",
            )
        _validate_target_snapshot(mutation.target)
        self._mutation = mutation

    def stage_public_receipt(
        self,
        receipt: MutationReceipt,
        *,
        durable_documents: Mapping[str, bytes] | None = None,
    ) -> None:
        """Bind one public idempotency receipt to this SQLite transaction."""
        if self._closed or self._public_mutation is not None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.internal,
                "unit of work already has a staged public receipt",
            )
        self._public_mutation = sqlite_public_mutation_record(
            receipt,
            durable_documents,
        )

    def commit(self) -> ProjectStateCommitResult:
        if self._closed or self._mutation is None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.internal,
                "unit of work has no staged command",
            )
        mutation = self._mutation
        public_record = self._public_mutation
        public_receipt = public_record.receipt if public_record is not None else None
        uses_public_namespace = mutation.operation_id.startswith(
            SQLITE_PUBLIC_RECEIPT_OPERATION_PREFIX
        )
        if (uses_public_namespace and public_receipt is None) or (
            _SQLITE_RESTORE_OPERATION.fullmatch(mutation.operation_id) is not None
            or mutation.operation_id.startswith("sqlite-bootstrap-")
        ):
            self._closed = True
            raise ProjectStorageError(
                ProjectStorageErrorCode.configuration_contradiction,
                "SQLite operation ID uses a reserved persistence namespace",
            )
        if public_receipt is not None and (
            mutation.operation_id
            != sqlite_public_receipt_operation_id(public_receipt.key_sha256)
            or mutation.receipt_id != public_receipt.key_sha256
        ):
            self._closed = True
            raise ProjectStorageError(
                ProjectStorageErrorCode.internal,
                "public receipt identity disagrees with the staged SQLite command",
            )
        timeout_ms = (
            max(1, int(mutation.lock_wait_timeout * 1000))
            if mutation.lock_wait_timeout
            else DEFAULT_BUSY_TIMEOUT_MS
        )
        created_blobs: list[Path] = []
        connection: sqlite3.Connection | None = None
        committed = False
        commit_outcome_ambiguous = False
        try:
            if _maintenance_marker_present(self._repository.root):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.recovery_required,
                    "SQLite project is fenced by a maintenance marker",
                )
            with self._repository.connections.connect(
                writable=True, busy_timeout_ms=timeout_ms
            ) as active:
                connection = active
                active.execute("BEGIN IMMEDIATE")
                self._inject("after_begin")
                if _maintenance_marker_present(self._repository.root):
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.recovery_required,
                        "SQLite project is fenced by a maintenance marker",
                    )
                maintenance = active.execute(
                    "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
                ).fetchone()
                if maintenance is None or str(maintenance["maintenance_state"]) != "ready":
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.recovery_required,
                        "SQLite project is fenced by a maintenance operation",
                    )
                replay = active.execute(
                    "SELECT receipt_id, project_uuid, actor, result_revision_sha256, "
                    "status, result_json FROM receipts WHERE operation_id = ?",
                    (mutation.operation_id,),
                ).fetchone()
                if replay is not None:
                    active.execute("ROLLBACK")
                    self._closed = True
                    return _validated_replay_result(
                        replay,
                        mutation=mutation,
                        public_record=public_record,
                    )
                current = _snapshot_from_connection(active)
                if mutation.expected_revision.sha256 != current.semantic_state_digest:
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.stale_revision,
                        "project state changed before the command could commit",
                    )
                created_blobs = _materialize_target_blobs(
                    self._repository,
                    current=current,
                    target=mutation.target,
                    supplied=mutation.blob_payloads,
                )
                self._inject("after_blob_stage")
                project_revision = _project_revision(active) + 1
                _write_snapshot(
                    active,
                    identity=self._repository.identity(),
                    snapshot=mutation.target,
                    project_revision=project_revision,
                    operation_id=mutation.operation_id,
                )
                self._inject("after_state_write")
                changed = _changed_entity_refs(current, mutation.target)
                result_payload: dict[str, object] = {
                    "revision": mutation.target.semantic_state_digest,
                    "changed_entities": [
                        {
                            "entity_type": item.entity_type,
                            "technical_id": item.technical_id,
                        }
                        for item in changed
                    ],
                    "receipt_id": mutation.receipt_id,
                }
                if public_receipt is not None:
                    result_payload["public_receipt"] = public_receipt.to_payload()
                    assert public_record is not None
                    result_payload["public_receipt_documents"] = (
                        _encode_public_receipt_documents(public_record)
                    )
                now = _utc_now()
                active.execute(
                    "INSERT INTO receipts(operation_id, receipt_id, project_uuid, actor, "
                    "expected_revision_sha256, result_revision_sha256, status, result_json, "
                    "created_at) VALUES (?, ?, ?, ?, ?, ?, 'applied', ?, ?)",
                    (
                        mutation.operation_id,
                        mutation.receipt_id,
                        mutation.target.project_uuid,
                        mutation.actor,
                        mutation.expected_revision.sha256,
                        mutation.target.semantic_state_digest,
                        _json_text(result_payload),
                        now,
                    ),
                )
                active.execute(
                    "INSERT INTO operation_records(operation_id, project_uuid, operation_kind, "
                    "status, started_at, completed_at) VALUES (?, ?, 'project-state-mutation', "
                    "'applied', ?, ?)",
                    (mutation.operation_id, mutation.target.project_uuid, now, now),
                )
                active.execute(
                    "DELETE FROM operation_records WHERE sequence IN ("
                    "SELECT sequence FROM operation_records ORDER BY sequence DESC LIMIT -1 OFFSET 1000)"
                )
                self._inject("before_commit")
                if _maintenance_marker_present(self._repository.root):
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.recovery_required,
                        "SQLite project became fenced during the command",
                    )
                try:
                    active.execute("COMMIT")
                except Exception:
                    # DB-API can report a lost acknowledgement after SQLite
                    # has durably ended the transaction. In that case the
                    # receipt and blob references may already be committed;
                    # never delete their bytes as if rollback were certain.
                    try:
                        commit_outcome_ambiguous = not active.in_transaction
                    except (AttributeError, sqlite3.Error):
                        commit_outcome_ambiguous = True
                    raise
                committed = True
                connection = None
                self._inject("after_commit")
        except ProjectStorageError as exc:
            _rollback_if_open(connection)
            if not committed and not commit_outcome_ambiguous:
                _remove_created_blobs(created_blobs)
            self._closed = True
            if commit_outcome_ambiguous:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite commit acknowledgement was lost; retry the exact operation",
                    diagnostic=str(exc),
                ) from exc
            raise
        except (OSError, ValueError, sqlite3.Error) as exc:
            _rollback_if_open(connection)
            if not committed and not commit_outcome_ambiguous:
                _remove_created_blobs(created_blobs)
            self._closed = True
            if commit_outcome_ambiguous:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite commit acknowledgement was lost; retry the exact operation",
                    diagnostic=str(exc),
                ) from exc
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite project-state command rolled back",
                diagnostic=str(exc),
            ) from exc
        self._closed = True
        # COMMIT and its receipt are atomic. A later serialized writer may
        # legitimately advance the global snapshot before this caller resumes
        # (for example while an after-commit hook is paused), so rereading the
        # latest project state here would falsely report this durable commit as
        # failed. Return the revision recorded by this transaction instead.
        return ProjectStateCommitResult(
            status="applied",
            operation_id=mutation.operation_id,
            revision=ProjectStateRevision(mutation.target.semantic_state_digest),
            changed_entities=changed,
            receipt_id=mutation.receipt_id,
        )

    def rollback(self) -> None:
        self._mutation = None
        self._public_mutation = None
        self._closed = True

    def __enter__(self) -> SQLiteProjectUnitOfWork:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc is not None and not self._closed:
            self.rollback()

    def _inject(self, stage: str) -> None:
        if self.failure_injector is not None:
            self.failure_injector(stage)


def create_sqlite_database(
    path: Path,
    *,
    identity: ProjectIdentity,
    snapshot: CanonicalMemorySnapshot,
    public_receipts: Iterable[SQLitePublicMutationRecord] = (),
    failure_injector: FailureInjector | None = None,
) -> None:
    _validate_target_snapshot(snapshot)
    if identity.project_uuid.value != snapshot.project_uuid:
        raise ProjectStorageError(
            ProjectStorageErrorCode.identity_mismatch,
            "SQLite initialization identity disagrees with canonical state",
        )
    factory = SQLiteConnectionFactory(path)
    factory.prepare_parent()
    if path.exists():
        raise ProjectStorageError(
            ProjectStorageErrorCode.configuration_contradiction,
            "SQLite initialization refuses to overwrite an existing database",
        )
    try:
        capabilities = factory.detect_capabilities()
        with factory.connect(writable=True) as connection:
            if not capabilities.foreign_keys or capabilities.journal_mode != "wal":
                raise ProjectStorageError(
                    ProjectStorageErrorCode.unsupported_capability,
                    "SQLite runtime cannot enforce the required durability configuration",
                )
            if failure_injector is not None:
                failure_injector("before_schema")
            connection.executescript(SQLITE_SCHEMA_V1)
            connection.execute(f"PRAGMA application_id = {SQLITE_APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION}")
            now = _utc_now()
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO schema_migrations(version, contract, ddl_sha256, applied_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    SQLITE_SCHEMA_VERSION,
                    SQLITE_SCHEMA_CONTRACT,
                    SQLITE_SCHEMA_V1_SHA256,
                    now,
                ),
            )
            _write_snapshot(
                connection,
                identity=identity,
                snapshot=snapshot,
                project_revision=1,
                operation_id="sqlite-bootstrap-v1",
            )
            for record in public_receipts:
                _insert_public_mutation_receipt(
                    connection,
                    record=record,
                    project_uuid=snapshot.project_uuid,
                    expected_revision=snapshot.semantic_state_digest,
                    result_revision=snapshot.semantic_state_digest,
                )
            if failure_injector is not None:
                failure_injector("before_schema_commit")
            connection.execute("COMMIT")
    except Exception:
        path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm", "-journal"):
            path.with_name(path.name + suffix).unlink(missing_ok=True)
        raise


def _insert_public_mutation_receipt(
    connection: sqlite3.Connection,
    *,
    record: SQLitePublicMutationRecord,
    project_uuid: str,
    expected_revision: str,
    result_revision: str,
) -> None:
    receipt = record.receipt
    operation_id = sqlite_public_receipt_operation_id(receipt.key_sha256)
    now = _utc_now()
    result_payload = {
        "revision": result_revision,
        "changed_entities": [],
        "receipt_id": receipt.key_sha256,
        "public_receipt": receipt.to_payload(),
        "public_receipt_documents": _encode_public_receipt_documents(record),
    }
    connection.execute(
        "INSERT INTO receipts(operation_id, receipt_id, project_uuid, actor, "
        "expected_revision_sha256, result_revision_sha256, status, result_json, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?, 'applied', ?, ?)",
        (
            operation_id,
            receipt.key_sha256,
            project_uuid,
            receipt.actor,
            expected_revision,
            result_revision,
            _json_text(result_payload),
            now,
        ),
    )
    connection.execute(
        "INSERT INTO operation_records(operation_id, project_uuid, operation_kind, "
        "status, started_at, completed_at) "
        "VALUES (?, ?, 'public-domain-mutation', 'applied', ?, ?)",
        (operation_id, project_uuid, now, now),
    )


def _write_snapshot(
    connection: sqlite3.Connection,
    *,
    identity: ProjectIdentity,
    snapshot: CanonicalMemorySnapshot,
    project_revision: int,
    operation_id: str,
) -> None:
    _validate_target_snapshot(snapshot)
    if identity.project_uuid.value != snapshot.project_uuid:
        raise ProjectStorageError(
            ProjectStorageErrorCode.identity_mismatch,
            "SQLite identity disagrees with canonical state",
        )
    now = _utc_now()
    remote = identity.remote_binding
    connection.execute(
        "INSERT INTO projects(project_uuid, display_name, mode, replica_id, remote_server_id, "
        "remote_project_id, policy_version, project_revision, current_revision_sha256, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_uuid) DO UPDATE SET display_name=excluded.display_name, "
        "mode=excluded.mode, replica_id=excluded.replica_id, "
        "remote_server_id=excluded.remote_server_id, remote_project_id=excluded.remote_project_id, "
        "policy_version=excluded.policy_version, project_revision=excluded.project_revision, "
        "current_revision_sha256=excluded.current_revision_sha256, updated_at=excluded.updated_at",
        (
            identity.project_uuid.value,
            identity.display_name,
            identity.mode.value,
            identity.replica_id.value if identity.replica_id is not None else None,
            remote.server_instance_id.value if remote is not None else None,
            remote.remote_project_id.value if remote is not None else None,
            identity.policy_version,
            project_revision,
            snapshot.semantic_state_digest,
            now,
            now,
        ),
    )
    for table in (
        "blob_references",
        "structure_assignments",
        "project_authority",
        "entity_relations",
        "entities",
        "project_lineage",
        "blobs",
    ):
        connection.execute(f"DELETE FROM {table}")
    for ordinal, item in enumerate(snapshot.lineage):
        source_revision = item.get("source_revision")
        connection.execute(
            "INSERT INTO project_lineage(project_uuid, ordinal, relation, source_project_uuid, "
            "source_revision_sha256, visibility) VALUES (?, ?, ?, ?, ?, ?)",
            (
                snapshot.project_uuid,
                ordinal,
                str(item.get("relation") or ""),
                str(item.get("source_project_uuid") or ""),
                str(source_revision.get("sha256") if isinstance(source_revision, Mapping) else ""),
                str(item.get("visibility") or ""),
            ),
        )
    for entity in snapshot.entities:
        lifecycle = _entity_lifecycle(entity)
        digest = semantic_sha256(entity.to_dict())
        connection.execute(
            "INSERT INTO entities(technical_id, project_uuid, entity_type, human_key, "
            "entity_version, last_project_revision, payload_schema, payload_schema_version, "
            "payload_json, semantic_digest, lifecycle_state, tombstone, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
            (
                entity.technical_id,
                snapshot.project_uuid,
                entity.entity_type,
                entity.human_key,
                entity.entity_version,
                project_revision,
                "p2p-canonical-entity-payload/v1",
                _json_text(entity.payload),
                digest,
                lifecycle,
                int(entity.tombstone),
                now,
                now,
            ),
        )
        connection.execute(
            "INSERT INTO entity_revisions(project_uuid, project_revision, technical_id, "
            "entity_version, semantic_digest, operation_id, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                snapshot.project_uuid,
                project_revision,
                entity.technical_id,
                entity.entity_version,
                digest,
                operation_id,
                now,
            ),
        )
    for relation in snapshot.relations:
        connection.execute(
            "INSERT INTO entity_relations(relation_id, project_uuid, relation_type, "
            "source_entity, target_entity, payload_json, semantic_digest, last_project_revision) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                relation.relation_id,
                snapshot.project_uuid,
                relation.relation_type,
                relation.source_entity,
                relation.target_entity,
                _json_text(relation.payload),
                semantic_sha256(relation.to_dict()),
                project_revision,
            ),
        )
    for blob in snapshot.blobs:
        connection.execute(
            "INSERT INTO blobs(digest, size, media_type, integrity_state, verified_at) "
            "VALUES (?, ?, ?, 'verified', ?)",
            (blob.digest, blob.size, blob.media_type, now),
        )
    known_blobs = {item.digest for item in snapshot.blobs}
    for entity in snapshot.entities:
        for digest in sorted(managed_blob_references(entity.payload)):
            if digest not in known_blobs:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "canonical entity references an unknown managed blob",
                )
            connection.execute(
                "INSERT INTO blob_references(entity_id, digest) VALUES (?, ?)",
                (entity.technical_id, digest),
            )
        for section_id, assignment_kind in _structure_assignments(entity.payload):
            connection.execute(
                "INSERT OR IGNORE INTO structure_assignments(project_uuid, entity_id, "
                "section_id, assignment_kind) VALUES (?, ?, ?, ?)",
                (snapshot.project_uuid, entity.technical_id, section_id, assignment_kind),
            )
    authority = next(
        (item for item in snapshot.entities if item.technical_id == "project:authority"), None
    )
    if authority is not None:
        connection.execute(
            "INSERT INTO project_authority(project_uuid, authority_entity, authority_epoch, "
            "payload_json, last_project_revision) VALUES (?, ?, ?, ?, ?)",
            (
                snapshot.project_uuid,
                authority.technical_id,
                _find_positive_int(authority.payload, {"authority_epoch", "generation"}),
                _json_text(authority.payload),
                project_revision,
            ),
        )
    connection.execute(
        "INSERT INTO storage_metadata(singleton, contract, schema_version, project_uuid, "
        "memory_schema, domain_contract, source_revision_kind, source_revision_value, "
        "semantic_state_digest, blob_manifest_digest, maintenance_state, updated_at) "
        "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?) "
        "ON CONFLICT(singleton) DO UPDATE SET project_uuid=excluded.project_uuid, "
        "memory_schema=excluded.memory_schema, domain_contract=excluded.domain_contract, "
        "source_revision_kind=excluded.source_revision_kind, "
        "source_revision_value=excluded.source_revision_value, "
        "semantic_state_digest=excluded.semantic_state_digest, "
        "blob_manifest_digest=excluded.blob_manifest_digest, maintenance_state='ready', "
        "updated_at=excluded.updated_at",
        (
            SQLITE_SCHEMA_CONTRACT,
            SQLITE_SCHEMA_VERSION,
            snapshot.project_uuid,
            snapshot.memory_schema,
            snapshot.domain_contract,
            str(snapshot.source_revision.get("kind") or "local"),
            str(snapshot.source_revision.get("value") or snapshot.semantic_state_digest),
            snapshot.semantic_state_digest,
            snapshot.blob_manifest_digest,
            now,
        ),
    )


def _snapshot_from_connection(connection: sqlite3.Connection) -> CanonicalMemorySnapshot:
    metadata = connection.execute(
        "SELECT * FROM storage_metadata WHERE singleton = 1"
    ).fetchone()
    if metadata is None:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite canonical metadata is missing",
        )
    entities = tuple(
        _entity_from_row(row)
        for row in connection.execute(
            "SELECT entity_type, technical_id, human_key, entity_version, payload_json, tombstone "
            "FROM entities ORDER BY entity_type, technical_id"
        )
    )
    relations = tuple(
        CanonicalRelation(
            relation_type=str(row["relation_type"]),
            relation_id=str(row["relation_id"]),
            source_entity=str(row["source_entity"]),
            target_entity=str(row["target_entity"]),
            payload=_json_mapping(str(row["payload_json"]), "relation payload"),
        )
        for row in connection.execute(
            "SELECT relation_type, relation_id, source_entity, target_entity, payload_json "
            "FROM entity_relations ORDER BY relation_type, relation_id"
        )
    )
    lineage = tuple(
        {
            "relation": str(row["relation"]),
            "source_project_uuid": str(row["source_project_uuid"]),
            "source_revision": {
                "namespace": "source_memory",
                "sha256": str(row["source_revision_sha256"]),
            },
            "visibility": str(row["visibility"]),
        }
        for row in connection.execute(
            "SELECT relation, source_project_uuid, source_revision_sha256, visibility "
            "FROM project_lineage ORDER BY ordinal"
        )
    )
    blobs = tuple(
        ManagedBlob(
            digest=str(row["digest"]),
            size=int(row["size"]),
            media_type=str(row["media_type"]),
        )
        for row in connection.execute(
            "SELECT digest, size, media_type FROM blobs ORDER BY digest"
        )
    )
    snapshot = CanonicalMemorySnapshot(
        project_uuid=str(metadata["project_uuid"]),
        entities=entities,
        relations=relations,
        lineage=lineage,
        blobs=blobs,
        semantic_state_digest=str(metadata["semantic_state_digest"]),
        blob_manifest_digest=str(metadata["blob_manifest_digest"]),
        source_revision={
            "kind": str(metadata["source_revision_kind"]),
            "value": str(metadata["source_revision_value"]),
        },
        memory_schema=int(metadata["memory_schema"]),
        domain_contract=str(metadata["domain_contract"]),
    )
    _validate_target_snapshot(snapshot)
    return snapshot


def _entity_from_row(row: sqlite3.Row) -> CanonicalEntity:
    return CanonicalEntity(
        entity_type=str(row["entity_type"]),
        technical_id=str(row["technical_id"]),
        human_key=str(row["human_key"]) if row["human_key"] is not None else None,
        entity_version=int(row["entity_version"]),
        payload=_json_mapping(str(row["payload_json"]), "entity payload"),
        tombstone=bool(row["tombstone"]),
    )


def _json_mapping(raw: str, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            f"SQLite {label} is not valid canonical JSON",
            diagnostic=str(exc),
        ) from exc
    if not isinstance(value, dict):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            f"SQLite {label} is not a JSON object",
        )
    return value


def _validate_target_snapshot(snapshot: CanonicalMemorySnapshot) -> None:
    digest = snapshot_digest(snapshot)
    if digest != snapshot.semantic_state_digest:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "canonical snapshot semantic digest is invalid",
        )
    blob_digest = semantic_sha256([item.to_dict() for item in snapshot.blobs])
    if blob_digest != snapshot.blob_manifest_digest:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "canonical snapshot blob manifest digest is invalid",
        )
    technical_ids = [item.technical_id for item in snapshot.entities]
    if len(technical_ids) != len(set(technical_ids)):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "canonical snapshot contains duplicate entity identities",
        )
    known = set(technical_ids)
    if any(
        item.source_entity not in known or item.target_entity not in known
        for item in snapshot.relations
    ):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "canonical snapshot contains a relation with an unknown endpoint",
        )


def _materialize_target_blobs(
    repository: SQLiteProjectStateRepository,
    *,
    current: CanonicalMemorySnapshot,
    target: CanonicalMemorySnapshot,
    supplied: Mapping[str, bytes],
) -> list[Path]:
    current_by_digest = {item.digest: item for item in current.blobs}
    blob_store = SQLiteBlobStore(repository)
    created: list[Path] = []
    for blob in target.blobs:
        content = supplied.get(blob.digest)
        if content is None and blob.digest in current_by_digest:
            content = blob_store.read(blob.digest)
        if content is None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "command target references a managed blob without payload",
            )
        raw = blob.digest.removeprefix("sha256:")
        if len(content) != blob.size or hashlib.sha256(content).hexdigest() != raw:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "managed blob payload does not match its metadata",
            )
        if install_sqlite_blob_bytes(repository.root, blob.digest, content):
            created.append(sqlite_blob_path(repository.root, blob.digest))
    return created


def _remove_created_blobs(paths: Iterable[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
            sync_directory(path.parent)
        except OSError:
            pass


def _rollback_if_open(connection: sqlite3.Connection | None) -> None:
    if connection is None:
        return
    try:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
    except sqlite3.Error:
        # Closing an sqlite3 connection already rolls an open transaction back.
        pass


def _project_revision(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT project_revision FROM projects").fetchone()
    if row is None:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite project revision counter is missing",
        )
    return int(row["project_revision"])


def _changed_entity_refs(
    before: CanonicalMemorySnapshot,
    after: CanonicalMemorySnapshot,
) -> tuple[ProjectEntityRef, ...]:
    old = {(item.entity_type, item.technical_id): item for item in before.entities}
    new = {(item.entity_type, item.technical_id): item for item in after.entities}
    return tuple(
        ProjectEntityRef(*key)
        for key in sorted(set(old) | set(new))
        if old.get(key) != new.get(key)
    )


def _entity_lifecycle(entity: CanonicalEntity) -> str:
    if entity.tombstone:
        return "retired"
    document = entity.payload.get("document")
    if isinstance(document, Mapping):
        status = str(document.get("status") or "").lower()
        if status in {"retired", "archived", "withdrawn"}:
            return "retired"
        if status in {"unclassified", "unassigned"}:
            return "unclassified"
    return "current"


def _find_positive_int(value: object, keys: set[str]) -> int | None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in keys and isinstance(nested, int) and not isinstance(nested, bool):
                return nested if nested > 0 else None
            found = _find_positive_int(nested, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_positive_int(nested, keys)
            if found is not None:
                return found
    return None


def _structure_assignments(value: object) -> tuple[tuple[str, str], ...]:
    assignments: set[tuple[str, str]] = set()

    def visit(nested: object, parent: str = "scope") -> None:
        if isinstance(nested, Mapping):
            for key, item in nested.items():
                if key in {"section_id", "primary_section_id"} and isinstance(item, str) and item:
                    assignments.add((item, parent))
                elif key == "section_ids" and isinstance(item, list):
                    assignments.update((section, parent) for section in item if isinstance(section, str) and section)
                else:
                    visit(item, key)
        elif isinstance(nested, list):
            for item in nested:
                visit(item, parent)

    visit(value)
    return tuple(sorted(assignments))

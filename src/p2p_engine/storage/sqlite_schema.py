from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

SQLITE_ADAPTER = "sqlite"
SQLITE_DATABASE_PATH = ".p2p/local/project.sqlite3"
SQLITE_MAINTENANCE_MARKER = ".p2p/local/sqlite-maintenance.json"
SQLITE_SCHEMA_CONTRACT = "p2p-sqlite-project-state/v1"
SQLITE_SCHEMA_VERSION = 1
SQLITE_APPLICATION_ID = 0x50325032

SQLITE_SCHEMA_V1 = """
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    contract TEXT NOT NULL,
    ddl_sha256 TEXT NOT NULL CHECK (length(ddl_sha256) = 64),
    applied_at TEXT NOT NULL
) STRICT;

CREATE TABLE projects (
    project_uuid TEXT PRIMARY KEY CHECK (length(project_uuid) = 36),
    display_name TEXT NOT NULL CHECK (length(display_name) BETWEEN 1 AND 512),
    mode TEXT NOT NULL CHECK (
        mode IN ('standalone', 'linked', 'remote-only', 'link-suspended', 'detached')
    ),
    replica_id TEXT,
    remote_server_id TEXT,
    remote_project_id TEXT,
    policy_version INTEGER NOT NULL CHECK (policy_version > 0),
    project_revision INTEGER NOT NULL CHECK (project_revision > 0),
    current_revision_sha256 TEXT NOT NULL CHECK (length(current_revision_sha256) = 64),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (mode = 'remote-only' AND replica_id IS NULL)
        OR (mode <> 'remote-only' AND replica_id IS NOT NULL)
    ),
    CHECK (
        (mode IN ('linked', 'remote-only', 'link-suspended')
         AND remote_server_id IS NOT NULL AND remote_project_id IS NOT NULL)
        OR
        (mode NOT IN ('linked', 'remote-only', 'link-suspended')
         AND remote_server_id IS NULL AND remote_project_id IS NULL)
    )
) STRICT;

CREATE TABLE storage_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    contract TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK (schema_version > 0),
    project_uuid TEXT NOT NULL UNIQUE REFERENCES projects(project_uuid) ON DELETE CASCADE,
    memory_schema INTEGER NOT NULL CHECK (memory_schema > 0),
    domain_contract TEXT NOT NULL,
    source_revision_kind TEXT NOT NULL,
    source_revision_value TEXT NOT NULL CHECK (length(source_revision_value) = 64),
    semantic_state_digest TEXT NOT NULL CHECK (length(semantic_state_digest) = 64),
    blob_manifest_digest TEXT NOT NULL CHECK (length(blob_manifest_digest) = 64),
    maintenance_state TEXT NOT NULL DEFAULT 'ready'
        CHECK (maintenance_state IN ('ready', 'migrating', 'restoring', 'recovery-required')),
    updated_at TEXT NOT NULL
) STRICT;

CREATE TABLE project_lineage (
    project_uuid TEXT NOT NULL REFERENCES projects(project_uuid) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    relation TEXT NOT NULL CHECK (relation IN ('derived_from', 'detached_from', 'restored_from_bundle')),
    source_project_uuid TEXT NOT NULL CHECK (length(source_project_uuid) = 36),
    source_revision_sha256 TEXT NOT NULL CHECK (length(source_revision_sha256) = 64),
    visibility TEXT NOT NULL CHECK (visibility IN ('preserved', 'private')),
    PRIMARY KEY (project_uuid, ordinal),
    UNIQUE (project_uuid, relation, source_project_uuid, source_revision_sha256)
) STRICT;

CREATE TABLE entities (
    technical_id TEXT PRIMARY KEY,
    project_uuid TEXT NOT NULL REFERENCES projects(project_uuid) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    human_key TEXT,
    entity_version INTEGER NOT NULL CHECK (entity_version > 0),
    last_project_revision INTEGER NOT NULL CHECK (last_project_revision > 0),
    payload_schema TEXT NOT NULL,
    payload_schema_version INTEGER NOT NULL CHECK (payload_schema_version > 0),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    semantic_digest TEXT NOT NULL CHECK (length(semantic_digest) = 64),
    lifecycle_state TEXT NOT NULL DEFAULT 'current'
        CHECK (lifecycle_state IN ('current', 'retired', 'unclassified')),
    tombstone INTEGER NOT NULL DEFAULT 0 CHECK (tombstone IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;

CREATE TABLE entity_revisions (
    project_uuid TEXT NOT NULL REFERENCES projects(project_uuid) ON DELETE CASCADE,
    project_revision INTEGER NOT NULL CHECK (project_revision > 0),
    technical_id TEXT NOT NULL,
    entity_version INTEGER NOT NULL CHECK (entity_version > 0),
    semantic_digest TEXT NOT NULL CHECK (length(semantic_digest) = 64),
    operation_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (project_uuid, project_revision, technical_id)
) STRICT;

CREATE TABLE entity_relations (
    relation_id TEXT PRIMARY KEY,
    project_uuid TEXT NOT NULL REFERENCES projects(project_uuid) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    source_entity TEXT NOT NULL REFERENCES entities(technical_id) ON DELETE CASCADE,
    target_entity TEXT NOT NULL REFERENCES entities(technical_id) ON DELETE CASCADE,
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    semantic_digest TEXT NOT NULL CHECK (length(semantic_digest) = 64),
    last_project_revision INTEGER NOT NULL CHECK (last_project_revision > 0)
) STRICT;

CREATE TABLE project_authority (
    project_uuid TEXT PRIMARY KEY REFERENCES projects(project_uuid) ON DELETE CASCADE,
    authority_entity TEXT NOT NULL REFERENCES entities(technical_id) ON DELETE CASCADE,
    authority_epoch INTEGER,
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    last_project_revision INTEGER NOT NULL CHECK (last_project_revision > 0)
) STRICT;

CREATE TABLE structure_assignments (
    project_uuid TEXT NOT NULL REFERENCES projects(project_uuid) ON DELETE CASCADE,
    entity_id TEXT NOT NULL REFERENCES entities(technical_id) ON DELETE CASCADE,
    section_id TEXT NOT NULL,
    assignment_kind TEXT NOT NULL,
    PRIMARY KEY (project_uuid, entity_id, section_id, assignment_kind)
) STRICT;

CREATE TABLE blobs (
    digest TEXT PRIMARY KEY CHECK (length(digest) = 71 AND substr(digest, 1, 7) = 'sha256:'),
    size INTEGER NOT NULL CHECK (size >= 0),
    media_type TEXT NOT NULL,
    integrity_state TEXT NOT NULL DEFAULT 'verified'
        CHECK (integrity_state IN ('verified', 'missing', 'corrupt')),
    verified_at TEXT NOT NULL
) STRICT;

CREATE TABLE blob_references (
    entity_id TEXT NOT NULL REFERENCES entities(technical_id) ON DELETE CASCADE,
    digest TEXT NOT NULL REFERENCES blobs(digest) ON DELETE RESTRICT,
    PRIMARY KEY (entity_id, digest)
) STRICT;

CREATE TABLE receipts (
    operation_id TEXT PRIMARY KEY,
    receipt_id TEXT NOT NULL,
    project_uuid TEXT NOT NULL REFERENCES projects(project_uuid) ON DELETE CASCADE,
    actor TEXT NOT NULL,
    expected_revision_sha256 TEXT NOT NULL CHECK (length(expected_revision_sha256) = 64),
    result_revision_sha256 TEXT NOT NULL CHECK (length(result_revision_sha256) = 64),
    status TEXT NOT NULL CHECK (status IN ('applied', 'replayed')),
    result_json TEXT NOT NULL CHECK (json_valid(result_json)),
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE operation_records (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL UNIQUE,
    project_uuid TEXT NOT NULL REFERENCES projects(project_uuid) ON DELETE CASCADE,
    operation_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    diagnostic_code TEXT NOT NULL DEFAULT ''
) STRICT;

CREATE INDEX idx_entities_kind_key
    ON entities(project_uuid, entity_type, human_key, technical_id);
CREATE INDEX idx_entities_revision
    ON entities(project_uuid, last_project_revision, technical_id);
CREATE INDEX idx_relations_source
    ON entity_relations(project_uuid, source_entity, relation_type);
CREATE INDEX idx_relations_target
    ON entity_relations(project_uuid, target_entity, relation_type);
CREATE INDEX idx_structure_section
    ON structure_assignments(project_uuid, section_id, assignment_kind);
CREATE INDEX idx_receipts_revision
    ON receipts(project_uuid, result_revision_sha256);
CREATE INDEX idx_operations_recent
    ON operation_records(project_uuid, sequence DESC);
CREATE INDEX idx_blob_references_digest
    ON blob_references(digest, entity_id);
"""

SQLITE_SCHEMA_V1_SHA256 = hashlib.sha256(SQLITE_SCHEMA_V1.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SQLiteDatabaseHeader:
    project_uuid: str
    schema_version: int
    contract: str
    semantic_state_digest: str
    maintenance_state: str


def read_sqlite_database_header(path: Path) -> SQLiteDatabaseHeader:
    if path.is_symlink() or not path.is_file():
        raise ValueError("P2P_SQLITE_DATABASE_MISSING: SQLite project database is missing")
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=1.0)
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT project_uuid, schema_version, contract, "
            "semantic_state_digest, maintenance_state "
            "FROM storage_metadata WHERE singleton = 1"
        ).fetchone()
        application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    except sqlite3.Error as exc:
        raise ValueError(
            f"P2P_SQLITE_DATABASE_INVALID: SQLite metadata cannot be read: {exc}"
        ) from exc
    finally:
        if "connection" in locals():
            connection.close()
    if row is None or application_id != SQLITE_APPLICATION_ID:
        raise ValueError("P2P_SQLITE_DATABASE_INVALID: database identity is unsupported")
    schema_version = int(row["schema_version"])
    if schema_version != user_version:
        raise ValueError("P2P_SQLITE_SCHEMA_MISMATCH: metadata and user_version disagree")
    return SQLiteDatabaseHeader(
        project_uuid=str(row["project_uuid"]),
        schema_version=schema_version,
        contract=str(row["contract"]),
        semantic_state_digest=str(row["semantic_state_digest"]),
        maintenance_state=str(row["maintenance_state"]),
    )

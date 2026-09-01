from __future__ import annotations

import ntpath
import os
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from p2p_engine.core.project_state_storage import (
    ProjectStorageError,
    ProjectStorageErrorCode,
)
from p2p_engine.storage.path_safety import (
    UnsafeProjectStoragePath,
    lexical_absolute,
    validate_confined_project_path,
)
from p2p_engine.storage.sqlite_schema import SQLITE_APPLICATION_ID

MINIMUM_SQLITE_VERSION = (3, 37, 0)
DEFAULT_BUSY_TIMEOUT_MS = 1_000
UNSAFE_MULTI_HOST_FILESYSTEMS = frozenset(
    {
        "9p",
        "afs",
        "ceph",
        "cifs",
        "fuse.sshfs",
        "glusterfs",
        "lustre",
        "nfs",
        "nfs4",
        "smb3",
        "windows-remote",
    }
)


@dataclass(frozen=True)
class SQLiteRuntimeCapabilities:
    sqlite_version: str
    json_functions: bool
    fts5: bool
    online_backup: bool
    journal_mode: str
    synchronous: str
    foreign_keys: bool
    busy_timeout_ms: int
    filesystem_type: str

    def to_dict(self) -> dict[str, object]:
        return {
            "sqlite_version": self.sqlite_version,
            "json_functions": self.json_functions,
            "fts5": self.fts5,
            "online_backup": self.online_backup,
            "journal_mode": self.journal_mode,
            "synchronous": self.synchronous,
            "foreign_keys": self.foreign_keys,
            "busy_timeout_ms": self.busy_timeout_ms,
            "filesystem_type": self.filesystem_type,
        }


def local_filesystem_type(path: Path) -> str:
    """Best-effort local mount detection without shelling out."""
    if os.name == "nt":
        return _windows_filesystem_type(path)
    mountinfo = Path("/proc/self/mountinfo")
    if not mountinfo.is_file():
        return "unknown"
    target = _nearest_existing(path).resolve()
    best: tuple[int, str] | None = None
    try:
        lines = mountinfo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "unknown"
    for line in lines:
        fields = line.split()
        try:
            separator = fields.index("-")
            mount_point = Path(_unescape_mount(fields[4])).resolve()
            filesystem = fields[separator + 1].lower()
        except (ValueError, IndexError, OSError):
            continue
        try:
            target.relative_to(mount_point)
        except ValueError:
            continue
        score = len(mount_point.parts)
        if best is None or score > best[0]:
            best = (score, filesystem)
    return best[1] if best is not None else "unknown"


def _windows_filesystem_type(
    path: os.PathLike[str],
    *,
    drive_type_resolver: Callable[[str], int] | None = None,
) -> str:
    value = os.fspath(path).replace("/", "\\")
    lowered = value.lower()
    if lowered.startswith("\\\\?\\unc\\") or (
        value.startswith("\\\\") and not lowered.startswith("\\\\?\\")
    ):
        return "windows-remote"
    drive, _tail = ntpath.splitdrive(value)
    if not drive:
        return "windows-local-or-unknown"
    resolver = drive_type_resolver or _windows_drive_type
    try:
        drive_type = resolver(f"{drive}\\")
    except OSError:
        return "windows-local-or-unknown"
    return "windows-remote" if drive_type == 4 else "windows-local"


def _windows_drive_type(root: str) -> int:
    import ctypes

    get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
    get_drive_type.argtypes = (ctypes.c_wchar_p,)
    get_drive_type.restype = ctypes.c_uint
    return int(get_drive_type(root))


def _nearest_existing(path: Path) -> Path:
    candidate = path.resolve(strict=False)
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _unescape_mount(value: str) -> str:
    return (
        value.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


class SQLiteConnectionFactory:
    def __init__(
        self,
        path: Path,
        *,
        project_root: Path | None = None,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
        filesystem_detector: Callable[[Path], str] = local_filesystem_type,
    ) -> None:
        self.path = lexical_absolute(path)
        self.project_root = project_root.resolve() if project_root is not None else None
        self.busy_timeout_ms = busy_timeout_ms
        self.filesystem_detector = filesystem_detector
        if busy_timeout_ms < 1 or busy_timeout_ms > 60_000:
            raise ValueError("P2P_SQLITE_BUSY_TIMEOUT_INVALID: timeout is outside safe bounds")

    def validate_environment(self) -> str:
        if sqlite3.sqlite_version_info < MINIMUM_SQLITE_VERSION:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "runtime SQLite is older than the supported schema baseline",
                diagnostic=sqlite3.sqlite_version,
            )
        self._validate_database_path(must_exist=False)
        filesystem = self.filesystem_detector(self.path).lower()
        if filesystem in UNSAFE_MULTI_HOST_FILESYSTEMS:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite project state requires a supported single-host local filesystem",
                diagnostic=filesystem,
            )
        return filesystem

    def prepare_parent(self) -> None:
        self.validate_environment()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._validate_database_path(must_exist=False)
        _restrict_permissions(self.path.parent, directory=True)

    @contextmanager
    def connect(
        self,
        *,
        writable: bool,
        busy_timeout_ms: int | None = None,
    ) -> Iterator[sqlite3.Connection]:
        timeout_ms = self.busy_timeout_ms if busy_timeout_ms is None else busy_timeout_ms
        if timeout_ms < 1 or timeout_ms > 60_000:
            raise ValueError("P2P_SQLITE_BUSY_TIMEOUT_INVALID: timeout is outside safe bounds")
        self.validate_environment()
        if writable:
            self.prepare_parent()
            self._validate_database_path(must_exist=False)
            target = str(self.path)
            uri = False
        else:
            self._validate_database_path(must_exist=True)
            target = f"{self.path.as_uri()}?mode=ro"
            uri = True
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                target,
                uri=uri,
                timeout=timeout_ms / 1000,
                isolation_level=None,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {int(timeout_ms)}")
            if writable:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = FULL")
                connection.execute("PRAGMA wal_autocheckpoint = 1000")
            else:
                connection.execute("PRAGMA query_only = ON")
            try:
                connection.execute("PRAGMA trusted_schema = OFF")
            except sqlite3.DatabaseError:  # pragma: no cover - older supported builds.
                pass
            yield connection
        except sqlite3.OperationalError as exc:
            lowered = str(exc).lower()
            if "locked" in lowered or "busy" in lowered:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.busy,
                    "SQLite project writer did not acquire the database within its timeout",
                    diagnostic=str(exc),
                ) from exc
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite project database operation failed",
                diagnostic=str(exc),
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite project database is invalid or corrupt",
                diagnostic=str(exc),
            ) from exc
        finally:
            if connection is not None:
                connection.close()
            if writable and self.path.exists():
                self._validate_database_path(must_exist=True)
                _restrict_permissions(self.path, directory=False)

    def _validate_database_path(self, *, must_exist: bool) -> None:
        root = self.project_root
        if root is None:
            # A direct factory without project context can still reject unsafe
            # leaf/parent indirection; callers that own a project must pass its
            # root to additionally enforce the containment boundary.
            root = _direct_path_validation_root(self.path)
        try:
            validate_confined_project_path(
                root,
                self.path,
                expected="file",
                must_exist=must_exist,
            )
        except UnsafeProjectStoragePath as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite project database path is missing or unsafe",
                diagnostic=str(exc),
            ) from exc

    def detect_capabilities(self) -> SQLiteRuntimeCapabilities:
        filesystem = self.validate_environment()
        with self.connect(writable=True) as connection:
            json_functions = bool(connection.execute("SELECT json_valid('{}')").fetchone()[0])
            options = {
                str(row[0]).upper() for row in connection.execute("PRAGMA compile_options")
            }
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            synchronous_value = int(connection.execute("PRAGMA synchronous").fetchone()[0])
            synchronous = {0: "off", 1: "normal", 2: "full", 3: "extra"}.get(
                synchronous_value, str(synchronous_value)
            )
            foreign_keys = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
        if not json_functions:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "runtime SQLite lacks required canonical JSON validation",
            )
        return SQLiteRuntimeCapabilities(
            sqlite_version=sqlite3.sqlite_version,
            json_functions=json_functions,
            fts5=any(option == "ENABLE_FTS5" for option in options),
            online_backup=hasattr(sqlite3.Connection, "backup"),
            journal_mode=journal_mode,
            synchronous=synchronous,
            foreign_keys=foreign_keys,
            busy_timeout_ms=self.busy_timeout_ms,
            filesystem_type=filesystem,
        )


def validate_sqlite_header(connection: sqlite3.Connection) -> None:
    application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
    if application_id != SQLITE_APPLICATION_ID:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite database does not carry the P2P application identity",
        )


def _restrict_permissions(path: Path, *, directory: bool) -> None:
    if os.name == "nt":
        return
    try:
        path.chmod(0o700 if directory else 0o600)
    except OSError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite storage permissions could not be restricted",
            diagnostic=str(exc),
        ) from exc


def _direct_path_validation_root(path: Path) -> Path:
    """Choose a stable existing ancestor while retaining parent-link checks."""

    candidate = path.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate

from __future__ import annotations

import hashlib
import os
import re
import secrets
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from p2p_engine.core.workspace_schema import (
    LOCK_ABSENT,
    LOCK_ACTIVE,
    LOCK_INVALID,
    LOCK_RECOVERY_OWNED,
    LOCK_STALE,
    WorkspaceTransactionLock,
    WorkspaceTransactionRecoveryResult,
    WorkspaceTransactionRecoveryStatus,
)
from p2p_engine.core.mutation_preview import MutationResult, SourcePrecondition
from p2p_engine.core.mutation_receipts import MUTATION_RECEIPT_ROOT
from p2p_engine.services.candidate_workspace import CandidateWorkspaceView
from p2p_engine.foundation.files import sync_directory, write_bytes_atomic, write_yaml_atomic


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_all(descriptor: int, content: bytes) -> None:
    remaining = memoryview(content)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("workspace transaction lock write made no progress")
        remaining = remaining[written:]


class WorkspaceTransactionLockService:
    def __init__(self, *, root: Path, p2p_dir: Path) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.transaction_root = self.p2p_dir / ".internal" / "workspace-transactions"
        self.transactions_root = self.transaction_root / "transactions"
        self.lock_path = self.transaction_root / "apply.lock"

    def acquire(self, transaction_id: str, *, owner: str) -> WorkspaceTransactionLock:
        _safe_identifier(transaction_id)
        self.transaction_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.transaction_root.chmod(0o700)
        payload = {
            "transaction_id": transaction_id,
            "pid": os.getpid(),
            "acquired_at": utc_now_iso(),
            "owner": owner,
        }
        content = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False).encode("utf-8")
        temporary_path = self.transaction_root / (
            f".apply.lock.{os.getpid()}.{secrets.token_hex(8)}.tmp"
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor: int | None = None
        try:
            descriptor = os.open(temporary_path, flags, 0o600)
            _write_all(descriptor, content)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            try:
                os.link(temporary_path, self.lock_path)
            except FileExistsError as exc:
                status = self.status()
                raise ValueError(
                    "P2P_WORKSPACE_TRANSACTION_LOCKED: workspace transaction lock "
                    f"is {status.state} for transaction "
                    f"{status.transaction_id or 'unknown'}"
                ) from exc
            sync_directory(self.transaction_root)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            temporary_path.unlink(missing_ok=True)
            sync_directory(self.transaction_root)
        return WorkspaceTransactionLock(
            state=LOCK_ACTIVE,
            path=self._relative(self.lock_path),
            transaction_id=transaction_id,
            pid=os.getpid(),
            acquired_at=str(payload["acquired_at"]),
            owner=owner,
        )

    def status(self) -> WorkspaceTransactionLock:
        try:
            payload = yaml.safe_load(self.lock_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return WorkspaceTransactionLock(
                state=LOCK_ABSENT,
                path=self._relative(self.lock_path),
            )
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            return WorkspaceTransactionLock(
                state=LOCK_INVALID,
                path=self._relative(self.lock_path),
                message=f"Cannot parse workspace transaction lock: {exc}",
            )
        if not isinstance(payload, dict):
            return WorkspaceTransactionLock(
                state=LOCK_INVALID,
                path=self._relative(self.lock_path),
                message="Workspace transaction lock payload must be a mapping.",
            )
        transaction_id = str(payload.get("transaction_id") or "")
        pid = payload.get("pid")
        if not transaction_id or isinstance(pid, bool) or not isinstance(pid, int):
            return WorkspaceTransactionLock(
                state=LOCK_INVALID,
                path=self._relative(self.lock_path),
                transaction_id=transaction_id,
                message="Workspace transaction lock is missing transaction_id or pid.",
            )
        transaction_dir = self.transactions_root / transaction_id
        state = LOCK_RECOVERY_OWNED if (transaction_dir / "journal.yml").exists() else (
            LOCK_ACTIVE if _pid_is_running(pid) else LOCK_STALE
        )
        return WorkspaceTransactionLock(
            state=state,
            path=self._relative(self.lock_path),
            transaction_id=transaction_id,
            pid=pid,
            acquired_at=str(payload.get("acquired_at") or ""),
            owner=str(payload.get("owner") or ""),
        )

    def release(self, transaction_id: str) -> None:
        status = self.status()
        if status.state == LOCK_ABSENT:
            return
        if status.transaction_id != transaction_id:
            raise ValueError(
                "Cannot release workspace transaction lock owned by transaction "
                f"{status.transaction_id or 'unknown'}"
            )
        self.lock_path.unlink(missing_ok=False)
        sync_directory(self.transaction_root)

    def require_write_available(self, operation: str, *, transaction_id: str = "") -> None:
        status = self.status()
        if status.state == LOCK_ABSENT:
            return
        if transaction_id and status.transaction_id == transaction_id:
            return
        raise ValueError(
            f"P2P_GOVERNED_WRITE_BLOCKED_BY_TRANSACTION: {operation} is blocked while "
            f"workspace transaction {status.transaction_id or 'unknown'} owns the write lock"
        )

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()


class DurableTransactionFilesystem:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        lock_service: WorkspaceTransactionLockService,
        allowed_project_targets: tuple[str, ...] = (),
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.lock_service = lock_service
        self.allowed_project_targets = frozenset(
            _normalize_project_target(item) for item in allowed_project_targets
        )

    def create_transaction(self, transaction_id: str) -> Path:
        _safe_identifier(transaction_id)
        self.lock_service.transactions_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock_service.transactions_root.chmod(0o700)
        transaction_dir = self.lock_service.transactions_root / transaction_id
        transaction_dir.mkdir(mode=0o700)
        transaction_dir.chmod(0o700)
        for name in ("originals", "candidates"):
            child = transaction_dir / name
            child.mkdir(mode=0o700)
            child.chmod(0o700)
        sync_directory(transaction_dir.parent)
        return transaction_dir

    def target_path(self, relative: str) -> Path:
        normalized = _normalize_target(relative, self.allowed_project_targets)
        live = self.root / normalized
        if live.is_symlink():
            raise ValueError(f"Workspace transaction target cannot be a symlink: {relative}")
        target = (self.root / normalized).resolve(strict=False)
        if normalized not in self.allowed_project_targets and not target.is_relative_to(self.p2p_dir):
            raise ValueError(f"Workspace transaction target escapes .p2p: {relative}")
        current = live.parent
        while current != self.root and current != self.p2p_dir.parent:
            if current.is_symlink():
                raise ValueError(f"Workspace transaction target parent cannot be a symlink: {relative}")
            if current == self.p2p_dir:
                break
            current = current.parent
        return live

    def snapshot_target(self, transaction_dir: Path, relative: str) -> dict[str, object]:
        target = self.target_path(relative)
        if not target.exists():
            return {"exists": False, "physical_sha256": None, "mode": None}
        if not target.is_file():
            raise ValueError(f"Workspace transaction target must be a regular file: {relative}")
        content = target.read_bytes()
        original = transaction_dir / "originals" / relative
        write_bytes_atomic(original, content, mode=0o600)
        return {
            "exists": True,
            "physical_sha256": hashlib.sha256(content).hexdigest(),
            "mode": target.stat().st_mode & 0o777,
        }

    def stage_candidate(self, transaction_dir: Path, relative: str, content: bytes) -> dict[str, object]:
        self.target_path(relative)
        candidate = transaction_dir / "candidates" / relative
        write_bytes_atomic(candidate, content, mode=0o600)
        return {
            "physical_sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
        }

    def read_candidate(self, transaction_dir: Path, relative: str) -> bytes:
        candidate = transaction_dir / "candidates" / _normalize_target(
            relative, self.allowed_project_targets
        )
        if not candidate.is_file() or candidate.is_symlink():
            raise ValueError(f"Missing or unsafe staged candidate: {relative}")
        return candidate.read_bytes()

    def replace_target(self, relative: str, content: bytes, *, mode: int | None = None) -> dict[str, object]:
        target = self.target_path(relative)
        report = write_bytes_atomic(target, content, mode=mode)
        return {
            "physical_sha256": hashlib.sha256(content).hexdigest(),
            "file_synced": report.file_synced,
            "directory_synced": report.directory_synced,
            "directory_sync_supported": report.directory_sync_supported,
        }

    def remove_target(self, relative: str) -> bool:
        target = self.target_path(relative)
        target.unlink(missing_ok=True)
        return sync_directory(target.parent)

    def read_original(self, transaction_dir: Path, relative: str) -> bytes:
        original = transaction_dir / "originals" / _normalize_target(
            relative, self.allowed_project_targets
        )
        if not original.is_file() or original.is_symlink():
            raise ValueError(f"Missing or unsafe transaction original: {relative}")
        return original.read_bytes()

    def write_journal(self, transaction_dir: Path, payload: dict[str, object]) -> None:
        write_yaml_atomic(transaction_dir / "journal.yml", payload)
        sync_directory(transaction_dir)

    def read_journal(self, transaction_dir: Path) -> dict[str, object]:
        path = transaction_dir / "journal.yml"
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Cannot read workspace transaction journal: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError("Workspace transaction journal must be a mapping")
        return value

    def cleanup(self, transaction_dir: Path) -> None:
        if not transaction_dir.resolve().is_relative_to(self.lock_service.transactions_root.resolve()):
            raise ValueError("Refusing to clean a path outside workspace transaction storage")
        shutil.rmtree(transaction_dir)
        sync_directory(transaction_dir.parent)
        try:
            transaction_dir.parent.rmdir()
        except OSError:
            pass


class AtomicMutationWriter:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        lock_service: WorkspaceTransactionLockService | None = None,
        failure_injector=None,
        allowed_project_targets: tuple[str, ...] = (),
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.lock_service = lock_service or WorkspaceTransactionLockService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.filesystem = DurableTransactionFilesystem(
            root=self.root,
            p2p_dir=self.p2p_dir,
            lock_service=self.lock_service,
            allowed_project_targets=allowed_project_targets,
        )
        self.failure_injector = failure_injector

    def apply(
        self,
        *,
        operation_id: str,
        candidates: dict[str, bytes | None],
        sources: tuple[SourcePrecondition, ...],
        preview_token: str,
        actor: str,
        candidate_validator=None,
        lock_wait_timeout: float = 0.0,
    ) -> MutationResult:
        transaction_id = f"mutation-{operation_id.replace(':', '-')}-{os.getpid()}-{hashlib.sha256(preview_token.encode()).hexdigest()[:10]}"
        source_map = {item.path: item for item in sources}
        lock_deadline = time.monotonic() + max(0.0, lock_wait_timeout)
        while True:
            try:
                self.lock_service.acquire(transaction_id, owner=actor)
                break
            except ValueError as exc:
                if time.monotonic() >= lock_deadline:
                    return MutationResult(
                        status="blocked",
                        operation_id=operation_id,
                        message=str(exc),
                    )
                time.sleep(min(0.01, max(0.0, lock_deadline - time.monotonic())))
        transaction_dir: Path | None = None
        journal: dict[str, object] = {}
        try:
            transaction_dir = self.filesystem.create_transaction(transaction_id)
            targets = sorted(candidates)
            preserved: dict[str, bytes | None] = {}
            for source in sorted(sources, key=lambda item: item.path):
                path = self.filesystem.target_path(source.path)
                current_exists = path.exists()
                current_hash = physical_sha256(path) if current_exists else None
                if current_exists != source.exists or current_hash != source.physical_sha256:
                    raise ValueError(
                        f"Mutation source changed before lock-protected commit: {source.path}"
                    )
                preserved[source.path] = path.read_bytes() if current_exists else None
            self._inject("after_source_recheck", "")
            journal = {
                "journal_version": 1,
                "transaction_id": transaction_id,
                "operation_id": operation_id,
                "state": "staging",
                "pid": os.getpid(),
                "actor": actor,
                "created_at": utc_now_iso(),
                "plan_fingerprint_sha256": preview_token,
                "source_version": 1,
                "target_version": 1,
                "target_order": targets,
                "originals": {},
                "candidates": {},
                "replaced": [],
                "physical_results": {},
            }
            originals = journal["originals"]
            candidate_meta = journal["candidates"]
            assert isinstance(originals, dict)
            assert isinstance(candidate_meta, dict)
            self._inject("before_staging", "")
            for target in targets:
                original = self.filesystem.snapshot_target(transaction_dir, target)
                expected = source_map.get(target)
                if expected is None:
                    raise ValueError(f"Missing source precondition for mutation target: {target}")
                if original["exists"] != expected.exists or original["physical_sha256"] != expected.physical_sha256:
                    raise ValueError(f"Mutation source changed before lock-protected commit: {target}")
                originals[target] = original
                content = candidates[target]
                candidate_meta[target] = (
                    self.filesystem.stage_candidate(transaction_dir, target, content)
                    if content is not None
                    else {"physical_sha256": None, "size": 0, "delete": True}
                )
            if candidate_validator is not None:
                self._inject("before_candidate_validation", "")
                view = CandidateWorkspaceView(
                    root=self.root,
                    candidates={
                        target: content
                        for target, content in candidates.items()
                        if content is not None
                    },
                    preserved=preserved,
                    owned_paths=set(candidates),
                )
                candidate_validator(view)
                self._inject("after_candidate_validation", "")
            self._inject("before_final_source_recheck", "")
            for source in sorted(sources, key=lambda item: item.path):
                path = self.filesystem.target_path(source.path)
                current_exists = path.exists()
                current_hash = physical_sha256(path) if current_exists else None
                if current_exists != source.exists or current_hash != source.physical_sha256:
                    raise ValueError(
                        f"Mutation source changed before lock-protected commit: {source.path}"
                    )
            self._inject("after_final_source_recheck", "")
            self._inject("before_journal", "")
            self.filesystem.write_journal(transaction_dir, journal)
            self._inject("after_journal", "")
            for target in targets:
                original = originals[target]
                assert isinstance(original, dict)
                current = physical_sha256(self.filesystem.target_path(target))
                expected_hash = original.get("physical_sha256") if original.get("exists") else None
                if current != expected_hash:
                    raise ValueError(f"Mutation target preimage changed: {target}")
                self._inject("before_replace", target)
                mode = original.get("mode")
                content = candidates[target]
                result = (
                    self.filesystem.replace_target(
                        target,
                        content,
                        mode=mode if isinstance(mode, int) else None,
                    )
                    if content is not None
                    else {"deleted": self.filesystem.remove_target(target)}
                )
                replaced = journal["replaced"]
                physical_results = journal["physical_results"]
                assert isinstance(replaced, list)
                assert isinstance(physical_results, dict)
                replaced.append(target)
                physical_results[target] = result
                journal["state"] = "committing"
                self.filesystem.write_journal(transaction_dir, journal)
                self._inject("after_replace", target)
            journal["state"] = "committed"
            self.filesystem.write_journal(transaction_dir, journal)
            self.filesystem.cleanup(transaction_dir)
            self.lock_service.release(transaction_id)
            return MutationResult(
                status="applied",
                operation_id=operation_id,
                changed_paths=tuple(targets),
                final_physical_hashes={
                    target: hashlib.sha256(content).hexdigest()
                    for target, content in candidates.items()
                    if content is not None
                },
                preview_token=preview_token,
                actor=actor,
                message="Mutation committed atomically.",
            )
        except Exception as exc:
            if transaction_dir is None:
                self.lock_service.release(transaction_id)
                return MutationResult(status="failed", operation_id=operation_id, message=str(exc))
            replaced = journal.get("replaced")
            if not isinstance(replaced, list) or not replaced:
                self.filesystem.cleanup(transaction_dir)
                self.lock_service.release(transaction_id)
                return MutationResult(status="failed", operation_id=operation_id, message=str(exc))
            restored: list[str] = []
            blocked: list[str] = []
            originals = journal.get("originals")
            candidate_meta = journal.get("candidates")
            assert isinstance(originals, dict)
            assert isinstance(candidate_meta, dict)
            for target in reversed(replaced):
                candidate = candidate_meta.get(target)
                original = originals.get(target)
                if not isinstance(candidate, dict) or not isinstance(original, dict):
                    blocked.append(target)
                    continue
                if physical_sha256(self.filesystem.target_path(target)) != candidate.get("physical_sha256"):
                    blocked.append(target)
                    continue
                if original.get("exists"):
                    mode = original.get("mode")
                    self.filesystem.replace_target(
                        target,
                        self.filesystem.read_original(transaction_dir, target),
                        mode=mode if isinstance(mode, int) else None,
                    )
                else:
                    self.filesystem.remove_target(target)
                restored.append(target)
            if blocked:
                journal["state"] = "recovery_required"
                journal["rollback_blocked_targets"] = blocked
                journal["restored"] = restored
                self.filesystem.write_journal(transaction_dir, journal)
                return MutationResult(
                    status="recovery_required",
                    operation_id=operation_id,
                    restored_paths=tuple(restored),
                    preview_token=preview_token,
                    actor=actor,
                    message=f"Mutation failed and external edits blocked rollback: {', '.join(blocked)}",
                    recovery_required=True,
                )
            self.filesystem.cleanup(transaction_dir)
            self.lock_service.release(transaction_id)
            return MutationResult(
                status="rolled_back",
                operation_id=operation_id,
                restored_paths=tuple(restored),
                preview_token=preview_token,
                actor=actor,
                message=f"Mutation failed and was rolled back: {exc}",
            )

    def _inject(self, stage: str, target: str) -> None:
        if self.failure_injector is not None:
            self.failure_injector(stage, target)


class WorkspaceTransactionRecoveryService:
    """Explicit recovery for interrupted current-schema atomic mutations."""

    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        lock_service: WorkspaceTransactionLockService | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.lock_service = lock_service or WorkspaceTransactionLockService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.filesystem = DurableTransactionFilesystem(
            root=self.root,
            p2p_dir=self.p2p_dir,
            lock_service=self.lock_service,
        )

    def status(self) -> WorkspaceTransactionRecoveryStatus:
        lock = self.lock_service.status()
        transaction_ids = self._journal_transaction_ids()
        if lock.state == LOCK_ABSENT and not transaction_ids:
            return WorkspaceTransactionRecoveryStatus(
                required=False,
                lock=lock,
                message="No workspace transaction recovery is required.",
            )
        if len(transaction_ids) > 1:
            return WorkspaceTransactionRecoveryStatus(
                required=True,
                lock=lock,
                journal_state="ambiguous",
                message=(
                    "Multiple interrupted workspace transactions were found: "
                    + ", ".join(transaction_ids)
                ),
            )
        transaction_id = lock.transaction_id or (transaction_ids[0] if transaction_ids else "")
        journal_state = "unknown"
        if transaction_id:
            transaction_dir = self.lock_service.transactions_root / transaction_id
            if (transaction_dir / "journal.yml").exists():
                try:
                    journal_state = str(self.filesystem.read_journal(transaction_dir).get("state") or "unknown")
                except ValueError:
                    journal_state = "invalid"
        actions = ()
        if transaction_id and journal_state not in {"invalid", "unknown"}:
            actions = ("rollback", "resume")
        elif transaction_id and lock.state == LOCK_STALE:
            actions = ("rollback",)
        return WorkspaceTransactionRecoveryStatus(
            required=True,
            lock=lock,
            transaction_id=transaction_id,
            journal_state=journal_state,
            available_actions=actions,
            message="An interrupted workspace transaction requires explicit recovery.",
        )

    def rollback(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ) -> WorkspaceTransactionRecoveryResult:
        blocked = self._validate_recovery_request(
            transaction_id=transaction_id,
            actor=actor,
            confirm=confirm,
        )
        if blocked is not None:
            return blocked
        transaction_dir = self.lock_service.transactions_root / transaction_id
        journal_path = transaction_dir / "journal.yml"
        if not journal_path.exists():
            lock = self.lock_service.status()
            if lock.state == LOCK_STALE and lock.transaction_id == transaction_id:
                self.lock_service.release(transaction_id)
                if transaction_dir.exists():
                    self.filesystem.cleanup(transaction_dir)
                return WorkspaceTransactionRecoveryResult(
                    status="rolled_back",
                    transaction_id=transaction_id,
                    message="Stale workspace transaction lock without a journal was removed.",
                )
            return WorkspaceTransactionRecoveryResult(
                status="recovery_required",
                transaction_id=transaction_id,
                message="The workspace transaction journal is missing.",
                recovery_required=True,
            )
        try:
            journal = self.filesystem.read_journal(transaction_dir)
            return self._rollback_journal(transaction_dir, journal)
        except (OSError, ValueError) as exc:
            return WorkspaceTransactionRecoveryResult(
                status="recovery_required",
                transaction_id=transaction_id,
                message=str(exc),
                recovery_required=True,
            )

    def resume(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ) -> WorkspaceTransactionRecoveryResult:
        blocked = self._validate_recovery_request(
            transaction_id=transaction_id,
            actor=actor,
            confirm=confirm,
        )
        if blocked is not None:
            return blocked
        transaction_dir = self.lock_service.transactions_root / transaction_id
        try:
            journal = self.filesystem.read_journal(transaction_dir)
            target_order = _journal_string_list(journal.get("target_order"), "target_order")
            replaced = _journal_string_list(journal.get("replaced"), "replaced")
            originals = _journal_mapping(journal.get("originals"), "originals")
            candidates = _journal_mapping(journal.get("candidates"), "candidates")
            for target in replaced:
                candidate = _journal_mapping(candidates.get(target), f"candidates.{target}")
                if physical_sha256(self.filesystem.target_path(target)) != candidate.get("physical_sha256"):
                    raise ValueError(f"Already replaced target changed externally: {target}")
            for target in target_order:
                if target in replaced:
                    continue
                original = _journal_mapping(originals.get(target), f"originals.{target}")
                expected = original.get("physical_sha256") if original.get("exists") else None
                if physical_sha256(self.filesystem.target_path(target)) != expected:
                    raise ValueError(f"Target preimage changed before replacement: {target}")
                candidate = _journal_mapping(candidates.get(target), f"candidates.{target}")
                if not candidate.get("delete"):
                    content = self.filesystem.read_candidate(transaction_dir, target)
                    if hashlib.sha256(content).hexdigest() != candidate.get("physical_sha256"):
                        raise ValueError(f"Staged candidate hash changed: {target}")
            changed: list[str] = []
            for target in target_order:
                if target in replaced:
                    continue
                original = _journal_mapping(originals.get(target), f"originals.{target}")
                candidate = _journal_mapping(candidates.get(target), f"candidates.{target}")
                if candidate.get("delete"):
                    self.filesystem.remove_target(target)
                else:
                    mode = original.get("mode")
                    self.filesystem.replace_target(
                        target,
                        self.filesystem.read_candidate(transaction_dir, target),
                        mode=mode if isinstance(mode, int) else None,
                    )
                replaced.append(target)
                changed.append(target)
                journal["replaced"] = replaced
                journal["state"] = "committing"
                self.filesystem.write_journal(transaction_dir, journal)
            journal["state"] = "committed"
            self.filesystem.write_journal(transaction_dir, journal)
            self.filesystem.cleanup(transaction_dir)
            self.lock_service.release(transaction_id)
            return WorkspaceTransactionRecoveryResult(
                status="applied",
                transaction_id=transaction_id,
                changed_paths=tuple(changed),
                message="Interrupted workspace transaction resumed and completed.",
            )
        except (OSError, ValueError) as exc:
            return WorkspaceTransactionRecoveryResult(
                status="recovery_required",
                transaction_id=transaction_id,
                message=str(exc),
                recovery_required=True,
            )

    def _rollback_journal(
        self,
        transaction_dir: Path,
        journal: dict[str, object],
    ) -> WorkspaceTransactionRecoveryResult:
        transaction_id = str(journal.get("transaction_id") or transaction_dir.name)
        replaced = _journal_string_list(journal.get("replaced"), "replaced")
        originals = _journal_mapping(journal.get("originals"), "originals")
        candidates = _journal_mapping(journal.get("candidates"), "candidates")
        restored: list[str] = []
        blocked: list[str] = []
        for target in reversed(replaced):
            candidate = _journal_mapping(candidates.get(target), f"candidates.{target}")
            if physical_sha256(self.filesystem.target_path(target)) != candidate.get("physical_sha256"):
                blocked.append(target)
                continue
            original = _journal_mapping(originals.get(target), f"originals.{target}")
            if original.get("exists"):
                mode = original.get("mode")
                self.filesystem.replace_target(
                    target,
                    self.filesystem.read_original(transaction_dir, target),
                    mode=mode if isinstance(mode, int) else None,
                )
            else:
                self.filesystem.remove_target(target)
            restored.append(target)
        if blocked:
            journal["state"] = "recovery_required"
            journal["rollback_blocked_targets"] = blocked
            journal["restored"] = restored
            self.filesystem.write_journal(transaction_dir, journal)
            return WorkspaceTransactionRecoveryResult(
                status="recovery_required",
                transaction_id=transaction_id,
                restored_paths=tuple(restored),
                message="Rollback preserved externally changed targets: " + ", ".join(blocked),
                recovery_required=True,
            )
        self.filesystem.cleanup(transaction_dir)
        try:
            self.lock_service.release(transaction_id)
        except ValueError as exc:
            return WorkspaceTransactionRecoveryResult(
                status="recovery_required",
                transaction_id=transaction_id,
                restored_paths=tuple(restored),
                message=f"Targets restored but lock cleanup requires recovery: {exc}",
                recovery_required=True,
            )
        return WorkspaceTransactionRecoveryResult(
            status="rolled_back",
            transaction_id=transaction_id,
            restored_paths=tuple(restored),
            message="Workspace transaction replacements were rolled back completely.",
        )

    def _validate_recovery_request(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ) -> WorkspaceTransactionRecoveryResult | None:
        if not confirm or not transaction_id.strip() or not actor.strip():
            return WorkspaceTransactionRecoveryResult(
                status="blocked",
                transaction_id=transaction_id,
                message="Transaction id, actor and explicit confirmation are required.",
                recovery_required=True,
            )
        recovery = self.status()
        known = set(self._journal_transaction_ids())
        if recovery.lock.transaction_id:
            known.add(recovery.lock.transaction_id)
        if transaction_id not in known:
            return WorkspaceTransactionRecoveryResult(
                status="blocked",
                transaction_id=transaction_id,
                message="Requested workspace recovery transaction is not active.",
                recovery_required=recovery.required,
            )
        if not self._actor_authorized(actor, transaction_id):
            return WorkspaceTransactionRecoveryResult(
                status="blocked",
                transaction_id=transaction_id,
                message=f"Actor {actor} is not authorized to recover workspace transactions.",
                recovery_required=True,
            )
        return None

    def _actor_authorized(self, actor: str, transaction_id: str) -> bool:
        permissions_path = self.p2p_dir / "project" / "permissions.yml"
        if permissions_path.exists():
            try:
                from p2p_engine.services.permissions import PermissionsService

                resolved = PermissionsService(
                    root=self.root,
                    p2p_dir=self.p2p_dir,
                ).resolve_actor(actor)
            except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError):
                return False
            return resolved.role == "owner"
        transaction_dir = self.lock_service.transactions_root / transaction_id
        try:
            journal = self.filesystem.read_journal(transaction_dir)
        except ValueError:
            return self.lock_service.status().owner == actor
        return str(journal.get("actor") or "") == actor

    def _journal_transaction_ids(self) -> list[str]:
        if not self.lock_service.transactions_root.exists():
            return []
        return sorted(
            path.name
            for path in self.lock_service.transactions_root.iterdir()
            if path.is_dir() and (path / "journal.yml").exists()
        )


def physical_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Expected regular file for hash: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_target(
    relative: str,
    allowed_project_targets: frozenset[str] = frozenset(),
) -> str:
    pure = PurePosixPath(str(relative).replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"Unsafe workspace transaction target: {relative}")
    normalized = pure.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in allowed_project_targets:
        return normalized
    if _is_mutation_receipt_target(normalized):
        return normalized
    if _is_project_structure_export_marker_target(normalized):
        return normalized
    if not normalized.startswith(".p2p/") or normalized.startswith(".p2p/.internal/"):
        raise ValueError(f"Workspace transaction target is outside allowed canonical paths: {relative}")
    return normalized


_MUTATION_RECEIPT_TARGET = re.compile(
    rf"^{re.escape(MUTATION_RECEIPT_ROOT)}/[0-9a-f]{{64}}\.yml$"
)


def _is_mutation_receipt_target(relative: str) -> bool:
    return _MUTATION_RECEIPT_TARGET.fullmatch(relative) is not None


_PROJECT_STRUCTURE_EXPORT_MARKER_TARGET = re.compile(
    r"^\.p2p/\.internal/project-structure-exports/[0-9a-f]{64}\.yml$"
)


def _is_project_structure_export_marker_target(relative: str) -> bool:
    return _PROJECT_STRUCTURE_EXPORT_MARKER_TARGET.fullmatch(relative) is not None


def _normalize_project_target(relative: str) -> str:
    pure = PurePosixPath(str(relative).replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"Unsafe repository mutation target: {relative}")
    normalized = pure.as_posix()
    if normalized.startswith(".p2p/") or normalized.startswith("./"):
        raise ValueError(f"Repository target allowlist must name an exact root file: {relative}")
    return normalized


def _safe_identifier(value: str) -> None:
    if not value or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in value):
        raise ValueError("Workspace transaction id contains unsafe characters")


def _journal_mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Workspace transaction journal field {field} must be a mapping")
    return value


def _journal_string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Workspace transaction journal field {field} must be a string sequence")
    return value


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True

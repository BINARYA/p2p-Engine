from __future__ import annotations

import hashlib
import json
import tarfile
import uuid
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, cast

from p2p_engine.core.canonical_memory import (
    CanonicalEntity,
    CanonicalMemorySnapshot,
    canonical_json_bytes,
    semantic_sha256,
)
from p2p_engine.core.project_identity import ProjectMode
from p2p_engine.core.project_replication import replication_entity_version
from p2p_engine.core.replica_drift import (
    MAX_DRIFT_DIFF_ENTRIES,
    DriftClassification,
    DriftFinding,
    ReconciliationCommand,
    ReplicaDriftStatus,
    ReplicaForensicBackup,
    ReplicaReconciliationPlan,
    ReplicaSemanticDiff,
    SemanticDiffEntry,
)
from p2p_engine.foundation.files import write_bytes_atomic
from p2p_engine.ports.project_state import ProjectStateAdapter
from p2p_engine.services.linked_replica import LinkedReplicaService
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService

_PLAN_ROOT = ".p2p/local/project-replication/reconciliation-plans"
_APPLY_STATE_CONTRACT = "p2p-replica-reconciliation-apply-state/v1"
_FORENSIC_ROOT = ".p2p-forensics"
_DOMAIN_KIND = "p2p.project.domain"
_DOMAIN_ID = "project:domain"


class ReplicaDriftService:
    """Backend-neutral drift policy over one selected project-state adapter."""

    def __init__(
        self,
        *,
        root: Path,
        adapter: ProjectStateAdapter,
        linked_replica: LinkedReplicaService,
    ) -> None:
        self.root = root.resolve()
        self.adapter = adapter
        self.linked_replica = linked_replica

    def status(self) -> ReplicaDriftStatus:
        try:
            binding = self.adapter.linked_replicas.load()
        except ValueError:
            return self._blocked_status(
                DriftClassification.structural_corruption,
                "P2P_LINKED_REPLICA_STATE_INVALID",
                "The local linked-replica binding cannot be verified.",
            )
        if binding is None:
            try:
                identity = self.adapter.repository.identity()
            except Exception:
                return self._blocked_status(
                    DriftClassification.structural_corruption,
                    "P2P_PROJECT_STATE_INTEGRITY_FAILURE",
                    "The local project identity cannot be verified.",
                )
            if identity.mode in {ProjectMode.linked, ProjectMode.link_suspended}:
                return self._blocked_status(
                    DriftClassification.identity_mismatch,
                    "P2P_LINKED_REPLICA_BINDING_MISSING",
                    "Linked identity exists but its replica binding is absent.",
                    project_uuid=identity.project_uuid.value,
                )
            return ReplicaDriftStatus(
                status="standalone",
                classification=None,
                project_uuid=identity.project_uuid.value,
                findings=(
                    DriftFinding(
                        "P2P_DRIFT_NOT_LINKED",
                        "This project uses local backup and restore, not linked reconciliation.",
                        False,
                    ),
                ),
                next_actions=("p2p project memory backup", "p2p project memory restore preview"),
            )

        base: dict[str, Any] = {
            "project_uuid": binding.project_uuid.value,
            "replica_id": binding.replica_id.value,
            "authority_epoch": binding.authority_epoch.value,
            "confirmed_revision": binding.last_applied_revision,
            "confirmed_change_batch_id": _last_confirmed_batch_id(
                self.root, binding.last_applied_revision
            ),
            "confirmed_semantic_digest": binding.snapshot_digest,
            "confirmed_blob_manifest_digest": binding.blob_manifest_digest,
        }
        transaction = WorkspaceTransactionLockService(
            root=self.root, p2p_dir=self.root / ".p2p"
        ).status()
        if transaction.state != "absent":
            return ReplicaDriftStatus(
                status="blocked",
                classification=DriftClassification.incomplete_local_operation,
                findings=(
                    DriftFinding(
                        "P2P_LINKED_REPLICA_INCOMPLETE_LOCAL_OPERATION",
                        "An interrupted or active local transaction must be resolved first.",
                        True,
                    ),
                ),
                next_actions=("p2p workspace transaction status",),
                **base,
            )
        try:
            self.adapter.linked_replicas.verify_active_identity(binding)
        except ValueError as exc:
            mismatch = "IDENTITY_MISMATCH" in str(exc)
            return ReplicaDriftStatus(
                status="blocked",
                classification=(
                    DriftClassification.identity_mismatch
                    if mismatch
                    else DriftClassification.structural_corruption
                ),
                findings=(
                    DriftFinding(
                        (
                            "P2P_LINKED_REPLICA_IDENTITY_MISMATCH"
                            if mismatch
                            else "P2P_LINKED_REPLICA_STRUCTURAL_CORRUPTION"
                        ),
                        (
                            "Project, replica or remote authority identity does not match the binding."
                            if mismatch
                            else "The selected storage adapter cannot verify project identity."
                        ),
                        True,
                    ),
                ),
                next_actions=("p2p drift backup", "p2p drift discard --confirm"),
                **base,
            )
        try:
            snapshot = self.adapter.repository.snapshot()
        except Exception:
            return ReplicaDriftStatus(
                status="blocked",
                classification=DriftClassification.structural_corruption,
                findings=(
                    DriftFinding(
                        "P2P_LINKED_REPLICA_STRUCTURAL_CORRUPTION",
                        "The selected storage adapter cannot prove canonical-state integrity.",
                        True,
                    ),
                ),
                next_actions=("p2p drift backup", "p2p drift discard --confirm"),
                **base,
            )
        if snapshot.project_uuid != binding.project_uuid.value:
            return ReplicaDriftStatus(
                status="blocked",
                classification=DriftClassification.identity_mismatch,
                current_semantic_digest=snapshot.semantic_state_digest,
                current_blob_manifest_digest=snapshot.blob_manifest_digest,
                findings=(
                    DriftFinding(
                        "P2P_LINKED_REPLICA_IDENTITY_MISMATCH",
                        "Canonical project identity differs from the registered replica.",
                        True,
                    ),
                ),
                next_actions=("p2p drift backup", "p2p drift discard --confirm"),
                **base,
            )
        if (
            snapshot.semantic_state_digest != binding.snapshot_digest
            or snapshot.blob_manifest_digest != binding.blob_manifest_digest
        ):
            return ReplicaDriftStatus(
                status="blocked",
                classification=DriftClassification.semantic_drift,
                current_semantic_digest=snapshot.semantic_state_digest,
                current_blob_manifest_digest=snapshot.blob_manifest_digest,
                findings=(
                    DriftFinding(
                        "P2P_LINKED_REPLICA_SEMANTIC_DRIFT",
                        "Local logical state differs from the last confirmed WaveKit revision.",
                        True,
                    ),
                ),
                next_actions=(
                    "p2p drift diff",
                    "p2p reconcile preview",
                    "p2p drift backup",
                    "p2p drift discard --confirm",
                ),
                **base,
            )
        return ReplicaDriftStatus(
            status="healthy",
            classification=DriftClassification.transient_valid,
            current_semantic_digest=snapshot.semantic_state_digest,
            current_blob_manifest_digest=snapshot.blob_manifest_digest,
            findings=(
                DriftFinding(
                    "P2P_LINKED_REPLICA_LOGICAL_STATE_VALID",
                    "Canonical state matches the last confirmed WaveKit evidence.",
                    False,
                ),
            ),
            next_actions=("p2p sync catch-up",),
            **base,
        )

    def verify(self) -> ReplicaDriftStatus:
        status = self.status()
        if status.status == "blocked":
            finding = status.findings[0]
            raise ValueError(f"{finding.code}: {finding.message}")
        return status

    def report(self, *, include_diff: bool = True) -> Mapping[str, object]:
        status = self.status()
        if status.status == "standalone":
            raise ValueError("P2P_DRIFT_NOT_LINKED: standalone projects are not reported")
        semantic_diff = None
        if include_diff and status.diff_available:
            semantic_diff = self.semantic_diff().to_dict()
        return self.linked_replica.report_drift(
            status=status.to_dict(),
            semantic_diff=semantic_diff,
        )

    def semantic_diff(self, *, limit: int = MAX_DRIFT_DIFF_ENTRIES) -> ReplicaSemanticDiff:
        if not 1 <= limit <= MAX_DRIFT_DIFF_ENTRIES:
            raise ValueError("P2P_DRIFT_LIMIT_INVALID: limit must be between 1 and 256")
        binding = self.adapter.linked_replicas.load()
        if binding is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: local binding is absent")
        manifest, bundle = self.linked_replica.download_verified_snapshot(
            operation_key=f"drift-diff:{binding.replica_id.value}:{binding.last_applied_revision}"
        )
        remote = self.linked_replica.codec.decode_bundle(bundle).snapshot
        try:
            local = self.adapter.repository.snapshot()
        except Exception:
            return ReplicaSemanticDiff(
                project_uuid=binding.project_uuid.value,
                replica_id=binding.replica_id.value,
                confirmed_revision=binding.last_applied_revision,
                current_remote_revision=manifest.remote_revision,
                entries=(),
                complete=False,
                truncated=False,
                issues=("P2P_DRIFT_LOCAL_STATE_UNDECODABLE",),
            )
        entries = self._diff_entries(remote, local)
        visible = entries[:limit]
        return ReplicaSemanticDiff(
            project_uuid=binding.project_uuid.value,
            replica_id=binding.replica_id.value,
            confirmed_revision=binding.last_applied_revision,
            current_remote_revision=manifest.remote_revision,
            entries=visible,
            complete=len(entries) <= limit,
            truncated=len(entries) > limit,
            issues=(),
        )

    def forensic_backup(self) -> ReplicaForensicBackup:
        binding = self.adapter.linked_replicas.load()
        project_uuid = (
            binding.project_uuid.value if binding is not None else "unbound-project"
        )
        backup_ref = f"fr_{uuid.uuid4().hex}"
        directory = self.root / _FORENSIC_ROOT / project_uuid
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = directory / f"{backup_ref}.tar"
        p2p_dir = self.root / ".p2p"
        if not p2p_dir.is_dir() or p2p_dir.is_symlink():
            raise ValueError(
                "P2P_DRIFT_BACKUP_FAILED: the suspect .p2p container is unavailable"
            )
        with tarfile.open(target, "x", dereference=False) as archive:
            archive.add(p2p_dir, arcname=".p2p", recursive=True, filter=_tar_filter)
        target.chmod(0o600)
        raw = target.read_bytes()
        file_count, byte_count = _verify_forensic_archive(target)
        return ReplicaForensicBackup(
            backup_ref=backup_ref,
            archive_sha256=hashlib.sha256(raw).hexdigest(),
            file_count=file_count,
            byte_count=byte_count,
            verified=True,
        )

    def discard_and_rebuild(self, *, confirm: bool) -> dict[str, object]:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: drift discard requires --confirm")
        status = self.status()
        if status.status != "blocked":
            raise ValueError("P2P_DRIFT_REBUILD_NOT_REQUIRED: local replica is not drifted")
        backup = self.forensic_backup()
        binding = self.adapter.linked_replicas.load()
        if binding is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: local binding is absent")
        result = self.linked_replica.rebuild_from_authority(
            operation_key=f"drift-rebuild:{binding.replica_id.value}:{backup.backup_ref}"
        )
        healthy = self.status()
        remote_health = self.linked_replica.report_drift(
            status=healthy.to_dict(), semantic_diff=None
        )
        return {
            "contract": "p2p-replica-drift-rebuild/v1",
            "status": "rebuilt",
            "forensic_backup": backup.to_dict(),
            "linked_replica": result.to_dict(),
            "remote_health": dict(remote_health),
            "suspect_bytes_uploaded": False,
        }

    def reconciliation_preview(self) -> ReplicaReconciliationPlan:
        binding = self.adapter.linked_replicas.load()
        if binding is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: local binding is absent")
        status = self.status()
        if status.classification != DriftClassification.semantic_drift:
            raise ValueError(
                "P2P_RECONCILIATION_UNAVAILABLE: a complete semantic drift is required"
            )
        manifest, bundle = self.linked_replica.download_verified_snapshot(
            operation_key=f"reconcile-preview:{binding.replica_id.value}:{binding.last_applied_revision}"
        )
        remote = self.linked_replica.codec.decode_bundle(bundle).snapshot
        local = self.adapter.repository.snapshot()
        commands, unsupported = self._translate(remote, local)
        plan = ReplicaReconciliationPlan(
            project_uuid=binding.project_uuid.value,
            replica_id=binding.replica_id.value,
            authority_epoch=binding.authority_epoch.value,
            confirmed_revision=binding.last_applied_revision,
            current_remote_revision=manifest.remote_revision,
            local_semantic_digest=local.semantic_state_digest,
            remote_semantic_digest=remote.semantic_state_digest,
            commands=commands,
            unsupported_differences=unsupported,
            conflicts=(),
            complete=bool(commands) and not unsupported,
        )
        semantic_diff = ReplicaSemanticDiff(
            project_uuid=binding.project_uuid.value,
            replica_id=binding.replica_id.value,
            confirmed_revision=binding.last_applied_revision,
            current_remote_revision=manifest.remote_revision,
            entries=self._diff_entries(remote, local),
            complete=True,
            truncated=False,
        )
        self.linked_replica.report_drift(
            status=status.to_dict(), semantic_diff=semantic_diff.to_dict()
        )
        if plan.complete:
            preview = self.linked_replica.preview_reconciliation(plan.to_dict())
            token = str(preview.get("preview_token") or "")
            if not token.startswith("sha256:") or len(token) != 71:
                raise ValueError(
                    "P2P_RECONCILIATION_RESPONSE_INVALID: preview token is invalid"
                )
            plan = ReplicaReconciliationPlan(
                project_uuid=plan.project_uuid,
                replica_id=plan.replica_id,
                authority_epoch=plan.authority_epoch,
                confirmed_revision=plan.confirmed_revision,
                current_remote_revision=plan.current_remote_revision,
                local_semantic_digest=plan.local_semantic_digest,
                remote_semantic_digest=plan.remote_semantic_digest,
                commands=plan.commands,
                unsupported_differences=plan.unsupported_differences,
                conflicts=plan.conflicts,
                complete=plan.complete,
                server_preview_token=token,
            )
        self._save_plan(plan)
        return plan

    def reconciliation_apply(self, *, plan_digest: str, confirm: bool) -> dict[str, object]:
        if not confirm:
            raise ValueError(
                "P2P_CONFIRMATION_REQUIRED: reconciliation apply requires --confirm"
            )
        plan = self._load_plan(plan_digest.removeprefix("sha256:"))
        if not plan.complete or plan.unsupported_differences or plan.conflicts:
            raise ValueError("P2P_RECONCILIATION_INCOMPLETE: plan cannot be applied")
        binding = self.adapter.linked_replicas.load()
        if binding is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: local binding is absent")
        if not plan.server_preview_token:
            raise ValueError(
                "P2P_RECONCILIATION_STALE_PLAN: WaveKit preview evidence is absent"
            )
        apply_state = self._load_apply_state(plan)
        backup_payload: Mapping[str, object]
        if apply_state is None or apply_state["state"] == "rebuild-pending":
            manifest, bundle = self.linked_replica.download_verified_snapshot(
                operation_key=(
                    f"reconcile-verify:{binding.replica_id.value}:"
                    f"{plan.plan_digest[:24]}"
                )
            )
            if (
                manifest.remote_revision != plan.current_remote_revision
                or manifest.semantic_state_digest != plan.remote_semantic_digest
                or binding.authority_epoch.value != plan.authority_epoch
            ):
                raise ValueError(
                    "P2P_RECONCILIATION_STALE_PLAN: WaveKit changed after preview"
                )
            if apply_state is None:
                backup_payload = self.forensic_backup().to_dict()
                self._save_apply_state(
                    plan,
                    state="rebuild-pending",
                    forensic_backup=backup_payload,
                )
            else:
                backup_payload = cast(
                    Mapping[str, object], apply_state["forensic_backup"]
                )
            self.linked_replica.rebuild_from_authority(
                operation_key=(
                    f"reconcile-rebuild:{binding.replica_id.value}:"
                    f"{plan.plan_digest[:24]}"
                ),
                manifest=manifest,
                bundle=bundle,
            )
            # Authoritative replacement swaps the whole .p2p container. Restore
            # only the exact local recovery evidence needed for idempotent retry;
            # the suspect plan copy also remains inside the forensic archive.
            self._save_plan(plan)
            self._save_apply_state(
                plan,
                state="remote-submit-pending",
                forensic_backup=backup_payload,
            )
        else:
            backup_payload = cast(
                Mapping[str, object], apply_state["forensic_backup"]
            )
        result = self.linked_replica.apply_reconciliation(
            plan_digest=f"sha256:{plan.plan_digest}",
            preview_token=plan.server_preview_token,
        )
        receipts_raw = result.get("receipts")
        receipts = (
            [dict(item) for item in receipts_raw if isinstance(item, Mapping)]
            if isinstance(receipts_raw, list)
            else []
        )
        self.linked_replica.catch_up()
        healthy = self.status()
        self.linked_replica.report_drift(status=healthy.to_dict(), semantic_diff=None)
        self._save_apply_state(
            plan,
            state="completed",
            forensic_backup=backup_payload,
        )
        return {
            "contract": "p2p-replica-reconciliation-result/v1",
            "status": "applied",
            "plan_digest": f"sha256:{plan.plan_digest}",
            "receipts": receipts,
            "forensic_backup": backup_payload,
            "suspect_bytes_uploaded": False,
        }

    @staticmethod
    def _diff_entries(
        confirmed: CanonicalMemorySnapshot,
        local: CanonicalMemorySnapshot,
    ) -> tuple[SemanticDiffEntry, ...]:
        before = {(item.entity_type, item.technical_id): item for item in confirmed.entities}
        after = {(item.entity_type, item.technical_id): item for item in local.entities}
        entries: list[SemanticDiffEntry] = []
        for key in sorted(set(before) | set(after)):
            old = before.get(key)
            new = after.get(key)
            if old is not None and new is not None and old.to_dict() == new.to_dict():
                continue
            change = "added" if old is None else "removed" if new is None else "modified"
            entries.append(
                SemanticDiffEntry(
                    change=change,
                    entity_type=key[0],
                    entity_id=key[1],
                    confirmed_version=None if old is None else old.entity_version,
                    local_version=None if new is None else new.entity_version,
                    confirmed_digest=None if old is None else semantic_sha256(old.to_dict()),
                    local_digest=None if new is None else semantic_sha256(new.to_dict()),
                )
            )
        before_blobs = {item.digest: item for item in confirmed.blobs}
        after_blobs = {item.digest: item for item in local.blobs}
        for digest in sorted(set(before_blobs) ^ set(after_blobs)):
            old_blob = before_blobs.get(digest)
            new_blob = after_blobs.get(digest)
            entries.append(
                SemanticDiffEntry(
                    change="added" if old_blob is None else "removed",
                    entity_type="managed-blob",
                    entity_id=digest,
                    confirmed_version=None,
                    local_version=None,
                    confirmed_digest=(
                        None
                        if old_blob is None
                        else semantic_sha256(old_blob.to_dict())
                    ),
                    local_digest=(
                        None
                        if new_blob is None
                        else semantic_sha256(new_blob.to_dict())
                    ),
                )
            )
        if not entries and confirmed.semantic_state_digest != local.semantic_state_digest:
            entries.append(
                SemanticDiffEntry(
                    change="modified",
                    entity_type="canonical-graph",
                    entity_id="project:canonical-graph",
                    confirmed_version=None,
                    local_version=None,
                    confirmed_digest=confirmed.semantic_state_digest,
                    local_digest=local.semantic_state_digest,
                )
            )
        return tuple(entries)

    def _translate(
        self,
        confirmed: CanonicalMemorySnapshot,
        local: CanonicalMemorySnapshot,
    ) -> tuple[tuple[ReconciliationCommand, ...], tuple[Mapping[str, object], ...]]:
        differences = self._diff_entries(confirmed, local)
        commands: list[ReconciliationCommand] = []
        unsupported: list[Mapping[str, object]] = []
        for item in differences:
            if item.entity_type != _DOMAIN_KIND or item.entity_id != _DOMAIN_ID:
                unsupported.append(
                    {
                        "entity_type": item.entity_type,
                        "entity_id": item.entity_id,
                        "reason": "no-allowlisted-domain-command",
                    }
                )
                continue
            desired = _entity(local, _DOMAIN_KIND, _DOMAIN_ID)
            current = _entity(confirmed, _DOMAIN_KIND, _DOMAIN_ID)
            descriptor = _domain_descriptor(desired)
            expected_version = 0 if current is None else _replication_version(current)
            if descriptor is None:
                commands.append(
                    ReconciliationCommand(
                        command="project.domain.clear",
                        payload_contract="p2p-linked-mcp-command/v1",
                        payload={},
                        entity_preconditions=(
                            {
                                "kind": "project.domain",
                                "id": _DOMAIN_ID,
                                "expected_version": expected_version,
                            },
                        ),
                        expected_effect="Clear the project domain through WaveKit authority.",
                    )
                )
                continue
            if not isinstance(descriptor.get("key"), str) or not descriptor["key"]:
                unsupported.append(
                    {
                        "entity_type": item.entity_type,
                        "entity_id": item.entity_id,
                        "reason": "invalid-domain-descriptor",
                    }
                )
                continue
            payload = {
                key: descriptor[key]
                for key in ("key", "name", "source", "external_ref")
                if key in descriptor and descriptor[key] is not None
            }
            commands.append(
                ReconciliationCommand(
                    command="project.domain.set",
                    payload_contract="p2p-linked-mcp-command/v1",
                    payload=payload,
                    entity_preconditions=(
                        {
                            "kind": "project.domain",
                            "id": _DOMAIN_ID,
                            "expected_version": expected_version,
                        },
                    ),
                    expected_effect="Set the project domain through WaveKit authority.",
                )
            )
        if len(commands) > 1:
            unsupported.append(
                {
                    "entity_type": _DOMAIN_KIND,
                    "entity_id": _DOMAIN_ID,
                    "reason": "multiple-domain-intents",
                }
            )
            commands.clear()
        return tuple(commands), tuple(unsupported)

    def _save_plan(self, plan: ReplicaReconciliationPlan) -> None:
        path = self.root / _PLAN_ROOT / f"{plan.plan_digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_bytes_atomic(path, canonical_json_bytes(plan.to_dict()), mode=0o600)

    def _apply_state_path(self, digest: str) -> Path:
        return self.root / _PLAN_ROOT / f"{digest}.apply.json"

    def _save_apply_state(
        self,
        plan: ReplicaReconciliationPlan,
        *,
        state: str,
        forensic_backup: Mapping[str, object],
    ) -> None:
        if state not in {"rebuild-pending", "remote-submit-pending", "completed"}:
            raise ValueError("P2P_RECONCILIATION_STATE_INVALID: state is invalid")
        payload = {
            "contract": _APPLY_STATE_CONTRACT,
            "plan_digest": f"sha256:{plan.plan_digest}",
            "server_preview_token": plan.server_preview_token,
            "state": state,
            "forensic_backup": dict(forensic_backup),
        }
        path = self._apply_state_path(plan.plan_digest)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_bytes_atomic(path, canonical_json_bytes(payload), mode=0o600)

    def _load_apply_state(
        self, plan: ReplicaReconciliationPlan
    ) -> dict[str, object] | None:
        path = self._apply_state_path(plan.plan_digest)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "P2P_RECONCILIATION_STATE_INVALID: apply recovery state is unreadable"
            ) from exc
        expected = {
            "contract",
            "plan_digest",
            "server_preview_token",
            "state",
            "forensic_backup",
        }
        if (
            not isinstance(raw, Mapping)
            or set(raw) != expected
            or raw.get("contract") != _APPLY_STATE_CONTRACT
            or raw.get("plan_digest") != f"sha256:{plan.plan_digest}"
            or raw.get("server_preview_token") != plan.server_preview_token
            or raw.get("state")
            not in {"rebuild-pending", "remote-submit-pending", "completed"}
            or not isinstance(raw.get("forensic_backup"), Mapping)
        ):
            raise ValueError(
                "P2P_RECONCILIATION_STATE_INVALID: apply recovery state differs"
            )
        backup = dict(raw["forensic_backup"])
        if (
            backup.get("contract") != "p2p-replica-forensic-backup/v1"
            or not str(backup.get("backup_ref") or "").startswith("fr_")
            or backup.get("verified") is not True
            or backup.get("physical_path_exposed") is not False
        ):
            raise ValueError(
                "P2P_RECONCILIATION_STATE_INVALID: forensic evidence differs"
            )
        return {"state": str(raw["state"]), "forensic_backup": backup}

    def _load_plan(self, digest: str) -> ReplicaReconciliationPlan:
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("P2P_RECONCILIATION_PLAN_INVALID: digest is invalid")
        path = self.root / _PLAN_ROOT / f"{digest}.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("P2P_RECONCILIATION_PLAN_NOT_FOUND: preview is absent") from exc
        if not isinstance(raw, Mapping):
            raise ValueError("P2P_RECONCILIATION_PLAN_INVALID: plan body is invalid")
        commands_raw = raw.get("commands")
        unsupported = raw.get("unsupported_differences")
        conflicts = raw.get("conflicts")
        if not isinstance(commands_raw, list) or not isinstance(unsupported, list) or not isinstance(conflicts, list):
            raise ValueError("P2P_RECONCILIATION_PLAN_INVALID: plan collections are invalid")
        commands = tuple(_command_from_mapping(item) for item in commands_raw)
        plan = ReplicaReconciliationPlan(
            project_uuid=str(raw.get("project_uuid") or ""),
            replica_id=str(raw.get("replica_id") or ""),
            authority_epoch=int(raw.get("authority_epoch") or 0),
            confirmed_revision=int(raw.get("confirmed_revision") or 0),
            current_remote_revision=int(raw.get("current_remote_revision") or 0),
            local_semantic_digest=str(
                raw.get("local_semantic_digest") or ""
            ).removeprefix("sha256:"),
            remote_semantic_digest=str(
                raw.get("remote_semantic_digest") or ""
            ).removeprefix("sha256:"),
            commands=commands,
            unsupported_differences=tuple(_mapping(item) for item in unsupported),
            conflicts=tuple(_mapping(item) for item in conflicts),
            complete=bool(raw.get("complete")),
            server_preview_token=str(raw.get("server_preview_token") or ""),
        )
        if plan.plan_digest != digest or raw.get("plan_digest") != f"sha256:{digest}":
            raise ValueError("P2P_RECONCILIATION_PLAN_INVALID: digest does not match")
        return plan

    @staticmethod
    def _blocked_status(
        classification: DriftClassification,
        code: str,
        message: str,
        *,
        project_uuid: str = "",
    ) -> ReplicaDriftStatus:
        return ReplicaDriftStatus(
            status="blocked",
            classification=classification,
            project_uuid=project_uuid,
            findings=(DriftFinding(code, message, True),),
            next_actions=("p2p drift backup", "p2p drift discard --confirm"),
        )


def _entity(
    snapshot: CanonicalMemorySnapshot, entity_type: str, entity_id: str
) -> CanonicalEntity | None:
    return next(
        (
            item
            for item in snapshot.entities
            if item.entity_type == entity_type and item.technical_id == entity_id
        ),
        None,
    )


def _domain_descriptor(entity: CanonicalEntity | None) -> Mapping[str, object] | None:
    if entity is None:
        return None
    document = entity.payload.get("document")
    if not isinstance(document, Mapping):
        return None
    domain = document.get("project_domain")
    if not isinstance(domain, Mapping):
        return None
    descriptor = domain.get("descriptor")
    return descriptor if isinstance(descriptor, Mapping) else None


def _replication_version(entity: CanonicalEntity) -> int:
    return replication_entity_version(
        kind=entity.entity_type,
        entity_id=entity.technical_id,
        payload_contract="p2p-canonical-memory/v1",
        payload=entity.payload,
    )


def _tar_filter(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    return info


def _verify_forensic_archive(path: Path) -> tuple[int, int]:
    file_count = 0
    byte_count = 0
    with tarfile.open(path, "r") as archive:
        for item in archive.getmembers():
            pure = PurePosixPath(item.name)
            if pure.is_absolute() or ".." in pure.parts or not pure.parts or pure.parts[0] != ".p2p":
                raise ValueError("P2P_DRIFT_BACKUP_FAILED: forensic archive is unsafe")
            if item.isfile():
                file_count += 1
                byte_count += item.size
    return file_count, byte_count


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_RECONCILIATION_PLAN_INVALID: entry is invalid")
    return dict(value)


def _command_from_mapping(value: object) -> ReconciliationCommand:
    raw = _mapping(value)
    payload = _mapping(raw.get("payload"))
    preconditions = raw.get("entity_preconditions")
    if not isinstance(preconditions, list):
        raise ValueError("P2P_RECONCILIATION_PLAN_INVALID: preconditions are invalid")
    return ReconciliationCommand(
        command=str(raw.get("command") or ""),
        payload_contract=str(raw.get("payload_contract") or ""),
        payload=payload,
        entity_preconditions=tuple(_mapping(item) for item in preconditions),
        expected_effect=str(raw.get("expected_effect") or ""),
    )


def _last_confirmed_batch_id(root: Path, revision: int) -> str:
    inbox = root / ".p2p" / "local" / "project-replication" / "inbox"
    if not inbox.is_dir() or inbox.is_symlink():
        return ""
    for path in sorted(inbox.glob("*.json")):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if (
            isinstance(value, Mapping)
            and value.get("contract") == "p2p-replica-inbox-entry/v1"
            and value.get("project_revision") == revision
        ):
            return str(value.get("change_batch_id") or "")[:256]
    return ""

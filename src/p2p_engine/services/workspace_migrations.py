from __future__ import annotations

import hashlib
import os
import secrets
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml

from p2p_engine.core.workspace_schema import (
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    LOCK_ABSENT,
    LOCK_STALE,
    MIGRATION_STATUS_APPLIED,
    MIGRATION_STATUS_BLOCKED,
    MIGRATION_STATUS_NO_OP,
    MIGRATION_STATUS_RECOVERY_REQUIRED,
    MIGRATION_STATUS_ROLLED_BACK,
    MIGRATION_STATUS_STAGE_FAILED,
    MIGRATION_STATUS_STALE_PLAN,
    MigrationApplyResult,
    MigrationRecoveryResult,
    MigrationRecoveryStatus,
)
from p2p_engine.foundation.files import read_yaml_mapping
from p2p_engine.services.candidate_workspace import CandidateWorkspaceView
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.project_maturity import domain_state_payload, normalize_project_domain
from p2p_engine.services.project_metadata import ProjectMetadataService
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    render_decision_projection,
    render_proposal_projection,
)
from p2p_engine.core.project_metadata import ProjectMetadataPatch
from p2p_engine.core.project_verticals import VerticalMigrationCandidate
from p2p_engine.services.workspace_compatibility import (
    SEMANTIC_AUDIT_ACTOR,
    SEMANTIC_AUDIT_TIMESTAMP,
    WorkspaceCompatibilityService,
)
from p2p_engine.services.workspace_schema import WorkspaceSchemaService
from p2p_engine.services.workspace_transactions import (
    DurableTransactionFilesystem,
    MigrationLockService,
    physical_sha256,
    utc_now_iso,
)


FailureInjector = Callable[[str, str], None]


class WorkspaceMigrationService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        compatibility: WorkspaceCompatibilityService,
        schema_service: WorkspaceSchemaService,
        lock_service: MigrationLockService | None = None,
        transaction_filesystem: DurableTransactionFilesystem | None = None,
        failure_injector: FailureInjector | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.compatibility = compatibility
        self.schema_service = schema_service
        self.lock_service = lock_service or MigrationLockService(root=self.root, p2p_dir=self.p2p_dir)
        self.filesystem = transaction_filesystem or DurableTransactionFilesystem(
            root=self.root,
            p2p_dir=self.p2p_dir,
            lock_service=self.lock_service,
        )
        self.failure_injector = failure_injector
        self.clock = clock

    def apply(
        self,
        *,
        target_version: int,
        owner_inputs: Mapping[str, object] | None,
        plan_fingerprint: str,
        actor: str,
        confirm: bool,
    ) -> MigrationApplyResult:
        actor = str(actor or "").strip()
        if not actor:
            return self._blocked(target_version, plan_fingerprint, "Explicit actor identity is required.")
        if not confirm:
            return self._blocked(target_version, plan_fingerprint, "Explicit --confirm is required.")
        plan = self.compatibility.plan(target_version, owner_inputs)
        if plan.status == MIGRATION_STATUS_NO_OP:
            return MigrationApplyResult(
                status=MIGRATION_STATUS_NO_OP,
                source_version=plan.source_version,
                target_version=plan.target_version,
                plan_fingerprint_sha256=plan.fingerprint_sha256,
                message="Workspace schema is already current.",
            )
        if not plan.applicable:
            return self._blocked(
                target_version,
                plan_fingerprint,
                "Migration plan contains unresolved blockers or runtime prerequisites.",
                source_version=plan.source_version,
            )
        if not plan_fingerprint or plan.fingerprint_sha256 != plan_fingerprint:
            return MigrationApplyResult(
                status=MIGRATION_STATUS_STALE_PLAN,
                source_version=plan.source_version,
                target_version=plan.target_version,
                plan_fingerprint_sha256=plan.fingerprint_sha256,
                message="Reviewed migration fingerprint does not match the recomputed plan.",
            )
        if not self._actor_authorized(actor, plan.owner_inputs):
            return self._blocked(
                target_version,
                plan_fingerprint,
                f"Actor {actor} is not an owner authorized to apply workspace migration.",
                source_version=plan.source_version,
            )
        recovery = self.recovery_status()
        if recovery.required:
            return self._blocked(
                target_version,
                plan_fingerprint,
                f"Recovery is required for transaction {recovery.transaction_id} before a new apply.",
                source_version=plan.source_version,
            )

        transaction_id = _new_transaction_id()
        try:
            self.lock_service.acquire(transaction_id, owner=actor)
        except ValueError as exc:
            return self._blocked(
                target_version,
                plan_fingerprint,
                str(exc),
                source_version=plan.source_version,
            )

        transaction_dir: Path | None = None
        journal: dict[str, object] = {}
        try:
            locked_plan = self.compatibility.plan(
                target_version,
                owner_inputs,
                active_transaction_id=transaction_id,
            )
            if (
                not locked_plan.applicable
                or locked_plan.fingerprint_sha256 != plan_fingerprint
                or locked_plan.source_version != plan.source_version
            ):
                self.lock_service.release(transaction_id)
                return MigrationApplyResult(
                    status=MIGRATION_STATUS_STALE_PLAN,
                    source_version=locked_plan.source_version,
                    target_version=target_version,
                    plan_fingerprint_sha256=locked_plan.fingerprint_sha256,
                    transaction_id=transaction_id,
                    message="Migration sources changed before lock-protected staging.",
                )
            self._inject("before_staging", "")
            transaction_dir = self.filesystem.create_transaction(transaction_id)
            candidates = self._render_apply_candidates(locked_plan.candidate_files, plan_fingerprint, actor)
            target_order = self._target_order(candidates)
            journal = self._build_journal(
                transaction_id=transaction_id,
                plan=locked_plan,
                actor=actor,
                target_order=target_order,
            )
            originals = journal["originals"]
            candidate_meta = journal["candidates"]
            assert isinstance(originals, dict)
            assert isinstance(candidate_meta, dict)
            for target in target_order:
                originals[target] = self.filesystem.snapshot_target(transaction_dir, target)
                candidate_meta[target] = self.filesystem.stage_candidate(
                    transaction_dir,
                    target,
                    candidates[target],
                )
            self.filesystem.write_journal(transaction_dir, journal)
            self._inject("after_journal", "")
            self._inject("before_candidate_validation", "")
            self._validate_candidates(candidates, originals)
            journal["state"] = "validated"
            self.filesystem.write_journal(transaction_dir, journal)

            for target in target_order:
                self._inject("before_replace", target)
                self._assert_preimage(target, originals[target])
                original = originals[target]
                assert isinstance(original, dict)
                mode = original.get("mode")
                result = self.filesystem.replace_target(
                    target,
                    candidates[target],
                    mode=mode if isinstance(mode, int) else None,
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

            final_status = self.schema_service.status()
            expected_state = (
                "current"
                if target_version == CURRENT_WORKSPACE_SCHEMA_VERSION
                else "upgrade_available"
            )
            if final_status.current_version != target_version or final_status.state != expected_state:
                raise ValueError("Committed workspace schema did not validate as the requested target version")
            journal["state"] = "committed"
            journal["committed_at"] = self.clock()
            self.filesystem.write_journal(transaction_dir, journal)
            self._inject("before_lock_cleanup", "")
            changed = tuple(target_order)
            semantic_hashes = {
                operation.target: str(operation.candidate_semantic_sha256)
                for operation in locked_plan.operations
                if operation.target in candidates and operation.candidate_semantic_sha256
            }
            physical_hashes = {target: hashlib.sha256(candidates[target]).hexdigest() for target in target_order}
            self.filesystem.cleanup(transaction_dir)
            self.lock_service.release(transaction_id)
            return MigrationApplyResult(
                status=MIGRATION_STATUS_APPLIED,
                source_version=locked_plan.source_version,
                target_version=locked_plan.target_version,
                plan_fingerprint_sha256=locked_plan.fingerprint_sha256,
                transaction_id=transaction_id,
                changed_paths=changed,
                semantic_hashes=semantic_hashes,
                physical_hashes=physical_hashes,
                message="Workspace migration committed successfully.",
            )
        except Exception as exc:
            if transaction_dir is None:
                self.lock_service.release(transaction_id)
                return MigrationApplyResult(
                    status=MIGRATION_STATUS_STAGE_FAILED,
                    source_version=plan.source_version,
                    target_version=target_version,
                    plan_fingerprint_sha256=plan_fingerprint,
                    transaction_id=transaction_id,
                    message=str(exc),
                )
            replaced = journal.get("replaced", [])
            if not isinstance(replaced, list) or not replaced:
                self.filesystem.cleanup(transaction_dir)
                self.lock_service.release(transaction_id)
                return MigrationApplyResult(
                    status=MIGRATION_STATUS_STAGE_FAILED,
                    source_version=plan.source_version,
                    target_version=target_version,
                    plan_fingerprint_sha256=plan_fingerprint,
                    transaction_id=transaction_id,
                    message=str(exc),
                )
            rollback = self._rollback_journal(transaction_dir, journal)
            return MigrationApplyResult(
                status=rollback.status,
                source_version=plan.source_version,
                target_version=target_version,
                plan_fingerprint_sha256=plan_fingerprint,
                transaction_id=transaction_id,
                restored_paths=rollback.restored_paths,
                message=f"Migration failed: {exc}. {rollback.message}",
                recovery_required=rollback.recovery_required,
            )

    def recovery_status(self) -> MigrationRecoveryStatus:
        lock = self.lock_service.status()
        transaction_ids: list[str] = []
        if self.lock_service.transactions_root.exists():
            transaction_ids = sorted(
                path.name
                for path in self.lock_service.transactions_root.iterdir()
                if path.is_dir() and (path / "journal.yml").exists()
            )
        if lock.state == LOCK_ABSENT and not transaction_ids:
            return MigrationRecoveryStatus(required=False, lock=lock, message="No migration recovery is required.")
        transaction_id = lock.transaction_id or (transaction_ids[0] if transaction_ids else "")
        journal_state = "unknown"
        if transaction_id:
            transaction_dir = self.lock_service.transactions_root / transaction_id
            if (transaction_dir / "journal.yml").exists():
                try:
                    journal = self.filesystem.read_journal(transaction_dir)
                    journal_state = str(journal.get("state") or "unknown")
                except ValueError:
                    journal_state = "invalid"
        return MigrationRecoveryStatus(
            required=True,
            lock=lock,
            transaction_id=transaction_id,
            journal_state=journal_state,
            available_actions=("rollback", "resume") if journal_state not in {"invalid", "unknown"} else ("rollback",),
            message="Interrupted or locked workspace migration requires explicit recovery.",
        )

    def rollback(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ) -> MigrationRecoveryResult:
        if not confirm or not str(actor or "").strip():
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_BLOCKED,
                transaction_id=transaction_id,
                message="Explicit actor and confirmation are required for rollback.",
                recovery_required=True,
            )
        recovery = self.recovery_status()
        if not recovery.required:
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_NO_OP,
                transaction_id=transaction_id,
                message="No recovery transaction exists.",
            )
        if recovery.transaction_id != transaction_id:
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_BLOCKED,
                transaction_id=transaction_id,
                message=f"Recovery belongs to transaction {recovery.transaction_id}.",
                recovery_required=True,
            )
        transaction_dir = self.lock_service.transactions_root / transaction_id
        if not self._recovery_actor_authorized(actor, transaction_dir):
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_BLOCKED,
                transaction_id=transaction_id,
                message=f"Actor {actor} is not an owner authorized to recover workspace migration.",
                recovery_required=True,
            )
        if recovery.lock.state == LOCK_STALE and recovery.journal_state == "unknown":
            self.lock_service.release(transaction_id)
            if transaction_dir.exists():
                self.filesystem.cleanup(transaction_dir)
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_ROLLED_BACK,
                transaction_id=transaction_id,
                message="Stale migration lock without a transaction journal was removed.",
            )
        try:
            journal = self.filesystem.read_journal(transaction_dir)
        except ValueError as exc:
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_RECOVERY_REQUIRED,
                transaction_id=transaction_id,
                message=str(exc),
                recovery_required=True,
            )
        return self._rollback_journal(transaction_dir, journal)

    def resume(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ) -> MigrationRecoveryResult:
        if not confirm or not str(actor or "").strip():
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_BLOCKED,
                transaction_id=transaction_id,
                message="Explicit actor and confirmation are required for resume.",
                recovery_required=True,
            )
        recovery = self.recovery_status()
        if not recovery.required or recovery.transaction_id != transaction_id:
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_BLOCKED,
                transaction_id=transaction_id,
                message="Requested recovery transaction is not active.",
                recovery_required=recovery.required,
            )
        transaction_dir = self.lock_service.transactions_root / transaction_id
        if not self._recovery_actor_authorized(actor, transaction_dir):
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_BLOCKED,
                transaction_id=transaction_id,
                message=f"Actor {actor} is not an owner authorized to recover workspace migration.",
                recovery_required=True,
            )
        try:
            journal = self.filesystem.read_journal(transaction_dir)
            target_order = _string_list(journal.get("target_order"), "target_order")
            replaced = _string_list(journal.get("replaced"), "replaced")
            originals = _mapping(journal.get("originals"), "originals")
            candidates = _mapping(journal.get("candidates"), "candidates")
            for target in replaced:
                candidate = _mapping(candidates.get(target), f"candidates.{target}")
                if physical_sha256(self.filesystem.target_path(target)) != candidate.get("physical_sha256"):
                    raise ValueError(f"Already replaced target changed externally: {target}")
            for target in target_order:
                if target in replaced:
                    continue
                self._assert_preimage(target, _mapping(originals.get(target), f"originals.{target}"))
                content = self.filesystem.read_candidate(transaction_dir, target)
                candidate = _mapping(candidates.get(target), f"candidates.{target}")
                if hashlib.sha256(content).hexdigest() != candidate.get("physical_sha256"):
                    raise ValueError(f"Staged candidate hash changed: {target}")
            changed: list[str] = []
            for target in target_order:
                if target in replaced:
                    continue
                original = _mapping(originals.get(target), f"originals.{target}")
                content = self.filesystem.read_candidate(transaction_dir, target)
                mode = original.get("mode")
                self.filesystem.replace_target(target, content, mode=mode if isinstance(mode, int) else None)
                replaced.append(target)
                changed.append(target)
                journal["replaced"] = replaced
                journal["state"] = "committing"
                self.filesystem.write_journal(transaction_dir, journal)
            target_version = int(journal.get("target_version") or 0)
            if self.schema_service.status().current_version != target_version:
                raise ValueError("Resumed migration did not produce the expected workspace schema")
            self.filesystem.cleanup(transaction_dir)
            self.lock_service.release(transaction_id)
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_APPLIED,
                transaction_id=transaction_id,
                changed_paths=tuple(changed),
                message="Interrupted migration resumed and completed.",
            )
        except (OSError, ValueError) as exc:
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_RECOVERY_REQUIRED,
                transaction_id=transaction_id,
                message=str(exc),
                recovery_required=True,
            )

    def _build_journal(
        self,
        *,
        transaction_id: str,
        plan: Any,
        actor: str,
        target_order: list[str],
    ) -> dict[str, object]:
        return {
            "journal_version": 1,
            "transaction_id": transaction_id,
            "state": "staging",
            "pid": os.getpid(),
            "actor": actor,
            "created_at": self.clock(),
            "plan_fingerprint_sha256": plan.fingerprint_sha256,
            "source_version": plan.source_version,
            "target_version": plan.target_version,
            "target_order": target_order,
            "originals": {},
            "candidates": {},
            "replaced": [],
            "physical_results": {},
        }

    def _render_apply_candidates(
        self,
        candidates: Mapping[str, bytes],
        plan_fingerprint: str,
        actor: str,
    ) -> dict[str, bytes]:
        applied_at = self.clock()
        rendered: dict[str, bytes] = {}
        for path, content in candidates.items():
            rendered[path] = (
                content.replace(SEMANTIC_AUDIT_TIMESTAMP.encode(), applied_at.encode())
                .replace(SEMANTIC_AUDIT_ACTOR.encode(), actor.encode())
                .replace(b"__P2P_PLAN_FINGERPRINT__", plan_fingerprint.encode())
            )
        return rendered

    def _validate_candidates(
        self,
        candidates: dict[str, bytes],
        originals: Mapping[str, object],
    ) -> None:
        preserved: dict[str, bytes | None] = {}
        for path, metadata in originals.items():
            item = _mapping(metadata, f"originals.{path}")
            target = self.filesystem.target_path(path)
            preserved[path] = target.read_bytes() if item.get("exists") else None
        view = CandidateWorkspaceView(
            root=self.root,
            candidates=candidates,
            preserved=preserved,
            owned_paths=set(candidates),
        )
        for path in sorted(candidates):
            if path.endswith((".yml", ".yaml")):
                view.read_yaml_mapping(path)
            else:
                view.read_bytes(path)
        self._validate_owned_candidates(view, candidates, preserved)
        view.assert_owned_reads_used_candidates()
        schema_path = ".p2p/project/workspace-schema.yml"
        if schema_path in candidates:
            payload = view.read_yaml_mapping(schema_path)
            raw = payload.get("workspace_schema")
            candidate_version = raw.get("current_version") if isinstance(raw, dict) else None
            if (
                isinstance(candidate_version, bool)
                or not isinstance(candidate_version, int)
                or candidate_version < 1
                or candidate_version > CURRENT_WORKSPACE_SCHEMA_VERSION
            ):
                raise ValueError("Candidate workspace schema is invalid or unsupported by this runtime")

    def _validate_owned_candidates(
        self,
        view: CandidateWorkspaceView,
        candidates: Mapping[str, bytes],
        preserved: Mapping[str, bytes | None],
    ) -> None:
        domain_path = ".p2p/project/domain.yml"
        project_path = ".p2p/project.yml"
        if domain_path in candidates:
            domain = view.read_yaml_mapping(domain_path)
            name = str(domain.get("name") or domain.get("type") or "")
            normalized = normalize_project_domain(name)
            expected = domain_state_payload(normalized)
            for field in ("status", "type", "name", "template"):
                if domain.get(field) != expected.get(field):
                    raise ValueError(f"Domain migration candidate has invalid `{field}`.")
            if project_path in candidates or preserved.get(project_path) is not None:
                project = view.read_yaml_mapping(project_path)
                manifest = project.get("project")
                manifest_domain = str(manifest.get("domain") or "") if isinstance(manifest, Mapping) else ""
                if normalize_project_domain(manifest_domain) != normalized:
                    raise ValueError("Domain migration candidate disagrees with project manifest domain.")

        permissions_path = ".p2p/project/permissions.yml"
        if permissions_path in candidates:
            PermissionsService(root=self.root, p2p_dir=self.p2p_dir).validate_policy_payload(
                view.read_yaml_mapping(permissions_path),
                require_single_owner=True,
            )

        if project_path in candidates:
            original_bytes = preserved.get(project_path)
            if original_bytes is None:
                raise ValueError("Project metadata migration requires an existing project manifest.")
            original = yaml.safe_load(original_bytes)
            candidate = view.read_yaml_mapping(project_path)
            if not isinstance(original, dict):
                raise ValueError("Existing project manifest must be a mapping.")
            before_project = original.get("project") if isinstance(original.get("project"), Mapping) else {}
            after_project = candidate.get("project") if isinstance(candidate.get("project"), Mapping) else {}
            before_workflow = original.get("workflow") if isinstance(original.get("workflow"), Mapping) else {}
            after_workflow = candidate.get("workflow") if isinstance(candidate.get("workflow"), Mapping) else {}
            values: dict[str, str] = {}
            for field, before, after in (
                ("status", before_project.get("status"), after_project.get("status")),
                ("workflow_phase", before_workflow.get("current_phase"), after_workflow.get("current_phase")),
                (
                    "current_objective",
                    before_workflow.get("current_objective") or before_workflow.get("next_goal"),
                    after_workflow.get("current_objective") or after_workflow.get("next_goal"),
                ),
            ):
                if before != after:
                    values[field] = str(after or "")
            ProjectMetadataService(root=self.root, p2p_dir=self.p2p_dir).validate_candidate(
                original,
                candidate,
                ProjectMetadataPatch(actor="migration", values=values),
            )

        vertical_paths = {
            ".p2p/project/vertical.yml",
            ".p2p/project/vertical.lock.yml",
            ".p2p/project/definition.yml",
            ".p2p/project/rubrics.yml",
        }
        selected = vertical_paths.intersection(candidates)
        if selected:
            definition_only_v2 = (
                selected == {".p2p/project/definition.yml"}
                and ".p2p/project/questions.yml" in candidates
            )
            if selected != vertical_paths and not definition_only_v2:
                raise ValueError("Vertical migration must own the complete four-artifact set.")
            definition = view.read_yaml_mapping(".p2p/project/definition.yml").get("project_definition")
            if not isinstance(definition, Mapping):
                raise ValueError("Vertical migration candidate has invalid root mappings.")
            sections = definition.get("sections")
            if not isinstance(sections, list) or any(
                isinstance(item, Mapping) and item.get("open_questions")
                for item in sections
            ):
                raise ValueError("Workspace schema v2 definition candidate retains legacy open questions.")
            if not definition_only_v2:
                active = view.read_yaml_mapping(".p2p/project/vertical.yml").get("project_vertical")
                lock = view.read_yaml_mapping(".p2p/project/vertical.lock.yml").get("project_vertical_lock")
                if not isinstance(active, Mapping) or not isinstance(lock, Mapping):
                    raise ValueError("Vertical migration candidate has invalid root mappings.")
                checksum = lock.get("checksum")
                if not isinstance(checksum, Mapping):
                    raise ValueError("Vertical migration lock candidate has no checksum mapping.")
                vertical = VerticalMigrationCandidate(
                    vertical_id=str(active.get("active_vertical_id") or ""),
                    profile=str(definition.get("profile") or "default"),
                    modules=tuple(str(item) for item in definition.get("modules", []) if isinstance(item, str)),
                    checksum=str(checksum.get("value") or ""),
                    candidate_files={path: candidates[path] for path in vertical_paths},
                )
                ProjectVerticalService(
                    root=self.root,
                    p2p_dir=self.p2p_dir,
                    proposal_summaries=lambda: [],
                    find_proposal_dir=lambda proposal_id: self.p2p_dir / "proposals" / proposal_id,
                ).validate_migration_candidate(vertical)

        questions_path = ".p2p/project/questions.yml"
        if questions_path in candidates:
            ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir).parse_payload(
                view.read_yaml_mapping(questions_path),
                target=questions_path,
            )

        ledger_targets = sorted(
            path
            for path in candidates
            if path.startswith(".p2p/proposals/")
            and path.endswith("/decision-events.yml")
        )
        codec = ProposalDecisionLedgerCodec()
        for ledger_path in ledger_targets:
            proposal_dir = ledger_path.rsplit("/", 1)[0]
            directory_name = proposal_dir.rsplit("/", 1)[-1]
            proposal_id = "-".join(directory_name.split("-", 2)[:2])
            ledger = codec.loads(
                view.read_bytes(ledger_path),
                expected_proposal_id=proposal_id,
            )
            proposal_path = f"{proposal_dir}/proposal.md"
            decision_path = f"{proposal_dir}/decision.md"
            proposal_text = view.read_bytes(proposal_path).decode("utf-8")
            decision_text = view.read_bytes(decision_path).decode("utf-8")
            if (
                render_proposal_projection(proposal_text, ledger.effective_state)
                != proposal_text
            ):
                raise ValueError(
                    f"Proposal projection does not match migrated ledger: {proposal_path}"
                )
            expected_decision = render_decision_projection(
                proposal_id,
                ledger.events[-1] if ledger.events else None,
                empty_state=ledger.effective_state,
            )
            if expected_decision != decision_text:
                raise ValueError(
                    f"Decision projection does not match migrated ledger: {decision_path}"
                )

    def _assert_preimage(self, target: str, original: Mapping[str, object]) -> None:
        current = physical_sha256(self.filesystem.target_path(target))
        expected = original.get("physical_sha256") if original.get("exists") else None
        if current != expected:
            raise ValueError(f"Target preimage changed before replacement: {target}")

    def _rollback_journal(
        self,
        transaction_dir: Path,
        journal: dict[str, object],
    ) -> MigrationRecoveryResult:
        transaction_id = str(journal.get("transaction_id") or transaction_dir.name)
        try:
            replaced = _string_list(journal.get("replaced"), "replaced")
            originals = _mapping(journal.get("originals"), "originals")
            candidates = _mapping(journal.get("candidates"), "candidates")
        except ValueError as exc:
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_RECOVERY_REQUIRED,
                transaction_id=transaction_id,
                message=str(exc),
                recovery_required=True,
            )
        restored: list[str] = []
        blocked: list[str] = []
        for target in reversed(replaced):
            candidate = _mapping(candidates.get(target), f"candidates.{target}")
            if physical_sha256(self.filesystem.target_path(target)) != candidate.get("physical_sha256"):
                blocked.append(target)
                continue
            original = _mapping(originals.get(target), f"originals.{target}")
            if original.get("exists"):
                content = self.filesystem.read_original(transaction_dir, target)
                mode = original.get("mode")
                self.filesystem.replace_target(target, content, mode=mode if isinstance(mode, int) else None)
            else:
                self.filesystem.remove_target(target)
            restored.append(target)
        if blocked:
            journal["state"] = "recovery_required"
            journal["rollback_blocked_targets"] = blocked
            journal["restored"] = restored
            self.filesystem.write_journal(transaction_dir, journal)
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_RECOVERY_REQUIRED,
                transaction_id=transaction_id,
                restored_paths=tuple(restored),
                message="Rollback preserved externally changed targets: " + ", ".join(blocked),
                recovery_required=True,
            )
        self.filesystem.cleanup(transaction_dir)
        try:
            self.lock_service.release(transaction_id)
        except ValueError as exc:
            return MigrationRecoveryResult(
                status=MIGRATION_STATUS_RECOVERY_REQUIRED,
                transaction_id=transaction_id,
                restored_paths=tuple(restored),
                message=f"Targets restored but lock cleanup requires recovery: {exc}",
                recovery_required=True,
            )
        return MigrationRecoveryResult(
            status=MIGRATION_STATUS_ROLLED_BACK,
            transaction_id=transaction_id,
            restored_paths=tuple(restored),
            message="Migration replacements were rolled back completely.",
        )

    def _actor_authorized(self, actor: str, owner_inputs: Mapping[str, object]) -> bool:
        path = self.p2p_dir / "project" / "permissions.yml"
        if path.exists():
            try:
                payload = read_yaml_mapping(path, default={})
            except ValueError:
                return False
            identities = payload.get("identities")
            identity = identities.get(actor) if isinstance(identities, dict) else None
            return isinstance(identity, dict) and identity.get("role") == "owner"
        owner = owner_inputs.get("owner")
        if not isinstance(owner, dict):
            return False
        return actor in {str(owner.get("id") or ""), str(owner.get("name") or "")}

    def _recovery_actor_authorized(self, actor: str, transaction_dir: Path) -> bool:
        if (self.p2p_dir / "project" / "permissions.yml").exists():
            return self._actor_authorized(actor, {})
        try:
            journal = self.filesystem.read_journal(transaction_dir)
        except ValueError:
            return False
        return str(journal.get("actor") or "") == actor

    def _target_order(self, candidates: Mapping[str, bytes]) -> list[str]:
        schema = ".p2p/project/workspace-schema.yml"
        regular = sorted(path for path in candidates if path != schema)
        return regular + ([schema] if schema in candidates else [])

    def _inject(self, stage: str, target: str) -> None:
        if self.failure_injector is not None:
            self.failure_injector(stage, target)

    def _blocked(
        self,
        target_version: int,
        fingerprint: str,
        message: str,
        *,
        source_version: int = 0,
    ) -> MigrationApplyResult:
        return MigrationApplyResult(
            status=MIGRATION_STATUS_BLOCKED,
            source_version=source_version,
            target_version=target_version,
            plan_fingerprint_sha256=fingerprint,
            message=message,
        )


def _new_transaction_id() -> str:
    return f"migration-{secrets.token_hex(8)}"


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Migration journal field {field} must be a mapping")
    return value


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Migration journal field {field} must be a string sequence")
    return value

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from p2p_engine.core.authority import AuthorityBasis, AuthorityContext, AuthorityEvidence
from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    MutationResult,
    source_precondition,
)
from p2p_engine.core.project_identity import (
    IDENTITY_TRANSITION_MATRIX,
    CopyCollisionAssessment,
    CopyIntent,
    DetachIdentityContract,
    LineageRelation,
    LineageVisibility,
    ProjectIdentity,
    ProjectIdentityMutationPreview,
    ProjectIdentityMutationResult,
    ProjectIdentityStatus,
    ProjectLineage,
    ProjectMode,
    ProjectUuid,
    RemoteProjectId,
    ReplicaId,
    ReplicaIdentityContract,
    ServerInstanceId,
    SourceMemoryRevision,
    TransferIdentityContract,
    project_identity_from_mapping,
)
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.project_identity import (
    PROJECT_MANIFEST_PATH,
    FilesystemProjectIdentityStore,
)

PROJECT_IDENTITY_ADOPT_OPERATION = "project-identity-adopt"
PROJECT_IDENTITY_DERIVE_OPERATION = "project-identity-derive"
PROJECT_IDENTITY_ADOPT_CAPABILITY = "project.identity.adopt"
PROJECT_IDENTITY_DERIVE_CAPABILITY = "project.identity.derive"


class ProjectIdentityStore(Protocol):
    """Minimal storage port needed by project-identity application services."""

    def exists(self) -> bool: ...

    def complete(self) -> bool: ...

    def load(self) -> ProjectIdentity: ...

    def manifest(self) -> dict[str, object]: ...

    def manifest_name(self) -> str: ...

    def candidate_documents(
        self,
        identity: ProjectIdentity,
        *,
        allow_project_uuid_change: bool = False,
    ) -> dict[str, bytes]: ...

    def source_revision(self) -> SourceMemoryRevision: ...


class ProjectIdentityService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        store: ProjectIdentityStore | None = None,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.store = store or FilesystemProjectIdentityStore(root=self.root, p2p_dir=self.p2p_dir)
        self.authority = authority or ProjectAuthorityService(root=self.root, p2p_dir=self.p2p_dir)
        self.receipts = receipts or MutationReceiptService(root=self.root, p2p_dir=self.p2p_dir)
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root, p2p_dir=self.p2p_dir
        )
        self.codec = AuthorityContractCodec()

    def status(self) -> ProjectIdentityStatus:
        manifest = self.root / PROJECT_MANIFEST_PATH
        if not manifest.exists():
            return ProjectIdentityStatus(
                state="uninitialized",
                identity=None,
                blockers=("Project manifest is missing.",),
                suggested_command="p2p init <name> --starter generic",
            )
        if not self.store.exists():
            return ProjectIdentityStatus(
                state="adoption_required",
                identity=None,
                blockers=("Existing project has no stable project identity contract.",),
                suggested_command=(
                    "p2p project identity adopt preview --operation-key <key> "
                    "--actor <owner> --format json"
                ),
            )
        if not self.store.complete():
            return ProjectIdentityStatus(
                state="invalid",
                identity=None,
                blockers=("Canonical identity and local replica records are incomplete.",),
                suggested_command="Restore the missing identity record from a verified backup.",
            )
        try:
            identity = self.store.load()
        except ValueError as exc:
            return ProjectIdentityStatus(
                state="invalid",
                identity=None,
                blockers=(str(exc),),
                suggested_command=(
                    "Inspect `p2p project identity status --format json`; do not edit IDs manually."
                ),
            )
        return ProjectIdentityStatus(state="valid", identity=identity)

    def show(self) -> ProjectIdentity:
        status = self.status()
        if status.identity is None or not status.mutable:
            detail = "; ".join(status.blockers) or status.state
            raise ValueError(f"P2P_PROJECT_IDENTITY_INVALID: {detail}")
        return status.identity

    def require_mutable(self, operation: str) -> ProjectIdentity:
        status = self.status()
        if status.state == "adoption_required":
            raise ValueError(
                "P2P_PROJECT_IDENTITY_ADOPTION_REQUIRED: existing project must complete "
                "the explicit identity adoption workflow before mutation; "
                f"blocked operation `{operation}`"
            )
        if not status.mutable or status.identity is None:
            detail = "; ".join(status.blockers) or status.state
            raise ValueError(
                "P2P_PROJECT_IDENTITY_INVALID: project identity blocks mutation "
                f"`{operation}`: {detail}"
            )
        return status.identity

    @staticmethod
    def transition_matrix() -> list[dict[str, object]]:
        return [item.to_dict() for item in IDENTITY_TRANSITION_MATRIX]

    def assess_copy(
        self,
        *,
        observed_project_uuid: str,
        observed_replica_id: str = "",
        intent: str = "",
    ) -> CopyCollisionAssessment:
        current = self.show()
        observed_project = ProjectUuid(observed_project_uuid)
        observed_replica = ReplicaId(observed_replica_id) if observed_replica_id else None
        try:
            selected = CopyIntent(intent) if intent else None
        except ValueError as exc:
            raise ValueError("P2P_PROJECT_COPY_INTENT_INVALID: copy intent is unsupported") from exc
        if observed_project != current.project_uuid:
            return CopyCollisionAssessment(
                state="different_project",
                project_uuid=current.project_uuid,
                local_replica_id=current.replica_id,
                observed_replica_id=observed_replica,
                selected_intent=selected,
                allowed=True,
                next_actions=(),
            )
        if observed_replica is not None and observed_replica != current.replica_id:
            return CopyCollisionAssessment(
                state="distinct_replica",
                project_uuid=current.project_uuid,
                local_replica_id=current.replica_id,
                observed_replica_id=observed_replica,
                selected_intent=selected,
                allowed=True,
                next_actions=(),
            )
        allowed = selected in {CopyIntent.same_instance, CopyIntent.read_only}
        return CopyCollisionAssessment(
            state="replica_collision",
            project_uuid=current.project_uuid,
            local_replica_id=current.replica_id,
            observed_replica_id=observed_replica,
            selected_intent=selected,
            allowed=allowed,
            next_actions=(
                "Confirm same-instance only after the previous operational copy is retired.",
                "Choose read-only inspection, register a new replica in a later linked lifecycle, or derive a new project.",
            ),
        )

    def transfer_contract(
        self,
        *,
        server_instance_id: str,
        remote_project_id: str = "",
    ) -> TransferIdentityContract:
        current = self.show()
        return TransferIdentityContract(
            project_uuid=current.project_uuid,
            server_instance_id=ServerInstanceId(server_instance_id),
            remote_project_id=(RemoteProjectId(remote_project_id) if remote_project_id else None),
        )

    def replica_contract(self, *, move: bool, operation_key: str) -> ReplicaIdentityContract:
        current = self.show()
        target = (
            current.replica_id
            if move and current.replica_id is not None
            else ReplicaId.for_project_operation(current.project_uuid, operation_key)
        )
        assert target is not None
        return ReplicaIdentityContract(
            project_uuid=current.project_uuid,
            source_replica_id=current.replica_id,
            target_replica_id=target,
            move=move,
        )

    def detach_contract(
        self,
        *,
        operation_key: str,
        retain_lineage: bool = True,
    ) -> DetachIdentityContract:
        current = self.show()
        target = ProjectUuid.for_operation(current.project_uuid, operation_key)
        return DetachIdentityContract(
            source_project_uuid=current.project_uuid,
            detached_project_uuid=target,
            detached_replica_id=ReplicaId.for_project_operation(target, operation_key),
            source_revision=self.store.source_revision(),
            retain_lineage=retain_lineage,
        )

    def preview_adoption(
        self,
        *,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
    ) -> ProjectIdentityMutationPreview:
        validate_idempotency_key(operation_key)
        status = self.status()
        if status.state != "adoption_required":
            raise ValueError(
                "P2P_PROJECT_IDENTITY_ADOPTION_NOT_APPLICABLE: adoption requires an "
                "identity-less, otherwise initialized project"
            )
        source_revision = self.store.source_revision()
        project_uuid = ProjectUuid.for_operation(None, f"{operation_key}:{source_revision.sha256}")
        candidate = ProjectIdentity(
            project_uuid=project_uuid,
            display_name=self.store.manifest_name(),
            mode=ProjectMode.standalone,
            replica_id=ReplicaId.for_project_operation(project_uuid, operation_key),
        )
        authority = self._authority(
            capability=PROJECT_IDENTITY_ADOPT_CAPABILITY,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
        )
        candidates = self.store.candidate_documents(candidate)
        backup_path = (
            ".p2p/.internal/identity-adoption-backups/"
            f"{idempotency_key_sha256(operation_key)}/project.yml"
        )
        candidates[backup_path] = (self.root / PROJECT_MANIFEST_PATH).read_bytes()
        receipt_path = self.receipts.relative_path(operation_key)
        sources = tuple(
            source_precondition(
                path,
                (self.root / path).read_bytes()
                if (self.root / path).is_file() and not (self.root / path).is_symlink()
                else None,
            )
            for path in sorted({*candidates, receipt_path})
        )
        mutation = MutationPreviewService.build(
            operation_id=PROJECT_IDENTITY_ADOPT_OPERATION,
            targets=tuple(sorted({*candidates, receipt_path})),
            actor=authority.executor.identity_id,
            authority=AuthorityBasis.root_authority.value,
            sources=sources,
            candidate_semantics={
                "identity": candidate.to_dict(),
                "source_revision": source_revision.to_dict(),
                "backup_path": backup_path,
            },
            semantic_diff={
                "project_uuid": {"before": None, "after": candidate.project_uuid.value},
                "replica_id": {"before": None, "after": candidate.replica_id.value},
            },
            token_context={
                "operation_key_sha256": idempotency_key_sha256(operation_key),
                "authority_context_sha256": authority.authority_context_sha256,
            },
            policy_version=1,
        )
        return ProjectIdentityMutationPreview(
            kind="adopt",
            previous=None,
            candidate=candidate,
            source_revision=source_revision,
            mutation=mutation,
            backup_path=backup_path,
        )

    def preview_derivation(
        self,
        *,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        display_name: str = "",
        retain_lineage: bool = True,
        lineage_visibility: str = "preserved",
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
    ) -> ProjectIdentityMutationPreview:
        validate_idempotency_key(operation_key)
        previous = self.show()
        source_revision = self.store.source_revision()
        project_uuid = ProjectUuid.for_operation(previous.project_uuid, operation_key)
        visibility = LineageVisibility(lineage_visibility)
        lineage = previous.lineage
        if retain_lineage:
            lineage = (
                *lineage,
                ProjectLineage(
                    relation=LineageRelation.derived_from,
                    source_project_uuid=previous.project_uuid,
                    source_revision=source_revision,
                    visibility=visibility,
                ),
            )
        candidate = ProjectIdentity(
            project_uuid=project_uuid,
            display_name=display_name or previous.display_name,
            mode=ProjectMode.standalone,
            replica_id=ReplicaId.for_project_operation(project_uuid, operation_key),
            remote_binding=None,
            lineage=lineage,
        )
        authority = self._authority(
            capability=PROJECT_IDENTITY_DERIVE_CAPABILITY,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
        )
        candidates = self.store.candidate_documents(
            candidate,
            allow_project_uuid_change=True,
        )
        receipt_path = self.receipts.relative_path(operation_key)
        sources = tuple(
            source_precondition(
                path,
                (self.root / path).read_bytes()
                if (self.root / path).is_file() and not (self.root / path).is_symlink()
                else None,
            )
            for path in sorted({*candidates, receipt_path})
        )
        mutation = MutationPreviewService.build(
            operation_id=PROJECT_IDENTITY_DERIVE_OPERATION,
            targets=tuple(sorted({*candidates, receipt_path})),
            actor=authority.executor.identity_id,
            authority=AuthorityBasis.root_authority.value,
            sources=sources,
            candidate_semantics={
                "previous": previous.to_dict(),
                "candidate": candidate.to_dict(),
                "source_revision": source_revision.to_dict(),
            },
            semantic_diff={
                "project_uuid": {
                    "before": previous.project_uuid.value,
                    "after": candidate.project_uuid.value,
                },
                "replica_id": {
                    "before": previous.replica_id.value if previous.replica_id else None,
                    "after": candidate.replica_id.value if candidate.replica_id else None,
                },
                "remote_binding": {
                    "before": (
                        previous.remote_binding.to_dict()
                        if previous.remote_binding is not None
                        else None
                    ),
                    "after": None,
                },
            },
            token_context={
                "operation_key_sha256": idempotency_key_sha256(operation_key),
                "authority_context_sha256": authority.authority_context_sha256,
                "retain_lineage": retain_lineage,
                "lineage_visibility": visibility.value,
            },
            policy_version=1,
        )
        return ProjectIdentityMutationPreview(
            kind="derive",
            previous=previous,
            candidate=candidate,
            source_revision=source_revision,
            mutation=mutation,
        )

    def apply_adoption(self, **kwargs: object) -> ProjectIdentityMutationResult:
        return self._apply(kind="adopt", **kwargs)

    def apply_derivation(self, **kwargs: object) -> ProjectIdentityMutationResult:
        return self._apply(kind="derive", **kwargs)

    def _apply(
        self,
        *,
        kind: str,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        preview_token: str,
        confirm: bool,
        display_name: str = "",
        retain_lineage: bool = True,
        lineage_visibility: str = "preserved",
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
    ) -> ProjectIdentityMutationResult:
        operation = "project_identity_adopt" if kind == "adopt" else "project_identity_derive"
        replay = self._replay(
            operation_key=operation_key,
            operation=operation,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            display_name=display_name,
            retain_lineage=retain_lineage,
            lineage_visibility=lineage_visibility,
            authority_context=authority_context,
        )
        if replay is not None:
            return replay
        preview = (
            self.preview_adoption(
                operation_key=operation_key,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                authority_context=authority_context,
                channel=channel,
            )
            if kind == "adopt"
            else self.preview_derivation(
                operation_key=operation_key,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                display_name=display_name,
                retain_lineage=retain_lineage,
                lineage_visibility=lineage_visibility,
                authority_context=authority_context,
                channel=channel,
            )
        )
        if not confirm:
            return self._non_applied(preview, "blocked", "Explicit confirmation is required.")
        if preview.mutation.preview_token != preview_token:
            return self._non_applied(
                preview,
                "stale_preview",
                "P2P_PROJECT_IDENTITY_STALE_PREVIEW: identity sources or inputs changed.",
            )
        evidence = self._authority(
            capability=(
                PROJECT_IDENTITY_ADOPT_CAPABILITY
                if kind == "adopt"
                else PROJECT_IDENTITY_DERIVE_CAPABILITY
            ),
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
        )
        candidates = self.store.candidate_documents(
            preview.candidate,
            allow_project_uuid_change=kind == "derive",
        )
        if preview.backup_path:
            candidates[preview.backup_path] = (self.root / PROJECT_MANIFEST_PATH).read_bytes()
        result_payload = {
            "operation": operation,
            "operation_id": (
                PROJECT_IDENTITY_ADOPT_OPERATION
                if kind == "adopt"
                else PROJECT_IDENTITY_DERIVE_OPERATION
            ),
            "kind": kind,
            "request": {
                "display_name": display_name,
                "retain_lineage": retain_lineage,
                "lineage_visibility": lineage_visibility,
            },
            "previous_identity": (
                preview.previous.to_dict() if preview.previous is not None else None
            ),
            "current_identity": preview.candidate.to_dict(),
            "source_revision": preview.source_revision.to_dict(),
            "backup_path": preview.backup_path or None,
            "changed_paths": sorted(candidates),
        }
        request_fingerprint = self.receipts.fingerprint(
            operation=operation,
            actor=evidence.executor.identity_id,
            preview_token=preview.mutation.preview_token,
            semantic_inputs={
                "kind": kind,
                "request": result_payload["request"],
                "source_revision": preview.source_revision.to_dict(),
                "candidate": preview.candidate.to_dict(),
            },
        )
        receipt_path, receipt_content, _receipt = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=operation,
            actor=evidence.executor.identity_id,
            request_fingerprint_sha256=request_fingerprint,
            preview_token=preview.mutation.preview_token,
            result=result_payload,
            candidates=candidates,
            authority=evidence,
        )
        mutation = self.atomic_writer.apply(
            operation_id=result_payload["operation_id"],
            candidates={**candidates, receipt_path: receipt_content},
            sources=preview.mutation.source_preconditions,
            preview_token=preview.mutation.preview_token,
            actor=evidence.executor.identity_id,
        )
        if mutation.status != "applied":
            replay = self._replay(
                operation_key=operation_key,
                operation=operation,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                display_name=display_name,
                retain_lineage=retain_lineage,
                lineage_visibility=lineage_visibility,
                authority_context=authority_context,
            )
            if replay is not None:
                return replay
            return self._non_applied(preview, mutation.status, mutation.message)
        return ProjectIdentityMutationResult(
            status="applied",
            kind=kind,
            previous=preview.previous,
            current=preview.candidate,
            source_revision=preview.source_revision,
            mutation=mutation,
            message="Project identity committed atomically.",
        )

    def _replay(
        self,
        *,
        operation_key: str,
        operation: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        display_name: str,
        retain_lineage: bool,
        lineage_visibility: str,
        authority_context: AuthorityContext | None,
    ) -> ProjectIdentityMutationResult | None:
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is None:
            return None
        if receipt.operation != operation or receipt.authority is None:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation")
        request = receipt.result.get("request")
        expected_request = {
            "display_name": display_name,
            "retain_lineage": retain_lineage,
            "lineage_visibility": lineage_visibility,
        }
        if not isinstance(request, Mapping) or dict(request) != expected_request:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to different identity inputs"
            )
        evidence = self.codec.evidence_from_mapping(receipt.authority)
        if authority_context is not None:
            if authority_context.digest_sha256 != evidence.authority_context_sha256:
                raise ValueError(
                    "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to different authority evidence"
                )
        elif (
            actor_id != evidence.subject.identity_id
            or executor_id != evidence.executor.identity_id
            or executor_kind != evidence.executor.kind.value
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to a different actor or executor"
            )
        current = self.show()
        recorded = receipt.result.get("current_identity")
        if not isinstance(recorded, Mapping) or current.to_dict() != dict(recorded):
            raise ValueError(
                "P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: current identity differs from receipt"
            )
        source = _source_revision_from_result(receipt.result)
        previous_raw = receipt.result.get("previous_identity")
        previous = (
            project_identity_from_mapping(previous_raw)
            if isinstance(previous_raw, Mapping)
            else None
        )
        return ProjectIdentityMutationResult(
            status="already_applied",
            kind="adopt" if operation == "project_identity_adopt" else "derive",
            previous=previous,
            current=current,
            source_revision=source,
            mutation=MutationResult(
                status="already_applied",
                operation_id=str(receipt.result.get("operation_id") or ""),
                preview_token="",
                actor=receipt.actor,
                message="Exact project identity mutation was already committed.",
            ),
            message="Exact project identity mutation was already committed.",
        )

    def _authority(
        self,
        *,
        capability: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        channel: str,
    ) -> AuthorityEvidence:
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=(capability,),
            channel=channel,
        )
        claim = context.claim_for(capability)
        if claim is None or claim.basis != AuthorityBasis.root_authority:
            raise ValueError(
                "P2P_AUTHORIZATION_DENIED: project identity mutation requires root authority"
            )
        return evidence

    @staticmethod
    def _non_applied(
        preview: ProjectIdentityMutationPreview,
        status: str,
        message: str,
    ) -> ProjectIdentityMutationResult:
        return ProjectIdentityMutationResult(
            status=status,
            kind=preview.kind,
            previous=preview.previous,
            current=preview.candidate,
            source_revision=preview.source_revision,
            mutation=MutationResult(
                status=status,
                operation_id=preview.mutation.operation_id,
                preview_token=preview.mutation.preview_token,
                actor=preview.mutation.actor,
                message=message,
            ),
            message=message,
        )


def _source_revision_from_result(result: Mapping[str, object]) -> SourceMemoryRevision:
    raw = result.get("source_revision")
    if not isinstance(raw, Mapping) or set(raw) != {"namespace", "sha256"}:
        raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: source revision is missing")
    if raw.get("namespace") != "source_memory":
        raise ValueError(
            "P2P_PROJECT_REVISION_NAMESPACE_MISMATCH: receipt source revision namespace is invalid"
        )
    return SourceMemoryRevision(str(raw.get("sha256") or ""))

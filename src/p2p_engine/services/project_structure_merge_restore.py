from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from p2p_engine.core.authority import AuthorityContext, AuthorityEvidence
from p2p_engine.core.mutation_preview import (
    SourcePrecondition,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.project_structure import (
    PROJECT_STRUCTURE_EVENT_LIMIT,
    ProjectStructure,
    ProjectStructureEvent,
    project_structure_from_mapping,
    validate_project_structure,
    with_project_structure_checksum,
)
from p2p_engine.core.project_structure_merge_restore import (
    PROJECT_STRUCTURE_MERGE_CAPABILITY,
    PROJECT_STRUCTURE_MERGE_OPERATION,
    PROJECT_STRUCTURE_RESTORE_CAPABILITY,
    PROJECT_STRUCTURE_RESTORE_OPERATION,
    STRUCTURE_MERGE_PLAN_CONTRACT,
    STRUCTURE_RESTORE_PLAN_CONTRACT,
    StructureComparison,
    StructureElementRef,
    StructureMergePlan,
    StructureRestorePlan,
    StructureSourceIdentity,
    StructureTransitionPreview,
    StructureTransitionResult,
)
from p2p_engine.core.project_structure_retirement import (
    StructureRetirementDisposition,
    StructureRetirementImpact,
    StructureRetirementPlan,
)
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    preview_token_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.project_memory import _memory_revision
from p2p_engine.services.project_structure import (
    PROJECT_STRUCTURE_EVENTS_PATH,
    PROJECT_STRUCTURE_PATH,
    ProjectStructureService,
    project_structure_bytes,
    project_structure_events_bytes,
    project_structure_events_from_bytes,
)
from p2p_engine.services.project_structure_replacement import (
    ProjectStructureReplacementService,
    _active_readiness_counts,
    _element_map,
)
from p2p_engine.services.project_structure_retirement import _classification_projection
from p2p_engine.services.project_structure_snapshots import (
    PROJECT_STRUCTURE_SNAPSHOTS_PATH,
    ProjectStructureSnapshotService,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso

STRUCTURE_TRANSITION_POLICY_VERSION = 1
STRUCTURE_PREVIEW_TTL_SECONDS = 900


@dataclass(frozen=True)
class _ResolvedSource:
    identity: StructureSourceIdentity
    structure: ProjectStructure
    external_reference: str = ""


@dataclass(frozen=True)
class _Build:
    preview: StructureTransitionPreview
    request: Mapping[str, object]
    request_fingerprint: str
    candidate_bytes: Mapping[str, bytes]
    source_preconditions: tuple[SourcePrecondition, ...]
    event: ProjectStructureEvent | None
    authority: AuthorityEvidence


class ProjectStructureMergeRestoreService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        structure_service: ProjectStructureService,
        memory_service,
        question_service,
        replacement_service: ProjectStructureReplacementService,
        authority: ProjectAuthorityService,
        receipts: MutationReceiptService,
        readiness_result: Callable[[], object] | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.structure_service = structure_service
        self.memory_service = memory_service
        self.question_service = question_service
        self.replacement = replacement_service
        self.retirement = replacement_service.retirement
        self.authority = authority
        self.receipts = receipts
        self.readiness_result = readiness_result
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root, p2p_dir=self.p2p_dir
        )
        self.clock = clock
        self.codec = AuthorityContractCodec()
        self.snapshots = ProjectStructureSnapshotService(root=self.root)
        self.bundle_codec = CanonicalBundleCodec()

    # Pure reads ---------------------------------------------------------
    def compare(
        self,
        *,
        source: str,
        selected: Sequence[StructureElementRef | Mapping[str, object]] = (),
        limit: int = 250,
    ) -> StructureComparison:
        _bounded_limit(limit)
        current = self.structure_service.show(include_retired=True)
        resolved = self._resolve_external_source(source)
        refs = _normalize_refs(selected)
        blockers: list[str] = []
        closure: tuple[StructureElementRef, ...] = ()
        collisions: tuple[Mapping[str, object], ...] = ()
        if refs:
            closure, closure_blockers = _dependency_closure(resolved.structure, refs)
            blockers.extend(closure_blockers)
            collisions = _collision_descriptions(current, resolved.structure, (*refs, *closure))
        elements = tuple(
            item.to_dict()
            for item in self.replacement._compare_elements(current, resolved.structure)
        )
        truncated = len(elements) > limit
        if truncated:
            blockers.append("P2P_STRUCTURE_COMPARISON_TRUNCATED")
        return StructureComparison(
            source=resolved.identity,
            current=current,
            elements=elements[:limit],
            selected=refs,
            dependency_closure=closure,
            collisions=collisions[:limit],
            blockers=tuple(sorted(set(blockers))),
            truncated=truncated,
        )

    def retained_list(self, *, limit: int = 20) -> dict[str, object]:
        current = self.structure_service.show(include_retired=True)
        payload = self.snapshots.list(structure_id=current.structure_id, limit=limit)
        payload["current"] = {
            "revision": current.revision,
            "checksum": current.checksum,
        }
        payload["mutation_performed"] = False
        return payload

    def retained_inspect(
        self, *, revision: int, include_structure: bool = False
    ) -> dict[str, object]:
        current = self.structure_service.show(include_retired=True)
        payload = self.snapshots.inspect(
            structure_id=current.structure_id,
            revision=revision,
            include_structure=include_structure,
        )
        payload["mutation_performed"] = False
        return payload

    # Preview ------------------------------------------------------------
    def merge_preview(
        self,
        *,
        source: str,
        plan: StructureMergePlan,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        limit: int = 250,
    ) -> StructureTransitionPreview:
        return self._build_merge(
            source=source,
            plan=plan,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
            operation_key=None,
            issued_at=self.clock(),
            limit=limit,
        ).preview

    def restore_preview(
        self,
        *,
        plan: StructureRestorePlan,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        limit: int = 250,
    ) -> StructureTransitionPreview:
        return self._build_restore(
            plan=plan,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
            operation_key=None,
            issued_at=self.clock(),
            limit=limit,
        ).preview

    # Apply --------------------------------------------------------------
    def merge_apply(
        self,
        *,
        source: str,
        plan: StructureMergePlan,
        preview_token: str,
        operation_key: str,
        confirm: bool,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
    ) -> StructureTransitionResult:
        return self._apply(
            operation="merge",
            source=source,
            merge_plan=plan,
            restore_plan=None,
            preview_token=preview_token,
            operation_key=operation_key,
            confirm=confirm,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
        )

    def restore_apply(
        self,
        *,
        plan: StructureRestorePlan,
        preview_token: str,
        operation_key: str,
        confirm: bool,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
    ) -> StructureTransitionResult:
        return self._apply(
            operation="restore",
            source="",
            merge_plan=None,
            restore_plan=plan,
            preview_token=preview_token,
            operation_key=operation_key,
            confirm=confirm,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
        )

    def _apply(
        self,
        *,
        operation: str,
        source: str,
        merge_plan: StructureMergePlan | None,
        restore_plan: StructureRestorePlan | None,
        preview_token: str,
        operation_key: str,
        confirm: bool,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        channel: str,
    ) -> StructureTransitionResult:
        if not confirm:
            raise ValueError("P2P_STRUCTURE_TRANSITION_CONFIRM_REQUIRED: apply requires --confirm")
        validate_idempotency_key(operation_key)
        issued_at = _validate_preview_token_age(preview_token, now=self.clock())
        expected_operation = (
            PROJECT_STRUCTURE_MERGE_OPERATION
            if operation == "merge"
            else PROJECT_STRUCTURE_RESTORE_OPERATION
        )
        replay = self._exact_replay(
            operation=operation,
            receipt_operation=expected_operation,
            operation_key=operation_key,
            preview_token=preview_token,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
        )
        if replay is not None:
            return replay
        if operation == "merge":
            assert merge_plan is not None
            build = self._build_merge(
                source=source,
                plan=merge_plan,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                authority_context=authority_context,
                channel=channel,
                operation_key=operation_key,
                issued_at=issued_at,
                limit=250,
            )
        else:
            assert restore_plan is not None
            build = self._build_restore(
                plan=restore_plan,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                authority_context=authority_context,
                channel=channel,
                operation_key=operation_key,
                issued_at=issued_at,
                limit=250,
            )
        if build.preview.preview_token != preview_token:
            raise ValueError(
                "P2P_STRUCTURE_TRANSITION_PREVIEW_MISMATCH: preview is stale or differs"
            )
        if (
            not build.preview.apply_allowed
            or build.preview.candidate is None
            or build.event is None
        ):
            raise ValueError(
                "P2P_STRUCTURE_TRANSITION_BLOCKED: " + ", ".join(build.preview.blockers)
            )
        candidate = build.preview.candidate
        evidence = build.authority
        receipt_operation = expected_operation
        changed_paths = sorted(build.candidate_bytes)
        summary = {
            "contract": "p2p-structure-transition-receipt/v1",
            "operation": receipt_operation,
            "operation_id": f"project.structure.{operation}.apply",
            "status": "applied",
            "request": dict(build.request),
            "source": build.preview.source.to_dict(),
            "previous": {
                "structure_id": build.preview.current.structure_id,
                "revision": build.preview.current.revision,
                "checksum": build.preview.current.checksum,
            },
            "current": {
                "structure_id": candidate.structure_id,
                "revision": candidate.revision,
                "checksum": candidate.checksum,
            },
            "previous_memory_revision": build.preview.expected_memory_revision,
            "current_memory_revision": str(
                build.preview.classification_projection.get(
                    "memory_revision", build.preview.expected_memory_revision
                )
            ),
            "event": build.event.to_dict(),
            "changed_entities": [
                "project.mutation_receipt",
                "project.structure",
                "project.structure_events",
                "project.structure_snapshots",
            ],
            "detached_copy": True,
            "active_release_subscription": False,
            "second_authority_created": False,
            "changed_paths": changed_paths,
        }
        receipt_path, receipt_content, _receipt = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=receipt_operation,
            actor=evidence.executor.identity_id,
            request_fingerprint_sha256=build.request_fingerprint,
            preview_token=preview_token,
            result=summary,
            candidates=build.candidate_bytes,
            authority=evidence,
        )
        mutation = self.atomic_writer.apply(
            operation_id=f"project-structure-{operation}",
            candidates={**build.candidate_bytes, receipt_path: receipt_content},
            sources=(
                *build.source_preconditions,
                source_precondition(receipt_path, None),
            ),
            preview_token=preview_token,
            actor=evidence.executor.identity_id,
            candidate_validator=lambda view: self._validate_candidate_view(
                view, candidate=candidate, event=build.event
            ),
        )
        if mutation.status != "applied":
            replay = self._exact_replay(
                operation=operation,
                receipt_operation=receipt_operation,
                operation_key=operation_key,
                preview_token=preview_token,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                authority_context=authority_context,
                channel=channel,
            )
            if replay is not None:
                return replay
            raise ValueError(
                "P2P_STRUCTURE_TRANSITION_MUTATION_FAILED: " + (mutation.message or mutation.status)
            )
        self.memory_service.invalidate()
        current = self.structure_service.show(include_retired=True)
        if current.revision != candidate.revision or current.checksum != candidate.checksum:
            raise ValueError("P2P_STRUCTURE_TRANSITION_POSTCONDITION_INVALID: structure differs")
        return StructureTransitionResult(
            operation=operation,
            status="applied",
            source=build.preview.source,
            previous=build.preview.current,
            current=current,
            previous_memory_revision=build.preview.expected_memory_revision,
            current_memory_revision=str(
                build.preview.classification_projection.get(
                    "memory_revision", build.preview.expected_memory_revision
                )
            ),
            event=build.event.to_dict(),
            actor=evidence.executor.identity_id,
            receipt_key_sha256=idempotency_key_sha256(operation_key),
            changed_entities=(
                "project.structure",
                "project.structure_events",
                "project.structure_snapshots",
                "project.mutation_receipt",
            ),
            message=f"Project structure {operation} applied as a forward revision.",
        )

    # Builders -----------------------------------------------------------
    def _build_merge(
        self,
        *,
        source: str,
        plan: StructureMergePlan,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        channel: str,
        operation_key: str | None,
        issued_at: str,
        limit: int,
    ) -> _Build:
        _bounded_limit(limit)
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=(PROJECT_STRUCTURE_MERGE_CAPABILITY,),
            channel=channel,
        )
        resolved = self._resolve_external_source(source)
        current = self.structure_service.show(include_retired=True)
        memory_revision, records_by_path, truncated_sources = self._memory_state()
        blockers: list[str] = []
        if plan.source != resolved.identity:
            blockers.append("P2P_STRUCTURE_MERGE_SOURCE_DRIFT")
        blockers.extend(
            _target_precondition_blockers(
                current, plan.expected_target_revision, plan.expected_target_checksum
            )
        )
        if memory_revision != plan.expected_memory_revision:
            blockers.append("P2P_STRUCTURE_MERGE_MEMORY_DRIFT")
        computed_closure, closure_blockers = _dependency_closure(resolved.structure, plan.selected)
        blockers.extend(closure_blockers)
        if tuple(item.identity for item in computed_closure) != tuple(
            item.identity for item in plan.dependency_closure
        ):
            blockers.append("P2P_STRUCTURE_MERGE_DEPENDENCY_CLOSURE_MISMATCH")
        all_refs = (*plan.selected, *computed_closure)
        candidate, planning_blockers = _merge_candidate(current, resolved.structure, plan, all_refs)
        blockers.extend(planning_blockers)
        if truncated_sources:
            blockers.append("P2P_STRUCTURE_MERGE_REFERENCE_INDEX_INCOMPLETE")
        elements = tuple(
            item.to_dict()
            for item in self.replacement._compare_elements(current, resolved.structure)
        )
        if len(elements) > limit:
            blockers.append("P2P_STRUCTURE_MERGE_COMPARISON_TRUNCATED")
        collisions = _collision_descriptions(current, resolved.structure, all_refs)
        if len(collisions) > limit:
            blockers.append("P2P_STRUCTURE_MERGE_COLLISION_TRUNCATED")
        reference_items, _questions, index_blockers = self.retirement._reference_index(
            structure=current,
            records_by_path=records_by_path,
        )
        blockers.extend(index_blockers)
        merge_impacts = _merge_reference_impacts(
            reference_items=reference_items,
            decisions=plan.collisions,
            refs=all_refs,
        )
        if len(merge_impacts) > limit:
            blockers.append("P2P_STRUCTURE_MERGE_IMPACT_TRUNCATED")
        if plan.dispositions:
            blockers.append("P2P_STRUCTURE_MERGE_DISPOSITION_UNKNOWN")
        if candidate is not None:
            candidate = with_project_structure_checksum(
                replace(candidate, revision=current.revision + 1)
            )
            if candidate.checksum == current.checksum:
                blockers.append("P2P_STRUCTURE_MERGE_NO_CHANGE")
        blockers = sorted(set(blockers))
        request = {"contract": STRUCTURE_MERGE_PLAN_CONTRACT, "plan": plan.to_dict()}
        plan_digest = semantic_sha256(plan.to_dict())
        preview_token = _preview_token(
            operation="merge",
            source=resolved.identity,
            current=current,
            memory_revision=memory_revision,
            plan_digest=plan_digest,
            authority_digest=context.digest_sha256,
            issued_at=issued_at,
        )
        candidate_bytes: dict[str, bytes] = {}
        event: ProjectStructureEvent | None = None
        if not blockers and candidate is not None:
            event, candidate_bytes = self._transition_candidates(
                operation="merge",
                previous=current,
                candidate=candidate,
                source=resolved.identity,
                evidence=evidence,
                memory_revision=memory_revision,
                records_by_path=records_by_path,
                impacts=(),
                dispositions=plan.dispositions,
            )
        readiness = _readiness_projection(current, candidate, blockers)
        classification = _classification_projection(
            reference_items=reference_items,
            required=(),
            plan=StructureRetirementPlan(),
            blockers=blockers,
        )
        classification = {
            **classification,
            **_identity_projection(candidate or current, memory_revision, blockers),
        }
        preview = StructureTransitionPreview(
            operation="merge",
            source=resolved.identity,
            current=current,
            candidate=candidate if not blockers else None,
            expected_memory_revision=memory_revision,
            selected=plan.selected,
            dependency_closure=computed_closure,
            elements=elements[:limit],
            collisions=collisions[:limit],
            impacts=tuple(merge_impacts[:limit]),
            required_dispositions=(),
            applied_dispositions=plan.dispositions,
            readiness_projection=readiness,
            classification_projection=classification,
            blockers=tuple(blockers),
            preview_token=preview_token if not blockers else "",
            plan_digest=plan_digest,
        )
        return _Build(
            preview=preview,
            request=request,
            request_fingerprint=_request_fingerprint(
                operation="merge",
                request=request,
                context_digest=context.digest_sha256,
                operation_key=operation_key,
            ),
            candidate_bytes=candidate_bytes,
            source_preconditions=self._source_preconditions(records_by_path),
            event=event,
            authority=evidence,
        )

    def _build_restore(
        self,
        *,
        plan: StructureRestorePlan,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        channel: str,
        operation_key: str | None,
        issued_at: str,
        limit: int,
    ) -> _Build:
        _bounded_limit(limit)
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=(PROJECT_STRUCTURE_RESTORE_CAPABILITY,),
            channel=channel,
        )
        current = self.structure_service.show(include_retired=True)
        memory_revision, records_by_path, truncated_sources = self._memory_state()
        blockers = _target_precondition_blockers(
            current, plan.expected_target_revision, plan.expected_target_checksum
        )
        if memory_revision != plan.expected_memory_revision:
            blockers.append("P2P_STRUCTURE_RESTORE_MEMORY_DRIFT")
        try:
            retained = self.snapshots.load(structure_id=current.structure_id).resolve(
                plan.source_revision
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if retained.checksum != plan.source_checksum:
            blockers.append("P2P_STRUCTURE_RESTORE_SOURCE_DRIFT")
        source_identity = StructureSourceIdentity(
            kind="retained_revision",
            identity=f"{current.structure_id}@{retained.revision}",
            digest=retained.checksum,
            schema_version=1,
        )
        historical = retained.structure
        candidate = with_project_structure_checksum(
            replace(
                historical,
                structure_id=current.structure_id,
                revision=current.revision + 1,
            )
        )
        if candidate.checksum == current.checksum:
            blockers.append("P2P_STRUCTURE_RESTORE_NO_CHANGE")
        elements = tuple(
            item.to_dict() for item in self.replacement._compare_elements(current, historical)
        )
        impacts, required, impact_blockers, reference_items = self._transition_impacts(
            current=current,
            target=historical,
            records_by_path=records_by_path,
            dispositions=plan.dispositions,
            truncated_sources=truncated_sources,
            limit=limit,
        )
        blockers.extend(impact_blockers)
        blockers = sorted(set(blockers))
        request = {"contract": STRUCTURE_RESTORE_PLAN_CONTRACT, "plan": plan.to_dict()}
        plan_digest = semantic_sha256(plan.to_dict())
        preview_token = _preview_token(
            operation="restore",
            source=source_identity,
            current=current,
            memory_revision=memory_revision,
            plan_digest=plan_digest,
            authority_digest=context.digest_sha256,
            issued_at=issued_at,
        )
        candidate_bytes: dict[str, bytes] = {}
        event: ProjectStructureEvent | None = None
        candidate_memory_revision = memory_revision
        if not blockers:
            event, candidate_bytes = self._transition_candidates(
                operation="restore",
                previous=current,
                candidate=candidate,
                source=source_identity,
                evidence=evidence,
                memory_revision=memory_revision,
                records_by_path=records_by_path,
                impacts=required,
                dispositions=plan.dispositions,
            )
            next_records = dict(records_by_path)
            for path, content in candidate_bytes.items():
                if path in records_by_path:
                    next_records[path] = content
            candidate_memory_revision = _memory_revision(tuple(sorted(next_records.items())))
        readiness = _readiness_projection(current, candidate, blockers)
        classification = _classification_projection(
            reference_items=reference_items,
            required=required,
            plan=StructureRetirementPlan(dispositions=plan.dispositions),
            blockers=blockers,
        )
        classification = {
            **classification,
            **_identity_projection(candidate, candidate_memory_revision, blockers),
        }
        preview = StructureTransitionPreview(
            operation="restore",
            source=source_identity,
            current=current,
            candidate=candidate if not blockers else None,
            expected_memory_revision=memory_revision,
            elements=elements[:limit],
            impacts=tuple(_public_impact(item) for item in impacts[:limit]),
            required_dispositions=tuple(_public_impact(item) for item in required[:limit]),
            applied_dispositions=plan.dispositions,
            readiness_projection=readiness,
            classification_projection={
                **classification,
                "memory_revision": candidate_memory_revision,
            },
            blockers=tuple(blockers),
            preview_token=preview_token if not blockers else "",
            plan_digest=plan_digest,
        )
        return _Build(
            preview=preview,
            request=request,
            request_fingerprint=_request_fingerprint(
                operation="restore",
                request=request,
                context_digest=context.digest_sha256,
                operation_key=operation_key,
            ),
            candidate_bytes=candidate_bytes,
            source_preconditions=self._source_preconditions(records_by_path),
            event=event,
            authority=evidence,
        )

    def _transition_impacts(
        self,
        *,
        current: ProjectStructure,
        target: ProjectStructure,
        records_by_path: Mapping[str, bytes],
        dispositions: Sequence[StructureRetirementDisposition],
        truncated_sources: bool,
        limit: int,
    ) -> tuple[
        list[StructureRetirementImpact],
        list[StructureRetirementImpact],
        list[str],
        Sequence[object],
    ]:
        removed = self.replacement._removed_targets(current, target)
        retiring_sections = {item.element_id for item in removed if item.kind == "section"}
        direct_artifacts = {item.element_id for item in removed if item.kind == "artifact"}
        direct_fields = {
            (item.section_id, item.element_id) for item in removed if item.kind == "field"
        }
        impacts = list(
            self.retirement._structural_impacts(
                current,
                targets=removed,
                retiring_sections=retiring_sections,
                direct_artifacts=direct_artifacts,
            )
        )
        reference_items, questions_artifact, index_blockers = self.retirement._reference_index(
            structure=current, records_by_path=records_by_path
        )
        impacts.extend(
            self.retirement._memory_impacts(
                retiring_sections=retiring_sections,
                direct_fields=direct_fields,
                direct_artifacts=direct_artifacts,
                reference_items=reference_items,
                questions_artifact=questions_artifact,
            )
        )
        required = [item for item in impacts if item.required_disposition]
        plan = StructureRetirementPlan(dispositions=tuple(dispositions))
        blockers = list(index_blockers)
        if truncated_sources:
            blockers.append("P2P_STRUCTURE_RESTORE_REFERENCE_INDEX_INCOMPLETE")
        blockers.extend(
            self.replacement._disposition_blockers(
                required=required,
                plan=type("RestorePlanAdapter", (), {"by_id": plan.by_id})(),
                target_structure=target,
            )
        )
        if len(impacts) > limit:
            blockers.append("P2P_STRUCTURE_RESTORE_IMPACT_TRUNCATED")
        return impacts, required, blockers, reference_items

    def _transition_candidates(
        self,
        *,
        operation: str,
        previous: ProjectStructure,
        candidate: ProjectStructure,
        source: StructureSourceIdentity,
        evidence: AuthorityEvidence,
        memory_revision: str,
        records_by_path: Mapping[str, bytes],
        impacts: Sequence[StructureRetirementImpact],
        dispositions: Sequence[StructureRetirementDisposition],
    ) -> tuple[ProjectStructureEvent, dict[str, bytes]]:
        structure_id, events = project_structure_events_from_bytes(
            (self.root / PROJECT_STRUCTURE_EVENTS_PATH).read_bytes()
        )
        if structure_id != previous.structure_id or len(events) >= PROJECT_STRUCTURE_EVENT_LIMIT:
            raise ValueError(
                "P2P_STRUCTURE_TRANSITION_EVENT_LEDGER_INVALID: ledger is unavailable or full"
            )
        timestamp = self.clock()
        event = ProjectStructureEvent(
            event_id=f"structure-event-{candidate.revision:08d}",
            event_type=f"structure_{'merged' if operation == 'merge' else 'restored'}",
            revision=candidate.revision,
            checksum=candidate.checksum,
            occurred_at=timestamp,
            subject_id=evidence.subject.identity_id,
            executor_id=evidence.executor.identity_id,
            authority=evidence.to_dict(),
            details={
                "source": source.to_dict(),
                "previous_revision": previous.revision,
                "previous_checksum": previous.checksum,
                "previous_memory_revision": memory_revision,
                "required_disposition_ids": [item.impact_id for item in impacts],
                "applied_dispositions": [item.to_dict() for item in dispositions],
                "forward_only": True,
                "detached_copy": True,
                "active_release_subscription": False,
                "second_authority_created": False,
            },
        )
        candidates = {
            PROJECT_STRUCTURE_PATH: project_structure_bytes(candidate),
            PROJECT_STRUCTURE_EVENTS_PATH: project_structure_events_bytes(
                structure_id=structure_id, events=(*events, event)
            ),
            PROJECT_STRUCTURE_SNAPSHOTS_PATH: self.snapshots.candidate_bytes(
                previous=previous,
                retained_at=timestamp,
                retained_by=evidence.subject.identity_id,
                reason=f"before-{operation}",
            ),
        }
        if operation == "restore" and impacts:
            removed = self.replacement._removed_targets(previous, candidate)
            retiring_sections = {item.element_id for item in removed if item.kind == "section"}
            direct_fields = {
                (item.section_id, item.element_id) for item in removed if item.kind == "field"
            }
            memory_candidates = self.retirement._memory_candidates(
                plan=StructureRetirementPlan(dispositions=tuple(dispositions)),
                required=impacts,
                candidate_structure=candidate,
                records_by_path=records_by_path,
                evidence=evidence,
                timestamp=timestamp,
                retiring_sections=retiring_sections,
                direct_fields=direct_fields,
            )
            candidates.update(memory_candidates)
        return event, candidates

    # Source/replay/validation ------------------------------------------
    def _resolve_external_source(self, reference: str) -> _ResolvedSource:
        value = str(reference or "").strip()
        if not value:
            raise ValueError("P2P_STRUCTURE_SOURCE_REQUIRED: exact release or bundle is required")
        path = Path(value)
        resolved_path = path if path.is_absolute() else self.root / path
        if resolved_path.is_file() and resolved_path.suffix.lower() == ".p2pbundle":
            decoded = self.bundle_codec.decode_bundle(resolved_path)
            entity = next(
                (
                    item
                    for item in decoded.snapshot.entities
                    if item.technical_id == "project:structure"
                ),
                None,
            )
            if entity is None:
                raise ValueError("P2P_STRUCTURE_SOURCE_INVALID: bundle has no canonical structure")
            document = entity.payload.get("document")
            if not isinstance(document, Mapping) or set(document) != {"project_structure"}:
                raise ValueError(
                    "P2P_STRUCTURE_SOURCE_INVALID: bundle structure contract is invalid"
                )
            structure = project_structure_from_mapping(document.get("project_structure"))
            return _ResolvedSource(
                identity=StructureSourceIdentity(
                    kind="bundle",
                    identity=f"bundle:{decoded.snapshot.project_uuid}",
                    digest=decoded.archive_sha256,
                    schema_version=decoded.snapshot.memory_schema,
                ),
                structure=structure,
                external_reference=value,
            )
        resolved = self.replacement._resolve_target(
            value, actor="structure-comparison", timestamp="1970-01-01T00:00:00Z"
        )
        return _ResolvedSource(
            identity=StructureSourceIdentity(
                kind="release",
                identity=resolved.release.coordinate,
                digest=resolved.release.semantic_checksum,
                schema_version=resolved.release.schema_version,
            ),
            structure=resolved.active_structure,
            external_reference=value,
        )

    def _memory_state(self) -> tuple[str, dict[str, bytes], bool]:
        records, truncated = self.memory_service._source_records()
        return _memory_revision(records), {path: content for path, content in records}, truncated

    def _source_preconditions(
        self, records_by_path: Mapping[str, bytes]
    ) -> tuple[SourcePrecondition, ...]:
        values = {
            path: source_precondition(path, content) for path, content in records_by_path.items()
        }
        for relative in (PROJECT_STRUCTURE_PATH, PROJECT_STRUCTURE_EVENTS_PATH):
            values[relative] = source_precondition(relative, (self.root / relative).read_bytes())
        values[PROJECT_STRUCTURE_SNAPSHOTS_PATH] = source_precondition(
            PROJECT_STRUCTURE_SNAPSHOTS_PATH, self.snapshots.source_content()
        )
        return tuple(values[key] for key in sorted(values))

    def _validate_candidate_view(
        self, view: object, *, candidate: ProjectStructure, event: ProjectStructureEvent
    ) -> None:
        from p2p_engine.services.project_structure import project_structure_from_bytes

        observed = project_structure_from_bytes(
            view.read_bytes(PROJECT_STRUCTURE_PATH)  # type: ignore[attr-defined]
        )
        structure_id, events = project_structure_events_from_bytes(
            view.read_bytes(PROJECT_STRUCTURE_EVENTS_PATH)  # type: ignore[attr-defined]
        )
        if (
            observed != candidate
            or structure_id != candidate.structure_id
            or not events
            or events[-1] != event
        ):
            raise ValueError("P2P_STRUCTURE_TRANSITION_CANDIDATE_INVALID: structure/event mismatch")
        # Decode through the adapter contract as part of the same candidate validation.
        from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
        from p2p_engine.services.project_structure_snapshots import (
            retained_structure_ledger_from_mapping,
        )

        raw = load_yaml(
            view.read_bytes(PROJECT_STRUCTURE_SNAPSHOTS_PATH),  # type: ignore[attr-defined]
            loader_contract=UNIQUE_LOADER_CONTRACT,
        )
        retained_structure_ledger_from_mapping(raw, structure_id=candidate.structure_id)

    def _exact_replay(
        self,
        *,
        operation: str,
        receipt_operation: str,
        operation_key: str,
        preview_token: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        channel: str,
    ) -> StructureTransitionResult | None:
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is None:
            return None
        if receipt.operation != receipt_operation or receipt.authority is None:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation")
        if receipt.preview_token_sha256 != preview_token_sha256(preview_token):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: preview token differs")
        evidence = self.codec.evidence_from_mapping(receipt.authority)
        if (
            evidence.subject.identity_id != actor_id
            or evidence.executor.identity_id != executor_id
            or evidence.executor.kind.value != executor_kind
            or evidence.channel != channel
        ):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: authority differs")
        if (
            authority_context is not None
            and authority_context.digest_sha256 != evidence.authority_context_sha256
        ):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: authority context differs")
        status = self.receipts.status(idempotency_key=operation_key)
        if status.postconditions_match is not True:
            raise ValueError("P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: transition state differs")
        result = receipt.result
        current = self.structure_service.show(include_retired=True)
        current_raw = result.get("current")
        previous_raw = result.get("previous")
        source_raw = result.get("source")
        if not all(isinstance(item, Mapping) for item in (current_raw, previous_raw, source_raw)):
            raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: transition receipt is invalid")
        assert (
            isinstance(current_raw, Mapping)
            and isinstance(previous_raw, Mapping)
            and isinstance(source_raw, Mapping)
        )
        if current.revision != current_raw.get("revision") or current.checksum != current_raw.get(
            "checksum"
        ):
            raise ValueError("P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: current structure differs")
        previous_revision = int(previous_raw.get("revision") or 0)
        previous = (
            self.snapshots.load(structure_id=current.structure_id)
            .resolve(previous_revision)
            .structure
        )
        source_identity = StructureSourceIdentity(
            kind=str(source_raw.get("kind") or ""),
            identity=str(source_raw.get("identity") or ""),
            digest=str(source_raw.get("digest") or ""),
            schema_version=int(source_raw.get("schema_version") or 0),
        )
        event = result.get("event")
        if not isinstance(event, Mapping):
            raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: event is invalid")
        return StructureTransitionResult(
            operation=operation,
            status="already_applied",
            source=source_identity,
            previous=previous,
            current=current,
            previous_memory_revision=str(result.get("previous_memory_revision") or ""),
            current_memory_revision=str(result.get("current_memory_revision") or ""),
            event=dict(event),
            actor=evidence.executor.identity_id,
            receipt_key_sha256=idempotency_key_sha256(operation_key),
            changed_entities=tuple(str(item) for item in result.get("changed_entities", ())),
            message=f"Project structure {operation} was already applied with this operation key.",
        )


def _normalize_refs(
    values: Sequence[StructureElementRef | Mapping[str, object]],
) -> tuple[StructureElementRef, ...]:
    from p2p_engine.core.project_structure_merge_restore import structure_element_ref_from_mapping

    refs = tuple(
        item if isinstance(item, StructureElementRef) else structure_element_ref_from_mapping(item)
        for item in values
    )
    identities = [item.identity for item in refs]
    if len(identities) != len(set(identities)):
        raise ValueError("P2P_STRUCTURE_SELECTION_INVALID: selected IDs must be unique")
    return refs


def _source_elements(structure: ProjectStructure) -> dict[str, object]:
    values: dict[str, object] = {}
    for item in structure.sections:
        values[f"section:{item.section_id}"] = item
    for item in structure.fields:
        values[f"field:{item.section_id}/{item.field_id}"] = item
    for item in structure.questions:
        values[f"question:{item.question_id}"] = item
    for item in structure.criteria:
        values[f"criterion:{item.criterion_id}"] = item
    for item in structure.artifacts:
        values[f"artifact:{item.artifact_id}"] = item
    return values


def _ref_for(kind: str, item: object) -> StructureElementRef:
    if kind == "section":
        return StructureElementRef(kind, getattr(item, "section_id"))
    if kind == "field":
        return StructureElementRef(kind, getattr(item, "field_id"), getattr(item, "section_id"))
    return StructureElementRef(kind, getattr(item, f"{kind}_id"))


def _dependency_closure(
    source: ProjectStructure,
    selected: Sequence[StructureElementRef],
) -> tuple[tuple[StructureElementRef, ...], list[str]]:
    elements = _source_elements(source)
    blockers: list[str] = []
    selected_ids = {item.identity for item in selected}
    closure: dict[str, StructureElementRef] = {}
    for ref in selected:
        item = elements.get(ref.identity)
        if item is None or getattr(item, "lifecycle", "active") != "active":
            blockers.append("P2P_STRUCTURE_SELECTION_UNKNOWN")
            continue
        if ref.kind == "section":
            section_id = ref.element_id
            for kind, collection in (
                ("field", source.fields),
                ("question", source.questions),
                ("criterion", source.criteria),
            ):
                for child in collection:
                    if child.section_id == section_id and child.lifecycle == "active":
                        child_ref = _ref_for(kind, child)
                        if child_ref.identity not in selected_ids:
                            closure[child_ref.identity] = child_ref
        elif ref.kind in {"field", "question", "criterion"}:
            section_id = getattr(item, "section_id")
            parent = StructureElementRef("section", section_id)
            if parent.identity not in selected_ids:
                closure[parent.identity] = parent
        elif ref.kind == "artifact":
            for section_id in getattr(item, "section_ids"):
                parent = StructureElementRef("section", section_id)
                if parent.identity not in selected_ids:
                    closure[parent.identity] = parent
    # A dependency section brings its nested children only when explicitly selected;
    # it remains a parent dependency otherwise.
    ordered = tuple(closure[key] for key in sorted(closure))
    if len(selected) + len(ordered) > 1000:
        blockers.append("P2P_STRUCTURE_DEPENDENCY_LIMIT_EXCEEDED")
    return ordered, blockers


def _collision_descriptions(
    current: ProjectStructure,
    source: ProjectStructure,
    refs: Sequence[StructureElementRef],
) -> tuple[Mapping[str, object], ...]:
    current_map = _element_map(current, active_only=False)
    source_map = _element_map(source, active_only=False)
    values = []
    for ref in refs:
        if ref.identity not in current_map:
            continue
        values.append(
            {
                "identity": ref.identity,
                "compatible": current_map[ref.identity]["hash"]
                == source_map.get(ref.identity, {}).get("hash"),
                "current_hash": current_map[ref.identity]["hash"],
                "source_hash": source_map.get(ref.identity, {}).get("hash"),
                "decision_required": True,
                "allowed_actions": sorted(
                    ("keep-current", "replace-with-impact", "import-as-new-id")
                ),
            }
        )
    return tuple(sorted(values, key=lambda item: str(item["identity"])))


def _merge_candidate(
    current: ProjectStructure,
    source: ProjectStructure,
    plan: StructureMergePlan,
    refs: Sequence[StructureElementRef],
) -> tuple[ProjectStructure | None, list[str]]:
    blockers: list[str] = []
    source_elements = _source_elements(source)
    current_elements = _source_elements(current)
    ref_ids = {item.identity for item in refs}
    placements = {item.identity: item for item in plan.placements}
    decisions = {item.identity: item for item in plan.collisions}
    if set(placements) != ref_ids:
        blockers.append("P2P_STRUCTURE_MERGE_PLACEMENT_INCOMPLETE")
    expected_collisions = {item.identity for item in refs if item.identity in current_elements}
    if set(decisions) != expected_collisions:
        blockers.append("P2P_STRUCTURE_MERGE_COLLISION_PLAN_INCOMPLETE")
    if blockers:
        return None, blockers

    sections = list(current.sections)
    fields = list(current.fields)
    questions = list(current.questions)
    criteria = list(current.criteria)
    artifacts = list(current.artifacts)
    section_mapping: dict[str, str] = {}
    for ref in refs:
        if ref.kind != "section":
            continue
        decision = decisions.get(ref.identity)
        section_mapping[ref.element_id] = (
            decision.new_id
            if decision and decision.action == "import-as-new-id"
            else ref.element_id
        )

    for ref in sorted(refs, key=lambda item: (item.kind != "section", item.identity)):
        item = source_elements.get(ref.identity)
        if item is None:
            blockers.append("P2P_STRUCTURE_SELECTION_UNKNOWN")
            continue
        placement = placements[ref.identity]
        decision = decisions.get(ref.identity)
        action = decision.action if decision else "import"
        if action == "keep-current":
            continue
        new_id = decision.new_id if decision and action == "import-as-new-id" else ref.element_id
        try:
            if ref.kind == "section":
                if placement.parent_id != "root":
                    blockers.append("P2P_STRUCTURE_MERGE_PLACEMENT_INVALID")
                    continue
                candidate_item = replace(
                    item, section_id=new_id, order=placement.order, lifecycle="active"
                )
                _replace_or_append(
                    sections, candidate_item, lambda value: value.section_id == new_id, action
                )
            elif ref.kind == "field":
                parent = placement.parent_id
                if parent == "root":
                    blockers.append("P2P_STRUCTURE_MERGE_PLACEMENT_INVALID")
                    continue
                candidate_item = replace(
                    item,
                    field_id=new_id,
                    section_id=parent,
                    order=placement.order,
                    lifecycle="active",
                )
                _replace_or_append(
                    fields,
                    candidate_item,
                    lambda value: value.section_id == parent and value.field_id == new_id,
                    action,
                )
            elif ref.kind == "question":
                parent = placement.parent_id
                if parent == "root":
                    blockers.append("P2P_STRUCTURE_MERGE_PLACEMENT_INVALID")
                    continue
                candidate_item = replace(
                    item,
                    question_id=new_id,
                    section_id=parent,
                    order=placement.order,
                    lifecycle="active",
                )
                _replace_or_append(
                    questions, candidate_item, lambda value: value.question_id == new_id, action
                )
            elif ref.kind == "criterion":
                parent = placement.parent_id
                if parent == "root":
                    blockers.append("P2P_STRUCTURE_MERGE_PLACEMENT_INVALID")
                    continue
                candidate_item = replace(
                    item,
                    criterion_id=new_id,
                    section_id=parent,
                    order=placement.order,
                    lifecycle="active",
                )
                _replace_or_append(
                    criteria, candidate_item, lambda value: value.criterion_id == new_id, action
                )
            else:
                if placement.parent_id != "root":
                    blockers.append("P2P_STRUCTURE_MERGE_PLACEMENT_INVALID")
                    continue
                mapped_sections = tuple(
                    section_mapping.get(value, value) for value in item.section_ids
                )
                candidate_item = replace(
                    item,
                    artifact_id=new_id,
                    section_ids=mapped_sections,
                    order=placement.order,
                    lifecycle="active",
                )
                _replace_or_append(
                    artifacts, candidate_item, lambda value: value.artifact_id == new_id, action
                )
        except ValueError:
            blockers.append("P2P_STRUCTURE_MERGE_ID_COLLISION")

    active_sections = sorted(
        (item for item in sections if item.lifecycle == "active"),
        key=lambda item: (item.order, item.section_id),
    )
    active_sections = [replace(item, order=index) for index, item in enumerate(active_sections)]
    retired_sections = [item for item in sections if item.lifecycle != "active"]
    candidate = replace(
        current,
        sections=tuple((*active_sections, *retired_sections)),
        fields=tuple(sorted(fields, key=lambda item: (item.section_id, item.order, item.field_id))),
        questions=tuple(
            sorted(questions, key=lambda item: (item.section_id, item.order, item.question_id))
        ),
        criteria=tuple(
            sorted(criteria, key=lambda item: (item.section_id, item.order, item.criterion_id))
        ),
        artifacts=tuple(sorted(artifacts, key=lambda item: (item.order, item.artifact_id))),
    )
    try:
        validate_project_structure(candidate, verify_checksum=False)
    except ValueError as exc:
        blockers.append(str(exc).split(":", 1)[0])
        return None, blockers
    return candidate, blockers


def _replace_or_append(values: list[object], item: object, predicate, action: str) -> None:
    indexes = [index for index, value in enumerate(values) if predicate(value)]
    if indexes:
        if action == "import-as-new-id":
            raise ValueError("new identity collides")
        values[indexes[0]] = item
    else:
        values.append(item)


def _target_precondition_blockers(
    current: ProjectStructure, expected_revision: int, expected_checksum: str
) -> list[str]:
    blockers = []
    if current.revision != expected_revision:
        blockers.append("P2P_STRUCTURE_TRANSITION_STALE_REVISION")
    if current.checksum != expected_checksum.removeprefix("sha256:"):
        blockers.append("P2P_STRUCTURE_TRANSITION_STALE_CHECKSUM")
    return blockers


def _readiness_projection(
    current: ProjectStructure,
    candidate: ProjectStructure | None,
    blockers: Sequence[str],
) -> dict[str, object]:
    before = _active_readiness_counts(current)
    after = _active_readiness_counts(candidate or current)
    return {
        "status": "blocked" if blockers else "projected",
        "before": before,
        "after": after if not blockers else None,
        "active_sections_delta": after["active_sections"] - before["active_sections"],
        "active_criteria_delta": after["active_criteria"] - before["active_criteria"],
        "score_projection": None,
        "score_projection_reason": "readiness is recalculated from the committed structure and memory",
    }


def _identity_projection(
    structure: ProjectStructure, memory_revision: str, blockers: Sequence[str]
) -> dict[str, object]:
    return {
        "status": "blocked" if blockers else "projected",
        "structure_id": structure.structure_id,
        "structure_revision": structure.revision,
        "structure_checksum": structure.checksum,
        "memory_revision": memory_revision,
    }


def _public_impact(impact: StructureRetirementImpact) -> dict[str, object]:
    payload = impact.to_dict()
    payload.pop("path", None)
    payload["logical_target"] = {
        "type": impact.object_type,
        "id": impact.object_id,
    }
    return payload


def _merge_reference_impacts(
    *,
    reference_items: Sequence[object],
    decisions: Sequence[object],
    refs: Sequence[StructureElementRef],
) -> list[dict[str, object]]:
    by_identity = {item.identity: item for item in decisions}
    touched_sections: set[str] = set()
    touched_artifacts: set[str] = set()
    for ref in refs:
        decision = by_identity.get(ref.identity)
        if decision is None or getattr(decision, "action", "") != "replace-with-impact":
            continue
        if ref.kind == "section":
            touched_sections.add(ref.element_id)
        elif ref.kind == "artifact":
            touched_artifacts.add(ref.element_id)
    impacts: list[dict[str, object]] = []
    for item in reference_items:
        section_ids = tuple(getattr(item, "section_ids", ()))
        object_id = str(getattr(item, "object_id", ""))
        if not (set(section_ids) & touched_sections) and object_id not in touched_artifacts:
            continue
        impacts.append(
            {
                "id": f"merge-reference:{getattr(item, 'object_type', 'object')}:{object_id}",
                "object_type": str(getattr(item, "object_type", "object")),
                "object_id": object_id,
                "state": "reference_preserved_after_typed_replacement",
                "active": bool(getattr(item, "active", False)),
                "section_ids": list(section_ids),
                "required_disposition": False,
                "logical_target": {
                    "type": str(getattr(item, "object_type", "object")),
                    "id": object_id,
                },
            }
        )
    return sorted(impacts, key=lambda value: str(value["id"]))


def _preview_token(
    *,
    operation: str,
    source: StructureSourceIdentity,
    current: ProjectStructure,
    memory_revision: str,
    plan_digest: str,
    authority_digest: str,
    issued_at: str,
) -> str:
    digest = semantic_sha256(
        {
            "policy_version": STRUCTURE_TRANSITION_POLICY_VERSION,
            "operation": operation,
            "source": source.to_dict(),
            "target_revision": current.revision,
            "target_checksum": current.checksum,
            "memory_revision": memory_revision,
            "plan_digest": plan_digest,
            "authority_context_sha256": authority_digest,
            "issued_at": issued_at,
            "ttl_seconds": STRUCTURE_PREVIEW_TTL_SECONDS,
        }
    )
    return f"{issued_at}.{digest}"


def _validate_preview_token_age(token: str, *, now: str) -> str:
    try:
        issued_at, digest = token.rsplit(".", 1)
        issued = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
        observed = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("P2P_STRUCTURE_TRANSITION_PREVIEW_INVALID: token is malformed") from exc
    if len(digest) != 64 or issued.tzinfo is None or observed.tzinfo is None:
        raise ValueError("P2P_STRUCTURE_TRANSITION_PREVIEW_INVALID: token is malformed")
    age = (observed.astimezone(timezone.utc) - issued.astimezone(timezone.utc)).total_seconds()
    if age < -5 or age > STRUCTURE_PREVIEW_TTL_SECONDS:
        raise ValueError("P2P_STRUCTURE_TRANSITION_PREVIEW_EXPIRED: preview token expired")
    return issued_at


def _request_fingerprint(
    *, operation: str, request: Mapping[str, object], context_digest: str, operation_key: str | None
) -> str:
    return semantic_sha256(
        {
            "policy_version": STRUCTURE_TRANSITION_POLICY_VERSION,
            "operation": operation,
            "request": dict(request),
            "authority_context_sha256": context_digest,
            "operation_key_sha256": idempotency_key_sha256(operation_key)
            if operation_key
            else None,
        }
    )


def _bounded_limit(limit: int) -> None:
    if isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise ValueError("P2P_STRUCTURE_TRANSITION_LIMIT_INVALID: limit must be between 1 and 1000")

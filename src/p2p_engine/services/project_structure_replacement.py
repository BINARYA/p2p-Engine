from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from p2p_engine.core.authority import AuthorityContext, AuthorityEvidence
from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    SourcePrecondition,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.portable_verticals import (
    PORTABLE_VERTICAL_SCHEMA_VERSION,
    VerticalCoordinate,
)
from p2p_engine.core.project_domain import StructureSource
from p2p_engine.core.project_structure import (
    ProjectStructure,
    ProjectStructureEvent,
    validate_project_structure,
    with_project_structure_checksum,
)
from p2p_engine.core.project_structure_replacement import (
    PROJECT_STRUCTURE_REPLACEMENT_CAPABILITY,
    PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
    PROJECT_STRUCTURE_REPLACEMENT_OPERATION_ID,
    STRUCTURE_REPLACEMENT_IMPACT_CONTRACT,
    STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
    STRUCTURE_REPLACEMENT_RESULT_CONTRACT,
    ProjectStructureReplacementInspection,
    ProjectStructureReplacementPreview,
    ProjectStructureReplacementResult,
    StructureReplacementElement,
    StructureReplacementPlan,
    StructureReplacementRelease,
    structure_replacement_plan_from_mapping,
)
from p2p_engine.core.project_structure_retirement import (
    StructureRetirementDisposition,
    StructureRetirementImpact,
    StructureRetirementPlan,
    StructureRetirementTarget,
)
from p2p_engine.core.project_verticals import VerticalPack
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    preview_token_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.project_memory import _memory_revision
from p2p_engine.services.project_structure import (
    PROJECT_STRUCTURE_EVENT_LIMIT,
    PROJECT_STRUCTURE_EVENTS_PATH,
    PROJECT_STRUCTURE_PATH,
    ProjectStructureService,
    project_structure_bytes,
    project_structure_events_bytes,
    project_structure_events_from_bytes,
    project_structure_from_bytes,
    project_structure_from_vertical_pack,
)
from p2p_engine.services.project_structure_retirement import (
    ProjectStructureRetirementService,
    _classification_projection,
)
from p2p_engine.services.project_structure_snapshots import (
    PROJECT_STRUCTURE_SNAPSHOTS_PATH,
    ProjectStructureSnapshotService,
)
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.vertical_packages import PortableVerticalPackageService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso

PROJECT_STRUCTURE_REPLACEMENT_POLICY_VERSION = 1


@dataclass(frozen=True)
class _ResolvedTarget:
    release: StructureReplacementRelease
    pack: VerticalPack
    active_structure: ProjectStructure


@dataclass(frozen=True)
class _Build:
    preview: ProjectStructureReplacementPreview
    request_fingerprint_sha256: str
    source_preconditions: tuple[SourcePrecondition, ...]
    candidate_bytes: dict[str, bytes]
    event: ProjectStructureEvent | None
    authority: AuthorityEvidence
    request: dict[str, object]


class ProjectStructureReplacementService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        structure_service: ProjectStructureService,
        memory_service,
        question_service,
        vertical_service: ProjectVerticalService,
        package_service: PortableVerticalPackageService | None = None,
        readiness_result: Callable[[], object] | None = None,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.structure_service = structure_service
        self.memory_service = memory_service
        self.question_service = question_service
        self.vertical_service = vertical_service
        self.package_service = package_service or PortableVerticalPackageService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            vertical_service=vertical_service,
        )
        self.readiness_result = readiness_result
        self.authority = authority or ProjectAuthorityService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.receipts = receipts or MutationReceiptService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.clock = clock
        self.codec = AuthorityContractCodec()
        self.snapshots = ProjectStructureSnapshotService(root=self.root)
        self.retirement = ProjectStructureRetirementService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            structure_service=structure_service,
            memory_service=memory_service,
            question_service=question_service,
            authority=self.authority,
            receipts=self.receipts,
            atomic_writer=self.atomic_writer,
            clock=clock,
        )

    def inspect_release(self, target: str) -> ProjectStructureReplacementInspection:
        resolved = self._resolve_target(target, actor="inspector", timestamp="1970-01-01T00:00:00Z")
        blockers = self._target_blockers(resolved.active_structure)
        return ProjectStructureReplacementInspection(
            target=resolved.release,
            candidate=resolved.active_structure,
            active_counts=_active_counts(resolved.active_structure),
            blockers=tuple(blockers),
        )

    def preview(
        self,
        *,
        target: str,
        expected_structure_revision: int,
        expected_memory_revision: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        plan: StructureReplacementPlan | Mapping[str, object] | None = None,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        limit: int = 100,
    ) -> ProjectStructureReplacementPreview:
        return self._build(
            target=target,
            expected_structure_revision=expected_structure_revision,
            expected_memory_revision=expected_memory_revision,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            plan=plan,
            authority_context=authority_context,
            channel=channel,
            consent_id=None,
            consent_sha256=None,
            operation_key=None,
            limit=limit,
        ).preview

    def apply(
        self,
        *,
        target: str,
        expected_structure_revision: int,
        expected_memory_revision: str,
        preview_token: str,
        operation_key: str,
        confirm: bool,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        plan: StructureReplacementPlan | Mapping[str, object],
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
        limit: int = 100,
    ) -> ProjectStructureReplacementResult:
        if not confirm:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_CONFIRM_REQUIRED: apply requires --confirm")
        validate_idempotency_key(operation_key)
        normalized_plan = _plan_from_input(plan)
        if normalized_plan is None:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_PLAN_REQUIRED: apply requires a replacement plan")
        request = _request_payload(
            plan=normalized_plan,
            expected_structure_revision=expected_structure_revision,
            expected_memory_revision=expected_memory_revision,
        )
        replay = self._exact_replay(
            operation_key=operation_key,
            request=request,
            preview_token=preview_token,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            authority_context=authority_context,
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        if replay is not None:
            return replay
        build = self._build(
            target=target,
            expected_structure_revision=expected_structure_revision,
            expected_memory_revision=expected_memory_revision,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            plan=normalized_plan,
            authority_context=authority_context,
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
            operation_key=operation_key,
            limit=limit,
        )
        if build.preview.preview.preview_token != preview_token:
            raise ValueError(
                "P2P_STRUCTURE_REPLACEMENT_PREVIEW_MISMATCH: preview token is stale or does not match this request"
            )
        if not build.preview.preview.apply_allowed:
            raise ValueError(
                "P2P_STRUCTURE_REPLACEMENT_BLOCKED: "
                + ", ".join(build.preview.preview.blockers)
            )
        if build.preview.candidate is None or build.event is None or not build.candidate_bytes:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_NO_CHANGE: replacement has no semantic effect")
        evidence = build.authority
        readiness_identity = _projected_identity(
            build.preview.candidate,
            str(build.preview.candidate_memory_revision or ""),
        )
        classification_identity = dict(readiness_identity)
        summary = {
            "contract": STRUCTURE_REPLACEMENT_RESULT_CONTRACT,
            "status": "applied",
            "operation": PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
            "operation_id": PROJECT_STRUCTURE_REPLACEMENT_OPERATION_ID,
            "request": build.request,
            "target": build.preview.target.to_dict(),
            "previous_revision": build.preview.current.revision,
            "previous_checksum": build.preview.current.checksum,
            "current": _structure_summary(build.preview.candidate),
            "previous_memory_revision": build.preview.previous_memory_revision,
            "current_memory_revision": build.preview.candidate_memory_revision,
            "event": build.event.to_dict(),
            "applied_dispositions": [
                item.to_dict() for item in build.preview.applied_dispositions
            ],
            "readiness_identity": readiness_identity,
            "classification_identity": classification_identity,
            "receipt": {
                "operation_key_sha256": idempotency_key_sha256(operation_key),
                "capability": PROJECT_STRUCTURE_REPLACEMENT_CAPABILITY,
            },
            "detached_copy": True,
            "active_release_subscription": False,
            "remote_publication": False,
            "publisher_ownership_granted": False,
            "moderation_rights_granted": False,
            "changed_paths": sorted(build.candidate_bytes),
        }
        receipt_path, receipt_content, _receipt = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
            actor=evidence.executor.identity_id,
            request_fingerprint_sha256=build.request_fingerprint_sha256,
            preview_token=preview_token,
            result=summary,
            candidates=build.candidate_bytes,
            authority=evidence,
        )
        sources = (
            *build.source_preconditions,
            source_precondition(receipt_path, None),
        )
        mutation = self.atomic_writer.apply(
            operation_id="project-structure-replacement",
            candidates={**build.candidate_bytes, receipt_path: receipt_content},
            sources=sources,
            preview_token=preview_token,
            actor=evidence.executor.identity_id,
            candidate_validator=lambda view: self._validate_candidate_view(
                view,
                build=build,
            ),
        )
        if mutation.status != "applied":
            replay = self._exact_replay(
                operation_key=operation_key,
                request=request,
                preview_token=preview_token,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                authority_context=authority_context,
                channel=channel,
                consent_id=consent_id,
                consent_sha256=consent_sha256,
            )
            if replay is not None:
                return replay
            raise ValueError(
                "P2P_STRUCTURE_REPLACEMENT_MUTATION_FAILED: "
                + (mutation.message or mutation.status)
            )
        self.memory_service.invalidate()
        current = self.structure_service.show(include_retired=True)
        self._validate_post_apply(
            expected=current,
            expected_memory_revision=str(build.preview.candidate_memory_revision or ""),
            readiness_identity=readiness_identity,
            classification_identity=classification_identity,
        )
        return ProjectStructureReplacementResult(
            status="applied",
            previous=build.preview.current,
            current=current,
            target=build.preview.target,
            previous_memory_revision=build.preview.previous_memory_revision,
            current_memory_revision=str(build.preview.candidate_memory_revision or ""),
            event=build.event,
            actor=evidence.executor.identity_id,
            dispositions=build.preview.applied_dispositions,
            readiness_identity=readiness_identity,
            classification_identity=classification_identity,
            changed_paths=tuple(sorted(build.candidate_bytes)),
            message="Project structure replacement applied atomically.",
        )

    def _build(
        self,
        *,
        target: str,
        expected_structure_revision: int,
        expected_memory_revision: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        plan: StructureReplacementPlan | Mapping[str, object] | None,
        authority_context: AuthorityContext | None,
        channel: str,
        consent_id: str | None,
        consent_sha256: str | None,
        operation_key: str | None,
        limit: int,
    ) -> _Build:
        if isinstance(expected_structure_revision, bool) or expected_structure_revision < 1:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_STALE_STRUCTURE: expected structure revision is invalid")
        _require_sha256(expected_memory_revision, "expected_memory_revision")
        if isinstance(limit, bool) or limit < 1 or limit > 1000:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_LIMIT_INVALID: limit must be between 1 and 1000")
        timestamp = self.clock()
        normalized_plan = _plan_from_input(plan)
        plan_supplied = normalized_plan is not None
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=(PROJECT_STRUCTURE_REPLACEMENT_CAPABILITY,),
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        resolved = self._resolve_target(target, actor=evidence.subject.identity_id, timestamp=timestamp)
        if normalized_plan is not None:
            self._validate_plan_target(normalized_plan, resolved.release)
        previous = self.structure_service.show(include_retired=True)
        if expected_structure_revision != previous.revision:
            raise ValueError(
                "P2P_STRUCTURE_REPLACEMENT_STALE_STRUCTURE: expected revision "
                f"{expected_structure_revision}, current revision is {previous.revision}"
            )
        records, truncated_sources = self.memory_service._source_records()
        records_by_path = {path: content for path, content in records}
        memory_revision = _memory_revision(records)
        if expected_memory_revision != memory_revision:
            raise ValueError(
                "P2P_STRUCTURE_REPLACEMENT_STALE_MEMORY: expected memory revision does not match current memory"
            )

        target_blockers = self._target_blockers(resolved.active_structure)
        elements = self._compare_elements(previous, resolved.active_structure)
        conflict_count = len([item for item in elements if item.state == "conflicting"])
        removed_targets = self._removed_targets(previous, resolved.active_structure)
        retiring_sections = {
            item.element_id for item in removed_targets if item.kind == "section"
        }
        direct_artifacts = {
            item.element_id for item in removed_targets if item.kind == "artifact"
        }
        direct_fields = {
            (item.section_id, item.element_id)
            for item in removed_targets
            if item.kind == "field"
        }
        structural_impacts = list(
            self.retirement._structural_impacts(
                previous,
                targets=removed_targets,
                retiring_sections=retiring_sections,
                direct_artifacts=direct_artifacts,
            )
        )
        reference_items, questions_artifact, index_blockers = self.retirement._reference_index(
            structure=previous,
            records_by_path=records_by_path,
        )
        memory_impacts = list(
            self.retirement._memory_impacts(
                retiring_sections=retiring_sections,
                direct_fields=direct_fields,
                direct_artifacts=direct_artifacts,
                reference_items=reference_items,
                questions_artifact=questions_artifact,
            )
        )
        impacts = [*structural_impacts, *memory_impacts]
        required_disposition_impacts = [
            item for item in impacts if item.required_disposition
        ]
        blockers: list[str] = list(target_blockers)
        if conflict_count:
            blockers.append("P2P_STRUCTURE_REPLACEMENT_ID_CONFLICT")
        blockers.extend(index_blockers)
        if truncated_sources:
            blockers.append("P2P_STRUCTURE_REPLACEMENT_REFERENCE_INDEX_INCOMPLETE")
        if len(impacts) > limit or len(elements) > limit:
            blockers.append("P2P_STRUCTURE_REPLACEMENT_IMPACT_TRUNCATED")
        if not plan_supplied:
            if required_disposition_impacts:
                blockers.append("P2P_STRUCTURE_REPLACEMENT_DISPOSITION_REQUIRED")
            blockers.append("P2P_STRUCTURE_REPLACEMENT_PLAN_REQUIRED")
        if normalized_plan is not None:
            blockers.extend(
                self._disposition_blockers(
                    required=required_disposition_impacts,
                    plan=normalized_plan,
                    target_structure=resolved.active_structure,
                )
            )

        structural_candidate: ProjectStructure | None = None
        if not target_blockers and not conflict_count:
            structural_candidate = self._candidate_structure(
                previous,
                target=resolved.active_structure,
                release=resolved.release,
            )
            structural_candidate = with_project_structure_checksum(
                replace(structural_candidate, revision=previous.revision + 1)
            )
            if structural_candidate.checksum == previous.checksum:
                blockers.append("P2P_STRUCTURE_REPLACEMENT_NO_CHANGE")
        candidate_structure: ProjectStructure | None = None
        candidate_memory_revision: str | None = None
        candidate_bytes: dict[str, bytes] = {}
        event: ProjectStructureEvent | None = None
        applied_dispositions: tuple[StructureRetirementDisposition, ...] = ()
        if not blockers and structural_candidate is not None and normalized_plan is not None:
            candidate_structure = structural_candidate
            structure_id, current_events = project_structure_events_from_bytes(
                (self.root / PROJECT_STRUCTURE_EVENTS_PATH).read_bytes()
            )
            if structure_id != previous.structure_id:
                raise ValueError("P2P_STRUCTURE_REPLACEMENT_INVALID: event ledger identity mismatch")
            if len(current_events) >= PROJECT_STRUCTURE_EVENT_LIMIT:
                raise ValueError("P2P_STRUCTURE_REPLACEMENT_EVENT_LIMIT: event limit exceeded")
            applied_dispositions = tuple(
                normalized_plan.by_id[item.impact_id]
                for item in required_disposition_impacts
            )
            event = ProjectStructureEvent(
                event_id=f"structure-event-{candidate_structure.revision:08d}",
                event_type="structure_replaced",
                revision=candidate_structure.revision,
                checksum=candidate_structure.checksum,
                occurred_at=timestamp,
                subject_id=evidence.subject.identity_id,
                executor_id=evidence.executor.identity_id,
                authority=evidence.to_dict(),
                details={
                    "target": resolved.release.to_dict(),
                    "previous": _structure_summary(previous),
                    "detached_copy": True,
                    "active_release_subscription": False,
                    "required_disposition_ids": [
                        item.impact_id for item in required_disposition_impacts
                    ],
                    "applied_dispositions": [
                        item.to_dict() for item in applied_dispositions
                    ],
                    "previous_memory_revision": memory_revision,
                },
            )
            candidate_bytes = {
                PROJECT_STRUCTURE_PATH: project_structure_bytes(candidate_structure),
                PROJECT_STRUCTURE_EVENTS_PATH: project_structure_events_bytes(
                    structure_id=candidate_structure.structure_id,
                    events=(*current_events, event),
                ),
                PROJECT_STRUCTURE_SNAPSHOTS_PATH: self.snapshots.candidate_bytes(
                    previous=previous,
                    retained_at=timestamp,
                    retained_by=evidence.subject.identity_id,
                    reason="before-replacement",
                ),
            }
            internal_plan = StructureRetirementPlan(
                dispositions=tuple(normalized_plan.dispositions)
            )
            memory_candidates = self.retirement._memory_candidates(
                plan=internal_plan,
                required=required_disposition_impacts,
                candidate_structure=candidate_structure,
                records_by_path=records_by_path,
                evidence=evidence,
                timestamp=timestamp,
                retiring_sections=retiring_sections,
                direct_fields=direct_fields,
            )
            candidate_bytes.update(memory_candidates)
            next_records = dict(records_by_path)
            for path, content in memory_candidates.items():
                next_records[path] = content
            candidate_memory_revision = _memory_revision(next_records)
            event = replace(
                event,
                details={
                    **dict(event.details),
                    "current_memory_revision": candidate_memory_revision,
                },
            )
            candidate_bytes[PROJECT_STRUCTURE_EVENTS_PATH] = project_structure_events_bytes(
                structure_id=candidate_structure.structure_id,
                events=(*current_events, event),
            )
        elif structural_candidate is not None:
            candidate_structure = structural_candidate

        internal_plan = StructureRetirementPlan(
            dispositions=tuple(normalized_plan.dispositions)
        ) if normalized_plan is not None else StructureRetirementPlan()
        classification_projection = _classification_projection(
            reference_items=reference_items,
            required=required_disposition_impacts,
            plan=internal_plan,
            blockers=blockers,
        )
        if structural_candidate is not None:
            classification_projection = {
                **classification_projection,
                "source_identity": _projected_identity(
                    structural_candidate,
                    candidate_memory_revision or memory_revision,
                ),
            }
        readiness_projection = self._readiness_projection(
            current=previous,
            target=resolved.active_structure,
            candidate=structural_candidate,
            memory_revision=candidate_memory_revision or memory_revision,
            blockers=blockers,
        )
        request = _request_payload(
            plan=normalized_plan,
            expected_structure_revision=expected_structure_revision,
            expected_memory_revision=expected_memory_revision,
        )
        preview_fingerprint = semantic_sha256(
            {
                "policy_version": PROJECT_STRUCTURE_REPLACEMENT_POLICY_VERSION,
                "operation": PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
                "request": request,
                "authority_context_sha256": context.digest_sha256,
            }
        )
        request_fingerprint = semantic_sha256(
            {
                "policy_version": PROJECT_STRUCTURE_REPLACEMENT_POLICY_VERSION,
                "operation": PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
                "operation_key_sha256": (
                    idempotency_key_sha256(operation_key)
                    if operation_key is not None
                    else None
                ),
                "request": request,
                "authority_context_sha256": context.digest_sha256,
            }
        )
        blockers = sorted(set(blockers))
        preview = MutationPreviewService.build(
            operation_id=f"project-structure-replacement:{_operation_slug(resolved.release.coordinate)}",
            targets=tuple(sorted(candidate_bytes)) or (
                PROJECT_STRUCTURE_EVENTS_PATH,
                PROJECT_STRUCTURE_PATH,
            ),
            actor=evidence.executor.identity_id,
            authority="typed_authority_context",
            sources=self.retirement._source_preconditions(records_by_path),
            candidate_semantics=self._candidate_semantics(
                release=resolved.release,
                candidate_structure=structural_candidate,
                event=event,
                elements=elements,
                impacts=impacts,
                blockers=blockers,
                applied_dispositions=applied_dispositions,
                plan=normalized_plan,
            ),
            semantic_diff={
                "contract": STRUCTURE_REPLACEMENT_IMPACT_CONTRACT,
                "target": resolved.release.to_dict(),
                "elements": [item.to_dict() for item in elements[:limit]],
                "element_total": len(elements),
                "element_returned": min(len(elements), limit),
                "element_truncated": len(elements) > limit,
                "impacts": [item.to_dict() for item in impacts[:limit]],
                "impact_total": len(impacts),
                "impact_returned": min(len(impacts), limit),
                "impact_truncated": len(impacts) > limit,
                "required_dispositions": [
                    item.to_dict() for item in required_disposition_impacts[:limit]
                ],
                "memory_revision_before": memory_revision,
                "memory_revision_after": candidate_memory_revision,
                "classification_projection": classification_projection,
                "readiness_projection": readiness_projection,
                "structure_revision_before": previous.revision,
                "structure_revision_after": (
                    structural_candidate.revision
                    if structural_candidate is not None
                    else None
                ),
                "detached_copy": True,
                "active_release_subscription": False,
            },
            token_context={
                "request_fingerprint_sha256": preview_fingerprint,
                "authority_context_sha256": context.digest_sha256,
                "source_structure_revision": previous.revision,
                "source_structure_checksum": previous.checksum,
                "source_memory_revision": memory_revision,
                "target_coordinate": resolved.release.coordinate,
                "target_semantic_checksum": resolved.release.semantic_checksum,
                "operation": PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
                "request": request,
            },
            blockers=blockers,
            policy_version=PROJECT_STRUCTURE_REPLACEMENT_POLICY_VERSION,
        )
        public_preview = ProjectStructureReplacementPreview(
            target=resolved.release,
            current=previous,
            previous_memory_revision=memory_revision,
            candidate=candidate_structure,
            candidate_memory_revision=candidate_memory_revision,
            elements=tuple(elements[:limit]),
            impacts=tuple(impacts[:limit]),
            required_dispositions=tuple(required_disposition_impacts[:limit]),
            applied_dispositions=applied_dispositions,
            preview=(
                replace(preview, preview_token="", apply_allowed=False)
                if blockers or not plan_supplied
                else preview
            ),
            plan_complete=plan_supplied and not blockers,
            classification_projection=classification_projection,
            readiness_projection=readiness_projection,
            blockers=tuple(blockers),
            message=(
                "Replacement preview is applyable."
                if preview.apply_allowed and plan_supplied
                else "Replacement preview has unresolved blockers."
            ),
        )
        return _Build(
            preview=public_preview,
            request_fingerprint_sha256=request_fingerprint,
            source_preconditions=self.retirement._source_preconditions(records_by_path),
            candidate_bytes=candidate_bytes,
            event=event,
            authority=evidence,
            request=request,
        )

    def _resolve_target(
        self,
        target: str,
        *,
        actor: str,
        timestamp: str,
    ) -> _ResolvedTarget:
        reference = str(target or "").strip()
        if not reference:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_TARGET_REQUIRED: exact target release is required")
        path = Path(reference)
        root_path = path if path.is_absolute() else self.root / path
        artifact_checksum = ""
        source_type = ""
        resolved_from = ""
        if root_path.exists():
            inspection = self.package_service.inspect(root_path, view="effective")
            pack = inspection.pack
            coordinate = str(VerticalCoordinate.parse(pack.coordinate))
            checksum = inspection.semantic_checksum
            artifact_checksum = inspection.artifact_checksum
            source_type = "portable_archive" if root_path.is_file() else "portable_directory"
        else:
            coordinate = str(VerticalCoordinate.parse(reference))
            resolved = self.vertical_service.resolve_pack(coordinate)
            pack = resolved.pack
            checksum = resolved.checksum
            source_type = resolved.source.source_type
        if pack.schema_version != PORTABLE_VERTICAL_SCHEMA_VERSION:
            raise ValueError(
                "P2P_STRUCTURE_REPLACEMENT_UNSUPPORTED_TARGET: target release must use portable schema 3"
            )
        source = StructureSource.vertical_release(coordinate, checksum)
        active = project_structure_from_vertical_pack(
            project_id="replacement-target",
            pack=pack,
            source=source,
            origin={
                "kind": "vertical_release",
                "identity": coordinate,
                "checksum": checksum,
                "external_ref": None,
            },
            actor=actor,
            applied_at=timestamp,
        )
        release = StructureReplacementRelease(
            reference=coordinate,
            coordinate=coordinate,
            semantic_checksum=checksum,
            schema_version=pack.schema_version,
            source_type=source_type,
            resolved_from=resolved_from,
            artifact_checksum=artifact_checksum,
        )
        return _ResolvedTarget(release=release, pack=pack, active_structure=active)

    def _target_blockers(self, structure: ProjectStructure) -> list[str]:
        validate_project_structure(structure)
        active_sections = set(structure.active_section_ids())
        blockers: list[str] = []
        if not active_sections:
            blockers.append("P2P_STRUCTURE_REPLACEMENT_EMPTY_TARGET: target release has no active sections")
        active_criteria = [
            item
            for item in structure.criteria
            if item.lifecycle == "active"
            and item.enabled
            and item.section_id in active_sections
        ]
        if not active_criteria:
            blockers.append("P2P_STRUCTURE_REPLACEMENT_NO_ACTIVE_CRITERIA: target release has no active criteria")
        return blockers

    def _compare_elements(
        self,
        current: ProjectStructure,
        target: ProjectStructure,
    ) -> tuple[StructureReplacementElement, ...]:
        current_all = _element_map(current, active_only=False)
        current_active = _element_map(current, active_only=True)
        target_active = _element_map(target, active_only=True)
        elements: list[StructureReplacementElement] = []
        for identity in sorted(set(current_all) | set(target_active)):
            current_entry = current_all.get(identity)
            current_active_entry = current_active.get(identity)
            target_entry = target_active.get(identity)
            kind = (current_entry or target_entry or current_active_entry)["kind"]  # type: ignore[index]
            if current_entry is not None and target_entry is not None and current_entry["hash"] != target_entry["hash"]:
                elements.append(
                    StructureReplacementElement(
                        kind=str(kind),
                        identity=identity,
                        state="conflicting",
                        current_hash=str(current_entry["hash"]),
                        target_hash=str(target_entry["hash"]),
                        message="Stable identity exists in both structures with incompatible semantics.",
                    )
                )
                continue
            if current_active_entry is not None and target_entry is not None:
                elements.append(
                    StructureReplacementElement(
                        kind=str(kind),
                        identity=identity,
                        state="preserved",
                        current_hash=str(current_active_entry["hash"]),
                        target_hash=str(target_entry["hash"]),
                    )
                )
                continue
            if current_active_entry is not None and target_entry is None:
                elements.append(
                    StructureReplacementElement(
                        kind=str(kind),
                        identity=identity,
                        state="retired",
                        current_hash=str(current_active_entry["hash"]),
                        message="Current active element is absent from the target release.",
                    )
                )
                continue
            if target_entry is not None:
                elements.append(
                    StructureReplacementElement(
                        kind=str(kind),
                        identity=identity,
                        state="added",
                        target_hash=str(target_entry["hash"]),
                        message="Target release element is not active in the current project structure.",
                    )
                )
        return tuple(elements)

    def _removed_targets(
        self,
        current: ProjectStructure,
        target: ProjectStructure,
    ) -> tuple[StructureRetirementTarget, ...]:
        target_active = _element_map(target, active_only=True)
        removed: list[StructureRetirementTarget] = []
        for identity, entry in _element_map(current, active_only=True).items():
            if identity in target_active:
                continue
            kind = str(entry["kind"])
            if kind == "field":
                section_id, field_id = identity.removeprefix("field:").split("/", 1)
                removed.append(
                    StructureRetirementTarget(
                        kind="field",
                        element_id=field_id,
                        section_id=section_id,
                    )
                )
            else:
                removed.append(
                    StructureRetirementTarget(
                        kind=kind,
                        element_id=identity.split(":", 1)[1],
                    )
                )
        return tuple(sorted(removed, key=lambda item: item.identity))

    def _candidate_structure(
        self,
        current: ProjectStructure,
        *,
        target: ProjectStructure,
        release: StructureReplacementRelease,
    ) -> ProjectStructure:
        origin = replace(
            target.origin,
            identity=release.coordinate,
            checksum=release.semantic_checksum,
            external_ref=None,
        )
        active_sections = [
            replace(item, lifecycle="active", order=index)
            for index, item in enumerate(
                sorted(target.sections, key=lambda value: (value.order, value.section_id))
            )
            if item.lifecycle == "active"
        ]
        target_keys = _element_key_sets(target)
        sections = [
            *active_sections,
            *(
                replace(item, lifecycle="retired")
                for item in current.sections
                if ("section", item.section_id) not in target_keys["section"]
            ),
        ]
        fields = [
            *(
                replace(item, lifecycle="active")
                for item in sorted(
                    target.fields,
                    key=lambda value: (value.section_id, value.order, value.field_id),
                )
                if item.lifecycle == "active"
            ),
            *(
                replace(item, lifecycle="retired")
                for item in current.fields
                if ("field", item.section_id, item.field_id) not in target_keys["field"]
            ),
        ]
        questions = [
            *(
                replace(item, lifecycle="active")
                for item in sorted(
                    target.questions,
                    key=lambda value: (value.section_id, value.order, value.question_id),
                )
                if item.lifecycle == "active"
            ),
            *(
                replace(item, lifecycle="retired")
                for item in current.questions
                if ("question", item.question_id) not in target_keys["question"]
            ),
        ]
        criteria = [
            *(
                replace(item, lifecycle="active")
                for item in sorted(
                    target.criteria,
                    key=lambda value: (value.section_id, value.order, value.criterion_id),
                )
                if item.lifecycle == "active"
            ),
            *(
                replace(item, lifecycle="retired")
                for item in current.criteria
                if ("criterion", item.criterion_id) not in target_keys["criterion"]
            ),
        ]
        artifacts = [
            *(
                replace(item, lifecycle="active")
                for item in sorted(
                    target.artifacts,
                    key=lambda value: (value.order, value.artifact_id),
                )
                if item.lifecycle == "active"
            ),
            *(
                replace(item, lifecycle="retired")
                for item in current.artifacts
                if ("artifact", item.artifact_id) not in target_keys["artifact"]
            ),
        ]
        return replace(
            target,
            structure_id=current.structure_id,
            revision=current.revision + 1,
            origin=origin,
            sections=tuple(sections),
            fields=tuple(fields),
            questions=tuple(questions),
            criteria=tuple(criteria),
            artifacts=tuple(artifacts),
        )

    def _disposition_blockers(
        self,
        *,
        required: Sequence[StructureRetirementImpact],
        plan: StructureReplacementPlan,
        target_structure: ProjectStructure,
    ) -> list[str]:
        blockers: list[str] = []
        required_ids = {item.impact_id for item in required if item.required_disposition}
        planned_ids = set(plan.by_id)
        if sorted(required_ids - planned_ids):
            blockers.append("P2P_STRUCTURE_REPLACEMENT_DISPOSITION_REQUIRED")
        if sorted(planned_ids - required_ids):
            blockers.append("P2P_STRUCTURE_REPLACEMENT_DISPOSITION_UNKNOWN")
        by_required = {item.impact_id: item for item in required if item.required_disposition}
        active_sections = set(target_structure.active_section_ids())
        for disposition_id in sorted(planned_ids & required_ids):
            disposition = plan.by_id[disposition_id]
            impact = by_required[disposition_id]
            if disposition.action not in impact.allowed_actions:
                blockers.append("P2P_STRUCTURE_REPLACEMENT_DISPOSITION_INVALID")
                continue
            if disposition.action == "reassign_sections":
                invalid = sorted(set(disposition.section_ids) - active_sections)
                if invalid:
                    blockers.append("P2P_STRUCTURE_REPLACEMENT_DISPOSITION_INVALID")
        return blockers

    def _validate_candidate_view(self, view: object, *, build: _Build) -> None:
        candidate = build.preview.candidate
        if candidate is None or build.event is None:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_INVALID: missing candidate")
        structure = project_structure_from_bytes(
            view.read_bytes(PROJECT_STRUCTURE_PATH)  # type: ignore[attr-defined]
        )
        structure_id, events = project_structure_events_from_bytes(
            view.read_bytes(PROJECT_STRUCTURE_EVENTS_PATH)  # type: ignore[attr-defined]
        )
        if (
            structure_id != structure.structure_id
            or not events
            or events[-1].event_type != "structure_replaced"
            or events[-1].revision != structure.revision
            or events[-1].checksum != structure.checksum
            or structure.checksum != candidate.checksum
        ):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_INVALID: candidate event ledger mismatch")
        proposal_ids = {
            impact.object_id
            for impact in build.preview.required_dispositions
            if impact.object_type == "proposal"
        }
        for proposal_id in proposal_ids:
            scope_path = self.retirement._proposal_scope_path(proposal_id)
            events_path = scope_path.rsplit("/", 1)[0] + "/memory-scope-events.yml"
            from p2p_engine.services.project_memory import validated_scope_pair_from_bytes

            validated_scope_pair_from_bytes(
                view.read_bytes(scope_path),  # type: ignore[attr-defined]
                view.read_bytes(events_path),  # type: ignore[attr-defined]
                expected_proposal_id=proposal_id,
            )
        if any(
            impact.object_type == "formal_question"
            for impact in build.preview.required_dispositions
        ):
            from p2p_engine.services.project_questions import PROJECT_QUESTIONS_PATH

            self.question_service.parse_bytes(
                view.read_bytes(PROJECT_QUESTIONS_PATH.as_posix()),  # type: ignore[attr-defined]
                target=PROJECT_QUESTIONS_PATH.as_posix(),
            )

    def _candidate_semantics(
        self,
        *,
        release: StructureReplacementRelease,
        candidate_structure: ProjectStructure | None,
        event: ProjectStructureEvent | None,
        elements: Sequence[StructureReplacementElement],
        impacts: Sequence[StructureRetirementImpact],
        blockers: Sequence[str],
        applied_dispositions: Sequence[StructureRetirementDisposition],
        plan: StructureReplacementPlan | None,
    ) -> dict[str, object]:
        if candidate_structure is None or event is None:
            return {
                "target": release.to_dict(),
                "blocked": sorted(set(blockers)),
                "element_states": [item.to_dict() for item in elements],
                "impact_ids": [item.impact_id for item in impacts],
                "plan": plan.to_dict() if plan is not None else None,
            }
        return {
            "target": release.to_dict(),
            PROJECT_STRUCTURE_PATH: {
                "structure_id": candidate_structure.structure_id,
                "revision": candidate_structure.revision,
                "checksum": candidate_structure.checksum,
                "origin": {
                    "kind": candidate_structure.origin.kind,
                    "identity": candidate_structure.origin.identity,
                    "checksum": candidate_structure.origin.checksum,
                },
                "semantic_payload": candidate_structure.semantic_payload(),
            },
            PROJECT_STRUCTURE_EVENTS_PATH: {
                "event_type": event.event_type,
                "revision": event.revision,
                "checksum": event.checksum,
                "target": event.details.get("target"),
                "detached_copy": event.details.get("detached_copy"),
                "required_disposition_ids": list(
                    event.details.get("required_disposition_ids", ())
                ),
                "applied_dispositions": list(
                    event.details.get("applied_dispositions", ())
                ),
            },
            "applied_dispositions": [
                item.to_dict() for item in applied_dispositions
            ],
            "plan": plan.to_dict() if plan is not None else None,
        }

    def _readiness_projection(
        self,
        *,
        current: ProjectStructure,
        target: ProjectStructure,
        candidate: ProjectStructure | None,
        memory_revision: str,
        blockers: Sequence[str],
    ) -> dict[str, object]:
        before = _active_readiness_counts(current)
        after_source = candidate or target
        after = _active_readiness_counts(after_source)
        payload: dict[str, object] = {
            "status": "blocked" if blockers else "projected",
            "before": before,
            "after": after if not blockers else None,
            "active_sections_delta": after["active_sections"] - before["active_sections"],
            "active_criteria_delta": after["active_criteria"] - before["active_criteria"],
            "score_projection": None,
            "score_projection_reason": "readiness is recalculated from project-owned structure and memory after apply",
        }
        if candidate is not None:
            payload["source_identity"] = _projected_identity(candidate, memory_revision)
        return payload

    def _validate_post_apply(
        self,
        *,
        expected: ProjectStructure,
        expected_memory_revision: str,
        readiness_identity: Mapping[str, object],
        classification_identity: Mapping[str, object],
    ) -> None:
        validate_project_structure(expected)
        classification = self.memory_service.classification()
        observed_classification = {
            "structure_id": classification.structure_id,
            "structure_revision": classification.structure_revision,
            "structure_checksum": classification.structure_checksum,
            "memory_revision": classification.memory_revision,
        }
        if observed_classification != dict(classification_identity):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_POST_APPLY_INVALID: memory classification identity mismatch")
        if classification.memory_revision != expected_memory_revision:
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_POST_APPLY_INVALID: memory revision mismatch")
        if self.readiness_result is None:
            return
        readiness = self.readiness_result()
        snapshot = getattr(readiness, "snapshot", None)
        observed_readiness = {
            "structure_id": getattr(snapshot, "structure_id", ""),
            "structure_revision": getattr(snapshot, "structure_revision", 0),
            "structure_checksum": getattr(snapshot, "structure_checksum", ""),
            "memory_revision": getattr(snapshot, "memory_revision", ""),
        }
        if observed_readiness != dict(readiness_identity):
            raise ValueError("P2P_STRUCTURE_REPLACEMENT_POST_APPLY_INVALID: readiness identity mismatch")

    def _exact_replay(
        self,
        *,
        operation_key: str,
        request: Mapping[str, object],
        preview_token: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        channel: str,
        consent_id: str | None,
        consent_sha256: str | None,
    ) -> ProjectStructureReplacementResult | None:
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is None:
            return None
        if receipt.operation != PROJECT_STRUCTURE_REPLACEMENT_OPERATION or receipt.authority is None:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation")
        if receipt.preview_token_sha256 != preview_token_sha256(preview_token):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: preview token differs")
        result = receipt.result
        if result.get("request") != dict(request):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key is bound to another replacement request")
        evidence = self.codec.evidence_from_mapping(receipt.authority)
        if (
            evidence.subject.identity_id != actor_id
            or evidence.executor.identity_id != executor_id
            or evidence.executor.kind.value != executor_kind
            or evidence.channel != channel
            or evidence.consent_id != consent_id
        ):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: replacement authority differs")
        if consent_sha256 is not None and consent_sha256 != evidence.consent_sha256:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: replacement consent content differs")
        if authority_context is not None and authority_context.digest_sha256 != evidence.authority_context_sha256:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: replacement authority context differs")
        status = self.receipts.status(idempotency_key=operation_key)
        if status.postconditions_match is not True:
            raise ValueError("P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: replacement postconditions no longer match")
        current_summary = _summary_from_mapping(result.get("current"))
        current = self.structure_service.show(include_retired=True)
        if (
            current.structure_id != current_summary["structure_id"]
            or current.revision != current_summary["revision"]
            or current.checksum != current_summary["checksum"]
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: current structure differs from receipt"
            )
        event = _structure_event_from_mapping(result.get("event"))
        previous = replace(
            current,
            revision=int(result.get("previous_revision") or 0),
            checksum=str(result.get("previous_checksum") or ""),
        )
        target = _release_from_mapping(result.get("target"))
        dispositions = tuple(
            StructureRetirementDisposition(
                disposition_id=item.get("id"),  # type: ignore[arg-type]
                action=str(item.get("action") or ""),
                section_ids=tuple(
                    str(section)
                    for section in _mapping_sequence(item.get("section_ids"))
                ),
                reason=str(item.get("reason") or ""),
            )
            for item in _mapping_sequence(result.get("applied_dispositions"))
            if isinstance(item, Mapping)
        )
        readiness_identity = result.get("readiness_identity")
        classification_identity = result.get("classification_identity")
        if not isinstance(readiness_identity, Mapping) or not isinstance(classification_identity, Mapping):
            raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: replacement identity is invalid")
        return ProjectStructureReplacementResult(
            status="already_applied",
            previous=previous,
            current=current,
            target=target,
            previous_memory_revision=str(result.get("previous_memory_revision") or ""),
            current_memory_revision=str(result.get("current_memory_revision") or ""),
            event=event,
            actor=evidence.executor.identity_id,
            dispositions=dispositions,
            readiness_identity=dict(readiness_identity),
            classification_identity=dict(classification_identity),
            changed_paths=tuple(str(item) for item in result.get("changed_paths", ())),
            message="Project structure replacement was already applied with this operation key.",
        )

    def _validate_plan_target(
        self,
        plan: StructureReplacementPlan,
        release: StructureReplacementRelease,
    ) -> None:
        if (
            plan.target_coordinate != release.coordinate
            or plan.target_semantic_checksum != release.semantic_checksum
        ):
            raise ValueError(
                "P2P_STRUCTURE_REPLACEMENT_PLAN_TARGET_MISMATCH: plan target must match the resolved release coordinate and checksum"
            )


def _plan_from_input(
    plan: StructureReplacementPlan | Mapping[str, object] | None,
) -> StructureReplacementPlan | None:
    if isinstance(plan, StructureReplacementPlan):
        return plan
    return structure_replacement_plan_from_mapping(plan)


def _request_payload(
    *,
    plan: StructureReplacementPlan | None,
    expected_structure_revision: int,
    expected_memory_revision: str,
) -> dict[str, object]:
    return {
        "contract": STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
        "expected_structure_revision": expected_structure_revision,
        "expected_memory_revision": expected_memory_revision,
        "plan": _plan_payload(plan),
    }


def _plan_payload(plan: StructureReplacementPlan | None) -> dict[str, object] | None:
    if plan is None:
        return None
    return {
        "contract": plan.contract,
        "target": {
            "coordinate": plan.target_coordinate,
            "semantic_checksum": plan.target_semantic_checksum,
        },
        "dispositions": [
            item.to_dict()
            for item in sorted(plan.dispositions, key=lambda value: value.disposition_id)
        ],
    }


def _active_counts(structure: ProjectStructure) -> dict[str, int]:
    active_sections = set(structure.active_section_ids())
    return {
        "sections": len(active_sections),
        "fields": len(
            [
                item for item in structure.fields
                if item.lifecycle == "active" and item.section_id in active_sections
            ]
        ),
        "questions": len(
            [
                item for item in structure.questions
                if item.lifecycle == "active" and item.section_id in active_sections
            ]
        ),
        "criteria": len(
            [
                item for item in structure.criteria
                if item.lifecycle == "active"
                and item.enabled
                and item.section_id in active_sections
            ]
        ),
        "artifacts": len(
            [item for item in structure.artifacts if item.lifecycle == "active"]
        ),
    }


def _active_readiness_counts(structure: ProjectStructure) -> dict[str, int]:
    counts = _active_counts(structure)
    return {
        "active_sections": counts["sections"],
        "active_criteria": counts["criteria"],
    }


def _element_map(
    structure: ProjectStructure,
    *,
    active_only: bool,
) -> dict[str, dict[str, object]]:
    values: dict[str, dict[str, object]] = {}
    active_sections = set(structure.active_section_ids())

    def include(lifecycle: str, section_id: str | None = None) -> bool:
        if active_only and lifecycle != "active":
            return False
        if active_only and section_id is not None and section_id not in active_sections:
            return False
        return True

    for item in structure.sections:
        if include(item.lifecycle):
            values[f"section:{item.section_id}"] = {
                "kind": "section",
                "hash": _element_hash(item),
            }
    for item in structure.fields:
        if include(item.lifecycle, item.section_id):
            values[f"field:{item.section_id}/{item.field_id}"] = {
                "kind": "field",
                "hash": _element_hash(item),
            }
    for item in structure.questions:
        if include(item.lifecycle, item.section_id):
            values[f"question:{item.question_id}"] = {
                "kind": "question",
                "hash": _element_hash(item),
            }
    for item in structure.criteria:
        if include(item.lifecycle, item.section_id):
            values[f"criterion:{item.criterion_id}"] = {
                "kind": "criterion",
                "hash": _element_hash(item),
            }
    for item in structure.artifacts:
        if include(item.lifecycle):
            values[f"artifact:{item.artifact_id}"] = {
                "kind": "artifact",
                "hash": _element_hash(item),
            }
    return values


def _element_hash(item: object) -> str:
    payload = item.to_dict()  # type: ignore[attr-defined]
    payload.pop("order", None)
    payload.pop("lifecycle", None)
    return semantic_sha256(payload)


def _element_key_sets(structure: ProjectStructure) -> dict[str, set[tuple[str, ...]]]:
    return {
        "section": {
            ("section", item.section_id)
            for item in structure.sections
            if item.lifecycle == "active"
        },
        "field": {
            ("field", item.section_id, item.field_id)
            for item in structure.fields
            if item.lifecycle == "active"
        },
        "question": {
            ("question", item.question_id)
            for item in structure.questions
            if item.lifecycle == "active"
        },
        "criterion": {
            ("criterion", item.criterion_id)
            for item in structure.criteria
            if item.lifecycle == "active"
        },
        "artifact": {
            ("artifact", item.artifact_id)
            for item in structure.artifacts
            if item.lifecycle == "active"
        },
    }


def _projected_identity(
    structure: ProjectStructure,
    memory_revision: str,
) -> dict[str, object]:
    return {
        "structure_id": structure.structure_id,
        "structure_revision": structure.revision,
        "structure_checksum": structure.checksum,
        "memory_revision": memory_revision,
    }


def _structure_summary(structure: ProjectStructure) -> dict[str, object]:
    return {
        "contract": structure.contract,
        "structure_id": structure.structure_id,
        "revision": structure.revision,
        "checksum": structure.checksum,
    }


def _summary_from_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_STRUCTURE_REPLACEMENT_RECEIPT_INVALID: current summary must be a mapping")
    revision = value.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int):
        raise ValueError("P2P_STRUCTURE_REPLACEMENT_RECEIPT_INVALID: revision is invalid")
    checksum = str(value.get("checksum") or "")
    _require_sha256(checksum, "checksum")
    return {
        "structure_id": str(value.get("structure_id") or ""),
        "revision": revision,
        "checksum": checksum,
    }


def _release_from_mapping(value: object) -> StructureReplacementRelease:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_STRUCTURE_REPLACEMENT_RECEIPT_INVALID: target release is invalid")
    return StructureReplacementRelease(
        reference=str(value.get("reference") or ""),
        coordinate=str(value.get("coordinate") or ""),
        semantic_checksum=str(value.get("semantic_checksum") or ""),
        schema_version=int(value.get("schema_version") or 0),
        source_type=str(value.get("source_type") or ""),
        resolved_from=str(value.get("resolved_from") or ""),
        artifact_checksum=str(value.get("artifact_checksum") or ""),
    )


def _structure_event_from_mapping(value: object) -> ProjectStructureEvent:
    from p2p_engine.core.project_structure import project_structure_event_from_mapping

    return project_structure_event_from_mapping(value)


def _mapping_sequence(value: object) -> Sequence[object]:
    if isinstance(value, list):
        return value
    return ()


def _operation_slug(value: str) -> str:
    return value.replace("/", "-").replace("@", "-").replace(".", "-")


def _require_sha256(value: object, field: str) -> str:
    checksum = str(value or "").removeprefix("sha256:")
    if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
        raise ValueError(f"P2P_STRUCTURE_REPLACEMENT_INVALID: {field} must be SHA-256")
    return checksum

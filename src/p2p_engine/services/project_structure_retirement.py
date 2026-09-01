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
from p2p_engine.core.project_memory import (
    PROJECT_MEMORY_SCOPE_EVENT_LIMIT,
    ProjectMemoryScope,
    ProjectMemoryScopeEvent,
    ProjectMemoryScopeKind,
)
from p2p_engine.core.project_questions import (
    ProjectQuestion,
    ProjectQuestionApplicability,
    ProjectQuestionArtifact,
    ProjectQuestionState,
    ProjectQuestionTransition,
)
from p2p_engine.core.project_structure import (
    ProjectStructure,
    ProjectStructureEvent,
    StructureArtifact,
    with_project_structure_checksum,
)
from p2p_engine.core.project_structure_retirement import (
    STRUCTURE_RETIREMENT_IMPACT_CONTRACT,
    STRUCTURE_RETIREMENT_PLAN_CONTRACT,
    STRUCTURE_RETIREMENT_RESULT_CONTRACT,
    ProjectStructureRetirementPreview,
    ProjectStructureRetirementResult,
    StructureRetirementDisposition,
    StructureRetirementImpact,
    StructureRetirementPlan,
    StructureRetirementTarget,
    structure_retirement_plan_from_mapping,
)
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    preview_token_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.project_memory import (
    _memory_revision,
    scope_bytes,
    scope_events_bytes,
    validated_scope_pair_from_bytes,
)
from p2p_engine.services.project_questions import (
    PROJECT_QUESTIONS_PATH,
    ProjectQuestionStateService,
)
from p2p_engine.services.project_structure import (
    PROJECT_STRUCTURE_EVENT_LIMIT,
    PROJECT_STRUCTURE_EVENTS_PATH,
    PROJECT_STRUCTURE_PATH,
    project_structure_bytes,
    project_structure_events_bytes,
    project_structure_events_from_bytes,
    project_structure_from_bytes,
)
from p2p_engine.services.project_structure_snapshots import (
    PROJECT_STRUCTURE_SNAPSHOTS_PATH,
    ProjectStructureSnapshotService,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso

PROJECT_STRUCTURE_RETIREMENT_OPERATION = "project_structure_retirement"
PROJECT_STRUCTURE_RETIREMENT_POLICY_VERSION = 1
_ACTIVE_PROPOSAL_STATES = frozenset(
    {"undecided", "deferred", "accepted", "accepted_with_changes"}
)
_AUTHORITY_CREATING_PROPOSAL_STATES = frozenset(
    {"accepted", "accepted_with_changes"}
)
_ACTIVE_QUESTION_STATES = frozenset(
    {
        ProjectQuestionState.TO_ANSWER,
        ProjectQuestionState.ANSWERED,
        ProjectQuestionState.DEFERRED,
        ProjectQuestionState.MUTED,
    }
)


@dataclass(frozen=True)
class _Build:
    preview: ProjectStructureRetirementPreview
    request_fingerprint_sha256: str
    source_preconditions: tuple[SourcePrecondition, ...]
    candidate_bytes: dict[str, bytes]
    event: ProjectStructureEvent | None
    authority: AuthorityEvidence
    request: dict[str, object]


@dataclass(frozen=True)
class _ReferenceItem:
    object_type: str
    object_id: str
    lifecycle: str
    active: bool
    section_ids: tuple[str, ...]
    path: str
    scope_kind: str = ""


class ProjectStructureRetirementService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        structure_service,
        memory_service,
        question_service: ProjectQuestionStateService,
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
        self.authority = authority or ProjectAuthorityService(root=self.root, p2p_dir=self.p2p_dir)
        self.receipts = receipts or MutationReceiptService(root=self.root, p2p_dir=self.p2p_dir)
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)
        self.clock = clock
        self.codec = AuthorityContractCodec()
        self.snapshots = ProjectStructureSnapshotService(root=self.root)

    def preview(
        self,
        *,
        targets: Sequence[StructureRetirementTarget | Mapping[str, object]],
        expected_structure_revision: int,
        expected_memory_revision: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        plan: StructureRetirementPlan | Mapping[str, object] | None = None,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        limit: int = 100,
    ) -> ProjectStructureRetirementPreview:
        return self._build(
            targets=targets,
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
        targets: Sequence[StructureRetirementTarget | Mapping[str, object]],
        expected_structure_revision: int,
        expected_memory_revision: str,
        preview_token: str,
        operation_key: str,
        confirm: bool,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        plan: StructureRetirementPlan | Mapping[str, object],
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
        limit: int = 100,
    ) -> ProjectStructureRetirementResult:
        if not confirm:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_CONFIRM_REQUIRED: apply requires --confirm")
        validate_idempotency_key(operation_key)
        raw_targets = _targets_from_input(targets)
        normalized_plan = _plan_from_input(plan)
        request = _request_payload(
            targets=raw_targets,
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
            targets=raw_targets,
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
            raise ValueError("P2P_STRUCTURE_RETIREMENT_PREVIEW_MISMATCH: preview token is stale or does not match this request")
        if not build.preview.preview.apply_allowed:
            raise ValueError(
                "P2P_STRUCTURE_RETIREMENT_BLOCKED: "
                + ", ".join(build.preview.preview.blockers)
            )
        if build.preview.candidate is None or build.event is None or not build.candidate_bytes:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_NO_CHANGE: retirement has no semantic effect")
        evidence = build.authority
        summary = {
            "contract": STRUCTURE_RETIREMENT_RESULT_CONTRACT,
            "operation": PROJECT_STRUCTURE_RETIREMENT_OPERATION,
            "operation_id": "project.structure.retire.apply",
            "request": build.request,
            "resolved_targets": [item.to_dict() for item in build.preview.targets],
            "previous_revision": build.preview.current.revision,
            "previous_checksum": build.preview.current.checksum,
            "current": _structure_summary(build.preview.candidate),
            "previous_memory_revision": build.preview.previous_memory_revision,
            "current_memory_revision": build.preview.candidate_memory_revision,
            "event": build.event.to_dict(),
            "applied_dispositions": [
                item.to_dict() for item in build.preview.applied_dispositions
            ],
            "changed_paths": sorted(build.candidate_bytes),
        }
        receipt_path, receipt_content, _receipt = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=PROJECT_STRUCTURE_RETIREMENT_OPERATION,
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
            operation_id="project-structure-retirement",
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
                "P2P_STRUCTURE_RETIREMENT_MUTATION_FAILED: "
                + (mutation.message or mutation.status)
            )
        self.memory_service.invalidate()
        return ProjectStructureRetirementResult(
            status="applied",
            previous=build.preview.current,
            current=build.preview.candidate,
            previous_memory_revision=build.preview.previous_memory_revision,
            current_memory_revision=str(build.preview.candidate_memory_revision or ""),
            event=build.event,
            actor=evidence.executor.identity_id,
            targets=build.preview.targets,
            dispositions=build.preview.applied_dispositions,
            changed_paths=tuple(sorted(build.candidate_bytes)),
            message="Project structure retirement applied atomically.",
        )

    def _build(
        self,
        *,
        targets: Sequence[StructureRetirementTarget | Mapping[str, object]],
        expected_structure_revision: int,
        expected_memory_revision: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        plan: StructureRetirementPlan | Mapping[str, object] | None,
        authority_context: AuthorityContext | None,
        channel: str,
        consent_id: str | None,
        consent_sha256: str | None,
        operation_key: str | None,
        limit: int,
    ) -> _Build:
        if isinstance(expected_structure_revision, bool) or expected_structure_revision < 1:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_STALE_STRUCTURE: expected structure revision is invalid")
        _require_sha256(expected_memory_revision, "expected_memory_revision")
        if isinstance(limit, bool) or limit < 1 or limit > 1000:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_LIMIT_INVALID: limit must be between 1 and 1000")
        raw_targets = _targets_from_input(targets)
        normalized_plan = _plan_from_input(plan)
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=("project.structure.retire",),
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        previous = self.structure_service.show(include_retired=True)
        if expected_structure_revision != previous.revision:
            raise ValueError(
                "P2P_STRUCTURE_RETIREMENT_STALE_STRUCTURE: expected revision "
                f"{expected_structure_revision}, current revision is {previous.revision}"
            )
        records, truncated_sources = self.memory_service._source_records()
        records_by_path = {path: content for path, content in records}
        memory_revision = _memory_revision(records)
        if expected_memory_revision != memory_revision:
            raise ValueError(
                "P2P_STRUCTURE_RETIREMENT_STALE_MEMORY: expected memory revision does not match current memory"
            )
        resolved_targets = self._resolve_targets(previous, raw_targets)
        request = _request_payload(
            targets=raw_targets,
            plan=normalized_plan,
            expected_structure_revision=expected_structure_revision,
            expected_memory_revision=expected_memory_revision,
        )
        preview_fingerprint = semantic_sha256(
            {
                "policy_version": PROJECT_STRUCTURE_RETIREMENT_POLICY_VERSION,
                "operation": PROJECT_STRUCTURE_RETIREMENT_OPERATION,
                "request": request,
                "authority_context_sha256": context.digest_sha256,
            }
        )
        request_fingerprint = semantic_sha256(
            {
                "policy_version": PROJECT_STRUCTURE_RETIREMENT_POLICY_VERSION,
                "operation": PROJECT_STRUCTURE_RETIREMENT_OPERATION,
                "operation_key_sha256": (
                    idempotency_key_sha256(operation_key)
                    if operation_key is not None
                    else None
                ),
                "request": request,
                "authority_context_sha256": context.digest_sha256,
            }
        )
        retiring_sections = {
            target.element_id for target in resolved_targets if target.kind == "section"
        }
        direct_artifacts = {
            target.element_id for target in resolved_targets if target.kind == "artifact"
        }
        direct_fields = {
            (target.section_id, target.element_id)
            for target in resolved_targets
            if target.kind == "field"
        }
        impacts = list(
            self._structural_impacts(
                previous,
                targets=resolved_targets,
                retiring_sections=retiring_sections,
                direct_artifacts=direct_artifacts,
            )
        )
        reference_items, questions_artifact, index_blockers = self._reference_index(
            structure=previous,
            records_by_path=records_by_path,
        )
        memory_impacts = list(
            self._memory_impacts(
                retiring_sections=retiring_sections,
                direct_fields=direct_fields,
                direct_artifacts=direct_artifacts,
                reference_items=reference_items,
                questions_artifact=questions_artifact,
            )
        )
        required_disposition_impacts = [
            item for item in memory_impacts if item.required_disposition
        ]
        impacts.extend(memory_impacts)
        blockers: list[str] = list(index_blockers)
        if truncated_sources:
            blockers.append("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE")
        disposition_blockers = self._disposition_blockers(
            required=required_disposition_impacts,
            plan=normalized_plan,
            structure=previous,
            retiring_sections=retiring_sections,
        )
        blockers.extend(disposition_blockers)
        candidate_structure: ProjectStructure | None = None
        candidate_memory_revision: str | None = None
        candidate_bytes: dict[str, bytes] = {}
        event: ProjectStructureEvent | None = None
        applied_dispositions: tuple[StructureRetirementDisposition, ...] = ()
        if not blockers:
            candidate_structure = self._candidate_structure(
                previous,
                targets=resolved_targets,
                plan=normalized_plan,
                retiring_sections=retiring_sections,
            )
            candidate_structure = with_project_structure_checksum(
                replace(candidate_structure, revision=previous.revision + 1)
            )
            if candidate_structure.checksum == previous.checksum:
                blockers.append("P2P_STRUCTURE_RETIREMENT_NO_CHANGE")
                candidate_structure = None
            else:
                structure_id, current_events = project_structure_events_from_bytes(
                    (self.root / PROJECT_STRUCTURE_EVENTS_PATH).read_bytes()
                )
                if structure_id != previous.structure_id:
                    raise ValueError("P2P_STRUCTURE_RETIREMENT_INVALID: event ledger identity mismatch")
                timestamp = self.clock()
                applied_dispositions = tuple(
                    normalized_plan.by_id[item.impact_id]
                    for item in required_disposition_impacts
                )
                event = ProjectStructureEvent(
                    event_id=f"structure-event-{candidate_structure.revision:08d}",
                    event_type="elements_retired",
                    revision=candidate_structure.revision,
                    checksum=candidate_structure.checksum,
                    occurred_at=timestamp,
                    subject_id=evidence.subject.identity_id,
                    executor_id=evidence.executor.identity_id,
                    authority=evidence.to_dict(),
                    details={
                        "targets": [item.to_dict() for item in resolved_targets],
                        "required_disposition_ids": [
                            item.impact_id for item in required_disposition_impacts
                        ],
                        "applied_dispositions": [
                            item.to_dict() for item in applied_dispositions
                        ],
                        "previous_memory_revision": memory_revision,
                    },
                )
                if len(current_events) >= PROJECT_STRUCTURE_EVENT_LIMIT:
                    raise ValueError("P2P_STRUCTURE_RETIREMENT_EVENT_LIMIT: event limit exceeded")
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
                        reason="before-retirement",
                    ),
                }
                memory_candidates = self._memory_candidates(
                    plan=normalized_plan,
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
        source_preconditions = self._source_preconditions(records_by_path)
        classification_projection = _classification_projection(
            reference_items=reference_items,
            required=required_disposition_impacts,
            plan=normalized_plan,
            blockers=blockers,
        )
        readiness_projection = _readiness_projection(
            structure=previous,
            targets=resolved_targets,
            retiring_sections=retiring_sections,
            candidate_structure=candidate_structure,
        )
        candidate_semantics = self._candidate_semantics(
            candidate_structure=candidate_structure,
            event=event,
            impacts=impacts,
            blockers=blockers,
            applied_dispositions=applied_dispositions,
        )
        preview = MutationPreviewService.build(
            operation_id="project-structure-retirement",
            targets=tuple(sorted(candidate_bytes)) or (
                PROJECT_STRUCTURE_EVENTS_PATH,
                PROJECT_STRUCTURE_PATH,
            ),
            actor=evidence.executor.identity_id,
            authority="typed_authority_context",
            sources=source_preconditions,
            candidate_semantics=candidate_semantics,
            semantic_diff={
                "contract": STRUCTURE_RETIREMENT_IMPACT_CONTRACT,
                "targets": [item.to_dict() for item in resolved_targets],
                "required_dispositions": [
                    item.to_dict() for item in required_disposition_impacts[:limit]
                ],
                "impacts": [item.to_dict() for item in impacts[:limit]],
                "impact_total": len(impacts),
                "impact_returned": min(len(impacts), limit),
                "impact_truncated": len(impacts) > limit,
                "memory_revision_before": memory_revision,
                "memory_revision_after": candidate_memory_revision,
                "classification_projection": classification_projection,
                "readiness_projection": readiness_projection,
                "structure_revision_before": previous.revision,
                "structure_revision_after": (
                    candidate_structure.revision
                    if candidate_structure is not None
                    else None
                ),
            },
            token_context={
                "request_fingerprint_sha256": preview_fingerprint,
                "authority_context_sha256": context.digest_sha256,
                "request": request,
            },
            blockers=tuple(sorted(set(blockers))),
            policy_version=PROJECT_STRUCTURE_RETIREMENT_POLICY_VERSION,
        )
        public_preview = ProjectStructureRetirementPreview(
            targets=resolved_targets,
            current=previous,
            previous_memory_revision=memory_revision,
            candidate=candidate_structure,
            candidate_memory_revision=candidate_memory_revision,
            impacts=tuple(impacts[:limit]),
            required_dispositions=tuple(required_disposition_impacts[:limit]),
            applied_dispositions=applied_dispositions,
            preview=preview,
            classification_projection=classification_projection,
            readiness_projection=readiness_projection,
            message=(
                "Retirement preview is applyable."
                if preview.apply_allowed
                else "Retirement preview has unresolved blockers."
            ),
        )
        return _Build(
            preview=public_preview,
            request_fingerprint_sha256=request_fingerprint,
            source_preconditions=source_preconditions,
            candidate_bytes=candidate_bytes,
            event=event,
            authority=evidence,
            request=request,
        )

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
    ) -> ProjectStructureRetirementResult | None:
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is None:
            return None
        if receipt.operation != PROJECT_STRUCTURE_RETIREMENT_OPERATION or receipt.authority is None:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation")
        if receipt.preview_token_sha256 != preview_token_sha256(preview_token):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: preview token differs")
        result = receipt.result
        if result.get("request") != dict(request):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key is bound to another retirement request")
        evidence = self.codec.evidence_from_mapping(receipt.authority)
        if (
            evidence.subject.identity_id != actor_id
            or evidence.executor.identity_id != executor_id
            or evidence.executor.kind.value != executor_kind
            or evidence.channel != channel
            or evidence.consent_id != consent_id
        ):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: retirement authority differs")
        if consent_sha256 is not None and consent_sha256 != evidence.consent_sha256:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: retirement consent content differs")
        if authority_context is not None and authority_context.digest_sha256 != evidence.authority_context_sha256:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: retirement authority context differs")
        status = self.receipts.status(idempotency_key=operation_key)
        if status.postconditions_match is not True:
            raise ValueError("P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: retirement postconditions no longer match")
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
        targets = tuple(
            StructureRetirementTarget(
                kind=str(item.get("kind") or ""),
                element_id=item.get("id"),  # type: ignore[arg-type]
                section_id=(
                    str(item.get("section_id"))
                    if item.get("section_id") is not None
                    else None
                ),
            )
            for item in _mapping_sequence(result.get("resolved_targets"))
            if isinstance(item, Mapping)
        )
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
        return ProjectStructureRetirementResult(
            status="already_applied",
            previous=previous,
            current=current,
            previous_memory_revision=str(result.get("previous_memory_revision") or ""),
            current_memory_revision=str(result.get("current_memory_revision") or ""),
            event=event,
            actor=evidence.executor.identity_id,
            targets=targets,
            dispositions=dispositions,
            changed_paths=tuple(str(item) for item in result.get("changed_paths", ())),
            message="Project structure retirement was already applied with this operation key.",
        )

    def _resolve_targets(
        self,
        structure: ProjectStructure,
        raw_targets: Sequence[StructureRetirementTarget],
    ) -> tuple[StructureRetirementTarget, ...]:
        resolved: list[StructureRetirementTarget] = []
        seen: set[str] = set()
        for target in raw_targets:
            item = self._resolve_target(structure, target)
            if item.identity in seen:
                raise ValueError(
                    f"P2P_STRUCTURE_RETIREMENT_TARGET_DUPLICATE: {item.identity}"
                )
            seen.add(item.identity)
            resolved.append(item)
        return tuple(sorted(resolved, key=lambda item: item.identity))

    def _resolve_target(
        self,
        structure: ProjectStructure,
        target: StructureRetirementTarget,
    ) -> StructureRetirementTarget:
        if target.kind == "section":
            active = {item.section_id for item in structure.sections if item.lifecycle == "active"}
            all_ids = {item.section_id for item in structure.sections}
            return _resolve_simple_target(target, active=active, all_ids=all_ids)
        if target.kind == "field":
            matches = [
                item
                for item in structure.fields
                if item.field_id == target.element_id
                and item.lifecycle == "active"
                and (target.section_id is None or item.section_id == target.section_id)
            ]
            all_matches = [
                item
                for item in structure.fields
                if item.field_id == target.element_id
                and (target.section_id is None or item.section_id == target.section_id)
            ]
            if not matches and all_matches:
                raise ValueError(
                    f"P2P_STRUCTURE_RETIREMENT_TARGET_RETIRED: {target.identity}"
                )
            if not matches:
                raise ValueError(
                    f"P2P_STRUCTURE_RETIREMENT_TARGET_UNKNOWN: {target.identity}"
                )
            if len(matches) > 1:
                raise ValueError(
                    "P2P_STRUCTURE_RETIREMENT_TARGET_AMBIGUOUS: field target requires section_id"
                )
            match = matches[0]
            return StructureRetirementTarget(
                kind="field",
                element_id=match.field_id,
                section_id=match.section_id,
            )
        attribute_by_kind = {
            "question": "question_id",
            "criterion": "criterion_id",
            "artifact": "artifact_id",
        }
        collection_by_kind = {
            "question": structure.questions,
            "criterion": structure.criteria,
            "artifact": structure.artifacts,
        }
        attribute = attribute_by_kind[target.kind]
        collection = collection_by_kind[target.kind]
        active = {
            str(getattr(item, attribute))
            for item in collection
            if getattr(item, "lifecycle") == "active"
        }
        all_ids = {str(getattr(item, attribute)) for item in collection}
        return _resolve_simple_target(target, active=active, all_ids=all_ids)

    def _structural_impacts(
        self,
        structure: ProjectStructure,
        *,
        targets: Sequence[StructureRetirementTarget],
        retiring_sections: set[str],
        direct_artifacts: set[str],
    ) -> tuple[StructureRetirementImpact, ...]:
        impacts: list[StructureRetirementImpact] = []
        direct_fields = {
            (item.section_id, item.element_id) for item in targets if item.kind == "field"
        }
        direct_questions = {item.element_id for item in targets if item.kind == "question"}
        direct_criteria = {item.element_id for item in targets if item.kind == "criterion"}
        for section in structure.sections:
            if section.section_id in retiring_sections:
                impacts.append(
                    _impact(
                        impact_id=f"structure_section:{section.section_id}",
                        object_type="structure_section",
                        object_id=section.section_id,
                        lifecycle=section.lifecycle,
                        state="will_retire",
                        section_ids=(section.section_id,),
                        retiring_section_ids=(section.section_id,),
                    )
                )
        for field in structure.fields:
            direct = (field.section_id, field.field_id) in direct_fields
            inherited = field.section_id in retiring_sections
            if direct or inherited:
                impacts.append(
                    _impact(
                        impact_id=f"structure_field:{field.section_id}/{field.field_id}",
                        object_type="structure_field",
                        object_id=field.field_id,
                        lifecycle=field.lifecycle,
                        state="will_retire" if direct else "will_retire_with_parent",
                        section_ids=(field.section_id,),
                        retiring_section_ids=(field.section_id,) if inherited else (),
                    )
                )
        for question in structure.questions:
            direct = question.question_id in direct_questions
            inherited = question.section_id in retiring_sections
            if direct or inherited:
                impacts.append(
                    _impact(
                        impact_id=f"structure_question:{question.question_id}",
                        object_type="structure_question",
                        object_id=question.question_id,
                        lifecycle=question.lifecycle,
                        state="will_retire" if direct else "will_retire_with_parent",
                        section_ids=(question.section_id,),
                        retiring_section_ids=(question.section_id,) if inherited else (),
                    )
                )
        for criterion in structure.criteria:
            direct = criterion.criterion_id in direct_criteria
            inherited = criterion.section_id in retiring_sections
            if direct or inherited:
                impacts.append(
                    _impact(
                        impact_id=f"structure_criterion:{criterion.criterion_id}",
                        object_type="structure_criterion",
                        object_id=criterion.criterion_id,
                        lifecycle=criterion.lifecycle,
                        state="will_retire" if direct else "will_retire_with_parent",
                        section_ids=(criterion.section_id,),
                        retiring_section_ids=(criterion.section_id,) if inherited else (),
                    )
                )
        for artifact in structure.artifacts:
            direct = artifact.artifact_id in direct_artifacts
            affected = tuple(sorted(set(artifact.section_ids) & retiring_sections))
            if direct:
                impacts.append(
                    _impact(
                        impact_id=f"structure_artifact:{artifact.artifact_id}",
                        object_type="structure_artifact",
                        object_id=artifact.artifact_id,
                        lifecycle=artifact.lifecycle,
                        state="will_retire",
                        section_ids=artifact.section_ids,
                        retiring_section_ids=affected,
                    )
                )
            elif affected and artifact.lifecycle == "active":
                allowed = (
                    ("retire",)
                    if set(artifact.section_ids) <= retiring_sections
                    else ("remove_sections", "retire")
                )
                impacts.append(
                    _impact(
                        impact_id=f"structure_artifact:{artifact.artifact_id}",
                        object_type="structure_artifact",
                        object_id=artifact.artifact_id,
                        lifecycle=artifact.lifecycle,
                        state="requires_resolution",
                        section_ids=artifact.section_ids,
                        retiring_section_ids=affected,
                        required_disposition=True,
                        allowed_actions=allowed,
                        default_action=allowed[0],
                        message="Artifact references a section being retired.",
                    )
                )
        return tuple(impacts)

    def _memory_impacts(
        self,
        *,
        retiring_sections: set[str],
        direct_fields: set[tuple[str | None, str]],
        direct_artifacts: set[str],
        reference_items: Sequence[_ReferenceItem],
        questions_artifact: ProjectQuestionArtifact | None,
    ) -> tuple[StructureRetirementImpact, ...]:
        del direct_artifacts
        impacts: list[StructureRetirementImpact] = []
        for item in reference_items:
            object_type = item.object_type
            object_id = item.object_id
            section_ids = item.section_ids
            affected = tuple(sorted(set(section_ids) & retiring_sections))
            if object_type == "proposal" and affected:
                lifecycle = item.lifecycle
                if item.active and lifecycle in _ACTIVE_PROPOSAL_STATES:
                    actions = (
                        ("reassign_sections", "project_global")
                        if lifecycle in _AUTHORITY_CREATING_PROPOSAL_STATES
                        else ("reassign_sections", "project_global", "unassigned")
                    )
                    impacts.append(
                        _impact(
                            impact_id=f"proposal:{object_id}:scope",
                            object_type="proposal",
                            object_id=object_id,
                            path=item.path,
                            lifecycle=lifecycle,
                            state="requires_resolution",
                            section_ids=section_ids,
                            retiring_section_ids=affected,
                            required_disposition=True,
                            allowed_actions=actions,
                            default_action=actions[0],
                            message="Active proposal scope references a section being retired.",
                        )
                    )
                else:
                    impacts.append(
                        _impact(
                            impact_id=f"proposal:{object_id}:scope",
                            object_type="proposal",
                            object_id=object_id,
                            path=item.path,
                            lifecycle=lifecycle,
                            state="historical_reference",
                            active=False,
                            section_ids=section_ids,
                            retiring_section_ids=affected,
                            message="Historical proposal reference is preserved.",
                        )
                    )
                continue
            if object_type == "formal_question":
                question = (
                    _question_by_id(questions_artifact, object_id)
                    if questions_artifact is not None
                    else None
                )
                field_affected = (
                    question is not None
                    and question.target.kind == "field"
                    and (question.section_id, question.target.target_id) in direct_fields
                )
                if not affected and not field_affected:
                    continue
                lifecycle = item.lifecycle
                if (
                    question is not None
                    and question.state in _ACTIVE_QUESTION_STATES
                    and question.applicability
                    in {
                        ProjectQuestionApplicability.ACTIVE,
                        ProjectQuestionApplicability.RECONCILIATION_REQUIRED,
                    }
                ):
                    impacts.append(
                        _impact(
                            impact_id=f"formal_question:{object_id}",
                            object_type="formal_question",
                            object_id=object_id,
                            path=PROJECT_QUESTIONS_PATH.as_posix(),
                            lifecycle=lifecycle,
                            state="requires_resolution",
                            section_ids=section_ids,
                            retiring_section_ids=affected,
                            required_disposition=True,
                            allowed_actions=("retire",),
                            default_action="retire",
                            message="Active formal question targets structure being retired.",
                        )
                    )
                else:
                    impacts.append(
                        _impact(
                            impact_id=f"formal_question:{object_id}",
                            object_type="formal_question",
                            object_id=object_id,
                            path=PROJECT_QUESTIONS_PATH.as_posix(),
                            lifecycle=lifecycle,
                            state="historical_reference",
                            active=False,
                            section_ids=section_ids,
                            retiring_section_ids=affected,
                            message="Historical formal question reference is preserved.",
                        )
                    )
        return tuple(impacts)

    def _reference_index(
        self,
        *,
        structure: ProjectStructure,
        records_by_path: Mapping[str, bytes],
    ) -> tuple[tuple[_ReferenceItem, ...], ProjectQuestionArtifact | None, tuple[str, ...]]:
        items: list[_ReferenceItem] = []
        blockers: list[str] = []
        all_sections = {item.section_id for item in structure.sections}
        active_sections = set(structure.active_section_ids())
        proposal_scope_paths = [
            path
            for path in sorted(records_by_path)
            if path.startswith(".p2p/proposals/")
            and path.endswith("/memory-scope.yml")
        ]
        for scope_path in proposal_scope_paths:
            proposal_id = _proposal_id_from_scope_path(scope_path)
            events_path = scope_path.rsplit("/", 1)[0] + "/memory-scope-events.yml"
            try:
                events_content = records_by_path[events_path]
                scope, _events = validated_scope_pair_from_bytes(
                    records_by_path[scope_path],
                    events_content,
                    expected_proposal_id=proposal_id,
                )
                lifecycle = self.memory_service.proposal_lifecycle(proposal_id)
                state = str(
                    getattr(
                        getattr(lifecycle, "effective_state", "unknown"),
                        "value",
                        getattr(lifecycle, "effective_state", "unknown"),
                    )
                )
                active = state in _ACTIVE_PROPOSAL_STATES
                section_ids = (
                    scope.section_ids
                    if scope.kind == ProjectMemoryScopeKind.sections
                    else ()
                )
                if active and section_ids and set(section_ids) - active_sections:
                    blockers.append("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE")
                if set(section_ids) - all_sections:
                    blockers.append("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE")
                items.append(
                    _ReferenceItem(
                        object_type="proposal",
                        object_id=proposal_id,
                        lifecycle=state,
                        active=active,
                        section_ids=section_ids,
                        path=scope_path,
                        scope_kind=scope.kind.value,
                    )
                )
            except (KeyError, ValueError):
                blockers.append("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE")
        questions_artifact: ProjectQuestionArtifact | None = None
        try:
            questions_artifact = self._questions_from_records(records_by_path)
        except ValueError:
            blockers.append("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE")
        if questions_artifact is not None:
            for question in questions_artifact.questions:
                active = (
                    question.state in _ACTIVE_QUESTION_STATES
                    and question.applicability
                    in {
                        ProjectQuestionApplicability.ACTIVE,
                        ProjectQuestionApplicability.RECONCILIATION_REQUIRED,
                    }
                )
                if question.section_id not in all_sections:
                    blockers.append("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE")
                if active and question.section_id not in active_sections:
                    blockers.append("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE")
                items.append(
                    _ReferenceItem(
                        object_type="formal_question",
                        object_id=question.question_id,
                        lifecycle=question.state.value,
                        active=active,
                        section_ids=(question.section_id,),
                        path=PROJECT_QUESTIONS_PATH.as_posix(),
                    )
                )
        return tuple(items), questions_artifact, tuple(sorted(set(blockers)))

    def _disposition_blockers(
        self,
        *,
        required: Sequence[StructureRetirementImpact],
        plan: StructureRetirementPlan,
        structure: ProjectStructure,
        retiring_sections: set[str],
    ) -> list[str]:
        blockers: list[str] = []
        required_ids = {item.impact_id for item in required if item.required_disposition}
        planned_ids = set(plan.by_id)
        missing = sorted(required_ids - planned_ids)
        extra = sorted(planned_ids - required_ids)
        if missing:
            blockers.append("P2P_STRUCTURE_RETIREMENT_DISPOSITION_REQUIRED")
        if extra:
            blockers.append("P2P_STRUCTURE_RETIREMENT_DISPOSITION_UNKNOWN")
        by_required = {item.impact_id: item for item in required if item.required_disposition}
        active_sections = set(structure.active_section_ids()) - retiring_sections
        for disposition_id in sorted(planned_ids & required_ids):
            disposition = plan.by_id[disposition_id]
            impact = by_required[disposition_id]
            if disposition.action not in impact.allowed_actions:
                blockers.append("P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID")
                continue
            if disposition.action == "reassign_sections":
                invalid = sorted(set(disposition.section_ids) - active_sections)
                if invalid:
                    blockers.append("P2P_STRUCTURE_RETIREMENT_DISPOSITION_INVALID")
        return blockers

    def _candidate_structure(
        self,
        structure: ProjectStructure,
        *,
        targets: Sequence[StructureRetirementTarget],
        plan: StructureRetirementPlan,
        retiring_sections: set[str],
    ) -> ProjectStructure:
        direct_fields = {
            (item.section_id, item.element_id) for item in targets if item.kind == "field"
        }
        direct_questions = {item.element_id for item in targets if item.kind == "question"}
        direct_criteria = {item.element_id for item in targets if item.kind == "criterion"}
        direct_artifacts = {item.element_id for item in targets if item.kind == "artifact"}
        order = 0
        sections = []
        for section in structure.sections:
            if section.section_id in retiring_sections:
                sections.append(replace(section, lifecycle="retired"))
                continue
            if section.lifecycle == "active":
                sections.append(replace(section, order=order))
                order += 1
            else:
                sections.append(section)
        fields = tuple(
            replace(field, lifecycle="retired")
            if field.section_id in retiring_sections
            or (field.section_id, field.field_id) in direct_fields
            else field
            for field in structure.fields
        )
        questions = tuple(
            replace(question, lifecycle="retired")
            if question.section_id in retiring_sections
            or question.question_id in direct_questions
            else question
            for question in structure.questions
        )
        criteria = tuple(
            replace(criterion, lifecycle="retired")
            if criterion.section_id in retiring_sections
            or criterion.criterion_id in direct_criteria
            else criterion
            for criterion in structure.criteria
        )
        artifacts: list[StructureArtifact] = []
        for artifact in structure.artifacts:
            disposition = plan.by_id.get(f"structure_artifact:{artifact.artifact_id}")
            if artifact.artifact_id in direct_artifacts or (
                disposition is not None and disposition.action == "retire"
            ):
                artifacts.append(replace(artifact, lifecycle="retired"))
            elif disposition is not None and disposition.action == "remove_sections":
                artifacts.append(
                    replace(
                        artifact,
                        section_ids=tuple(
                            section_id
                            for section_id in artifact.section_ids
                            if section_id not in retiring_sections
                        ),
                    )
                )
            else:
                artifacts.append(artifact)
        return replace(
            structure,
            sections=tuple(sections),
            fields=fields,
            questions=questions,
            criteria=criteria,
            artifacts=tuple(artifacts),
        )

    def _memory_candidates(
        self,
        *,
        plan: StructureRetirementPlan,
        required: Sequence[StructureRetirementImpact],
        candidate_structure: ProjectStructure,
        records_by_path: Mapping[str, bytes],
        evidence: AuthorityEvidence,
        timestamp: str,
        retiring_sections: set[str],
        direct_fields: set[tuple[str | None, str]],
    ) -> dict[str, bytes]:
        candidates: dict[str, bytes] = {}
        proposal_impacts = [
            item
            for item in required
            if item.required_disposition and item.object_type == "proposal"
        ]
        for impact in proposal_impacts:
            disposition = plan.by_id[impact.impact_id]
            proposal_id = impact.object_id
            scope_path = self._proposal_scope_path(proposal_id)
            events_path = scope_path.rsplit("/", 1)[0] + "/memory-scope-events.yml"
            previous, events = validated_scope_pair_from_bytes(
                records_by_path[scope_path],
                records_by_path[events_path],
                expected_proposal_id=proposal_id,
            )
            next_kind: ProjectMemoryScopeKind
            next_sections: tuple[str, ...]
            if disposition.action == "reassign_sections":
                next_kind = ProjectMemoryScopeKind.sections
                next_sections = disposition.section_ids
            elif disposition.action == "project_global":
                next_kind = ProjectMemoryScopeKind.project_global
                next_sections = ()
            else:
                next_kind = ProjectMemoryScopeKind.unassigned
                next_sections = ()
            next_scope = ProjectMemoryScope(
                object_type="proposal",
                object_id=proposal_id,
                revision=previous.revision + 1,
                kind=next_kind,
                section_ids=next_sections,
                structure_id=candidate_structure.structure_id,
                structure_revision=candidate_structure.revision,
                structure_checksum=candidate_structure.checksum,
                updated_at=timestamp,
                updated_by=evidence.subject.identity_id,
                authority=evidence.to_dict(),
            )
            if len(events) >= PROJECT_MEMORY_SCOPE_EVENT_LIMIT:
                raise ValueError("P2P_STRUCTURE_RETIREMENT_SCOPE_EVENT_LIMIT: event limit exceeded")
            event = ProjectMemoryScopeEvent(
                event_id=f"scope-event-{next_scope.revision:08d}",
                scope_revision=next_scope.revision,
                scope_sha256=next_scope.semantic_sha256,
                occurred_at=timestamp,
                subject_id=evidence.subject.identity_id,
                executor_id=evidence.executor.identity_id,
                authority=evidence.to_dict(),
                previous_kind=previous.kind.value,
                current_kind=next_scope.kind.value,
                section_ids=next_scope.section_ids,
            )
            candidates[scope_path] = scope_bytes(next_scope)
            candidates[events_path] = scope_events_bytes(
                proposal_id=proposal_id,
                events=(*events, event),
            )
        question_impacts = [
            item
            for item in required
            if item.required_disposition and item.object_type == "formal_question"
        ]
        if question_impacts:
            question_path = PROJECT_QUESTIONS_PATH.as_posix()
            artifact = self._questions_from_records(records_by_path)
            if artifact is None:
                raise ValueError("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE: project questions artifact is missing")
            required_ids = {item.object_id for item in question_impacts}
            updated_questions = tuple(
                self._retired_question(
                    question,
                    evidence=evidence,
                    timestamp=timestamp,
                    retiring_sections=retiring_sections,
                    direct_fields=direct_fields,
                )
                if question.question_id in required_ids
                else question
                for question in artifact.questions
            )
            candidate_artifact = replace(
                artifact,
                questions=updated_questions,
                updated_at=timestamp,
                updated_by=evidence.subject.identity_id,
            )
            candidates[question_path] = self.question_service.candidate_bytes(candidate_artifact)
        return candidates

    def _retired_question(
        self,
        question: ProjectQuestion,
        *,
        evidence: AuthorityEvidence,
        timestamp: str,
        retiring_sections: set[str],
        direct_fields: set[tuple[str | None, str]],
    ) -> ProjectQuestion:
        affected = question.section_id in retiring_sections or (
            question.target.kind == "field"
            and (question.section_id, question.target.target_id) in direct_fields
        )
        if not affected:
            return question
        transition = ProjectQuestionTransition(
            operation="retire_for_structure_retirement",
            from_state=question.state.value,
            to_state=ProjectQuestionState.RETIRED.value,
            actor=evidence.subject.identity_id,
            role="owner",
            reason="Retired because the referenced project structure target was retired.",
            at=timestamp,
            provenance={
                "retiring_section_ids": sorted(retiring_sections),
                "retiring_field_ids": [
                    f"{section_id}/{field_id}"
                    for section_id, field_id in sorted(direct_fields)
                ],
            },
        )
        return replace(
            question,
            revision=question.revision + 1,
            state=ProjectQuestionState.RETIRED,
            applicability=ProjectQuestionApplicability.TARGET_REMOVED,
            transitions=(*question.transitions, transition),
            updated_at=timestamp,
            updated_by=evidence.subject.identity_id,
        )

    def _source_preconditions(
        self,
        records_by_path: Mapping[str, bytes],
    ) -> tuple[SourcePrecondition, ...]:
        sources = {
            path: source_precondition(path, content)
            for path, content in records_by_path.items()
        }
        for relative in (PROJECT_STRUCTURE_PATH, PROJECT_STRUCTURE_EVENTS_PATH):
            sources[relative] = source_precondition(
                relative,
                (self.root / relative).read_bytes(),
            )
        sources[PROJECT_STRUCTURE_SNAPSHOTS_PATH] = source_precondition(
            PROJECT_STRUCTURE_SNAPSHOTS_PATH,
            self.snapshots.source_content(),
        )
        return tuple(sources[path] for path in sorted(sources))

    def _candidate_semantics(
        self,
        *,
        candidate_structure: ProjectStructure | None,
        event: ProjectStructureEvent | None,
        impacts: Sequence[StructureRetirementImpact],
        blockers: Sequence[str],
        applied_dispositions: Sequence[StructureRetirementDisposition],
    ) -> dict[str, object]:
        if candidate_structure is None or event is None:
            return {
                "blocked": sorted(set(blockers)),
                "impact_ids": [item.impact_id for item in impacts],
            }
        return {
            PROJECT_STRUCTURE_PATH: candidate_structure.to_storage_dict(),
            PROJECT_STRUCTURE_EVENTS_PATH: {
                "event_type": event.event_type,
                "revision": event.revision,
                "checksum": event.checksum,
                "targets": list(event.details.get("targets", ())),
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
        }

    def _validate_candidate_view(self, view: object, *, build: _Build) -> None:
        candidate = build.preview.candidate
        if candidate is None or build.event is None:
            raise ValueError("P2P_STRUCTURE_RETIREMENT_INVALID: missing candidate")
        structure = project_structure_from_bytes(
            view.read_bytes(PROJECT_STRUCTURE_PATH)  # type: ignore[attr-defined]
        )
        structure_id, events = project_structure_events_from_bytes(
            view.read_bytes(PROJECT_STRUCTURE_EVENTS_PATH)  # type: ignore[attr-defined]
        )
        if (
            structure_id != structure.structure_id
            or not events
            or events[-1].revision != structure.revision
            or events[-1].checksum != structure.checksum
            or structure.checksum != candidate.checksum
        ):
            raise ValueError("P2P_STRUCTURE_RETIREMENT_INVALID: candidate event ledger mismatch")
        proposal_ids = {
            impact.object_id
            for impact in build.preview.required_dispositions
            if impact.object_type == "proposal"
        }
        for proposal_id in proposal_ids:
            scope_path = self._proposal_scope_path(proposal_id)
            events_path = scope_path.rsplit("/", 1)[0] + "/memory-scope-events.yml"
            validated_scope_pair_from_bytes(
                view.read_bytes(scope_path),  # type: ignore[attr-defined]
                view.read_bytes(events_path),  # type: ignore[attr-defined]
                expected_proposal_id=proposal_id,
            )
        if any(
            impact.object_type == "formal_question"
            for impact in build.preview.required_dispositions
        ):
            self.question_service.parse_bytes(
                view.read_bytes(PROJECT_QUESTIONS_PATH.as_posix()),  # type: ignore[attr-defined]
                target=PROJECT_QUESTIONS_PATH.as_posix(),
            )

    def _proposal_scope_path(self, proposal_id: str) -> str:
        proposal_dir = self.memory_service.find_proposal_dir(proposal_id)
        return (proposal_dir / "memory-scope.yml").relative_to(self.root).as_posix()

    def _questions_from_records(
        self,
        records_by_path: Mapping[str, bytes],
    ) -> ProjectQuestionArtifact | None:
        content = records_by_path.get(PROJECT_QUESTIONS_PATH.as_posix())
        if content is None:
            return None
        return self.question_service.parse_bytes(
            content,
            target=PROJECT_QUESTIONS_PATH.as_posix(),
        )


def _targets_from_input(
    targets: Sequence[StructureRetirementTarget | Mapping[str, object]],
) -> tuple[StructureRetirementTarget, ...]:
    if not targets:
        raise ValueError("P2P_STRUCTURE_RETIREMENT_TARGET_REQUIRED: at least one target is required")
    from p2p_engine.core.project_structure_retirement import (
        structure_retirement_target_from_mapping,
    )

    return tuple(
        item
        if isinstance(item, StructureRetirementTarget)
        else structure_retirement_target_from_mapping(item)
        for item in targets
    )


def _plan_from_input(
    plan: StructureRetirementPlan | Mapping[str, object] | None,
) -> StructureRetirementPlan:
    if isinstance(plan, StructureRetirementPlan):
        return plan
    return structure_retirement_plan_from_mapping(plan)


def _request_payload(
    *,
    targets: Sequence[StructureRetirementTarget],
    plan: StructureRetirementPlan,
    expected_structure_revision: int,
    expected_memory_revision: str,
) -> dict[str, object]:
    return {
        "contract": STRUCTURE_RETIREMENT_PLAN_CONTRACT,
        "expected_structure_revision": expected_structure_revision,
        "expected_memory_revision": expected_memory_revision,
        "targets": [
            item.to_dict()
            for item in sorted(targets, key=lambda value: value.identity)
        ],
        "plan": _plan_payload(plan),
    }


def _plan_payload(plan: StructureRetirementPlan) -> dict[str, object]:
    return {
        "contract": plan.contract,
        "dispositions": [
            item.to_dict()
            for item in sorted(plan.dispositions, key=lambda value: value.disposition_id)
        ],
    }


def _resolve_simple_target(
    target: StructureRetirementTarget,
    *,
    active: set[str],
    all_ids: set[str],
) -> StructureRetirementTarget:
    if target.element_id in active:
        return target
    if target.element_id in all_ids:
        raise ValueError(
            f"P2P_STRUCTURE_RETIREMENT_TARGET_RETIRED: {target.identity}"
        )
    raise ValueError(f"P2P_STRUCTURE_RETIREMENT_TARGET_UNKNOWN: {target.identity}")


def _impact(
    *,
    impact_id: str,
    object_type: str,
    object_id: str,
    lifecycle: str,
    state: str,
    path: str = PROJECT_STRUCTURE_PATH,
    active: bool = True,
    section_ids: Sequence[str] = (),
    retiring_section_ids: Sequence[str] = (),
    required_disposition: bool = False,
    allowed_actions: Sequence[str] = (),
    default_action: str | None = None,
    message: str = "",
) -> StructureRetirementImpact:
    return StructureRetirementImpact(
        impact_id=impact_id,
        object_type=object_type,
        object_id=object_id,
        path=path,
        lifecycle=lifecycle,
        state=state,
        active=active,
        section_ids=tuple(section_ids),
        retiring_section_ids=tuple(retiring_section_ids),
        required_disposition=required_disposition,
        allowed_actions=tuple(allowed_actions),
        default_action=default_action,
        message=message,
    )


def _question_by_id(
    artifact: ProjectQuestionArtifact | None,
    question_id: str,
) -> ProjectQuestion | None:
    if artifact is None:
        return None
    return next(
        (item for item in artifact.questions if item.question_id == question_id),
        None,
    )


def _proposal_id_from_scope_path(scope_path: str) -> str:
    parts = scope_path.split("/")
    if len(parts) < 4 or parts[0:2] != [".p2p", "proposals"]:
        raise ValueError("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE: invalid proposal scope path")
    name = parts[2]
    proposal_parts = name.split("-", 2)
    if len(proposal_parts) < 2:
        raise ValueError("P2P_STRUCTURE_RETIREMENT_REFERENCE_INDEX_INCOMPLETE: invalid proposal directory")
    return f"{proposal_parts[0]}-{proposal_parts[1]}"


def _classification_projection(
    *,
    reference_items: Sequence[_ReferenceItem],
    required: Sequence[StructureRetirementImpact],
    plan: StructureRetirementPlan,
    blockers: Sequence[str],
) -> dict[str, object]:
    required_by_id = {
        item.impact_id: item
        for item in required
        if item.required_disposition
    }
    proposal_dispositions = {
        item.object_id: plan.by_id.get(item.impact_id)
        for item in required_by_id.values()
        if item.object_type == "proposal"
    }
    question_retire_ids = {
        item.object_id
        for item in required_by_id.values()
        if item.object_type == "formal_question"
        and (plan.by_id.get(item.impact_id) is not None)
        and plan.by_id[item.impact_id].action == "retire"
    }
    before = {
        "active_total": 0,
        "proposal_scopes_section": 0,
        "proposal_scopes_global": 0,
        "proposal_scopes_unassigned": 0,
        "formal_questions_active": 0,
    }
    after = dict(before)
    reassigned = 0
    made_global = 0
    made_unassigned = 0
    retired_questions = 0
    for item in reference_items:
        if not item.active:
            continue
        before["active_total"] += 1
        if item.object_type == "proposal":
            if item.scope_kind == ProjectMemoryScopeKind.sections.value:
                before["proposal_scopes_section"] += 1
            elif item.scope_kind == ProjectMemoryScopeKind.unassigned.value:
                before["proposal_scopes_unassigned"] += 1
            else:
                before["proposal_scopes_global"] += 1
            disposition = proposal_dispositions.get(item.object_id)
            if disposition is None:
                after["active_total"] += 1
                if item.scope_kind == ProjectMemoryScopeKind.sections.value:
                    after["proposal_scopes_section"] += 1
                elif item.scope_kind == ProjectMemoryScopeKind.unassigned.value:
                    after["proposal_scopes_unassigned"] += 1
                else:
                    after["proposal_scopes_global"] += 1
            elif disposition.action == "reassign_sections":
                after["active_total"] += 1
                after["proposal_scopes_section"] += 1
                reassigned += 1
            elif disposition.action == "project_global":
                after["active_total"] += 1
                after["proposal_scopes_global"] += 1
                made_global += 1
            elif disposition.action == "unassigned":
                after["active_total"] += 1
                after["proposal_scopes_unassigned"] += 1
                made_unassigned += 1
            continue
        if item.object_type == "formal_question":
            before["formal_questions_active"] += 1
            if item.object_id in question_retire_ids:
                retired_questions += 1
            else:
                after["active_total"] += 1
                after["formal_questions_active"] += 1
    return {
        "status": "blocked" if blockers else "projected",
        "before": before,
        "after": after if not blockers else None,
        "proposal_scopes_reassigned": reassigned,
        "proposal_scopes_global": made_global,
        "proposal_scopes_unassigned": made_unassigned,
        "formal_questions_retired": retired_questions,
    }


def _readiness_projection(
    *,
    structure: ProjectStructure,
    targets: Sequence[StructureRetirementTarget],
    retiring_sections: set[str],
    candidate_structure: ProjectStructure | None,
) -> dict[str, object]:
    active_before = [
        item
        for item in structure.criteria
        if item.lifecycle == "active" and item.enabled
    ]
    if candidate_structure is not None:
        active_after = [
            item
            for item in candidate_structure.criteria
            if item.lifecycle == "active" and item.enabled
        ]
    else:
        direct_criteria = {
            item.element_id for item in targets if item.kind == "criterion"
        }
        active_after = [
            item
            for item in active_before
            if item.criterion_id not in direct_criteria
            and item.section_id not in retiring_sections
        ]
    return {
        "status": "projected",
        "active_criteria_before": len(active_before),
        "active_criteria_after": len(active_after),
        "active_criteria_delta": len(active_after) - len(active_before),
        "score_projection": None,
        "score_projection_reason": "readiness scoring is rebased on project structure in the next migration step",
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
        raise ValueError("P2P_STRUCTURE_RETIREMENT_RECEIPT_INVALID: current summary must be a mapping")
    revision = value.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int):
        raise ValueError("P2P_STRUCTURE_RETIREMENT_RECEIPT_INVALID: revision is invalid")
    checksum = str(value.get("checksum") or "")
    _require_sha256(checksum, "checksum")
    return {
        "structure_id": str(value.get("structure_id") or ""),
        "revision": revision,
        "checksum": checksum,
    }


def _structure_event_from_mapping(value: object) -> ProjectStructureEvent:
    from p2p_engine.core.project_structure import project_structure_event_from_mapping

    return project_structure_event_from_mapping(value)


def _mapping_sequence(value: object) -> Sequence[object]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("P2P_STRUCTURE_RETIREMENT_RECEIPT_INVALID: expected a sequence")
    return value


def _require_sha256(value: object, field: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"P2P_STRUCTURE_RETIREMENT_INVALID: {field} must be SHA-256")
    return text

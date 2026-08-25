from __future__ import annotations

from dataclasses import replace
import hashlib
import re
from pathlib import Path
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING

from p2p_engine.core.authority import AuthorityContext, AuthorityEvidence
from p2p_engine.core.mutation_preview import MutationPreviewService, semantic_sha256, source_precondition
from p2p_engine.core.project_domain import StructureSource
from p2p_engine.core.project_structure import (
    PROJECT_STRUCTURE_CONTRACT,
    PROJECT_STRUCTURE_EVENTS_CONTRACT,
    PROJECT_STRUCTURE_EVENT_LIMIT,
    PROJECT_STRUCTURE_MUTATION_CONTRACT,
    PROJECT_STRUCTURE_PUBLIC_HISTORY_LIMIT,
    ProjectStructure,
    ProjectStructureEvent,
    ProjectStructureHistory,
    ProjectStructureMutationPlan,
    ProjectStructureMutationResult,
    StructureArtifact,
    StructureCriterion,
    StructureField,
    StructureOrigin,
    StructureQuestion,
    StructureSection,
    normalize_structure_id,
    project_structure_checksum,
    project_structure_event_from_mapping,
    project_structure_from_mapping,
    validate_project_structure,
    with_project_structure_checksum,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.mutation_receipts import MutationReceiptService, idempotency_key_sha256, validate_idempotency_key
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso

if TYPE_CHECKING:
    from p2p_engine.core.project_verticals import VerticalPack


PROJECT_STRUCTURE_PATH = ".p2p/project/structure.yml"
PROJECT_STRUCTURE_EVENTS_PATH = ".p2p/project/structure-events.yml"
PROJECT_STRUCTURE_OPERATION = "project_structure_change"
PROJECT_STRUCTURE_POLICY_VERSION = 1


class ProjectStructureService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.path = self.root / PROJECT_STRUCTURE_PATH
        self.events_path = self.root / PROJECT_STRUCTURE_EVENTS_PATH
        self.authority = authority or ProjectAuthorityService(root=self.root, p2p_dir=self.p2p_dir)
        self.receipts = receipts or MutationReceiptService(root=self.root, p2p_dir=self.p2p_dir)
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)
        self.clock = clock
        self.codec = AuthorityContractCodec()

    def show(self, *, include_retired: bool = False) -> ProjectStructure:
        # Keep the canonical aggregate checksum-valid. Public callers apply the
        # active/retired projection through ProjectStructure.to_dict().
        del include_retired
        return project_structure_from_bytes(self._read_file(self.path, "structure"))

    def history(self, *, limit: int = 20) -> ProjectStructureHistory:
        if isinstance(limit, bool) or limit < 1 or limit > PROJECT_STRUCTURE_PUBLIC_HISTORY_LIMIT:
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_INVALID: history limit must be between 1 and "
                f"{PROJECT_STRUCTURE_PUBLIC_HISTORY_LIMIT}"
            )
        structure_id, events = project_structure_events_from_bytes(
            self._read_file(self.events_path, "structure events")
        )
        total = len(events)
        returned = tuple(events[-limit:])
        return ProjectStructureHistory(
            structure_id=structure_id,
            events=returned,
            total=total,
            returned=len(returned),
            truncated=total > len(returned),
        )

    def validate(self) -> tuple[str, ...]:
        structure = project_structure_from_bytes(self._read_file(self.path, "structure"))
        structure_id, events = project_structure_events_from_bytes(
            self._read_file(self.events_path, "structure events")
        )
        findings: list[str] = []
        if structure_id != structure.structure_id:
            findings.append("event ledger structure_id does not match canonical structure")
        if not events:
            findings.append("event ledger has no initialization evidence")
        else:
            revisions = [item.revision for item in events]
            if revisions != sorted(revisions) or len(revisions) != len(set(revisions)):
                findings.append("event revisions are not unique and monotonic")
            last = events[-1]
            if last.revision != structure.revision or last.checksum != structure.checksum:
                findings.append("event ledger head does not match canonical structure")
        return tuple(findings)

    def plan(
        self,
        *,
        operation: str,
        operation_key: str,
        expected_revision: int,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        request: Mapping[str, object],
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
    ) -> ProjectStructureMutationPlan:
        validate_idempotency_key(operation_key)
        if operation not in {"add_section", "update_metadata", "reorder_sections"}:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: unsupported simple structure operation")
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=("project.structure.edit",),
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        previous = self.show(include_retired=True)
        if expected_revision != previous.revision:
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_STALE_REVISION: expected revision "
                f"{expected_revision}, current revision is {previous.revision}"
            )
        normalized_request, candidate, event_type, details = self._mutate(
            previous,
            operation=operation,
            request=request,
        )
        candidate = with_project_structure_checksum(
            replace(candidate, revision=previous.revision + 1)
        )
        if candidate.checksum == previous.checksum:
            raise ValueError("P2P_PROJECT_STRUCTURE_NO_CHANGE: mutation has no semantic effect")
        event = ProjectStructureEvent(
            event_id=f"structure-event-{candidate.revision:08d}",
            event_type=event_type,
            revision=candidate.revision,
            checksum=candidate.checksum,
            occurred_at=self.clock(),
            subject_id=evidence.subject.identity_id,
            executor_id=evidence.executor.identity_id,
            authority=evidence.to_dict(),
            details=details,
        )
        ledger_structure_id, current_events = project_structure_events_from_bytes(
            self._read_file(self.events_path, "structure events")
        )
        if ledger_structure_id != previous.structure_id:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: event ledger identity mismatch")
        if len(current_events) >= PROJECT_STRUCTURE_EVENT_LIMIT:
            raise ValueError("P2P_PROJECT_STRUCTURE_LIMIT_EXCEEDED: event limit exceeded")
        structure_bytes = project_structure_bytes(candidate)
        event_bytes = project_structure_events_bytes(
            structure_id=candidate.structure_id,
            events=(*current_events, event),
        )
        receipt_path = self.receipts.relative_path(operation_key)
        candidates = {
            PROJECT_STRUCTURE_PATH: structure_bytes,
            PROJECT_STRUCTURE_EVENTS_PATH: event_bytes,
        }
        request_fingerprint = semantic_sha256(
            {
                "policy_version": PROJECT_STRUCTURE_POLICY_VERSION,
                "operation": operation,
                "operation_key_sha256": idempotency_key_sha256(operation_key),
                "expected_revision": expected_revision,
                "request": normalized_request,
                "authority_context_sha256": context.digest_sha256,
            }
        )
        sources = (
            source_precondition(PROJECT_STRUCTURE_PATH, self.path.read_bytes()),
            source_precondition(PROJECT_STRUCTURE_EVENTS_PATH, self.events_path.read_bytes()),
            source_precondition(receipt_path, None),
        )
        preview = MutationPreviewService.build(
            operation_id=f"project-structure-{operation.replace('_', '-')}",
            targets=(*sorted(candidates), receipt_path),
            actor=evidence.executor.identity_id,
            authority="root_authority",
            sources=sources,
            candidate_semantics={
                PROJECT_STRUCTURE_PATH: candidate.to_storage_dict(),
                PROJECT_STRUCTURE_EVENTS_PATH: {
                    "structure_id": candidate.structure_id,
                    "event": event.to_dict(),
                },
            },
            semantic_diff={
                "operation": operation,
                "request": normalized_request,
                "revision_before": previous.revision,
                "revision_after": candidate.revision,
                "checksum_before": previous.checksum,
                "checksum_after": candidate.checksum,
            },
            token_context={
                "request_fingerprint_sha256": request_fingerprint,
                "authority_context_sha256": context.digest_sha256,
                "operation_key_sha256": idempotency_key_sha256(operation_key),
            },
            policy_version=PROJECT_STRUCTURE_POLICY_VERSION,
        )
        return ProjectStructureMutationPlan(
            operation=operation,
            request=normalized_request,
            previous=previous,
            next=candidate,
            event=event,
            operation_key_sha256=idempotency_key_sha256(operation_key),
            request_fingerprint_sha256=request_fingerprint,
            preview_token=preview.preview_token,
            source_preconditions=preview.source_preconditions,
            candidate_bytes=candidates,
            authority=evidence,
        )

    def apply(
        self,
        *,
        operation: str,
        operation_key: str,
        expected_revision: int,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        request: Mapping[str, object],
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
    ) -> ProjectStructureMutationResult:
        replay = self._exact_replay(
            operation=operation,
            operation_key=operation_key,
            expected_revision=expected_revision,
            actor_id=actor_id,
            executor_id=executor_id,
            request=request,
            authority_context=authority_context,
            channel=channel,
            consent_id=consent_id,
        )
        if replay is not None:
            return replay
        plan = self.plan(
            operation=operation,
            operation_key=operation_key,
            expected_revision=expected_revision,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            request=request,
            authority_context=authority_context,
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        evidence = plan.authority
        if not isinstance(evidence, AuthorityEvidence):
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: structure plan lost authority evidence")
        summary = {
            "contract": PROJECT_STRUCTURE_MUTATION_CONTRACT,
            "operation": PROJECT_STRUCTURE_OPERATION,
            "operation_id": f"project.structure.{operation}",
            "requested_operation": operation,
            "request": dict(plan.request),
            "expected_revision": expected_revision,
            "previous_revision": plan.previous.revision,
            "previous_checksum": plan.previous.checksum,
            "current": _structure_receipt_summary(plan.next),
            "event": plan.event.to_dict(),
            "changed_paths": sorted(plan.candidate_bytes),
        }
        receipt_path, receipt_content, _ = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=PROJECT_STRUCTURE_OPERATION,
            actor=evidence.executor.identity_id,
            request_fingerprint_sha256=plan.request_fingerprint_sha256,
            preview_token=plan.preview_token,
            result=summary,
            candidates=plan.candidate_bytes,
            authority=evidence,
        )
        mutation = self.atomic_writer.apply(
            operation_id=f"project-structure-{operation.replace('_', '-')}",
            candidates={**plan.candidate_bytes, receipt_path: receipt_content},
            sources=plan.source_preconditions,
            preview_token=plan.preview_token,
            actor=evidence.executor.identity_id,
            candidate_validator=lambda view: _validate_candidate_view(view),
        )
        if mutation.status != "applied":
            replay = self._exact_replay(
                operation=operation,
                operation_key=operation_key,
                expected_revision=expected_revision,
                actor_id=actor_id,
                executor_id=executor_id,
                request=request,
                authority_context=authority_context,
                channel=channel,
                consent_id=consent_id,
            )
            if replay is not None:
                return replay
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_MUTATION_FAILED: " + (mutation.message or mutation.status)
            )
        return ProjectStructureMutationResult(
            status="applied",
            operation=operation,
            previous=plan.previous,
            current=plan.next,
            event=plan.event,
            actor=evidence.executor.identity_id,
            changed_paths=tuple(sorted(plan.candidate_bytes)),
            message="Project-owned structure changed atomically.",
        )

    def _exact_replay(
        self,
        *,
        operation: str,
        operation_key: str,
        expected_revision: int,
        actor_id: str,
        executor_id: str,
        request: Mapping[str, object],
        authority_context: AuthorityContext | None,
        channel: str,
        consent_id: str | None,
    ) -> ProjectStructureMutationResult | None:
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is None:
            return None
        if receipt.operation != PROJECT_STRUCTURE_OPERATION or receipt.authority is None:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation")
        result = receipt.result
        replay_request = dict(request)
        if operation == "add_section":
            replay_section = StructureSection(
                section_id=str(
                    replay_request.get("section_id")
                    or _slug(str(replay_request.get("title") or ""))
                ),
                title=str(replay_request.get("title") or ""),
                description=str(replay_request.get("description") or ""),
                required=_required_bool(replay_request.get("required", True), "required"),
                order=0,
            )
            replay_request = {
                "section_id": replay_section.section_id,
                "title": replay_section.title,
                "description": replay_section.description,
                "required": replay_section.required,
            }
        if (
            result.get("requested_operation") != operation
            or result.get("expected_revision") != expected_revision
            or result.get("request") != replay_request
        ):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key is bound to another structure request")
        evidence = self.codec.evidence_from_mapping(receipt.authority)
        if (
            evidence.subject.identity_id != actor_id
            or evidence.executor.identity_id != executor_id
            or evidence.channel != channel
            or evidence.consent_id != consent_id
        ):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: structure mutation authority differs")
        if authority_context is not None and authority_context.digest_sha256 != evidence.authority_context_sha256:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: authority context differs")
        current_summary = _structure_summary_from_mapping(result.get("current"))
        current = self.show(include_retired=True)
        if (
            current.structure_id != current_summary["structure_id"]
            or current.revision != current_summary["revision"]
            or current.checksum != current_summary["checksum"]
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: current structure differs from receipt"
            )
        event = project_structure_event_from_mapping(result.get("event"))
        previous = replace(
            current,
            revision=int(result.get("previous_revision") or 0),
            checksum=str(result.get("previous_checksum") or ""),
        )
        return ProjectStructureMutationResult(
            status="already_applied",
            operation=operation,
            previous=previous,
            current=current,
            event=event,
            actor=evidence.executor.identity_id,
            changed_paths=tuple(str(item) for item in result.get("changed_paths", ())),
            message="Project structure mutation was already applied with this operation key.",
        )

    def _mutate(
        self,
        structure: ProjectStructure,
        *,
        operation: str,
        request: Mapping[str, object],
    ) -> tuple[dict[str, object], ProjectStructure, str, dict[str, object]]:
        if operation == "add_section":
            return self._add_section(structure, request)
        if operation == "update_metadata":
            return self._update_metadata(structure, request)
        return self._reorder_sections(structure, request)

    def _add_section(
        self,
        structure: ProjectStructure,
        request: Mapping[str, object],
    ) -> tuple[dict[str, object], ProjectStructure, str, dict[str, object]]:
        allowed = {"section_id", "title", "description", "required"}
        _reject_unknown(request, allowed)
        title = str(request.get("title") or "").strip()
        section_id = str(request.get("section_id") or _slug(title))
        section = StructureSection(
            section_id=section_id,
            title=title,
            description=str(request.get("description") or ""),
            required=_required_bool(request.get("required", True), "required"),
            order=len(structure.active_section_ids()),
        )
        if any(item.section_id == section.section_id for item in structure.sections):
            raise ValueError(
                f"P2P_PROJECT_STRUCTURE_ID_CONFLICT: section `{section.section_id}` already exists or was retired"
            )
        normalized = {
            "section_id": section.section_id,
            "title": section.title,
            "description": section.description,
            "required": section.required,
        }
        return (
            normalized,
            replace(structure, sections=(*structure.sections, section)),
            "section_added",
            {"section_id": section.section_id},
        )

    def _update_metadata(
        self,
        structure: ProjectStructure,
        request: Mapping[str, object],
    ) -> tuple[dict[str, object], ProjectStructure, str, dict[str, object]]:
        allowed = {"element_kind", "element_id", "section_id", "title", "description", "required", "enabled", "priority", "keywords"}
        _reject_unknown(request, allowed)
        kind = str(request.get("element_kind") or "").strip().lower()
        element_id = normalize_structure_id(request.get("element_id"), field_name="element_id")
        section_id = (
            normalize_structure_id(request.get("section_id"), field_name="section_id")
            if request.get("section_id") is not None
            else None
        )
        if section_id is not None and kind != "field":
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: section_id only disambiguates fields")
        updates = {key: value for key, value in request.items() if key not in {"element_kind", "element_id", "section_id"}}
        if not updates:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: metadata update is empty")
        attribute_map = {
            "section": ("sections", "section_id", {"title", "description", "required"}),
            "field": ("fields", "field_id", {"title", "description", "required"}),
            "question": ("questions", "question_id", {"title", "description", "priority"}),
            "criterion": ("criteria", "criterion_id", {"title", "required", "enabled", "keywords"}),
            "artifact": ("artifacts", "artifact_id", {"title", "required"}),
        }
        if kind not in attribute_map:
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: element_kind is unsupported")
        collection_name, id_name, allowed_updates = attribute_map[kind]
        unknown_updates = sorted(set(updates) - allowed_updates)
        if unknown_updates:
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_INVALID: unsupported metadata fields: "
                + ", ".join(unknown_updates)
            )
        items = list(getattr(structure, collection_name))
        matches = [
            i
            for i, item in enumerate(items)
            if getattr(item, id_name) == element_id
            and (section_id is None or getattr(item, "section_id", None) == section_id)
        ]
        if not matches:
            raise ValueError(f"P2P_PROJECT_STRUCTURE_UNKNOWN_ELEMENT: {kind} `{element_id}`")
        if len(matches) > 1:
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_AMBIGUOUS_ELEMENT: field ID requires section_id"
            )
        index = matches[0]
        current = items[index]
        replacements: dict[str, object] = {}
        for key, value in updates.items():
            actual = key
            if kind == "field" and key == "title":
                actual = "label"
            elif kind == "question" and key == "title":
                actual = "prompt"
            elif kind == "question" and key == "description":
                actual = "rationale"
            if actual in {"required", "enabled"}:
                value = _required_bool(value, key)
            if actual == "keywords":
                if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
                    raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: keywords must be a list")
                value = tuple(str(item) for item in value)
            replacements[actual] = value
        items[index] = replace(current, **replacements)
        candidate = replace(structure, **{collection_name: tuple(items)})
        normalized = {"element_kind": kind, "element_id": element_id, **updates}
        if section_id is not None:
            normalized["section_id"] = section_id
        return normalized, candidate, "metadata_updated", {"element_kind": kind, "element_id": element_id, "fields": sorted(updates)}

    def _reorder_sections(
        self,
        structure: ProjectStructure,
        request: Mapping[str, object],
    ) -> tuple[dict[str, object], ProjectStructure, str, dict[str, object]]:
        _reject_unknown(request, {"section_ids"})
        raw = request.get("section_ids")
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: section_ids must be a list")
        section_ids = tuple(normalize_structure_id(item, field_name="section_id") for item in raw)
        active_ids = structure.active_section_ids()
        if len(section_ids) != len(set(section_ids)) or set(section_ids) != set(active_ids):
            raise ValueError(
                "P2P_PROJECT_STRUCTURE_REORDER_INVALID: reorder must contain every active section exactly once"
            )
        order = {section_id: index for index, section_id in enumerate(section_ids)}
        sections = tuple(
            replace(item, order=order[item.section_id]) if item.lifecycle == "active" else item
            for item in structure.sections
        )
        sections = tuple(sorted(sections, key=lambda item: (item.lifecycle != "active", item.order, item.section_id)))
        normalized = {"section_ids": list(section_ids)}
        return normalized, replace(structure, sections=sections), "sections_reordered", normalized

    @staticmethod
    def _read_file(path: Path, label: str) -> bytes:
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"{label} is missing or unsafe")
            return path.read_bytes()
        except OSError as exc:
            raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: cannot read {label}: {exc}") from exc


def project_structure_from_vertical_pack(
    *,
    project_id: str,
    pack: "VerticalPack | None",
    source: StructureSource,
    origin: Mapping[str, object],
    actor: str,
    applied_at: str,
    rubric_enabled: Mapping[str, bool] | None = None,
) -> ProjectStructure:
    structure_id = _derived_id(f"{project_id}-structure")
    normalized_origin = StructureOrigin(
        kind=str(origin.get("kind") or source.kind),
        identity=str(origin.get("identity") or source.starter_id or source.coordinate or "empty"),
        checksum=origin.get("checksum"),  # type: ignore[arg-type]
        external_ref=origin.get("external_ref"),  # type: ignore[arg-type]
        applied_at=applied_at,
        applied_by=actor,
    )
    if pack is None:
        empty = ProjectStructure(
            structure_id=structure_id,
            revision=1,
            checksum="0" * 64,
            origin=normalized_origin,
        )
        return with_project_structure_checksum(empty)
    sections = tuple(
        StructureSection(
            section_id=item.section_id,
            title=item.title,
            description=item.purpose,
            required=item.required,
            order=index,
        )
        for index, item in enumerate(sorted(pack.sections, key=lambda value: (value.priority, value.section_id)))
    )
    fields: list[StructureField] = []
    for section in sorted(pack.sections, key=lambda value: (value.priority, value.section_id)):
        section_fields = section.fields or ()
        if not section_fields:
            question = next(
                (item for item in pack.questions if item.section_id == section.section_id),
                None,
            )
            fields.append(
                StructureField(
                    field_id="summary",
                    section_id=section.section_id,
                    label=section.title,
                    description=question.question if question else "",
                    required=section.required,
                    order=0,
                )
            )
            continue
        for index, item in enumerate(section_fields):
            fields.append(
                StructureField(
                    field_id=item.field_id,
                    section_id=section.section_id,
                    label=item.label,
                    description=item.question,
                    required=item.required,
                    order=index,
                )
            )
    questions = tuple(
        StructureQuestion(
            question_id=item.question_id,
            section_id=item.section_id,
            prompt=item.question,
            priority=item.priority,
            rationale=item.rationale,
            order=index,
        )
        for index, item in enumerate(pack.questions)
    )
    criteria = tuple(
        StructureCriterion(
            criterion_id=item.rubric_id,
            section_id=item.section_id,
            title=item.title,
            required=item.required,
            enabled=(rubric_enabled or {}).get(item.rubric_id, True),
            keywords=tuple(item.keywords),
            order=index,
        )
        for index, item in enumerate(pack.rubrics)
    )
    artifacts = tuple(
        StructureArtifact(
            artifact_id=item.artifact_id,
            title=item.title,
            section_ids=tuple(item.section_ids),
            required=item.required,
            order=index,
        )
        for index, item in enumerate(pack.artifacts)
    )
    candidate = ProjectStructure(
        structure_id=structure_id,
        revision=1,
        checksum="0" * 64,
        origin=normalized_origin,
        sections=sections,
        fields=tuple(fields),
        questions=questions,
        criteria=criteria,
        artifacts=artifacts,
    )
    return with_project_structure_checksum(candidate)


def initial_project_structure_event(
    structure: ProjectStructure,
    *,
    actor: str,
    occurred_at: str,
) -> ProjectStructureEvent:
    return ProjectStructureEvent(
        event_id="structure-event-00000001",
        event_type="initialized",
        revision=structure.revision,
        checksum=structure.checksum,
        occurred_at=occurred_at,
        subject_id=actor,
        executor_id=actor,
        details={"origin": structure.origin.to_dict()},
    )


def project_structure_bytes(structure: ProjectStructure) -> bytes:
    validate_project_structure(structure)
    return yaml_dump({"project_structure": structure.to_storage_dict()}).encode("ascii")


def project_structure_from_bytes(content: bytes) -> ProjectStructure:
    try:
        payload = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {exc}") from exc
    if not isinstance(payload, Mapping) or set(payload) != {"project_structure"}:
        raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: expected project_structure root")
    return project_structure_from_mapping(payload.get("project_structure"))


def project_structure_events_bytes(
    *,
    structure_id: str,
    events: Sequence[ProjectStructureEvent],
) -> bytes:
    if len(events) > PROJECT_STRUCTURE_EVENT_LIMIT:
        raise ValueError("P2P_PROJECT_STRUCTURE_LIMIT_EXCEEDED: event limit exceeded")
    return yaml_dump(
        {
            "project_structure_events": {
                "contract": PROJECT_STRUCTURE_EVENTS_CONTRACT,
                "structure_id": normalize_structure_id(structure_id, field_name="structure_id"),
                "events": [item.to_dict() for item in events],
            }
        }
    ).encode("ascii")


def project_structure_events_from_bytes(
    content: bytes,
) -> tuple[str, tuple[ProjectStructureEvent, ...]]:
    try:
        payload = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {exc}") from exc
    root = payload.get("project_structure_events") if isinstance(payload, Mapping) else None
    if not isinstance(root, Mapping):
        raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: expected project_structure_events root")
    unknown = sorted(set(root) - {"contract", "structure_id", "events"})
    if unknown or root.get("contract") != PROJECT_STRUCTURE_EVENTS_CONTRACT:
        raise ValueError("P2P_PROJECT_STRUCTURE_UNSUPPORTED: event contract is unsupported")
    raw_events = root.get("events")
    if isinstance(raw_events, (str, bytes)) or not isinstance(raw_events, Sequence):
        raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: events must be a list")
    if len(raw_events) > PROJECT_STRUCTURE_EVENT_LIMIT:
        raise ValueError("P2P_PROJECT_STRUCTURE_LIMIT_EXCEEDED: event limit exceeded")
    return (
        normalize_structure_id(root.get("structure_id"), field_name="structure_id"),
        tuple(project_structure_event_from_mapping(item) for item in raw_events),
    )


def _validate_candidate_view(view: object) -> None:
    structure = project_structure_from_bytes(view.read_bytes(PROJECT_STRUCTURE_PATH))  # type: ignore[attr-defined]
    structure_id, events = project_structure_events_from_bytes(
        view.read_bytes(PROJECT_STRUCTURE_EVENTS_PATH)  # type: ignore[attr-defined]
    )
    if structure_id != structure.structure_id or not events:
        raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: candidate event ledger mismatch")
    if events[-1].revision != structure.revision or events[-1].checksum != structure.checksum:
        raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: candidate event head mismatch")


def _reject_unknown(request: Mapping[str, object], allowed: set[str]) -> None:
    unknown = sorted(str(item) for item in set(request) - allowed)
    if unknown:
        raise ValueError(
            "P2P_PROJECT_STRUCTURE_INVALID: unsupported request fields: " + ", ".join(unknown)
        )


def _required_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"P2P_PROJECT_STRUCTURE_INVALID: {field_name} must be boolean")
    return value


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return _derived_id(slug)


def _derived_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.lower()).strip("-_")
    if not slug:
        raise ValueError("P2P_PROJECT_STRUCTURE_INVALID: derived ID is empty")
    if len(slug) > 64:
        suffix = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:12]
        slug = f"{slug[:50].rstrip('-_')}-{suffix}"
    return normalize_structure_id(slug, field_name="derived_id")


def _structure_receipt_summary(structure: ProjectStructure) -> dict[str, object]:
    return {
        "contract": PROJECT_STRUCTURE_CONTRACT,
        "structure_id": structure.structure_id,
        "revision": structure.revision,
        "checksum": structure.checksum,
    }


def _structure_summary_from_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != {
        "contract",
        "structure_id",
        "revision",
        "checksum",
    }:
        raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: invalid structure summary")
    if value.get("contract") != PROJECT_STRUCTURE_CONTRACT:
        raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: unsupported structure summary")
    structure_id = normalize_structure_id(value.get("structure_id"), field_name="structure_id")
    revision = value.get("revision")
    checksum = str(value.get("checksum") or "")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: invalid structure revision")
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: invalid structure checksum")
    return {"structure_id": structure_id, "revision": revision, "checksum": checksum}

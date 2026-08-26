from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from collections.abc import Callable, Mapping, Sequence

from p2p_engine.core.authority import AuthorityContext, AuthorityEvidence
from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    SourcePrecondition,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.project_memory import (
    MEMORY_CLASSIFICATION_ITEM_STATES,
    PROJECT_MEMORY_OBJECT_LIMIT,
    PROJECT_MEMORY_SCOPE_CONTRACT,
    PROJECT_MEMORY_SCOPE_EVENT_LIMIT,
    PROJECT_MEMORY_SCOPE_EVENTS_CONTRACT,
    PROJECT_MEMORY_SCOPE_MUTATION_CONTRACT,
    MemoryClassificationItem,
    MemoryClassificationSnapshot,
    ProjectMemoryScope,
    ProjectMemoryScopeEvent,
    ProjectMemoryScopeKind,
    ProjectMemoryScopeMutationResult,
    project_memory_scope_from_mapping,
)
from p2p_engine.core.project_questions import (
    ProjectQuestionApplicability,
    ProjectQuestionArtifact,
    ProjectQuestionState,
)
from p2p_engine.core.project_structure import ProjectStructure
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.project_structure import (
    PROJECT_STRUCTURE_PATH,
    project_structure_from_bytes,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso


PROJECT_MEMORY_SCOPE_OPERATION = "project_memory_scope_change"
PROJECT_MEMORY_SCOPE_POLICY_VERSION = 1
PROJECT_MEMORY_SOURCE_POLICY_VERSION = 1
_SCOPE_FILENAME = "memory-scope.yml"
_EVENTS_FILENAME = "memory-scope-events.yml"
_ACTIVE_PROPOSAL_STATES = frozenset(
    {"undecided", "deferred", "accepted", "accepted_with_changes"}
)
_ACTIVE_QUESTION_STATES = frozenset(
    {
        ProjectQuestionState.TO_ANSWER,
        ProjectQuestionState.ANSWERED,
        ProjectQuestionState.DEFERRED,
        ProjectQuestionState.MUTED,
    }
)


class ProjectMemoryService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
        project_structure: Callable[[], ProjectStructure],
        proposal_lifecycle: Callable[[str], object],
        project_questions: Callable[[], ProjectQuestionArtifact | None] | None = None,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.find_proposal_dir = find_proposal_dir
        self.project_structure = project_structure
        self.proposal_lifecycle = proposal_lifecycle
        self.project_questions = project_questions
        self.authority = authority or ProjectAuthorityService(root=self.root, p2p_dir=self.p2p_dir)
        self.receipts = receipts or MutationReceiptService(root=self.root, p2p_dir=self.p2p_dir)
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)
        self.clock = clock
        self.codec = AuthorityContractCodec()
        self._cached_identity: tuple[str, int, str, str] | None = None
        self._cached_snapshot: MemoryClassificationSnapshot | None = None

    def initial_scope_candidates(
        self,
        *,
        proposal_id: str,
        proposal_dir: Path,
        actor: str,
    ) -> dict[str, bytes]:
        structure = self.project_structure()
        scope = ProjectMemoryScope(
            object_type="proposal",
            object_id=proposal_id,
            revision=1,
            kind=ProjectMemoryScopeKind.unassigned,
            structure_id=structure.structure_id,
            structure_revision=structure.revision,
            structure_checksum=structure.checksum,
            updated_at=self.clock(),
            updated_by=actor,
        )
        event = ProjectMemoryScopeEvent(
            event_id="scope-event-00000001",
            scope_revision=1,
            scope_sha256=scope.semantic_sha256,
            occurred_at=scope.updated_at,
            subject_id=actor,
            executor_id=actor,
            authority={},
            previous_kind=None,
            current_kind=scope.kind.value,
            section_ids=(),
        )
        relative_dir = proposal_dir.relative_to(self.root).as_posix()
        return {
            f"{relative_dir}/{_SCOPE_FILENAME}": scope_bytes(scope),
            f"{relative_dir}/{_EVENTS_FILENAME}": scope_events_bytes(
                proposal_id=proposal_id,
                events=(event,),
            ),
        }

    def show_scope(self, proposal_id: str) -> ProjectMemoryScope:
        proposal_dir = self.find_proposal_dir(proposal_id)
        scope_path = proposal_dir / _SCOPE_FILENAME
        events_path = proposal_dir / _EVENTS_FILENAME
        for path in (scope_path, events_path):
            if not path.is_file() or path.is_symlink():
                raise ValueError(
                    "P2P_PROJECT_MEMORY_SCOPE_INVALID: canonical scope or event "
                    "ledger is missing or unsafe"
                )
        scope, _events = validated_scope_pair_from_bytes(
            scope_path.read_bytes(),
            events_path.read_bytes(),
            expected_proposal_id=proposal_id,
        )
        return scope

    def memory_revision(self) -> str:
        records, _ = self._source_records()
        return _memory_revision(records)

    def assign_scope(
        self,
        *,
        proposal_id: str,
        kind: str,
        section_ids: Sequence[str],
        operation_key: str,
        expected_memory_revision: str,
        expected_structure_revision: int,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
    ) -> ProjectMemoryScopeMutationResult:
        validate_idempotency_key(operation_key)
        replay = self._exact_replay(
            proposal_id=proposal_id,
            kind=kind,
            section_ids=section_ids,
            operation_key=operation_key,
            expected_memory_revision=expected_memory_revision,
            expected_structure_revision=expected_structure_revision,
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

        normalized_kind, normalized_sections = _normalize_target(kind, section_ids)
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=("project.memory.classify",),
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        structure = self.project_structure()
        if expected_structure_revision != structure.revision:
            raise ValueError(
                "P2P_PROJECT_MEMORY_SCOPE_STALE_STRUCTURE: expected structure revision "
                f"{expected_structure_revision}, current revision is {structure.revision}"
            )
        records, truncated = self._source_records()
        if truncated:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_SOURCE_LIMIT: classifiable memory exceeds limit")
        memory_revision = _memory_revision(records)
        if expected_memory_revision != memory_revision:
            raise ValueError(
                "P2P_PROJECT_MEMORY_SCOPE_STALE_MEMORY: expected memory revision does not match current memory"
            )
        active_ids = set(structure.active_section_ids())
        all_ids = {item.section_id for item in structure.sections}
        if normalized_kind == ProjectMemoryScopeKind.sections:
            retired = sorted(set(normalized_sections) & (all_ids - active_ids))
            unknown = sorted(set(normalized_sections) - all_ids)
            if retired:
                raise ValueError(
                    "P2P_PROJECT_MEMORY_SCOPE_RETIRED_SECTION: " + ", ".join(retired)
                )
            if unknown:
                raise ValueError(
                    "P2P_PROJECT_MEMORY_SCOPE_UNKNOWN_SECTION: " + ", ".join(unknown)
                )
        proposal_dir = self.find_proposal_dir(proposal_id)
        scope_path = (proposal_dir / _SCOPE_FILENAME).relative_to(self.root).as_posix()
        events_path = (proposal_dir / _EVENTS_FILENAME).relative_to(self.root).as_posix()
        scope_file = self.root / scope_path
        events_file = self.root / events_path
        previous = self.show_scope(proposal_id)
        if previous.kind == normalized_kind and previous.section_ids == normalized_sections:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_NO_CHANGE: requested scope is already current")
        next_scope = ProjectMemoryScope(
            object_type="proposal",
            object_id=proposal_id,
            revision=previous.revision + 1,
            kind=normalized_kind,
            section_ids=normalized_sections,
            structure_id=structure.structure_id,
            structure_revision=structure.revision,
            structure_checksum=structure.checksum,
            updated_at=self.clock(),
            updated_by=evidence.subject.identity_id,
            authority=evidence.to_dict(),
        )
        existing_events = scope_events_from_bytes(
            events_file.read_bytes(),
            expected_proposal_id=proposal_id,
        )
        if len(existing_events) >= PROJECT_MEMORY_SCOPE_EVENT_LIMIT:
            raise ValueError("P2P_PROJECT_MEMORY_SCOPE_EVENT_LIMIT: event limit exceeded")
        event = ProjectMemoryScopeEvent(
            event_id=f"scope-event-{next_scope.revision:08d}",
            scope_revision=next_scope.revision,
            scope_sha256=next_scope.semantic_sha256,
            occurred_at=next_scope.updated_at,
            subject_id=evidence.subject.identity_id,
            executor_id=evidence.executor.identity_id,
            authority=evidence.to_dict(),
            previous_kind=previous.kind.value,
            current_kind=next_scope.kind.value,
            section_ids=next_scope.section_ids,
        )
        candidates = {
            scope_path: scope_bytes(next_scope),
            events_path: scope_events_bytes(
                proposal_id=proposal_id,
                events=(*existing_events, event),
            ),
        }
        next_records = dict(records)
        next_records.update(candidates)
        next_memory_revision = _memory_revision(tuple(sorted(next_records.items())))
        normalized_request = {
            "proposal_id": proposal_id,
            "kind": normalized_kind.value,
            "section_ids": list(normalized_sections),
            "expected_memory_revision": expected_memory_revision,
            "expected_structure_revision": expected_structure_revision,
        }
        request_fingerprint = semantic_sha256(
            {
                "policy_version": PROJECT_MEMORY_SCOPE_POLICY_VERSION,
                "operation_key_sha256": idempotency_key_sha256(operation_key),
                "request": normalized_request,
                "authority_context_sha256": context.digest_sha256,
            }
        )
        receipt_path = self.receipts.relative_path(operation_key)
        sources_by_path = {path: content for path, content in records}
        sources = tuple(
            source_precondition(path, content)
            for path, content in sorted(sources_by_path.items())
        ) + tuple(
            source_precondition(path, None)
            for path in sorted(set(candidates) - set(sources_by_path))
        ) + (
            source_precondition(
                ".p2p/project/structure.yml",
                (self.root / ".p2p/project/structure.yml").read_bytes(),
            ),
            source_precondition(receipt_path, None),
        )
        preview = MutationPreviewService.build(
            operation_id="project-memory-scope-set",
            targets=(*sorted(candidates), receipt_path),
            actor=evidence.executor.identity_id,
            authority="typed_authority_context",
            sources=sources,
            candidate_semantics={
                scope_path: next_scope.to_dict(),
                events_path: event.to_dict(),
            },
            semantic_diff={
                "proposal_id": proposal_id,
                "scope_before": previous.kind.value,
                "scope_after": next_scope.kind.value,
                "sections_before": list(previous.section_ids),
                "sections_after": list(next_scope.section_ids),
                "memory_revision_before": memory_revision,
                "memory_revision_after": next_memory_revision,
            },
            token_context={
                "request_fingerprint_sha256": request_fingerprint,
                "authority_context_sha256": context.digest_sha256,
                "operation_key_sha256": idempotency_key_sha256(operation_key),
            },
            policy_version=PROJECT_MEMORY_SCOPE_POLICY_VERSION,
        )
        summary = {
            "contract": PROJECT_MEMORY_SCOPE_MUTATION_CONTRACT,
            "operation": PROJECT_MEMORY_SCOPE_OPERATION,
            "operation_id": "project.memory.scope.set",
            "request": normalized_request,
            "previous_scope": previous.to_dict(include_authority=False),
            "current_scope": next_scope.to_dict(),
            "previous_memory_revision": memory_revision,
            "current_memory_revision": next_memory_revision,
            "event": event.to_dict(),
            "changed_paths": sorted(candidates),
        }
        receipt_path, receipt_content, _ = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=PROJECT_MEMORY_SCOPE_OPERATION,
            actor=evidence.executor.identity_id,
            request_fingerprint_sha256=request_fingerprint,
            preview_token=preview.preview_token,
            result=summary,
            candidates=candidates,
            authority=evidence,
        )
        mutation = self.atomic_writer.apply(
            operation_id="project-memory-scope-set",
            candidates={**candidates, receipt_path: receipt_content},
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=evidence.executor.identity_id,
            candidate_validator=lambda view: _validate_candidate_view(
                view,
                proposal_id=proposal_id,
                scope_path=scope_path,
                events_path=events_path,
                expected_scope_sha256=next_scope.semantic_sha256,
            ),
        )
        if mutation.status != "applied":
            replay = self._exact_replay(
                proposal_id=proposal_id,
                kind=kind,
                section_ids=section_ids,
                operation_key=operation_key,
                expected_memory_revision=expected_memory_revision,
                expected_structure_revision=expected_structure_revision,
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
                "P2P_PROJECT_MEMORY_SCOPE_MUTATION_FAILED: "
                + (mutation.message or mutation.status)
            )
        self.invalidate()
        return ProjectMemoryScopeMutationResult(
            status="applied",
            previous=previous,
            current=next_scope,
            previous_memory_revision=memory_revision,
            current_memory_revision=next_memory_revision,
            event=event,
            actor=evidence.executor.identity_id,
            message="Project-memory scope changed atomically.",
        )

    def classification(self) -> MemoryClassificationSnapshot:
        structure = self.project_structure()
        memory_revision = self.memory_revision()
        identity = (
            structure.structure_id,
            structure.revision,
            structure.checksum,
            memory_revision,
        )
        if identity == self._cached_identity and self._cached_snapshot is not None:
            return self._cached_snapshot
        active_sections = set(structure.active_section_ids())
        retired_sections = {
            item.section_id for item in structure.sections if item.lifecycle == "retired"
        }
        items: list[MemoryClassificationItem] = []
        diagnostics: list[Mapping[str, object]] = []
        truncated = False
        proposal_dirs = sorted(
            (
                path
                for path in (self.p2p_dir / "proposals").glob("PROP-*-*")
                if path.is_dir() and not path.is_symlink()
            ),
            key=lambda path: path.name,
        )
        if len(proposal_dirs) > PROJECT_MEMORY_OBJECT_LIMIT:
            proposal_dirs = proposal_dirs[:PROJECT_MEMORY_OBJECT_LIMIT]
            truncated = True
        for proposal_dir in proposal_dirs:
            proposal_id = proposal_dir.name.split("-", 2)
            if len(proposal_id) < 2:
                continue
            identifier = f"{proposal_id[0]}-{proposal_id[1]}"
            try:
                lifecycle = self.proposal_lifecycle(identifier)
                state = str(getattr(getattr(lifecycle, "effective_state", "unknown"), "value", getattr(lifecycle, "effective_state", "unknown")))
                active = state in _ACTIVE_PROPOSAL_STATES
                scope = self.show_scope(identifier)
                items.append(
                    _classification_item(
                        object_type="proposal",
                        object_id=identifier,
                        lifecycle=state,
                        active=active,
                        scope=scope,
                        active_sections=active_sections,
                        retired_sections=retired_sections,
                    )
                )
            except ValueError as exc:
                items.append(
                    MemoryClassificationItem(
                        object_type="proposal",
                        object_id=identifier,
                        lifecycle="unknown",
                        state="unknown",
                        scope_kind="unknown",
                        decision_blocking=True,
                        message=str(exc),
                    )
                )
                diagnostics.append(
                    {"code": "P2P_MEMORY_CLASSIFICATION_SCOPE_INVALID", "object_id": identifier, "message": str(exc)}
                )
        questions = None
        questions_invalid = False
        if self.project_questions is not None:
            try:
                questions = self.project_questions()
            except ValueError as exc:
                questions_invalid = True
                diagnostics.append(
                    {
                        "code": "P2P_MEMORY_CLASSIFICATION_QUESTIONS_INVALID",
                        "message": str(exc),
                    }
                )
        if questions is not None:
            remaining = max(0, PROJECT_MEMORY_OBJECT_LIMIT - len(items))
            if len(questions.questions) > remaining:
                truncated = True
            for question in questions.questions[:remaining]:
                active = (
                    question.state in _ACTIVE_QUESTION_STATES
                    and question.applicability
                    in {
                        ProjectQuestionApplicability.ACTIVE,
                        ProjectQuestionApplicability.RECONCILIATION_REQUIRED,
                    }
                )
                scope = ProjectMemoryScope(
                    object_type="proposal",
                    object_id="PROP-000",
                    revision=1,
                    kind=ProjectMemoryScopeKind.sections,
                    section_ids=(question.section_id,),
                    structure_id=structure.structure_id,
                    structure_revision=structure.revision,
                    structure_checksum=structure.checksum,
                )
                item = _classification_item(
                    object_type="formal_question",
                    object_id=question.question_id,
                    lifecycle=question.state.value,
                    active=active,
                    scope=scope,
                    active_sections=active_sections,
                    retired_sections=retired_sections,
                )
                items.append(replace(item, decision_blocking=False))
        status, counts, per_type = _classification_summary(items, truncated=truncated)
        if questions_invalid:
            status = "unknown"
        final_structure = self.project_structure()
        final_memory_revision = self.memory_revision()
        if (
            final_structure.revision != structure.revision
            or final_structure.checksum != structure.checksum
            or final_memory_revision != memory_revision
        ):
            status = "stale"
            diagnostics.append(
                {"code": "P2P_MEMORY_CLASSIFICATION_STALE", "message": "Canonical memory or structure changed during classification."}
            )
        snapshot = MemoryClassificationSnapshot(
            status=status,
            structure_id=structure.structure_id,
            structure_revision=structure.revision,
            structure_checksum=structure.checksum,
            memory_revision=memory_revision,
            counts=counts,
            per_type=per_type,
            items=tuple(items),
            truncated=truncated,
            diagnostics=tuple(diagnostics),
        )
        if status != "stale":
            self._cached_identity = identity
            self._cached_snapshot = snapshot
        return snapshot

    def invalidate(self) -> None:
        self._cached_identity = None
        self._cached_snapshot = None

    def require_decision_scope(self, proposal_id: str) -> ProjectMemoryScope:
        scope, _sources = self._capture_decision_scope(proposal_id)
        return scope

    def decision_scope_preconditions(
        self,
        proposal_id: str,
    ) -> tuple[SourcePrecondition, ...]:
        _scope, sources = self._capture_decision_scope(proposal_id)
        return sources

    def _capture_decision_scope(
        self,
        proposal_id: str,
    ) -> tuple[ProjectMemoryScope, tuple[SourcePrecondition, ...]]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        scope_path = proposal_dir / _SCOPE_FILENAME
        events_path = proposal_dir / _EVENTS_FILENAME
        structure_path = self.root / PROJECT_STRUCTURE_PATH
        required = (scope_path, events_path, structure_path)
        for path in required:
            if not path.is_file() or path.is_symlink():
                raise ValueError(
                    "P2P_PROJECT_MEMORY_SCOPE_INVALID: required decision source is "
                    f"missing or unsafe: {path.relative_to(self.root).as_posix()}"
                )
        scope_content = scope_path.read_bytes()
        events_content = events_path.read_bytes()
        structure_content = structure_path.read_bytes()
        scope, events = validated_scope_pair_from_bytes(
            scope_content,
            events_content,
            expected_proposal_id=proposal_id,
        )
        structure = project_structure_from_bytes(structure_content)
        if scope.kind == ProjectMemoryScopeKind.unassigned:
            raise ValueError(
                "P2P_PROJECT_MEMORY_SCOPE_DECISION_BLOCKED: authority-creating decision requires sections or project_global scope"
            )
        if scope.kind == ProjectMemoryScopeKind.sections:
            active = set(structure.active_section_ids())
            invalid = sorted(set(scope.section_ids) - active)
            if invalid:
                raise ValueError(
                    "P2P_PROJECT_MEMORY_SCOPE_REASSIGNMENT_REQUIRED: authority-creating decision references non-active sections: "
                    + ", ".join(invalid)
                )
        sources = tuple(
            source_precondition(
                path.relative_to(self.root).as_posix(),
                content,
            )
            for path, content in (
                (scope_path, scope_content),
                (events_path, events_content),
                (structure_path, structure_content),
            )
        )
        return scope, sources

    def _source_records(self) -> tuple[tuple[tuple[str, bytes], ...], bool]:
        selected: list[tuple[str, bytes]] = []
        question_path = self.p2p_dir / "project" / "questions.yml"
        if question_path.is_file() and not question_path.is_symlink():
            selected.append((question_path.relative_to(self.root).as_posix(), question_path.read_bytes()))
        proposal_root = self.p2p_dir / "proposals"
        filenames = {"proposal.md", "decision-events.yml", _SCOPE_FILENAME, _EVENTS_FILENAME}
        if proposal_root.is_dir():
            for proposal_dir in sorted(proposal_root.iterdir(), key=lambda path: path.name):
                if not proposal_dir.is_dir() or proposal_dir.is_symlink():
                    continue
                for filename in sorted(filenames):
                    path = proposal_dir / filename
                    if path.is_file() and not path.is_symlink():
                        selected.append((path.relative_to(self.root).as_posix(), path.read_bytes()))
        truncated = len(selected) > PROJECT_MEMORY_OBJECT_LIMIT * len(filenames) + 1
        return tuple(selected[: PROJECT_MEMORY_OBJECT_LIMIT * len(filenames) + 1]), truncated

    def _exact_replay(
        self,
        *,
        proposal_id: str,
        kind: str,
        section_ids: Sequence[str],
        operation_key: str,
        expected_memory_revision: str,
        expected_structure_revision: int,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        channel: str,
        consent_id: str | None,
        consent_sha256: str | None,
    ) -> ProjectMemoryScopeMutationResult | None:
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is None:
            return None
        if receipt.operation != PROJECT_MEMORY_SCOPE_OPERATION or receipt.authority is None:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation")
        normalized_kind, normalized_sections = _normalize_target(kind, section_ids)
        expected_request = {
            "proposal_id": proposal_id,
            "kind": normalized_kind.value,
            "section_ids": list(normalized_sections),
            "expected_memory_revision": expected_memory_revision,
            "expected_structure_revision": expected_structure_revision,
        }
        result = receipt.result
        if result.get("request") != expected_request:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: operation key is bound to another scope request")
        evidence = self.codec.evidence_from_mapping(receipt.authority)
        if (
            evidence.subject.identity_id != actor_id
            or evidence.executor.identity_id != executor_id
            or evidence.executor.kind.value != executor_kind
            or evidence.channel != channel
            or evidence.consent_id != consent_id
        ):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: scope mutation authority differs")
        if consent_sha256 is not None and consent_sha256 != evidence.consent_sha256:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: scope consent content differs")
        if authority_context is not None and authority_context.digest_sha256 != evidence.authority_context_sha256:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: scope authority context differs")
        previous = project_memory_scope_from_mapping(result.get("previous_scope"))
        current = project_memory_scope_from_mapping(result.get("current_scope"))
        persisted = self.show_scope(proposal_id)
        if persisted.semantic_sha256 != current.semantic_sha256:
            raise ValueError("P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: current scope differs from receipt")
        event = _event_from_mapping(result.get("event"))
        return ProjectMemoryScopeMutationResult(
            status="already_applied",
            previous=previous,
            current=current,
            previous_memory_revision=str(result.get("previous_memory_revision") or ""),
            current_memory_revision=str(result.get("current_memory_revision") or ""),
            event=event,
            actor=evidence.executor.identity_id,
            message="Project-memory scope mutation was already applied with this operation key.",
        )


def scope_bytes(scope: ProjectMemoryScope) -> bytes:
    return yaml_dump({"project_memory_scope": scope.to_dict()}).encode("ascii")


def scope_from_bytes(content: bytes, *, expected_proposal_id: str) -> ProjectMemoryScope:
    try:
        payload = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"P2P_PROJECT_MEMORY_SCOPE_INVALID: cannot parse scope: {exc}") from exc
    if not isinstance(payload, Mapping) or set(payload) != {"project_memory_scope"}:
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: expected project_memory_scope root")
    scope = project_memory_scope_from_mapping(payload.get("project_memory_scope"))
    if scope.object_id != expected_proposal_id:
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: proposal binding mismatch")
    return scope


def scope_events_bytes(
    *,
    proposal_id: str,
    events: Sequence[ProjectMemoryScopeEvent],
) -> bytes:
    return yaml_dump(
        {
            "project_memory_scope_events": {
                "contract": PROJECT_MEMORY_SCOPE_EVENTS_CONTRACT,
                "proposal_id": proposal_id,
                "events": [item.to_dict() for item in events],
            }
        }
    ).encode("ascii")


def scope_events_from_bytes(
    content: bytes,
    *,
    expected_proposal_id: str,
) -> tuple[ProjectMemoryScopeEvent, ...]:
    try:
        payload = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"P2P_PROJECT_MEMORY_SCOPE_INVALID: cannot parse scope events: {exc}") from exc
    root = payload.get("project_memory_scope_events") if isinstance(payload, Mapping) else None
    if not isinstance(root, Mapping):
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: expected scope-events root")
    if root.get("contract") != PROJECT_MEMORY_SCOPE_EVENTS_CONTRACT or root.get("proposal_id") != expected_proposal_id:
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: scope-events binding mismatch")
    raw_events = root.get("events")
    if not isinstance(raw_events, list) or len(raw_events) > PROJECT_MEMORY_SCOPE_EVENT_LIMIT:
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: scope-events sequence is invalid")
    events = tuple(_event_from_mapping(item) for item in raw_events)
    revisions = [item.scope_revision for item in events]
    if revisions != list(range(1, len(events) + 1)):
        raise ValueError(
            "P2P_PROJECT_MEMORY_SCOPE_INVALID: scope-event revisions are not contiguous"
        )
    if any(
        item.event_id != f"scope-event-{item.scope_revision:08d}"
        for item in events
    ):
        raise ValueError(
            "P2P_PROJECT_MEMORY_SCOPE_INVALID: scope-event identity is not canonical"
        )
    return events


def validated_scope_pair_from_bytes(
    scope_content: bytes,
    events_content: bytes,
    *,
    expected_proposal_id: str,
) -> tuple[ProjectMemoryScope, tuple[ProjectMemoryScopeEvent, ...]]:
    scope = scope_from_bytes(
        scope_content,
        expected_proposal_id=expected_proposal_id,
    )
    events = scope_events_from_bytes(
        events_content,
        expected_proposal_id=expected_proposal_id,
    )
    if not events:
        raise ValueError(
            "P2P_PROJECT_MEMORY_SCOPE_INVALID: scope event ledger is empty"
        )
    head = events[-1]
    if (
        head.scope_revision != scope.revision
        or head.scope_sha256 != scope.semantic_sha256
        or head.current_kind != scope.kind.value
        or head.section_ids != scope.section_ids
    ):
        raise ValueError(
            "P2P_PROJECT_MEMORY_SCOPE_INVALID: scope and event head diverge"
        )
    return scope, events


def _event_from_mapping(value: object) -> ProjectMemoryScopeEvent:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: scope event must be a mapping")
    authority = value.get("authority") or {}
    sections = value.get("section_ids") or ()
    if not isinstance(authority, Mapping) or isinstance(sections, (str, bytes)) or not isinstance(sections, Sequence):
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: malformed scope event")
    return ProjectMemoryScopeEvent(
        event_id=str(value.get("event_id") or ""),
        scope_revision=int(value.get("scope_revision") or 0),
        scope_sha256=str(value.get("scope_sha256") or ""),
        occurred_at=str(value.get("occurred_at") or ""),
        subject_id=str(value.get("subject_id") or ""),
        executor_id=str(value.get("executor_id") or ""),
        authority=dict(authority),
        previous_kind=(str(value.get("previous_kind")) if value.get("previous_kind") is not None else None),
        current_kind=str(value.get("current_kind") or ""),
        section_ids=tuple(str(item) for item in sections),
    )


def _normalize_target(
    kind: str,
    section_ids: Sequence[str],
) -> tuple[ProjectMemoryScopeKind, tuple[str, ...]]:
    try:
        normalized_kind = ProjectMemoryScopeKind(str(kind).strip().lower())
    except ValueError as exc:
        raise ValueError("P2P_PROJECT_MEMORY_SCOPE_INVALID: kind must be sections, project_global or unassigned") from exc
    normalized_sections = tuple(str(item).strip().lower() for item in section_ids)
    probe = ProjectMemoryScope(
        object_type="proposal",
        object_id="PROP-000",
        revision=1,
        kind=normalized_kind,
        section_ids=normalized_sections,
        structure_id="probe",
        structure_revision=1,
        structure_checksum="0" * 64,
    )
    return probe.kind, probe.section_ids


def _memory_revision(records: Sequence[tuple[str, bytes]] | Mapping[str, bytes]) -> str:
    values = records.items() if isinstance(records, Mapping) else records
    return semantic_sha256(
        {
            "policy_version": PROJECT_MEMORY_SOURCE_POLICY_VERSION,
            "sources": {
                path: hashlib.sha256(content).hexdigest()
                for path, content in sorted(values)
            },
        }
    )


def _classification_item(
    *,
    object_type: str,
    object_id: str,
    lifecycle: str,
    active: bool,
    scope: ProjectMemoryScope,
    active_sections: set[str],
    retired_sections: set[str],
) -> MemoryClassificationItem:
    if not active:
        return MemoryClassificationItem(
            object_type=object_type,
            object_id=object_id,
            lifecycle=lifecycle,
            state="historical",
            scope_kind=scope.kind.value,
            section_ids=scope.section_ids,
        )
    if scope.kind == ProjectMemoryScopeKind.unassigned:
        return MemoryClassificationItem(
            object_type=object_type,
            object_id=object_id,
            lifecycle=lifecycle,
            state="unassigned",
            scope_kind=scope.kind.value,
            decision_blocking=object_type == "proposal",
        )
    if scope.kind == ProjectMemoryScopeKind.project_global:
        return MemoryClassificationItem(
            object_type=object_type,
            object_id=object_id,
            lifecycle=lifecycle,
            state="project_global",
            scope_kind=scope.kind.value,
        )
    active_ids = tuple(sorted(set(scope.section_ids) & active_sections))
    retired_ids = tuple(sorted(set(scope.section_ids) & retired_sections))
    unknown_ids = tuple(sorted(set(scope.section_ids) - active_sections - retired_sections))
    requires = bool(retired_ids or unknown_ids)
    return MemoryClassificationItem(
        object_type=object_type,
        object_id=object_id,
        lifecycle=lifecycle,
        state="requires_reassignment" if requires else "section_classified",
        scope_kind=scope.kind.value,
        section_ids=scope.section_ids,
        active_section_ids=active_ids,
        retired_section_ids=retired_ids,
        unknown_section_ids=unknown_ids,
        decision_blocking=requires and object_type == "proposal",
        message=("Scope references non-active sections." if requires else ""),
    )


def _classification_summary(
    items: Sequence[MemoryClassificationItem],
    *,
    truncated: bool,
) -> tuple[str, dict[str, int], dict[str, dict[str, int]]]:
    counts = {
        "active_total": 0,
        "section_classified": 0,
        "project_global": 0,
        "unassigned": 0,
        "requires_reassignment": 0,
        "decision_blocking": 0,
        "historical": 0,
        "unknown": 0,
    }
    per_type: dict[str, dict[str, int]] = {}
    for item in items:
        bucket = per_type.setdefault(
            item.object_type,
            {key: 0 for key in counts},
        )
        if item.state != "historical":
            counts["active_total"] += 1
            bucket["active_total"] += 1
        counts[item.state] += 1
        bucket[item.state] += 1
        if item.decision_blocking:
            counts["decision_blocking"] += 1
            bucket["decision_blocking"] += 1
    if truncated or counts["unknown"]:
        status = "unknown"
    elif counts["active_total"] == 0:
        status = "not_applicable"
    elif counts["unassigned"] or counts["requires_reassignment"]:
        status = "incomplete"
    else:
        status = "complete"
    return status, counts, per_type


def _validate_candidate_view(
    view: object,
    *,
    proposal_id: str,
    scope_path: str,
    events_path: str,
    expected_scope_sha256: str,
) -> None:
    scope, _events = validated_scope_pair_from_bytes(
        view.read_bytes(scope_path),  # type: ignore[attr-defined]
        view.read_bytes(events_path),  # type: ignore[attr-defined]
        expected_proposal_id=proposal_id,
    )
    if scope.semantic_sha256 != expected_scope_sha256:
        raise ValueError(
            "P2P_PROJECT_MEMORY_SCOPE_INVALID: candidate scope checksum diverges"
        )

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Callable, Iterable, Sequence

from p2p_engine.core.project_readiness import (
    PROJECT_READINESS_CURSOR_POLICY_VERSION,
    PROJECT_READINESS_DEFAULT_PAYLOAD_BYTES,
    PROJECT_READINESS_DEFAULT_PAGE_SIZE,
    PROJECT_READINESS_GAP_POLICY_VERSION,
    PROJECT_READINESS_MAX_PAGE_SIZE,
    ProjectReadinessCursor,
    ProjectReadinessDiagnostic,
    ProjectReadinessGap,
    ProjectReadinessGapKind,
    ProjectReadinessGapSeverity,
    ProjectReadinessPage,
    ProjectReadinessResult,
    ProjectReadinessSectionSnapshot,
    ProjectReadinessSnapshot,
    readiness_class_rank,
    readiness_gap_identity,
    readiness_snapshot_identity,
)


class ProjectReadinessSnapshotBuilder:
    def build(
        self,
        *,
        workspace_schema_version: int,
        workspace_schema_state: str,
        vertical_id: str,
        vertical_version: str,
        vertical_lock_checksum: str,
        profile: str,
        modules: Sequence[str],
        source_hashes: dict[str, str],
        policy_versions: dict[str, int],
        definition_valid: bool,
        definition_exists: bool,
        fallback_used: bool,
        vertical_source: str,
        sections: Sequence[ProjectReadinessSectionSnapshot],
        unmapped_proposals: Sequence[str],
        owner_available: bool = True,
        diagnostics: Sequence[ProjectReadinessDiagnostic] = (),
    ) -> ProjectReadinessSnapshot:
        identity = readiness_snapshot_identity(
            workspace_schema_version=workspace_schema_version,
            workspace_schema_state=workspace_schema_state,
            vertical_id=vertical_id,
            vertical_version=vertical_version,
            vertical_lock_checksum=vertical_lock_checksum,
            profile=profile,
            modules=modules,
            source_hashes=source_hashes,
            policy_versions=policy_versions,
        )
        return ProjectReadinessSnapshot(
            identity=identity,
            definition_valid=definition_valid,
            definition_exists=definition_exists,
            fallback_used=fallback_used,
            vertical_source=vertical_source,
            sections=tuple(sections),
            unmapped_proposals=tuple(sorted(str(item) for item in unmapped_proposals)),
            owner_available=owner_available,
            diagnostics=tuple(diagnostics),
        )


class ProjectReadinessSourceAccess:
    def __init__(
        self,
        *,
        root: Path,
        reader: Callable[[Path], bytes] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.reader = reader or (lambda path: path.read_bytes())
        self._cache: dict[Path, bytes | None] = {}
        self._counts: Counter[str] = Counter()

    @property
    def counts(self) -> dict[str, int]:
        return dict(sorted(self._counts.items()))

    def read_optional(self, path: Path) -> bytes | None:
        resolved = path.resolve()
        if resolved in self._cache:
            return self._cache[resolved]
        if not resolved.exists():
            self._cache[resolved] = None
            return None
        content = self.reader(resolved)
        key = self._display_path(resolved)
        self._counts[key] += 1
        self._cache[resolved] = content
        return content

    def _display_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()


class ProjectReadinessGapService:
    def classify(self, snapshot: ProjectReadinessSnapshot) -> ProjectReadinessResult:
        gaps: list[ProjectReadinessGap] = []
        if snapshot.identity.workspace_schema_state == "invalid":
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.COMPATIBILITY_BLOCKER,
                    severity=ProjectReadinessGapSeverity.BLOCKER,
                    target_kind="workspace_schema",
                    target_id="workspace_schema",
                    definition_status="not_applicable",
                    next_operation="p2p workspace schema status --format json",
                    rationale="Workspace schema state is invalid and cannot authorize convergence writes.",
                )
            )
        if not snapshot.owner_available:
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.AUTHORITY_BLOCKER,
                    severity=ProjectReadinessGapSeverity.BLOCKER,
                    target_kind="permissions",
                    target_id="owner",
                    definition_status="not_applicable",
                    next_operation="p2p permissions show",
                    rationale="No project-declared owner is available for required owner decisions.",
                )
            )
        for diagnostic in snapshot.diagnostics:
            if diagnostic.severity != "error" or "LOCK" not in diagnostic.code:
                continue
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.INTEGRITY_BLOCKER,
                    severity=ProjectReadinessGapSeverity.BLOCKER,
                    target_kind="vertical_lock",
                    target_id=diagnostic.code,
                    definition_status="not_applicable",
                    next_operation=diagnostic.suggested_command or "p2p project vertical lock show",
                    rationale=diagnostic.message,
                )
            )
        if not snapshot.definition_exists or not snapshot.definition_valid:
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.INTEGRITY_BLOCKER,
                    severity=ProjectReadinessGapSeverity.BLOCKER,
                    target_kind="project_definition",
                    target_id="project_definition",
                    definition_status="missing" if not snapshot.definition_exists else "invalid",
                    next_operation="p2p project definition show",
                    rationale=(
                        "Project definition state is missing."
                        if not snapshot.definition_exists
                        else "Project definition state is invalid."
                    ),
                )
            )

        for section in snapshot.sections:
            gaps.extend(self._section_gaps(snapshot, section))

        if snapshot.unmapped_proposals:
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.INFORMATIONAL_LEGACY,
                    severity=ProjectReadinessGapSeverity.INFO,
                    target_kind="proposal_collection",
                    target_id="unmapped_proposals",
                    definition_status="not_applicable",
                    heuristic_suggestions=snapshot.unmapped_proposals,
                    next_operation="p2p project readiness gaps --kind informational_legacy",
                    rationale=(
                        f"{len(snapshot.unmapped_proposals)} proposals have no declared coverage "
                        "for the selected vertical."
                    ),
                )
            )

        self._validate_gap_id_collisions(gaps)
        ordered = tuple(sorted(gaps, key=self.sort_key))
        counts = Counter(item.kind.value for item in ordered)
        counts["total"] = len(ordered)
        return ProjectReadinessResult(
            snapshot=snapshot.identity,
            gaps=ordered,
            diagnostics=snapshot.diagnostics,
            counts=dict(sorted(counts.items())),
        )

    def _section_gaps(
        self,
        snapshot: ProjectReadinessSnapshot,
        section: ProjectReadinessSectionSnapshot,
    ) -> list[ProjectReadinessGap]:
        gaps: list[ProjectReadinessGap] = []
        applicable = section.definition_status != "not_applicable"
        for question in section.question_states:
            if question.applicability != "applicable":
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.COMPATIBILITY_BLOCKER,
                        severity=ProjectReadinessGapSeverity.BLOCKER,
                        target_kind=question.target_kind,
                        target_id=question.target_id,
                        next_operation="p2p project questions reconcile-preview",
                        rationale=f"Question `{question.question_id}` is not compatible with the active vertical.",
                        question_id=question.question_id,
                        question_revision=question.revision,
                    )
                )
            elif question.state == "answered":
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.ANSWERED_NOT_APPLIED,
                        severity=ProjectReadinessGapSeverity.HIGH,
                        target_kind=question.target_kind,
                        target_id=question.target_id,
                        next_operation="p2p project readiness convergence preview",
                        rationale=f"Question `{question.question_id}` has owner evidence awaiting apply.",
                        question_id=question.question_id,
                        question_revision=question.revision,
                    )
                )
            elif question.state == "to_answer":
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.INCOMPLETE_REQUIRED_DEFINITION,
                        severity=ProjectReadinessGapSeverity.HIGH,
                        target_kind=question.target_kind,
                        target_id=question.target_id,
                        next_operation=(
                            f"p2p project readiness questions answer {question.question_id}"
                        ),
                        rationale=f"Question `{question.question_id}` requires owner input.",
                        question_id=question.question_id,
                        question_revision=question.revision,
                    )
                )
        if section.required and applicable and section.open_blocker_ids:
            for blocker_id in section.open_blocker_ids:
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.OWNER_DECISION_BLOCKER,
                        severity=ProjectReadinessGapSeverity.BLOCKER,
                        target_kind="blocker",
                        target_id=blocker_id,
                        next_operation="p2p project questions next",
                        rationale=f"Required section `{section.section_id}` has an unresolved blocker.",
                    )
                )
        has_active_question = any(
            item.applicability == "applicable" and item.state in {"to_answer", "answered"}
            for item in section.question_states
        )
        if (
            section.required
            and applicable
            and section.definition_status != "complete"
            and not has_active_question
        ):
            gaps.append(
                self._gap(
                    snapshot,
                    section=section,
                    kind=ProjectReadinessGapKind.INCOMPLETE_REQUIRED_DEFINITION,
                    severity=ProjectReadinessGapSeverity.HIGH,
                    target_kind="section",
                    target_id=section.section_id,
                    missing_fields=section.missing_required_fields,
                    next_operation="p2p project questions next",
                    rationale=f"Required section `{section.section_id}` is not complete.",
                )
            )
        for assumption in section.assumptions:
            if assumption.status != "to_validate" or not applicable:
                continue
            gaps.append(
                self._gap(
                    snapshot,
                    section=section,
                    kind=ProjectReadinessGapKind.ASSUMPTION_TO_VALIDATE,
                    severity=ProjectReadinessGapSeverity.MEDIUM,
                    target_kind="assumption",
                    target_id=assumption.assumption_id,
                    next_operation="p2p project questions next",
                    rationale=f"Assumption `{assumption.assumption_id}` requires owner validation.",
                    dependency_rank=assumption.dependency_rank,
                )
            )
        if applicable and not section.active_declared_proposals:
            gaps.append(
                self._gap(
                    snapshot,
                    section=section,
                    kind=ProjectReadinessGapKind.OPTIONAL_DECLARED_EVIDENCE,
                    severity=ProjectReadinessGapSeverity.LOW,
                    target_kind="section_evidence",
                    target_id=section.section_id,
                    next_operation="p2p proposal vertical-coverage status <PROPOSAL-ID>",
                    rationale=f"Section `{section.section_id}` has no active declared proposal evidence.",
                )
            )
        return gaps

    def _gap(
        self,
        snapshot: ProjectReadinessSnapshot,
        *,
        section: ProjectReadinessSectionSnapshot | None,
        kind: ProjectReadinessGapKind,
        severity: ProjectReadinessGapSeverity,
        target_kind: str,
        target_id: str,
        next_operation: str,
        rationale: str,
        definition_status: str | None = None,
        missing_fields: Sequence[str] = (),
        heuristic_suggestions: Sequence[str] | None = None,
        dependency_rank: int = 100,
        question_id: str = "",
        question_revision: int | None = None,
    ) -> ProjectReadinessGap:
        section_id = section.section_id if section else ""
        gap_id, digest = readiness_gap_identity(
            vertical_id=snapshot.identity.vertical_id,
            section_id=section_id,
            kind=kind,
            target_kind=target_kind,
            target_id=target_id,
        )
        priority_class = readiness_class_rank(kind)
        section_priority = section.priority if section else 0
        dependency_tie_break = dependency_rank if kind == ProjectReadinessGapKind.ASSUMPTION_TO_VALIDATE else 0
        tie_break: tuple[object, ...] = (priority_class, dependency_tie_break, section_priority, gap_id)
        return ProjectReadinessGap(
            gap_id=gap_id,
            identity_sha256=digest,
            snapshot_fingerprint=snapshot.identity.fingerprint,
            vertical_id=snapshot.identity.vertical_id,
            vertical_version=snapshot.identity.vertical_version,
            vertical_lock_checksum=snapshot.identity.vertical_lock_checksum,
            section_id=section_id,
            target_kind=target_kind,
            target_id=target_id,
            kind=kind,
            severity=severity,
            applicability="applicable",
            definition_status=definition_status or (section.definition_status if section else "not_initialized"),
            missing_fields=tuple(sorted(str(item) for item in missing_fields)),
            declared_evidence=section.active_declared_proposals if section else (),
            heuristic_suggestions=(
                tuple(sorted(str(item) for item in heuristic_suggestions))
                if heuristic_suggestions is not None
                else (section.heuristic_proposals if section else ())
            ),
            required_authority="owner" if kind not in {ProjectReadinessGapKind.OPTIONAL_DECLARED_EVIDENCE, ProjectReadinessGapKind.INFORMATIONAL_LEGACY} else "reviewer",
            owner_input_required=kind not in {ProjectReadinessGapKind.OPTIONAL_DECLARED_EVIDENCE, ProjectReadinessGapKind.INFORMATIONAL_LEGACY},
            question_id=question_id,
            question_revision=question_revision,
            next_operation=next_operation,
            rationale=rationale,
            priority_class=priority_class,
            priority_policy_version=PROJECT_READINESS_GAP_POLICY_VERSION,
            priority_rationale=self._priority_rationale(kind),
            tie_break=tie_break,
            dependency_rank=dependency_rank,
        )

    @staticmethod
    def sort_key(gap: ProjectReadinessGap) -> tuple[object, ...]:
        return gap.tie_break

    @staticmethod
    def _validate_gap_id_collisions(gaps: Sequence[ProjectReadinessGap]) -> None:
        digests: dict[str, str] = {}
        for gap in gaps:
            existing = digests.setdefault(gap.gap_id, gap.identity_sha256)
            if existing != gap.identity_sha256:
                raise ValueError(
                    f"Project readiness gap id collision for `{gap.gap_id}`; full identities differ."
                )

    @staticmethod
    def _priority_rationale(kind: ProjectReadinessGapKind) -> str:
        labels = {
            1: "Integrity, compatibility, authority and owner-decision blockers come first.",
            2: "Owner answers already received should be applied before requesting more input.",
            3: "Incomplete required definition sections precede assumptions and optional evidence.",
            4: "Assumptions are ordered by declared dependency impact with a neutral fallback.",
            5: "Optional declared evidence follows required definition work.",
            6: "Informational legacy state is lowest priority.",
        }
        return labels[readiness_class_rank(kind)]


class ProjectReadinessPaginationService:
    def page_items(
        self,
        *,
        collection: str,
        snapshot_fingerprint: str,
        items: Sequence[object],
        key: Callable[[object], tuple[object, ...]],
        limit: int = PROJECT_READINESS_DEFAULT_PAGE_SIZE,
        cursor: str = "",
    ) -> ProjectReadinessPage:
        return self._page(
            collection=collection,
            snapshot_fingerprint=snapshot_fingerprint,
            items=items,
            key=key,
            limit=limit,
            cursor=cursor,
        )

    def page_gaps(
        self,
        result: ProjectReadinessResult,
        *,
        limit: int = PROJECT_READINESS_DEFAULT_PAGE_SIZE,
        cursor: str = "",
        predicate: Callable[[ProjectReadinessGap], bool] | None = None,
    ) -> ProjectReadinessPage:
        items = [item for item in result.gaps if predicate is None or predicate(item)]
        return self._page(
            collection="gaps",
            snapshot_fingerprint=result.snapshot.fingerprint,
            items=items,
            key=lambda item: item.tie_break,
            limit=limit,
            cursor=cursor,
        )

    def page_values(
        self,
        *,
        collection: str,
        snapshot_fingerprint: str,
        values: Iterable[str],
        limit: int = PROJECT_READINESS_DEFAULT_PAGE_SIZE,
        cursor: str = "",
    ) -> ProjectReadinessPage:
        items = sorted(dict.fromkeys(str(item) for item in values))
        return self._page(
            collection=collection,
            snapshot_fingerprint=snapshot_fingerprint,
            items=items,
            key=lambda item: (item,),
            limit=limit,
            cursor=cursor,
        )

    def _page(
        self,
        *,
        collection: str,
        snapshot_fingerprint: str,
        items: Sequence[object],
        key: Callable[[object], tuple[object, ...]],
        limit: int,
        cursor: str,
    ) -> ProjectReadinessPage:
        normalized_limit = int(limit)
        if normalized_limit < 1 or normalized_limit > PROJECT_READINESS_MAX_PAGE_SIZE:
            raise ValueError(f"Readiness page limit must be between 1 and {PROJECT_READINESS_MAX_PAGE_SIZE}.")
        start = 0
        if cursor:
            decoded = ProjectReadinessCursor.decode(cursor)
            if decoded.collection != collection:
                raise ValueError("Readiness cursor belongs to a different collection.")
            if decoded.policy_version != PROJECT_READINESS_CURSOR_POLICY_VERSION:
                raise ValueError("Readiness cursor policy changed. Restart pagination without a cursor.")
            if decoded.snapshot_fingerprint != snapshot_fingerprint:
                raise ValueError(
                    "P2P349_PROJECT_READINESS_CURSOR_STALE: stale_cursor: readiness sources changed; "
                    "restart pagination without a cursor."
                )
            for index, item in enumerate(items):
                if tuple(key(item)) == decoded.last_key:
                    start = index + 1
                    break
            else:
                raise ValueError(
                    "P2P349_PROJECT_READINESS_CURSOR_STALE: stale_cursor: cursor key is no longer present; "
                    "restart pagination."
                )
        selected = tuple(items[start : start + normalized_limit])
        diagnostics: tuple[ProjectReadinessDiagnostic, ...] = ()
        payload_bytes = self._payload_size(selected)
        while selected and payload_bytes > PROJECT_READINESS_DEFAULT_PAYLOAD_BYTES:
            selected = selected[:-1]
            payload_bytes = self._payload_size(selected)
        if not selected and start < len(items):
            diagnostics = (
                ProjectReadinessDiagnostic(
                    code="P2P353_READINESS_PAYLOAD_LIMIT",
                    severity="warning",
                    message=(
                        "The next readiness record exceeds the default payload budget. "
                        "Use a narrower collection filter or detail request."
                    ),
                ),
            )
        truncated = start + len(selected) < len(items)
        next_cursor = ""
        if truncated and selected:
            next_cursor = ProjectReadinessCursor(
                collection=collection,
                snapshot_fingerprint=snapshot_fingerprint,
                policy_version=PROJECT_READINESS_CURSOR_POLICY_VERSION,
                last_key=tuple(key(selected[-1])),
            ).encode()
        return ProjectReadinessPage(
            collection=collection,
            snapshot_fingerprint=snapshot_fingerprint,
            items=selected,
            total=len(items),
            limit=normalized_limit,
            next_cursor=next_cursor,
            truncated=truncated,
            payload_bytes=payload_bytes,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _payload_size(items: Sequence[object]) -> int:
        from p2p_engine.core.mutation_preview import canonical_json_bytes

        values = []
        for item in items:
            to_dict = getattr(item, "to_dict", None)
            values.append(to_dict() if callable(to_dict) else item)
        return len(canonical_json_bytes(values))


def attach_question_reference(
    gap: ProjectReadinessGap,
    *,
    question_id: str,
    question_revision: int,
    next_operation: str,
) -> ProjectReadinessGap:
    return replace(
        gap,
        question_id=question_id,
        question_revision=question_revision,
        next_operation=next_operation,
    )

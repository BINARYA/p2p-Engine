from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath

import yaml

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.proposal_decision_events import (
    PROPOSAL_DECISION_IMPACT_POLICY_VERSION,
    ProposalDecisionDependencyControl,
    ProposalDecisionDependencyKind,
    ProposalDecisionDependencyStatus,
    ProposalDecisionEventType,
    ProposalDecisionImpactCompleteness,
    ProposalDecisionImpactItem,
    ProposalDecisionImpactPage,
    ProposalDecisionImpactSeverity,
    ProposalDecisionImpactSnapshot,
    ProposalDecisionLifecycleView,
)
from p2p_engine.foundation.markdown import read_frontmatter


IMPACT_POLICY_VERSION = PROPOSAL_DECISION_IMPACT_POLICY_VERSION
MAX_IMPACT_PAGE_LIMIT = 100
_CURSOR = re.compile(r"^PDIC-(\d+)-([0-9a-f]{16})$")
_CHANGE_TERMINAL = frozenset({"completed", "cancelled", "rejected", "superseded"})
_WORK_TERMINAL = frozenset({"accepted", "retired", "cleaned", "completed", "cancelled"})
_FRESHNESS_NOT_PROVIDED = object()
_KIND_RANK = {
    kind: index
    for index, kind in enumerate(
        (
            ProposalDecisionDependencyKind.change,
            ProposalDecisionDependencyKind.work,
            ProposalDecisionDependencyKind.software_spec,
            ProposalDecisionDependencyKind.vertical_evidence,
            ProposalDecisionDependencyKind.relation,
            ProposalDecisionDependencyKind.conflict,
            ProposalDecisionDependencyKind.decision_context,
            ProposalDecisionDependencyKind.project_projection,
            ProposalDecisionDependencyKind.freshness,
            ProposalDecisionDependencyKind.publication,
        )
    )
}
_STATUS_RANK = {
    ProposalDecisionDependencyStatus.active: 0,
    ProposalDecisionDependencyStatus.current: 1,
    ProposalDecisionDependencyStatus.completed: 2,
    ProposalDecisionDependencyStatus.generated: 3,
    ProposalDecisionDependencyStatus.stale: 4,
    ProposalDecisionDependencyStatus.historical: 5,
    ProposalDecisionDependencyStatus.terminal: 6,
    ProposalDecisionDependencyStatus.unknown: 7,
}


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: yaml.SafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key `{key}`")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


class ProposalDecisionImpactService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
        freshness_status: Callable[[], object] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.find_proposal_dir = find_proposal_dir
        self.freshness_status = freshness_status

    def capture(
        self,
        proposal_id: str,
        *,
        source_head_event_id: str | None,
        event_type: ProposalDecisionEventType,
        freshness_status_snapshot: object = _FRESHNESS_NOT_PROVIDED,
    ) -> ProposalDecisionImpactSnapshot:
        capture = _ImpactCapture(root=self.root, p2p_dir=self.p2p_dir)
        items: list[ProposalDecisionImpactItem] = []
        diagnostics: list[str] = []
        affected_changes = self._capture_changes(
            capture,
            proposal_id,
            source_head_event_id,
            items,
            diagnostics,
        )
        affected_work = self._capture_work(
            capture,
            proposal_id,
            source_head_event_id,
            affected_changes,
            items,
            diagnostics,
        )
        self._capture_specs(
            capture,
            proposal_id,
            source_head_event_id,
            affected_changes,
            items,
            diagnostics,
        )
        self._capture_vertical_evidence(
            capture,
            proposal_id,
            source_head_event_id,
            items,
            diagnostics,
        )
        self._capture_relations_and_conflicts(
            capture,
            proposal_id,
            source_head_event_id,
            affected_changes,
            affected_work,
            items,
            diagnostics,
        )
        self._capture_project_views(
            capture,
            proposal_id,
            source_head_event_id,
            items,
            diagnostics,
        )
        self._capture_publication(
            capture,
            proposal_id,
            source_head_event_id,
            affected_changes,
            items,
        )
        self._capture_freshness(
            capture,
            proposal_id,
            source_head_event_id,
            bool(items),
            items,
            diagnostics,
            freshness_status_snapshot,
        )
        ordered = tuple(
            sorted(
                _dedupe_items(items),
                key=lambda item: (
                    _KIND_RANK[item.dependency_kind],
                    _STATUS_RANK[item.dependency_status],
                    item.dependency_id,
                    item.relationship,
                    item.impact_id,
                ),
            )
        )
        kind_counts = Counter(item.dependency_kind.value for item in ordered)
        status_counts = Counter(item.dependency_status.value for item in ordered)
        complete = not any(
            diagnostic.startswith("P2P370_DECISION_IMPACT_INCOMPLETE")
            for diagnostic in diagnostics
        )
        source_fingerprint = semantic_sha256(
            {
                "policy_version": IMPACT_POLICY_VERSION,
                "proposal_id": proposal_id,
                "source_head_event_id": source_head_event_id,
                "event_type": event_type.value,
                "sources": capture.hashes,
                "items": [item.to_dict() for item in ordered],
                "diagnostics": diagnostics,
            }
        )
        preview_token = semantic_sha256(
            {
                "policy_version": IMPACT_POLICY_VERSION,
                "proposal_id": proposal_id,
                "source_head_event_id": source_head_event_id,
                "event_type": event_type.value,
                "source_fingerprint_sha256": source_fingerprint,
            }
        )
        return ProposalDecisionImpactSnapshot(
            proposal_id=proposal_id,
            source_head_event_id=source_head_event_id,
            event_type=event_type,
            completeness=(
                ProposalDecisionImpactCompleteness.complete
                if complete
                else ProposalDecisionImpactCompleteness.incomplete
            ),
            items=ordered,
            source_fingerprint_sha256=source_fingerprint,
            preview_token=preview_token,
            source_bytes=dict(capture.atomic_sources),
            kind_counts=dict(sorted(kind_counts.items())),
            status_counts=dict(sorted(status_counts.items())),
            diagnostics=tuple(diagnostics),
            access_counters=dict(sorted(capture.counters.items())),
        )

    def provider(
        self,
        proposal_id: str,
        event_type: ProposalDecisionEventType,
        lifecycle: ProposalDecisionLifecycleView,
    ) -> Mapping[str, object]:
        return self.capture(
            proposal_id,
            source_head_event_id=lifecycle.head_event_id,
            event_type=event_type,
        ).provider_payload()

    def page(
        self,
        snapshot: ProposalDecisionImpactSnapshot,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ProposalDecisionImpactPage:
        if isinstance(limit, bool) or not 1 <= limit <= MAX_IMPACT_PAGE_LIMIT:
            raise ValueError(
                f"Decision impact limit must be between 1 and {MAX_IMPACT_PAGE_LIMIT}."
            )
        offset = self._cursor_offset(snapshot, cursor)
        items = snapshot.items[offset : offset + limit]
        next_offset = offset + len(items)
        next_cursor = (
            self._cursor(snapshot, next_offset)
            if next_offset < snapshot.total_count
            else None
        )
        return ProposalDecisionImpactPage(
            proposal_id=snapshot.proposal_id,
            source_head_event_id=snapshot.source_head_event_id,
            items=items,
            total_count=snapshot.total_count,
            returned_count=len(items),
            omitted_count=snapshot.total_count - offset - len(items),
            next_cursor=next_cursor,
            completeness=snapshot.completeness,
            diagnostics=snapshot.diagnostics,
        )

    def _capture_changes(
        self,
        capture: "_ImpactCapture",
        proposal_id: str,
        source_head: str | None,
        items: list[ProposalDecisionImpactItem],
        diagnostics: list[str],
    ) -> set[str]:
        result: set[str] = set()
        root = self.p2p_dir / "changes"
        for directory in capture.directories(root, "change_directories"):
            change_id = _id_from_directory(directory, "CHANGE")
            if change_id is None:
                continue
            source_paths: list[str] = []
            payloads: list[object] = []
            for filename in (
                "included-proposals.yml",
                "referenced-proposals.yml",
                "included-decisions.yml",
            ):
                path = directory / filename
                if not path.exists():
                    continue
                source_paths.append(capture.relative(path))
                parsed = capture.yaml(path, diagnostics, required=True)
                if parsed is not None:
                    payloads.append(parsed)
            change_path = directory / "change.md"
            status = "unknown"
            if change_path.exists():
                source_paths.append(capture.relative(change_path))
                text = capture.text(change_path, diagnostics, required=True)
                if text is not None:
                    frontmatter = read_frontmatter(text)
                    status = str(frontmatter.get("status") or "unknown")
                    payloads.append(frontmatter)
            if not any(_contains_reference(value, proposal_id) for value in payloads):
                continue
            result.add(change_id)
            dependency_status = (
                ProposalDecisionDependencyStatus.completed
                if status == "completed"
                else ProposalDecisionDependencyStatus.terminal
                if status in _CHANGE_TERMINAL
                else ProposalDecisionDependencyStatus.active
            )
            items.append(
                self._item(
                    proposal_id,
                    source_head,
                    ProposalDecisionDependencyKind.change,
                    change_id,
                    dependency_status,
                    ProposalDecisionDependencyControl.owner_controlled,
                    "includes_decision",
                    source_paths,
                    remediation_kind="review_revoked_change",
                    remediation_command=f"p2p change show {change_id}",
                    severity=(
                        ProposalDecisionImpactSeverity.high
                        if dependency_status
                        == ProposalDecisionDependencyStatus.active
                        else ProposalDecisionImpactSeverity.medium
                    ),
                    capture=capture,
                )
            )
        return result

    def _capture_work(
        self,
        capture: "_ImpactCapture",
        proposal_id: str,
        source_head: str | None,
        affected_changes: set[str],
        items: list[ProposalDecisionImpactItem],
        diagnostics: list[str],
    ) -> set[str]:
        result: set[str] = set()
        root = self.p2p_dir / "work"
        for directory in capture.directories(root, "work_directories"):
            work_id = _id_from_directory(directory, "WORK")
            manifest = directory / "manifest.yml"
            if work_id is None or not manifest.exists():
                continue
            payload = capture.yaml(manifest, diagnostics, required=True)
            if payload is None:
                continue
            source = payload.get("source") if isinstance(payload, Mapping) else None
            direct = _contains_reference(source, proposal_id)
            change_id = (
                str(source.get("change") or "")
                if isinstance(source, Mapping)
                else ""
            )
            if not direct and change_id not in affected_changes:
                continue
            result.add(work_id)
            status = str(payload.get("status") or "unknown")
            dependency_status = (
                ProposalDecisionDependencyStatus.terminal
                if status in _WORK_TERMINAL
                else ProposalDecisionDependencyStatus.active
            )
            items.append(
                self._item(
                    proposal_id,
                    source_head,
                    ProposalDecisionDependencyKind.work,
                    work_id,
                    dependency_status,
                    ProposalDecisionDependencyControl.owner_controlled,
                    "implements_change" if change_id else "references_proposal",
                    (capture.relative(manifest),),
                    remediation_kind="review_revoked_work",
                    remediation_command=f"p2p work show {work_id}",
                    severity=ProposalDecisionImpactSeverity.high,
                    capture=capture,
                )
            )
        return result

    def _capture_specs(
        self,
        capture: "_ImpactCapture",
        proposal_id: str,
        source_head: str | None,
        affected_changes: set[str],
        items: list[ProposalDecisionImpactItem],
        diagnostics: list[str],
    ) -> None:
        root = self.p2p_dir / "outputs" / "software-spec"
        for directory in capture.directories(root, "software_spec_directories"):
            change_id = directory.name
            if change_id not in affected_changes:
                continue
            paths: list[str] = []
            for path in sorted(
                (item for item in directory.iterdir() if item.is_file()),
                key=lambda item: item.name,
            ):
                paths.append(capture.relative(path))
                capture.bytes(path, diagnostics, required=False)
            items.append(
                self._item(
                    proposal_id,
                    source_head,
                    ProposalDecisionDependencyKind.software_spec,
                    change_id,
                    ProposalDecisionDependencyStatus.generated,
                    ProposalDecisionDependencyControl.generated,
                    "generated_from_change",
                    paths,
                    remediation_kind="review_revoked_software_spec",
                    remediation_command=f"p2p spec lifecycle --change {change_id}",
                    severity=ProposalDecisionImpactSeverity.medium,
                    capture=capture,
                )
            )

    def _capture_vertical_evidence(
        self,
        capture: "_ImpactCapture",
        proposal_id: str,
        source_head: str | None,
        items: list[ProposalDecisionImpactItem],
        diagnostics: list[str],
    ) -> None:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "vertical-coverage.yml"
        if not path.exists():
            return
        payload = capture.yaml(path, diagnostics, required=True)
        if payload is None:
            return
        coverage = payload.get("vertical_coverage")
        sections = (
            coverage.get("sections")
            if isinstance(coverage, Mapping)
            else None
        )
        section_ids = tuple(
            sorted(
                {
                    str(section.get("id") or "").strip()
                    for section in sections
                    if isinstance(section, Mapping)
                    and str(section.get("id") or "").strip()
                }
            )
        ) if isinstance(sections, list) else ()
        for section_id in section_ids or ("unclassified",):
            items.append(
                self._item(
                    proposal_id,
                    source_head,
                    ProposalDecisionDependencyKind.vertical_evidence,
                    section_id,
                    ProposalDecisionDependencyStatus.current,
                    ProposalDecisionDependencyControl.owner_controlled,
                    "provides_vertical_evidence",
                    (capture.relative(path),),
                    remediation_kind="review_revoked_vertical_evidence",
                    remediation_command=(
                        f"p2p proposal vertical coverage status {proposal_id}"
                    ),
                    severity=ProposalDecisionImpactSeverity.high,
                    capture=capture,
                )
            )

    def _capture_relations_and_conflicts(
        self,
        capture: "_ImpactCapture",
        proposal_id: str,
        source_head: str | None,
        affected_changes: set[str],
        affected_work: set[str],
        items: list[ProposalDecisionImpactItem],
        diagnostics: list[str],
    ) -> None:
        references = {proposal_id, *affected_changes, *affected_work}
        relation_path = self.p2p_dir / "registries" / "relations.yml"
        if relation_path.exists():
            payload = capture.yaml(relation_path, diagnostics, required=True)
            records = payload.get("relations") if isinstance(payload, Mapping) else None
            if records is not None and not isinstance(records, list):
                diagnostics.append(
                    "P2P370_DECISION_IMPACT_INCOMPLETE: relations registry must "
                    "contain a sequence"
                )
            if isinstance(records, list):
                for index, record in enumerate(records, start=1):
                    if not _contains_any_reference(record, references):
                        continue
                    relation_id = (
                        str(record.get("id") or f"REL-{index:04d}")
                        if isinstance(record, Mapping)
                        else f"REL-{index:04d}"
                    )
                    items.append(
                        self._item(
                            proposal_id,
                            source_head,
                            ProposalDecisionDependencyKind.relation,
                            relation_id,
                            ProposalDecisionDependencyStatus.generated,
                            ProposalDecisionDependencyControl.generated,
                            "records_dependency_relation",
                            (capture.relative(relation_path),),
                            remediation_kind="review_revoked_relation",
                            remediation_command="p2p registry show relations",
                            severity=ProposalDecisionImpactSeverity.medium,
                            capture=capture,
                        )
                    )
        conflict_path = self.p2p_dir / "project" / "conflicts.yml"
        if conflict_path.exists():
            payload = capture.yaml(conflict_path, diagnostics, required=True)
            records = payload.get("conflicts") if isinstance(payload, Mapping) else None
            if records is not None and not isinstance(records, list):
                diagnostics.append(
                    "P2P370_DECISION_IMPACT_INCOMPLETE: conflicts must contain a sequence"
                )
            if isinstance(records, list):
                for index, record in enumerate(records, start=1):
                    if not _contains_any_reference(record, references):
                        continue
                    conflict_id = (
                        str(record.get("id") or f"CONFLICT-{index:03d}")
                        if isinstance(record, Mapping)
                        else f"CONFLICT-{index:03d}"
                    )
                    items.append(
                        self._item(
                            proposal_id,
                            source_head,
                            ProposalDecisionDependencyKind.conflict,
                            conflict_id,
                            ProposalDecisionDependencyStatus.historical,
                            ProposalDecisionDependencyControl.curated,
                            "records_proposal_conflict",
                            (capture.relative(conflict_path),),
                            remediation_kind="review_revoked_conflict",
                            remediation_command="p2p conflict list",
                            severity=ProposalDecisionImpactSeverity.medium,
                            capture=capture,
                        )
                    )

    def _capture_project_views(
        self,
        capture: "_ImpactCapture",
        proposal_id: str,
        source_head: str | None,
        items: list[ProposalDecisionImpactItem],
        diagnostics: list[str],
    ) -> None:
        decisions = self.p2p_dir / "project" / "decisions-map.yml"
        manifest = self.p2p_dir / "project" / "projection-manifest.yml"
        if not decisions.exists():
            return
        payload = capture.yaml(decisions, diagnostics, required=False)
        paths = [capture.relative(decisions)]
        if manifest.exists():
            capture.yaml(manifest, diagnostics, required=False)
            paths.append(capture.relative(manifest))
        if payload is None or not _contains_reference(payload, proposal_id):
            return
        items.append(
            self._item(
                proposal_id,
                source_head,
                ProposalDecisionDependencyKind.project_projection,
                "project_projections",
                ProposalDecisionDependencyStatus.generated,
                ProposalDecisionDependencyControl.generated,
                "projects_active_decision",
                paths,
                remediation_kind="refresh_decision_dependent_projection",
                remediation_command="p2p project refresh",
                severity=ProposalDecisionImpactSeverity.medium,
                capture=capture,
            )
        )
        items.append(
            self._item(
                proposal_id,
                source_head,
                ProposalDecisionDependencyKind.decision_context,
                "decision_context",
                ProposalDecisionDependencyStatus.generated,
                ProposalDecisionDependencyControl.generated,
                "indexes_decision_authority",
                (capture.relative(decisions),),
                remediation_kind="refresh_decision_context",
                remediation_command="p2p context --target " + proposal_id,
                severity=ProposalDecisionImpactSeverity.low,
                capture=capture,
            )
        )

    def _capture_publication(
        self,
        capture: "_ImpactCapture",
        proposal_id: str,
        source_head: str | None,
        affected_changes: set[str],
        items: list[ProposalDecisionImpactItem],
    ) -> None:
        references = {proposal_id, *affected_changes}
        paths = (
            self.root / "outputs" / "latest" / "publication-manifest.yml",
            self.root / "outputs" / "latest" / "project.md",
            self.root / "outputs" / "latest" / "project.curated.md",
        )
        matched: list[str] = []
        for path in paths:
            if not path.exists() or not path.is_file() or path.is_symlink():
                continue
            content = capture.external_bytes(path)
            if any(value.encode("utf-8") in content for value in references):
                matched.append(capture.relative(path))
        if not matched:
            return
        items.append(
            self._item(
                proposal_id,
                source_head,
                ProposalDecisionDependencyKind.publication,
                "publication_packet",
                ProposalDecisionDependencyStatus.generated,
                ProposalDecisionDependencyControl.owner_controlled,
                "publishes_decision_dependent_content",
                matched,
                remediation_kind="review_revoked_publication_source",
                remediation_command="p2p project publish status",
                severity=ProposalDecisionImpactSeverity.medium,
                capture=capture,
            )
        )

    def _capture_freshness(
        self,
        capture: "_ImpactCapture",
        proposal_id: str,
        source_head: str | None,
        has_dependencies: bool,
        items: list[ProposalDecisionImpactItem],
        diagnostics: list[str],
        freshness_status_snapshot: object,
    ) -> None:
        if not has_dependencies:
            return
        if freshness_status_snapshot is _FRESHNESS_NOT_PROVIDED:
            if self.freshness_status is None:
                return
            try:
                status = self.freshness_status()
            except (OSError, ValueError) as exc:
                diagnostics.append(
                    "P2P370_DECISION_IMPACT_INCOMPLETE: freshness status failed: "
                    f"{exc}"
                )
                return
        else:
            status = freshness_status_snapshot
        if status is None:
            return
        state = str(getattr(status, "status", "unknown"))
        items.append(
            self._item(
                proposal_id,
                source_head,
                ProposalDecisionDependencyKind.freshness,
                "derived_freshness",
                (
                    ProposalDecisionDependencyStatus.current
                    if state == "current"
                    else ProposalDecisionDependencyStatus.stale
                ),
                ProposalDecisionDependencyControl.generated,
                "tracks_decision_dependent_derivations",
                (),
                remediation_kind="review_decision_freshness",
                remediation_command="p2p project freshness",
                severity=ProposalDecisionImpactSeverity.low,
                capture=capture,
                additional_fingerprint={"freshness_status": state},
            )
        )

    @staticmethod
    def _item(
        proposal_id: str,
        source_head: str | None,
        kind: ProposalDecisionDependencyKind,
        dependency_id: str,
        status: ProposalDecisionDependencyStatus,
        control: ProposalDecisionDependencyControl,
        relationship: str,
        source_paths,
        *,
        remediation_kind: str,
        remediation_command: str,
        severity: ProposalDecisionImpactSeverity,
        capture: "_ImpactCapture",
        additional_fingerprint: Mapping[str, object] | None = None,
    ) -> ProposalDecisionImpactItem:
        paths = tuple(sorted(dict.fromkeys(str(path) for path in source_paths)))
        source_fingerprint = semantic_sha256(
            {
                "paths": {
                    path: capture.hashes.get(path)
                    for path in paths
                },
                "additional": dict(additional_fingerprint or {}),
            }
        )
        identity = semantic_sha256(
            {
                "policy_version": IMPACT_POLICY_VERSION,
                "proposal_id": proposal_id,
                "source_head_event_id": source_head,
                "dependency_kind": kind.value,
                "dependency_id": dependency_id,
                "relationship": relationship,
            }
        )
        return ProposalDecisionImpactItem(
            impact_id=f"PDI-{identity[:24]}",
            dependency_kind=kind,
            dependency_id=dependency_id,
            dependency_status=status,
            dependency_control=control,
            relationship=relationship,
            authority_effect=(
                "requires_review_after_source_authority_change"
            ),
            source_paths=paths,
            source_fingerprint_sha256=source_fingerprint,
            remediation_kind=remediation_kind,
            remediation_command=remediation_command,
            severity=severity,
        )

    @staticmethod
    def _cursor(snapshot: ProposalDecisionImpactSnapshot, offset: int) -> str:
        binding = semantic_sha256(
            {
                "policy_version": IMPACT_POLICY_VERSION,
                "proposal_id": snapshot.proposal_id,
                "source_head_event_id": snapshot.source_head_event_id,
                "source_fingerprint_sha256": snapshot.source_fingerprint_sha256,
                "offset": offset,
            }
        )[:16]
        return f"PDIC-{offset}-{binding}"

    @classmethod
    def _cursor_offset(
        cls,
        snapshot: ProposalDecisionImpactSnapshot,
        cursor: str | None,
    ) -> int:
        if cursor is None:
            return 0
        match = _CURSOR.fullmatch(cursor)
        if match is None:
            raise ValueError("Invalid decision impact cursor.")
        offset = int(match.group(1))
        if cls._cursor(snapshot, offset) != cursor:
            raise ValueError(
                "Decision impact cursor is stale or belongs to another snapshot."
            )
        return offset


class _ImpactCapture:
    def __init__(self, *, root: Path, p2p_dir: Path) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.atomic_sources: dict[str, bytes | None] = {}
        self.hashes: dict[str, str] = {}
        self.counters: Counter[str] = Counter()

    def directories(self, path: Path, counter: str) -> tuple[Path, ...]:
        self.counters["directory_enumerations"] += 1
        self.counters[counter] += 1
        if not path.exists():
            return ()
        return tuple(
            sorted(
                (
                    item
                    for item in path.iterdir()
                    if item.is_dir() and not item.is_symlink()
                ),
                key=lambda item: item.name,
            )
        )

    def bytes(
        self,
        path: Path,
        diagnostics: list[str],
        *,
        required: bool,
    ) -> bytes | None:
        relative = self.relative(path)
        self.counters["file_reads"] += 1
        if relative in self.hashes:
            self.counters["cache_hits"] += 1
            return self.atomic_sources.get(relative)
        try:
            if not path.is_file() or path.is_symlink():
                raise OSError("not a regular file")
            content = path.read_bytes()
        except OSError as exc:
            if required:
                diagnostics.append(
                    "P2P370_DECISION_IMPACT_INCOMPLETE: cannot read "
                    f"{relative}: {exc}"
                )
            return None
        self.hashes[relative] = hashlib.sha256(content).hexdigest()
        if path.resolve().is_relative_to(self.p2p_dir):
            self.atomic_sources[relative] = content
        return content

    def external_bytes(self, path: Path) -> bytes:
        relative = self.relative(path)
        self.counters["file_reads"] += 1
        content = path.read_bytes()
        self.hashes[relative] = hashlib.sha256(content).hexdigest()
        return content

    def text(
        self,
        path: Path,
        diagnostics: list[str],
        *,
        required: bool,
    ) -> str | None:
        content = self.bytes(path, diagnostics, required=required)
        if content is None:
            return None
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            if required:
                diagnostics.append(
                    "P2P370_DECISION_IMPACT_INCOMPLETE: invalid UTF-8 in "
                    f"{self.relative(path)}: {exc}"
                )
            return None

    def yaml(
        self,
        path: Path,
        diagnostics: list[str],
        *,
        required: bool,
    ) -> dict[str, object] | None:
        text = self.text(path, diagnostics, required=required)
        if text is None:
            return None
        self.counters["yaml_parses"] += 1
        try:
            payload = yaml.load(text, Loader=_UniqueKeyLoader)
        except (yaml.YAMLError, ValueError) as exc:
            if required:
                diagnostics.append(
                    "P2P370_DECISION_IMPACT_INCOMPLETE: invalid YAML in "
                    f"{self.relative(path)}: {exc}"
                )
            return None
        if not isinstance(payload, dict):
            if required:
                diagnostics.append(
                    "P2P370_DECISION_IMPACT_INCOMPLETE: expected mapping in "
                    f"{self.relative(path)}"
                )
            return None
        return payload

    def relative(self, path: Path) -> str:
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"Impact source escapes project root: {path}")
        relative = resolved.relative_to(self.root).as_posix()
        pure = PurePosixPath(relative)
        if not pure.parts or ".." in pure.parts:
            raise ValueError(f"Unsafe impact source path: {path}")
        return relative


def _contains_reference(value: object, target: str) -> bool:
    if isinstance(value, str):
        return value == target
    if isinstance(value, Mapping):
        return any(
            _contains_reference(key, target)
            or _contains_reference(item, target)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_reference(item, target) for item in value)
    return False


def _contains_any_reference(value: object, targets: set[str]) -> bool:
    return any(_contains_reference(value, target) for target in targets)


def _id_from_directory(path: Path, prefix: str) -> str | None:
    match = re.match(rf"^({re.escape(prefix)}-\d{{3,}})(?:-|$)", path.name)
    return match.group(1) if match else None


def _dedupe_items(
    items: list[ProposalDecisionImpactItem],
) -> list[ProposalDecisionImpactItem]:
    result: list[ProposalDecisionImpactItem] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        key = (
            item.dependency_kind.value,
            item.dependency_id,
            item.relationship,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result

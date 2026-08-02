from __future__ import annotations

from dataclasses import replace
from datetime import date
import hashlib
from pathlib import Path
import re
from typing import Mapping

from p2p_engine.core.mutation_preview import MutationPreviewService, semantic_sha256, source_precondition
from p2p_engine.core.portable_verticals import (
    VerticalLifecyclePreview,
    VerticalLifecycleResult,
    VerticalCoordinate,
)
from p2p_engine.core.project_verticals import (
    ProjectDefinitionHistoryEntry,
    ProjectDefinitionOrphan,
    ProjectDefinitionState,
    VerticalDependency,
    VerticalMigrationCandidate,
    VerticalPack,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.project_verticals import (
    ProjectVerticalService,
    project_definition_state_from_payload,
    project_definition_state_payload,
)
from p2p_engine.services.vertical_packages import (
    PortableVerticalPackageService,
    normalize_expected_checksum,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


class VerticalLifecycleService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        vertical_service: ProjectVerticalService,
        package_service: PortableVerticalPackageService,
        atomic_writer: AtomicMutationWriter | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.vertical_service = vertical_service
        self.package_service = package_service
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)

    def install_preview(
        self,
        artifact: Path,
        *,
        expected_checksum: str,
        actor: str = "local",
    ) -> VerticalLifecyclePreview:
        artifact = artifact if artifact.is_absolute() else self.root / artifact
        expected = normalize_expected_checksum(expected_checksum)
        inspection = self.package_service.inspect(artifact, view="effective")
        actual = inspection.artifact_checksum
        if not actual or actual != expected:
            raise ValueError(
                f"P2P_VERTICAL_CHECKSUM_MISMATCH: expected {expected}, got {actual or 'none'}"
            )
        coordinate = inspection.pack.coordinate
        if not coordinate:
            raise ValueError("P2P_VERTICAL_PORTABLE_V2_REQUIRED: artifact has no exact coordinate")
        closure = self._dependency_closure(inspection.pack)
        entries = self.package_service.read_archive(artifact)
        prefix = self._install_prefix(VerticalCoordinate.parse(coordinate))
        candidates = {f"{prefix}/{name}": content for name, content in entries.items()}
        blockers: list[str] = []
        try:
            existing_resolution = self.vertical_service.resolve_pack(coordinate)
        except ValueError:
            existing_resolution = None
        if existing_resolution is not None and existing_resolution.checksum != inspection.semantic_checksum:
            blockers.append(
                f"P2P_VERTICAL_INSTALL_CONFLICT: {coordinate} already resolves to a different semantic checksum"
            )
        target_root = self.root / prefix
        existing = self._installed_files(target_root)
        expected_existing = {
            (target_root / name).relative_to(self.root).as_posix(): content
            for name, content in entries.items()
        }
        if existing and (
            set(existing) != set(expected_existing)
            or any(existing[path] != expected_existing[path] for path in existing if path in expected_existing)
        ):
            blockers.append(
                f"P2P_VERTICAL_INSTALL_CONFLICT: {coordinate} is already installed with different content"
            )
        sources = self._source_preconditions(candidates)
        impact = {
            "artifact_checksum": actual,
            "semantic_checksum": inspection.semantic_checksum,
            "install_prefix": prefix,
            "entries": sorted(entries),
            "dependency_closure": closure,
            "idempotent": bool(existing) and not blockers,
        }
        preview = MutationPreviewService.build(
            operation_id=f"project-vertical-install:{_operation_slug(coordinate)}",
            targets=tuple(candidates),
            actor=actor,
            authority="project_vertical_install",
            sources=sources,
            candidate_semantics=_candidate_semantics(candidates),
            semantic_diff=impact,
            token_context={
                "coordinate": coordinate,
                "artifact_checksum": actual,
                "dependency_closure_sha256": semantic_sha256(closure),
            },
            blockers=blockers,
        )
        return VerticalLifecyclePreview(
            operation="install",
            coordinate=coordinate,
            preview=preview,
            impact=impact,
            blockers=tuple(blockers),
            candidate_files=candidates,
        )

    def install_apply(
        self,
        artifact: Path,
        *,
        expected_checksum: str,
        preview_token: str,
        confirmed: bool,
        actor: str,
    ) -> VerticalLifecycleResult:
        self._require_confirmation(confirmed)
        preview = self.install_preview(
            artifact,
            expected_checksum=expected_checksum,
            actor=actor,
        )
        return self._apply_preview(preview, preview_token=preview_token, actor=actor)

    def adopt_preview(
        self,
        reference: str,
        *,
        actor: str = "local",
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecyclePreview:
        coordinate = str(VerticalCoordinate.parse(reference))
        current = self.vertical_service.project_definition_view()
        blockers: list[str] = []
        if current.state is not None and _has_meaningful_evidence(current.state):
            blockers.append("P2P_VERTICAL_ADOPTION_REQUIRES_MIGRATION: project definition contains evidence")
        candidate = self.vertical_service.render_migration_candidate(
            coordinate,
            actor=actor,
            profile=profile,
            modules=modules,
        )
        candidate = self._with_portable_lock(candidate)
        self.vertical_service.validate_migration_candidate(candidate)
        impact = {
            "from_vertical": current.state.vertical_id if current.state else "",
            "to_vertical": coordinate,
            "definition_reset": True,
            "reconciliation_required": candidate.reconciliation_required,
        }
        return self._governed_preview(
            operation="adopt",
            coordinate=coordinate,
            candidate=candidate,
            actor=actor,
            impact=impact,
            blockers=blockers,
            token_context={"profile": profile, "modules": sorted(modules or [])},
        )

    def adopt_apply(
        self,
        reference: str,
        *,
        preview_token: str,
        confirmed: bool,
        actor: str,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecycleResult:
        self._require_confirmation(confirmed)
        preview = self.adopt_preview(
            reference,
            actor=actor,
            profile=profile,
            modules=modules,
        )
        return self._apply_preview(preview, preview_token=preview_token, actor=actor)

    def migrate_preview(
        self,
        reference: str,
        *,
        actor: str = "local",
        mapping: Mapping[str, object] | None = None,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecyclePreview:
        coordinate = str(VerticalCoordinate.parse(reference))
        current_view = self.vertical_service.project_definition_view()
        if current_view.state is None:
            raise ValueError("P2P_VERTICAL_MIGRATION_REQUIRES_DEFINITION: use adopt for an empty project")
        if not _has_meaningful_evidence(current_view.state):
            raise ValueError("P2P_VERTICAL_MIGRATION_REQUIRES_EVIDENCE: use adopt for an empty definition")
        normalized_mapping, rubric_mapping = _parse_mapping(mapping or {})
        candidate = self.vertical_service.render_migration_candidate(
            coordinate,
            actor=actor,
            profile=profile,
            modules=modules,
            rubric_mapping=rubric_mapping,
        )
        candidate = self._with_portable_lock(candidate)
        migrated, impact, blockers = self._migrated_definition(
            current_view.state,
            candidate,
            normalized_mapping,
            actor=actor,
        )
        candidate.candidate_files[".p2p/project/definition.yml"] = yaml_dump(
            project_definition_state_payload(migrated)
        ).encode("utf-8")
        self.vertical_service.validate_migration_candidate(candidate)
        impact["reconciliation_required"] = candidate.reconciliation_required
        return self._governed_preview(
            operation="migrate",
            coordinate=coordinate,
            candidate=candidate,
            actor=actor,
            impact=impact,
            blockers=blockers,
            token_context={
                "field_mapping_sha256": semantic_sha256(normalized_mapping),
                "rubric_mapping_sha256": semantic_sha256(rubric_mapping),
                "profile": profile,
                "modules": sorted(modules or []),
            },
        )

    def migrate_apply(
        self,
        reference: str,
        *,
        preview_token: str,
        confirmed: bool,
        actor: str,
        mapping: Mapping[str, object] | None = None,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecycleResult:
        self._require_confirmation(confirmed)
        preview = self.migrate_preview(
            reference,
            actor=actor,
            mapping=mapping,
            profile=profile,
            modules=modules,
        )
        return self._apply_preview(preview, preview_token=preview_token, actor=actor)

    def _governed_preview(
        self,
        *,
        operation: str,
        coordinate: str,
        candidate: VerticalMigrationCandidate,
        actor: str,
        impact: dict[str, object],
        blockers: list[str],
        token_context: dict[str, object],
    ) -> VerticalLifecyclePreview:
        sources = self._source_preconditions(candidate.candidate_files)
        preview = MutationPreviewService.build(
            operation_id=f"project-vertical-{operation}:{_operation_slug(coordinate)}",
            targets=tuple(candidate.candidate_files),
            actor=actor,
            authority=f"project_vertical_{operation}",
            sources=sources,
            candidate_semantics=_candidate_semantics(candidate.candidate_files),
            semantic_diff=impact,
            token_context={"coordinate": coordinate, **token_context},
            blockers=blockers,
        )
        return VerticalLifecyclePreview(
            operation=operation,
            coordinate=coordinate,
            preview=preview,
            impact=impact,
            blockers=tuple(blockers),
            candidate_files=candidate.candidate_files,
        )

    def _apply_preview(
        self,
        preview: VerticalLifecyclePreview,
        *,
        preview_token: str,
        actor: str,
    ) -> VerticalLifecycleResult:
        if preview.blockers or preview.preview is None:
            raise ValueError(
                "P2P_VERTICAL_OPERATION_BLOCKED: " + "; ".join(preview.blockers or ("preview is not applicable",))
            )
        if preview.preview.preview_token != preview_token:
            raise ValueError("P2P_VERTICAL_STALE_PREVIEW: preview token does not match current state")
        mutation = self.atomic_writer.apply(
            operation_id=preview.preview.operation_id,
            candidates=preview.candidate_files,
            sources=preview.preview.source_preconditions,
            preview_token=preview_token,
            actor=actor,
        )
        if mutation.status != "applied":
            code = "P2P_VERTICAL_PROJECT_BUSY" if mutation.status == "blocked" else "P2P_VERTICAL_APPLY_FAILED"
            raise ValueError(f"{code}: {mutation.message or mutation.status}")
        return VerticalLifecycleResult(
            operation=preview.operation,
            coordinate=preview.coordinate,
            mutation=mutation,
        )

    def _dependency_closure(self, pack: VerticalPack) -> list[dict[str, str]]:
        closure: list[dict[str, str]] = []
        visited: set[str] = set()

        def visit(dependency: VerticalDependency, stack: tuple[str, ...]) -> None:
            coordinate = str(VerticalCoordinate.parse(dependency.coordinate))
            if coordinate in stack:
                raise ValueError(
                    "P2P_VERTICAL_DEPENDENCY_CYCLE: " + " -> ".join([*stack, coordinate])
                )
            resolved = self.vertical_service.resolve_pack(coordinate)
            expected = dependency.checksum.removeprefix("sha256:")
            if resolved.checksum != expected:
                raise ValueError(
                    f"P2P_VERTICAL_DEPENDENCY_CHECKSUM_MISMATCH: {coordinate} expected {expected}, got {resolved.checksum}"
                )
            if coordinate in visited:
                return
            visited.add(coordinate)
            for child in resolved.pack.manifest.dependencies if resolved.pack.manifest else []:
                visit(child, (*stack, coordinate))
            closure.append({"coordinate": coordinate, "checksum": f"sha256:{resolved.checksum}"})

        for item in pack.manifest.dependencies if pack.manifest else []:
            visit(item, (pack.coordinate,))
        return sorted(closure, key=lambda item: item["coordinate"])

    def _with_portable_lock(self, candidate: VerticalMigrationCandidate) -> VerticalMigrationCandidate:
        resolved = self.vertical_service.resolve_pack(candidate.reference or candidate.vertical_id)
        if not resolved.pack.coordinate:
            return candidate
        lock_path = ".p2p/project/vertical.lock.yml"
        payload = load_yaml(candidate.candidate_files[lock_path])
        if not isinstance(payload, dict) or not isinstance(payload.get("project_vertical_lock"), dict):
            raise ValueError("P2P_VERTICAL_INVALID_LOCK_CANDIDATE: missing lock mapping")
        lock = payload["project_vertical_lock"]
        assert isinstance(lock, dict)
        lock["coordinate"] = resolved.pack.coordinate
        lock["dependencies"] = self._dependency_closure(resolved.pack)
        if resolved.pack.path is not None:
            pack_root = resolved.pack.path.parent if resolved.pack.path.name == "manifest.yml" else resolved.pack.path.parent
            entries = self.package_service.canonical_entries(pack_root)
            artifact_checksum = hashlib.sha256(self.package_service.archive_bytes(entries)).hexdigest()
            lock["artifact_checksum"] = {"algorithm": "sha256", "value": artifact_checksum}
        candidate.candidate_files[lock_path] = yaml_dump(payload).encode("utf-8")
        return candidate

    def _migrated_definition(
        self,
        current: ProjectDefinitionState,
        candidate: VerticalMigrationCandidate,
        mapping: dict[str, str],
        *,
        actor: str,
    ) -> tuple[ProjectDefinitionState, dict[str, object], list[str]]:
        payload = load_yaml(candidate.candidate_files[".p2p/project/definition.yml"])
        if not isinstance(payload, dict):
            raise ValueError("P2P_VERTICAL_INVALID_DEFINITION_CANDIDATE: expected mapping")
        target = project_definition_state_from_payload(payload, path=Path(".p2p/project/definition.yml"))
        target_sections = {section.section_id: section for section in target.sections}
        target_pack = self.vertical_service.resolve_pack(candidate.reference or candidate.vertical_id).pack
        target_fields = {
            f"{section.section_id}.{field.field_id}"
            for section in target_pack.sections
            for field in section.fields
        }
        target_fields.update(
            f"{section.section_id}.summary"
            for section in target_pack.sections
            if not section.fields
        )
        source_fields = {
            f"{section.section_id}.{field_id}": (section, field)
            for section in current.sections
            for field_id, field in section.fields.items()
        }
        blockers: list[str] = []
        used_targets: set[str] = set()
        for source_path, target_path in mapping.items():
            if source_path not in source_fields:
                blockers.append(f"P2P_VERTICAL_INVALID_MAPPING: unknown source field `{source_path}`")
            if target_path not in target_fields:
                blockers.append(f"P2P_VERTICAL_INVALID_MAPPING: unknown target field `{target_path}`")
            if target_path in used_targets:
                blockers.append(f"P2P_VERTICAL_INVALID_MAPPING: duplicate target field `{target_path}`")
            used_targets.add(target_path)
        preserved: list[dict[str, str]] = []
        orphans = list(current.orphans)
        for source_path, (source_section, field) in source_fields.items():
            target_path = mapping.get(source_path, source_path if source_path in target_fields else "")
            if target_path and target_path in target_fields:
                section_id, field_id = target_path.split(".", 1)
                target_section = target_sections[section_id]
                target_section.fields[field_id] = replace(field, field_id=field_id)
                target_section.missing_required_fields = [
                    item for item in target_section.missing_required_fields if item != field_id
                ]
                preserved.append({"from": source_path, "to": target_path})
                continue
            orphans.append(
                _field_orphan(
                    current=current,
                    source_path=source_path,
                    value=field.value,
                    source=field.source,
                    updated_at=field.updated_at,
                    target_vertical=candidate.reference or candidate.vertical_id,
                )
            )
        for source_section in current.sections:
            target_section = target_sections.get(source_section.section_id)
            if target_section is not None:
                target_section.assumptions = list(source_section.assumptions)
                target_section.open_questions = list(source_section.open_questions)
                target_section.blockers = list(source_section.blockers)
                if source_section.status == "blocked" and source_section.blockers:
                    target_section.status = "blocked"
                elif not target_section.missing_required_fields and source_section.status in {"complete", "assumed"}:
                    target_section.status = source_section.status
                elif target_section.fields:
                    target_section.status = "partial"
                continue
            for kind, values in (
                ("assumptions", source_section.assumptions),
                ("open_questions", source_section.open_questions),
                ("blockers", source_section.blockers),
            ):
                if values:
                    orphans.append(
                        _field_orphan(
                            current=current,
                            source_path=f"{source_section.section_id}.{kind}",
                            value=[item.__dict__ for item in values],
                            source="project_definition",
                            updated_at="",
                            target_vertical=candidate.reference or candidate.vertical_id,
                        )
                    )
        migrated = replace(
            target,
            sections=list(target_sections.values()),
            orphans=orphans,
            history=[
                *current.history,
                ProjectDefinitionHistoryEntry(
                    at=date.today().isoformat(),
                    actor=actor,
                    operation="migrate_project_vertical",
                ),
            ],
        )
        impact = {
            "from_vertical": current.vertical_id,
            "to_vertical": candidate.reference or candidate.vertical_id,
            "preserved_fields": preserved,
            "orphaned_values": len(orphans) - len(current.orphans),
            "existing_orphans": len(current.orphans),
            "field_mapping": mapping,
            "added_sections": sorted(set(target_sections) - {item.section_id for item in current.sections}),
            "removed_sections": sorted({item.section_id for item in current.sections} - set(target_sections)),
        }
        return migrated, impact, blockers

    def _source_preconditions(self, candidates: dict[str, bytes]) -> tuple:
        return tuple(
            source_precondition(
                path,
                (self.root / path).read_bytes() if (self.root / path).exists() else None,
            )
            for path in sorted(candidates)
        )

    @staticmethod
    def _install_prefix(coordinate: VerticalCoordinate) -> str:
        return (
            ".p2p/project/verticals/_portable/"
            f"{coordinate.publisher}/{coordinate.vertical_id}/{coordinate.version}"
        )

    def _installed_files(self, target: Path) -> dict[str, bytes]:
        if not target.exists():
            return {}
        if target.is_symlink() or not target.is_dir():
            raise ValueError(f"P2P_VERTICAL_INSTALL_CONFLICT: unsafe existing target `{target}`")
        result: dict[str, bytes] = {}
        for path in target.rglob("*"):
            if path.is_dir():
                if path.is_symlink():
                    raise ValueError(f"P2P_VERTICAL_INSTALL_CONFLICT: linked directory `{path}`")
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"P2P_VERTICAL_INSTALL_CONFLICT: unsafe existing entry `{path}`")
            result[path.relative_to(self.root).as_posix()] = path.read_bytes()
        return result

    @staticmethod
    def _require_confirmation(confirmed: bool) -> None:
        if not confirmed:
            raise ValueError("P2P_VERTICAL_CONFIRMATION_REQUIRED: apply requires --confirm")


def _candidate_semantics(candidates: dict[str, bytes]) -> dict[str, object]:
    return {
        path: {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
        for path, content in candidates.items()
    }


def _operation_slug(coordinate: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", coordinate)


def _has_meaningful_evidence(state: ProjectDefinitionState) -> bool:
    if state.orphans:
        return True
    for section in state.sections:
        if section.assumptions or section.blockers:
            return True
        if section.open_questions and any(question.status != "open" for question in section.open_questions):
            return True
        for field in section.fields.values():
            if field.value not in (None, "", [], {}):
                return True
    return False


def _parse_mapping(payload: Mapping[str, object]) -> tuple[dict[str, str], dict[str, str]]:
    raw_fields = payload.get("field_mapping", payload.get("mappings", {}))
    field_mapping: dict[str, str] = {}
    if isinstance(raw_fields, dict):
        field_mapping = {str(source): str(target) for source, target in raw_fields.items()}
    elif isinstance(raw_fields, list):
        for index, item in enumerate(raw_fields):
            if not isinstance(item, dict):
                raise ValueError(f"P2P_VERTICAL_INVALID_MAPPING: mappings[{index}] must be a mapping")
            source = str(item.get("from") or "")
            target = str(item.get("to") or "")
            if not source or not target:
                raise ValueError(f"P2P_VERTICAL_INVALID_MAPPING: mappings[{index}] requires from and to")
            field_mapping[source] = target
    elif raw_fields not in ({}, None):
        raise ValueError("P2P_VERTICAL_INVALID_MAPPING: field_mapping must be a mapping or list")
    raw_rubrics = payload.get("rubric_mapping", {})
    if not isinstance(raw_rubrics, dict):
        raise ValueError("P2P_VERTICAL_INVALID_MAPPING: rubric_mapping must be a mapping")
    rubric_mapping = {str(source): str(target) for source, target in raw_rubrics.items()}
    return field_mapping, rubric_mapping


def _field_orphan(
    *,
    current: ProjectDefinitionState,
    source_path: str,
    value: object,
    source: str,
    updated_at: str,
    target_vertical: str,
) -> ProjectDefinitionOrphan:
    section_id, field_id = source_path.split(".", 1)
    orphan_id = "ORPH-" + semantic_sha256(
        {
            "source_vertical": current.vertical_id,
            "source_path": source_path,
            "value": value,
            "target_vertical": target_vertical,
        }
    )[:12]
    return ProjectDefinitionOrphan(
        orphan_id=orphan_id,
        source_vertical=current.vertical_id,
        source_section_id=section_id,
        source_field_id=field_id,
        value=value,
        source=source,
        updated_at=updated_at,
        reason="unmapped_during_vertical_migration",
        target_vertical=target_vertical,
    )

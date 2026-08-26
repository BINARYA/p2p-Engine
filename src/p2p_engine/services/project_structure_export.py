from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import re
import shutil
from collections.abc import Callable, Mapping, Sequence

from p2p_engine.core.authority import AuthorityContext, AuthorityEvidence
from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.portable_verticals import VerticalCoordinate, is_semantic_version
from p2p_engine.core.project_domain import (
    ProjectDomainRef,
    normalize_domain_tags,
)
from p2p_engine.core.project_structure import (
    PROJECT_STRUCTURE_CONTRACT,
    ProjectStructure,
    validate_project_structure,
)
from p2p_engine.core.project_structure_export import (
    PROJECT_STRUCTURE_EXPORT_CAPABILITY,
    PROJECT_STRUCTURE_EXPORT_MARKER_CONTRACT,
    PROJECT_STRUCTURE_EXPORT_OPERATION,
    PROJECT_STRUCTURE_EXPORT_OPERATION_ID,
    PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT,
    ProjectStructureExportCounts,
    ProjectStructureExportEligibility,
    ProjectStructureExportPreview,
    ProjectStructureExportResult,
    ProjectStructureExportSource,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.project_structure import (
    PROJECT_STRUCTURE_PATH,
    ProjectStructureService,
)
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso


PROJECT_STRUCTURE_EXPORT_POLICY_VERSION = 1
_LICENSE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._+-]{0,62}[A-Za-z0-9])?$")
_TEXT_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_DISALLOW_DERIVATION_LICENSES = frozenset(
    {
        "all-rights-reserved",
        "cc-by-nd-4.0",
        "cc-by-nc-nd-4.0",
        "no-derivatives",
        "proprietary-no-derivatives",
    }
)


class ProjectStructureExportService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        structure_service: ProjectStructureService,
        vertical_service: ProjectVerticalService,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        drafts: VerticalDraftService | None = None,
        lifecycle: VerticalDraftLifecycleService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.structure_service = structure_service
        self.vertical_service = vertical_service
        self.authority = authority or ProjectAuthorityService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.receipts = receipts or MutationReceiptService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        from p2p_engine.services.vertical_draft_lifecycle import (
            VerticalDraftLifecycleService,
        )
        from p2p_engine.services.vertical_drafts import VerticalDraftService

        self.drafts = drafts or VerticalDraftService(self.root)
        self.lifecycle = lifecycle or VerticalDraftLifecycleService(
            self.root,
            drafts=self.drafts,
        )
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.clock = clock
        self.codec = AuthorityContractCodec()

    def eligibility(self) -> ProjectStructureExportEligibility:
        structure = self.structure_service.show(include_retired=True)
        source, counts, blockers = self._source_counts_and_blockers(structure)
        return ProjectStructureExportEligibility(
            eligible=not blockers,
            source=source,
            counts=counts,
            blockers=tuple(blockers),
        )

    def preview(
        self,
        *,
        publisher: str,
        vertical_id: str,
        version: str,
        name: str,
        license_id: str,
        primary_domain: Mapping[str, object],
        domain_tags: Sequence[str] = (),
        lineage_mode: str,
        parent_coordinate: str = "",
        parent_semantic_checksum: str = "",
        description: str = "",
        actor_id: str = "owner",
        executor_id: str = "",
    ) -> ProjectStructureExportPreview:
        request = self._normalized_request(
            publisher=publisher,
            vertical_id=vertical_id,
            version=version,
            name=name,
            license_id=license_id,
            primary_domain=primary_domain,
            domain_tags=domain_tags,
            lineage_mode=lineage_mode,
            parent_coordinate=parent_coordinate,
            parent_semantic_checksum=parent_semantic_checksum,
            description=description,
        )
        structure = self.structure_service.show(include_retired=True)
        return self._preview_from_structure(
            structure,
            request=request,
            actor_id=actor_id,
            executor_id=executor_id,
        )

    def apply(
        self,
        *,
        publisher: str,
        vertical_id: str,
        version: str,
        name: str,
        license_id: str,
        primary_domain: Mapping[str, object],
        domain_tags: Sequence[str] = (),
        lineage_mode: str,
        expected_structure_revision: int,
        expected_structure_checksum: str,
        preview_token: str,
        operation_key: str,
        materialization_target: Path,
        package_output: Path,
        confirm: bool,
        parent_coordinate: str = "",
        parent_semantic_checksum: str = "",
        description: str = "",
        actor_id: str = "owner",
        executor_id: str = "",
        executor_kind: str = "person",
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
    ) -> ProjectStructureExportResult:
        if not confirm:
            raise ValueError("P2P_STRUCTURE_EXPORT_CONFIRM_REQUIRED: pass --confirm to export")
        validate_idempotency_key(operation_key)
        request = self._normalized_request(
            publisher=publisher,
            vertical_id=vertical_id,
            version=version,
            name=name,
            license_id=license_id,
            primary_domain=primary_domain,
            domain_tags=domain_tags,
            lineage_mode=lineage_mode,
            parent_coordinate=parent_coordinate,
            parent_semantic_checksum=parent_semantic_checksum,
            description=description,
        )
        expected_checksum = _checksum(expected_structure_checksum, "expected_structure_checksum")
        executor = executor_id or actor_id
        fingerprint = self.receipts.fingerprint(
            operation=PROJECT_STRUCTURE_EXPORT_OPERATION,
            actor=executor,
            preview_token=preview_token,
            semantic_inputs={
                "policy_version": PROJECT_STRUCTURE_EXPORT_POLICY_VERSION,
                "request": request,
                "expected_structure_revision": expected_structure_revision,
                "expected_structure_checksum": expected_checksum,
            },
        )
        replay = self.receipts.replay(
            idempotency_key=operation_key,
            request_fingerprint_sha256=fingerprint,
        )
        if replay is not None:
            evidence = self._replay_authority(
                replay.authority,
                actor_id=actor_id,
                executor_id=executor,
                executor_kind=executor_kind,
                authority_context=authority_context,
                channel=channel,
                consent_id=consent_id,
            )
            return self._result_from_receipt(
                replay.result,
                preview_token=preview_token,
                actor=executor,
                status="already_applied",
                authority=evidence,
            )

        _context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor,
            executor_kind=executor_kind,
            required_capabilities=(PROJECT_STRUCTURE_EXPORT_CAPABILITY,),
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        structure = self.structure_service.show(include_retired=True)
        if (
            structure.revision != expected_structure_revision
            or structure.checksum != expected_checksum
        ):
            raise ValueError(
                "P2P_STRUCTURE_EXPORT_STALE_SOURCE: expected structure "
                f"{expected_structure_revision}/{expected_checksum}, current is "
                f"{structure.revision}/{structure.checksum}"
            )
        preview = self._preview_from_structure(
            structure,
            request=request,
            actor_id=actor_id,
            executor_id=executor,
        )
        if preview.preview.preview_token != preview_token:
            raise ValueError("P2P_STRUCTURE_EXPORT_STALE_PREVIEW: preview token does not match current state")
        if preview.blockers:
            raise ValueError(
                "P2P_STRUCTURE_EXPORT_BLOCKED: " + "; ".join(preview.blockers)
            )
        materialization_target = self._safe_destination(
            materialization_target,
            field="materialization_target",
            require_suffix="",
        )
        package_output = self._safe_destination(
            package_output,
            field="package_output",
            require_suffix=".p2pv",
        )
        draft_id = _draft_id_for_operation(operation_key)
        created_draft = False
        created_materialization = not materialization_target.exists()
        created_package = not package_output.exists()
        try:
            draft = self._ensure_draft(
                draft_id,
                dict(preview.draft_document),
                source=preview.source,
            )
            created_draft = draft.operation == "create"
            draft_view = self._ensure_materialized(
                draft_id,
                target=materialization_target,
            )
            draft_view = self._ensure_validated(draft_id)
            draft_view = self._ensure_packaged(draft_id, output=package_output)
            package = draft_view.evidence.package or {}
            semantic_checksum = _checksum(package.get("semantic_checksum"), "package.semantic_checksum")
            artifact_checksum = _checksum(package.get("artifact_checksum"), "package.artifact_checksum")
            result_summary = self._result_summary(
                status="applied",
                source=preview.source,
                request=request,
                lineage=preview.lineage,
                domain_metadata=preview.domain_metadata,
                draft_id=draft_id,
                draft_revision=draft_view.state.revision,
                draft_document_hash=draft_view.state.document_hash,
                semantic_checksum=semantic_checksum,
                artifact_checksum=artifact_checksum,
                artifact_size=int(package.get("size") or 0),
                artifact_entries=tuple(str(item) for item in package.get("entries", ())),
                marker_path=self._marker_path(operation_key),
                operation_key_sha256=idempotency_key_sha256(operation_key),
            )
            marker = self._marker_bytes(
                result_summary,
                authority=evidence,
                request_fingerprint_sha256=fingerprint,
            )
            marker_path = self._marker_path(operation_key)
            receipt_path, receipt_content, _ = self.receipts.prepare(
                idempotency_key=operation_key,
                operation=PROJECT_STRUCTURE_EXPORT_OPERATION,
                actor=executor,
                request_fingerprint_sha256=fingerprint,
                preview_token=preview_token,
                result=result_summary,
                candidates={marker_path: marker},
                authority=evidence,
            )
            sources = (
                source_precondition(
                    PROJECT_STRUCTURE_PATH,
                    self.structure_service.path.read_bytes(),
                ),
                source_precondition(marker_path, None),
                source_precondition(receipt_path, None),
            )
            mutation = self.atomic_writer.apply(
                operation_id="project-structure-export-apply",
                candidates={marker_path: marker, receipt_path: receipt_content},
                sources=sources,
                preview_token=preview_token,
                actor=executor,
            )
            if mutation.status != "applied":
                raise ValueError(
                    "P2P_STRUCTURE_EXPORT_RECEIPT_FAILED: "
                    + (mutation.message or mutation.status)
                )
            mutation = replace(
                mutation,
                changed_paths=tuple(path for path in mutation.changed_paths if path != receipt_path),
                final_physical_hashes={
                    path: digest
                    for path, digest in mutation.final_physical_hashes.items()
                    if path != receipt_path
                },
            )
            return ProjectStructureExportResult(
                status="applied",
                coordinate=str(request["coordinate"]),
                source=preview.source,
                lineage=preview.lineage,
                domain_metadata=preview.domain_metadata,
                draft_id=draft_id,
                draft_revision=draft_view.state.revision,
                draft_document_hash=draft_view.state.document_hash,
                semantic_checksum=semantic_checksum,
                artifact_checksum=artifact_checksum,
                artifact_size=int(package.get("size") or 0),
                artifact_entries=tuple(str(item) for item in package.get("entries", ())),
                marker_path=marker_path,
                operation_key_sha256=idempotency_key_sha256(operation_key),
                mutation=mutation,
                authority=evidence,
                materialization_target=materialization_target,
                package_output=package_output,
            )
        except Exception:
            self._cleanup_partial(
                draft_id=draft_id,
                remove_draft=created_draft,
                materialization_target=materialization_target,
                remove_materialization=created_materialization,
                package_output=package_output,
                remove_package=created_package,
            )
            raise

    def _preview_from_structure(
        self,
        structure: ProjectStructure,
        *,
        request: Mapping[str, object],
        actor_id: str,
        executor_id: str,
    ) -> ProjectStructureExportPreview:
        source, counts, blockers = self._source_counts_and_blockers(structure)
        lineage, lineage_blockers = self._lineage(structure, request)
        blockers.extend(lineage_blockers)
        document = self._document(structure, request=request, lineage=lineage)
        try:
            from p2p_engine.services.vertical_drafts import (
                normalize_vertical_draft_document,
                vertical_draft_document_hash,
            )

            normalized = normalize_vertical_draft_document(document)
            document_hash = vertical_draft_document_hash(normalized)
        except ValueError as exc:
            normalized = document
            document_hash = "0" * 64
            blockers.append(str(exc))
        validation = self.drafts.assess(
            state=_draft_state_stub(normalized, document_hash),
            evidence=_draft_evidence_stub(document_hash),
        )
        blockers.extend(
            f"{item.code}: {item.field}: {item.message}"
            for item in validation.diagnostics
            if item.severity == "error"
        )
        blockers = sorted(set(blockers))
        preview = MutationPreviewService.build(
            operation_id=f"project-structure-export:{_operation_slug(str(request['coordinate']))}",
            targets=("vertical_draft_document", "portable_vertical_package"),
            actor=executor_id or actor_id,
            authority="project_vertical_export_preview_read_only",
            sources=(
                source_precondition(
                    PROJECT_STRUCTURE_PATH,
                    self.structure_service.path.read_bytes(),
                ),
            ),
            candidate_semantics={
                "vertical_draft_document": normalized,
                "export_request": dict(request),
            },
            semantic_diff={
                "operation": PROJECT_STRUCTURE_EXPORT_OPERATION,
                "coordinate": request["coordinate"],
                "source": source.to_dict(),
                "counts": counts.to_dict(),
                "lineage": lineage,
                "domain_metadata": request["domain_metadata"],
                "draft_document_hash": document_hash,
            },
            token_context={
                "policy_version": PROJECT_STRUCTURE_EXPORT_POLICY_VERSION,
                "structure_revision": source.revision,
                "structure_checksum": source.checksum,
                "active_semantic_hash": source.active_semantic_hash,
                "lineage_mode": request["lineage_mode"],
                "coordinate": request["coordinate"],
            },
            blockers=blockers,
        )
        return ProjectStructureExportPreview(
            source=source,
            counts=counts,
            coordinate=str(request["coordinate"]),
            lineage=lineage,
            domain_metadata=dict(request["domain_metadata"]),  # type: ignore[arg-type]
            draft_document_hash=document_hash,
            draft_document=normalized,
            preview=preview,
            blockers=tuple(blockers),
        )

    def _source_counts_and_blockers(
        self,
        structure: ProjectStructure,
    ) -> tuple[ProjectStructureExportSource, ProjectStructureExportCounts, list[str]]:
        validate_project_structure(structure)
        active_section_ids = {
            item.section_id for item in structure.sections if item.lifecycle == "active"
        }
        active = {
            "sections": len(active_section_ids),
            "fields": len(
                [
                    item
                    for item in structure.fields
                    if item.lifecycle == "active" and item.section_id in active_section_ids
                ]
            ),
            "questions": len(
                [
                    item
                    for item in structure.questions
                    if item.lifecycle == "active" and item.section_id in active_section_ids
                ]
            ),
            "criteria": len(
                [
                    item
                    for item in structure.criteria
                    if item.lifecycle == "active"
                    and item.enabled
                    and item.section_id in active_section_ids
                ]
            ),
            "artifacts": len([item for item in structure.artifacts if item.lifecycle == "active"]),
        }
        excluded_retired = {
            "sections": len([item for item in structure.sections if item.lifecycle == "retired"]),
            "fields": len([item for item in structure.fields if item.lifecycle == "retired"]),
            "questions": len([item for item in structure.questions if item.lifecycle == "retired"]),
            "criteria": len([item for item in structure.criteria if item.lifecycle == "retired"]),
            "artifacts": len([item for item in structure.artifacts if item.lifecycle == "retired"]),
        }
        excluded_disabled = {
            "criteria": len(
                [
                    item
                    for item in structure.criteria
                    if item.lifecycle == "active" and not item.enabled
                ]
            )
        }
        source = ProjectStructureExportSource(
            structure_id=structure.structure_id,
            revision=structure.revision,
            checksum=structure.checksum,
            active_semantic_hash=semantic_sha256(_active_structure_payload(structure)),
            origin=structure.origin.to_dict(),
        )
        blockers: list[str] = []
        if not active_section_ids:
            blockers.append("P2P_STRUCTURE_EXPORT_EMPTY: active structure has no sections")
        return (
            source,
            ProjectStructureExportCounts(
                active=active,
                excluded_retired=excluded_retired,
                excluded_disabled=excluded_disabled,
            ),
            blockers,
        )

    def _normalized_request(
        self,
        *,
        publisher: str,
        vertical_id: str,
        version: str,
        name: str,
        license_id: str,
        primary_domain: Mapping[str, object],
        domain_tags: Sequence[str],
        lineage_mode: str,
        parent_coordinate: str,
        parent_semantic_checksum: str,
        description: str,
    ) -> dict[str, object]:
        coordinate = VerticalCoordinate.parse(f"{publisher}/{vertical_id}@{version}")
        if not is_semantic_version(version):
            raise ValueError("P2P_STRUCTURE_EXPORT_INVALID_METADATA: version must be semantic")
        license_text = str(license_id or "").strip()
        if not _LICENSE.fullmatch(license_text):
            raise ValueError("P2P_STRUCTURE_EXPORT_INVALID_METADATA: license is unsafe")
        display_name = _bounded_text(name, "name", 200)
        description_text = _bounded_text(
            description
            or f"Reusable vertical exported from project structure for {display_name}.",
            "description",
            2000,
        )
        primary = ProjectDomainRef.from_mapping(primary_domain)
        tags = normalize_domain_tags(list(domain_tags))
        mode = str(lineage_mode or "").strip().lower()
        if mode not in {"derived", "independent"}:
            raise ValueError(
                "P2P_STRUCTURE_EXPORT_INVALID_LINEAGE: lineage mode must be derived or independent"
            )
        checksum = (
            _checksum(parent_semantic_checksum, "parent_semantic_checksum")
            if parent_semantic_checksum
            else ""
        )
        parent = str(VerticalCoordinate.parse(parent_coordinate)) if parent_coordinate else ""
        if (parent and not checksum) or (checksum and not parent):
            raise ValueError(
                "P2P_STRUCTURE_EXPORT_INVALID_LINEAGE: parent coordinate and checksum must be supplied together"
            )
        return {
            "coordinate": str(coordinate),
            "identity": {
                "publisher": coordinate.publisher,
                "id": coordinate.vertical_id,
                "version": coordinate.version,
                "license": license_text,
            },
            "name": display_name,
            "description": description_text,
            "lineage_mode": mode,
            "parent": (
                {"coordinate": parent, "semantic_checksum": checksum}
                if parent and checksum
                else None
            ),
            "domain_metadata": {
                "primary_domain": primary.to_dict(),
                "domain_tags": list(tags),
            },
        }

    def _lineage(
        self,
        structure: ProjectStructure,
        request: Mapping[str, object],
    ) -> tuple[dict[str, object], list[str]]:
        mode = str(request["lineage_mode"])
        parent = request.get("parent")
        blockers: list[str] = []
        eligible = _eligible_parent(structure)
        if mode == "independent":
            return {
                "mode": "independent",
                "forked_from": None,
                "previous_release": None,
                "legal_attribution_preserved": True,
            }, blockers
        if parent is None:
            parent = eligible
        if parent is None:
            blockers.append(
                "P2P_STRUCTURE_EXPORT_PARENT_REQUIRED: derived export requires a vertical-release project origin"
            )
            return {
                "mode": "derived",
                "forked_from": None,
                "previous_release": None,
                "legal_attribution_preserved": True,
            }, blockers
        parent_ref = _reference(parent)
        if eligible is None or parent_ref != eligible:
            blockers.append(
                "P2P_STRUCTURE_EXPORT_PARENT_NOT_ELIGIBLE: parent must match the project structure origin"
            )
        try:
            resolved = self.vertical_service.resolve_pack(parent_ref["coordinate"])
            if resolved.checksum != parent_ref["semantic_checksum"]:
                blockers.append(
                    "P2P_STRUCTURE_EXPORT_PARENT_CHECKSUM_MISMATCH: parent checksum does not match the installed release"
                )
            license_id = (
                resolved.pack.manifest.license_id
                if resolved.pack.manifest is not None
                else ""
            )
            if not _license_allows_derivation(license_id):
                blockers.append(
                    "P2P_STRUCTURE_EXPORT_PARENT_LICENSE_FORBIDS_DERIVATION: parent license does not allow derivation"
                )
        except ValueError:
            blockers.append(
                "P2P_STRUCTURE_EXPORT_PARENT_UNAVAILABLE: parent release must be resolvable offline"
            )
        return {
            "mode": "derived",
            "forked_from": parent_ref,
            "previous_release": None,
            "legal_attribution_preserved": True,
        }, blockers

    def _document(
        self,
        structure: ProjectStructure,
        *,
        request: Mapping[str, object],
        lineage: Mapping[str, object],
    ) -> dict[str, object]:
        active_section_ids = {
            item.section_id for item in structure.sections if item.lifecycle == "active"
        }
        fields_by_section: dict[str, list[dict[str, object]]] = {
            section_id: [] for section_id in active_section_ids
        }
        for item in sorted(structure.fields, key=lambda value: (value.section_id, value.order, value.field_id)):
            if item.lifecycle != "active" or item.section_id not in active_section_ids:
                continue
            fields_by_section[item.section_id].append(
                {
                    "id": item.field_id,
                    "label": item.label,
                    "required": item.required,
                    "question": item.description,
                    "assisted_answer": "",
                    "completion_criteria": [],
                    "common_mistakes": [],
                    "suggested_artifacts": [],
                    "maturity_gates": [],
                }
            )
        sections = [
            {
                "id": item.section_id,
                "title": item.title,
                "purpose": item.description or item.title,
                "required": item.required,
                "priority": (index + 1) * 10,
                "fields": fields_by_section[item.section_id],
                "completion_policy": {},
            }
            for index, item in enumerate(
                sorted(
                    [item for item in structure.sections if item.lifecycle == "active"],
                    key=lambda value: (value.order, value.section_id),
                )
            )
        ]
        rubrics = [
            {
                "id": item.criterion_id,
                "title": item.title,
                "section_id": item.section_id,
                "required": item.required,
                "keywords": list(item.keywords),
                "weight": item.weight,
                "evaluation": item.evaluation,
            }
            for item in sorted(
                structure.criteria,
                key=lambda value: (value.section_id, value.order, value.criterion_id),
            )
            if item.lifecycle == "active"
            and item.enabled
            and item.section_id in active_section_ids
        ]
        questions = [
            {
                "id": item.question_id,
                "section_id": item.section_id,
                "priority": item.priority,
                "question": item.prompt,
                "rationale": item.rationale,
            }
            for item in sorted(
                structure.questions,
                key=lambda value: (value.section_id, value.order, value.question_id),
            )
            if item.lifecycle == "active" and item.section_id in active_section_ids
        ]
        artifacts = []
        for item in sorted(structure.artifacts, key=lambda value: (value.order, value.artifact_id)):
            if item.lifecycle != "active":
                continue
            artifacts.append(
                {
                    "id": item.artifact_id,
                    "title": item.title,
                    "section_ids": [
                        section_id
                        for section_id in item.section_ids
                        if section_id in active_section_ids
                    ],
                    "required": item.required,
                }
            )
        forked_from = lineage.get("forked_from")
        return {
            "contract_version": "p2p-vertical-draft/v1",
            "identity": dict(request["identity"]),  # type: ignore[arg-type]
            "name": request["name"],
            "description": request["description"],
            "visibility": "private",
            "extends": None,
            "lineage": {
                "forked_from": forked_from if isinstance(forked_from, Mapping) else None,
                "previous_release": None,
            },
            "dependencies": [],
            "sections": sections,
            "rubrics": rubrics,
            "questions": questions,
            "artifacts": artifacts,
            "profiles": {"enabled": [], "definitions": []},
            "modules": {"enabled": [], "definitions": []},
            "examples": [],
            "source_attribution": {
                "source_kind": "project_structure_export",
                "project_structure": {
                    "contract": PROJECT_STRUCTURE_CONTRACT,
                    "structure_id": structure.structure_id,
                    "revision": structure.revision,
                    "checksum": structure.checksum,
                    "active_semantic_hash": semantic_sha256(
                        _active_structure_payload(structure)
                    ),
                },
                "project_structure_origin": structure.origin.to_dict(),
                "lineage_mode": lineage["mode"],
                "legal_attribution_preserved": True,
            },
            "compatibility": {
                "generated_from": "project_structure_export",
                "source_structure_contract": PROJECT_STRUCTURE_CONTRACT,
            },
            "domain_metadata": dict(request["domain_metadata"]),  # type: ignore[arg-type]
        }

    def _ensure_draft(
        self,
        draft_id: str,
        document: dict[str, object],
        *,
        source: ProjectStructureExportSource,
    ):
        from p2p_engine.core.vertical_drafts import VerticalDraftOrigin
        from p2p_engine.services.vertical_drafts import (
            VerticalDraftService,
            normalize_vertical_draft_document,
            vertical_draft_document_hash,
        )

        deterministic_drafts = VerticalDraftService(
            self.root,
            catalog=self.drafts.catalog,
            draft_root=self.drafts.draft_root,
            id_factory=lambda: draft_id,
        )
        try:
            current = deterministic_drafts.inspect(draft_id)
        except ValueError as exc:
            if not str(exc).startswith("P2P_VERTICAL_DRAFT_NOT_FOUND"):
                raise
            return deterministic_drafts.create_from_document(
                document,
                origin=VerticalDraftOrigin(
                    kind="project_structure_export",
                    semantic_checksum=source.active_semantic_hash,
                ),
            )
        normalized = normalize_vertical_draft_document(document)
        if current.state.document_hash != vertical_draft_document_hash(normalized):
            raise ValueError(
                "P2P_STRUCTURE_EXPORT_DRAFT_CONFLICT: deterministic draft ID already exists with different content"
            )
        from p2p_engine.core.vertical_drafts import VerticalDraftOperationResult

        return VerticalDraftOperationResult(
            operation="replay",
            draft=current,
            changed_paths=(),
        )

    def _ensure_materialized(self, draft_id: str, *, target: Path):
        view = self.drafts.inspect(draft_id)
        materialization = view.evidence.materialization or {}
        if (
            materialization.get("revision") == view.state.revision
            and materialization.get("document_hash") == view.state.document_hash
            and Path(str(materialization.get("target") or "")).resolve(strict=False)
            == target.resolve(strict=False)
            and target.exists()
        ):
            return view
        return self.lifecycle.materialize(draft_id, target).draft

    def _ensure_validated(self, draft_id: str):
        view = self.drafts.inspect(draft_id)
        validation = view.evidence.validation or {}
        if (
            validation.get("revision") == view.state.revision
            and validation.get("document_hash") == view.state.document_hash
            and validation.get("valid") is True
        ):
            return view
        return self.lifecycle.validate(draft_id).draft

    def _ensure_packaged(self, draft_id: str, *, output: Path):
        view = self.drafts.inspect(draft_id)
        package = view.evidence.package or {}
        if (
            package.get("revision") == view.state.revision
            and package.get("document_hash") == view.state.document_hash
            and Path(str(package.get("path") or "")).resolve(strict=False)
            == output.resolve(strict=False)
            and output.exists()
        ):
            return view
        return self.lifecycle.package(draft_id, output).draft

    def _result_summary(
        self,
        *,
        status: str,
        source: ProjectStructureExportSource,
        request: Mapping[str, object],
        lineage: Mapping[str, object],
        domain_metadata: Mapping[str, object],
        draft_id: str,
        draft_revision: int,
        draft_document_hash: str,
        semantic_checksum: str,
        artifact_checksum: str,
        artifact_size: int,
        artifact_entries: tuple[str, ...],
        marker_path: str,
        operation_key_sha256: str,
    ) -> dict[str, object]:
        return {
            "contract": PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT,
            "status": status,
            "operation": PROJECT_STRUCTURE_EXPORT_OPERATION,
            "operation_id": PROJECT_STRUCTURE_EXPORT_OPERATION_ID,
            "request": dict(request),
            "source": source.to_dict(),
            "lineage": dict(lineage),
            "domain_metadata": dict(domain_metadata),
            "draft": {
                "draft_id": draft_id,
                "revision": draft_revision,
                "document_hash": draft_document_hash,
            },
            "package": {
                "coordinate": request["coordinate"],
                "semantic_checksum": semantic_checksum,
                "artifact_checksum": artifact_checksum,
                "size": artifact_size,
                "entries": sorted(artifact_entries),
            },
            "receipt": {
                "operation_key_sha256": operation_key_sha256,
                "marker_path": marker_path,
                "capability": PROJECT_STRUCTURE_EXPORT_CAPABILITY,
            },
            "remote_publication": False,
            "publisher_ownership_granted": False,
            "changed_paths": [marker_path],
        }

    def _marker_bytes(
        self,
        result: Mapping[str, object],
        *,
        authority: AuthorityEvidence,
        request_fingerprint_sha256: str,
    ) -> bytes:
        return yaml_dump(
            {
                "project_structure_export": {
                    "contract": PROJECT_STRUCTURE_EXPORT_MARKER_CONTRACT,
                    "completed_at": self.clock(),
                    "request_fingerprint_sha256": request_fingerprint_sha256,
                    "authority_context_sha256": authority.authority_context_sha256,
                    "result": dict(result),
                }
            }
        ).encode("ascii")

    def _marker_path(self, operation_key: str) -> str:
        return (
            ".p2p/.internal/project-structure-exports/"
            f"{idempotency_key_sha256(operation_key)}.yml"
        )

    def _replay_authority(
        self,
        raw: Mapping[str, object] | None,
        *,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        channel: str,
        consent_id: str | None,
    ) -> AuthorityEvidence:
        if raw is None:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: export receipt lacks authority evidence")
        evidence = self.codec.evidence_from_mapping(raw)
        if (
            evidence.subject.identity_id != actor_id
            or evidence.executor.identity_id != executor_id
            or evidence.executor.kind.value != executor_kind
            or evidence.channel != channel
            or evidence.consent_id != consent_id
        ):
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: export authority differs")
        if authority_context is not None and authority_context.digest_sha256 != evidence.authority_context_sha256:
            raise ValueError("P2P_IDEMPOTENCY_CONFLICT: authority context differs")
        return evidence

    def _result_from_receipt(
        self,
        result: Mapping[str, object],
        *,
        preview_token: str,
        actor: str,
        status: str,
        authority: AuthorityEvidence,
    ) -> ProjectStructureExportResult:
        source = result.get("source")
        draft = result.get("draft")
        package = result.get("package")
        receipt = result.get("receipt")
        if not isinstance(source, Mapping) or not isinstance(draft, Mapping) or not isinstance(package, Mapping) or not isinstance(receipt, Mapping):
            raise ValueError("P2P_IDEMPOTENCY_RECEIPT_CORRUPT: export result is invalid")
        marker_path = str(receipt.get("marker_path") or "")
        return ProjectStructureExportResult(
            status=status,
            coordinate=str(package.get("coordinate") or ""),
            source=ProjectStructureExportSource(
                structure_id=str(source.get("structure_id") or ""),
                revision=int(source.get("revision") or 0),
                checksum=str(source.get("checksum") or ""),
                active_semantic_hash=str(source.get("active_semantic_hash") or ""),
                origin=source.get("origin") if isinstance(source.get("origin"), Mapping) else {},
            ),
            lineage=result.get("lineage") if isinstance(result.get("lineage"), Mapping) else {},
            domain_metadata=(
                result.get("domain_metadata")
                if isinstance(result.get("domain_metadata"), Mapping)
                else {}
            ),
            draft_id=str(draft.get("draft_id") or ""),
            draft_revision=int(draft.get("revision") or 0),
            draft_document_hash=str(draft.get("document_hash") or ""),
            semantic_checksum=str(package.get("semantic_checksum") or ""),
            artifact_checksum=str(package.get("artifact_checksum") or ""),
            artifact_size=int(package.get("size") or 0),
            artifact_entries=tuple(str(item) for item in package.get("entries", ())),
            marker_path=marker_path,
            operation_key_sha256=str(receipt.get("operation_key_sha256") or ""),
            mutation=MutationResult(
                status=status,
                operation_id=PROJECT_STRUCTURE_EXPORT_OPERATION_ID,
                changed_paths=(marker_path,),
                preview_token=preview_token,
                actor=actor,
                message="Project structure export was already applied with this operation key.",
            ),
            authority=authority,
        )

    def _safe_destination(
        self,
        value: Path,
        *,
        field: str,
        require_suffix: str,
    ) -> Path:
        path = value if value.is_absolute() else self.root / value
        resolved = path.resolve(strict=False)
        if resolved == self.root or resolved == self.p2p_dir or resolved.is_relative_to(self.p2p_dir):
            raise ValueError(f"P2P_STRUCTURE_EXPORT_DESTINATION_UNSAFE: {field} cannot target .p2p")
        if require_suffix and resolved.suffix.lower() != require_suffix:
            raise ValueError(
                f"P2P_STRUCTURE_EXPORT_DESTINATION_UNSAFE: {field} must end with {require_suffix}"
            )
        current = resolved.parent
        while current != current.parent:
            if current.exists() and current.is_symlink():
                raise ValueError(
                    f"P2P_STRUCTURE_EXPORT_DESTINATION_UNSAFE: {field} parent is a symlink"
                )
            if current == self.root:
                break
            current = current.parent
        return resolved

    def _cleanup_partial(
        self,
        *,
        draft_id: str,
        remove_draft: bool,
        materialization_target: Path,
        remove_materialization: bool,
        package_output: Path,
        remove_package: bool,
    ) -> None:
        if remove_package:
            package_output.unlink(missing_ok=True)
        if remove_materialization and materialization_target.exists():
            shutil.rmtree(materialization_target, ignore_errors=True)
        if remove_draft:
            shutil.rmtree(self.drafts.draft_root / draft_id, ignore_errors=True)


def _active_structure_payload(structure: ProjectStructure) -> dict[str, object]:
    active_section_ids = {
        item.section_id for item in structure.sections if item.lifecycle == "active"
    }
    return {
        "structure_id": structure.structure_id,
        "sections": [
            item.to_dict()
            for item in sorted(structure.sections, key=lambda value: (value.order, value.section_id))
            if item.lifecycle == "active"
        ],
        "fields": [
            item.to_dict()
            for item in sorted(structure.fields, key=lambda value: (value.section_id, value.order, value.field_id))
            if item.lifecycle == "active" and item.section_id in active_section_ids
        ],
        "questions": [
            item.to_dict()
            for item in sorted(structure.questions, key=lambda value: (value.section_id, value.order, value.question_id))
            if item.lifecycle == "active" and item.section_id in active_section_ids
        ],
        "criteria": [
            item.semantic_payload()
            for item in sorted(structure.criteria, key=lambda value: (value.section_id, value.order, value.criterion_id))
            if item.lifecycle == "active"
            and item.enabled
            and item.section_id in active_section_ids
        ],
        "artifacts": [
            item.to_dict()
            for item in sorted(structure.artifacts, key=lambda value: (value.order, value.artifact_id))
            if item.lifecycle == "active"
        ],
    }


def _eligible_parent(structure: ProjectStructure) -> dict[str, str] | None:
    origin = structure.origin
    if origin.kind != "vertical_release" or not origin.checksum:
        return None
    return {
        "coordinate": str(VerticalCoordinate.parse(origin.identity)),
        "semantic_checksum": _checksum(origin.checksum, "origin.checksum"),
    }


def _reference(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_STRUCTURE_EXPORT_INVALID_LINEAGE: parent must be a mapping")
    return {
        "coordinate": str(VerticalCoordinate.parse(str(value.get("coordinate") or ""))),
        "semantic_checksum": _checksum(value.get("semantic_checksum"), "parent.semantic_checksum"),
    }


def _checksum(value: object, field: str) -> str:
    text = str(value or "").strip().lower().removeprefix("sha256:")
    if re.fullmatch(r"[0-9a-f]{64}", text) is None:
        raise ValueError(f"P2P_STRUCTURE_EXPORT_INVALID_CHECKSUM: {field} must be SHA-256")
    return text


def _license_allows_derivation(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized not in _DISALLOW_DERIVATION_LICENSES and "-nd" not in normalized


def _bounded_text(value: object, field: str, maximum_bytes: int) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text or len(text.encode("utf-8")) > maximum_bytes or _TEXT_CONTROL.search(text):
        raise ValueError(f"P2P_STRUCTURE_EXPORT_INVALID_METADATA: {field} is empty or unsafe")
    return text


def _draft_id_for_operation(operation_key: str) -> str:
    digest = hashlib.sha256(
        ("p2p-project-structure-export:" + operation_key).encode("utf-8")
    ).hexdigest()
    return "VDRAFT-" + digest[:20].upper()


def _operation_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80]


def _draft_state_stub(document: Mapping[str, object], document_hash: str):
    from p2p_engine.core.vertical_drafts import VerticalDraftOrigin, VerticalDraftState

    return VerticalDraftState(
        draft_id="VDRAFT-0000000000000000",
        revision=1,
        document_hash=document_hash,
        status="drafted",
        origin=VerticalDraftOrigin(kind="project_structure_export"),
        document=dict(document),
        path=Path("."),
    )


def _draft_evidence_stub(document_hash: str):
    from p2p_engine.core.vertical_drafts import VerticalDraftEvidence

    return VerticalDraftEvidence.empty(1, document_hash)

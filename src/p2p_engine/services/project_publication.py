from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    relative_to_root as _relative_to_root,
    write_text_atomic as _write_text_atomic,
    write_yaml_atomic as _write_yaml_atomic,
)
from p2p_engine.services.project_publication_validation import (
    ProjectPublicationValidator,
    PublicationValidationResult,
    validation_result_payload,
)
from p2p_engine.services.project_publication_rendering import (
    PdfRenderer,
    PublicationRenderResult,
    now_utc_iso,
    render_pdf_with_weasyprint,
)
from p2p_engine.services.visible_project_export import VisibleProjectExportResult


PUBLICATION_PIPELINE = "human_project_publication"
PUBLICATION_ROLE = "canonical_human_publication"
PROFILE_ID = "neutral-v1-standard"
MANIFEST_VERSION = 1
FINGERPRINT_VERSION = 1

_PROPOSAL_FINGERPRINT_FILES = (
    "proposal.md",
    "alternatives.md",
    "decision.md",
    "findings.md",
    "risks.md",
    "assumptions.md",
    "open-questions.md",
    "readiness.yml",
    "impact-map.yml",
    "artifact-state.yml",
)


@dataclass(frozen=True)
class PublicationPaths:
    latest_dir: Path
    source_export: Path
    profile: Path
    curator_input: Path
    curated: Path
    validation: Path
    pdf: Path
    review: Path
    manifest: Path


@dataclass(frozen=True)
class SourceFingerprint:
    sha256: str
    inputs: list[dict[str, str]]


@dataclass(frozen=True)
class PublicationStageStatus:
    name: str
    path: Path
    exists: bool
    status: str
    stale: bool
    sha256: str | None = None
    recorded_sha256: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class ProjectPublicationStatus:
    manifest_path: Path
    source_fingerprint_sha256: str
    stages: list[PublicationStageStatus]
    validation_status: str
    render_status: str
    review_status: str
    approved_for_publication: bool


@dataclass(frozen=True)
class ProjectPublicationPrepareResult:
    status: str
    exported: bool
    reused_export: bool
    latest_path: Path
    archived_path: Path | None
    profile_path: Path
    curator_input_path: Path
    manifest_path: Path
    source_fingerprint_sha256: str
    source_sha256: str
    stale_downstream: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectPublicationImportResult:
    status: str
    curated_path: Path
    manifest_path: Path
    imported_from: Path
    curated_sha256: str
    source_fingerprint_sha256: str
    source_sha256: str
    profile_sha256: str


@dataclass(frozen=True)
class ProjectPublicationReviewResult:
    status: str
    review_path: Path
    reviewer: str
    reviewed_at: str
    curated_sha256: str
    pdf_sha256: str
    notes: list[str] = field(default_factory=list)


class ProjectPublicationService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        export_visible_project: Callable[[], VisibleProjectExportResult],
        accepted_proposals: Callable[[], list[dict[str, object]]],
        project_vertical_lock_status: Callable[[], Any] | None = None,
        project_definition_view: Callable[[], Any] | None = None,
        pdf_renderer: PdfRenderer | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.export_visible_project = export_visible_project
        self.accepted_proposals = accepted_proposals
        self.project_vertical_lock_status = project_vertical_lock_status
        self.project_definition_view = project_definition_view
        self.pdf_renderer = pdf_renderer or render_pdf_with_weasyprint

    def paths(self) -> PublicationPaths:
        latest = self.root / "outputs" / "latest"
        return PublicationPaths(
            latest_dir=latest,
            source_export=latest / "project.md",
            profile=latest / "publication-profile.yml",
            curator_input=latest / "curator-input.md",
            curated=latest / "project.curated.md",
            validation=latest / "publication-validation.yml",
            pdf=latest / "project.pdf",
            review=latest / "publication-review.yml",
            manifest=latest / "publication-manifest.yml",
        )

    def prepare(self) -> ProjectPublicationPrepareResult:
        paths = self.paths()
        manifest = self._read_manifest()
        source_fingerprint = self.source_fingerprint()
        source_stage = self._stage(manifest, "source_export")
        recorded_fingerprint = str(
            source_stage.get("source_fingerprint_sha256")
            or manifest.get("source_state", {}).get("fingerprint_sha256")
            or ""
        )
        recorded_source_hash = str(source_stage.get("sha256") or "")
        current_source_hash = _sha256_file(paths.source_export) if paths.source_export.exists() else ""
        export_valid = (
            paths.source_export.exists()
            and recorded_fingerprint == source_fingerprint.sha256
            and bool(recorded_source_hash)
            and recorded_source_hash == current_source_hash
        )

        exported = False
        archived_path: Path | None = None
        if not export_valid:
            export_result = self.export_visible_project()
            exported = True
            archived_path = export_result.archived_path
            if not paths.source_export.exists():
                raise ValueError("Visible project export did not write outputs/latest/project.md")
            current_source_hash = _sha256_file(paths.source_export)

        profile_payload = self._profile_payload()
        _write_yaml_atomic(paths.profile, profile_payload)
        profile_hash = _sha256_file(paths.profile)

        curator_input = self._curator_input_text(
            source_fingerprint=source_fingerprint,
            source_sha256=current_source_hash,
            profile_sha256=profile_hash,
        )
        _write_text_atomic(paths.curator_input, curator_input)
        curator_input_hash = _sha256_file(paths.curator_input)

        previous_stages = self._manifest_stages(manifest)
        stale_downstream = self._stale_downstream_after_prepare(
            previous_stages,
            source_fingerprint_sha256=source_fingerprint.sha256,
            source_sha256=current_source_hash,
            profile_sha256=profile_hash,
        )
        stages = dict(previous_stages)
        stages["source_export"] = {
            "path": _rel(paths.source_export, self.root),
            "source_fingerprint_sha256": source_fingerprint.sha256,
            "sha256": current_source_hash,
        }
        stages["profile"] = {
            "path": _rel(paths.profile, self.root),
            "profile_id": PROFILE_ID,
            "sha256": profile_hash,
        }
        stages["curator_packet"] = {
            "path": _rel(paths.curator_input, self.root),
            "source_fingerprint_sha256": source_fingerprint.sha256,
            "source_sha256": current_source_hash,
            "profile_sha256": profile_hash,
            "sha256": curator_input_hash,
        }

        self._write_manifest(
            {
                "schema_version": MANIFEST_VERSION,
                "pipeline": PUBLICATION_PIPELINE,
                "publication_role": PUBLICATION_ROLE,
                "governance_authority": "derived",
                "source_of_truth": ".p2p/",
                "updated_at": _now_iso(),
                "source_state": {
                    "fingerprint_version": FINGERPRINT_VERSION,
                    "fingerprint_sha256": source_fingerprint.sha256,
                    "inputs": source_fingerprint.inputs,
                },
                "stages": stages,
            }
        )

        return ProjectPublicationPrepareResult(
            status="prepared",
            exported=exported,
            reused_export=not exported,
            latest_path=_relative(paths.source_export, self.root),
            archived_path=archived_path,
            profile_path=_relative(paths.profile, self.root),
            curator_input_path=_relative(paths.curator_input, self.root),
            manifest_path=_relative(paths.manifest, self.root),
            source_fingerprint_sha256=source_fingerprint.sha256,
            source_sha256=current_source_hash,
            stale_downstream=stale_downstream,
        )

    def import_curated(self, source: Path) -> ProjectPublicationImportResult:
        paths = self.paths()
        manifest = self._read_manifest(require=True)
        packet_stage = self._stage(manifest, "curator_packet")
        if not paths.curator_input.exists():
            raise ValueError("Publication curator input is missing. Run p2p project publish prepare first.")
        if not paths.profile.exists():
            raise ValueError("Publication profile is missing. Run p2p project publish prepare first.")
        if not paths.source_export.exists():
            raise ValueError("Visible project export is missing. Run p2p project publish prepare first.")

        self._require_current_packet(packet_stage)
        source_path = self._safe_import_source(source, paths)
        try:
            content = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Curated publication import must be a UTF-8 Markdown file") from exc

        _write_text_atomic(paths.curated, content)
        curated_sha256 = _sha256_file(paths.curated)
        stages = self._manifest_stages(manifest)
        stages["curated"] = {
            "path": _rel(paths.curated, self.root),
            "imported_from": _rel(source_path, self.root),
            "imported_at": _now_iso(),
            "source_fingerprint_sha256": str(packet_stage.get("source_fingerprint_sha256") or ""),
            "source_sha256": str(packet_stage.get("source_sha256") or ""),
            "profile_sha256": str(packet_stage.get("profile_sha256") or ""),
            "curator_packet_sha256": str(packet_stage.get("sha256") or ""),
            "sha256": curated_sha256,
        }
        manifest["updated_at"] = _now_iso()
        manifest["stages"] = stages
        self._write_manifest(manifest)

        return ProjectPublicationImportResult(
            status="imported",
            curated_path=_relative(paths.curated, self.root),
            manifest_path=_relative(paths.manifest, self.root),
            imported_from=_relative(source_path, self.root),
            curated_sha256=curated_sha256,
            source_fingerprint_sha256=str(packet_stage.get("source_fingerprint_sha256") or ""),
            source_sha256=str(packet_stage.get("source_sha256") or ""),
            profile_sha256=str(packet_stage.get("profile_sha256") or ""),
        )

    def validate(self) -> PublicationValidationResult:
        paths = self.paths()
        manifest = self._read_manifest()
        curated_sha256 = _sha256_file(paths.curated) if paths.curated.exists() else ""
        profile_sha256 = _sha256_file(paths.profile) if paths.profile.exists() else ""
        validator = ProjectPublicationValidator(root=self.root)
        result = validator.validate(
            curated_path=paths.curated,
            profile_path=paths.profile,
            manifest_path=paths.manifest,
            manifest=manifest,
            curated_sha256=curated_sha256,
            profile_sha256=profile_sha256,
        )
        _write_yaml_atomic(paths.validation, validation_result_payload(result))
        validation_sha256 = _sha256_file(paths.validation)
        stages = self._manifest_stages(manifest)
        stages["validation"] = {
            "path": _rel(paths.validation, self.root),
            "curated_sha256": curated_sha256,
            "profile_sha256": profile_sha256,
            "validator_version": result.validator_version,
            "validated_at": result.validated_at,
            "status": result.status,
            "sha256": validation_sha256,
        }
        manifest.update(
            {
                "schema_version": MANIFEST_VERSION,
                "pipeline": PUBLICATION_PIPELINE,
                "publication_role": PUBLICATION_ROLE,
                "governance_authority": "derived",
                "source_of_truth": ".p2p/",
                "updated_at": _now_iso(),
                "stages": stages,
            }
        )
        self._write_manifest(manifest)
        return result

    def render(self) -> PublicationRenderResult:
        paths = self.paths()
        manifest = self._read_manifest(require=True)
        status = self.status()
        validation_stage_status = _stage_by_name(status.stages, "validation")
        validation_stage = self._stage(manifest, "validation")
        if validation_stage_status.status != "ready":
            raise ValueError("Publication validation is missing or stale. Run p2p project publish validate first.")
        if str(validation_stage.get("status") or "") != "passed":
            raise ValueError("Publication validation must pass before rendering PDF.")
        if not paths.curated.exists():
            raise ValueError("Curated publication Markdown is missing.")

        curated_sha256 = _sha256_file(paths.curated)
        validation_sha256 = _sha256_file(paths.validation)
        markdown_text = paths.curated.read_text(encoding="utf-8")
        renderer_name = self.pdf_renderer(markdown_text, paths.pdf, self.root)
        pdf_sha256 = _sha256_file(paths.pdf)
        rendered_at = now_utc_iso()
        stages = self._manifest_stages(manifest)
        stages["render"] = {
            "path": _rel(paths.pdf, self.root),
            "curated_sha256": curated_sha256,
            "validation_sha256": validation_sha256,
            "theme": "neutral-v1",
            "renderer": renderer_name,
            "rendered_at": rendered_at,
            "status": "rendered",
            "sha256": pdf_sha256,
        }
        manifest["updated_at"] = _now_iso()
        manifest["stages"] = stages
        self._write_manifest(manifest)
        return PublicationRenderResult(
            status="rendered",
            path=_relative(paths.pdf, self.root),
            sha256=pdf_sha256,
            curated_sha256=curated_sha256,
            validation_sha256=validation_sha256,
            theme="neutral-v1",
            renderer=renderer_name,
            rendered_at=rendered_at,
        )

    def review(
        self,
        *,
        status: str,
        reviewer: str = "owner",
        notes: list[str] | None = None,
    ) -> ProjectPublicationReviewResult:
        normalized_status = status.strip().lower()
        if normalized_status not in {"approved", "changes_requested"}:
            raise ValueError("Review status must be approved or changes_requested.")
        reviewer = reviewer.strip() or "owner"
        notes = [note for note in notes or [] if note.strip()]
        paths = self.paths()
        manifest = self._read_manifest(require=True)
        publication_status = self.status()
        render_status = _stage_by_name(publication_status.stages, "render")
        if render_status.status != "ready":
            raise ValueError("Publication PDF is missing or stale. Run p2p project publish render first.")
        if not paths.curated.exists() or not paths.pdf.exists():
            raise ValueError("Publication review requires current curated Markdown and PDF.")

        curated_sha256 = _sha256_file(paths.curated)
        pdf_sha256 = _sha256_file(paths.pdf)
        validation_sha256 = _sha256_file(paths.validation) if paths.validation.exists() else ""
        rendered_stage = self._stage(manifest, "render")
        if str(rendered_stage.get("curated_sha256") or "") != curated_sha256:
            raise ValueError("Publication PDF is stale for the current curated Markdown.")
        if str(rendered_stage.get("sha256") or "") != pdf_sha256:
            raise ValueError("Publication PDF hash differs from the manifest.")

        reviewed_at = now_utc_iso()
        payload = {
            "schema_version": MANIFEST_VERSION,
            "status": normalized_status,
            "reviewed_at": reviewed_at,
            "reviewer": reviewer,
            "reviewed_artifacts": [
                {"path": _rel(paths.curated, self.root), "sha256": curated_sha256},
                {"path": _rel(paths.pdf, self.root), "sha256": pdf_sha256},
            ],
            "validation": _rel(paths.validation, self.root),
            "notes": notes,
        }
        _write_yaml_atomic(paths.review, payload)
        review_sha256 = _sha256_file(paths.review)
        stages = self._manifest_stages(manifest)
        stages["review"] = {
            "path": _rel(paths.review, self.root),
            "status": normalized_status,
            "reviewed_at": reviewed_at,
            "reviewer": reviewer,
            "curated_sha256": curated_sha256,
            "pdf_sha256": pdf_sha256,
            "validation_sha256": validation_sha256,
            "sha256": review_sha256,
        }
        manifest["updated_at"] = _now_iso()
        manifest["stages"] = stages
        self._write_manifest(manifest)
        return ProjectPublicationReviewResult(
            status=normalized_status,
            review_path=_relative(paths.review, self.root),
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            curated_sha256=curated_sha256,
            pdf_sha256=pdf_sha256,
            notes=notes,
        )

    def status(self) -> ProjectPublicationStatus:
        paths = self.paths()
        manifest = self._read_manifest()
        source_fingerprint = self.source_fingerprint()
        stages = self._stage_statuses(paths, manifest, source_fingerprint)
        validation_stage = _stage_by_name(stages, "validation")
        render_stage = _stage_by_name(stages, "render")
        review_stage = _stage_by_name(stages, "review")
        approved = self._approved_for_publication(manifest, stages)
        return ProjectPublicationStatus(
            manifest_path=_relative(paths.manifest, self.root),
            source_fingerprint_sha256=source_fingerprint.sha256,
            stages=stages,
            validation_status=self._manifest_stage_status(manifest, "validation", validation_stage),
            render_status=self._manifest_stage_status(manifest, "render", render_stage),
            review_status=self._manifest_stage_status(manifest, "review", review_stage),
            approved_for_publication=approved,
        )

    def source_fingerprint(self) -> SourceFingerprint:
        inputs: list[dict[str, str]] = []
        for path in self._source_fingerprint_paths():
            if path.exists() and path.is_file():
                inputs.append(
                    {
                        "path": _rel(path, self.root),
                        "sha256": _sha256_file(path),
                    }
                )
        payload = {"version": FINGERPRINT_VERSION, "inputs": sorted(inputs, key=lambda item: item["path"])}
        return SourceFingerprint(sha256=_stable_sha256(payload), inputs=payload["inputs"])

    def _source_fingerprint_paths(self) -> list[Path]:
        paths = [
            self.p2p_dir / "project.yml",
            self.p2p_dir / "registries" / "proposals.yml",
            self.p2p_dir / "registries" / "decisions.yml",
            self.p2p_dir / "registries" / "artifacts.yml",
            self.p2p_dir / "registries" / "readiness.yml",
            self.root / "outputs" / "latest" / "visible-export-source-manifest.yml",
        ]
        project_dir = self.p2p_dir / "project"
        if project_dir.exists():
            paths.extend(sorted(path for path in project_dir.glob("*.yml") if path.is_file()))
        for proposal in self.accepted_proposals():
            proposal_dir = _proposal_dir_from_record(proposal, self.root)
            if proposal_dir is None:
                continue
            paths.extend(proposal_dir / filename for filename in _PROPOSAL_FINGERPRINT_FILES)
        unique: dict[str, Path] = {}
        for path in paths:
            unique[str(path.resolve())] = path
        return [unique[key] for key in sorted(unique)]

    def _profile_payload(self) -> dict[str, object]:
        return {
            "schema_version": MANIFEST_VERSION,
            "profile_id": PROFILE_ID,
            "profile_role": "fixed_applied_manifest",
            "resolved_values": {
                "audience": "mixed",
                "depth": "standard",
                "language": "project_default",
                "vertical_structure": "adaptive",
                "include_appendix": False,
                "theme": "neutral-v1",
            },
        }

    def _curator_input_text(
        self,
        *,
        source_fingerprint: SourceFingerprint,
        source_sha256: str,
        profile_sha256: str,
    ) -> str:
        paths = self.paths()
        source_text = paths.source_export.read_text(encoding="utf-8")
        traceability_lines = self._traceability_lines()
        lines = [
            "# P2P Project Curator Input",
            "",
            "## Source Export",
            "",
            f"- path: `{_rel(paths.source_export, self.root)}`",
            f"- sha256: `{source_sha256}`",
            f"- p2p_source_fingerprint_sha256: `{source_fingerprint.sha256}`",
            "- source_of_truth: `.p2p/`",
            "",
            "## Publication Profile",
            "",
            f"- path: `{_rel(paths.profile, self.root)}`",
            f"- sha256: `{profile_sha256}`",
            "- profile_id: `neutral-v1-standard`",
            "- audience: `mixed`",
            "- depth: `standard`",
            "- language: `project_default`",
            "- vertical_structure: `adaptive`",
            "- include_appendix: `false`",
            "- theme: `neutral-v1`",
            "",
            "## Curator Contract",
            "",
            "- Produce one canonical human project document at `outputs/latest/project.curated.md`.",
            "- Do not create commercial, technical, investor, executive, or audience-specific variants.",
            "- Explain the project first, then use governance history only as supporting evidence.",
            "- Adapt headings, grouping, terminology, and explanatory order to the active vertical when available.",
            "- Distinguish current, implemented, planned, partial, pending, missing, legacy, risk, assumption, and open-question evidence.",
            "- Preserve traceability for material claims using proposal IDs, decision IDs, Change Set IDs, Work IDs, or source artifact paths.",
            "- Remove placeholders, empty sections, repeated boilerplate, and internal governance noise from the main body.",
            "- Include a clear source-of-truth statement that `.p2p/` remains authoritative.",
            "",
            "## Vertical Summary",
            "",
            self._vertical_summary(),
            "",
            "## Traceability Inputs",
            "",
            *(traceability_lines or ["- No accepted proposal traceability inputs found."]),
            "",
            "## Complete Source Export",
            "",
            "The following content is generated output. Use it as input evidence, not as governance state.",
            "",
            "```markdown",
            source_text.rstrip(),
            "```",
            "",
        ]
        return "\n".join(lines)

    def _traceability_lines(self) -> list[str]:
        lines: list[str] = []
        for proposal in self.accepted_proposals():
            proposal_id = str(proposal.get("proposal_id") or proposal.get("id") or "").strip()
            title = str(proposal.get("title") or "").strip()
            source = str(proposal.get("source") or proposal.get("path") or "").strip()
            if proposal_id:
                suffix = f" - {title}" if title else ""
                source_suffix = f" (`{source}`)" if source else ""
                lines.append(f"- {proposal_id}{suffix}{source_suffix}")
        return lines

    def _vertical_summary(self) -> str:
        lines: list[str] = []
        if self.project_vertical_lock_status is None:
            lines.append("- lock_status: unavailable")
        else:
            try:
                lock = self.project_vertical_lock_status()
            except ValueError:
                lock = None
            if lock is None:
                lines.append("- lock_status: unavailable")
            else:
                lines.append(f"- lock_status: {getattr(lock, 'status', 'unknown')}")
                locked = getattr(lock, "locked", None)
                if locked is not None:
                    lines.append(f"- active_vertical: {getattr(locked, 'vertical_id', 'unknown')}")
        if self.project_definition_view is None:
            lines.append("- definition_state: unavailable")
        else:
            try:
                definition = self.project_definition_view()
            except ValueError:
                definition = None
            if definition is None:
                lines.append("- definition_state: unavailable")
            else:
                lines.append(f"- definition_state_exists: {str(bool(getattr(definition, 'exists', False))).lower()}")
                lines.append(f"- definition_state_valid: {str(bool(getattr(definition, 'valid', False))).lower()}")
        return "\n".join(lines)

    def _require_current_packet(self, packet_stage: dict[str, object]) -> None:
        paths = self.paths()
        current_fingerprint = self.source_fingerprint().sha256
        current_source_hash = _sha256_file(paths.source_export)
        current_profile_hash = _sha256_file(paths.profile)
        current_packet_hash = _sha256_file(paths.curator_input)
        if str(packet_stage.get("source_fingerprint_sha256") or "") != current_fingerprint:
            raise ValueError("Publication curator input is stale: P2P source fingerprint changed.")
        if str(packet_stage.get("source_sha256") or "") != current_source_hash:
            raise ValueError("Publication curator input is stale: source export hash changed.")
        if str(packet_stage.get("profile_sha256") or "") != current_profile_hash:
            raise ValueError("Publication curator input is stale: publication profile hash changed.")
        if str(packet_stage.get("sha256") or "") != current_packet_hash:
            raise ValueError("Publication curator input is stale: packet hash changed.")

    def _safe_import_source(self, source: Path, paths: PublicationPaths) -> Path:
        resolved = source.expanduser().resolve()
        root = self.root.resolve()
        p2p_dir = self.p2p_dir.resolve()
        if not resolved.exists():
            raise ValueError(f"Curated publication import source does not exist: {source}")
        if not resolved.is_file():
            raise ValueError(f"Curated publication import source is not a file: {source}")
        if not _is_relative_to(resolved, root):
            raise ValueError("Curated publication import source must be inside the project root.")
        if _is_relative_to(resolved, p2p_dir):
            raise ValueError("Curated publication import source must not be under .p2p/.")
        if resolved == paths.curated.resolve():
            raise ValueError("Use an external curated draft path; do not import the canonical output path.")
        return resolved

    def _stage_statuses(
        self,
        paths: PublicationPaths,
        manifest: dict[str, object],
        source_fingerprint: SourceFingerprint,
    ) -> list[PublicationStageStatus]:
        source = self._stage_file_status(
            "source_export",
            paths.source_export,
            self._stage(manifest, "source_export"),
        )
        if source.status == "ready":
            source_stage = self._stage(manifest, "source_export")
            if str(source_stage.get("source_fingerprint_sha256") or "") != source_fingerprint.sha256:
                source = _stale(source, "P2P source fingerprint changed")
        profile = self._stage_file_status("profile", paths.profile, self._stage(manifest, "profile"))
        packet = self._dependent_status(
            "curator_packet",
            paths.curator_input,
            self._stage(manifest, "curator_packet"),
            blockers=(source, profile),
            required={
                "source_fingerprint_sha256": source_fingerprint.sha256,
                "source_sha256": source.sha256 or "",
                "profile_sha256": profile.sha256 or "",
            },
        )
        curated = self._dependent_status(
            "curated",
            paths.curated,
            self._stage(manifest, "curated"),
            blockers=(source, profile, packet),
            required={
                "source_fingerprint_sha256": source_fingerprint.sha256,
                "source_sha256": source.sha256 or "",
                "profile_sha256": profile.sha256 or "",
            },
        )
        validation = self._dependent_status(
            "validation",
            paths.validation,
            self._stage(manifest, "validation"),
            blockers=(curated,),
            required={"curated_sha256": curated.sha256 or ""},
        )
        render = self._dependent_status(
            "render",
            paths.pdf,
            self._stage(manifest, "render"),
            blockers=(curated, validation),
            required={
                "curated_sha256": curated.sha256 or "",
                "validation_sha256": validation.sha256 or "",
            },
        )
        review = self._dependent_status(
            "review",
            paths.review,
            self._stage(manifest, "review"),
            blockers=(curated, render),
            required={
                "curated_sha256": curated.sha256 or "",
                "pdf_sha256": render.sha256 or "",
            },
        )
        return [source, profile, packet, curated, validation, render, review]

    def _stage_file_status(
        self,
        name: str,
        path: Path,
        stage: dict[str, object],
    ) -> PublicationStageStatus:
        if not path.exists():
            return PublicationStageStatus(name=name, path=_relative(path, self.root), exists=False, status="missing", stale=False)
        sha256 = _sha256_file(path)
        recorded = str(stage.get("sha256") or "")
        if not recorded:
            return PublicationStageStatus(
                name=name,
                path=_relative(path, self.root),
                exists=True,
                status="stale",
                stale=True,
                sha256=sha256,
                recorded_sha256=None,
                reason="manifest hash missing",
            )
        if recorded != sha256:
            return PublicationStageStatus(
                name=name,
                path=_relative(path, self.root),
                exists=True,
                status="stale",
                stale=True,
                sha256=sha256,
                recorded_sha256=recorded,
                reason="file hash differs from manifest",
            )
        return PublicationStageStatus(
            name=name,
            path=_relative(path, self.root),
            exists=True,
            status="ready",
            stale=False,
            sha256=sha256,
            recorded_sha256=recorded,
        )

    def _dependent_status(
        self,
        name: str,
        path: Path,
        stage: dict[str, object],
        *,
        blockers: tuple[PublicationStageStatus, ...],
        required: dict[str, str],
    ) -> PublicationStageStatus:
        status = self._stage_file_status(name, path, stage)
        if status.status == "missing":
            return status
        stale_blocker = next((blocker for blocker in blockers if blocker.stale or blocker.status != "ready"), None)
        if stale_blocker is not None:
            return _stale(status, f"{stale_blocker.name} is {stale_blocker.status}")
        for key, expected in required.items():
            if expected and str(stage.get(key) or "") != expected:
                return _stale(status, f"{key} differs from current stage")
        return status

    def _approved_for_publication(
        self,
        manifest: dict[str, object],
        stages: list[PublicationStageStatus],
    ) -> bool:
        review = _stage_by_name(stages, "review")
        if review.status != "ready":
            return False
        review_stage = self._stage(manifest, "review")
        return str(review_stage.get("status") or "") == "approved"

    def _manifest_stage_status(
        self,
        manifest: dict[str, object],
        name: str,
        stage_status: PublicationStageStatus,
    ) -> str:
        if stage_status.status != "ready":
            return stage_status.status
        stage = self._stage(manifest, name)
        return str(stage.get("status") or stage_status.status)

    def _stale_downstream_after_prepare(
        self,
        stages: dict[str, object],
        *,
        source_fingerprint_sha256: str,
        source_sha256: str,
        profile_sha256: str,
    ) -> list[str]:
        source_stage = _as_mapping(stages.get("source_export"))
        profile_stage = _as_mapping(stages.get("profile"))
        changed = (
            str(source_stage.get("source_fingerprint_sha256") or "") != source_fingerprint_sha256
            or str(source_stage.get("sha256") or "") != source_sha256
            or str(profile_stage.get("sha256") or "") != profile_sha256
        )
        if not changed:
            return []
        return ["curator_packet", "curated", "validation", "render", "review"]

    def _read_manifest(self, *, require: bool = False) -> dict[str, object]:
        path = self.paths().manifest
        if require and not path.exists():
            raise ValueError("Publication manifest is missing. Run p2p project publish prepare first.")
        return _read_yaml_mapping(path, default={})

    def _write_manifest(self, payload: dict[str, object]) -> None:
        _write_yaml_atomic(self.paths().manifest, payload)

    def _stage(self, manifest: dict[str, object], name: str) -> dict[str, object]:
        return _as_mapping(self._manifest_stages(manifest).get(name))

    def _manifest_stages(self, manifest: dict[str, object]) -> dict[str, object]:
        return _as_mapping(manifest.get("stages"))


def _proposal_dir_from_record(record: dict[str, object], root: Path) -> Path | None:
    raw = record.get("path") or record.get("source")
    if raw is None:
        return None
    path = raw if isinstance(raw, Path) else Path(str(raw))
    if not path.is_absolute():
        path = root / path
    return path


def _stage_by_name(stages: list[PublicationStageStatus], name: str) -> PublicationStageStatus:
    for stage in stages:
        if stage.name == name:
            return stage
    raise ValueError(f"Unknown publication stage: {name}")


def _stale(status: PublicationStageStatus, reason: str) -> PublicationStageStatus:
    return PublicationStageStatus(
        name=status.name,
        path=status.path,
        exists=status.exists,
        status="stale",
        stale=True,
        sha256=status.sha256,
        recorded_sha256=status.recorded_sha256,
        reason=reason,
    )


def _as_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_sha256(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _relative(path: Path, root: Path) -> Path:
    return _relative_to_root(path, root)


def _rel(path: Path, root: Path) -> str:
    return _relative(path, root).as_posix()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True

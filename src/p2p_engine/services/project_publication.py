from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any

try:  # pragma: no cover - platform-specific branch
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows
    _fcntl = None

try:  # pragma: no cover - platform-specific branch
    import msvcrt as _msvcrt
except ImportError:  # pragma: no cover - POSIX
    _msvcrt = None

from p2p_engine.core.project_publication import (
    DEFAULT_PUBLICATION_LANGUAGE,
    DEFAULT_PUBLICATION_OUTPUT_NAME,
    PUBLICATION_CATALOG_VERSION,
    PUBLICATION_CONTRACT_VERSION,
    PUBLICATION_EVIDENCE_GENERATOR,
    PUBLICATION_MANIFEST_VERSION,
    PUBLICATION_PROFILE_ID,
    PublicationEdition,
    PublicationEditionPaths,
    normalize_contribution_policy,
    resolve_publication_paths,
)
from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.core.vertical_memory import VerticalProjectMemoryView
from p2p_engine.foundation.files import (
    relative_to_root as _relative_to_root,
    write_bytes_atomic as _write_bytes_atomic,
    write_text_atomic as _write_text_atomic,
    write_yaml_atomic as _write_yaml_atomic,
)
from p2p_engine.services.project_publication_contracts import (
    physical_sha256,
    read_publication_yaml,
    validate_evidence_accounting,
    validate_model_contributions,
    validate_publication_catalog,
    validate_publication_evidence_index,
    validate_publication_model,
    validate_publication_profile,
)
from p2p_engine.services.project_publication_evidence import (
    ProjectPublicationEvidenceService,
    evidence_index_is_current,
)
from p2p_engine.services.project_publication_rendering import (
    PdfRenderer,
    PublicationRenderResult,
    now_utc_iso,
    render_pdf_with_weasyprint,
)
from p2p_engine.services.project_publication_validation import (
    ProjectPublicationValidator,
    PublicationValidationResult,
    validation_result_payload,
)
from p2p_engine.services.visible_project_export import VisibleProjectExportResult
from p2p_engine.services.workspace_reads import WorkspaceReadContext


PUBLICATION_PIPELINE = "human_project_publication"
PUBLICATION_ROLE = "human_project_language_edition"
FINGERPRINT_VERSION = 2


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
    edition: PublicationEdition
    manifest_path: Path
    source_fingerprint_sha256: str
    stages: list[PublicationStageStatus]
    validation_status: str
    render_status: str
    review_status: str
    approved_for_publication: bool
    diagnostics: tuple[PublicationEditionDiagnostic, ...] = ()


@dataclass(frozen=True)
class PublicationCatalogEntry:
    edition: PublicationEdition
    manifest_path: Path
    updated_at: str
    validation_status: str
    render_status: str
    review_status: str


@dataclass(frozen=True)
class PublicationEditionDiagnostic:
    code: str
    message: str
    path: Path


@dataclass(frozen=True)
class PublicationCatalogResult:
    catalog_path: Path
    editions: tuple[PublicationCatalogEntry, ...]
    diagnostics: tuple[PublicationEditionDiagnostic, ...] = ()


@dataclass(frozen=True)
class ProjectPublicationPrepareResult:
    status: str
    edition: PublicationEdition
    exported: bool
    reused_export: bool
    latest_path: Path
    archived_path: Path | None
    evidence_path: Path
    evidence_sha256: str
    profile_path: Path
    curator_input_path: Path
    manifest_path: Path
    candidate_markdown_path: Path
    candidate_model_path: Path
    candidate_evidence_path: Path
    source_fingerprint_sha256: str
    source_sha256: str
    stale_downstream: list[str] = field(default_factory=list)
    written_paths: tuple[Path, ...] = ()
    reused_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ProjectPublicationImportResult:
    status: str
    edition: PublicationEdition
    curated_path: Path
    model_path: Path
    evidence_accounting_path: Path
    manifest_path: Path
    imported_from: Path
    model_imported_from: Path
    evidence_imported_from: Path
    curated_sha256: str
    model_sha256: str
    evidence_accounting_sha256: str
    source_fingerprint_sha256: str
    source_sha256: str
    profile_sha256: str
    written_paths: tuple[Path, ...] = ()
    reused_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ProjectPublicationReviewResult:
    status: str
    edition: PublicationEdition
    review_path: Path
    reviewer: str
    reviewed_at: str
    curated_sha256: str
    pdf_sha256: str
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _PreparedSharedEvidence:
    source_fingerprint: SourceFingerprint
    source_sha256: str
    evidence_payload: Mapping[str, object]
    evidence_physical_sha256: str
    evidence_semantic_sha256: str
    evidence_written: bool
    exported: bool
    archived_path: Path | None


@dataclass(frozen=True)
class _ValidatedImportCandidates:
    markdown_path: Path
    model_path: Path
    accounting_path: Path
    markdown_bytes: bytes
    expected_bindings: Mapping[str, str]


@dataclass(frozen=True)
class _CommittedImport:
    curated_sha256: str
    model_sha256: str
    accounting_sha256: str
    written_paths: tuple[Path, ...]
    reused_paths: tuple[Path, ...]


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
        proposal_decision_lifecycles: (
            Callable[[], dict[str, ProposalDecisionLifecycleView]] | None
        ) = None,
        vertical_project_memory: Callable[[], VerticalProjectMemoryView] | None = None,
        pdf_renderer: PdfRenderer | None = None,
        transaction_hook: Callable[[str, Path | None], None] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.export_visible_project = export_visible_project
        self.accepted_proposals = accepted_proposals
        self.project_vertical_lock_status = project_vertical_lock_status
        self.project_definition_view = project_definition_view
        self.proposal_decision_lifecycles = proposal_decision_lifecycles
        self.vertical_project_memory = vertical_project_memory
        self.pdf_renderer = pdf_renderer or render_pdf_with_weasyprint
        self.transaction_hook = transaction_hook
        self.evidence_service = ProjectPublicationEvidenceService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            accepted_proposals=accepted_proposals,
            proposal_decision_lifecycles=proposal_decision_lifecycles,
            vertical_memory=vertical_project_memory,
        )

    def paths(
        self,
        *,
        language: str = DEFAULT_PUBLICATION_LANGUAGE,
        output_name: str = DEFAULT_PUBLICATION_OUTPUT_NAME,
    ) -> PublicationEditionPaths:
        return resolve_publication_paths(
            self.root,
            PublicationEdition.create(language=language, output_name=output_name),
        )

    def prepare(
        self,
        *,
        language: str = DEFAULT_PUBLICATION_LANGUAGE,
        output_name: str = DEFAULT_PUBLICATION_OUTPUT_NAME,
        contributions: str = "auto",
    ) -> ProjectPublicationPrepareResult:
        paths = self.paths(language=language, output_name=output_name)
        policy = normalize_contribution_policy(contributions)
        written_paths: list[Path] = []
        reused_paths: list[Path] = []
        manifest = self._read_manifest(paths)
        shared = self._prepare_shared_evidence(paths, manifest)
        _record_write_result(
            paths.evidence_index,
            shared.evidence_written,
            root=self.root,
            written=written_paths,
            reused=reused_paths,
        )
        include_contributions = self._include_contributions(shared.evidence_payload, policy)
        profile_hash, packet_hash = self._prepare_profile_and_packet(
            paths=paths,
            shared=shared,
            policy=policy,
            include_contributions=include_contributions,
            written_paths=written_paths,
            reused_paths=reused_paths,
        )
        stale_downstream = self._commit_prepare_manifest(
            paths=paths,
            manifest=manifest,
            shared=shared,
            profile_sha256=profile_hash,
            packet_sha256=packet_hash,
            written_paths=written_paths,
            reused_paths=reused_paths,
        )
        self._write_catalog()
        return ProjectPublicationPrepareResult(
            status="prepared",
            edition=paths.edition,
            exported=shared.exported,
            reused_export=not shared.exported,
            latest_path=_relative(paths.source_export, self.root),
            archived_path=shared.archived_path,
            evidence_path=_relative(paths.evidence_index, self.root),
            evidence_sha256=shared.evidence_semantic_sha256,
            profile_path=_relative(paths.profile, self.root),
            curator_input_path=_relative(paths.curator_input, self.root),
            manifest_path=_relative(paths.manifest, self.root),
            candidate_markdown_path=_relative(paths.candidate_markdown, self.root),
            candidate_model_path=_relative(paths.candidate_model, self.root),
            candidate_evidence_path=_relative(paths.candidate_evidence, self.root),
            source_fingerprint_sha256=shared.source_fingerprint.sha256,
            source_sha256=shared.source_sha256,
            stale_downstream=stale_downstream,
            written_paths=tuple(written_paths),
            reused_paths=tuple(reused_paths),
        )

    def _prepare_profile_and_packet(
        self,
        *,
        paths: PublicationEditionPaths,
        shared: _PreparedSharedEvidence,
        policy: str,
        include_contributions: bool,
        written_paths: list[Path],
        reused_paths: list[Path],
    ) -> tuple[str, str]:
        profile_payload = self._profile_payload(
            paths.edition,
            contribution_policy=policy,
            include_contributions=include_contributions,
        )
        _record_write_result(
            paths.profile,
            _write_yaml_if_changed(paths.profile, profile_payload),
            root=self.root,
            written=written_paths,
            reused=reused_paths,
        )
        profile_sha256 = _sha256_file(paths.profile)
        packet = self._curator_input_text(
            paths=paths,
            source_fingerprint=shared.source_fingerprint,
            source_sha256=shared.source_sha256,
            evidence_physical_sha256=shared.evidence_physical_sha256,
            evidence_semantic_sha256=shared.evidence_semantic_sha256,
            profile_sha256=profile_sha256,
        )
        _record_write_result(
            paths.curator_input,
            _write_text_if_changed(paths.curator_input, packet),
            root=self.root,
            written=written_paths,
            reused=reused_paths,
        )
        return profile_sha256, _sha256_file(paths.curator_input)

    def _commit_prepare_manifest(
        self,
        *,
        paths: PublicationEditionPaths,
        manifest: Mapping[str, object],
        shared: _PreparedSharedEvidence,
        profile_sha256: str,
        packet_sha256: str,
        written_paths: list[Path],
        reused_paths: list[Path],
    ) -> list[str]:
        previous_stages = _manifest_stages(manifest)
        changed = _prepare_inputs_changed(
            previous_stages,
            source_fingerprint_sha256=shared.source_fingerprint.sha256,
            source_sha256=shared.source_sha256,
            evidence_sha256=shared.evidence_physical_sha256,
            evidence_semantic_sha256=shared.evidence_semantic_sha256,
            profile_sha256=profile_sha256,
            packet_sha256=packet_sha256,
        )
        stages = dict(previous_stages)
        stages.update(
            self._prepared_stage_payloads(
                paths,
                shared=shared,
                profile_sha256=profile_sha256,
                packet_sha256=packet_sha256,
            )
        )
        _record_write_result(
            paths.manifest,
            self._write_manifest(
                paths,
                self._manifest_payload(
                    paths.edition,
                    source_fingerprint=shared.source_fingerprint,
                    stages=stages,
                ),
            ),
            root=self.root,
            written=written_paths,
            reused=reused_paths,
        )
        return (
            ["model", "evidence_accounting", "curated", "validation", "render", "review"]
            if changed
            else []
        )

    def _prepared_stage_payloads(
        self,
        paths: PublicationEditionPaths,
        *,
        shared: _PreparedSharedEvidence,
        profile_sha256: str,
        packet_sha256: str,
    ) -> dict[str, object]:
        return {
            "source_export": {
                "path": _rel(paths.source_export, self.root),
                "source_fingerprint_sha256": shared.source_fingerprint.sha256,
                "sha256": shared.source_sha256,
            },
            "evidence_index": {
                "path": _rel(paths.evidence_index, self.root),
                "source_fingerprint_sha256": shared.source_fingerprint.sha256,
                "source_sha256": shared.source_sha256,
                "semantic_sha256": shared.evidence_semantic_sha256,
                "sha256": shared.evidence_physical_sha256,
            },
            "profile": {
                "path": _rel(paths.profile, self.root),
                "profile_id": PUBLICATION_PROFILE_ID,
                "sha256": profile_sha256,
            },
            "curator_packet": {
                "path": _rel(paths.curator_input, self.root),
                "source_fingerprint_sha256": shared.source_fingerprint.sha256,
                "source_sha256": shared.source_sha256,
                "evidence_sha256": shared.evidence_physical_sha256,
                "evidence_semantic_sha256": shared.evidence_semantic_sha256,
                "profile_sha256": profile_sha256,
                "sha256": packet_sha256,
            },
        }

    def _prepare_shared_evidence(
        self,
        paths: PublicationEditionPaths,
        manifest: Mapping[str, object],
    ) -> _PreparedSharedEvidence:
        read_context = WorkspaceReadContext(self.root)
        fingerprint_sha256, fingerprint_inputs = self.evidence_service.source_fingerprint(
            read_context=read_context,
            finalize=False,
        )
        source_fingerprint = SourceFingerprint(
            sha256=fingerprint_sha256,
            inputs=list(fingerprint_inputs),
        )
        evidence_payload = self._read_evidence_index(paths)
        source_stage = _manifest_stage(manifest, "source_export")
        recorded_fingerprint = str(
            source_stage.get("source_fingerprint_sha256")
            or evidence_payload.get("source_fingerprint_sha256")
            or ""
        )
        source_sha256 = _sha256_file(paths.source_export) if paths.source_export.exists() else ""
        recorded_source_hash = str(
            source_stage.get("sha256")
            or _as_mapping(evidence_payload.get("source_export")).get("sha256")
            or ""
        )
        export_valid = (
            paths.source_export.exists()
            and recorded_fingerprint == source_fingerprint.sha256
            and bool(recorded_source_hash)
            and recorded_source_hash == source_sha256
        )
        exported = False
        archived_path: Path | None = None
        if not export_valid:
            export_result = self.export_visible_project()
            exported = True
            archived_path = export_result.archived_path
            if not paths.source_export.exists():
                raise ValueError("Visible project export did not write outputs/latest/project.md")
            source_sha256 = _sha256_file(paths.source_export)

        if evidence_index_is_current(
            evidence_payload,
            source_fingerprint_sha256=source_fingerprint.sha256,
            source_export_sha256=source_sha256,
            generator=PUBLICATION_EVIDENCE_GENERATOR,
        ):
            consistency = read_context.finalize()
            if not consistency.current:
                raise ValueError("Publication sources changed during prepare; retry the operation.")
            evidence_written = False
        else:
            evidence_capture = self.evidence_service.capture(read_context=read_context)
            evidence_payload = self.evidence_service.build_from_capture(
                evidence_capture,
                source_export_path=paths.source_export,
                source_export_sha256=source_sha256,
            )
            evidence_written = _write_yaml_if_changed(paths.evidence_index, evidence_payload)
        return _PreparedSharedEvidence(
            source_fingerprint=source_fingerprint,
            source_sha256=source_sha256,
            evidence_payload=evidence_payload,
            evidence_physical_sha256=_sha256_file(paths.evidence_index),
            evidence_semantic_sha256=str(evidence_payload.get("semantic_sha256") or ""),
            evidence_written=evidence_written,
            exported=exported,
            archived_path=archived_path,
        )

    @staticmethod
    def _include_contributions(
        evidence_payload: Mapping[str, object],
        policy: str,
    ) -> bool:
        contribution_summary = _as_mapping(evidence_payload.get("contributions"))
        attributed = sum(
            int(item.get("count") or 0)
            for item in contribution_summary.get("rows", [])
            if isinstance(item, Mapping) and str(item.get("author") or "") != "Unattributed"
        )
        if policy == "include" and attributed == 0:
            raise ValueError(
                "Contribution chapter was requested but no attributed contribution records are available."
            )
        return policy == "include" or (policy == "auto" and attributed > 0)

    def import_curated(
        self,
        source: Path | None = None,
        *,
        model: Path | None = None,
        evidence_accounting: Path | None = None,
        language: str = DEFAULT_PUBLICATION_LANGUAGE,
        output_name: str = DEFAULT_PUBLICATION_OUTPUT_NAME,
    ) -> ProjectPublicationImportResult:
        paths = self.paths(language=language, output_name=output_name)
        with self._edition_import_lock(paths.edition):
            return self._import_curated_locked(
                paths,
                source=source,
                model=model,
                evidence_accounting=evidence_accounting,
            )

    def _import_curated_locked(
        self,
        paths: PublicationEditionPaths,
        *,
        source: Path | None,
        model: Path | None,
        evidence_accounting: Path | None,
    ) -> ProjectPublicationImportResult:
        manifest = self._read_manifest(paths, require=True)
        packet_stage = _manifest_stage(manifest, "curator_packet")
        self._require_current_packet(paths, packet_stage)
        candidates = self._validate_import_candidates(
            paths,
            packet_stage=packet_stage,
            source=source,
            model=model,
            evidence_accounting=evidence_accounting,
        )
        committed = self._commit_import(paths, manifest, candidates)
        self._write_catalog()
        return ProjectPublicationImportResult(
            status="imported",
            edition=paths.edition,
            curated_path=_relative(paths.markdown, self.root),
            model_path=_relative(paths.model, self.root),
            evidence_accounting_path=_relative(paths.evidence_accounting, self.root),
            manifest_path=_relative(paths.manifest, self.root),
            imported_from=_relative(candidates.markdown_path, self.root),
            model_imported_from=_relative(candidates.model_path, self.root),
            evidence_imported_from=_relative(candidates.accounting_path, self.root),
            curated_sha256=committed.curated_sha256,
            model_sha256=committed.model_sha256,
            evidence_accounting_sha256=committed.accounting_sha256,
            source_fingerprint_sha256=candidates.expected_bindings[
                "source_fingerprint_sha256"
            ],
            source_sha256=candidates.expected_bindings["source_export_sha256"],
            profile_sha256=candidates.expected_bindings["profile_sha256"],
            written_paths=committed.written_paths,
            reused_paths=committed.reused_paths,
        )

    def _validate_import_candidates(
        self,
        paths: PublicationEditionPaths,
        *,
        packet_stage: Mapping[str, object],
        source: Path | None,
        model: Path | None,
        evidence_accounting: Path | None,
    ) -> _ValidatedImportCandidates:
        source_path = self._safe_import_source(source or paths.candidate_markdown, paths, ".md")
        model_path = self._safe_import_source(model or paths.candidate_model, paths, ".yml")
        accounting_path = self._safe_import_source(
            evidence_accounting or paths.candidate_evidence,
            paths,
            ".yml",
        )
        if len({source_path, model_path, accounting_path}) != 3:
            raise ValueError("Publication candidate Markdown, model, and accounting paths must be distinct.")
        try:
            markdown = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Curated publication import must be UTF-8 Markdown.") from exc
        if not markdown.strip():
            raise ValueError("Curated publication import must not be empty.")

        evidence_index = read_publication_yaml(paths.evidence_index, label="publication evidence index")
        validate_publication_evidence_index(evidence_index)
        model_payload = read_publication_yaml(model_path, label="publication model")
        expected_bindings = {
            "curator_packet_sha256": str(packet_stage.get("sha256") or ""),
            "evidence_index_sha256": str(packet_stage.get("evidence_semantic_sha256") or ""),
            "source_export_sha256": str(packet_stage.get("source_sha256") or ""),
            "source_fingerprint_sha256": str(packet_stage.get("source_fingerprint_sha256") or ""),
            "profile_sha256": str(packet_stage.get("profile_sha256") or ""),
        }
        validated_model = validate_publication_model(
            model_payload,
            edition=paths.edition,
            expected_bindings=expected_bindings,
            evidence_index=evidence_index,
        )
        profile_payload = read_publication_yaml(paths.profile, label="publication profile")
        validate_publication_profile(profile_payload, edition=paths.edition)
        validate_model_contributions(
            validated_model,
            profile=profile_payload,
            evidence_index=evidence_index,
        )
        model_hash = physical_sha256(model_path)
        accounting_payload = read_publication_yaml(accounting_path, label="publication evidence accounting")
        validate_evidence_accounting(
            accounting_payload,
            edition=paths.edition,
            evidence_index=evidence_index,
            model=validated_model,
            model_sha256=model_hash,
        )
        return _ValidatedImportCandidates(
            markdown_path=source_path,
            model_path=model_path,
            accounting_path=accounting_path,
            markdown_bytes=markdown.encode("utf-8"),
            expected_bindings=expected_bindings,
        )

    def _commit_import(
        self,
        paths: PublicationEditionPaths,
        manifest: Mapping[str, object],
        candidates: _ValidatedImportCandidates,
    ) -> _CommittedImport:
        prior_manifest_hash = _sha256_file(paths.manifest)
        targets: dict[Path, bytes] = {
            paths.model: candidates.model_path.read_bytes(),
            paths.evidence_accounting: candidates.accounting_path.read_bytes(),
            paths.markdown: candidates.markdown_bytes,
        }
        previous = _capture_targets(targets)
        previous[paths.manifest] = paths.manifest.read_bytes()
        written_paths: list[Path] = []
        reused_paths: list[Path] = []
        try:
            for target, content in targets.items():
                if target.exists() and target.read_bytes() == content:
                    reused_paths.append(_relative(target, self.root))
                    continue
                self._transaction_event("before_replace", target)
                _write_bytes_if_changed(target, content)
                self._transaction_event("after_replace", target)
                written_paths.append(_relative(target, self.root))
            if _sha256_file(paths.manifest) != prior_manifest_hash:
                raise ValueError("Publication manifest changed during import; prepare and retry.")
            model_target_hash = _sha256_file(paths.model)
            accounting_target_hash = _sha256_file(paths.evidence_accounting)
            markdown_hash = _sha256_file(paths.markdown)
            stages = _manifest_stages(manifest)
            stages.update(
                {
                    "model": {
                        "path": _rel(paths.model, self.root),
                        "imported_from": _rel(candidates.model_path, self.root),
                        "imported_at": _now_iso(),
                        **candidates.expected_bindings,
                        "sha256": model_target_hash,
                    },
                    "evidence_accounting": {
                        "path": _rel(paths.evidence_accounting, self.root),
                        "imported_from": _rel(candidates.accounting_path, self.root),
                        "imported_at": _now_iso(),
                        "model_sha256": model_target_hash,
                        "evidence_index_sha256": candidates.expected_bindings[
                            "evidence_index_sha256"
                        ],
                        "sha256": accounting_target_hash,
                    },
                    "curated": {
                        "path": _rel(paths.markdown, self.root),
                        "imported_from": _rel(candidates.markdown_path, self.root),
                        "imported_at": _now_iso(),
                        "model_sha256": model_target_hash,
                        "evidence_accounting_sha256": accounting_target_hash,
                        **candidates.expected_bindings,
                        "sha256": markdown_hash,
                    },
                }
            )
            self._transaction_event("before_manifest_commit", paths.manifest)
            self._write_manifest(
                paths,
                self._manifest_payload(
                    paths.edition,
                    source_fingerprint=self.source_fingerprint(),
                    stages=stages,
                ),
            )
            self._transaction_event("after_manifest_commit", paths.manifest)
        except Exception:
            _restore_targets(previous)
            raise
        return _CommittedImport(
            curated_sha256=markdown_hash,
            model_sha256=model_target_hash,
            accounting_sha256=accounting_target_hash,
            written_paths=tuple(written_paths),
            reused_paths=tuple(reused_paths),
        )

    @contextmanager
    def _edition_import_lock(self, edition: PublicationEdition):
        identity = hashlib.sha256(
            f"{self.root}:{edition.edition_key}".encode("utf-8")
        ).hexdigest()[:24]
        lock_path = Path(tempfile.gettempdir()) / f"p2p-publication-{identity}.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        locked = False
        try:
            try:
                _lock_file(descriptor)
                locked = True
            except (BlockingIOError, OSError) as exc:
                raise ValueError(
                    f"Publication import for {edition.edition_key} is already in progress."
                ) from exc
            yield
        finally:
            try:
                if locked:
                    _unlock_file(descriptor)
            finally:
                os.close(descriptor)

    def _transaction_event(self, event: str, path: Path | None = None) -> None:
        if self.transaction_hook is not None:
            self.transaction_hook(event, path)

    def validate(
        self,
        *,
        language: str = DEFAULT_PUBLICATION_LANGUAGE,
        output_name: str = DEFAULT_PUBLICATION_OUTPUT_NAME,
    ) -> PublicationValidationResult:
        paths = self.paths(language=language, output_name=output_name)
        manifest = self._read_manifest(paths)
        source_fingerprint = self.source_fingerprint()
        validator = ProjectPublicationValidator(root=self.root)
        result = validator.validate(
            edition=paths.edition,
            markdown_path=paths.markdown,
            model_path=paths.model,
            evidence_accounting_path=paths.evidence_accounting,
            evidence_index_path=paths.evidence_index,
            profile_path=paths.profile,
            manifest_path=paths.manifest,
            manifest=manifest,
            current_source_fingerprint_sha256=source_fingerprint.sha256,
        )
        _write_yaml_atomic(paths.validation, validation_result_payload(result))
        validation_hash = _sha256_file(paths.validation)
        stages = _manifest_stages(manifest)
        stages["validation"] = {
            "path": _rel(paths.validation, self.root),
            "curated_sha256": _sha256_file(paths.markdown) if paths.markdown.exists() else "",
            "model_sha256": _sha256_file(paths.model) if paths.model.exists() else "",
            "evidence_accounting_sha256": (
                _sha256_file(paths.evidence_accounting) if paths.evidence_accounting.exists() else ""
            ),
            "profile_sha256": _sha256_file(paths.profile) if paths.profile.exists() else "",
            "validator_version": result.validator_version,
            "validated_at": result.validated_at,
            "status": result.status,
            "sha256": validation_hash,
        }
        self._write_manifest(
            paths,
            self._manifest_payload(
                paths.edition,
                source_fingerprint=source_fingerprint,
                stages=stages,
            ),
        )
        self._write_catalog()
        return result

    def render(
        self,
        *,
        language: str = DEFAULT_PUBLICATION_LANGUAGE,
        output_name: str = DEFAULT_PUBLICATION_OUTPUT_NAME,
    ) -> PublicationRenderResult:
        paths = self.paths(language=language, output_name=output_name)
        manifest = self._read_manifest(paths, require=True)
        status = self.status(language=language, output_name=output_name)
        validation_status = _stage_by_name(status.stages, "validation")
        validation_stage = _manifest_stage(manifest, "validation")
        if validation_status.status != "ready":
            raise ValueError(
                f"Publication validation for {paths.edition.edition_key} is missing or stale. "
                f"Run p2p project publish validate --language {paths.edition.language} "
                f"--output-name {paths.edition.output_name}."
            )
        if str(validation_stage.get("status") or "") != "passed":
            raise ValueError("Publication validation must pass before rendering PDF.")
        model = read_publication_yaml(paths.model, label="publication model")
        title = str(_as_mapping(model.get("project")).get("title") or paths.edition.output_name)
        markdown = paths.markdown.read_text(encoding="utf-8")
        renderer_name = self.pdf_renderer(
            markdown,
            paths.pdf,
            self.root,
            language=paths.edition.language,
            title=title,
        )
        pdf_hash = _sha256_file(paths.pdf)
        stages = _manifest_stages(manifest)
        stages["render"] = {
            "path": _rel(paths.pdf, self.root),
            "curated_sha256": _sha256_file(paths.markdown),
            "model_sha256": _sha256_file(paths.model),
            "evidence_accounting_sha256": _sha256_file(paths.evidence_accounting),
            "validation_sha256": _sha256_file(paths.validation),
            "theme": "neutral-v1",
            "renderer": renderer_name,
            "rendered_at": now_utc_iso(),
            "status": "rendered",
            "sha256": pdf_hash,
        }
        self._write_manifest(
            paths,
            self._manifest_payload(
                paths.edition,
                source_fingerprint=self.source_fingerprint(),
                stages=stages,
            ),
        )
        self._write_catalog()
        return PublicationRenderResult(
            status="rendered",
            path=_relative(paths.pdf, self.root),
            sha256=pdf_hash,
            curated_sha256=_sha256_file(paths.markdown),
            validation_sha256=_sha256_file(paths.validation),
            theme="neutral-v1",
            renderer=renderer_name,
            rendered_at=str(stages["render"]["rendered_at"]),
            language=paths.edition.language,
            edition_key=paths.edition.edition_key,
        )

    def review(
        self,
        *,
        status: str,
        reviewer: str = "owner",
        notes: list[str] | None = None,
        language: str = DEFAULT_PUBLICATION_LANGUAGE,
        output_name: str = DEFAULT_PUBLICATION_OUTPUT_NAME,
    ) -> ProjectPublicationReviewResult:
        normalized_status = status.strip().lower()
        if normalized_status not in {"approved", "changes_requested"}:
            raise ValueError("Review status must be approved or changes_requested.")
        paths = self.paths(language=language, output_name=output_name)
        manifest = self._read_manifest(paths, require=True)
        publication_status = self.status(language=language, output_name=output_name)
        if _stage_by_name(publication_status.stages, "render").status != "ready":
            raise ValueError("Publication PDF is missing or stale. Run publication render first.")
        reviewed_at = now_utc_iso()
        hashes = {
            "curated_sha256": _sha256_file(paths.markdown),
            "pdf_sha256": _sha256_file(paths.pdf),
            "validation_sha256": _sha256_file(paths.validation),
            "model_sha256": _sha256_file(paths.model),
            "evidence_accounting_sha256": _sha256_file(paths.evidence_accounting),
        }
        payload = {
            "schema_version": PUBLICATION_CONTRACT_VERSION,
            "edition": paths.edition.to_dict(),
            "status": normalized_status,
            "reviewed_at": reviewed_at,
            "reviewer": reviewer.strip() or "owner",
            "reviewed_artifacts": [
                {"path": _rel(paths.markdown, self.root), "sha256": hashes["curated_sha256"]},
                {"path": _rel(paths.pdf, self.root), "sha256": hashes["pdf_sha256"]},
            ],
            "bindings": hashes,
            "notes": [item for item in notes or [] if item.strip()],
            "governance_authority": "derived_publication_review",
        }
        _write_yaml_atomic(paths.review, payload)
        stages = _manifest_stages(manifest)
        stages["review"] = {
            "path": _rel(paths.review, self.root),
            "status": normalized_status,
            "reviewed_at": reviewed_at,
            "reviewer": payload["reviewer"],
            **hashes,
            "sha256": _sha256_file(paths.review),
        }
        self._write_manifest(
            paths,
            self._manifest_payload(
                paths.edition,
                source_fingerprint=self.source_fingerprint(),
                stages=stages,
            ),
        )
        self._write_catalog()
        return ProjectPublicationReviewResult(
            status=normalized_status,
            edition=paths.edition,
            review_path=_relative(paths.review, self.root),
            reviewer=str(payload["reviewer"]),
            reviewed_at=reviewed_at,
            curated_sha256=hashes["curated_sha256"],
            pdf_sha256=hashes["pdf_sha256"],
            notes=list(payload["notes"]),
        )

    def status(
        self,
        *,
        language: str = DEFAULT_PUBLICATION_LANGUAGE,
        output_name: str = DEFAULT_PUBLICATION_OUTPUT_NAME,
        read_context: WorkspaceReadContext | None = None,
    ) -> ProjectPublicationStatus:
        paths = self.paths(language=language, output_name=output_name)
        source_fingerprint = self.source_fingerprint(read_context=read_context)
        try:
            manifest = self._read_manifest(paths)
        except ValueError as exc:
            diagnostic = PublicationEditionDiagnostic(
                code="publication_manifest_invalid",
                message=str(exc),
                path=_relative(paths.manifest, self.root),
            )
            return ProjectPublicationStatus(
                edition=paths.edition,
                manifest_path=_relative(paths.manifest, self.root),
                source_fingerprint_sha256=source_fingerprint.sha256,
                stages=_invalid_manifest_stage_statuses(paths, self.root, str(exc)),
                validation_status="invalid",
                render_status="invalid",
                review_status="invalid",
                approved_for_publication=False,
                diagnostics=(diagnostic,),
            )
        stages = self._stage_statuses(paths, manifest, source_fingerprint)
        validation = _stage_by_name(stages, "validation")
        render = _stage_by_name(stages, "render")
        review = _stage_by_name(stages, "review")
        return ProjectPublicationStatus(
            edition=paths.edition,
            manifest_path=_relative(paths.manifest, self.root),
            source_fingerprint_sha256=source_fingerprint.sha256,
            stages=stages,
            validation_status=_resolved_stage_status(manifest, "validation", validation),
            render_status=_resolved_stage_status(manifest, "render", render),
            review_status=_resolved_stage_status(manifest, "review", review),
            approved_for_publication=(
                review.status == "ready"
                and str(_manifest_stage(manifest, "review").get("status") or "") == "approved"
            ),
        )

    def list_editions(self) -> PublicationCatalogResult:
        default_paths = self.paths()
        entries: list[PublicationCatalogEntry] = []
        diagnostics: list[PublicationEditionDiagnostic] = []
        publication_root = default_paths.latest_dir / "publications"
        if publication_root.exists():
            for manifest_path in sorted(publication_root.glob("*/manifest.yml")):
                try:
                    manifest = read_publication_yaml(
                        manifest_path,
                        label="publication edition manifest",
                    )
                except ValueError as exc:
                    diagnostics.append(
                        PublicationEditionDiagnostic(
                            "publication_manifest_invalid",
                            str(exc),
                            _relative(manifest_path, self.root),
                        )
                    )
                    continue
                if int(manifest.get("schema_version") or 0) != PUBLICATION_MANIFEST_VERSION:
                    diagnostics.append(
                        PublicationEditionDiagnostic(
                            "publication_manifest_version_unsupported",
                            f"Unsupported publication manifest version: {manifest.get('schema_version')}",
                            _relative(manifest_path, self.root),
                        )
                    )
                    continue
                if str(manifest.get("pipeline") or "") != PUBLICATION_PIPELINE:
                    diagnostics.append(
                        PublicationEditionDiagnostic(
                            "publication_manifest_pipeline_invalid",
                            "Publication manifest pipeline is invalid.",
                            _relative(manifest_path, self.root),
                        )
                    )
                    continue
                edition_payload = _as_mapping(manifest.get("edition"))
                try:
                    edition = PublicationEdition.create(
                        language=str(edition_payload.get("language") or ""),
                        output_name=str(edition_payload.get("output_name") or ""),
                    )
                except ValueError as exc:
                    diagnostics.append(
                        PublicationEditionDiagnostic(
                            "publication_edition_invalid",
                            str(exc),
                            _relative(manifest_path, self.root),
                        )
                    )
                    continue
                if edition_payload != edition.to_dict():
                    diagnostics.append(
                        PublicationEditionDiagnostic(
                            "publication_edition_not_canonical",
                            "Publication manifest edition identity is not canonical.",
                            _relative(manifest_path, self.root),
                        )
                    )
                    continue
                if edition.edition_key != manifest_path.parent.name:
                    diagnostics.append(
                        PublicationEditionDiagnostic(
                            "publication_edition_key_mismatch",
                            "Manifest edition key does not match its directory.",
                            _relative(manifest_path, self.root),
                        )
                    )
                    continue
                if not isinstance(manifest.get("stages"), Mapping):
                    diagnostics.append(
                        PublicationEditionDiagnostic(
                            "publication_manifest_stages_invalid",
                            "Publication manifest stages must be a mapping.",
                            _relative(manifest_path, self.root),
                        )
                    )
                    continue
                stages = _manifest_stages(manifest)
                entries.append(
                    PublicationCatalogEntry(
                        edition=edition,
                        manifest_path=_relative(manifest_path, self.root),
                        updated_at=str(manifest.get("updated_at") or ""),
                        validation_status=self._catalog_stage_status(stages, "validation"),
                        render_status=self._catalog_stage_status(stages, "render"),
                        review_status=self._catalog_stage_status(stages, "review"),
                    )
                )
        entries.sort(key=lambda item: (item.edition.output_name, item.edition.language))
        return PublicationCatalogResult(
            catalog_path=_relative(default_paths.catalog, self.root),
            editions=tuple(entries),
            diagnostics=tuple(diagnostics),
        )

    def _catalog_stage_status(self, stages: Mapping[str, object], name: str) -> str:
        stage = _as_mapping(stages.get(name))
        relative = str(stage.get("path") or "")
        recorded = str(stage.get("sha256") or "")
        if not relative or not recorded:
            return "missing"
        path = (self.root / relative).resolve()
        if not _is_relative_to(path, self.root) or not path.is_file() or path.is_symlink():
            return "stale"
        if _sha256_file(path) != recorded:
            return "stale"
        return str(stage.get("status") or "ready")

    def source_fingerprint(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> SourceFingerprint:
        sha256, inputs = self.evidence_service.source_fingerprint(
            read_context=read_context,
            finalize=read_context is None,
        )
        return SourceFingerprint(sha256=sha256, inputs=list(inputs))

    def _profile_payload(
        self,
        edition: PublicationEdition,
        *,
        contribution_policy: str,
        include_contributions: bool,
    ) -> dict[str, object]:
        return {
            "schema_version": PUBLICATION_CONTRACT_VERSION,
            "profile_id": PUBLICATION_PROFILE_ID,
            "profile_role": "edition_applied_manifest",
            "edition": edition.to_dict(),
            "reader": {"knowledge_of_p2p": "none", "audience_variant": False},
            "editorial": {
                "structure": "vertical_adaptive",
                "traceability_in_body": False,
                "contributions": contribution_policy,
                "include_contributions": include_contributions,
            },
            "render": {"theme": "neutral-v1"},
        }

    def _curator_input_text(
        self,
        *,
        paths: PublicationEditionPaths,
        source_fingerprint: SourceFingerprint,
        source_sha256: str,
        evidence_physical_sha256: str,
        evidence_semantic_sha256: str,
        profile_sha256: str,
    ) -> str:
        lines = [
            "# Human Project Publication Curator Input",
            "",
            "## Edition",
            "",
            f"- key: `{paths.edition.edition_key}`",
            f"- language: `{paths.edition.language}`",
            f"- output_name: `{paths.edition.output_name}`",
            "- audience_variant: `false`",
            "- reader_knowledge_of_p2p: `none`",
            "",
            "## Complete Evidence Boundary",
            "",
            f"- source_export: `{_rel(paths.source_export, self.root)}`",
            f"- source_export_sha256: `{source_sha256}`",
            f"- source_fingerprint_sha256: `{source_fingerprint.sha256}`",
            f"- evidence_index: `{_rel(paths.evidence_index, self.root)}`",
            f"- evidence_index_sha256: `{evidence_physical_sha256}`",
            f"- evidence_index_semantic_sha256: `{evidence_semantic_sha256}`",
            f"- profile: `{_rel(paths.profile, self.root)}`",
            f"- profile_sha256: `{profile_sha256}`",
            "",
            "The source export is available for complete research but is not the document outline.",
            "The evidence index contains complete payloads or complete hash-bound source locators.",
            "Use no implicit knowledge from adjacent projects, brands, or prior conversations.",
            "",
            "## Exact Candidate Outputs",
            "",
            f"- markdown: `{_rel(paths.candidate_markdown, self.root)}`",
            f"- project_model: `{_rel(paths.candidate_model, self.root)}`",
            f"- evidence_accounting: `{_rel(paths.candidate_evidence, self.root)}`",
            "",
            "## Candidate Binding Contract",
            "",
            "Set the project-model bindings exactly as follows:",
            "",
            f"- `curator_packet_sha256`: physical SHA256 of `{_rel(paths.curator_input, self.root)}`",
            f"- `evidence_index_sha256`: `{evidence_semantic_sha256}`",
            f"- `source_export_sha256`: `{source_sha256}`",
            f"- `source_fingerprint_sha256`: `{source_fingerprint.sha256}`",
            f"- `profile_sha256`: `{profile_sha256}`",
            "",
            "The packet cannot embed its own physical hash. Compute it from the packet file",
            "after prepare has completed. In evidence accounting, set `model_sha256` to the",
            "physical SHA256 of the completed candidate model and reuse the evidence semantic",
            "hash above as `evidence_index_sha256`.",
            "Use the exact model and accounting field names from",
            "`references/publication-contracts.md`; do not substitute equivalent-looking keys.",
            "",
            "## Editorial Contract",
            "",
            "1. Read the active vertical and every evidence-index entry.",
            "2. Build the project model before writing prose.",
            "3. Account for every evidence ID exactly once.",
            "4. Write an autonomous project document for a reader who does not know P2P workflow.",
            "5. Do not expose internal IDs, hashes, paths, readiness, or upstream governance status.",
            "6. Explain proposal or lifecycle concepts only when they are evidenced subject matter of the project.",
            "7. Use the selected language consistently and keep project scope invariant across editions.",
            "8. Use the prepared contributor figures exactly when the profile includes Contributions.",
            "9. Complete the editorial rubric and write only the candidate triplet.",
            "10. Do not import, render, review, approve, or edit `.p2p/`.",
            "",
            "## Import Command",
            "",
            "```bash",
            f"p2p project publish import {_rel(paths.candidate_markdown, self.root)} \\",
            f"  --model {_rel(paths.candidate_model, self.root)} \\",
            f"  --evidence-accounting {_rel(paths.candidate_evidence, self.root)} \\",
            f"  --language {paths.edition.language} --output-name {paths.edition.output_name}",
            "```",
            "",
        ]
        return "\n".join(lines)

    def _require_current_packet(
        self,
        paths: PublicationEditionPaths,
        packet_stage: Mapping[str, object],
    ) -> None:
        required = (
            ("profile", paths.profile),
            ("curator input", paths.curator_input),
            ("source export", paths.source_export),
            ("evidence index", paths.evidence_index),
        )
        for label, path in required:
            if not path.exists():
                raise ValueError(f"Publication {label} is missing. Run publication prepare first.")
        current_fingerprint = self.source_fingerprint().sha256
        checks = {
            "source_fingerprint_sha256": current_fingerprint,
            "source_sha256": _sha256_file(paths.source_export),
            "evidence_sha256": _sha256_file(paths.evidence_index),
            "evidence_semantic_sha256": str(
                read_publication_yaml(paths.evidence_index, label="publication evidence index").get(
                    "semantic_sha256"
                )
                or ""
            ),
            "profile_sha256": _sha256_file(paths.profile),
            "sha256": _sha256_file(paths.curator_input),
        }
        for key, expected in checks.items():
            if str(packet_stage.get(key) or "") != expected:
                raise ValueError(f"Publication curator input is stale: {key} changed.")

    def _safe_import_source(
        self,
        source: Path,
        paths: PublicationEditionPaths,
        suffix: str,
    ) -> Path:
        candidate = source.expanduser()
        if ".." in candidate.parts:
            raise ValueError("Publication import source must not contain parent traversal.")
        if not candidate.is_absolute():
            candidate = self.root / candidate
        try:
            relative_candidate = candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Publication import source must be inside the project root.") from exc
        current = self.root
        for part in relative_candidate.parts:
            current /= part
            if current.is_symlink():
                raise ValueError("Publication import source must not use symlinks.")
        resolved = candidate.resolve()
        if not resolved.exists() or not resolved.is_file():
            raise ValueError(f"Publication import source is missing or not a file: {source}")
        if not _is_relative_to(resolved, self.root):
            raise ValueError("Publication import source must be inside the project root.")
        if _is_relative_to(resolved, self.p2p_dir):
            raise ValueError("Publication import source must not be under .p2p/.")
        if resolved.suffix.lower() != suffix:
            raise ValueError(f"Publication import source must use {suffix}: {source}")
        if resolved in {path.resolve() for path in paths.canonical_targets()}:
            raise ValueError("Use a candidate draft path; do not import a canonical output path.")
        return resolved

    def _stage_statuses(
        self,
        paths: PublicationEditionPaths,
        manifest: Mapping[str, object],
        source_fingerprint: SourceFingerprint,
    ) -> list[PublicationStageStatus]:
        source = _file_status(self.root, "source_export", paths.source_export, _manifest_stage(manifest, "source_export"))
        if source.status == "ready" and str(
            _manifest_stage(manifest, "source_export").get("source_fingerprint_sha256") or ""
        ) != source_fingerprint.sha256:
            source = _stale(source, "source fingerprint changed")
        evidence = _dependent_status(
            self.root,
            "evidence_index",
            paths.evidence_index,
            _manifest_stage(manifest, "evidence_index"),
            blockers=(source,),
            required={
                "source_fingerprint_sha256": source_fingerprint.sha256,
                "source_sha256": source.sha256 or "",
            },
        )
        profile = _file_status(self.root, "profile", paths.profile, _manifest_stage(manifest, "profile"))
        packet = _dependent_status(
            self.root,
            "curator_packet",
            paths.curator_input,
            _manifest_stage(manifest, "curator_packet"),
            blockers=(source, evidence, profile),
            required={
                "source_fingerprint_sha256": source_fingerprint.sha256,
                "source_sha256": source.sha256 or "",
                "evidence_sha256": evidence.sha256 or "",
                "profile_sha256": profile.sha256 or "",
            },
        )
        model = _dependent_status(
            self.root,
            "model",
            paths.model,
            _manifest_stage(manifest, "model"),
            blockers=(packet,),
            required={"curator_packet_sha256": packet.sha256 or ""},
        )
        accounting = _dependent_status(
            self.root,
            "evidence_accounting",
            paths.evidence_accounting,
            _manifest_stage(manifest, "evidence_accounting"),
            blockers=(evidence, model),
            required={"model_sha256": model.sha256 or ""},
        )
        curated = _dependent_status(
            self.root,
            "curated",
            paths.markdown,
            _manifest_stage(manifest, "curated"),
            blockers=(model, accounting),
            required={
                "model_sha256": model.sha256 or "",
                "evidence_accounting_sha256": accounting.sha256 or "",
            },
        )
        validation = _dependent_status(
            self.root,
            "validation",
            paths.validation,
            _manifest_stage(manifest, "validation"),
            blockers=(curated, model, accounting),
            required={
                "curated_sha256": curated.sha256 or "",
                "model_sha256": model.sha256 or "",
                "evidence_accounting_sha256": accounting.sha256 or "",
            },
        )
        render = _dependent_status(
            self.root,
            "render",
            paths.pdf,
            _manifest_stage(manifest, "render"),
            blockers=(curated, validation),
            required={
                "curated_sha256": curated.sha256 or "",
                "validation_sha256": validation.sha256 or "",
            },
        )
        review = _dependent_status(
            self.root,
            "review",
            paths.review,
            _manifest_stage(manifest, "review"),
            blockers=(model, accounting, curated, validation, render),
            required={
                "model_sha256": model.sha256 or "",
                "evidence_accounting_sha256": accounting.sha256 or "",
                "curated_sha256": curated.sha256 or "",
                "validation_sha256": validation.sha256 or "",
                "pdf_sha256": render.sha256 or "",
            },
        )
        return [source, evidence, profile, packet, model, accounting, curated, validation, render, review]

    def _manifest_payload(
        self,
        edition: PublicationEdition,
        *,
        source_fingerprint: SourceFingerprint,
        stages: Mapping[str, object],
    ) -> dict[str, object]:
        return {
            "schema_version": PUBLICATION_MANIFEST_VERSION,
            "pipeline": PUBLICATION_PIPELINE,
            "publication_role": PUBLICATION_ROLE,
            "governance_authority": "derived",
            "source_of_truth": ".p2p/",
            "edition": edition.to_dict(),
            "updated_at": _now_iso(),
            "source_state": {
                "fingerprint_version": FINGERPRINT_VERSION,
                "fingerprint_sha256": source_fingerprint.sha256,
                "input_count": len(source_fingerprint.inputs),
            },
            "stages": dict(stages),
        }

    def _read_evidence_index(self, paths: PublicationEditionPaths) -> dict[str, object]:
        if not paths.evidence_index.exists():
            return {}
        try:
            return validate_publication_evidence_index(
                read_publication_yaml(paths.evidence_index, label="publication evidence index")
            )
        except ValueError:
            return {}

    def _read_manifest(
        self,
        paths: PublicationEditionPaths,
        *,
        require: bool = False,
    ) -> dict[str, object]:
        if require and not paths.manifest.exists():
            raise ValueError(
                f"Publication manifest for {paths.edition.edition_key} is missing. "
                "Run publication prepare first."
            )
        manifest = (
            read_publication_yaml(paths.manifest, label="publication edition manifest")
            if paths.manifest.exists()
            else {}
        )
        if manifest and int(manifest.get("schema_version") or 0) != PUBLICATION_MANIFEST_VERSION:
            raise ValueError(
                f"Unsupported publication manifest version for {paths.edition.edition_key}."
            )
        if manifest:
            if str(manifest.get("pipeline") or "") != PUBLICATION_PIPELINE:
                raise ValueError(
                    f"Invalid publication manifest pipeline for {paths.edition.edition_key}."
                )
            raw_edition = _as_mapping(manifest.get("edition"))
            if raw_edition != paths.edition.to_dict():
                raise ValueError(
                    f"Publication manifest edition does not match {paths.edition.edition_key}."
                )
            if not isinstance(manifest.get("stages"), Mapping):
                raise ValueError(
                    f"Invalid publication manifest stages for {paths.edition.edition_key}."
                )
        return manifest

    def _write_manifest(self, paths: PublicationEditionPaths, payload: Mapping[str, object]) -> bool:
        current = (
            read_publication_yaml(paths.manifest, label="publication edition manifest")
            if paths.manifest.exists()
            else {}
        )
        candidate = dict(payload)
        if int(candidate.get("schema_version") or 0) != PUBLICATION_MANIFEST_VERSION:
            raise ValueError("Cannot write an unsupported publication manifest version.")
        if _as_mapping(candidate.get("edition")) != paths.edition.to_dict():
            raise ValueError("Cannot write a publication manifest for another edition.")
        if current and _without_updated_at(current) == _without_updated_at(candidate):
            return False
        _write_yaml_atomic(paths.manifest, candidate)
        return True

    def _write_catalog(self) -> None:
        result = self.list_editions()
        payload = {
            "schema_version": PUBLICATION_CATALOG_VERSION,
            "updated_at": _now_iso(),
            "editions": [
                {
                    "edition": item.edition.to_dict(),
                    "manifest": item.manifest_path.as_posix(),
                    "updated_at": item.updated_at,
                    "validation_status": item.validation_status,
                    "render_status": item.render_status,
                    "review_status": item.review_status,
                }
                for item in result.editions
            ],
            "diagnostics": [
                {
                    "code": item.code,
                    "message": item.message,
                    "path": item.path.as_posix(),
                }
                for item in result.diagnostics
            ],
        }
        catalog_path = self.paths().catalog
        current = (
            validate_publication_catalog(
                read_publication_yaml(catalog_path, label="publication catalog")
            )
            if catalog_path.exists()
            else {}
        )
        if current and _without_updated_at(current) == _without_updated_at(payload):
            return
        validate_publication_catalog(payload)
        _write_yaml_atomic(catalog_path, payload)

def _manifest_stages(manifest: Mapping[str, object]) -> dict[str, object]:
    return _as_mapping(manifest.get("stages"))


def _manifest_stage(manifest: Mapping[str, object], name: str) -> dict[str, object]:
    return _as_mapping(_manifest_stages(manifest).get(name))


def _file_status(
    root: Path,
    name: str,
    path: Path,
    stage: Mapping[str, object],
) -> PublicationStageStatus:
    relative = _relative(path, root)
    if not path.exists():
        return PublicationStageStatus(name, relative, False, "missing", False)
    sha256 = _sha256_file(path)
    recorded = str(stage.get("sha256") or "")
    if not recorded:
        return PublicationStageStatus(name, relative, True, "stale", True, sha256, None, "manifest hash missing")
    if recorded != sha256:
        return PublicationStageStatus(name, relative, True, "stale", True, sha256, recorded, "file hash differs from manifest")
    return PublicationStageStatus(name, relative, True, "ready", False, sha256, recorded)


def _dependent_status(
    root: Path,
    name: str,
    path: Path,
    stage: Mapping[str, object],
    *,
    blockers: Sequence[PublicationStageStatus],
    required: Mapping[str, str],
) -> PublicationStageStatus:
    status = _file_status(root, name, path, stage)
    if status.status == "missing":
        return status
    blocker = next((item for item in blockers if item.status != "ready"), None)
    if blocker is not None:
        return _stale(status, f"{blocker.name} is {blocker.status}")
    for key, expected in required.items():
        if expected and str(stage.get(key) or "") != expected:
            return _stale(status, f"{key} differs from current stage")
    return status


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


def _stage_by_name(stages: Sequence[PublicationStageStatus], name: str) -> PublicationStageStatus:
    for stage in stages:
        if stage.name == name:
            return stage
    raise ValueError(f"Unknown publication stage: {name}")


def _resolved_stage_status(
    manifest: Mapping[str, object],
    name: str,
    status: PublicationStageStatus,
) -> str:
    if status.status != "ready":
        return status.status
    return str(_manifest_stage(manifest, name).get("status") or status.status)


def _invalid_manifest_stage_statuses(
    paths: PublicationEditionPaths,
    root: Path,
    reason: str,
) -> list[PublicationStageStatus]:
    stage_paths = (
        ("source_export", paths.source_export),
        ("evidence_index", paths.evidence_index),
        ("profile", paths.profile),
        ("curator_packet", paths.curator_input),
        ("model", paths.model),
        ("evidence_accounting", paths.evidence_accounting),
        ("curated", paths.markdown),
        ("validation", paths.validation),
        ("render", paths.pdf),
        ("review", paths.review),
    )
    return [
        PublicationStageStatus(
            name=name,
            path=_relative(path, root),
            exists=path.is_file() and not path.is_symlink(),
            status="invalid",
            stale=True,
            sha256=_sha256_file(path) if path.is_file() and not path.is_symlink() else None,
            reason=reason,
        )
        for name, path in stage_paths
    ]


def _prepare_inputs_changed(
    stages: Mapping[str, object],
    *,
    source_fingerprint_sha256: str,
    source_sha256: str,
    evidence_sha256: str,
    evidence_semantic_sha256: str,
    profile_sha256: str,
    packet_sha256: str,
) -> bool:
    source = _as_mapping(stages.get("source_export"))
    evidence = _as_mapping(stages.get("evidence_index"))
    profile = _as_mapping(stages.get("profile"))
    packet = _as_mapping(stages.get("curator_packet"))
    return any(
        (
            str(source.get("source_fingerprint_sha256") or "") != source_fingerprint_sha256,
            str(source.get("sha256") or "") != source_sha256,
            str(evidence.get("sha256") or "") != evidence_sha256,
            str(evidence.get("semantic_sha256") or "") != evidence_semantic_sha256,
            str(profile.get("sha256") or "") != profile_sha256,
            str(packet.get("sha256") or "") != packet_sha256,
        )
    )


def _capture_targets(targets: Mapping[Path, bytes]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in targets}


def _restore_targets(previous: Mapping[Path, bytes | None]) -> None:
    for path, content in previous.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            _write_bytes_atomic(path, content)


def _write_text_if_changed(path: Path, content: str) -> bool:
    encoded = content.encode("utf-8")
    if path.exists() and path.read_bytes() == encoded:
        return False
    _write_text_atomic(path, content)
    return True


def _write_yaml_if_changed(path: Path, payload: Mapping[str, object]) -> bool:
    from p2p_engine.foundation.files import yaml_dump

    content = yaml_dump(dict(payload))
    return _write_text_if_changed(path, content)


def _write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    _write_bytes_atomic(path, content)
    return True


def _record_write_result(
    path: Path,
    changed: bool,
    *,
    root: Path,
    written: list[Path],
    reused: list[Path],
) -> None:
    target = _relative(path, root)
    (written if changed else reused).append(target)


def _lock_file(descriptor: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(descriptor, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return
    if _msvcrt is None:  # pragma: no cover - unsupported Python platform
        raise OSError("No supported publication lock primitive is available.")
    if os.fstat(descriptor).st_size == 0:
        os.write(descriptor, b"0")
    os.lseek(descriptor, 0, os.SEEK_SET)
    _msvcrt.locking(descriptor, _msvcrt.LK_NBLCK, 1)


def _unlock_file(descriptor: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(descriptor, _fcntl.LOCK_UN)
        return
    if _msvcrt is None:  # pragma: no cover - unsupported Python platform
        return
    os.lseek(descriptor, 0, os.SEEK_SET)
    _msvcrt.locking(descriptor, _msvcrt.LK_UNLCK, 1)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _relative(path: Path, root: Path) -> Path:
    return _relative_to_root(path, root)


def _rel(path: Path, root: Path) -> str:
    return _relative(path, root).as_posix()


def _as_mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _without_updated_at(payload: Mapping[str, object]) -> dict[str, object]:
    result = dict(payload)
    result.pop("updated_at", None)
    return result


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True

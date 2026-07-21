from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

from p2p_engine.core.project_publication import (
    PUBLICATION_CONTRACT_VERSION,
    PUBLICATION_MANIFEST_VERSION,
    PUBLICATION_VALIDATOR_VERSION,
    PublicationEdition,
    resolve_publication_paths,
)
from p2p_engine.services.project_publication_contracts import (
    physical_sha256,
    read_publication_yaml,
    validate_evidence_accounting,
    validate_model_contributions,
    validate_publication_evidence_index,
    validate_publication_model,
    validate_publication_profile,
)


_PLACEHOLDER_PATTERNS = (
    r"\bTBD\b",
    r"\bTODO\b",
    r"\blorem ipsum\b",
)
_INTERNAL_ID = re.compile(r"\b(?:PROP|CHANGE|WORK|EVENT|DECISION)-\d+[A-Z0-9-]*\b")
_WORKFLOW_HEADING = re.compile(
    r"^#{2,}\s+(?:accepted proposals|proposal status|decision events|change sets|work items|readiness|governance status)\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
_GOVERNANCE_NARRATION = re.compile(
    r"\b(?:proposal was (?:accepted|rejected|revoked)|readiness (?:gate|review)|"
    r"change set (?:status|lifecycle)|work item (?:status|lifecycle)|decision event)\b",
    flags=re.IGNORECASE,
)
_PROPOSAL_CHRONOLOGY = re.compile(
    r"\b(?:first|second|third|next|subsequent|earlier|later) proposal\b|"
    r"\bproposal (?:one|two|three|history|chronology)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class PublicationValidationFinding:
    severity: str
    code: str
    message: str
    path: Path | None = None
    line: int | None = None


@dataclass(frozen=True)
class PublicationValidationResult:
    schema_version: int
    status: str
    validated_at: str
    edition: PublicationEdition
    input: Path
    curated_sha256: str
    model: Path
    model_sha256: str
    evidence_accounting: Path
    evidence_accounting_sha256: str
    profile: Path
    profile_sha256: str
    source_export: Path
    source_export_sha256: str
    curator_input: Path
    curator_input_sha256: str
    evidence_index: Path
    evidence_index_sha256: str
    manifest: Path
    publication_contract_version: int
    validator_version: str
    findings: list[PublicationValidationFinding] = field(default_factory=list)


class ProjectPublicationValidator:
    def __init__(self, *, root: Path) -> None:
        self.root = root.resolve()

    def validate(
        self,
        *,
        edition: PublicationEdition,
        markdown_path: Path,
        model_path: Path,
        evidence_accounting_path: Path,
        evidence_index_path: Path,
        profile_path: Path,
        manifest_path: Path,
        manifest: Mapping[str, object],
        current_source_fingerprint_sha256: str = "",
    ) -> PublicationValidationResult:
        findings: list[PublicationValidationFinding] = []
        expected_paths = resolve_publication_paths(self.root, edition)
        findings.extend(
            self._path_and_manifest_findings(
                edition=edition,
                markdown_path=markdown_path,
                model_path=model_path,
                evidence_accounting_path=evidence_accounting_path,
                evidence_index_path=evidence_index_path,
                profile_path=profile_path,
                manifest_path=manifest_path,
                manifest=manifest,
                current_source_fingerprint_sha256=current_source_fingerprint_sha256,
            )
        )
        findings.extend(
            self._missing_input_findings(
                markdown_path=markdown_path,
                model_path=model_path,
                evidence_accounting_path=evidence_accounting_path,
                evidence_index_path=evidence_index_path,
                profile_path=profile_path,
                curator_input_path=expected_paths.curator_input,
                source_export_path=expected_paths.source_export,
            )
        )
        if any(finding.code.startswith("missing_") for finding in findings):
            return self._result(
                edition,
                markdown_path,
                model_path,
                evidence_accounting_path,
                profile_path,
                findings,
            )

        packet_stage = self._append_chain_findings(
            manifest=manifest,
            source_export_path=expected_paths.source_export,
            curator_input_path=expected_paths.curator_input,
            markdown_path=markdown_path,
            model_path=model_path,
            evidence_accounting_path=evidence_accounting_path,
            evidence_index_path=evidence_index_path,
            profile_path=profile_path,
            findings=findings,
        )
        evidence_index, profile, model = self._validated_contract_payloads(
            edition=edition,
            packet_stage=packet_stage,
            model_path=model_path,
            evidence_accounting_path=evidence_accounting_path,
            evidence_index_path=evidence_index_path,
            profile_path=profile_path,
            findings=findings,
        )
        try:
            text = markdown_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(
                _error("invalid_utf8", "Publication Markdown must be UTF-8.", markdown_path)
            )
        else:
            findings.extend(
                self._document_contract_findings(
                    text,
                    markdown_path,
                    edition,
                    model,
                    profile,
                    evidence_index,
                )
            )
        return self._result(
            edition,
            markdown_path,
            model_path,
            evidence_accounting_path,
            profile_path,
            findings,
        )

    def _path_and_manifest_findings(
        self,
        *,
        edition: PublicationEdition,
        markdown_path: Path,
        model_path: Path,
        evidence_accounting_path: Path,
        evidence_index_path: Path,
        profile_path: Path,
        manifest_path: Path,
        manifest: Mapping[str, object],
        current_source_fingerprint_sha256: str,
    ) -> list[PublicationValidationFinding]:
        findings: list[PublicationValidationFinding] = []
        expected_paths = resolve_publication_paths(self.root, edition)
        for label, actual, expected in (
            ("Markdown", markdown_path, expected_paths.markdown),
            ("model", model_path, expected_paths.model),
            ("evidence accounting", evidence_accounting_path, expected_paths.evidence_accounting),
            ("evidence index", evidence_index_path, expected_paths.evidence_index),
            ("profile", profile_path, expected_paths.profile),
            ("manifest", manifest_path, expected_paths.manifest),
        ):
            if actual.resolve() != expected.resolve():
                findings.append(_error("unsafe_output_path", f"Publication {label} path does not match the edition contract.", actual))

        if not manifest_path.exists():
            findings.append(_error("invalid_manifest", "Publication manifest is missing.", manifest_path))
        elif int(manifest.get("schema_version") or 0) != PUBLICATION_MANIFEST_VERSION:
            findings.append(_error("invalid_manifest_version", "Publication manifest version is unsupported.", manifest_path))
        if manifest.get("pipeline") != "human_project_publication":
            findings.append(_error("invalid_manifest", "Publication manifest pipeline is invalid.", manifest_path))
        manifest_edition = _mapping(manifest.get("edition"))
        if str(manifest_edition.get("key") or "") != edition.edition_key:
            findings.append(_error("edition_mismatch", "Publication manifest edition does not match the selected edition.", manifest_path))
        source_stage = _mapping(_mapping(manifest.get("stages")).get("source_export"))
        if (
            current_source_fingerprint_sha256
            and str(source_stage.get("source_fingerprint_sha256") or "")
            != current_source_fingerprint_sha256
        ):
            findings.append(
                _error(
                    "source_fingerprint_stale",
                    "Publication sources changed after this edition was prepared.",
                    manifest_path,
                )
            )
        return findings

    @staticmethod
    def _missing_input_findings(
        *,
        markdown_path: Path,
        model_path: Path,
        evidence_accounting_path: Path,
        evidence_index_path: Path,
        profile_path: Path,
        curator_input_path: Path,
        source_export_path: Path,
    ) -> list[PublicationValidationFinding]:
        required_paths = (
            ("missing_source_export", source_export_path, "Publication source export is missing."),
            ("missing_profile", profile_path, "Publication profile is missing."),
            ("missing_evidence_index", evidence_index_path, "Publication evidence index is missing."),
            ("missing_curator_packet", curator_input_path, "Publication curator packet is missing."),
            ("missing_model", model_path, "Publication model is missing."),
            ("missing_evidence_accounting", evidence_accounting_path, "Publication evidence accounting is missing."),
            ("missing_curated", markdown_path, "Publication Markdown is missing."),
        )
        return [_error(code, message, path) for code, path, message in required_paths if not path.exists()]

    def _append_chain_findings(
        self,
        *,
        manifest: Mapping[str, object],
        source_export_path: Path,
        curator_input_path: Path,
        markdown_path: Path,
        model_path: Path,
        evidence_accounting_path: Path,
        evidence_index_path: Path,
        profile_path: Path,
        findings: list[PublicationValidationFinding],
    ) -> dict[str, object]:
        stages = _mapping(manifest.get("stages"))
        for stage_name, path in (
            ("source_export", source_export_path),
            ("profile", profile_path),
            ("evidence_index", evidence_index_path),
            ("curator_packet", curator_input_path),
            ("model", model_path),
            ("evidence_accounting", evidence_accounting_path),
            ("curated", markdown_path),
        ):
            stage = _mapping(stages.get(stage_name))
            if str(stage.get("sha256") or "") != physical_sha256(path):
                findings.append(
                    _error(
                        f"{stage_name}_hash_mismatch",
                        f"Publication {stage_name} hash differs from the manifest.",
                        path,
                    )
                )

        source_stage = _mapping(stages.get("source_export"))
        evidence_stage = _mapping(stages.get("evidence_index"))
        packet_stage = _mapping(stages.get("curator_packet"))
        _append_binding_findings(
            findings,
            evidence_stage,
            {
                "source_fingerprint_sha256": str(source_stage.get("source_fingerprint_sha256") or ""),
                "source_sha256": physical_sha256(source_export_path),
            },
            path=evidence_index_path,
            stage="evidence_index",
        )
        _append_binding_findings(
            findings,
            packet_stage,
            {
                "source_fingerprint_sha256": str(source_stage.get("source_fingerprint_sha256") or ""),
                "source_sha256": physical_sha256(source_export_path),
                "evidence_sha256": physical_sha256(evidence_index_path),
                "profile_sha256": physical_sha256(profile_path),
            },
            path=curator_input_path,
            stage="curator_packet",
        )
        return packet_stage

    def _validated_contract_payloads(
        self,
        *,
        edition: PublicationEdition,
        packet_stage: Mapping[str, object],
        model_path: Path,
        evidence_accounting_path: Path,
        evidence_index_path: Path,
        profile_path: Path,
        findings: list[PublicationValidationFinding],
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        evidence_index: dict[str, object] = {}
        profile: dict[str, object] = {}
        model: dict[str, object] = {}
        try:
            evidence_index = read_publication_yaml(evidence_index_path, label="publication evidence index")
            validate_publication_evidence_index(evidence_index)
            profile = read_publication_yaml(profile_path, label="publication profile")
            model = read_publication_yaml(model_path, label="publication model")
            accounting = read_publication_yaml(
                evidence_accounting_path,
                label="publication evidence accounting",
            )
            validate_publication_profile(profile, edition=edition)
            expected_bindings = {
                "curator_packet_sha256": str(packet_stage.get("sha256") or ""),
                "evidence_index_sha256": str(packet_stage.get("evidence_semantic_sha256") or ""),
                "source_export_sha256": str(packet_stage.get("source_sha256") or ""),
                "source_fingerprint_sha256": str(packet_stage.get("source_fingerprint_sha256") or ""),
                "profile_sha256": str(packet_stage.get("profile_sha256") or ""),
            }
            validated_model = validate_publication_model(
                model,
                edition=edition,
                expected_bindings=expected_bindings,
                evidence_index=evidence_index,
            )
            validate_model_contributions(
                validated_model,
                profile=profile,
                evidence_index=evidence_index,
            )
            validate_evidence_accounting(
                accounting,
                edition=edition,
                evidence_index=evidence_index,
                model=validated_model,
                model_sha256=physical_sha256(model_path),
            )
            self._contribution_findings(
                profile,
                evidence_index,
                model,
                findings,
                model_path,
            )
        except ValueError as exc:
            findings.append(_error("publication_contract_invalid", str(exc)))
        return evidence_index, profile, model

    def _contribution_findings(
        self,
        profile: Mapping[str, object],
        evidence_index: Mapping[str, object],
        model: Mapping[str, object],
        findings: list[PublicationValidationFinding],
        path: Path,
    ) -> None:
        editorial = _mapping(profile.get("editorial"))
        include = bool(editorial.get("include_contributions"))
        expected = _mapping(evidence_index.get("contributions"))
        actual = model.get("contributions")
        if include and not isinstance(actual, Mapping):
            findings.append(_error("contributions_missing", "Publication model must include the prepared contribution summary.", path))
            return
        if not include and isinstance(actual, Mapping):
            findings.append(_error("contributions_unexpected", "Publication model includes Contributions while the profile omits it.", path))
            return
        if include and isinstance(actual, Mapping):
            expected_rows = expected.get("rows")
            actual_rows = actual.get("rows")
            if actual_rows != expected_rows:
                findings.append(_error("contributions_mismatch", "Publication model contribution figures differ from prepared evidence.", path))
            limitation = str(actual.get("reader_limitation") or "").strip()
            if not limitation:
                findings.append(_error("contributions_limitation_missing", "Contribution summary must preserve the metric limitation.", path))

    def _document_contract_findings(
        self,
        text: str,
        path: Path,
        edition: PublicationEdition,
        model: Mapping[str, object],
        profile: Mapping[str, object],
        evidence_index: Mapping[str, object],
    ) -> list[PublicationValidationFinding]:
        findings: list[PublicationValidationFinding] = []
        if not text.strip():
            findings.append(_error("empty_document", "Publication Markdown must not be empty.", path, 1))
            return findings
        h1_lines = [(index, line) for index, line in _numbered_lines(text) if line.startswith("# ")]
        if len(h1_lines) != 1:
            findings.append(_error("single_h1_required", "Publication must contain exactly one H1.", path, h1_lines[0][0] if h1_lines else 1))
        if text.count("```") % 2 != 0:
            findings.append(_error("markdown_unclosed_fence", "Markdown contains an unclosed fenced code block.", path))

        prose = _without_fenced_code(text)
        match = _INTERNAL_ID.search(prose)
        if match:
            findings.append(
                _error(
                    "internal_traceability_id",
                    f"Reader prose contains internal workflow ID {match.group(0)}.",
                    path,
                    _line_for_offset(prose, match.start()),
                )
            )
        if _WORKFLOW_HEADING.search(prose):
            findings.append(_warning("probable_workflow_narration", "Document headings appear to expose upstream planning workflow.", path))
        governance_match = _GOVERNANCE_NARRATION.search(prose)
        if governance_match:
            findings.append(
                _warning(
                    "probable_governance_narration",
                    "Document appears to narrate upstream governance mechanics.",
                    path,
                    _line_for_offset(prose, governance_match.start()),
                )
            )
        chronology_match = _PROPOSAL_CHRONOLOGY.search(prose)
        if chronology_match:
            findings.append(
                _warning(
                    "probable_proposal_chronology",
                    "Document appears to organize project content as proposal chronology.",
                    path,
                    _line_for_offset(prose, chronology_match.start()),
                )
            )
        if re.search(r"\.p2p/.*(?:authoritative|source of truth)|source of truth.*\.p2p/", prose, flags=re.IGNORECASE):
            findings.append(_warning("source_of_truth_boilerplate", "Reader prose contains upstream source-of-truth boilerplate.", path))
        if any(re.search(pattern, prose, flags=re.IGNORECASE) for pattern in _PLACEHOLDER_PATTERNS):
            findings.append(_warning("placeholder_text", "Document contains known placeholder text.", path))
        if re.search(r"\breadiness\s+(?:score|percentage|percent|%)", prose, flags=re.IGNORECASE):
            findings.append(_warning("readiness_narration", "Document appears to expose project readiness mechanics.", path))
        if _has_long_chapter(prose):
            findings.append(_advisory("long_chapter", "One or more chapters are unusually long.", path))
        if _probable_language_mismatch(prose, edition.language):
            findings.append(_advisory("probable_language_mismatch", "Document language may not match the selected edition.", path))

        project = _mapping(model.get("project"))
        title = str(project.get("title") or "").strip()
        if title and h1_lines and title.casefold() not in h1_lines[0][1].casefold():
            findings.append(_advisory("project_title_mismatch", "Document H1 does not clearly match the publication model title.", path, h1_lines[0][0]))
        if not re.search(r"^##\s+\S", prose, flags=re.MULTILINE):
            findings.append(_advisory("weak_structure", "Document has no developed second-level sections.", path))
        findings.extend(_model_prose_findings(prose, path, model, evidence_index))
        findings.extend(
            self._contribution_document_findings(
                prose,
                path,
                profile,
                model,
                evidence_index,
            )
        )
        return findings

    def _contribution_document_findings(
        self,
        text: str,
        path: Path,
        profile: Mapping[str, object],
        model: Mapping[str, object],
        evidence_index: Mapping[str, object],
    ) -> list[PublicationValidationFinding]:
        findings: list[PublicationValidationFinding] = []
        include = bool(_mapping(profile.get("editorial")).get("include_contributions"))
        contribution = model.get("contributions")
        outline = model.get("outline")
        outline_items = [dict(item) for item in outline if isinstance(item, Mapping)] if isinstance(outline, list) else []
        contribution_sections = [
            item for item in outline_items if str(item.get("role") or "") == "contributions"
        ]
        probable_heading = re.search(
            r"^##\s+(?:contributions?|contributors?|contributi|contributori)\s*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not include:
            if probable_heading:
                findings.append(
                    _error(
                        "contributions_unexpected",
                        "Reader document includes a Contributions chapter while the profile omits it.",
                        path,
                        _line_for_offset(text, probable_heading.start()),
                    )
                )
            return findings
        if not isinstance(contribution, Mapping):
            return findings
        if not contribution_sections:
            findings.append(
                _error(
                    "contributions_outline_missing",
                    "Publication model must assign a localized outline section the contributions role.",
                    path,
                )
            )
        else:
            heading = str(contribution_sections[0].get("heading") or "").strip()
            if heading and not re.search(rf"^##\s+{re.escape(heading)}\s*$", text, flags=re.MULTILINE):
                findings.append(
                    _error(
                        "contributions_chapter_missing",
                        "Reader document is missing the model-declared Contributions chapter.",
                        path,
                    )
                )
        prepared = _mapping(evidence_index.get("contributions"))
        rows = prepared.get("rows")
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                author = str(row.get("author") or "")
                percentage = str(row.get("percentage") or "")
                if author and percentage and (author not in text or percentage not in text):
                    findings.append(
                        _error(
                            "contributions_figures_missing",
                            f"Reader document does not preserve the prepared contribution figure for {author}.",
                            path,
                        )
                    )
        reader_limitation = str(contribution.get("reader_limitation") or "").strip()
        if not reader_limitation or reader_limitation.casefold() not in text.casefold():
            findings.append(
                _error(
                    "contributions_limitation_missing",
                    "Reader document must preserve the model's localized contribution limitation.",
                    path,
                )
            )
        if re.search(
            r"\b(?:share of effort|ownership share|intellectual property share|merit share)\b",
            text,
            flags=re.IGNORECASE,
        ):
            findings.append(
                _error(
                    "contributions_forbidden_interpretation",
                    "Contribution records must not be described as effort, ownership, merit, or IP shares.",
                    path,
                )
            )
        return findings

    def _result(
        self,
        edition: PublicationEdition,
        markdown_path: Path,
        model_path: Path,
        evidence_accounting_path: Path,
        profile_path: Path,
        findings: list[PublicationValidationFinding],
    ) -> PublicationValidationResult:
        status = "failed" if any(finding.severity == "error" for finding in findings) else "passed"
        paths = resolve_publication_paths(self.root, edition)
        normalized_findings = [
            replace(finding, path=_relative(finding.path, self.root))
            if finding.path is not None
            else finding
            for finding in findings
        ]
        return PublicationValidationResult(
            schema_version=PUBLICATION_CONTRACT_VERSION,
            status=status,
            validated_at=date.today().isoformat(),
            edition=edition,
            input=_relative(markdown_path, self.root),
            curated_sha256=physical_sha256(markdown_path) if markdown_path.exists() else "",
            model=_relative(model_path, self.root),
            model_sha256=physical_sha256(model_path) if model_path.exists() else "",
            evidence_accounting=_relative(evidence_accounting_path, self.root),
            evidence_accounting_sha256=(
                physical_sha256(evidence_accounting_path) if evidence_accounting_path.exists() else ""
            ),
            profile=_relative(profile_path, self.root),
            profile_sha256=physical_sha256(profile_path) if profile_path.exists() else "",
            source_export=_relative(paths.source_export, self.root),
            source_export_sha256=(
                physical_sha256(paths.source_export) if paths.source_export.exists() else ""
            ),
            curator_input=_relative(paths.curator_input, self.root),
            curator_input_sha256=(
                physical_sha256(paths.curator_input) if paths.curator_input.exists() else ""
            ),
            evidence_index=_relative(paths.evidence_index, self.root),
            evidence_index_sha256=(
                physical_sha256(paths.evidence_index) if paths.evidence_index.exists() else ""
            ),
            manifest=_relative(paths.manifest, self.root),
            publication_contract_version=PUBLICATION_CONTRACT_VERSION,
            validator_version=PUBLICATION_VALIDATOR_VERSION,
            findings=normalized_findings,
        )


def validation_result_payload(result: PublicationValidationResult) -> dict[str, object]:
    return {
        "schema_version": result.schema_version,
        "status": result.status,
        "validated_at": result.validated_at,
        "edition": result.edition.to_dict(),
        "input": result.input.as_posix(),
        "curated_sha256": result.curated_sha256,
        "model": result.model.as_posix(),
        "model_sha256": result.model_sha256,
        "evidence_accounting": result.evidence_accounting.as_posix(),
        "evidence_accounting_sha256": result.evidence_accounting_sha256,
        "profile": result.profile.as_posix(),
        "profile_sha256": result.profile_sha256,
        "source_export": result.source_export.as_posix(),
        "source_export_sha256": result.source_export_sha256,
        "curator_input": result.curator_input.as_posix(),
        "curator_input_sha256": result.curator_input_sha256,
        "evidence_index": result.evidence_index.as_posix(),
        "evidence_index_sha256": result.evidence_index_sha256,
        "manifest": result.manifest.as_posix(),
        "publication_contract_version": result.publication_contract_version,
        "validator_version": result.validator_version,
        "findings": [
            {
                "severity": finding.severity,
                "code": finding.code,
                "message": finding.message,
                **({"path": finding.path.as_posix()} if finding.path is not None else {}),
                **({"line": finding.line} if finding.line is not None else {}),
            }
            for finding in result.findings
        ],
    }


def _error(
    code: str,
    message: str,
    path: Path | None = None,
    line: int | None = None,
) -> PublicationValidationFinding:
    return PublicationValidationFinding("error", code, message, path, line)


def _warning(
    code: str,
    message: str,
    path: Path | None = None,
    line: int | None = None,
) -> PublicationValidationFinding:
    return PublicationValidationFinding("warning", code, message, path, line)


def _advisory(
    code: str,
    message: str,
    path: Path | None = None,
    line: int | None = None,
) -> PublicationValidationFinding:
    return PublicationValidationFinding("advisory", code, message, path, line)


def _append_binding_findings(
    findings: list[PublicationValidationFinding],
    recorded: Mapping[str, object],
    expected: Mapping[str, str],
    *,
    path: Path,
    stage: str,
) -> None:
    for key, expected_value in expected.items():
        if not expected_value or str(recorded.get(key) or "") != expected_value:
            findings.append(
                _error(
                    f"{stage}_{key}_mismatch",
                    f"Publication {stage} binding {key} is missing or stale.",
                    path,
                )
            )


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _numbered_lines(text: str) -> list[tuple[int, str]]:
    return list(enumerate(text.splitlines(), start=1))


def _without_fenced_code(text: str) -> str:
    lines = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            lines.append("")
            continue
        lines.append("" if fenced else line)
    return "\n".join(lines)


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _has_long_chapter(text: str) -> bool:
    sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
    return any(len(section.split()) > 1800 for section in sections[1:])


def _probable_language_mismatch(text: str, language: str) -> bool:
    primary = language.split("-", 1)[0]
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if len(words) < 80 or primary not in {"en", "it"}:
        return False
    english = sum(word in {"the", "and", "project", "with", "for", "from", "that"} for word in words)
    italian = sum(word in {"il", "la", "e", "progetto", "con", "per", "dal", "che"} for word in words)
    return (primary == "en" and italian > english * 2) or (primary == "it" and english > italian * 2)


def _model_prose_findings(
    text: str,
    path: Path,
    model: Mapping[str, object],
    evidence_index: Mapping[str, object],
) -> list[PublicationValidationFinding]:
    findings: list[PublicationValidationFinding] = []
    normalized = text.casefold()
    outline = model.get("outline")
    outline_items = [dict(item) for item in outline if isinstance(item, Mapping)] if isinstance(outline, list) else []
    missing_headings = [
        str(item.get("heading") or "").strip()
        for item in outline_items
        if str(item.get("heading") or "").strip()
        and not re.search(
            rf"^#{{1,6}}\s+{re.escape(str(item.get('heading') or '').strip())}\s*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    ]
    if missing_headings:
        findings.append(
            _advisory(
                "model_outline_prose_mismatch",
                "Reader document may not reflect model outline headings: "
                + ", ".join(missing_headings[:5]),
                path,
            )
        )
    claims = model.get("claims")
    claim_items = [dict(item) for item in claims if isinstance(item, Mapping)] if isinstance(claims, list) else []
    unmatched_claims = []
    for item in claim_items:
        statement = str(item.get("statement") or "")
        tokens = {
            token.casefold()
            for token in re.findall(r"[^\W\d_]{4,}", statement, flags=re.UNICODE)
        }
        if tokens and not any(token in normalized for token in tokens):
            unmatched_claims.append(str(item.get("id") or "unknown"))
    if unmatched_claims:
        findings.append(
            _advisory(
                "model_claim_prose_mismatch",
                "Reader document may omit model claims; inspect sidecar IDs: "
                + ", ".join(unmatched_claims[:10]),
                path,
            )
        )
    vertical = _mapping(evidence_index.get("vertical"))
    required = vertical.get("required_sections")
    required_count = len(required) if isinstance(required, list) else 0
    heading_count = len(re.findall(r"^##\s+\S", text, flags=re.MULTILINE))
    if bool(vertical.get("available")) and required_count > 1 and heading_count < 2:
        findings.append(
            _advisory(
                "weak_vertical_framing",
                "Reader document may be too shallow for the active vertical.",
                path,
            )
        )
    return findings


def _relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path

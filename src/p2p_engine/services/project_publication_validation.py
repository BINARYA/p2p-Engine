from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


VALIDATOR_VERSION = "publication-validator-v1"
_PLACEHOLDER_PATTERNS = (
    r"\bTBD\b",
    r"\bTODO\b",
    r"\bnot recorded\b",
    r"\bpending\.",
    r"\blorem ipsum\b",
)


@dataclass(frozen=True)
class PublicationValidationFinding:
    severity: str
    code: str
    message: str
    line: int | None = None


@dataclass(frozen=True)
class PublicationValidationResult:
    schema_version: int
    status: str
    validated_at: str
    input: Path
    curated_sha256: str
    profile: Path
    profile_sha256: str
    validator_version: str
    findings: list[PublicationValidationFinding] = field(default_factory=list)


class ProjectPublicationValidator:
    def __init__(self, *, root: Path) -> None:
        self.root = root

    def validate(
        self,
        *,
        curated_path: Path,
        profile_path: Path,
        manifest_path: Path,
        manifest: dict[str, object],
        curated_sha256: str,
        profile_sha256: str,
    ) -> PublicationValidationResult:
        findings: list[PublicationValidationFinding] = []
        stages = _as_mapping(manifest.get("stages"))
        source_stage = _as_mapping(stages.get("source_export"))
        profile_stage = _as_mapping(stages.get("profile"))
        curated_stage = _as_mapping(stages.get("curated"))

        if not manifest_path.exists():
            findings.append(_error("invalid_manifest", "Publication manifest is missing."))
        if manifest.get("pipeline") != "human_project_publication":
            findings.append(_error("invalid_manifest", "Publication manifest pipeline is invalid."))
        if not profile_path.exists():
            findings.append(_error("invalid_profile", "Publication profile is missing."))
        elif profile_stage.get("sha256") != profile_sha256:
            findings.append(_error("profile_hash_mismatch", "Publication profile hash differs from manifest."))

        for key in ("source_fingerprint_sha256", "sha256"):
            if not source_stage.get(key):
                findings.append(_error("missing_source_hash", f"Source export manifest stage is missing {key}."))
        for key in ("source_fingerprint_sha256", "source_sha256", "profile_sha256", "sha256"):
            if not curated_stage.get(key):
                findings.append(_error("missing_curated_hash", f"Curated manifest stage is missing {key}."))

        if not _safe_output_path(curated_path, self.root):
            findings.append(_error("unsafe_output_path", "Curated publication path must stay under outputs/latest."))
        if not curated_path.exists():
            findings.append(_error("missing_curated", "Curated publication Markdown is missing."))
            return self._result(curated_path, curated_sha256, profile_path, profile_sha256, findings)
        if curated_stage.get("sha256") != curated_sha256:
            findings.append(_error("curated_hash_mismatch", "Curated Markdown hash differs from manifest."))

        text = curated_path.read_text(encoding="utf-8")
        findings.extend(self._document_contract_findings(text))
        return self._result(curated_path, curated_sha256, profile_path, profile_sha256, findings)

    def _document_contract_findings(self, text: str) -> list[PublicationValidationFinding]:
        findings: list[PublicationValidationFinding] = []
        h1_lines = [(index, line) for index, line in _numbered_lines(text) if line.startswith("# ")]
        if len(h1_lines) != 1:
            line = h1_lines[0][0] if h1_lines else 1
            findings.append(_error("single_h1_required", "Curated document must contain exactly one H1.", line))
        if not _has_heading(text, "Executive Summary"):
            findings.append(_error("executive_summary_missing", "Curated document must include an Executive Summary section."))
        if not _has_source_of_truth_statement(text):
            findings.append(_error("source_of_truth_missing", "Curated document must state that .p2p/ remains authoritative."))
        if text.count("```") % 2 != 0:
            findings.append(_error("markdown_unclosed_fence", "Markdown contains an unclosed fenced code block."))
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _PLACEHOLDER_PATTERNS):
            findings.append(_warning("placeholder_text", "Document contains known placeholder text."))

        prop_heading_count = len(re.findall(r"^#+\s+PROP-\d+", text, flags=re.MULTILINE))
        if prop_heading_count >= 3:
            findings.append(
                _warning(
                    "probable_proposal_dump",
                    "Document appears to mirror proposal headings instead of a project-first structure.",
                )
            )
        if len(re.findall(r"\bPROP-\d+\b", text)) < 1 and ".p2p" not in text:
            findings.append(_advisory("weak_traceability", "Document has weak visible source traceability."))
        if len(re.findall(r"^#+\s+PROP-\d+", text, flags=re.MULTILINE)) > 1:
            findings.append(_warning("repeated_prop_headings", "Main body repeats proposal headings."))
        if _has_long_chapter(text):
            findings.append(_advisory("long_chapter", "One or more chapters are unusually long."))
        if not re.search(r"\b(current|implemented|planned|pending|missing|legacy)\b", text, flags=re.IGNORECASE):
            findings.append(
                _advisory(
                    "weak_state_distinctions",
                    "Document does not clearly signal current/planned/pending/missing state distinctions.",
                )
            )
        if not re.search(r"\b(vertical|domain|settore|contesto|prodotto|project)\b", text, flags=re.IGNORECASE):
            findings.append(_advisory("weak_vertical_framing", "Document has weak apparent vertical/domain framing."))
        return findings

    def _result(
        self,
        curated_path: Path,
        curated_sha256: str,
        profile_path: Path,
        profile_sha256: str,
        findings: list[PublicationValidationFinding],
    ) -> PublicationValidationResult:
        status = "failed" if any(finding.severity == "error" for finding in findings) else "passed"
        return PublicationValidationResult(
            schema_version=1,
            status=status,
            validated_at=date.today().isoformat(),
            input=_relative(curated_path, self.root),
            curated_sha256=curated_sha256,
            profile=_relative(profile_path, self.root),
            profile_sha256=profile_sha256,
            validator_version=VALIDATOR_VERSION,
            findings=findings,
        )


def validation_result_payload(result: PublicationValidationResult) -> dict[str, object]:
    return {
        "schema_version": result.schema_version,
        "status": result.status,
        "validated_at": result.validated_at,
        "input": result.input.as_posix(),
        "curated_sha256": result.curated_sha256,
        "profile": result.profile.as_posix(),
        "profile_sha256": result.profile_sha256,
        "validator_version": result.validator_version,
        "findings": [
            {
                "severity": finding.severity,
                "code": finding.code,
                "message": finding.message,
                **({"line": finding.line} if finding.line is not None else {}),
            }
            for finding in result.findings
        ],
    }


def _error(code: str, message: str, line: int | None = None) -> PublicationValidationFinding:
    return PublicationValidationFinding(severity="error", code=code, message=message, line=line)


def _warning(code: str, message: str, line: int | None = None) -> PublicationValidationFinding:
    return PublicationValidationFinding(severity="warning", code=code, message=message, line=line)


def _advisory(code: str, message: str, line: int | None = None) -> PublicationValidationFinding:
    return PublicationValidationFinding(severity="advisory", code=code, message=message, line=line)


def _as_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _numbered_lines(text: str) -> list[tuple[int, str]]:
    return [(index, line) for index, line in enumerate(text.splitlines(), start=1)]


def _has_heading(text: str, heading: str) -> bool:
    return re.search(rf"^##\s+{re.escape(heading)}\s*$", text, flags=re.IGNORECASE | re.MULTILINE) is not None


def _has_source_of_truth_statement(text: str) -> bool:
    return bool(re.search(r"\.p2p/?", text) and re.search(r"(authoritative|source[- ]of[- ]truth|fonte)", text, re.IGNORECASE))


def _has_long_chapter(text: str) -> bool:
    chapters = re.split(r"^##\s+", text, flags=re.MULTILINE)
    return any(len(chapter.split()) > 1200 for chapter in chapters)


def _safe_output_path(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to((root / "outputs" / "latest").resolve())
    except ValueError:
        return False
    return True


def _relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path

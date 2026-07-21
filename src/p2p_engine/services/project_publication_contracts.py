from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping, Sequence

from p2p_engine.core.project_publication import (
    EVIDENCE_DISPOSITIONS,
    PUBLICATION_ACCOUNTING_VERSION,
    PUBLICATION_CATALOG_VERSION,
    PUBLICATION_CONTRACT_VERSION,
    PUBLICATION_EDITORIAL_EVALUATION_VERSION,
    PUBLICATION_EDITORIAL_RUBRIC_VERSION,
    PUBLICATION_EVIDENCE_GENERATOR,
    PUBLICATION_MODEL_VERSION,
    PUBLICATION_PROFILE_ID,
    PublicationEdition,
    normalize_contribution_policy,
)
from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml_mapping


_VERTICAL_DISPOSITIONS = {"covered", "combined", "unsupported", "not_applicable"}
_EDITORIAL_DIMENSIONS = {
    "autonomy",
    "vertical_coherence",
    "evidence_use",
    "language_consistency",
    "structure",
    "reader_usefulness",
}
_EVALUATION_KINDS = {"self", "independent", "owner"}


def validate_publication_profile(
    payload: Mapping[str, object],
    *,
    edition: PublicationEdition,
) -> dict[str, object]:
    _require_version(payload, PUBLICATION_CONTRACT_VERSION, "publication profile")
    if str(payload.get("profile_id") or "") != PUBLICATION_PROFILE_ID:
        raise ValueError("Publication profile ID is unsupported.")
    raw_edition = _mapping(payload.get("edition"), "publication profile edition")
    expected_edition = edition.to_dict()
    for key, expected in expected_edition.items():
        if str(raw_edition.get(key) or "") != expected:
            raise ValueError(f"Publication profile edition {key} does not match the selected edition.")
    reader = _mapping(payload.get("reader"), "publication profile reader")
    if str(reader.get("knowledge_of_p2p") or "") != "none":
        raise ValueError("Publication profile reader must not require P2P knowledge.")
    if reader.get("audience_variant") is not False:
        raise ValueError("Publication language editions cannot be audience variants.")
    editorial = _mapping(payload.get("editorial"), "publication profile editorial policy")
    if str(editorial.get("structure") or "") != "vertical_adaptive":
        raise ValueError("Publication profile must use vertical-adaptive structure.")
    if editorial.get("traceability_in_body") is not False:
        raise ValueError("Publication profile must keep traceability outside reader prose.")
    policy = normalize_contribution_policy(str(editorial.get("contributions") or ""))
    include = editorial.get("include_contributions")
    if not isinstance(include, bool):
        raise ValueError("Publication profile include_contributions must be boolean.")
    if (policy == "include" and not include) or (policy == "omit" and include):
        raise ValueError("Publication contribution policy conflicts with include_contributions.")
    render = _mapping(payload.get("render"), "publication profile render policy")
    if str(render.get("theme") or "") != "neutral-v1":
        raise ValueError("Publication profile render theme is unsupported.")
    return dict(payload)


def validate_publication_catalog(payload: Mapping[str, object]) -> dict[str, object]:
    _require_version(payload, PUBLICATION_CATALOG_VERSION, "publication catalog")
    editions = _mapping_list(payload.get("editions"), "publication catalog editions")
    seen: set[str] = set()
    previous: tuple[str, str] | None = None
    for row in editions:
        raw = _mapping(row.get("edition"), "publication catalog edition")
        edition = PublicationEdition.create(
            language=str(raw.get("language") or ""),
            output_name=str(raw.get("output_name") or ""),
        )
        if raw != edition.to_dict():
            raise ValueError(f"Publication catalog edition {edition.edition_key} is not canonical.")
        if edition.edition_key in seen:
            raise ValueError(f"Duplicate publication catalog edition: {edition.edition_key}")
        seen.add(edition.edition_key)
        order = (edition.output_name, edition.language)
        if previous is not None and order < previous:
            raise ValueError("Publication catalog editions are not in stable order.")
        previous = order
        _required_text(row, "manifest", f"publication catalog edition {edition.edition_key}")
    _mapping_list(payload.get("diagnostics"), "publication catalog diagnostics")
    return dict(payload)


def read_publication_yaml(path: Path, *, label: str) -> dict[str, object]:
    try:
        content = path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"{label} is missing: {path}") from exc
    try:
        return load_yaml_mapping(content, loader_contract=UNIQUE_LOADER_CONTRACT)
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} must be UTF-8 YAML: {path}") from exc
    except ValueError as exc:
        raise ValueError(f"Invalid {label}: {exc}") from exc


def validate_publication_evidence_index(payload: Mapping[str, object]) -> dict[str, object]:
    _require_version(payload, PUBLICATION_CONTRACT_VERSION, "publication evidence index")
    if str(payload.get("generator") or "") != PUBLICATION_EVIDENCE_GENERATOR:
        raise ValueError("Publication evidence generator is unsupported.")
    _required_sha256(payload, "source_fingerprint_sha256", "publication evidence index")
    source_export = _mapping(payload.get("source_export"), "publication evidence source export")
    _required_text(source_export, "path", "publication evidence source export")
    _required_sha256(source_export, "sha256", "publication evidence source export")
    source_catalog = _mapping(payload.get("source_catalog"), "publication evidence source catalog")
    sources = _mapping_list(source_catalog.get("sources"), "publication evidence sources")
    source_paths = _unique_records(sources, "path", "publication evidence source")
    for path, source in source_paths.items():
        _required_sha256(source, "sha256", f"publication evidence source {path}")
    if int(source_catalog.get("source_count") or -1) != len(sources):
        raise ValueError("Publication evidence source count does not match the source catalog.")
    entries = _mapping_list(payload.get("entries"), "publication evidence entries")
    entries_by_id = _unique_records(entries, "id", "publication evidence")
    for evidence_id, entry in entries_by_id.items():
        for key in (
            "kind",
            "authority_class",
            "editorial_class",
            "source_path",
            "source_selector",
            "content_mode",
        ):
            _required_text(entry, key, f"publication evidence {evidence_id}")
        _required_sha256(entry, "semantic_sha256", f"publication evidence {evidence_id}")
        if str(entry.get("content_mode") or "") != "inline_complete":
            raise ValueError(
                f"Publication evidence {evidence_id} uses an unsupported content mode."
            )
        _mapping(entry.get("payload"), f"publication evidence {evidence_id} payload")
        sections = entry.get("vertical_sections")
        if not isinstance(sections, list) or any(not isinstance(item, str) for item in sections):
            raise ValueError(
                f"Publication evidence {evidence_id} vertical_sections must be a string list."
            )
    counts = _mapping(payload.get("counts"), "publication evidence counts")
    if int(counts.get("total") or -1) != len(entries):
        raise ValueError("Publication evidence total count does not match its entries.")
    recorded = str(payload.get("semantic_sha256") or "")
    content = dict(payload)
    content.pop("semantic_sha256", None)
    if not recorded or semantic_sha256(content) != recorded:
        raise ValueError("Publication evidence semantic hash is missing or stale.")
    return dict(payload)


def validate_publication_model(
    payload: Mapping[str, object],
    *,
    edition: PublicationEdition,
    expected_bindings: Mapping[str, str],
    evidence_index: Mapping[str, object],
) -> dict[str, object]:
    _require_version(payload, PUBLICATION_MODEL_VERSION, "publication model")
    _require_edition(payload, edition, "publication model")
    _require_bindings(payload, expected_bindings, "publication model")

    _validate_model_project(payload, evidence_index)
    evidence_by_id = _evidence_by_id(evidence_index)
    claims_by_id = _validate_model_claims(payload, evidence_by_id)
    _validate_reader_questions(payload, set(claims_by_id))
    outline_ids = _validate_model_outline(payload, set(claims_by_id))
    _validate_vertical_coverage(payload, evidence_index, outline_ids)
    _validate_editorial_assessment(payload)
    return dict(payload)


def _validate_model_project(
    payload: Mapping[str, object],
    evidence_index: Mapping[str, object],
) -> None:
    project = _mapping(payload.get("project"), "publication model project")
    _required_text(project, "title", "publication model project")
    _required_text(project, "thesis", "publication model project")
    vertical = _mapping(evidence_index.get("vertical"), "publication evidence vertical")
    model_vertical_id = _required_text(project, "vertical_id", "publication model project")
    if bool(vertical.get("available")):
        if model_vertical_id != str(vertical.get("id") or ""):
            raise ValueError("Publication model vertical ID does not match prepared evidence.")
    else:
        if model_vertical_id != "generic":
            raise ValueError("Publication model without vertical guidance must use vertical_id generic.")
        _required_text(
            project,
            "vertical_guidance_unavailable_reason",
            "publication model project",
        )


def _validate_model_claims(
    payload: Mapping[str, object],
    evidence_by_id: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    claims = _mapping_list(payload.get("claims"), "publication model claims")
    claims_by_id = _unique_records(claims, "id", "publication model claim")
    if not claims_by_id:
        raise ValueError("Publication model must contain at least one claim.")
    for claim_id, claim in claims_by_id.items():
        _required_text(claim, "statement", f"publication model claim {claim_id}")
        evidence_ids = _unique_text_list(
            claim.get("evidence_ids"),
            f"claim {claim_id} evidence_ids",
        )
        owner_input = claim.get("owner_input")
        if not evidence_ids and not isinstance(owner_input, Mapping):
            raise ValueError(f"Publication model claim {claim_id} has no evidence or owner input provenance.")
        unknown = sorted(set(evidence_ids) - set(evidence_by_id))
        if unknown:
            raise ValueError(
                f"Publication model claim {claim_id} references unknown evidence: {', '.join(unknown)}"
            )
        for evidence_id in evidence_ids:
            editorial_class = str(evidence_by_id[evidence_id].get("editorial_class") or "")
            if editorial_class in {
                "process_only",
                "historical_context",
                "duplicate",
                "contradictory",
                "insufficient",
            }:
                raise ValueError(
                    f"Publication model claim {claim_id} cannot use "
                    f"{editorial_class.replace('_', '-')} evidence {evidence_id}."
                )
        if isinstance(owner_input, Mapping):
            _required_text(owner_input, "source", f"claim {claim_id} owner_input")
    return claims_by_id


def _validate_reader_questions(
    payload: Mapping[str, object],
    claim_ids: set[str],
) -> None:
    questions = _mapping_list(payload.get("reader_questions"), "publication model reader_questions")
    questions_by_id = _unique_records(questions, "id", "reader question")
    if not questions_by_id:
        raise ValueError("Publication model must contain at least one reader question.")
    for question_id, question in questions_by_id.items():
        _required_text(question, "question", f"reader question {question_id}")
        _require_known_ids(
            _unique_text_list(
                question.get("answered_by"),
                f"reader question {question_id} answered_by",
            ),
            claim_ids,
            f"reader question {question_id}",
        )


def _validate_model_outline(
    payload: Mapping[str, object],
    claim_ids: set[str],
) -> set[str]:
    outline = _mapping_list(payload.get("outline"), "publication model outline")
    outline_by_id = _unique_records(outline, "id", "outline section")
    for section_id, section in outline_by_id.items():
        _required_text(section, "role", f"outline section {section_id}")
        _required_text(section, "heading", f"outline section {section_id}")
        _require_known_ids(
            _unique_text_list(
                section.get("claim_ids"),
                f"outline section {section_id} claim_ids",
            ),
            claim_ids,
            f"outline section {section_id}",
        )
    if not outline_by_id:
        raise ValueError("Publication model outline must contain at least one section.")
    return set(outline_by_id)


def _validate_vertical_coverage(
    payload: Mapping[str, object],
    evidence_index: Mapping[str, object],
    known_outline_ids: set[str],
) -> None:
    coverage = _mapping_list(payload.get("vertical_coverage"), "publication model vertical_coverage")
    coverage_by_id = _unique_records(coverage, "section_id", "vertical coverage")
    required_sections = _required_vertical_sections(evidence_index)
    missing_sections = sorted(required_sections - set(coverage_by_id))
    unknown_sections = sorted(set(coverage_by_id) - required_sections)
    if missing_sections:
        raise ValueError(
            "Publication model vertical coverage is missing required sections: "
            + ", ".join(missing_sections)
        )
    if unknown_sections:
        raise ValueError(
            "Publication model vertical coverage contains unknown sections: "
            + ", ".join(unknown_sections)
        )
    for section_id, item in coverage_by_id.items():
        disposition = str(item.get("disposition") or "")
        if disposition not in _VERTICAL_DISPOSITIONS:
            raise ValueError(
                f"Invalid vertical coverage disposition for {section_id}: {disposition}"
            )
        item_outline_ids = _unique_text_list(
            item.get("outline_ids"),
            f"vertical coverage {section_id} outline_ids",
        )
        if disposition in {"covered", "combined"} and not item_outline_ids:
            raise ValueError(f"Vertical coverage {section_id} requires an outline reference.")
        if disposition in {"unsupported", "not_applicable"}:
            _required_text(item, "reason", f"vertical coverage {section_id}")
        _require_known_ids(
            item_outline_ids,
            known_outline_ids,
            f"vertical coverage {section_id}",
        )


def _validate_editorial_assessment(payload: Mapping[str, object]) -> None:
    assessment = _mapping(payload.get("editorial_assessment"), "editorial assessment")
    if str(assessment.get("rubric_version") or "") != PUBLICATION_EDITORIAL_RUBRIC_VERSION:
        raise ValueError(
            "Publication model editorial assessment must use "
            f"{PUBLICATION_EDITORIAL_RUBRIC_VERSION}."
        )
    if not isinstance(assessment.get("results"), list):
        raise ValueError("Publication model editorial assessment results must be a list.")
    assessment_rows = _mapping_list(
        assessment.get("results"),
        "publication model editorial assessment results",
    )
    assessment_by_dimension = _unique_records(
        assessment_rows,
        "dimension",
        "editorial assessment dimension",
    )
    missing_dimensions = sorted(_EDITORIAL_DIMENSIONS - set(assessment_by_dimension))
    if missing_dimensions:
        raise ValueError(
            "Publication model editorial assessment is missing dimensions: "
            + ", ".join(missing_dimensions)
        )
    for dimension, row in assessment_by_dimension.items():
        if dimension not in _EDITORIAL_DIMENSIONS:
            raise ValueError(f"Unknown editorial assessment dimension: {dimension}")
        try:
            score = int(row.get("score") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid editorial assessment score for {dimension}.") from exc
        if score < 4 or score > 5:
            raise ValueError(
                f"Editorial assessment score for {dimension} must be between 4 and 5."
            )
        if str(row.get("evaluator") or "") != "self":
            raise ValueError(
                f"Candidate editorial assessment for {dimension} must be recorded as self."
            )


def validate_evidence_accounting(
    payload: Mapping[str, object],
    *,
    edition: PublicationEdition,
    evidence_index: Mapping[str, object],
    model: Mapping[str, object],
    model_sha256: str,
) -> dict[str, object]:
    _require_version(payload, PUBLICATION_ACCOUNTING_VERSION, "evidence accounting")
    if str(payload.get("edition_key") or "") != edition.edition_key:
        raise ValueError("Evidence accounting edition key does not match the selected edition.")
    bindings = _mapping(payload.get("bindings"), "evidence accounting bindings")
    expected_evidence_hash = str(evidence_index.get("semantic_sha256") or "")
    if str(bindings.get("model_sha256") or "") != model_sha256:
        raise ValueError("Evidence accounting model hash does not match the candidate model.")
    if str(bindings.get("evidence_index_sha256") or "") != expected_evidence_hash:
        raise ValueError("Evidence accounting evidence-index hash is stale.")

    evidence_by_id = _evidence_by_id(evidence_index)
    claims = _mapping_list(model.get("claims"), "publication model claims")
    claims_by_id = _unique_records(claims, "id", "publication model claim")
    accounting = _mapping_list(payload.get("evidence"), "evidence accounting records")
    accounting_by_id = _unique_records(accounting, "evidence_id", "evidence accounting record")
    expected_ids = set(evidence_by_id)
    actual_ids = set(accounting_by_id)
    missing = sorted(expected_ids - actual_ids)
    unknown = sorted(actual_ids - expected_ids)
    if missing:
        raise ValueError("Evidence accounting is incomplete; missing: " + ", ".join(missing))
    if unknown:
        raise ValueError("Evidence accounting contains unknown evidence: " + ", ".join(unknown))

    linked_pairs: set[tuple[str, str]] = set()
    for evidence_id, record in accounting_by_id.items():
        disposition = str(record.get("disposition") or "")
        if disposition not in EVIDENCE_DISPOSITIONS:
            raise ValueError(f"Invalid evidence disposition for {evidence_id}: {disposition}")
        source = evidence_by_id[evidence_id]
        editorial_class = str(source.get("editorial_class") or "")
        claim_ids = _unique_text_list(
            record.get("claim_ids"),
            f"accounting {evidence_id} claim_ids",
        )
        _require_known_ids(claim_ids, set(claims_by_id), f"accounting {evidence_id}")
        if editorial_class == "process_only" and disposition != "process_only":
            raise ValueError(f"Process-only evidence {evidence_id} must remain process_only.")
        if disposition == "process_only" and editorial_class != "process_only":
            raise ValueError(f"Project evidence {evidence_id} cannot be disposed as process_only.")
        required_disposition = {
            "historical_context": "historical",
            "duplicate": "duplicate",
            "contradictory": "contradictory",
            "insufficient": "insufficient",
        }.get(editorial_class)
        if required_disposition is not None and disposition != required_disposition:
            raise ValueError(
                f"{editorial_class.replace('_', ' ').title()} evidence {evidence_id} "
                f"must use disposition {required_disposition}."
            )
        if disposition == "used" and not claim_ids:
            raise ValueError(f"Used evidence {evidence_id} must reference at least one claim.")
        if disposition not in {"used", "supporting_context"}:
            if claim_ids:
                raise ValueError(
                    f"Excluded evidence {evidence_id} cannot reference publication claims."
                )
            _required_text(record, "reason", f"accounting {evidence_id}")
        for claim_id in claim_ids:
            linked_pairs.add((claim_id, evidence_id))

    model_pairs: set[tuple[str, str]] = set()
    for claim_id, claim in claims_by_id.items():
        for evidence_id in _text_list(claim.get("evidence_ids"), f"claim {claim_id} evidence_ids"):
            model_pairs.add((claim_id, evidence_id))
            if (claim_id, evidence_id) not in linked_pairs:
                raise ValueError(
                    f"Claim {claim_id} and evidence {evidence_id} are not linked by accounting."
                )
    extra_pairs = sorted(linked_pairs - model_pairs)
    if extra_pairs:
        claim_id, evidence_id = extra_pairs[0]
        raise ValueError(
            f"Accounting links claim {claim_id} to evidence {evidence_id}, "
            "but the publication model does not contain that link."
        )
    return dict(payload)


def validate_model_contributions(
    model: Mapping[str, object],
    *,
    profile: Mapping[str, object],
    evidence_index: Mapping[str, object],
) -> None:
    editorial = _mapping(profile.get("editorial"), "publication profile editorial policy")
    include = bool(editorial.get("include_contributions"))
    actual = model.get("contributions")
    outline = _mapping_list(model.get("outline"), "publication model outline")
    contribution_sections = [
        item for item in outline if str(item.get("role") or "") == "contributions"
    ]
    if not include:
        if isinstance(actual, Mapping) or contribution_sections:
            raise ValueError(
                "Publication model includes Contributions while the profile omits it."
            )
        return
    if not isinstance(actual, Mapping):
        raise ValueError("Publication model must include the prepared contribution summary.")
    expected = _mapping(evidence_index.get("contributions"), "publication contribution summary")
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            raise ValueError("Publication model contribution figures differ from prepared evidence.")
    _required_text(actual, "reader_limitation", "publication model contributions")
    if len(contribution_sections) != 1:
        raise ValueError(
            "Publication model must contain exactly one outline section with role contributions."
        )


def validate_editorial_evaluation(
    payload: Mapping[str, object],
    *,
    edition: PublicationEdition,
) -> dict[str, object]:
    _require_version(
        payload,
        PUBLICATION_EDITORIAL_EVALUATION_VERSION,
        "publication editorial evaluation",
    )
    if str(payload.get("rubric_version") or "") != PUBLICATION_EDITORIAL_RUBRIC_VERSION:
        raise ValueError("Editorial evaluation rubric version is unsupported.")
    if str(payload.get("edition_key") or "") != edition.edition_key:
        raise ValueError("Editorial evaluation edition key does not match the selected edition.")
    evaluation_kind = str(payload.get("evaluation_kind") or "")
    if evaluation_kind not in _EVALUATION_KINDS:
        raise ValueError(f"Invalid editorial evaluation kind: {evaluation_kind}")
    _required_text(payload, "evaluator", "editorial evaluation")
    scores = _mapping_list(payload.get("scores"), "editorial evaluation scores")
    scores_by_dimension = _unique_records(scores, "dimension", "editorial evaluation score")
    missing = sorted(_EDITORIAL_DIMENSIONS - set(scores_by_dimension))
    unknown = sorted(set(scores_by_dimension) - _EDITORIAL_DIMENSIONS)
    if missing:
        raise ValueError("Editorial evaluation is missing dimensions: " + ", ".join(missing))
    if unknown:
        raise ValueError("Editorial evaluation contains unknown dimensions: " + ", ".join(unknown))
    below_threshold = []
    for dimension, row in scores_by_dimension.items():
        try:
            score = int(row.get("score") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid editorial evaluation score for {dimension}.") from exc
        if score < 1 or score > 5:
            raise ValueError(f"Editorial evaluation score for {dimension} must be from 1 to 5.")
        if score < 4:
            below_threshold.append(dimension)
        _required_text(row, "rationale", f"editorial evaluation score {dimension}")
    failures = _text_list(
        payload.get("zero_tolerance_failures"),
        "editorial evaluation zero_tolerance_failures",
    )
    expected_status = "passed" if not below_threshold and not failures else "failed"
    if str(payload.get("status") or "") != expected_status:
        raise ValueError(
            f"Editorial evaluation status must be {expected_status} for the recorded scores."
        )
    return dict(payload)


def physical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_version(payload: Mapping[str, object], expected: int, label: str) -> None:
    try:
        actual = int(payload.get("schema_version") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {label} schema version.") from exc
    if actual != expected:
        raise ValueError(f"Unsupported {label} schema version: {actual}; expected {expected}.")


def _require_edition(payload: Mapping[str, object], edition: PublicationEdition, label: str) -> None:
    raw = _mapping(payload.get("edition"), f"{label} edition")
    if str(raw.get("key") or "") != edition.edition_key:
        raise ValueError(f"{label.title()} edition key does not match the selected edition.")
    if str(raw.get("language") or "") != edition.language:
        raise ValueError(f"{label.title()} language does not match the selected edition.")


def _require_bindings(
    payload: Mapping[str, object],
    expected: Mapping[str, str],
    label: str,
) -> None:
    bindings = _mapping(payload.get("bindings"), f"{label} bindings")
    for key, expected_value in expected.items():
        if str(bindings.get(key) or "") != expected_value:
            raise ValueError(f"{label.title()} binding {key} is stale or missing.")


def _evidence_by_id(payload: Mapping[str, object]) -> dict[str, dict[str, object]]:
    entries = _mapping_list(payload.get("entries"), "publication evidence entries")
    return _unique_records(entries, "id", "publication evidence")


def _required_vertical_sections(payload: Mapping[str, object]) -> set[str]:
    vertical = _mapping(payload.get("vertical"), "publication evidence vertical")
    sections = _mapping_list(vertical.get("required_sections"), "required vertical sections")
    return {
        str(item.get("id") or "")
        for item in sections
        if str(item.get("id") or "")
    }


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Invalid {label}: expected a mapping.")
    return dict(value)


def _mapping_list(value: object, label: str) -> list[dict[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"Invalid {label}: expected a list.")
    result: list[dict[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"Invalid {label} item at index {index}: expected a mapping.")
        result.append(dict(item))
    return result


def _unique_records(
    records: Sequence[Mapping[str, object]],
    key: str,
    label: str,
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for item in records:
        identity = str(item.get(key) or "").strip()
        if not identity:
            raise ValueError(f"{label.title()} is missing {key}.")
        if identity in result:
            raise ValueError(f"Duplicate {label} ID: {identity}")
        result[identity] = dict(item)
    return result


def _text_list(value: object, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"Invalid {label}: expected a list.")
    result = [str(item or "").strip() for item in value]
    if any(not item for item in result):
        raise ValueError(f"Invalid {label}: values must be non-empty strings.")
    if len(result) != len(set(result)):
        raise ValueError(f"Invalid {label}: duplicate values are not allowed.")
    return result


def _unique_text_list(value: object, label: str) -> list[str]:
    result = _text_list(value, label)
    if len(result) != len(set(result)):
        raise ValueError(f"Invalid {label}: duplicate values are not allowed.")
    return result


def _required_text(payload: Mapping[str, object], key: str, label: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"{label.title()} is missing {key}.")
    return value


def _required_sha256(payload: Mapping[str, object], key: str, label: str) -> str:
    value = _required_text(payload, key, label)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError(f"Invalid {label}: {key} must be a SHA-256 digest.")
    return value


def _require_known_ids(values: Sequence[str], known: set[str], label: str) -> None:
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(f"{label.title()} references unknown IDs: {', '.join(unknown)}")

from __future__ import annotations

from copy import deepcopy

import pytest

from p2p_engine.core.project_publication import PublicationEdition
from p2p_engine.services.project_publication_contracts import (
    validate_evidence_accounting,
    validate_publication_model,
)


def _evidence() -> dict[str, object]:
    return {
        "schema_version": 2,
        "semantic_sha256": "evidence-hash",
        "vertical": {
            "available": True,
            "id": "software_project",
            "required_sections": [
                {"id": "product_scope", "title": "Product Scope"},
            ]
        },
        "entries": [
            {
                "id": "EVD-ACTIVE",
                "editorial_class": "project_evidence",
                "authority_class": "active",
            },
            {
                "id": "EVD-HISTORY",
                "editorial_class": "historical_context",
                "authority_class": "historical",
            },
            {
                "id": "EVD-PROCESS",
                "editorial_class": "process_only",
                "authority_class": "active",
            },
        ],
    }


def _bindings() -> dict[str, str]:
    return {
        "curator_packet_sha256": "packet-hash",
        "evidence_index_sha256": "evidence-hash",
        "source_export_sha256": "source-hash",
        "source_fingerprint_sha256": "fingerprint-hash",
        "profile_sha256": "profile-hash",
    }


def _model() -> dict[str, object]:
    return {
        "schema_version": 2,
        "edition": {"key": "project-en", "language": "en"},
        "bindings": _bindings(),
        "project": {
            "title": "Demo Project",
            "thesis": "A complete project description.",
            "vertical_id": "software_project",
        },
        "reader_questions": [
            {
                "id": "RQ-001",
                "question": "What does the project include?",
                "answered_by": ["CLM-001"],
            }
        ],
        "claims": [
            {
                "id": "CLM-001",
                "statement": "The project has a bounded scope.",
                "evidence_ids": ["EVD-ACTIVE"],
                "vertical_sections": ["product_scope"],
            }
        ],
        "outline": [
            {
                "id": "SEC-001",
                "role": "project_overview",
                "heading": "Project Overview",
                "claim_ids": ["CLM-001"],
            }
        ],
        "vertical_coverage": [
            {
                "section_id": "product_scope",
                "disposition": "covered",
                "outline_ids": ["SEC-001"],
            }
        ],
        "editorial_assessment": {
            "rubric_version": "publication-editorial-rubric-v2",
            "results": [
                {"dimension": dimension, "score": 5, "evaluator": "self"}
                for dimension in (
                    "autonomy",
                    "vertical_coherence",
                    "evidence_use",
                    "language_consistency",
                    "structure",
                    "reader_usefulness",
                )
            ],
        },
    }


def _accounting() -> dict[str, object]:
    return {
        "schema_version": 2,
        "edition_key": "project-en",
        "bindings": {
            "model_sha256": "model-hash",
            "evidence_index_sha256": "evidence-hash",
        },
        "evidence": [
            {
                "evidence_id": "EVD-ACTIVE",
                "disposition": "used",
                "claim_ids": ["CLM-001"],
                "reason": "Supports the scope claim.",
            },
            {
                "evidence_id": "EVD-HISTORY",
                "disposition": "historical",
                "claim_ids": [],
                "reason": "Historical context is not current project substance.",
            },
            {
                "evidence_id": "EVD-PROCESS",
                "disposition": "process_only",
                "claim_ids": [],
                "reason": "Upstream process metadata.",
            },
        ],
    }


def test_publication_model_and_accounting_accept_complete_contracts() -> None:
    edition = PublicationEdition.create()
    model = validate_publication_model(
        _model(),
        edition=edition,
        expected_bindings=_bindings(),
        evidence_index=_evidence(),
    )

    accounting = validate_evidence_accounting(
        _accounting(),
        edition=edition,
        evidence_index=_evidence(),
        model=model,
        model_sha256="model-hash",
    )

    assert accounting["edition_key"] == "project-en"


def test_publication_model_rejects_unknown_and_process_only_evidence() -> None:
    for evidence_id, message in (
        ("EVD-UNKNOWN", "unknown evidence"),
        ("EVD-PROCESS", "process-only"),
    ):
        model = deepcopy(_model())
        model["claims"][0]["evidence_ids"] = [evidence_id]
        with pytest.raises(ValueError, match=message):
            validate_publication_model(
                model,
                edition=PublicationEdition.create(),
                expected_bindings=_bindings(),
                evidence_index=_evidence(),
            )


def test_publication_model_requires_all_vertical_sections() -> None:
    model = deepcopy(_model())
    model["vertical_coverage"] = []

    with pytest.raises(ValueError, match="missing required sections"):
        validate_publication_model(
            model,
            edition=PublicationEdition.create(),
            expected_bindings=_bindings(),
            evidence_index=_evidence(),
        )


def test_publication_model_allows_explicit_owner_input_provenance() -> None:
    model = deepcopy(_model())
    model["claims"][0]["evidence_ids"] = []
    model["claims"][0]["owner_input"] = {"source": "owner interview 2026-07-21"}

    result = validate_publication_model(
        model,
        edition=PublicationEdition.create(),
        expected_bindings=_bindings(),
        evidence_index=_evidence(),
    )

    assert result["claims"][0]["owner_input"]


def test_publication_model_requires_explicit_generic_vertical_fallback() -> None:
    evidence = _evidence()
    evidence["vertical"] = {"available": False, "id": "", "required_sections": []}
    model = _model()
    model["vertical_coverage"] = []

    with pytest.raises(ValueError, match="vertical_id generic"):
        validate_publication_model(
            model,
            edition=PublicationEdition.create(),
            expected_bindings=_bindings(),
            evidence_index=evidence,
        )

    model["project"]["vertical_id"] = "generic"
    model["project"]["vertical_guidance_unavailable_reason"] = "No valid vertical was available."
    assert validate_publication_model(
        model,
        edition=PublicationEdition.create(),
        expected_bindings=_bindings(),
        evidence_index=evidence,
    )["project"]["vertical_id"] == "generic"


@pytest.mark.parametrize(
    ("field", "message"),
    [("claims", "one claim"), ("reader_questions", "reader question")],
)
def test_publication_model_requires_claims_and_reader_questions(field: str, message: str) -> None:
    model = _model()
    model[field] = []

    with pytest.raises(ValueError, match=message):
        validate_publication_model(
            model,
            edition=PublicationEdition.create(),
            expected_bindings=_bindings(),
            evidence_index=_evidence(),
        )


def test_publication_model_rejects_duplicate_references() -> None:
    model = _model()
    model["claims"][0]["evidence_ids"] = ["EVD-ACTIVE", "EVD-ACTIVE"]

    with pytest.raises(ValueError, match="duplicate values"):
        validate_publication_model(
            model,
            edition=PublicationEdition.create(),
            expected_bindings=_bindings(),
            evidence_index=_evidence(),
        )


def test_evidence_accounting_requires_exact_evidence_set() -> None:
    accounting = deepcopy(_accounting())
    accounting["evidence"].pop()

    with pytest.raises(ValueError, match="incomplete"):
        validate_evidence_accounting(
            accounting,
            edition=PublicationEdition.create(),
            evidence_index=_evidence(),
            model=_model(),
            model_sha256="model-hash",
        )


def test_evidence_accounting_rejects_unknown_and_duplicate_ids() -> None:
    unknown = deepcopy(_accounting())
    unknown["evidence"].append(
        {
            "evidence_id": "EVD-UNKNOWN",
            "disposition": "not_applicable",
            "claim_ids": [],
            "reason": "Unknown.",
        }
    )
    with pytest.raises(ValueError, match="unknown evidence"):
        validate_evidence_accounting(
            unknown,
            edition=PublicationEdition.create(),
            evidence_index=_evidence(),
            model=_model(),
            model_sha256="model-hash",
        )

    duplicate = deepcopy(_accounting())
    duplicate["evidence"].append(deepcopy(duplicate["evidence"][0]))
    with pytest.raises(ValueError, match="Duplicate evidence accounting record"):
        validate_evidence_accounting(
            duplicate,
            edition=PublicationEdition.create(),
            evidence_index=_evidence(),
            model=_model(),
            model_sha256="model-hash",
        )


def test_evidence_accounting_keeps_process_only_records_out_of_claims() -> None:
    accounting = deepcopy(_accounting())
    accounting["evidence"][2]["disposition"] = "used"
    accounting["evidence"][2]["claim_ids"] = ["CLM-001"]

    with pytest.raises(ValueError, match="must remain process_only"):
        validate_evidence_accounting(
            accounting,
            edition=PublicationEdition.create(),
            evidence_index=_evidence(),
            model=_model(),
            model_sha256="model-hash",
        )


def test_evidence_accounting_requires_bidirectional_claim_links() -> None:
    accounting = deepcopy(_accounting())
    accounting["evidence"][0]["claim_ids"] = []

    with pytest.raises(ValueError, match="Used evidence"):
        validate_evidence_accounting(
            accounting,
            edition=PublicationEdition.create(),
            evidence_index=_evidence(),
            model=_model(),
            model_sha256="model-hash",
        )


def test_publication_model_rejects_historical_claim_evidence() -> None:
    model = deepcopy(_model())
    model["claims"][0]["evidence_ids"] = ["EVD-HISTORY"]

    with pytest.raises(ValueError, match="historical-context"):
        validate_publication_model(
            model,
            edition=PublicationEdition.create(),
            expected_bindings=_bindings(),
            evidence_index=_evidence(),
        )


@pytest.mark.parametrize(("mutation", "message"), [
    (lambda rows: rows.pop(), "missing dimensions"),
    (lambda rows: rows[0].update(score=3), "between 4 and 5"),
    (lambda rows: rows[0].update(evaluator="owner"), "recorded as self"),
])
def test_publication_model_enforces_editorial_rubric_thresholds(mutation, message: str) -> None:
    model = deepcopy(_model())
    mutation(model["editorial_assessment"]["results"])

    with pytest.raises(ValueError, match=message):
        validate_publication_model(
            model,
            edition=PublicationEdition.create(),
            expected_bindings=_bindings(),
            evidence_index=_evidence(),
        )

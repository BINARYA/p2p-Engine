from __future__ import annotations

import hashlib
import re

import pytest

from p2p_engine.core.project_publication import PublicationEdition
from p2p_engine.services.project_publication_contracts import validate_editorial_evaluation


DIMENSIONS = (
    "autonomy",
    "vertical_coherence",
    "evidence_use",
    "language_consistency",
    "structure",
    "reader_usefulness",
)


def _evaluation(edition_key: str, *, scores: dict[str, int] | None = None, failures=()):
    values = scores or {dimension: 5 for dimension in DIMENSIONS}
    status = "passed" if all(value >= 4 for value in values.values()) and not failures else "failed"
    return {
        "schema_version": 1,
        "rubric_version": "publication-editorial-rubric-v2",
        "edition_key": edition_key,
        "evaluation_kind": "independent",
        "evaluator": "isolated-fixture-evaluator",
        "scores": [
            {
                "dimension": dimension,
                "score": values[dimension],
                "rationale": f"Fixture satisfies {dimension.replace('_', ' ')} checks.",
            }
            for dimension in DIMENSIONS
        ],
        "zero_tolerance_failures": list(failures),
        "status": status,
    }


SOFTWARE_DOCUMENT = """# Local Project Memory Engine

## Purpose and users

The engine helps project owners and their agents preserve project intent and
recover the decisions that shape current project direction.

## Capabilities and boundaries

It organizes project evidence, supports bounded retrieval, and keeps owner
authority separate from generated summaries. It does not claim that downstream
work has been implemented or delivered.

## Data and interfaces

Project records remain file-backed and can be inspected through local commands
and structured tool calls. Derived indexes can be rebuilt from authoritative
project evidence.

## Quality and risks

Deterministic validation protects traceability. Remaining risks concern scale,
ambiguous evidence, and incomplete owner input.
"""


BOARD_GAME_DOCUMENT = """# Harbor Council

## Players and objective

Two to four players guide rival councils and win by completing the most valuable
public harbor plan.

## Components and setup

Players arrange the shared board, project cards, resource tokens, and council
markers before choosing starting roles.

## Turn flow and interaction

Each turn offers an action, a negotiation window, and a shared consequence.
Players may cooperate on public works while competing for recognition.

## Progression and ending

Completed works advance the harbor track. The game ends after the final district
is resolved, then supported scoring rules determine the winner.
"""


CUSTOM_DOCUMENT = """# Community Archive

## Project purpose

The project defines a community-owned archive with a bounded collection scope.

## Participation and stewardship

Contributors submit material under explicit stewardship rules. Unresolved
retention questions remain visible as project uncertainties.

## Collection lifecycle

The archive describes intake, review, preservation, access, and removal without
assuming any external product, organization, or implementation platform.
"""


@pytest.mark.parametrize(
    ("document", "required", "forbidden"),
    [
        (
            SOFTWARE_DOCUMENT,
            ("Purpose and users", "Capabilities and boundaries", "Data and interfaces", "Quality and risks"),
            ("PROP-", "CHANGE-", ".p2p/", "readiness score"),
        ),
        (
            BOARD_GAME_DOCUMENT,
            ("Players and objective", "Components and setup", "Turn flow and interaction", "Progression and ending"),
            ("API", "deployment", "data model", "PROP-"),
        ),
        (
            CUSTOM_DOCUMENT,
            ("Project purpose", "Participation and stewardship", "Collection lifecycle"),
            ("WaveKit", "PROP-", "source fingerprint", ".p2p/"),
        ),
    ],
)
def test_vertical_forward_evaluation_fixtures_are_autonomous(
    document: str,
    required: tuple[str, ...],
    forbidden: tuple[str, ...],
) -> None:
    assert sum(line.startswith("# ") for line in document.splitlines()) == 1
    assert all(item in document for item in required)
    assert all(item.lower() not in document.lower() for item in forbidden)
    assert not re.search(r"\b(?:PROP|CHANGE|WORK|EVENT|DECISION)-\d+", document)
    result = validate_editorial_evaluation(
        _evaluation("project-en"),
        edition=PublicationEdition.create(),
    )
    assert result["status"] == "passed"


def test_english_and_italian_editions_keep_scope_but_not_document_hash() -> None:
    english = SOFTWARE_DOCUMENT
    italian = """# Motore locale per la memoria di progetto

## Scopo e utenti

Il motore aiuta i responsabili e gli agenti a conservare l'intento del progetto
e recuperare le decisioni che definiscono la direzione corrente.

## Capacita e confini

Organizza le evidenze, supporta il recupero limitato e mantiene l'autorita del
responsabile separata dalle sintesi generate.

## Dati, interfacce, qualita e rischi

I dati restano basati su file e accessibili tramite comandi locali. La validazione
deterministica tutela la tracciabilita; scala e input incompleti restano rischi.
"""
    scope_by_language = {
        "en": {"purpose", "users", "capabilities", "boundaries", "data", "interfaces", "quality", "risks"},
        "it": {"purpose", "users", "capabilities", "boundaries", "data", "interfaces", "quality", "risks"},
    }

    assert scope_by_language["en"] == scope_by_language["it"]
    assert hashlib.sha256(english.encode()).hexdigest() != hashlib.sha256(italian.encode()).hexdigest()
    assert validate_editorial_evaluation(
        _evaluation("project-en"),
        edition=PublicationEdition.create(language="en"),
    )["status"] == "passed"
    assert validate_editorial_evaluation(
        _evaluation("project-it"),
        edition=PublicationEdition.create(language="it"),
    )["status"] == "passed"


def test_editorial_evaluation_status_cannot_hide_threshold_failure() -> None:
    payload = _evaluation("project-en", scores={**{item: 5 for item in DIMENSIONS}, "autonomy": 3})
    payload["status"] = "passed"

    with pytest.raises(ValueError, match="must be failed"):
        validate_editorial_evaluation(payload, edition=PublicationEdition.create())

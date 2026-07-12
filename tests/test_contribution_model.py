import pytest

from p2p_engine.core.contribution import (
    ContributionType,
    allowed_contribution_type_values,
    parse_contribution_type,
)


def test_contribution_type_contract_includes_canonical_authoring_concepts() -> None:
    values = set(allowed_contribution_type_values())

    assert {
        "finding",
        "open_question",
        "alternative",
        "risk",
        "assumption",
        "constraint",
        "objection",
        "implementation_suggestion",
        "scope_boundary",
    }.issubset(values)


def test_contribution_type_contract_preserves_legacy_values() -> None:
    values = set(allowed_contribution_type_values())

    assert {
        "feature_request",
        "alternative_proposal",
        "architectural_principle",
        "objective",
        "suggestion",
    }.issubset(values)


def test_parse_contribution_type_reports_allowed_values() -> None:
    assert parse_contribution_type("finding") == ContributionType.finding

    with pytest.raises(ValueError, match="Allowed: .*finding.*open_question.*assumption"):
        parse_contribution_type("unsupported")

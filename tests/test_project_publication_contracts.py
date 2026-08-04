from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.core.project_publication import (
    PUBLICATION_PROFILE_ID,
    PublicationEdition,
    contribution_share_summary,
    normalize_contribution_policy,
    normalize_publication_language,
    normalize_publication_output_name,
    resolve_publication_paths,
)
from p2p_engine.services.project_publication_contracts import (
    validate_publication_catalog,
    validate_publication_profile,
)


@pytest.mark.parametrize(
    ("value", "canonical", "path_value"),
    (
        ("en", "en", "en"),
        ("EN", "en", "en"),
        ("eng", "en", "en"),
        ("ita", "it", "it"),
        ("en_US", "en-US", "en-us"),
        ("zh-hant-tw", "zh-Hant-TW", "zh-hant-tw"),
        ("de-CH-1901", "de-CH-1901", "de-ch-1901"),
        ("en-us-u-ca-gregory", "en-US-u-ca-gregory", "en-us-u-ca-gregory"),
        ("tlh", "tlh", "tlh"),
        ("i-klingon", "i-klingon", "i-klingon"),
        ("x-org-project", "x-org-project", "x-org-project"),
    ),
)
def test_publication_language_normalization(
    value: str,
    canonical: str,
    path_value: str,
) -> None:
    assert normalize_publication_language(value) == (canonical, path_value)


@pytest.mark.parametrize(
    "value",
    (
        "",
        " ",
        "en/us",
        "en\\us",
        "en.md",
        "e",
        "en--US",
        "en-verylongtag",
        "en-a",
        "en-US-u",
        "en-US-u-ca-u-nu",
        "x",
    ),
)
def test_publication_language_rejects_unsafe_or_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="language"):
        normalize_publication_language(value)


@pytest.mark.parametrize("value", ("project", "outputxyz", "a", "a-1", "a" * 64))
def test_publication_output_name_accepts_safe_ascii_slugs(value: str) -> None:
    assert normalize_publication_output_name(value) == value


@pytest.mark.parametrize(
    "value",
    ("", "Project", "project.pdf", "../project", ".project", "project_1", "publications", "a" * 65),
)
def test_publication_output_name_rejects_unsafe_or_reserved_values(value: str) -> None:
    with pytest.raises(ValueError, match="[Pp]ublication"):
        normalize_publication_output_name(value)


def test_publication_edition_and_paths_are_deterministic(tmp_path: Path) -> None:
    edition = PublicationEdition.create(language="eng", output_name="outputxyz")

    paths = resolve_publication_paths(tmp_path, edition)

    assert edition.to_dict() == {
        "output_name": "outputxyz",
        "language": "en",
        "path_language": "en",
        "key": "outputxyz-en",
    }
    assert paths.markdown == tmp_path / "outputs/latest/outputxyz-en.md"
    assert paths.pdf == tmp_path / "outputs/latest/outputxyz-en.pdf"
    assert paths.profile == tmp_path / "outputs/latest/publications/outputxyz-en/profile.yml"
    assert paths.candidate_model == tmp_path / "drafts/project-publication/outputxyz-en.model.yml"


def test_publication_edition_paths_do_not_collide(tmp_path: Path) -> None:
    identities = (
        PublicationEdition.create(language="en", output_name="project"),
        PublicationEdition.create(language="it", output_name="project"),
        PublicationEdition.create(language="en", output_name="other"),
    )
    targets = [resolve_publication_paths(tmp_path, edition).markdown for edition in identities]

    assert len(set(targets)) == len(targets)


def test_publication_paths_reject_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "latest").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes"):
        resolve_publication_paths(tmp_path, PublicationEdition.create())


def test_contribution_shares_are_deterministic_and_total_100_percent() -> None:
    summary = contribution_share_summary(["alice", "bob", "bob", "", "alice", "carol"])

    assert summary.denominator == 6
    assert sum(row.basis_points for row in summary.rows) == 10_000
    assert [row.author for row in summary.rows] == ["alice", "bob", "Unattributed", "carol"]
    assert [row.percentage for row in summary.rows] == ["33.33", "33.33", "16.67", "16.67"]
    assert "do not measure effort" in summary.to_dict()["limitation"]


def test_contribution_shares_keep_case_variants_separate() -> None:
    summary = contribution_share_summary(["Alice", "alice", " Alice "])

    assert [(row.author, row.count) for row in summary.rows] == [("Alice", 2), ("alice", 1)]
    assert summary.advisories


def test_contribution_shares_handle_empty_and_unicode_authors() -> None:
    assert contribution_share_summary([]).rows == ()
    summary = contribution_share_summary(["Jose\u0301", "Jos\u00e9", None])
    assert [(row.author, row.count) for row in summary.rows] == [("Jos\u00e9", 2), ("Unattributed", 1)]


@pytest.mark.parametrize("value", ("auto", "include", "omit", " AUTO "))
def test_contribution_policy_normalization(value: str) -> None:
    assert normalize_contribution_policy(value) in {"auto", "include", "omit"}


def test_contribution_policy_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="Allowed"):
        normalize_contribution_policy("guess")


def test_publication_profile_enforces_reader_and_edition_contract() -> None:
    edition = PublicationEdition.create(language="it", output_name="manual")
    payload = {
        "schema_version": 2,
        "profile_id": PUBLICATION_PROFILE_ID,
        "edition": edition.to_dict(),
        "reader": {"knowledge_of_p2p": "none", "audience_variant": False},
        "editorial": {
            "structure": "vertical_adaptive",
            "traceability_in_body": False,
            "contributions": "omit",
            "include_contributions": False,
        },
        "render": {"theme": "neutral-v1"},
    }

    assert validate_publication_profile(payload, edition=edition) == payload
    payload["reader"]["audience_variant"] = True
    with pytest.raises(ValueError, match="audience variants"):
        validate_publication_profile(payload, edition=edition)


def test_publication_catalog_requires_unique_stably_sorted_canonical_editions() -> None:
    en = PublicationEdition.create()
    it = PublicationEdition.create(language="it")
    payload = {
        "schema_version": 2,
        "editions": [
            {"edition": en.to_dict(), "manifest": "outputs/latest/publications/project-en/manifest.yml"},
            {"edition": it.to_dict(), "manifest": "outputs/latest/publications/project-it/manifest.yml"},
        ],
        "diagnostics": [],
    }

    assert validate_publication_catalog(payload) == payload
    payload["editions"].append(payload["editions"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        validate_publication_catalog(payload)


def test_publication_catalog_rejects_future_contract() -> None:
    with pytest.raises(ValueError, match="Unsupported publication catalog"):
        validate_publication_catalog(
            {"schema_version": 3, "editions": [], "diagnostics": []}
        )

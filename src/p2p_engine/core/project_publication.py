from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unicodedata
from typing import Mapping, Sequence


PUBLICATION_CONTRACT_VERSION = 2
PUBLICATION_PROFILE_ID = "human-project-publication-v2"
PUBLICATION_EVIDENCE_GENERATOR = "publication-evidence-v2"
PUBLICATION_MODEL_VERSION = 2
PUBLICATION_ACCOUNTING_VERSION = 2
PUBLICATION_MANIFEST_VERSION = 2
PUBLICATION_CATALOG_VERSION = 2
PUBLICATION_VALIDATOR_VERSION = "publication-validator-v2"
PUBLICATION_EDITORIAL_RUBRIC_VERSION = "publication-editorial-rubric-v2"
PUBLICATION_EDITORIAL_EVALUATION_VERSION = 1

DEFAULT_PUBLICATION_LANGUAGE = "en"
DEFAULT_PUBLICATION_OUTPUT_NAME = "project"
CONTRIBUTION_POLICIES = ("auto", "include", "omit")
EVIDENCE_DISPOSITIONS = (
    "used",
    "supporting_context",
    "historical",
    "duplicate",
    "contradictory",
    "insufficient",
    "not_applicable",
    "process_only",
)

_OUTPUT_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_LANGUAGE_PRIMARY = re.compile(r"^[A-Za-z]{2,8}$")
_LANGUAGE_SUBTAG = re.compile(r"^[A-Za-z0-9]{1,8}$")
_LANGUAGE_VARIANT = re.compile(r"^(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3})$")
_RESERVED_OUTPUT_NAMES = {
    "latest",
    "publication",
    "publications",
    "publication-evidence",
    "publication-manifest",
    "publication-profile",
    "publication-review",
    "publication-validation",
    "curator-input",
}
_LANGUAGE_ALIASES = {"eng": "en", "ita": "it"}
_GRANDFATHERED_LANGUAGE_TAGS = {
    "art-lojban": "art-lojban",
    "cel-gaulish": "cel-gaulish",
    "en-gb-oed": "en-GB-oed",
    "i-ami": "i-ami",
    "i-bnn": "i-bnn",
    "i-default": "i-default",
    "i-enochian": "i-enochian",
    "i-hak": "i-hak",
    "i-klingon": "i-klingon",
    "i-lux": "i-lux",
    "i-mingo": "i-mingo",
    "i-navajo": "i-navajo",
    "i-pwn": "i-pwn",
    "i-tao": "i-tao",
    "i-tay": "i-tay",
    "i-tsu": "i-tsu",
    "no-bok": "no-bok",
    "no-nyn": "no-nyn",
    "sgn-be-fr": "sgn-BE-FR",
    "sgn-be-nl": "sgn-BE-NL",
    "sgn-ch-de": "sgn-CH-DE",
    "zh-guoyu": "zh-guoyu",
    "zh-hakka": "zh-hakka",
    "zh-min": "zh-min",
    "zh-min-nan": "zh-min-nan",
    "zh-xiang": "zh-xiang",
}


@dataclass(frozen=True)
class PublicationEdition:
    output_name: str
    language: str
    path_language: str
    edition_key: str

    @classmethod
    def create(
        cls,
        *,
        language: str = DEFAULT_PUBLICATION_LANGUAGE,
        output_name: str = DEFAULT_PUBLICATION_OUTPUT_NAME,
    ) -> PublicationEdition:
        canonical, path_language = normalize_publication_language(language)
        safe_output_name = normalize_publication_output_name(output_name)
        return cls(
            output_name=safe_output_name,
            language=canonical,
            path_language=path_language,
            edition_key=f"{safe_output_name}-{path_language}",
        )

    @property
    def is_default_english(self) -> bool:
        return (
            self.output_name == DEFAULT_PUBLICATION_OUTPUT_NAME
            and self.language == DEFAULT_PUBLICATION_LANGUAGE
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "output_name": self.output_name,
            "language": self.language,
            "path_language": self.path_language,
            "key": self.edition_key,
        }


@dataclass(frozen=True)
class PublicationEditionPaths:
    edition: PublicationEdition
    latest_dir: Path
    source_export: Path
    evidence_index: Path
    catalog: Path
    metadata_dir: Path
    profile: Path
    curator_input: Path
    manifest: Path
    model: Path
    evidence_accounting: Path
    validation: Path
    review: Path
    markdown: Path
    pdf: Path
    candidate_markdown: Path
    candidate_model: Path
    candidate_evidence: Path

    def canonical_targets(self) -> tuple[Path, ...]:
        return (
            self.profile,
            self.curator_input,
            self.manifest,
            self.model,
            self.evidence_accounting,
            self.validation,
            self.review,
            self.markdown,
            self.pdf,
        )


@dataclass(frozen=True)
class PublicationEvidenceEntry:
    evidence_id: str
    kind: str
    authority_class: str
    editorial_class: str
    vertical_sections: tuple[str, ...]
    source_path: str
    source_selector: str
    semantic_sha256: str
    content_mode: str
    payload: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.evidence_id,
            "kind": self.kind,
            "authority_class": self.authority_class,
            "editorial_class": self.editorial_class,
            "vertical_sections": list(self.vertical_sections),
            "source_path": self.source_path,
            "source_selector": self.source_selector,
            "semantic_sha256": self.semantic_sha256,
            "content_mode": self.content_mode,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class PublicationContributionShare:
    author: str
    count: int
    basis_points: int

    @property
    def percentage(self) -> str:
        return f"{self.basis_points / 100:.2f}"

    def to_dict(self) -> dict[str, object]:
        return {
            "author": self.author,
            "count": self.count,
            "basis_points": self.basis_points,
            "percentage": self.percentage,
        }


@dataclass(frozen=True)
class PublicationContributionSummary:
    policy_version: str
    denominator: int
    rows: tuple[PublicationContributionShare, ...]
    source_evidence_ids: tuple[str, ...] = ()
    advisories: tuple[str, ...] = ()

    @property
    def attributed_count(self) -> int:
        return sum(row.count for row in self.rows if row.author != "Unattributed")

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "denominator": self.denominator,
            "rows": [row.to_dict() for row in self.rows],
            "source_evidence_ids": list(self.source_evidence_ids),
            "advisories": list(self.advisories),
            "limitation": (
                "Percentages are shares of explicitly recorded contribution records; "
                "they do not measure effort, quality, merit, ownership, code authorship, or IP."
            ),
        }


def normalize_publication_language(value: str) -> tuple[str, str]:
    raw = str(value or "").strip().replace("_", "-")
    if not raw:
        raise ValueError("Publication language is required.")
    if "/" in raw or "\\" in raw or "." in raw or any(ord(char) < 32 for char in raw):
        raise ValueError(f"Invalid publication language tag: {value}")
    grandfathered = _GRANDFATHERED_LANGUAGE_TAGS.get(raw.lower())
    if grandfathered is not None:
        return grandfathered, grandfathered.lower()
    parts = raw.split("-")
    if parts[0].lower() == "x":
        if len(parts) == 1 or any(
            not part or not _LANGUAGE_SUBTAG.fullmatch(part) for part in parts[1:]
        ):
            raise ValueError(f"Invalid publication language tag: {value}")
        canonical = "-".join(["x", *(part.lower() for part in parts[1:])])
        return canonical, canonical
    if not _LANGUAGE_PRIMARY.fullmatch(parts[0]):
        raise ValueError(f"Invalid publication language tag: {value}")
    if any(not part or not _LANGUAGE_SUBTAG.fullmatch(part) for part in parts[1:]):
        raise ValueError(f"Invalid publication language tag: {value}")

    primary = _LANGUAGE_ALIASES.get(parts[0].lower(), parts[0].lower())
    normalized = [primary]
    index = 1
    extlangs = 0
    while (
        index < len(parts)
        and len(parts[index]) == 3
        and parts[index].isalpha()
        and extlangs < 3
        and len(primary) <= 3
    ):
        normalized.append(parts[index].lower())
        index += 1
        extlangs += 1
    if index < len(parts) and len(parts[index]) == 4 and parts[index].isalpha():
        normalized.append(parts[index].title())
        index += 1
    if index < len(parts) and (
        (len(parts[index]) == 2 and parts[index].isalpha())
        or (len(parts[index]) == 3 and parts[index].isdigit())
    ):
        normalized.append(parts[index].upper())
        index += 1

    variants: set[str] = set()
    while index < len(parts) and _LANGUAGE_VARIANT.fullmatch(parts[index]):
        variant = parts[index].lower()
        if variant in variants:
            raise ValueError(f"Invalid publication language tag: {value}")
        variants.add(variant)
        normalized.append(variant)
        index += 1

    extensions: set[str] = set()
    while index < len(parts) and len(parts[index]) == 1 and parts[index].lower() != "x":
        singleton = parts[index].lower()
        if singleton in extensions:
            raise ValueError(f"Invalid publication language tag: {value}")
        extensions.add(singleton)
        normalized.append(singleton)
        index += 1
        start = index
        while index < len(parts) and 2 <= len(parts[index]) <= 8 and parts[index].isalnum():
            normalized.append(parts[index].lower())
            index += 1
        if index == start:
            raise ValueError(f"Invalid publication language tag: {value}")

    if index < len(parts) and parts[index].lower() == "x":
        normalized.append("x")
        index += 1
        start = index
        while index < len(parts) and 1 <= len(parts[index]) <= 8 and parts[index].isalnum():
            normalized.append(parts[index].lower())
            index += 1
        if index == start:
            raise ValueError(f"Invalid publication language tag: {value}")
    if index != len(parts):
        raise ValueError(f"Invalid publication language tag: {value}")
    canonical = "-".join(normalized)
    return canonical, canonical.lower()


def normalize_publication_output_name(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Publication output name is required.")
    if len(raw) > 64 or not _OUTPUT_NAME.fullmatch(raw):
        raise ValueError(
            "Publication output name must be a lowercase ASCII slug of at most 64 characters."
        )
    if raw in _RESERVED_OUTPUT_NAMES:
        raise ValueError(f"Reserved publication output name: {raw}")
    return raw


def resolve_publication_paths(root: Path, edition: PublicationEdition) -> PublicationEditionPaths:
    root = root.resolve()
    latest = root / "outputs" / "latest"
    metadata_dir = latest / "publications" / edition.edition_key
    drafts = root / "drafts" / "project-publication"
    paths = PublicationEditionPaths(
        edition=edition,
        latest_dir=latest,
        source_export=latest / "project.md",
        evidence_index=latest / "publication-evidence.yml",
        catalog=latest / "publications.yml",
        metadata_dir=metadata_dir,
        profile=metadata_dir / "profile.yml",
        curator_input=metadata_dir / "curator-input.md",
        manifest=metadata_dir / "manifest.yml",
        model=metadata_dir / "project-model.yml",
        evidence_accounting=metadata_dir / "evidence-accounting.yml",
        validation=metadata_dir / "validation.yml",
        review=metadata_dir / "review.yml",
        markdown=latest / f"{edition.edition_key}.md",
        pdf=latest / f"{edition.edition_key}.pdf",
        candidate_markdown=drafts / f"{edition.edition_key}.md",
        candidate_model=drafts / f"{edition.edition_key}.model.yml",
        candidate_evidence=drafts / f"{edition.edition_key}.evidence.yml",
    )
    _require_under(root / "outputs", root, "Publication output directory")
    _require_under(paths.latest_dir, root / "outputs", "Publication output root")
    _require_under(drafts, root, "Publication draft root")
    _require_under(paths.metadata_dir, paths.latest_dir / "publications", "Publication metadata")
    for candidate in (
        paths.candidate_markdown,
        paths.candidate_model,
        paths.candidate_evidence,
    ):
        _require_under(candidate, drafts, "Publication draft")
    for path in paths.canonical_targets():
        _require_under(path, paths.latest_dir, "Publication target")
    return paths


def normalize_contribution_author(value: object) -> str:
    normalized = unicodedata.normalize("NFC", str(value or ""))
    collapsed = " ".join(normalized.split())
    return collapsed or "Unattributed"


def contribution_share_summary(
    authors: Sequence[object],
    *,
    source_evidence_ids: Sequence[str] = (),
) -> PublicationContributionSummary:
    counts: dict[str, int] = {}
    for value in authors:
        author = normalize_contribution_author(value)
        counts[author] = counts.get(author, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return PublicationContributionSummary(
            policy_version="recorded-contribution-share-v1",
            denominator=0,
            rows=(),
            source_evidence_ids=tuple(sorted(set(source_evidence_ids))),
        )

    floors: dict[str, int] = {}
    remainders: list[tuple[int, str]] = []
    for author, count in counts.items():
        numerator = count * 10_000
        floors[author] = numerator // total
        remainders.append((numerator % total, author))
    remaining = 10_000 - sum(floors.values())
    for _remainder, author in sorted(remainders, key=lambda item: (-item[0], item[1]))[:remaining]:
        floors[author] += 1

    rows = tuple(
        PublicationContributionShare(
            author=author,
            count=counts[author],
            basis_points=floors[author],
        )
        for author in sorted(counts, key=lambda item: (-counts[item], item))
    )
    advisories = _contribution_identity_advisories(tuple(counts))
    return PublicationContributionSummary(
        policy_version="recorded-contribution-share-v1",
        denominator=total,
        rows=rows,
        source_evidence_ids=tuple(sorted(set(source_evidence_ids))),
        advisories=advisories,
    )


def normalize_contribution_policy(value: str) -> str:
    normalized = str(value or "auto").strip().lower()
    if normalized not in CONTRIBUTION_POLICIES:
        raise ValueError(
            f"Invalid contribution policy: {value}. Allowed: {', '.join(CONTRIBUTION_POLICIES)}"
        )
    return normalized


def _contribution_identity_advisories(authors: tuple[str, ...]) -> tuple[str, ...]:
    by_casefold: dict[str, list[str]] = {}
    for author in authors:
        if author == "Unattributed":
            continue
        by_casefold.setdefault(author.casefold(), []).append(author)
    advisories = []
    for variants in by_casefold.values():
        if len(variants) > 1:
            advisories.append(
                "Possible contributor identity variants were kept separate: "
                + ", ".join(sorted(variants))
            )
    return tuple(sorted(advisories))


def _require_under(path: Path, parent: Path, label: str) -> None:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} path escapes its declared root: {path}") from exc

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Protocol

import yaml

from p2p_engine.core.decision_context import (
    Completeness,
    DecisionContextDiagnostic,
    DiagnosticSeverity,
    ExtractionSession,
    ParsedFragment,
    SOURCE_CATALOG_VERSION,
    SourceAccessStats,
    SourceClassification,
    SourceDocument,
    SourceKind,
    SourcePresence,
    SourceSpan,
)


_PROPOSAL_ID_RE = re.compile(r"^(PROP-[0-9]+)(?:-|$)", re.IGNORECASE)
_CHOICE_ID_RE = re.compile(r"^(CHOICE-[0-9]+)(?:-|$)", re.IGNORECASE)
_CHANGE_ID_RE = re.compile(r"^(CHANGE-[0-9]+)(?:-|$)", re.IGNORECASE)
_WORK_ID_RE = re.compile(r"^(WORK-[0-9]+)(?:-|$)", re.IGNORECASE)
_HEADING_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*#*[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")


class SourceAccessor(Protocol):
    def proposal_directories(self, proposals_root: Path) -> list[Path]: ...

    def read_bytes(self, path: Path) -> bytes: ...


class FileSourceAccessor:
    def proposal_directories(self, proposals_root: Path) -> list[Path]:
        return [path for path in proposals_root.iterdir() if path.is_dir()]

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()


@dataclass(frozen=True)
class SourceDescriptor:
    path: Path
    owner_id: str
    source_kind: SourceKind
    classification: SourceClassification
    required: bool
    parser: str = "markdown"


@dataclass(frozen=True)
class SourceCatalog:
    version: str
    descriptors: tuple[SourceDescriptor, ...]
    diagnostics: tuple[DecisionContextDiagnostic, ...]


class _DuplicateYamlKeyError(ValueError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateYamlKeyError(f"Duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


class _AccessCounter:
    def __init__(self) -> None:
        self.discovery_passes = 0
        self.reads: Counter[str] = Counter()
        self.hashes: Counter[str] = Counter()
        self.parses: Counter[str] = Counter()

    def freeze(self) -> SourceAccessStats:
        return SourceAccessStats(
            discovery_passes=self.discovery_passes,
            reads=MappingProxyType(dict(sorted(self.reads.items()))),
            hashes=MappingProxyType(dict(sorted(self.hashes.items()))),
            parses=MappingProxyType(dict(sorted(self.parses.items()))),
        )


class DecisionContextSourceService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path | None = None,
        accessor: SourceAccessor | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = (p2p_dir or self.root / ".p2p").resolve()
        self.accessor = accessor or FileSourceAccessor()

    def build_proposal_decision_session(self) -> ExtractionSession:
        counter = _AccessCounter()
        catalog = self._proposal_decision_catalog(counter)
        diagnostics = list(catalog.diagnostics)
        if any(item.fatal for item in diagnostics):
            return ExtractionSession(
                source_catalog_version=catalog.version,
                source_fingerprint_sha256=_source_fingerprint(catalog.version, ()),
                completeness=Completeness.UNAVAILABLE,
                sources=(),
                diagnostics=tuple(sorted(diagnostics, key=_diagnostic_sort_key)),
                access_stats=counter.freeze(),
            )

        documents: list[SourceDocument] = []
        for descriptor in catalog.descriptors:
            document, source_diagnostics = self._capture(descriptor, counter)
            documents.append(document)
            diagnostics.extend(source_diagnostics)

        documents.sort(key=lambda item: (item.path, item.source_kind.value))
        diagnostics.sort(key=_diagnostic_sort_key)
        completeness = _aggregate_completeness(documents, diagnostics)
        return ExtractionSession(
            source_catalog_version=catalog.version,
            source_fingerprint_sha256=_source_fingerprint(catalog.version, documents),
            completeness=completeness,
            sources=tuple(documents),
            diagnostics=tuple(diagnostics),
            access_stats=counter.freeze(),
        )

    def build_full_session(self) -> ExtractionSession:
        counter = _AccessCounter()
        catalog = self._full_catalog(counter)
        diagnostics = list(catalog.diagnostics)
        if any(item.fatal for item in diagnostics):
            return ExtractionSession(
                source_catalog_version=catalog.version,
                source_fingerprint_sha256=_source_fingerprint(catalog.version, ()),
                completeness=Completeness.UNAVAILABLE,
                sources=(),
                diagnostics=tuple(sorted(diagnostics, key=_diagnostic_sort_key)),
                access_stats=counter.freeze(),
            )
        documents: list[SourceDocument] = []
        for descriptor in catalog.descriptors:
            document, source_diagnostics = self._capture(descriptor, counter)
            documents.append(document)
            diagnostics.extend(source_diagnostics)
        documents.sort(key=lambda item: (item.path, item.source_kind.value))
        diagnostics.sort(key=_diagnostic_sort_key)
        return ExtractionSession(
            source_catalog_version=catalog.version,
            source_fingerprint_sha256=_source_fingerprint(catalog.version, documents),
            completeness=_aggregate_completeness(documents, diagnostics),
            sources=tuple(documents),
            diagnostics=tuple(diagnostics),
            access_stats=counter.freeze(),
        )

    def _proposal_decision_catalog(self, counter: _AccessCounter) -> SourceCatalog:
        proposals_root = self.p2p_dir / "proposals"
        counter.discovery_passes += 1
        if not proposals_root.is_dir():
            diagnostic = _diagnostic(
                code="DC-SOURCE-MISSING-GOVERNED-ROOT",
                severity=DiagnosticSeverity.ERROR,
                fatal=True,
                message="Governed proposal root is missing.",
                source_path=_relative_path(self.root, proposals_root),
                recovery="Initialize or repair the project through supported P2P commands.",
            )
            return SourceCatalog(SOURCE_CATALOG_VERSION, (), (diagnostic,))

        descriptors: list[SourceDescriptor] = []
        diagnostics: list[DecisionContextDiagnostic] = []
        owner_paths: dict[str, Path] = {}
        for proposal_dir in sorted(self.accessor.proposal_directories(proposals_root), key=lambda path: path.name):
            match = _PROPOSAL_ID_RE.match(proposal_dir.name)
            if match is None:
                continue
            owner_id = match.group(1).upper()
            existing = owner_paths.get(owner_id)
            if existing is not None:
                diagnostics.append(
                    _diagnostic(
                        code="DC-IDENTITY-DUPLICATE-OWNER",
                        severity=DiagnosticSeverity.ERROR,
                        fatal=True,
                        message=f"Multiple proposal directories resolve to {owner_id}.",
                        source_path=_relative_path(self.root, proposal_dir),
                        target_id=owner_id,
                        recovery="Resolve duplicate proposal identity through the supported proposal workflow.",
                    )
                )
                continue
            owner_paths[owner_id] = proposal_dir
            descriptors.extend(
                (
                    SourceDescriptor(
                        path=proposal_dir / "proposal.md",
                        owner_id=owner_id,
                        source_kind=SourceKind.PROPOSAL_BODY,
                        classification=SourceClassification.CANONICAL_SEMANTIC,
                        required=True,
                    ),
                    SourceDescriptor(
                        path=proposal_dir / "decision.md",
                        owner_id=owner_id,
                        source_kind=SourceKind.PROPOSAL_DECISION,
                        classification=SourceClassification.CANONICAL_SEMANTIC,
                        required=False,
                    ),
                )
            )
        descriptors.sort(key=lambda item: (_relative_path(self.root, item.path), item.source_kind.value))
        diagnostics.sort(key=_diagnostic_sort_key)
        return SourceCatalog(SOURCE_CATALOG_VERSION, tuple(descriptors), tuple(diagnostics))

    def _full_catalog(self, counter: _AccessCounter) -> SourceCatalog:
        proposals_root = self.p2p_dir / "proposals"
        counter.discovery_passes += 1
        if not proposals_root.is_dir():
            diagnostic = _diagnostic(
                code="DC-SOURCE-MISSING-GOVERNED-ROOT",
                severity=DiagnosticSeverity.ERROR,
                fatal=True,
                message="Governed proposal root is missing.",
                source_path=_relative_path(self.root, proposals_root),
                recovery="Initialize or repair the project through supported P2P commands.",
            )
            return SourceCatalog(SOURCE_CATALOG_VERSION, (), (diagnostic,))

        descriptors: list[SourceDescriptor] = []
        diagnostics: list[DecisionContextDiagnostic] = []
        owner_paths: dict[str, Path] = {}
        for proposal_dir in sorted(self.accessor.proposal_directories(proposals_root), key=lambda path: path.name):
            match = _PROPOSAL_ID_RE.match(proposal_dir.name)
            if match is None:
                continue
            owner_id = match.group(1).upper()
            if owner_id in owner_paths:
                diagnostics.append(
                    _diagnostic(
                        code="DC-IDENTITY-DUPLICATE-OWNER",
                        severity=DiagnosticSeverity.ERROR,
                        fatal=True,
                        message=f"Multiple proposal directories resolve to {owner_id}.",
                        source_path=_relative_path(self.root, proposal_dir),
                        target_id=owner_id,
                        recovery="Resolve duplicate proposal identity through the supported proposal workflow.",
                    )
                )
                continue
            owner_paths[owner_id] = proposal_dir
            descriptors.extend(_proposal_source_descriptors(proposal_dir, owner_id))

        descriptors.extend(
            self._directory_source_descriptors(
                self.p2p_dir / "choices", _CHOICE_ID_RE, _choice_source_descriptors, diagnostics
            )
        )
        descriptors.extend(
            self._directory_source_descriptors(
                self.p2p_dir / "changes", _CHANGE_ID_RE, _change_source_descriptors, diagnostics
            )
        )
        descriptors.extend(
            self._directory_source_descriptors(
                self.p2p_dir / "work", _WORK_ID_RE, _work_source_descriptors, diagnostics
            )
        )
        descriptors.extend(_project_source_descriptors(self.p2p_dir))
        descriptors.sort(key=lambda item: (_relative_path(self.root, item.path), item.source_kind.value))
        diagnostics.sort(key=_diagnostic_sort_key)
        return SourceCatalog(SOURCE_CATALOG_VERSION, tuple(descriptors), tuple(diagnostics))

    def _directory_source_descriptors(
        self,
        directory: Path,
        identity_pattern: re.Pattern[str],
        factory: Callable[[Path, str], tuple[SourceDescriptor, ...]],
        diagnostics: list[DecisionContextDiagnostic],
    ) -> list[SourceDescriptor]:
        if not directory.is_dir():
            return []
        descriptors: list[SourceDescriptor] = []
        owner_paths: dict[str, Path] = {}
        for item_dir in sorted((path for path in directory.iterdir() if path.is_dir()), key=lambda path: path.name):
            match = identity_pattern.match(item_dir.name)
            if match is None:
                continue
            owner_id = match.group(1).upper()
            if owner_id in owner_paths:
                diagnostics.append(
                    _diagnostic(
                        code="DC-IDENTITY-DUPLICATE-OWNER",
                        severity=DiagnosticSeverity.ERROR,
                        fatal=True,
                        message=f"Multiple governed directories resolve to {owner_id}.",
                        source_path=_relative_path(self.root, item_dir),
                        target_id=owner_id,
                        recovery="Resolve duplicate identity through the supported workflow.",
                    )
                )
                continue
            owner_paths[owner_id] = item_dir
            descriptors.extend(factory(item_dir, owner_id))
        return descriptors

    def _capture(
        self,
        descriptor: SourceDescriptor,
        counter: _AccessCounter,
    ) -> tuple[SourceDocument, tuple[DecisionContextDiagnostic, ...]]:
        relative_path = _relative_path(self.root, descriptor.path)
        if not descriptor.path.is_file():
            diagnostics: tuple[DecisionContextDiagnostic, ...] = ()
            if descriptor.required:
                diagnostics = (
                    _diagnostic(
                        code="DC-SOURCE-MISSING-REQUIRED",
                        severity=DiagnosticSeverity.WARNING,
                        fatal=False,
                        message=f"Required {descriptor.source_kind.value} source is missing.",
                        source_path=relative_path,
                        target_id=descriptor.owner_id,
                        recovery="Repair the proposal through supported P2P commands.",
                    ),
                )
            return (
                SourceDocument(
                    path=relative_path,
                    owner_id=descriptor.owner_id,
                    source_kind=descriptor.source_kind,
                    classification=descriptor.classification,
                    presence=SourcePresence.MISSING,
                    sha256=None,
                    completeness=Completeness.UNAVAILABLE,
                    frontmatter=MappingProxyType({}),
                    fragments=(),
                    diagnostic_ids=tuple(item.diagnostic_id for item in diagnostics),
                ),
                diagnostics,
            )

        try:
            counter.reads[relative_path] += 1
            content = self.accessor.read_bytes(descriptor.path)
        except OSError as exc:
            diagnostic = _diagnostic(
                code="DC-SOURCE-READ-FAILED",
                severity=DiagnosticSeverity.ERROR,
                fatal=False,
                message=f"Could not read source: {exc}",
                source_path=relative_path,
                target_id=descriptor.owner_id,
                recovery="Check source readability and retry.",
            )
            return (
                SourceDocument(
                    path=relative_path,
                    owner_id=descriptor.owner_id,
                    source_kind=descriptor.source_kind,
                    classification=descriptor.classification,
                    presence=SourcePresence.INVALID,
                    sha256=None,
                    completeness=Completeness.UNAVAILABLE,
                    frontmatter=MappingProxyType({}),
                    fragments=(),
                    diagnostic_ids=(diagnostic.diagnostic_id,),
                ),
                (diagnostic,),
            )

        counter.hashes[relative_path] += 1
        source_hash = hashlib.sha256(content).hexdigest()
        counter.parses[relative_path] += 1
        if descriptor.parser == "yaml":
            document, diagnostics = parse_yaml_source(
                descriptor=descriptor,
                relative_path=relative_path,
                content=content,
                source_hash=source_hash,
            )
        else:
            document, diagnostics = parse_markdown_source(
                descriptor=descriptor,
                relative_path=relative_path,
                content=content,
                source_hash=source_hash,
            )
        return document, diagnostics


def parse_markdown_source(
    *,
    descriptor: SourceDescriptor,
    relative_path: str,
    content: bytes,
    source_hash: str,
) -> tuple[SourceDocument, tuple[DecisionContextDiagnostic, ...]]:
    diagnostics: list[DecisionContextDiagnostic] = []
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        diagnostic = _diagnostic(
            code="DC-SOURCE-DECODE-FAILED",
            severity=DiagnosticSeverity.ERROR,
            fatal=False,
            message=f"Source is not valid UTF-8: {exc}",
            source_path=relative_path,
            target_id=descriptor.owner_id,
            recovery="Rewrite the source as UTF-8 through a supported workflow.",
        )
        return (
            SourceDocument(
                path=relative_path,
                owner_id=descriptor.owner_id,
                source_kind=descriptor.source_kind,
                classification=descriptor.classification,
                presence=SourcePresence.INVALID,
                sha256=source_hash,
                completeness=Completeness.UNAVAILABLE,
                frontmatter=MappingProxyType({}),
                fragments=(),
                diagnostic_ids=(diagnostic.diagnostic_id,),
                _content=content,
            ),
            (diagnostic,),
        )

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    frontmatter, body_text, body_start_line, frontmatter_diagnostics = _parse_frontmatter(
        normalized,
        source_path=relative_path,
        target_id=descriptor.owner_id,
    )
    diagnostics.extend(frontmatter_diagnostics)
    fragments, section_diagnostics = _parse_sections(
        body_text,
        source_kind=descriptor.source_kind,
        source_path=relative_path,
        target_id=descriptor.owner_id,
        line_offset=body_start_line - 1,
    )
    diagnostics.extend(section_diagnostics)
    completeness = Completeness.PARTIAL if diagnostics else Completeness.COMPLETE
    diagnostics.sort(key=_diagnostic_sort_key)
    document = SourceDocument(
        path=relative_path,
        owner_id=descriptor.owner_id,
        source_kind=descriptor.source_kind,
        classification=descriptor.classification,
        presence=SourcePresence.PRESENT,
        sha256=source_hash,
        completeness=completeness,
        frontmatter=_freeze_mapping(frontmatter),
        fragments=tuple(fragments),
        diagnostic_ids=tuple(item.diagnostic_id for item in diagnostics),
        _content=content,
    )
    return document, tuple(diagnostics)


def parse_yaml_source(
    *,
    descriptor: SourceDescriptor,
    relative_path: str,
    content: bytes,
    source_hash: str,
) -> tuple[SourceDocument, tuple[DecisionContextDiagnostic, ...]]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        diagnostic = _diagnostic(
            code="DC-SOURCE-DECODE-FAILED",
            severity=DiagnosticSeverity.ERROR,
            fatal=False,
            message=f"Source is not valid UTF-8: {exc}",
            source_path=relative_path,
            target_id=descriptor.owner_id,
            recovery="Rewrite the source as UTF-8 through a supported workflow.",
        )
        return _invalid_structured_document(descriptor, relative_path, source_hash, content, diagnostic), (diagnostic,)
    try:
        loaded = yaml.load(text, Loader=_UniqueKeyLoader)
    except _DuplicateYamlKeyError as exc:
        diagnostic = _diagnostic(
            code="DC-SOURCE-DUPLICATE-KEY",
            severity=DiagnosticSeverity.WARNING,
            fatal=False,
            message=str(exc),
            source_path=relative_path,
            target_id=descriptor.owner_id,
            recovery="Remove the duplicate YAML key.",
        )
        return _invalid_structured_document(descriptor, relative_path, source_hash, content, diagnostic), (diagnostic,)
    except yaml.YAMLError as exc:
        diagnostic = _diagnostic(
            code="DC-SOURCE-MALFORMED-YAML",
            severity=DiagnosticSeverity.WARNING,
            fatal=False,
            message=f"YAML is malformed: {_bounded(str(exc), 160)}",
            source_path=relative_path,
            target_id=descriptor.owner_id,
            recovery="Correct the YAML through the supported artifact workflow.",
        )
        return _invalid_structured_document(descriptor, relative_path, source_hash, content, diagnostic), (diagnostic,)
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        diagnostic = _diagnostic(
            code="DC-SOURCE-INVALID-YAML-SHAPE",
            severity=DiagnosticSeverity.WARNING,
            fatal=False,
            message="Structured source must contain a top-level YAML mapping.",
            source_path=relative_path,
            target_id=descriptor.owner_id,
            recovery="Use the documented top-level mapping for this artifact.",
        )
        return _invalid_structured_document(descriptor, relative_path, source_hash, content, diagnostic), (diagnostic,)
    document = SourceDocument(
        path=relative_path,
        owner_id=descriptor.owner_id,
        source_kind=descriptor.source_kind,
        classification=descriptor.classification,
        presence=SourcePresence.PRESENT,
        sha256=source_hash,
        completeness=Completeness.COMPLETE,
        frontmatter=_freeze_mapping({str(key): value for key, value in loaded.items()}),
        fragments=(),
        diagnostic_ids=(),
        _content=content,
    )
    return document, ()


def _invalid_structured_document(
    descriptor: SourceDescriptor,
    relative_path: str,
    source_hash: str,
    content: bytes,
    diagnostic: DecisionContextDiagnostic,
) -> SourceDocument:
    return SourceDocument(
        path=relative_path,
        owner_id=descriptor.owner_id,
        source_kind=descriptor.source_kind,
        classification=descriptor.classification,
        presence=SourcePresence.INVALID,
        sha256=source_hash,
        completeness=Completeness.PARTIAL,
        frontmatter=MappingProxyType({}),
        fragments=(),
        diagnostic_ids=(diagnostic.diagnostic_id,),
        _content=content,
    )


def _proposal_source_descriptors(proposal_dir: Path, owner_id: str) -> tuple[SourceDescriptor, ...]:
    return (
        SourceDescriptor(
            proposal_dir / "proposal.md",
            owner_id,
            SourceKind.PROPOSAL_BODY,
            SourceClassification.CANONICAL_SEMANTIC,
            True,
        ),
        SourceDescriptor(
            proposal_dir / "decision.md",
            owner_id,
            SourceKind.PROPOSAL_DECISION,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
        ),
        SourceDescriptor(
            proposal_dir / "related-proposals.yml",
            owner_id,
            SourceKind.RELATED_PROPOSALS,
            SourceClassification.GOVERNED_EVIDENCE,
            False,
            "yaml",
        ),
        SourceDescriptor(
            proposal_dir / "impact-map.yml",
            owner_id,
            SourceKind.IMPACT_MAP,
            SourceClassification.GOVERNED_EVIDENCE,
            False,
            "yaml",
        ),
        SourceDescriptor(
            proposal_dir / "conflict-analysis.yml",
            owner_id,
            SourceKind.CONFLICT_ANALYSIS,
            SourceClassification.GOVERNED_EVIDENCE,
            False,
            "yaml",
        ),
        SourceDescriptor(
            proposal_dir / "artifact-state.yml",
            owner_id,
            SourceKind.ARTIFACT_STATE,
            SourceClassification.QUALITY_METADATA,
            False,
            "yaml",
        ),
        SourceDescriptor(
            proposal_dir / "readiness.yml",
            owner_id,
            SourceKind.READINESS,
            SourceClassification.QUALITY_METADATA,
            False,
            "yaml",
        ),
        SourceDescriptor(
            proposal_dir / "questions.yml",
            owner_id,
            SourceKind.QUESTIONS,
            SourceClassification.QUALITY_METADATA,
            False,
            "yaml",
        ),
        SourceDescriptor(
            proposal_dir / "contributions.yml",
            owner_id,
            SourceKind.CONTRIBUTIONS,
            SourceClassification.QUALITY_METADATA,
            False,
            "yaml",
        ),
        SourceDescriptor(
            proposal_dir / "vertical-coverage.yml",
            owner_id,
            SourceKind.VERTICAL_COVERAGE,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
    )


def _choice_source_descriptors(choice_dir: Path, owner_id: str) -> tuple[SourceDescriptor, ...]:
    return (
        SourceDescriptor(
            choice_dir / "choice.md",
            owner_id,
            SourceKind.PROJECT_CHOICE,
            SourceClassification.CANONICAL_SEMANTIC,
            True,
        ),
        SourceDescriptor(
            choice_dir / "decision.md",
            owner_id,
            SourceKind.PROJECT_CHOICE_DECISION,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
        ),
        SourceDescriptor(
            choice_dir / "links.yml",
            owner_id,
            SourceKind.PROJECT_CHOICE_LINKS,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
    )


def _change_source_descriptors(change_dir: Path, owner_id: str) -> tuple[SourceDescriptor, ...]:
    return (
        SourceDescriptor(
            change_dir / "change.md",
            owner_id,
            SourceKind.CHANGE_SET,
            SourceClassification.CANONICAL_SEMANTIC,
            True,
        ),
        SourceDescriptor(
            change_dir / "included-proposals.yml",
            owner_id,
            SourceKind.CHANGE_RELATIONS,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
        SourceDescriptor(
            change_dir / "referenced-proposals.yml",
            owner_id,
            SourceKind.CHANGE_RELATIONS,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
        SourceDescriptor(
            change_dir / "included-decisions.yml",
            owner_id,
            SourceKind.CHANGE_RELATIONS,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
        SourceDescriptor(
            change_dir / "impact-map.yml",
            owner_id,
            SourceKind.IMPACT_MAP,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
    )


def _work_source_descriptors(work_dir: Path, owner_id: str) -> tuple[SourceDescriptor, ...]:
    return (
        SourceDescriptor(
            work_dir / "manifest.yml",
            owner_id,
            SourceKind.WORK_MANIFEST,
            SourceClassification.EXECUTION_METADATA,
            True,
            "yaml",
        ),
    )


def _project_source_descriptors(p2p_dir: Path) -> tuple[SourceDescriptor, ...]:
    return (
        SourceDescriptor(
            p2p_dir / "project" / "conflicts.yml",
            "PROJECT",
            SourceKind.PROJECT_CONFLICTS,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
        SourceDescriptor(
            p2p_dir / "governance" / "decision-precedents.yml",
            "PROJECT",
            SourceKind.DECISION_PRECEDENTS,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
        SourceDescriptor(
            p2p_dir / "governance" / "constitution.md",
            "PROJECT",
            SourceKind.GOVERNANCE_CONSTRAINT,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
        ),
        SourceDescriptor(
            p2p_dir / "governance" / "decision-rules.md",
            "PROJECT",
            SourceKind.GOVERNANCE_CONSTRAINT,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
        ),
        SourceDescriptor(
            p2p_dir / "governance" / "relevance-criteria.md",
            "PROJECT",
            SourceKind.GOVERNANCE_CONSTRAINT,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
        ),
        SourceDescriptor(
            p2p_dir / "project" / "definition.yml",
            "PROJECT",
            SourceKind.PROJECT_DEFINITION,
            SourceClassification.CANONICAL_SEMANTIC,
            False,
            "yaml",
        ),
    )


def fragment_for_label(document: SourceDocument, label: str) -> ParsedFragment | None:
    normalized = _slug(label)
    return next((fragment for fragment in document.fragments if fragment.anchor == normalized), None)


def fragments_for_label(document: SourceDocument, label: str) -> tuple[ParsedFragment, ...]:
    normalized = _slug(label)
    return tuple(fragment for fragment in document.fragments if fragment.anchor == normalized)


def _parse_frontmatter(
    text: str,
    *,
    source_path: str,
    target_id: str,
) -> tuple[dict[str, object], str, int, list[DecisionContextDiagnostic]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, 1, []
    closing_index = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if closing_index is None:
        diagnostic = _diagnostic(
            code="DC-SOURCE-MALFORMED-FRONTMATTER",
            severity=DiagnosticSeverity.WARNING,
            fatal=False,
            message="Frontmatter opening delimiter has no closing delimiter.",
            source_path=source_path,
            target_id=target_id,
            recovery="Close or remove the frontmatter block.",
        )
        return {}, text, 1, [diagnostic]

    raw_frontmatter = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])
    if text.endswith("\n"):
        body += "\n"
    if not raw_frontmatter.strip():
        return {}, body, closing_index + 2, []
    try:
        loaded = yaml.load(raw_frontmatter, Loader=_UniqueKeyLoader)
    except _DuplicateYamlKeyError as exc:
        diagnostic = _diagnostic(
            code="DC-SOURCE-DUPLICATE-KEY",
            severity=DiagnosticSeverity.WARNING,
            fatal=False,
            message=str(exc),
            source_path=source_path,
            target_id=target_id,
            recovery="Remove the duplicate frontmatter key.",
        )
        return {}, body, closing_index + 2, [diagnostic]
    except yaml.YAMLError as exc:
        diagnostic = _diagnostic(
            code="DC-SOURCE-MALFORMED-YAML",
            severity=DiagnosticSeverity.WARNING,
            fatal=False,
            message=f"Frontmatter YAML is malformed: {_bounded(str(exc), 160)}",
            source_path=source_path,
            target_id=target_id,
            recovery="Correct the frontmatter YAML.",
        )
        return {}, body, closing_index + 2, [diagnostic]
    if loaded is None:
        return {}, body, closing_index + 2, []
    if not isinstance(loaded, dict):
        diagnostic = _diagnostic(
            code="DC-SOURCE-INVALID-FRONTMATTER-SHAPE",
            severity=DiagnosticSeverity.WARNING,
            fatal=False,
            message="Frontmatter must be a YAML mapping.",
            source_path=source_path,
            target_id=target_id,
            recovery="Use key/value frontmatter fields.",
        )
        return {}, body, closing_index + 2, [diagnostic]
    return {str(key): value for key, value in loaded.items()}, body, closing_index + 2, []


def _parse_sections(
    text: str,
    *,
    source_kind: SourceKind,
    source_path: str,
    target_id: str,
    line_offset: int,
) -> tuple[list[ParsedFragment], list[DecisionContextDiagnostic]]:
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    fence_character = ""
    fence_length = 0
    for index, line in enumerate(lines):
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if not fence_character:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = ""
                fence_length = 0
            continue
        if fence_character:
            continue
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            label = heading_match.group(1).strip().rstrip("#").rstrip()
            headings.append((index, label))

    occurrence_by_anchor: Counter[str] = Counter()
    fragments: list[ParsedFragment] = []
    diagnostics: list[DecisionContextDiagnostic] = []
    for heading_position, (start_index, label) in enumerate(headings):
        end_index = headings[heading_position + 1][0] if heading_position + 1 < len(headings) else len(lines)
        anchor = _slug(label)
        occurrence_by_anchor[anchor] += 1
        occurrence = occurrence_by_anchor[anchor]
        raw_text = "\n".join(lines[start_index + 1 : end_index]).strip()
        fragment_id = f"{source_kind.value}:{anchor}:{occurrence}"
        fragments.append(
            ParsedFragment(
                fragment_id=fragment_id,
                anchor=anchor,
                occurrence=occurrence,
                label=label,
                text=raw_text,
                text_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                span=SourceSpan(
                    start_line=start_index + 1 + line_offset,
                    end_line=max(start_index + 1 + line_offset, end_index + line_offset),
                ),
            )
        )
        if occurrence > 1:
            diagnostics.append(
                _diagnostic(
                    code="DC-SOURCE-DUPLICATE-SECTION",
                    severity=DiagnosticSeverity.ADVISORY,
                    fatal=False,
                    message=f"Section {label!r} occurs more than once.",
                    source_path=source_path,
                    fragment_id=fragment_id,
                    target_id=target_id,
                    recovery="Confirm whether repeated sections are intentional.",
                )
            )
    return fragments, diagnostics


def _source_fingerprint(version: str, documents: tuple[SourceDocument, ...] | list[SourceDocument]) -> str:
    payload = {
        "source_catalog_version": version,
        "sources": [
            {
                "path": document.path,
                "presence": document.presence.value,
                "sha256": document.sha256,
            }
            for document in sorted(documents, key=lambda item: (item.path, item.source_kind.value))
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _aggregate_completeness(
    documents: list[SourceDocument],
    diagnostics: list[DecisionContextDiagnostic],
) -> Completeness:
    if any(item.fatal for item in diagnostics):
        return Completeness.UNAVAILABLE
    present = [document for document in documents if document.presence == SourcePresence.PRESENT]
    if not present:
        return Completeness.UNAVAILABLE
    if any(document.completeness != Completeness.COMPLETE for document in present):
        return Completeness.PARTIAL
    if any(item.severity in {DiagnosticSeverity.WARNING, DiagnosticSeverity.ERROR} for item in diagnostics):
        return Completeness.PARTIAL
    return Completeness.COMPLETE


def _diagnostic(
    *,
    code: str,
    severity: DiagnosticSeverity,
    fatal: bool,
    message: str,
    source_path: str = "",
    fragment_id: str = "",
    target_id: str = "",
    recovery: str = "",
    snippet: str = "",
) -> DecisionContextDiagnostic:
    identity = "|".join((code, source_path, fragment_id, target_id, message))
    diagnostic_id = f"dcd:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"
    return DecisionContextDiagnostic(
        diagnostic_id=diagnostic_id,
        code=code,
        severity=severity,
        fatal=fatal,
        message=message,
        source_path=source_path,
        fragment_id=fragment_id,
        target_id=target_id,
        recovery=recovery,
        snippet=_bounded(snippet, 160),
    )


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "section"


def _freeze_mapping(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): _freeze_value(value) for key, value in values.items()})


def _freeze_value(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _bounded(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _diagnostic_sort_key(item: DecisionContextDiagnostic) -> tuple[str, str, str, str]:
    return item.source_path, item.code, item.fragment_id, item.diagnostic_id

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Callable
import uuid

from p2p_engine.core.portable_verticals import VerticalCoordinate, is_semantic_version
from p2p_engine.core.project_domain import ProjectDomainRef, normalize_domain_tags
from p2p_engine.core.project_verticals import VerticalPack
from p2p_engine.core.vertical_registry import VerticalCatalogItem
from p2p_engine.core.vertical_drafts import (
    VERTICAL_DRAFT_DOCUMENT_VERSION,
    VERTICAL_DRAFT_EVIDENCE_VERSION,
    VERTICAL_DRAFT_MAX_DOCUMENT_BYTES,
    VERTICAL_DRAFT_MAX_FIELDS,
    VERTICAL_DRAFT_MAX_SECTIONS,
    VERTICAL_DRAFT_MAX_TEXT_BYTES,
    VERTICAL_DRAFT_STATE_VERSION,
    VerticalDraftAssessment,
    VerticalDraftDiagnostic,
    VerticalDraftEvidence,
    VerticalDraftOperationResult,
    VerticalDraftOrigin,
    VerticalDraftState,
    VerticalDraftView,
)
from p2p_engine.foundation.files import write_bytes_atomic, write_yaml_atomic
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.vertical_catalog import VerticalCatalogService
from p2p_engine.services.vertical_registry import vertical_user_paths


_DRAFT_ID = re.compile(r"^VDRAFT-[0-9A-F]{16,32}$")
_CONTENT_ID = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?$")
_CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
_ROOT_FIELDS = {
    "contract_version",
    "identity",
    "name",
    "description",
    "visibility",
    "extends",
    "lineage",
    "dependencies",
    "sections",
    "rubrics",
    "questions",
    "artifacts",
    "profiles",
    "modules",
    "examples",
    "source_attribution",
    "compatibility",
    "domain_metadata",
}


class VerticalDraftService:
    def __init__(
        self,
        root: Path,
        *,
        catalog: VerticalCatalogService | None = None,
        draft_root: Path | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.catalog = catalog or VerticalCatalogService(self.root)
        self.draft_root = (draft_root or vertical_user_paths().vertical_drafts_root).resolve()
        self.id_factory = id_factory or (
            lambda: f"VDRAFT-{uuid.uuid4().hex[:20].upper()}"
        )

    @staticmethod
    def schema() -> dict[str, object]:
        return {
            "contract_version": VERTICAL_DRAFT_DOCUMENT_VERSION,
            "state_version": VERTICAL_DRAFT_STATE_VERSION,
            "evidence_version": VERTICAL_DRAFT_EVIDENCE_VERSION,
            "limits": {
                "max_document_bytes": VERTICAL_DRAFT_MAX_DOCUMENT_BYTES,
                "max_sections": VERTICAL_DRAFT_MAX_SECTIONS,
                "max_fields": VERTICAL_DRAFT_MAX_FIELDS,
                "max_text_bytes": VERTICAL_DRAFT_MAX_TEXT_BYTES,
            },
            "identity": "publisher/id@semantic-version",
            "lineage_fields": ["forked_from", "previous_release"],
            "network_access": False,
        }

    def create_empty(
        self,
        *,
        publisher: str = "",
        vertical_id: str = "",
        version: str = "",
        license_id: str = "",
        name: str = "",
        description: str = "",
        visibility: str = "private",
    ) -> VerticalDraftOperationResult:
        document = self.empty_document(
            publisher=publisher,
            vertical_id=vertical_id,
            version=version,
            license_id=license_id,
            name=name,
            description=description,
            visibility=visibility,
        )
        return self._create(document, VerticalDraftOrigin(kind="empty"))

    def create_from(
        self,
        coordinate: str,
        *,
        publisher: str = "",
        vertical_id: str = "",
        version: str = "",
        license_id: str = "",
        name: str = "",
        description: str = "",
        visibility: str = "private",
        extends: str = "",
        forked_from: str = "",
        previous_release: str = "",
    ) -> VerticalDraftOperationResult:
        exact = str(VerticalCoordinate.parse(coordinate))
        item = self.catalog.resolve(exact)
        if item.artifact_path is not None:
            inspection = self.catalog.inspect_cached(item)
            pack = inspection.pack
            examples = self._cached_examples(item)
        else:
            pack = self.catalog.workspace.show_project_vertical(exact)
            examples = self._pack_examples(pack)
        document = self.document_from_pack(pack, examples=examples)
        identity = dict(document["identity"])
        identity["publisher"] = publisher or str(identity.get("publisher") or "")
        identity["id"] = vertical_id or str(identity.get("id") or "")
        identity["version"] = version or str(identity.get("version") or "")
        identity["license"] = license_id or str(identity.get("license") or "")
        document["identity"] = identity
        document["name"] = name or str(document.get("name") or "")
        document["description"] = description or str(document.get("description") or "")
        document["visibility"] = visibility
        document["extends"] = self._resolved_reference(extends) if extends else None
        document["dependencies"] = (
            [dict(document["extends"])] if document["extends"] else []
        )
        document["lineage"] = {
            "forked_from": self._resolved_reference(forked_from) if forked_from else None,
            "previous_release": (
                self._resolved_reference(previous_release) if previous_release else None
            ),
        }
        document["source_attribution"] = {
            "origin_coordinate": exact,
            "origin_semantic_checksum": item.semantic_checksum,
        }
        return self._create(
            document,
            VerticalDraftOrigin(
                kind="clone",
                coordinate=exact,
                semantic_checksum=item.semantic_checksum,
            ),
        )

    def inspect(self, draft_id: str) -> VerticalDraftView:
        state, evidence = self._read(draft_id)
        return self._view(state, evidence)

    def update(
        self,
        draft_id: str,
        document: dict[str, object],
        *,
        expected_revision: int | None = None,
        expected_hash: str = "",
    ) -> VerticalDraftOperationResult:
        if expected_revision is None and not expected_hash:
            raise ValueError(
                "P2P_VERTICAL_DRAFT_PRECONDITION_REQUIRED: expected revision or hash is required"
            )
        directory = self._directory(draft_id)
        with _DraftLock(directory / ".lock"):
            current, _evidence = self._read(draft_id)
            if expected_revision is not None and current.revision != expected_revision:
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_CONFLICT: expected revision does not match current draft"
                )
            if expected_hash and current.document_hash != expected_hash:
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_CONFLICT: expected hash does not match current draft"
                )
            normalized = normalize_vertical_draft_document(document)
            document_hash = vertical_draft_document_hash(normalized)
            state = VerticalDraftState(
                draft_id=current.draft_id,
                revision=current.revision + 1,
                document_hash=document_hash,
                status="drafted",
                origin=current.origin,
                document=normalized,
                path=current.path,
            )
            evidence = VerticalDraftEvidence.empty(state.revision, state.document_hash)
            self._write_pair(state, evidence)
        return VerticalDraftOperationResult(
            operation="update",
            draft=self._view(state, evidence),
            changed_paths=(
                str(self._draft_path(draft_id)),
                str(self._evidence_path(draft_id)),
            ),
        )

    def replace_evidence(
        self,
        draft_id: str,
        updater: Callable[[VerticalDraftState, VerticalDraftEvidence], VerticalDraftEvidence],
    ) -> VerticalDraftView:
        directory = self._directory(draft_id)
        with _DraftLock(directory / ".lock"):
            state, evidence = self._read(draft_id)
            updated = updater(state, evidence)
            if (
                updated.revision != state.revision
                or updated.document_hash != state.document_hash
            ):
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_EVIDENCE_STALE: evidence is not bound to current draft"
                )
            write_yaml_atomic(self._evidence_path(draft_id), _evidence_payload(updated))
        return self._view(state, updated)

    def assess(
        self,
        state: VerticalDraftState,
        evidence: VerticalDraftEvidence,
    ) -> VerticalDraftAssessment:
        diagnostics = document_diagnostics(state.document, origin=state.origin)
        readiness = document_readiness(state.document)
        structurally_valid = not any(item.severity == "error" for item in diagnostics)
        package = evidence.package or {}
        validation = evidence.validation or {}
        current_evidence = (
            evidence.revision == state.revision
            and evidence.document_hash == state.document_hash
        )
        publishable = bool(
            structurally_valid
            and current_evidence
            and validation.get("valid") is True
            and package.get("artifact_checksum")
        )
        return VerticalDraftAssessment(
            revision=state.revision,
            document_hash=state.document_hash,
            readiness=readiness,
            structurally_valid=structurally_valid,
            publishable=publishable,
            diagnostics=tuple(diagnostics),
        )

    @staticmethod
    def empty_document(
        *,
        publisher: str = "",
        vertical_id: str = "",
        version: str = "",
        license_id: str = "",
        name: str = "",
        description: str = "",
        visibility: str = "private",
    ) -> dict[str, object]:
        return normalize_vertical_draft_document(
            {
                "contract_version": VERTICAL_DRAFT_DOCUMENT_VERSION,
                "identity": {
                    "publisher": publisher,
                    "id": vertical_id,
                    "version": version,
                    "license": license_id,
                },
                "name": name,
                "description": description,
                "visibility": visibility,
                "extends": None,
                "lineage": {"forked_from": None, "previous_release": None},
                "dependencies": [],
                "sections": [],
                "rubrics": [],
                "questions": [],
                "artifacts": [],
                "profiles": {"enabled": [], "definitions": []},
                "modules": {"enabled": [], "definitions": []},
                "examples": [],
                "source_attribution": {},
                "compatibility": {},
                "domain_metadata": {"primary_domain": None, "domain_tags": []},
            }
        )

    @staticmethod
    def document_from_pack(
        pack: VerticalPack,
        *,
        examples: list[dict[str, str]] | None = None,
    ) -> dict[str, object]:
        manifest = pack.manifest
        if manifest is None:
            raise ValueError("P2P_VERTICAL_PORTABLE_V3_REQUIRED: source pack has no manifest")
        dependencies = [
            {
                "coordinate": item.coordinate,
                "semantic_checksum": item.checksum.removeprefix("sha256:"),
            }
            for item in manifest.dependencies
        ]
        dependency_by_coordinate = {
            str(item["coordinate"]): str(item["semantic_checksum"])
            for item in dependencies
        }
        extends = (
            {
                "coordinate": pack.extends,
                "semantic_checksum": dependency_by_coordinate.get(pack.extends, ""),
            }
            if pack.extends
            else None
        )
        document = {
            "contract_version": VERTICAL_DRAFT_DOCUMENT_VERSION,
            "identity": {
                "publisher": manifest.publisher,
                "id": pack.vertical_id,
                "version": pack.version,
                "license": manifest.license_id,
            },
            "name": pack.name,
            "description": pack.description,
            "visibility": "private",
            "extends": extends,
            "lineage": {
                "forked_from": _coordinate_reference(manifest.lineage.get("forked_from", "")),
                "previous_release": _coordinate_reference(
                    manifest.lineage.get("previous_release", "")
                ),
            },
            "dependencies": dependencies,
            "sections": [_section_document(item) for item in pack.sections],
            "rubrics": [
                {
                    "id": item.rubric_id,
                    "title": item.title,
                    "section_id": item.section_id,
                    "required": item.required,
                    "keywords": list(item.keywords),
                }
                for item in pack.rubrics
            ],
            "questions": [_question_document(item) for item in pack.questions],
            "artifacts": [
                {
                    "id": item.artifact_id,
                    "title": item.title,
                    "section_ids": list(item.section_ids),
                    "required": item.required,
                }
                for item in pack.artifacts
            ],
            "profiles": {
                "enabled": list(pack.profiles),
                "definitions": [
                    {
                        "id": item.profile_id,
                        "title": item.title,
                        "description": item.description,
                        "enabled_modules": list(item.enabled_modules),
                    }
                    for item in pack.profile_specs
                ],
            },
            "modules": {
                "enabled": list(pack.modules),
                "definitions": [
                    {
                        "id": item.module_id,
                        "title": item.title,
                        "description": item.description,
                        "section_ids": list(item.section_ids),
                    }
                    for item in pack.module_specs
                ],
            },
            "examples": list(examples or []),
            "source_attribution": {"pack_source": manifest.source},
            "compatibility": dict(pack.compatibility),
            "domain_metadata": {
                "primary_domain": (
                    manifest.primary_domain.to_dict()
                    if manifest.primary_domain is not None
                    else None
                ),
                "domain_tags": list(manifest.domain_tags),
            },
        }
        return normalize_vertical_draft_document(document)

    def _create(
        self,
        document: dict[str, object],
        origin: VerticalDraftOrigin,
    ) -> VerticalDraftOperationResult:
        normalized = normalize_vertical_draft_document(document)
        draft_id = _validate_draft_id(self.id_factory())
        directory = self._directory(draft_id)
        if directory.exists():
            raise ValueError(f"P2P_VERTICAL_DRAFT_CONFLICT: draft `{draft_id}` already exists")
        document_hash = vertical_draft_document_hash(normalized)
        state = VerticalDraftState(
            draft_id=draft_id,
            revision=1,
            document_hash=document_hash,
            status="drafted",
            origin=origin,
            document=normalized,
            path=directory,
        )
        evidence = VerticalDraftEvidence.empty(1, document_hash)
        self.draft_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        candidate = Path(tempfile.mkdtemp(prefix=f".{draft_id}.", dir=self.draft_root))
        try:
            write_yaml_atomic(candidate / "draft.yml", _state_payload(state))
            write_yaml_atomic(candidate / "evidence.yml", _evidence_payload(evidence))
            candidate.replace(directory)
        finally:
            shutil.rmtree(candidate, ignore_errors=True)
        return VerticalDraftOperationResult(
            operation="create",
            draft=self._view(state, evidence),
            changed_paths=(str(directory / "draft.yml"), str(directory / "evidence.yml")),
        )

    def _view(
        self,
        state: VerticalDraftState,
        evidence: VerticalDraftEvidence,
    ) -> VerticalDraftView:
        return VerticalDraftView(
            state=state,
            evidence=evidence,
            assessment=self.assess(state, evidence),
        )

    def _read(self, draft_id: str) -> tuple[VerticalDraftState, VerticalDraftEvidence]:
        draft_id = _validate_draft_id(draft_id)
        draft_path = self._draft_path(draft_id)
        evidence_path = self._evidence_path(draft_id)
        if not draft_path.is_file() or draft_path.is_symlink():
            raise ValueError(f"P2P_VERTICAL_DRAFT_NOT_FOUND: draft `{draft_id}` does not exist")
        try:
            draft_raw = load_yaml(draft_path.read_bytes())
            evidence_raw = load_yaml(evidence_path.read_bytes())
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"P2P_VERTICAL_DRAFT_INVALID: {exc}") from exc
        draft = draft_raw.get("vertical_draft") if isinstance(draft_raw, dict) else None
        evidence = (
            evidence_raw.get("vertical_draft_evidence")
            if isinstance(evidence_raw, dict)
            else None
        )
        if not isinstance(draft, dict) or not isinstance(evidence, dict):
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: invalid draft persistence envelope")
        if draft.get("contract_version") != VERTICAL_DRAFT_STATE_VERSION:
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: unsupported draft state contract")
        if evidence.get("contract_version") != VERTICAL_DRAFT_EVIDENCE_VERSION:
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: unsupported evidence contract")
        origin = draft.get("origin")
        if not isinstance(origin, dict):
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: origin must be a mapping")
        document = normalize_vertical_draft_document(draft.get("document"))
        document_hash = vertical_draft_document_hash(document)
        if document_hash != str(draft.get("document_hash") or ""):
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: persisted document hash mismatch")
        persisted_draft_id = _validate_draft_id(str(draft.get("draft_id") or ""))
        if persisted_draft_id != draft_id:
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: persisted draft ID does not match path")
        parsed_origin = _parse_origin(origin)
        state = VerticalDraftState(
            draft_id=persisted_draft_id,
            revision=_positive_revision(draft.get("revision")),
            document_hash=document_hash,
            status=str(draft.get("status") or "drafted"),
            origin=parsed_origin,
            document=document,
            path=self._directory(draft_id),
        )
        parsed_evidence = _parse_evidence(evidence)
        if (
            parsed_evidence.revision != state.revision
            or parsed_evidence.document_hash != state.document_hash
        ):
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: evidence binding is stale")
        return state, parsed_evidence

    def _write_pair(
        self,
        state: VerticalDraftState,
        evidence: VerticalDraftEvidence,
    ) -> None:
        draft_path = self._draft_path(state.draft_id)
        evidence_path = self._evidence_path(state.draft_id)
        draft_before = draft_path.read_bytes()
        evidence_before = evidence_path.read_bytes()
        try:
            write_yaml_atomic(draft_path, _state_payload(state))
            write_yaml_atomic(evidence_path, _evidence_payload(evidence))
        except Exception:
            write_bytes_atomic(draft_path, draft_before)
            write_bytes_atomic(evidence_path, evidence_before)
            raise

    def _resolved_reference(self, coordinate: str) -> dict[str, str]:
        exact = str(VerticalCoordinate.parse(coordinate))
        item = self.catalog.resolve(exact)
        return {
            "coordinate": exact,
            "semantic_checksum": item.semantic_checksum,
        }

    def _pack_examples(self, pack: VerticalPack) -> list[dict[str, str]]:
        assets: dict[str, str] = {}
        current: VerticalPack | None = pack
        visited: set[str] = set()
        while current is not None:
            identity = current.coordinate or current.vertical_id
            if identity in visited:
                break
            visited.add(identity)
            if current.path is not None:
                root = current.path.parent
                for name in current.examples:
                    path = root / "examples" / name
                    if path.is_file() and not path.is_symlink():
                        assets[name] = path.read_text(encoding="utf-8")
            current = (
                self.catalog.workspace.show_project_vertical(current.extends)
                if current.extends
                else None
            )
        return [
            {"path": name, "content": assets[name]}
            for name in sorted(assets)
        ]

    def _cached_examples(self, item: VerticalCatalogItem) -> list[dict[str, str]]:
        assets: dict[str, str] = {}
        for cached in self.catalog.installation_closure(item):
            entries = self.catalog.workspace._portable_vertical_package_service().read_archive(
                cached.artifact_path
            )
            for name, content in entries.items():
                if name.startswith("examples/"):
                    assets[name.removeprefix("examples/")] = content.decode("utf-8")
        return [
            {"path": name, "content": assets[name]}
            for name in sorted(assets)
        ]

    def _directory(self, draft_id: str) -> Path:
        return self.draft_root / _validate_draft_id(draft_id)

    def _draft_path(self, draft_id: str) -> Path:
        return self._directory(draft_id) / "draft.yml"

    def _evidence_path(self, draft_id: str) -> Path:
        return self._directory(draft_id) / "evidence.yml"


def normalize_vertical_draft_document(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("P2P_VERTICAL_DRAFT_INVALID: document must be a mapping")
    unknown = set(value) - _ROOT_FIELDS
    if unknown:
        raise ValueError(f"P2P_VERTICAL_DRAFT_INVALID: unknown fields {sorted(unknown)}")
    if value.get("contract_version") != VERTICAL_DRAFT_DOCUMENT_VERSION:
        raise ValueError(
            "P2P_VERTICAL_DRAFT_UNSUPPORTED_CONTRACT: expected p2p-vertical-draft/v1"
        )
    identity = _mapping(value.get("identity"), "identity")
    _reject_unknown(identity, {"publisher", "id", "version", "license"}, "identity")
    lineage = _mapping(value.get("lineage", {}), "lineage")
    _reject_unknown(lineage, {"forked_from", "previous_release"}, "lineage")
    sections = _mapping_list(value.get("sections", []), "sections")
    if len(sections) > VERTICAL_DRAFT_MAX_SECTIONS:
        raise ValueError("P2P_VERTICAL_DRAFT_LIMIT: too many sections")
    field_count = sum(
        len(_mapping_list(section.get("fields", []), f"sections[{index}].fields"))
        for index, section in enumerate(sections)
    )
    if field_count > VERTICAL_DRAFT_MAX_FIELDS:
        raise ValueError("P2P_VERTICAL_DRAFT_LIMIT: too many fields")
    profiles = _collection(value.get("profiles", {}), "profiles")
    modules = _collection(value.get("modules", {}), "modules")
    domain_metadata = _mapping(value.get("domain_metadata", {}), "domain_metadata")
    _reject_unknown(
        domain_metadata,
        {"primary_domain", "domain_tags"},
        "domain_metadata",
    )
    primary_domain_raw = domain_metadata.get("primary_domain")
    primary_domain = (
        ProjectDomainRef.from_mapping(primary_domain_raw).to_dict()
        if primary_domain_raw is not None
        else None
    )
    domain_tags = list(normalize_domain_tags(domain_metadata.get("domain_tags", [])))
    document: dict[str, object] = {
        "contract_version": VERTICAL_DRAFT_DOCUMENT_VERSION,
        "identity": {
            "publisher": _text(identity.get("publisher")),
            "id": _text(identity.get("id")),
            "version": _text(identity.get("version")),
            "license": _text(identity.get("license")),
        },
        "name": _text(value.get("name")),
        "description": _text(value.get("description")),
        "visibility": _text(value.get("visibility") or "private"),
        "extends": _reference(value.get("extends"), "extends"),
        "lineage": {
            "forked_from": _reference(lineage.get("forked_from"), "lineage.forked_from"),
            "previous_release": _reference(
                lineage.get("previous_release"),
                "lineage.previous_release",
            ),
        },
        "dependencies": [
            _reference(item, f"dependencies[{index}]")
            for index, item in enumerate(_list(value.get("dependencies", []), "dependencies"))
        ],
        "sections": _plain_mapping_list(sections),
        "rubrics": _plain_mapping_list(_mapping_list(value.get("rubrics", []), "rubrics")),
        "questions": _plain_mapping_list(
            _mapping_list(value.get("questions", []), "questions")
        ),
        "artifacts": _plain_mapping_list(
            _mapping_list(value.get("artifacts", []), "artifacts")
        ),
        "profiles": profiles,
        "modules": modules,
        "examples": _plain_mapping_list(
            _mapping_list(value.get("examples", []), "examples")
        ),
        "source_attribution": _plain_mapping(
            _mapping(value.get("source_attribution", {}), "source_attribution")
        ),
        "compatibility": _plain_mapping(
            _mapping(value.get("compatibility", {}), "compatibility")
        ),
        "domain_metadata": {
            "primary_domain": primary_domain,
            "domain_tags": domain_tags,
        },
    }
    _validate_text_limits(document)
    encoded = canonical_vertical_draft_document(document)
    if len(encoded) > VERTICAL_DRAFT_MAX_DOCUMENT_BYTES:
        raise ValueError("P2P_VERTICAL_DRAFT_LIMIT: document is too large")
    return json.loads(encoded.decode("ascii"))


def canonical_vertical_draft_document(document: dict[str, object]) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def vertical_draft_document_hash(document: dict[str, object]) -> str:
    return hashlib.sha256(canonical_vertical_draft_document(document)).hexdigest()


def document_diagnostics(
    document: dict[str, object],
    *,
    origin: VerticalDraftOrigin,
) -> list[VerticalDraftDiagnostic]:
    issues: list[VerticalDraftDiagnostic] = []

    def error(code: str, field: str, message: str) -> None:
        issues.append(VerticalDraftDiagnostic(code=code, field=field, message=message))

    identity = _mapping(document.get("identity"), "identity")
    for field in ("publisher", "id", "version", "license"):
        if not _text(identity.get(field)):
            error("P2P_VERTICAL_DRAFT_REQUIRED", f"identity.{field}", "required")
    coordinate = ""
    if all(_text(identity.get(field)) for field in ("publisher", "id", "version")):
        try:
            coordinate = str(
                VerticalCoordinate.parse(
                    f"{identity['publisher']}/{identity['id']}@{identity['version']}"
                )
            )
        except ValueError as exc:
            error("P2P_VERTICAL_INVALID_COORDINATE", "identity", str(exc))
    if identity.get("version") and not is_semantic_version(str(identity["version"])):
        error("P2P_VERTICAL_INVALID_SEMVER", "identity.version", "must be semantic version")
    for field in ("name", "description"):
        if not _text(document.get(field)):
            error("P2P_VERTICAL_DRAFT_REQUIRED", field, "required")
    if document.get("visibility") not in {"public", "private"}:
        error("P2P_VERTICAL_INVALID_VISIBILITY", "visibility", "must be public or private")
    sections = _mapping_list(document.get("sections", []), "sections")
    if not sections:
        error(
            "P2P_VERTICAL_NO_SECTIONS",
            "sections",
            "at least one governed section is required",
        )
    section_ids: set[str] = set()
    field_count = 0
    for index, section in enumerate(sections):
        section_id = _text(section.get("id"))
        if not section_id or not _CONTENT_ID.fullmatch(section_id):
            error("P2P_VERTICAL_DRAFT_INVALID_ID", f"sections[{index}].id", "invalid ID")
        elif section_id in section_ids:
            error("P2P_VERTICAL_DRAFT_DUPLICATE_ID", f"sections[{index}].id", "duplicate ID")
        section_ids.add(section_id)
        for field in ("title", "purpose"):
            if not _text(section.get(field)):
                error("P2P_VERTICAL_DRAFT_REQUIRED", f"sections[{index}].{field}", "required")
        fields = _mapping_list(section.get("fields", []), f"sections[{index}].fields")
        field_ids: set[str] = set()
        for field_index, field in enumerate(fields):
            field_count += 1
            field_id = _text(field.get("id"))
            if not field_id or not _CONTENT_ID.fullmatch(field_id):
                error(
                    "P2P_VERTICAL_DRAFT_INVALID_ID",
                    f"sections[{index}].fields[{field_index}].id",
                    "invalid ID",
                )
            elif field_id in field_ids:
                error(
                    "P2P_VERTICAL_DRAFT_DUPLICATE_ID",
                    f"sections[{index}].fields[{field_index}].id",
                    "duplicate ID",
                )
            field_ids.add(field_id)
            if not _text(field.get("label")):
                error(
                    "P2P_VERTICAL_DRAFT_REQUIRED",
                    f"sections[{index}].fields[{field_index}].label",
                    "required",
                )
    _reference_diagnostics(document.get("extends"), "extends", issues)
    dependency_coordinates: dict[str, str] = {}
    for index, dependency in enumerate(_list(document.get("dependencies", []), "dependencies")):
        _reference_diagnostics(dependency, f"dependencies[{index}]", issues)
        if isinstance(dependency, dict):
            dependency_coordinates[_text(dependency.get("coordinate"))] = _text(
                dependency.get("semantic_checksum")
            )
    extends = document.get("extends")
    if isinstance(extends, dict) and extends:
        extends_coordinate = _text(extends.get("coordinate"))
        if dependency_coordinates.get(extends_coordinate) != _text(
            extends.get("semantic_checksum")
        ):
            error(
                "P2P_VERTICAL_MISSING_BASE_DEPENDENCY",
                "extends",
                "structural base must have an exact matching dependency",
            )
    lineage = _mapping(document.get("lineage", {}), "lineage")
    for field in ("forked_from", "previous_release"):
        _reference_diagnostics(lineage.get(field), f"lineage.{field}", issues)
        reference = lineage.get(field)
        if coordinate and isinstance(reference, dict) and reference.get("coordinate") == coordinate:
            error(
                "P2P_VERTICAL_DRAFT_SELF_LINEAGE",
                f"lineage.{field}",
                "lineage cannot target the release being authored",
            )
    if origin.kind == "clone" and coordinate and coordinate == origin.coordinate:
        error(
            "P2P_VERTICAL_DRAFT_IDENTITY_UNCHANGED",
            "identity",
            "a clone needs a new publisher, ID or semantic version",
        )
    for index, rubric in enumerate(_mapping_list(document.get("rubrics", []), "rubrics")):
        if _text(rubric.get("section_id")) not in section_ids:
            error(
                "P2P_VERTICAL_DRAFT_UNKNOWN_SECTION",
                f"rubrics[{index}].section_id",
                "unknown section",
            )
    for collection in ("questions", "artifacts"):
        for index, item in enumerate(_mapping_list(document.get(collection, []), collection)):
            references = (
                [_text(item.get("section_id"))]
                if collection == "questions"
                else [_text(value) for value in _list(item.get("section_ids", []), "section_ids")]
            )
            if any(reference not in section_ids for reference in references):
                error(
                    "P2P_VERTICAL_DRAFT_UNKNOWN_SECTION",
                    f"{collection}[{index}]",
                    "references an unknown section",
                )
    if field_count > VERTICAL_DRAFT_MAX_FIELDS:
        error("P2P_VERTICAL_DRAFT_LIMIT", "sections.fields", "too many fields")
    return issues


def document_readiness(document: dict[str, object]) -> int:
    sections = _mapping_list(document.get("sections", []), "sections")
    if not sections:
        return 0
    identity = _mapping(document.get("identity", {}), "identity")
    checks = [
        bool(_text(identity.get(field)))
        for field in ("publisher", "id", "version", "license")
    ]
    checks.extend([bool(_text(document.get("name"))), bool(_text(document.get("description")))])
    for section in sections:
        checks.extend(
            [
                bool(_text(section.get("id"))),
                bool(_text(section.get("title"))),
                bool(_text(section.get("purpose"))),
            ]
        )
        fields = _mapping_list(section.get("fields", []), "fields")
        for field in fields:
            checks.extend([bool(_text(field.get("id"))), bool(_text(field.get("label")))])
    return round(100 * sum(checks) / len(checks)) if checks else 0


class _DraftLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "_DraftLock":
        try:
            self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.write(self.fd, str(os.getpid()).encode("ascii"))
        except FileExistsError as exc:
            raise ValueError("P2P_VERTICAL_DRAFT_BUSY: another draft mutation is active") from exc
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.fd is not None:
            os.close(self.fd)
        self.path.unlink(missing_ok=True)


def _state_payload(state: VerticalDraftState) -> dict[str, object]:
    return {
        "vertical_draft": {
            "contract_version": VERTICAL_DRAFT_STATE_VERSION,
            "draft_id": state.draft_id,
            "revision": state.revision,
            "document_hash": state.document_hash,
            "status": state.status,
            "origin": state.origin.to_dict(),
            "document": state.document,
        }
    }


def _evidence_payload(evidence: VerticalDraftEvidence) -> dict[str, object]:
    return {"vertical_draft_evidence": evidence.to_dict()}


def _parse_evidence(value: dict[str, object]) -> VerticalDraftEvidence:
    return VerticalDraftEvidence(
        revision=_positive_revision(value.get("revision")),
        document_hash=_checksum(value.get("document_hash"), "evidence document_hash"),
        materialization=_optional_mapping(value.get("materialization"), "materialization"),
        validation=_optional_mapping(value.get("validation"), "validation"),
        package=_optional_mapping(value.get("package"), "package"),
        local_adds=tuple(_mapping_list(value.get("local_adds", []), "local_adds")),
        publications=tuple(_mapping_list(value.get("publications", []), "publications")),
        last_publication_failure=_optional_mapping(
            value.get("last_publication_failure"),
            "last_publication_failure",
        ),
    )


def _validate_draft_id(value: str) -> str:
    draft_id = str(value).strip().upper()
    if not _DRAFT_ID.fullmatch(draft_id):
        raise ValueError("P2P_VERTICAL_DRAFT_INVALID_ID: invalid vertical draft ID")
    return draft_id


def _parse_origin(value: dict[str, object]) -> VerticalDraftOrigin:
    _reject_unknown(value, {"kind", "coordinate", "semantic_checksum"}, "origin")
    kind = _text(value.get("kind"))
    coordinate = _text(value.get("coordinate"))
    semantic_checksum = _text(value.get("semantic_checksum")).lower().removeprefix(
        "sha256:"
    )
    if kind == "empty":
        if coordinate or semantic_checksum:
            raise ValueError(
                "P2P_VERTICAL_DRAFT_INVALID: empty origin cannot identify a release"
            )
    elif kind == "clone":
        try:
            coordinate = str(VerticalCoordinate.parse(coordinate))
        except ValueError as exc:
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: clone origin coordinate is invalid") from exc
        if not _CHECKSUM.fullmatch(semantic_checksum):
            raise ValueError(
                "P2P_VERTICAL_DRAFT_INVALID: clone origin checksum must be SHA-256"
            )
    else:
        raise ValueError("P2P_VERTICAL_DRAFT_INVALID: unsupported draft origin")
    return VerticalDraftOrigin(
        kind=kind,
        coordinate=coordinate,
        semantic_checksum=semantic_checksum,
    )


def _positive_revision(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("P2P_VERTICAL_DRAFT_INVALID: revision must be a positive integer")
    try:
        revision = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("P2P_VERTICAL_DRAFT_INVALID: revision must be a positive integer") from exc
    if revision < 1:
        raise ValueError("P2P_VERTICAL_DRAFT_INVALID: revision must be a positive integer")
    return revision


def _checksum(value: object, field: str) -> str:
    text = _text(value).lower().removeprefix("sha256:")
    if not _CHECKSUM.fullmatch(text):
        raise ValueError(f"P2P_VERTICAL_DRAFT_INVALID: {field} must be SHA-256")
    return text


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"P2P_VERTICAL_DRAFT_INVALID: {field} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _optional_mapping(value: object, field: str) -> dict[str, object] | None:
    if value is None:
        return None
    return _mapping(value, field)


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"P2P_VERTICAL_DRAFT_INVALID: {field} must be a list")
    return value


def _mapping_list(value: object, field: str) -> list[dict[str, object]]:
    return [_mapping(item, f"{field}[{index}]") for index, item in enumerate(_list(value, field))]


def _plain_mapping(value: dict[str, object]) -> dict[str, object]:
    try:
        return json.loads(json.dumps(value, ensure_ascii=True))
    except (TypeError, ValueError) as exc:
        raise ValueError("P2P_VERTICAL_DRAFT_INVALID: document values must be JSON-compatible") from exc


def _plain_mapping_list(value: list[dict[str, object]]) -> list[dict[str, object]]:
    return [_plain_mapping(item) for item in value]


def _collection(value: object, field: str) -> dict[str, object]:
    collection = _mapping(value, field)
    _reject_unknown(collection, {"enabled", "definitions"}, field)
    enabled = [_text(item) for item in _list(collection.get("enabled", []), f"{field}.enabled")]
    definitions = _plain_mapping_list(
        _mapping_list(collection.get("definitions", []), f"{field}.definitions")
    )
    for definition in definitions:
        definition_id = _text(definition.get("id"))
        if definition_id and definition_id not in enabled:
            enabled.append(definition_id)
    return {"enabled": enabled, "definitions": definitions}


def _reference(value: object, field: str) -> dict[str, str] | None:
    if value is None or value == {}:
        return None
    reference = _mapping(value, field)
    _reject_unknown(reference, {"coordinate", "semantic_checksum"}, field)
    return {
        "coordinate": _text(reference.get("coordinate")),
        "semantic_checksum": _text(reference.get("semantic_checksum")).lower().removeprefix(
            "sha256:"
        ),
    }


def _coordinate_reference(value: str) -> dict[str, str] | None:
    return {"coordinate": value, "semantic_checksum": ""} if value else None


def _reject_unknown(value: dict[str, object], allowed: set[str], field: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(
            f"P2P_VERTICAL_DRAFT_INVALID: {field} has unknown fields {sorted(unknown)}"
        )


def _text(value: object) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def _validate_text_limits(value: object, field: str = "document") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_text_limits(item, f"{field}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_text_limits(item, f"{field}[{index}]")
    elif isinstance(value, str) and len(value.encode("utf-8")) > VERTICAL_DRAFT_MAX_TEXT_BYTES:
        raise ValueError(f"P2P_VERTICAL_DRAFT_LIMIT: text value too large at {field}")


def _reference_diagnostics(
    value: object,
    field: str,
    issues: list[VerticalDraftDiagnostic],
) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        issues.append(
            VerticalDraftDiagnostic(
                code="P2P_VERTICAL_DRAFT_INVALID_REFERENCE",
                field=field,
                message="reference must be a mapping",
            )
        )
        return
    try:
        VerticalCoordinate.parse(_text(value.get("coordinate")))
    except ValueError as exc:
        issues.append(
            VerticalDraftDiagnostic(
                code="P2P_VERTICAL_DRAFT_INVALID_REFERENCE",
                field=f"{field}.coordinate",
                message=str(exc),
            )
        )
    if not _CHECKSUM.fullmatch(_text(value.get("semantic_checksum"))):
        issues.append(
            VerticalDraftDiagnostic(
                code="P2P_VERTICAL_DRAFT_INVALID_REFERENCE",
                field=f"{field}.semantic_checksum",
                message="semantic checksum must be SHA-256",
            )
        )


def _section_document(section) -> dict[str, object]:
    return {
        "id": section.section_id,
        "title": section.title,
        "purpose": section.purpose,
        "required": section.required,
        "priority": section.priority,
        "fields": [
            {
                "id": field.field_id,
                "label": field.label,
                "required": field.required,
                "question": field.question,
                "assisted_answer": field.assisted_answer,
                "completion_criteria": list(field.completion_criteria),
                "common_mistakes": list(field.common_mistakes),
                "suggested_artifacts": list(field.suggested_artifacts),
                "maturity_gates": list(field.maturity_gates),
            }
            for field in section.fields
        ],
        "completion_policy": (
            {
                "allow_assumed_completion": section.completion_policy.allow_assumed_completion,
                "required_fields": list(section.completion_policy.required_fields),
            }
            if section.completion_policy
            else {}
        ),
    }


def _question_document(question) -> dict[str, object]:
    result: dict[str, object] = {
        "id": question.question_id,
        "section_id": question.section_id,
        "priority": question.priority,
        "question": question.question,
        "rationale": question.rationale,
    }
    if question.target_kind and question.target_id:
        result["target"] = {"kind": question.target_kind, "id": question.target_id}
    if question.answer_contract:
        result["answer_contract"] = dict(question.answer_contract)
    if question.fallback_key:
        result["fallback_key"] = question.fallback_key
    if question.aliases:
        result["aliases"] = list(question.aliases)
    if question.deferred_trigger:
        result["deferred_trigger"] = dict(question.deferred_trigger)
    return result

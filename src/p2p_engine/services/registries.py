from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path

from p2p_engine.core.mutation_preview import semantic_sha256, source_precondition
from p2p_engine.core.registries import (
    REGISTRY_GENERATOR_CONTRACT_VERSION,
    REGISTRY_MANIFEST_VERSION,
    REGISTRY_SOURCE_CATALOG_POLICY_VERSION,
    RegistryBundleManifest,
    RegistryOutputManifest,
    RegistryStatus,
)
from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.services.workspace_reads import WorkspaceReadContext


@dataclass(frozen=True)
class RegistryView:
    name: str
    path: Path
    records: list[dict[str, object]]
    source: str = "registry"


@dataclass(frozen=True)
class _CatalogEntry:
    path: str
    identity: str
    content: bytes | None
    scopes: tuple[str, ...]


RegistryRecords = Callable[[], list[dict[str, object]]]
RegistryRecordsFromProposals = Callable[[list[dict[str, object]]], list[dict[str, object]]]
RegistryRecordsFromProposalsChanges = Callable[
    [list[dict[str, object]], list[dict[str, object]]],
    list[dict[str, object]],
]
RegistryRecordsWithChanges = Callable[[list[dict[str, object]]], list[dict[str, object]]]


REGISTRY_DEFINITIONS: dict[str, dict[str, str]] = {
    "proposals": {"filename": "proposals.yml", "source": ".p2p/proposals"},
    "decisions": {
        "filename": "decisions.yml",
        "source": (
            ".p2p/proposals/*/decision-events.yml "
            "and schema-v2 decision.md compatibility projections"
        ),
    },
    "changes": {"filename": "changes.yml", "source": ".p2p/changes"},
    "choices": {"filename": "choices.yml", "source": ".p2p/choices and proposal votes"},
    "relations": {"filename": "relations.yml", "source": ".p2p proposal and change metadata"},
    "artifacts": {"filename": "artifacts.yml", "source": ".p2p"},
    "readiness": {"filename": "readiness.yml", "source": ".p2p/proposals/*/readiness.yml"},
}
REGISTRY_MANIFEST_PATH = ".p2p/registries/manifest.yml"
REGISTRY_OWNED_PATHS = (
    REGISTRY_MANIFEST_PATH,
    *(
        f".p2p/registries/{definition['filename']}"
        for definition in REGISTRY_DEFINITIONS.values()
    ),
)
_PROPOSAL_CONTENT_FILES = {
    "proposal.md": ("proposals", "decisions", "relations", "readiness"),
    "decision.md": ("decisions",),
    "decision-events.yml": ("proposals", "decisions", "relations", "readiness"),
    "readiness.yml": ("readiness",),
    "votes.yml": ("choices",),
}
_CHANGE_CONTENT_FILES = {
    "change.md": ("changes", "proposals", "relations", "readiness"),
    "tasks.yml": ("changes",),
    "referenced-proposals.yml": ("changes", "relations"),
}
_CHOICE_CONTENT_FILES = {
    "choice.md": ("choices",),
    "options.yml": ("choices",),
    "decision.md": ("choices",),
}


class RegistryService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        duplicate_proposal_ids: Callable[[], dict[str, list[Path]]],
        duplicate_message: Callable[[dict[str, list[Path]]], str],
        proposal_records: RegistryRecords,
        change_records: RegistryRecords,
        decision_records: RegistryRecordsFromProposals,
        choice_records: RegistryRecords,
        relation_records: RegistryRecordsFromProposalsChanges,
        artifact_records: RegistryRecordsFromProposalsChanges,
        readiness_records: RegistryRecordsFromProposals,
        proposal_records_with_changes: RegistryRecordsWithChanges | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
    ) -> None:
        self.root = root.resolve()
        self._root_part_count = len(self.root.parts)
        self.p2p_dir = p2p_dir.resolve()
        self.duplicate_proposal_ids = duplicate_proposal_ids
        self.duplicate_message = duplicate_message
        self.proposal_records = proposal_records
        self.change_records = change_records
        self.decision_records = decision_records
        self.choice_records = choice_records
        self.relation_records = relation_records
        self.artifact_records = artifact_records
        self.readiness_records = readiness_records
        self.proposal_records_with_changes = proposal_records_with_changes
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )

    def refresh(self) -> list[Path]:
        duplicates = self.duplicate_proposal_ids()
        if duplicates:
            raise ValueError(self.duplicate_message(duplicates))
        catalog = self._source_catalog()
        source_fingerprint, scope_fingerprints = _catalog_fingerprints(catalog)
        records_by_name = self._render_records()
        candidates: dict[str, bytes] = {}
        output_manifest: dict[str, RegistryOutputManifest] = {}
        for name, definition in REGISTRY_DEFINITIONS.items():
            relative = f".p2p/registries/{definition['filename']}"
            content = _yaml_dump(
                {
                    "generated": True,
                    "source": definition["source"],
                    name: records_by_name[name],
                }
            ).encode("utf-8")
            candidates[relative] = content
            output_manifest[definition["filename"]] = RegistryOutputManifest(
                sha256=hashlib.sha256(content).hexdigest(),
                records=len(records_by_name[name]),
            )
        manifest = RegistryBundleManifest(
            manifest_version=REGISTRY_MANIFEST_VERSION,
            generator_contract_version=REGISTRY_GENERATOR_CONTRACT_VERSION,
            source_catalog_policy_version=REGISTRY_SOURCE_CATALOG_POLICY_VERSION,
            source_fingerprint_sha256=source_fingerprint,
            source_scopes=scope_fingerprints,
            outputs=output_manifest,
            owned_paths=tuple(REGISTRY_OWNED_PATHS),
        )
        manifest.validate()
        candidates[REGISTRY_MANIFEST_PATH] = _yaml_dump(manifest.to_dict()).encode("utf-8")
        if all(
            (self.root / relative).is_file()
            and (self.root / relative).read_bytes() == content
            for relative, content in candidates.items()
        ):
            return []
        source_contents = {
            entry.path: entry.content
            for entry in catalog
            if entry.content is not None
        }
        for relative in candidates:
            path = self.root / relative
            source_contents[relative] = path.read_bytes() if path.is_file() else None
        preconditions = tuple(
            source_precondition(path, content)
            for path, content in sorted(source_contents.items())
        )
        preview_token = semantic_sha256(
            {
                "operation": "registry-bundle-refresh",
                "source_fingerprint": source_fingerprint,
                "outputs": {
                    path: hashlib.sha256(content).hexdigest()
                    for path, content in sorted(candidates.items())
                },
            }
        )

        def validate_candidate(view) -> None:
            current_fingerprint, _ = _catalog_fingerprints(self._source_catalog())
            if current_fingerprint != source_fingerprint:
                raise ValueError("Registry source catalog changed during candidate generation")
            payload = view.read_yaml_mapping(REGISTRY_MANIFEST_PATH)
            parsed = _manifest_from_payload(payload)
            parsed.validate()
            for filename, output in parsed.outputs.items():
                content = view.read_bytes(f".p2p/registries/{filename}")
                if hashlib.sha256(content).hexdigest() != output.sha256:
                    raise ValueError(f"Registry candidate digest mismatch: {filename}")
            view.assert_owned_reads_used_candidates()

        result = self.atomic_writer.apply(
            operation_id="registry-bundle-refresh",
            candidates=candidates,
            sources=preconditions,
            preview_token=preview_token,
            actor="p2p-registry-refresh",
            candidate_validator=validate_candidate,
        )
        if result.status != "applied":
            raise ValueError(result.message or f"Registry refresh failed: {result.status}")
        return [
            Path(f".p2p/registries/{definition['filename']}")
            for definition in REGISTRY_DEFINITIONS.values()
        ] + [Path(REGISTRY_MANIFEST_PATH)]

    def status(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> RegistryStatus:
        registries_dir = self.p2p_dir / "registries"
        manifest_path = self.root / REGISTRY_MANIFEST_PATH
        try:
            manifest_exists = (
                read_context.documents.capture(manifest_path).exists
                if read_context is not None
                else manifest_path.exists()
            )
        except ValueError as exc:
            return self._status_without_manifest("invalid", reason=str(exc))
        if not manifest_exists:
            state = "legacy_unverifiable" if any(
                (registries_dir / item["filename"]).exists()
                for item in REGISTRY_DEFINITIONS.values()
            ) else "missing"
            return self._status_without_manifest(state)
        try:
            payload = (
                read_context.documents.yaml(manifest_path)
                if read_context is not None
                else _read_yaml_mapping(manifest_path, default={})
            )
            if not isinstance(payload, Mapping):
                raise ValueError("Invalid registry manifest: expected mapping")
            manifest = _manifest_from_payload(
                payload
            )
            manifest.validate()
        except ValueError as exc:
            state = "unsupported" if "Unsupported" in str(exc) else "invalid"
            return self._status_without_manifest(state, reason=str(exc))
        current_fingerprint, _ = _catalog_fingerprints(
            self._source_catalog(read_context=read_context)
        )
        files: list[Mapping[str, object]] = []
        output_mismatch = False
        for name, definition in REGISTRY_DEFINITIONS.items():
            filename = definition["filename"]
            output = manifest.outputs.get(filename)
            path = registries_dir / filename
            if read_context is not None:
                try:
                    document = read_context.documents.capture(path)
                except ValueError:
                    exists = False
                    digest = ""
                else:
                    exists = document.exists
                    digest = document.physical_sha256 or ""
            else:
                exists = path.is_file()
                digest = hashlib.sha256(path.read_bytes()).hexdigest() if exists else ""
            valid = output is not None and digest == output.sha256
            output_mismatch = output_mismatch or not valid
            files.append(
                {
                    "name": filename,
                    "exists": exists,
                    "generated": valid,
                    "records": output.records if output is not None else 0,
                    "sha256": digest,
                }
            )
        source_stale = current_fingerprint != manifest.source_fingerprint_sha256
        stale = source_stale or output_mismatch
        state = "mixed_output" if output_mismatch else "stale" if source_stale else "current"
        reason = (
            "One or more registry outputs do not match the committed manifest."
            if output_mismatch
            else "Canonical registry sources changed after refresh."
            if source_stale
            else "Registry bundle source and output fingerprints are current."
        )
        return RegistryStatus(
            registries_dir=registries_dir.relative_to(self.root),
            files=tuple(files),
            proposals_count=_manifest_record_count(manifest, "proposals.yml"),
            changes_count=_manifest_record_count(manifest, "changes.yml"),
            stale=stale,
            state=state,
            reason=reason,
            manifest_version=manifest.manifest_version,
            source_fingerprint_sha256=manifest.source_fingerprint_sha256,
            current_source_fingerprint_sha256=current_fingerprint,
            verification={"sources": "hashed", "outputs": "hashed", "records": "not_rebuilt"},
        )

    def fast_status(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> RegistryStatus:
        registries_dir = self.p2p_dir / "registries"
        manifest_path = self.root / REGISTRY_MANIFEST_PATH
        try:
            exists = (
                read_context.documents.capture(manifest_path).exists
                if read_context is not None
                else manifest_path.is_file()
            )
        except ValueError as exc:
            return self._status_without_manifest("invalid", reason=str(exc))
        if not exists:
            state = "legacy_unverifiable" if any(
                (registries_dir / item["filename"]).exists()
                for item in REGISTRY_DEFINITIONS.values()
            ) else "missing"
            return self._status_without_manifest(state)
        try:
            payload = (
                read_context.documents.yaml(manifest_path)
                if read_context is not None
                else _read_yaml_mapping(manifest_path, default={})
            )
            if not isinstance(payload, Mapping):
                raise ValueError("Invalid registry manifest: expected mapping")
            manifest = _manifest_from_payload(payload)
            manifest.validate()
        except ValueError as exc:
            state = "unsupported" if "Unsupported" in str(exc) else "invalid"
            return self._status_without_manifest(state, reason=str(exc))
        files: list[Mapping[str, object]] = []
        output_mismatch = False
        for definition in REGISTRY_DEFINITIONS.values():
            filename = definition["filename"]
            output = manifest.outputs.get(filename)
            path = registries_dir / filename
            try:
                if read_context is not None:
                    document = read_context.documents.capture(path)
                    exists = document.exists
                    digest = document.physical_sha256 or ""
                else:
                    exists = path.is_file() and not path.is_symlink()
                    digest = hashlib.sha256(path.read_bytes()).hexdigest() if exists else ""
            except ValueError:
                exists = False
                digest = ""
            valid = output is not None and digest == output.sha256
            output_mismatch = output_mismatch or not valid
            files.append(
                {
                    "name": filename,
                    "exists": exists,
                    "generated": valid,
                    "records": output.records if output is not None else 0,
                    "sha256": digest,
                }
            )
        return RegistryStatus(
            registries_dir=registries_dir.relative_to(self.root),
            files=tuple(files),
            proposals_count=_manifest_record_count(manifest, "proposals.yml"),
            changes_count=_manifest_record_count(manifest, "changes.yml"),
            stale=output_mismatch,
            state="mixed_output" if output_mismatch else "current",
            reason=(
                "One or more registry outputs do not match the committed manifest."
                if output_mismatch
                else "Registry manifest and outputs are intact; canonical sources were not rehashed."
            ),
            manifest_version=manifest.manifest_version,
            source_fingerprint_sha256=manifest.source_fingerprint_sha256,
            current_source_fingerprint_sha256="",
            verification={
                "sources": "not_run",
                "outputs": "hashed",
                "records": "not_rebuilt",
            },
        )

    def show(
        self,
        name: str,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> RegistryView:
        if name not in REGISTRY_DEFINITIONS:
            raise ValueError(f"Unsupported registry: {name}")
        definition = REGISTRY_DEFINITIONS[name]
        path = self.p2p_dir / "registries" / definition["filename"]
        status = self.status(read_context=read_context)
        if status.state != "current":
            records = self._render_records()[name]
            return RegistryView(
                name=name,
                path=path.relative_to(self.root),
                records=records,
                source="canonical_fallback",
            )
        data = (
            read_context.documents.yaml(path)
            if read_context is not None
            else _read_yaml_mapping(path, default={})
        )
        if not isinstance(data, Mapping):
            raise ValueError(f"Invalid registry file: expected `{name}` mapping.")
        records = data.get(name, [])
        if not isinstance(records, list):
            raise ValueError(f"Invalid registry file: expected `{name}` list.")
        return RegistryView(
            name=name,
            path=path.relative_to(self.root),
            records=[record for record in records if isinstance(record, dict)],
        )

    def _render_records(self) -> dict[str, list[dict[str, object]]]:
        changes = self.change_records()
        proposals = (
            self.proposal_records_with_changes(changes)
            if self.proposal_records_with_changes is not None
            else self.proposal_records()
        )
        return {
            "proposals": proposals,
            "decisions": self.decision_records(proposals),
            "changes": changes,
            "choices": self.choice_records(),
            "relations": self.relation_records(proposals, changes),
            "artifacts": self.artifact_records(proposals, changes),
            "readiness": self.readiness_records(proposals),
        }

    def _source_catalog(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> tuple[_CatalogEntry, ...]:
        entries: list[_CatalogEntry] = []
        for domain, content_files in (
            ("proposals", _PROPOSAL_CONTENT_FILES),
            ("changes", _CHANGE_CONTENT_FILES),
            ("choices", _CHOICE_CONTENT_FILES),
        ):
            base = self.p2p_dir / domain
            if not base.exists():
                continue
            if base.is_symlink() or not base.is_dir():
                raise ValueError(f"Unsafe registry source directory: {base}")
            paths = (
                read_context.documents.discover(
                    base,
                    policy=f"registry-{domain}-sources-v1",
                    recursive=True,
                )
                if read_context is not None
                else sorted(
                    base.rglob("*"),
                    key=lambda item: item.relative_to(self.root).as_posix(),
                )
            )
            for path in paths:
                if path.is_symlink():
                    raise ValueError(f"Registry source catalog rejects symlink: {path}")
                relative = "/".join(path.parts[self._root_part_count :])
                if path.is_dir():
                    scopes = _directory_scopes(domain)
                    entries.append(_CatalogEntry(relative, "directory", None, scopes))
                    continue
                if not path.is_file():
                    continue
                scopes = content_files.get(path.name, _identity_scopes(domain))
                content = (
                    read_context.documents.bytes(path)
                    if read_context is not None
                    else path.read_bytes()
                ) if path.name in content_files else None
                identity = (
                    hashlib.sha256(content).hexdigest()
                    if content is not None
                    else "file"
                )
                entries.append(_CatalogEntry(relative, identity, content, tuple(scopes)))
        return tuple(entries)

    def _status_without_manifest(self, state: str, *, reason: str = "") -> RegistryStatus:
        registries_dir = self.p2p_dir / "registries"
        files = tuple(
            {
                "name": definition["filename"],
                "exists": (registries_dir / definition["filename"]).is_file(),
                "generated": False,
                "records": 0,
            }
            for definition in REGISTRY_DEFINITIONS.values()
        )
        return RegistryStatus(
            registries_dir=registries_dir.relative_to(self.root),
            files=files,
            proposals_count=_child_directory_count(self.p2p_dir / "proposals"),
            changes_count=_child_directory_count(self.p2p_dir / "changes"),
            stale=True,
            state=state,
            reason=reason or (
                "Legacy registry files have no verifiable bundle manifest."
                if state == "legacy_unverifiable"
                else "Registry bundle manifest is missing."
            ),
            verification={"sources": "not_verified", "outputs": "not_verified"},
        )


def _directory_scopes(domain: str) -> tuple[str, ...]:
    if domain == "proposals":
        return ("proposals", "decisions", "choices", "relations", "artifacts", "readiness")
    if domain == "changes":
        return ("changes", "proposals", "relations", "artifacts", "readiness")
    return ("choices",)


def _identity_scopes(domain: str) -> tuple[str, ...]:
    if domain == "proposals":
        return ("proposals", "artifacts")
    if domain == "changes":
        return ("changes", "artifacts")
    return ()


def _catalog_fingerprints(
    catalog: tuple[_CatalogEntry, ...],
) -> tuple[str, dict[str, str]]:
    all_payload = [(item.path, item.identity) for item in catalog]
    scopes = {
        name: semantic_sha256(
            [(item.path, item.identity) for item in catalog if name in item.scopes]
        )
        for name in REGISTRY_DEFINITIONS
    }
    return semantic_sha256(all_payload), scopes


def _manifest_from_payload(payload: Mapping[str, object]) -> RegistryBundleManifest:
    data = payload.get("registry_bundle")
    if not isinstance(data, Mapping):
        raise ValueError("Invalid registry manifest: missing registry_bundle mapping")
    fingerprint = data.get("source_fingerprint")
    if not isinstance(fingerprint, Mapping) or fingerprint.get("algorithm") != "sha256":
        raise ValueError("Invalid registry manifest source fingerprint")
    raw_scopes = data.get("source_scopes")
    raw_outputs = data.get("outputs")
    owned = data.get("owned_paths")
    if not isinstance(raw_scopes, Mapping) or not isinstance(raw_outputs, Mapping) or not isinstance(owned, list):
        raise ValueError("Invalid registry manifest collections")
    outputs: dict[str, RegistryOutputManifest] = {}
    for name, value in raw_outputs.items():
        if not isinstance(value, Mapping):
            raise ValueError(f"Invalid registry output manifest: {name}")
        records = value.get("records")
        if isinstance(records, bool) or not isinstance(records, int):
            raise ValueError(f"Invalid registry output count: {name}")
        outputs[str(name)] = RegistryOutputManifest(
            sha256=str(value.get("sha256") or ""),
            records=records,
        )
    return RegistryBundleManifest(
        manifest_version=int(data.get("manifest_version") or 0),
        generator_contract_version=str(data.get("generator_contract_version") or ""),
        source_catalog_policy_version=str(data.get("source_catalog_policy_version") or ""),
        source_fingerprint_sha256=str(fingerprint.get("value") or ""),
        source_scopes={str(key): str(value) for key, value in raw_scopes.items()},
        outputs=outputs,
        owned_paths=tuple(str(item) for item in owned),
    )


def _manifest_record_count(manifest: RegistryBundleManifest, filename: str) -> int:
    output = manifest.outputs.get(filename)
    return output.records if output is not None else 0


def _child_directory_count(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for item in path.iterdir() if item.is_dir() and not item.is_symlink())

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    SourcePrecondition,
)
from p2p_engine.foundation.files import (
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import read_frontmatter, read_markdown_section, read_title
from p2p_engine.foundation.validators import validate_yaml_key
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


SOFTWARE_SPEC_REQUIRED_FILES = (
    "index.md",
    "requirements.md",
    "design.md",
    "commands.yml",
    "data-model.yml",
    "acceptance.md",
    "provenance.yml",
)
SOFTWARE_SPEC_PROVENANCE_SCHEMA_VERSION = 1
SOFTWARE_SPEC_RENDERER_VERSION = 1
SOFTWARE_SPEC_GENERATOR = "p2p_engine.software_spec"
SOFTWARE_SPEC_NON_PROVENANCE_FILES = tuple(
    filename for filename in SOFTWARE_SPEC_REQUIRED_FILES if filename != "provenance.yml"
)


class SoftwareSpecFreshness(StrEnum):
    CURRENT = "current"
    CURRENT_IMPORTED = "current_imported"
    STALE = "stale"
    MODIFIED = "modified"
    INVALID = "invalid"
    INCOMPLETE = "incomplete"


class SoftwareSpecOrigin(StrEnum):
    GENERATED = "generated"
    IMPORTED = "imported"
    INVALID = "invalid"


@dataclass(frozen=True)
class SoftwareSpecSourceRecord:
    path: str
    exists: bool
    sha256: str = ""

    def payload(self) -> dict[str, object]:
        return {
            "path": self.path,
            "exists": self.exists,
            "sha256": self.sha256,
        }

    def precondition(self) -> SourcePrecondition:
        return SourcePrecondition(
            path=self.path,
            exists=self.exists,
            physical_sha256=self.sha256 or None,
        )


@dataclass(frozen=True)
class SoftwareSpecProposalInput:
    proposal_id: str
    title: str
    proposal: str


@dataclass(frozen=True)
class SoftwareSpecCandidate:
    change_id: str
    title: str
    files: tuple[tuple[str, str], ...]
    sources: tuple[SoftwareSpecSourceRecord, ...]
    source_fingerprint_sha256: str
    renderer_version: int = SOFTWARE_SPEC_RENDERER_VERSION

    def file_map(self) -> dict[str, str]:
        return dict(self.files)


@dataclass(frozen=True)
class SoftwareSpecStatus:
    change_id: str
    title: str
    status: str
    path: Path
    lifecycle: Any | None = None
    freshness: SoftwareSpecFreshness = SoftwareSpecFreshness.INVALID
    origin: SoftwareSpecOrigin = SoftwareSpecOrigin.INVALID
    current_source_fingerprint_sha256: str = ""
    recorded_source_fingerprint_sha256: str = ""
    changed_sources: tuple[str, ...] = ()
    changed_outputs: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    suggested_command: str = ""


@dataclass(frozen=True)
class SoftwareSpecPrompt:
    change_id: str
    prompt_path: Path


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _physical_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _proposal_title(proposal_id: str, text: str) -> str:
    title = read_title(text) or proposal_id
    cleaned = re.sub(rf"^{re.escape(proposal_id)}\s*[-—]\s*", "", title).strip()
    return cleaned or title


def _mapping_from_bytes(content: bytes | None, *, default: dict[str, object]) -> dict[str, object]:
    if content is None:
        return dict(default)
    value = load_yaml(content)
    return value if isinstance(value, dict) else dict(default)


def _safe_int(value: object, *, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


class SoftwareSpecService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_change_dir: Callable[[str], Path],
        show_change_set: Callable[[str], Any],
        find_proposal_dir: Callable[[str], Path],
        proposal_lifecycle_status: (
            Callable[[str], ProposalDecisionLifecycleView] | None
        ) = None,
        atomic_writer: AtomicMutationWriter | None = None,
        source_reader: Callable[[Path], bytes] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_change_dir = find_change_dir
        self.show_change_set = show_change_set
        self.find_proposal_dir = find_proposal_dir
        self.proposal_lifecycle_status = proposal_lifecycle_status
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.source_reader = source_reader or (lambda path: path.read_bytes())

    def required_files(self) -> tuple[str, ...]:
        return SOFTWARE_SPEC_REQUIRED_FILES

    def refresh(self, change_id: str) -> SoftwareSpecStatus:
        candidate = self.build_candidate(change_id)
        spec_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        self._commit_required_files(
            operation_id=f"software-spec-refresh:{change_id}",
            spec_dir=spec_dir,
            files=candidate.file_map(),
            dependency_sources=candidate.sources,
            actor="system",
        )
        return SoftwareSpecStatus(
            change_id=change_id,
            title=candidate.title,
            status="generated",
            path=spec_dir.relative_to(self.root),
            freshness=SoftwareSpecFreshness.CURRENT,
            origin=SoftwareSpecOrigin.GENERATED,
            current_source_fingerprint_sha256=candidate.source_fingerprint_sha256,
            recorded_source_fingerprint_sha256=candidate.source_fingerprint_sha256,
            reasons=(
                "source_fingerprint_matches",
                "generated_outputs_match_candidate",
            ),
        )

    def build_candidate(self, change_id: str) -> SoftwareSpecCandidate:
        for _attempt in range(2):
            candidate = self._build_candidate_once(change_id)
            if self._sources_still_match(candidate.sources):
                return candidate
        raise ValueError(
            f"software_spec_source_changed_during_read:{change_id}"
        )

    def _build_candidate_once(self, change_id: str) -> SoftwareSpecCandidate:
        change_dir = self.find_change_dir(change_id)
        change_path = change_dir / "change.md"
        tasks_path = change_dir / "tasks.yml"
        change_content = self._read_source(change_path)
        tasks_content = self._read_source(tasks_path)
        self._require_source(change_path, change_content)
        self._require_source(tasks_path, tasks_content)
        change_text = (change_content or b"").decode("utf-8")
        frontmatter = read_frontmatter(change_text)
        title = str(frontmatter.get("title") or read_title(change_text) or change_id)
        source = frontmatter.get("source", {})
        if not isinstance(source, dict):
            source = {}
        included_proposals = _string_list(source.get("accepted_proposals"))
        proposal_inputs: list[SoftwareSpecProposalInput] = []
        source_records = [
            self._source_record(change_path, change_content),
            self._source_record(tasks_path, tasks_content),
        ]
        generated_from = [
            str(change_path.relative_to(self.root)),
            str(tasks_path.relative_to(self.root)),
        ]
        decision_bindings: list[dict[str, object]] = []
        for proposal_id in included_proposals:
            proposal_dir = self.find_proposal_dir(proposal_id)
            proposal_path = proposal_dir / "proposal.md"
            proposal_content = self._read_source(proposal_path)
            self._require_source(proposal_path, proposal_content)
            proposal_text = (proposal_content or b"").decode("utf-8")
            proposal_inputs.append(
                SoftwareSpecProposalInput(
                    proposal_id=proposal_id,
                    title=_proposal_title(proposal_id, proposal_text),
                    proposal=(
                        read_markdown_section(proposal_text, "Proposal")
                        or "Not provided."
                    ),
                )
            )
            source_records.append(
                self._source_record(proposal_path, proposal_content)
            )
            generated_from.append(str(proposal_path.relative_to(self.root)))
            if self.proposal_lifecycle_status is not None:
                lifecycle = self.proposal_lifecycle_status(proposal_id)
                decision_bindings.append(
                    {
                        "proposal": proposal_id,
                        "effective_state": lifecycle.effective_state.value,
                        "head_event_id": lifecycle.head_event_id,
                        "decision_semantic_sha256": (
                            lifecycle.decision_semantic_sha256
                        ),
                        "proposal_binding_status": (
                            lifecycle.proposal_binding_status.value
                        ),
                    }
                )
                ledger_path = proposal_dir / "decision-events.yml"
                if ledger_path.exists():
                    ledger_content = self._read_source(ledger_path)
                    self._require_source(ledger_path, ledger_content)
                    source_records.append(
                        self._source_record(ledger_path, ledger_content)
                    )
                    generated_from.append(
                        str(ledger_path.relative_to(self.root))
                    )

        tasks_data = _mapping_from_bytes(tasks_content, default={"tasks": []})
        tasks = tasks_data.get("tasks", [])
        task_list = tasks if isinstance(tasks, list) else []
        non_provenance = {
            "index.md": self._index_markdown(
                change_id=change_id,
                title=title,
                change_path=change_dir.relative_to(self.root),
                summary=read_markdown_section(change_text, "Summary") or "Not specified yet.",
                frontmatter=frontmatter,
                included_proposals=included_proposals,
            ),
            "requirements.md": self._requirements_markdown(
                proposal_inputs,
                change_text,
            ),
            "design.md": self._design_markdown(frontmatter, change_text),
            "commands.yml": _yaml_dump({"commands": self._commands(task_list)}),
            "data-model.yml": _yaml_dump(
                {"entities": self._entities(frontmatter, proposal_inputs)}
            ),
            "acceptance.md": self._acceptance_markdown(change_text, task_list),
        }
        ordered_sources = tuple(sorted(source_records, key=lambda item: item.path))
        source_fingerprint = self._source_fingerprint(
            change_id=change_id,
            sources=ordered_sources,
        )
        provenance = {
            "source": {
                "change": change_id,
                "included_proposals": included_proposals,
                "accepted_decisions": source.get("accepted_decisions", []),
                "decision_bindings": decision_bindings,
            },
            "generated_from": generated_from,
            "p2p_generation": {
                "schema_version": SOFTWARE_SPEC_PROVENANCE_SCHEMA_VERSION,
                "origin": SoftwareSpecOrigin.GENERATED.value,
                "generator": SOFTWARE_SPEC_GENERATOR,
                "renderer_version": SOFTWARE_SPEC_RENDERER_VERSION,
                "source_fingerprint": {
                    "algorithm": "sha256",
                    "value": source_fingerprint,
                },
                "sources": [item.payload() for item in ordered_sources],
                "outputs": [
                    {
                        "path": filename,
                        "sha256": _physical_sha256(
                            non_provenance[filename].encode("utf-8")
                        ),
                    }
                    for filename in SOFTWARE_SPEC_NON_PROVENANCE_FILES
                ],
            },
        }
        files = {
            **non_provenance,
            "provenance.yml": _yaml_dump(provenance),
        }
        return SoftwareSpecCandidate(
            change_id=change_id,
            title=title,
            files=tuple((filename, files[filename]) for filename in self.required_files()),
            sources=ordered_sources,
            source_fingerprint_sha256=source_fingerprint,
        )

    def statuses(self) -> list[SoftwareSpecStatus]:
        specs_dir = self.p2p_dir / "outputs" / "software-spec"
        statuses: list[SoftwareSpecStatus] = []
        for path in sorted(specs_dir.iterdir()) if specs_dir.exists() else []:
            if not path.is_dir():
                continue
            change_id = path.name
            title = change_id
            try:
                title = self.show_change_set(change_id).title
            except ValueError:
                index_title = read_title(_read_optional(path / "index.md"))
                title = index_title or change_id
            statuses.append(self._status(path, change_id=change_id, title=title))
        return statuses

    def show(self, change_id: str) -> str:
        path = self.p2p_dir / "outputs" / "software-spec" / change_id / "index.md"
        if not path.exists():
            raise ValueError("Software spec not found. Run `p2p spec refresh --change CHANGE-XXX` first.")
        return path.read_text(encoding="utf-8")

    def create_prompt(self, change_id: str) -> SoftwareSpecPrompt:
        self.refresh(change_id)
        spec_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        change = self.show_change_set(change_id)
        prompt_path = spec_dir / "spec-refine.prompt.md"
        context = "\n\n".join(
            [
                _read_optional(spec_dir / "index.md"),
                _read_optional(spec_dir / "requirements.md"),
                _read_optional(spec_dir / "design.md"),
                _read_optional(spec_dir / "acceptance.md"),
            ]
        )
        prompt_path.write_text(self._refine_prompt(change, context), encoding="utf-8")
        return SoftwareSpecPrompt(change_id=change_id, prompt_path=prompt_path.relative_to(self.root))

    def import_spec(self, change_id: str, source: Path) -> list[Path]:
        source = source.resolve()
        if not source.is_dir():
            raise ValueError(f"Software spec source directory not found: {source}")
        files: dict[str, str] = {}
        for filename in self.required_files():
            path = source / filename
            if not path.exists():
                raise ValueError(f"Missing required software spec artifact: {filename}")
            files[filename] = path.read_bytes().decode("utf-8")
        validate_yaml_key(files["commands.yml"], "commands")
        validate_yaml_key(files["data-model.yml"], "entities")
        validate_yaml_key(files["provenance.yml"], "source")
        provenance = load_yaml(files["provenance.yml"])
        if not isinstance(provenance, dict):
            raise ValueError("Invalid provenance.yml: expected a mapping.")
        if "p2p_generation" in provenance:
            raise ValueError(
                "Imported provenance must not define reserved `p2p_generation` metadata."
            )
        provenance["p2p_generation"] = {
            "schema_version": SOFTWARE_SPEC_PROVENANCE_SCHEMA_VERSION,
            "origin": SoftwareSpecOrigin.IMPORTED.value,
            "generator": f"{SOFTWARE_SPEC_GENERATOR}.import",
        }
        files["provenance.yml"] = _yaml_dump(provenance)

        target_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        self._commit_required_files(
            operation_id=f"software-spec-import:{change_id}",
            spec_dir=target_dir,
            files=files,
            dependency_sources=(),
            actor="import",
        )
        return [
            (target_dir / filename).relative_to(self.root)
            for filename in self.required_files()
        ]

    def _status(
        self,
        spec_dir: Path,
        *,
        change_id: str,
        title: str,
    ) -> SoftwareSpecStatus:
        relative = spec_dir.relative_to(self.root)
        missing = tuple(
            filename
            for filename in self.required_files()
            if not (spec_dir / filename).is_file()
        )
        if missing:
            return SoftwareSpecStatus(
                change_id=change_id,
                title=title,
                status="incomplete",
                path=relative,
                freshness=SoftwareSpecFreshness.INCOMPLETE,
                reasons=("missing_required_files:" + ",".join(missing),),
                suggested_command=f"p2p spec refresh --change {change_id}",
            )
        try:
            provenance = load_yaml((spec_dir / "provenance.yml").read_bytes())
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            return self._invalid_status(
                change_id,
                title,
                relative,
                "invalid_provenance",
            )
        if not isinstance(provenance, dict):
            return self._invalid_status(
                change_id,
                title,
                relative,
                "invalid_provenance",
            )
        generation = provenance.get("p2p_generation")
        if generation is None:
            return self._invalid_status(
            change_id=change_id,
            title=title,
            relative=relative,
            reason="missing_generation_provenance",
        )
        return self._current_provenance_status(
            spec_dir,
            change_id=change_id,
            title=title,
            provenance=generation,
        )

    def _current_provenance_status(
        self,
        spec_dir: Path,
        *,
        change_id: str,
        title: str,
        provenance: object,
    ) -> SoftwareSpecStatus:
        relative = spec_dir.relative_to(self.root)
        if not isinstance(provenance, Mapping):
            return self._invalid_status(
                change_id,
                title,
                relative,
                "invalid_generation_provenance",
            )
        schema_version = _safe_int(provenance.get("schema_version"))
        if schema_version != SOFTWARE_SPEC_PROVENANCE_SCHEMA_VERSION:
            return self._invalid_status(
                change_id,
                title,
                relative,
                "unsupported_generation_provenance",
            )
        origin = str(provenance.get("origin") or "")
        if origin == SoftwareSpecOrigin.IMPORTED.value:
            return SoftwareSpecStatus(
                change_id=change_id,
                title=title,
                status="generated",
                path=relative,
                freshness=SoftwareSpecFreshness.CURRENT_IMPORTED,
                origin=SoftwareSpecOrigin.IMPORTED,
                reasons=("current_imported_provenance",),
            )
        if origin != SoftwareSpecOrigin.GENERATED.value:
            return self._invalid_status(
                change_id,
                title,
                relative,
                "unsupported_artifact_origin",
            )
        try:
            candidate = self.build_candidate(change_id)
        except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError):
            return self._invalid_status(
                change_id,
                title,
                relative,
                "authoritative_source_unavailable",
                origin=SoftwareSpecOrigin.GENERATED,
            )
        fingerprint = provenance.get("source_fingerprint")
        if (
            not isinstance(fingerprint, Mapping)
            or str(fingerprint.get("algorithm") or "") != "sha256"
            or not str(fingerprint.get("value") or "")
        ):
            return self._invalid_status(
                change_id,
                title,
                relative,
                "invalid_source_fingerprint",
                origin=SoftwareSpecOrigin.GENERATED,
            )
        recorded = str(fingerprint.get("value") or "")
        current = candidate.source_fingerprint_sha256
        if recorded != current:
            reasons = ["source_fingerprint_changed"]
            if _safe_int(provenance.get("renderer_version")) != SOFTWARE_SPEC_RENDERER_VERSION:
                reasons.append("renderer_contract_changed")
            return SoftwareSpecStatus(
                change_id=change_id,
                title=title,
                status="generated",
                path=relative,
                freshness=SoftwareSpecFreshness.STALE,
                origin=SoftwareSpecOrigin.GENERATED,
                current_source_fingerprint_sha256=current,
                recorded_source_fingerprint_sha256=recorded,
                changed_sources=self._changed_sources(
                    provenance.get("sources"),
                    candidate.sources,
                ),
                reasons=tuple(reasons),
                suggested_command=f"p2p spec refresh --change {change_id}",
            )
        changed_outputs = self._changed_outputs(spec_dir, candidate.file_map())
        if changed_outputs:
            return SoftwareSpecStatus(
                change_id=change_id,
                title=title,
                status="generated",
                path=relative,
                freshness=SoftwareSpecFreshness.MODIFIED,
                origin=SoftwareSpecOrigin.GENERATED,
                current_source_fingerprint_sha256=current,
                recorded_source_fingerprint_sha256=recorded,
                changed_outputs=changed_outputs,
                reasons=("generated_output_changed",),
                suggested_command=f"p2p spec refresh --change {change_id}",
            )
        return SoftwareSpecStatus(
            change_id=change_id,
            title=title,
            status="generated",
            path=relative,
            freshness=SoftwareSpecFreshness.CURRENT,
            origin=SoftwareSpecOrigin.GENERATED,
            current_source_fingerprint_sha256=current,
            recorded_source_fingerprint_sha256=recorded,
            reasons=(
                "source_fingerprint_matches",
                "generated_outputs_match_candidate",
            ),
        )

    def _invalid_status(
        self,
        change_id: str,
        title: str,
        relative: Path,
        reason: str,
        *,
        origin: SoftwareSpecOrigin = SoftwareSpecOrigin.INVALID,
        current_fingerprint: str = "",
    ) -> SoftwareSpecStatus:
        return SoftwareSpecStatus(
            change_id=change_id,
            title=title,
            status="generated",
            path=relative,
            freshness=SoftwareSpecFreshness.INVALID,
            origin=origin,
            current_source_fingerprint_sha256=current_fingerprint,
            reasons=(reason,),
            suggested_command=f"p2p spec refresh --change {change_id}",
        )

    def _commit_required_files(
        self,
        *,
        operation_id: str,
        spec_dir: Path,
        files: Mapping[str, str],
        dependency_sources: tuple[SoftwareSpecSourceRecord, ...],
        actor: str,
    ) -> None:
        targets = {
            (spec_dir / filename).relative_to(self.root).as_posix():
            files[filename].encode("utf-8")
            for filename in self.required_files()
        }
        unchanged = all(
            (self.root / relative).is_file()
            and (self.root / relative).read_bytes() == content
            for relative, content in targets.items()
        )
        if unchanged and dependency_sources and not self._sources_still_match(
            dependency_sources
        ):
            raise ValueError("software_spec_source_changed_before_commit")
        if unchanged:
            return
        source_map = {item.path: item.precondition() for item in dependency_sources}
        for relative in targets:
            path = self.root / relative
            content = path.read_bytes() if path.is_file() else None
            source_map[relative] = SourcePrecondition(
                path=relative,
                exists=content is not None,
                physical_sha256=(
                    _physical_sha256(content) if content is not None else None
                ),
            )
        sources = tuple(source_map[path] for path in sorted(source_map))
        token = MutationPreviewService.token(
            operation_id=operation_id,
            targets=tuple(targets),
            sources=sources,
            candidate_semantics={
                relative: _physical_sha256(content)
                for relative, content in targets.items()
            },
        )
        result = self.atomic_writer.apply(
            operation_id=operation_id,
            candidates=targets,
            sources=sources,
            preview_token=token,
            actor=actor,
        )
        if result.status != "applied":
            raise ValueError(
                result.message
                or f"Software spec mutation failed: {result.status}"
            )

    def _read_source(self, path: Path) -> bytes | None:
        try:
            return self.source_reader(path)
        except FileNotFoundError:
            return None

    def _source_record(
        self,
        path: Path,
        content: bytes | None,
    ) -> SoftwareSpecSourceRecord:
        return SoftwareSpecSourceRecord(
            path=path.relative_to(self.root).as_posix(),
            exists=content is not None,
            sha256=_physical_sha256(content) if content is not None else "",
        )

    def _require_source(self, path: Path, content: bytes | None) -> None:
        if content is None:
            relative = path.relative_to(self.root).as_posix()
            raise ValueError(f"software_spec_source_missing:{relative}")

    def _source_fingerprint(
        self,
        *,
        change_id: str,
        sources: tuple[SoftwareSpecSourceRecord, ...],
    ) -> str:
        from p2p_engine.core.mutation_preview import semantic_sha256

        return semantic_sha256(
            {
                "contract_version": SOFTWARE_SPEC_PROVENANCE_SCHEMA_VERSION,
                "renderer_version": SOFTWARE_SPEC_RENDERER_VERSION,
                "change_id": change_id,
                "sources": [item.payload() for item in sources],
            }
        )

    def _sources_still_match(
        self,
        sources: tuple[SoftwareSpecSourceRecord, ...],
    ) -> bool:
        for source in sources:
            path = self.root / source.path
            if path.is_file() != source.exists:
                return False
            if source.exists and _physical_sha256(path.read_bytes()) != source.sha256:
                return False
        return True

    def _changed_sources(
        self,
        recorded: object,
        current: tuple[SoftwareSpecSourceRecord, ...],
    ) -> tuple[str, ...]:
        recorded_map = {
            str(item.get("path") or ""): (
                bool(item.get("exists", True)),
                str(item.get("sha256") or ""),
            )
            for item in recorded
            if isinstance(item, Mapping) and str(item.get("path") or "")
        } if isinstance(recorded, list) else {}
        current_map = {
            item.path: (item.exists, item.sha256)
            for item in current
        }
        return tuple(
            path
            for path in sorted(set(recorded_map) | set(current_map))
            if recorded_map.get(path) != current_map.get(path)
        )

    def _changed_outputs(
        self,
        spec_dir: Path,
        candidate: Mapping[str, str],
    ) -> tuple[str, ...]:
        return tuple(
            filename
            for filename in self.required_files()
            if (spec_dir / filename).read_bytes()
            != candidate[filename].encode("utf-8")
        )

    def _index_markdown(
        self,
        *,
        change_id: str,
        title: str,
        change_path: Path,
        summary: str,
        frontmatter: dict[str, object],
        included_proposals: list[str],
    ) -> str:
        return (
            f"# Software Spec - {change_id} - {title}\n\n"
            "## Summary\n\n"
            f"{summary}\n\n"
            "## Source\n\n"
            f"- Change Set: `{change_id}`\n"
            f"- Change path: `{change_path}`\n"
            f"- Included proposals: {', '.join(included_proposals) if included_proposals else 'none'}\n\n"
            "## Targets\n\n"
            f"- execution_domains: {', '.join(_string_list(frontmatter.get('execution_domains'))) or 'none'}\n"
            f"- implementation_targets: {', '.join(_string_list(frontmatter.get('implementation_targets'))) or 'none'}\n"
            f"- spec_targets: {', '.join(_string_list(frontmatter.get('spec_targets'))) or 'none'}\n"
            f"- export_targets: {', '.join(_string_list(frontmatter.get('export_targets'))) or 'none'}\n"
        )

    def _requirements_markdown(self, proposals: list[Any], change_text: str) -> str:
        lines = ["# Requirements", "", "## Functional Requirements", ""]
        if proposals:
            for proposal in proposals:
                lines.extend([f"### {proposal.proposal_id} - {proposal.title}", "", proposal.proposal, ""])
        else:
            lines.extend(["Not specified yet.", ""])
        lines.extend(
            [
                "## Non-Goals / Exclusions",
                "",
                read_markdown_section(change_text, "Excluded") or "Not specified yet.",
                "",
                "## Constraints",
                "",
                "Do not treat raw proposal discussion as implementation requirements without accepted scope.",
                "",
                "## Open Questions",
                "",
                "Not specified yet.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _design_markdown(self, frontmatter: dict[str, object], change_text: str) -> str:
        return (
            "# Design\n\n"
            "## Implementation Targets\n\n"
            f"{', '.join(_string_list(frontmatter.get('implementation_targets'))) or 'Not specified yet.'}\n\n"
            "## Data Flow\n\n"
            "Not specified yet.\n\n"
            "## CLI/API Surface\n\n"
            "Not specified yet.\n\n"
            "## Storage / Artifacts\n\n"
            f"{read_markdown_section(change_text, 'Deliverables') or 'Not specified yet.'}\n"
        )

    def _commands(self, tasks: list[object]) -> list[dict[str, object]]:
        commands: list[dict[str, object]] = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            title = str(task.get("title") or "")
            if "command" in title.lower() or task.get("domain") == "software":
                commands.append(
                    {
                        "name": title,
                        "purpose": str(task.get("deliverable") or task.get("description") or "Not specified yet."),
                        "status": str(task.get("status") or "unknown"),
                    }
                )
        return commands

    def _entities(self, frontmatter: dict[str, object], proposals: list[Any]) -> list[dict[str, object]]:
        entities = [
            {"name": "ChangeSet", "description": "Operational package derived from accepted project intent."},
            {"name": "SoftwareSpec", "description": "P2P-native normalized implementation-facing specification."},
        ]
        for target in _string_list(frontmatter.get("export_targets")):
            entities.append({"name": f"ExportTarget:{target}", "description": "Downstream export target."})
        for proposal in proposals:
            entities.append({"name": proposal.proposal_id, "description": proposal.title})
        return entities

    def _acceptance_markdown(self, change_text: str, tasks: list[object]) -> str:
        lines = [
            "# Acceptance",
            "",
            "## Criteria",
            "",
            read_markdown_section(change_text, "Acceptance Criteria") or "Not specified yet.",
            "",
            "## Tests / Verification",
            "",
        ]
        task_lines = []
        for task in tasks:
            if isinstance(task, dict):
                task_lines.append(f"- {task.get('id', '-')}: {task.get('title', 'Untitled')} ({task.get('status', 'unknown')})")
        lines.extend(task_lines or ["- Not specified yet."])
        lines.append("")
        return "\n".join(lines)

    def _refine_prompt(self, change: Any, context: str) -> str:
        return (
            f"# P2P Software Spec Refinement Prompt - {change.change_id}\n\n"
            "You are refining a P2P-native software specification for implementation and downstream export.\n\n"
            "## Governance Boundary\n\n"
            "Do not add requirements that are not supported by accepted proposals, decisions, or the Change Set. "
            "Mark missing information as open questions instead of inventing it.\n\n"
            "## Required Output\n\n"
            "Return a directory containing exactly these artifacts:\n\n"
            "- index.md\n"
            "- requirements.md\n"
            "- design.md\n"
            "- commands.yml with top-level `commands`\n"
            "- data-model.yml with top-level `entities`\n"
            "- acceptance.md\n"
            "- provenance.yml with top-level `source`\n\n"
            "## Current Deterministic Spec Context\n\n"
            f"{context}\n"
        )

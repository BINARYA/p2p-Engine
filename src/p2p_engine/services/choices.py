from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from p2p_engine.core.authority import AuthorityContext, AuthorityEvidence
from p2p_engine.core.choice_reads import (
    CHOICE_READ_DEFAULT_LIMIT,
    ChoiceDefinitionRead,
    ChoiceDetailRead,
    ChoiceIntegrityRead,
    ChoiceLifecycleRead,
    ChoiceListRead,
    ChoiceOptionRead,
    ChoicePageMetadata,
    ChoiceRelationPageRead,
    ChoiceRelationRead,
    ChoiceSelectionRead,
    ChoiceSummaryRead,
    validate_choice_read_page,
)
from p2p_engine.core.choices import (
    CHOICE_DEFINITION_CONTRACT,
    CHOICE_LIFECYCLE_CONTRACT,
    CHOICE_TRANSITION_PREVIEW_CONTRACT,
    CHOICE_TRANSITION_RESULT_CONTRACT,
    DEFAULT_GOVERNANCE_BOUNDARY,
    ChoiceDefinition,
    ChoiceOptionDefinition,
    ChoiceState,
    ChoiceTerminalEvent,
    ChoiceTransitionKind,
    is_active_choice_state,
    is_terminal_choice_state,
    normalize_choice_state,
    normalize_definition_text,
    require_transition_allowed,
    transition_target,
    validate_supersession_graph,
)
from p2p_engine.core.mutation_preview import (
    MutationPreview,
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.foundation.files import slugify as _foundation_slugify
from p2p_engine.foundation.files import yaml_dump as _yaml_dump
from p2p_engine.foundation.markdown import (
    read_frontmatter,
    read_markdown_section,
    read_title,
    replace_frontmatter,
)
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.authority import ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter

CHOICE_TRANSITION_CAPABILITY = "choice.lifecycle.transition"
CHOICE_TRANSITION_POLICY_VERSION = 1


@dataclass(frozen=True)
class ChoiceStatus:
    choice_id: str
    title: str
    status: str
    path: Path
    selected_option: str | None
    terminal: bool = False
    seal_status: str = "unknown"
    integrity_status: str = "unknown"
    definition_digest: str | None = None
    replacement_choice_id: str | None = None


@dataclass(frozen=True)
class ChoiceDetail:
    choice_id: str
    title: str
    status: str
    path: Path
    selected_option: str | None
    options: list[dict[str, object]]
    related_proposals: list[dict[str, object]]
    related_changes: list[dict[str, object]]
    blocks: list[dict[str, object]]
    terminal: bool = False
    seal_status: str = "unknown"
    integrity_status: str = "unknown"
    definition_digest: str | None = None
    terminal_event: dict[str, object] | None = None
    replacement_choice_id: str | None = None
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChoiceListReadBundle:
    semantic: ChoiceListRead
    compatibility: tuple[ChoiceStatus, ...]


@dataclass(frozen=True)
class ChoiceDetailReadBundle:
    semantic: ChoiceDetailRead
    compatibility: ChoiceDetail


@dataclass(frozen=True)
class ChoiceDiscoveryFinding:
    finding_id: str
    kind: str
    target: str
    severity: str
    reason: str
    suggested_command: str


@dataclass(frozen=True)
class ChoiceTransitionPlan:
    choice_id: str
    transition: str
    target_state: str
    definition_digest: str | None
    selected_option: str | None
    replacement_choice_id: str | None
    blockers_cleared: int
    preview: MutationPreview
    candidates: Mapping[str, bytes] = field(repr=False)
    authority: AuthorityEvidence = field(repr=False)
    request_fingerprint_sha256: str = field(repr=False)
    replay_request_sha256: str = field(repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": CHOICE_TRANSITION_PREVIEW_CONTRACT,
            "choice_id": self.choice_id,
            "transition": self.transition,
            "target_state": self.target_state,
            "definition_digest": self.definition_digest,
            "selected_option": self.selected_option,
            "replacement_choice_id": self.replacement_choice_id,
            "blockers_cleared": self.blockers_cleared,
            "mutation": self.preview.to_dict(),
            "authority": self.authority.to_dict(),
        }


@dataclass(frozen=True)
class ChoiceTransitionResult:
    status: str
    choice: ChoiceStatus
    transition: str
    mutation: MutationResult | None = None
    replayed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": CHOICE_TRANSITION_RESULT_CONTRACT,
            "status": self.status,
            "transition": self.transition,
            "choice": {
                "choice_id": self.choice.choice_id,
                "title": self.choice.title,
                "state": self.choice.status,
                "terminal": self.choice.terminal,
                "selected_option": self.choice.selected_option,
                "replacement_choice_id": self.choice.replacement_choice_id,
                "definition_digest": self.choice.definition_digest,
                "seal_status": self.choice.seal_status,
                "integrity_status": self.choice.integrity_status,
                "path": self.choice.path.as_posix(),
            },
            "mutation": self.mutation.to_dict() if self.mutation is not None else None,
            "replayed": self.replayed,
        }


@dataclass(frozen=True)
class _LoadedChoice:
    choice_dir: Path
    definition: ChoiceDefinition | None
    status: ChoiceState
    seal_status: str
    integrity_status: str
    stored_digest: str | None
    selected_option_id: str | None
    terminal_event: dict[str, object] | None
    replacement_choice_id: str | None
    choice_text: str
    options_payload: dict[str, object]
    decision_text: str
    links_payload: dict[str, object]
    lifecycle_bytes: bytes | None


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


class ChoiceLifecycleService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
        find_change_dir: Callable[[str], Path],
        choice_registry_records: Callable[[], list[dict[str, object]]],
        governance_preflight: Callable[..., object] | None = None,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.find_proposal_dir = find_proposal_dir
        self.find_change_dir = find_change_dir
        self.choice_registry_records = choice_registry_records
        self.governance_preflight = governance_preflight
        self.authority = authority or ProjectAuthorityService(root=self.root, p2p_dir=self.p2p_dir)
        self.receipts = receipts or MutationReceiptService(root=self.root, p2p_dir=self.p2p_dir)
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)

    def create(
        self,
        title: str,
        options: list[str],
        related: list[str] | None = None,
        source: str | None = None,
        *,
        problem: str,
        context: str,
        governance_boundary: str = DEFAULT_GOVERNANCE_BOUNDARY,
    ) -> ChoiceStatus:
        related = related or []
        for proposal_id in related:
            if not proposal_id.startswith("PROP-"):
                raise ValueError(f"P2P_CHOICE_RELATION_INVALID: unsupported related target `{proposal_id}`")
            self.find_proposal_dir(proposal_id)
        choice_id = self._next_id()
        definition = ChoiceDefinition.build(
            choice_id=choice_id,
            title=title,
            problem=problem,
            context=context,
            governance_boundary=governance_boundary,
            option_titles=options,
        )
        choice_dir = self.p2p_dir / "choices" / f"{choice_id}-{_foundation_slugify(definition.title, fallback='item')}"
        today = date.today().isoformat()
        frontmatter = _yaml_dump(
            {
                "choice_id": choice_id,
                "title": definition.title,
                "status": ChoiceState.open.value,
                "created_at": today,
                "created_by": "local",
                "source": {"intake": source} if source else {},
                "related": {"proposals": related},
            }
        )
        artifacts = {
            choice_dir / "choice.md": (
                f"---\n{frontmatter}---\n\n# {choice_id} - {definition.title}\n\n"
                f"## Problem\n\n{definition.problem}\n\n"
                f"## Context\n\n{definition.context}\n\n"
                f"## Governance Boundary\n\n{definition.governance_boundary}\n"
            ).encode("utf-8"),
            choice_dir / "options.yml": _yaml_dump(
                {"options": [item.to_dict() for item in definition.options]}
            ).encode("utf-8"),
            choice_dir / "decision.md": self._decision_bytes(choice_id, ChoiceState.open, None, None),
            choice_dir / "links.yml": _yaml_dump(
                {
                    "source": {"intake": source} if source else {},
                    "related_proposals": [
                        {"proposal": item, "relationship": "references", "rationale": ""}
                        for item in related
                    ],
                    "related_changes": [],
                    "blocks": [],
                }
            ).encode("utf-8"),
            choice_dir / "lifecycle.yml": self._lifecycle_bytes(
                choice_id, definition.digest, "complete", ChoiceState.open, None
            ),
        }
        candidates = {_relative(self.root, path): content for path, content in artifacts.items()}
        result = self.atomic_writer.apply(
            operation_id="choice_create",
            candidates=candidates,
            sources=tuple(source_precondition(path, None) for path in sorted(candidates)),
            preview_token=semantic_sha256({"operation": "choice_create", "definition": definition.to_dict()}),
            actor="local",
        )
        if result.status != "applied":
            raise ValueError(f"P2P_CHOICE_CREATE_FAILED: {result.message}")
        return self._status(self._load(choice_id))

    def statuses(self) -> list[ChoiceStatus]:
        return [self._status(self._load_dir(path)) for path in self._choice_dirs()]

    def list_read_bundle(
        self,
        *,
        limit: int = CHOICE_READ_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> ChoiceListReadBundle:
        validate_choice_read_page(limit=limit, offset=offset)
        loaded = [self._load_dir(path) for path in self._choice_dirs()]
        loaded.sort(key=self._choice_id)
        selected = loaded[offset : offset + limit + 1]
        has_more = len(selected) > limit
        page_items = selected[:limit]
        compatibility = tuple(self._status(item) for item in page_items)
        semantic = ChoiceListRead(
            items=tuple(self._summary_read(item) for item in page_items),
            page=ChoicePageMetadata.build(
                limit=limit,
                offset=offset,
                returned=len(page_items),
                has_more=has_more,
            ),
        )
        return ChoiceListReadBundle(semantic=semantic, compatibility=compatibility)

    def list_read(
        self,
        *,
        limit: int = CHOICE_READ_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> ChoiceListRead:
        return self.list_read_bundle(limit=limit, offset=offset).semantic

    def show(self, choice_id: str) -> ChoiceDetail:
        return self._detail(self._load(choice_id))

    def detail_read_bundle(
        self,
        choice_id: str,
        *,
        limit: int = CHOICE_READ_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> ChoiceDetailReadBundle:
        validate_choice_read_page(limit=limit, offset=offset)
        loaded = self._load(choice_id)
        compatibility = self._detail(loaded)
        relations = self._relations_read(loaded, supersedes=compatibility.supersedes)
        selected = relations[offset : offset + limit + 1]
        has_more = len(selected) > limit
        page_items = selected[:limit]
        definition = loaded.definition
        frontmatter = read_frontmatter(loaded.choice_text)
        normalized_choice_id = self._choice_id(loaded)
        options = (
            tuple(
                ChoiceOptionRead(option.option_id, option.title)
                for option in definition.options
            )
            if definition is not None
            else tuple(
                ChoiceOptionRead(str(item.get("id") or ""), str(item.get("title") or ""))
                for item in self._definition_options(loaded.options_payload, strict=False)
                if str(item.get("id") or "") and str(item.get("title") or "")
            )
        )
        selection = self._selection_read(loaded)
        semantic = ChoiceDetailRead(
            choice_id=normalized_choice_id,
            definition=ChoiceDefinitionRead(
                source_contract=(
                    CHOICE_DEFINITION_CONTRACT if loaded.seal_status == "sealed" else "legacy"
                ),
                completeness="complete" if definition is not None else "incomplete",
                digest=loaded.stored_digest,
                choice_id=normalized_choice_id,
                title=str(
                    frontmatter.get("title")
                    or read_title(loaded.choice_text)
                    or normalized_choice_id
                ),
                problem=definition.problem if definition is not None else None,
                context=definition.context if definition is not None else None,
                governance_boundary=(
                    definition.governance_boundary if definition is not None else None
                ),
                options=options,
            ),
            lifecycle=ChoiceLifecycleRead(
                source_contract=(
                    CHOICE_LIFECYCLE_CONTRACT if loaded.lifecycle_bytes is not None else "legacy"
                ),
                state=loaded.status.value,
                terminal=is_terminal_choice_state(loaded.status),
                selected_option=selection,
                terminal_event=loaded.terminal_event,
                replacement_choice_id=loaded.replacement_choice_id,
            ),
            integrity=ChoiceIntegrityRead(
                seal_status=loaded.seal_status,
                integrity_status=loaded.integrity_status,
            ),
            relations=ChoiceRelationPageRead(
                items=tuple(page_items),
                page=ChoicePageMetadata.build(
                    limit=limit,
                    offset=offset,
                    returned=len(page_items),
                    has_more=has_more,
                ),
            ),
        )
        return ChoiceDetailReadBundle(semantic=semantic, compatibility=compatibility)

    def detail_read(
        self,
        choice_id: str,
        *,
        limit: int = CHOICE_READ_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> ChoiceDetailRead:
        return self.detail_read_bundle(choice_id, limit=limit, offset=offset).semantic

    def _detail(self, loaded: _LoadedChoice) -> ChoiceDetail:
        definition = loaded.definition
        frontmatter = read_frontmatter(loaded.choice_text)
        choice_id = self._choice_id(loaded)
        supersedes = tuple(
            self._choice_id(item)
            for item in (self._load_dir(path) for path in self._choice_dirs())
            if item.replacement_choice_id == choice_id
        )
        return ChoiceDetail(
            choice_id=str(frontmatter.get("choice_id") or choice_id),
            title=str(frontmatter.get("title") or read_title(loaded.choice_text) or choice_id),
            status=loaded.status.value,
            path=loaded.choice_dir.relative_to(self.root),
            selected_option=self._selected_display(loaded),
            options=(
                [item.to_dict() for item in definition.options]
                if definition is not None
                else self._definition_options(loaded.options_payload, strict=False)
            ),
            related_proposals=self._mapping_list(loaded.links_payload, "related_proposals"),
            related_changes=self._mapping_list(loaded.links_payload, "related_changes"),
            blocks=self._mapping_list(loaded.links_payload, "blocks"),
            terminal=is_terminal_choice_state(loaded.status),
            seal_status=loaded.seal_status,
            integrity_status=loaded.integrity_status,
            definition_digest=loaded.stored_digest,
            terminal_event=loaded.terminal_event,
            replacement_choice_id=loaded.replacement_choice_id,
            supersedes=supersedes,
        )

    def _summary_read(self, loaded: _LoadedChoice) -> ChoiceSummaryRead:
        status = self._status(loaded)
        return ChoiceSummaryRead(
            choice_id=status.choice_id,
            title=status.title,
            state=status.status,
            terminal=status.terminal,
            definition_contract=(
                CHOICE_DEFINITION_CONTRACT if loaded.seal_status == "sealed" else "legacy"
            ),
            definition_completeness=(
                "complete" if loaded.definition is not None else "incomplete"
            ),
            definition_digest=status.definition_digest,
            seal_status=status.seal_status,
            integrity_status=status.integrity_status,
            selected_option=self._selection_read(loaded),
            replacement_choice_id=status.replacement_choice_id,
        )

    def _selection_read(self, loaded: _LoadedChoice) -> ChoiceSelectionRead | None:
        option_id = loaded.selected_option_id
        if option_id is None:
            return None
        if loaded.definition is not None:
            option = loaded.definition.option(option_id)
            return ChoiceSelectionRead(option.option_id, option.title)
        selected = read_markdown_section(loaded.decision_text, "Selected Option") or ""
        prefix, separator, title = selected.partition(" - ")
        return ChoiceSelectionRead(
            option_id=prefix.strip().upper() or option_id,
            title=title.strip() if separator and title.strip() else None,
        )

    def _relations_read(
        self,
        loaded: _LoadedChoice,
        *,
        supersedes: tuple[str, ...],
    ) -> list[ChoiceRelationRead]:
        relations: list[ChoiceRelationRead] = []
        for item in self._mapping_list(loaded.links_payload, "related_proposals"):
            target = str(item.get("proposal") or item.get("target") or "").strip()
            if target:
                relations.append(
                    self._relation_read(
                        "related_proposal", "proposal", target, item
                    )
                )
        for item in self._mapping_list(loaded.links_payload, "related_changes"):
            target = str(item.get("change") or item.get("target") or "").strip()
            if target:
                relations.append(
                    self._relation_read("related_change", "change", target, item)
                )
        for item in self._mapping_list(loaded.links_payload, "blocks"):
            target = str(item.get("target") or "").strip()
            if target:
                relations.append(
                    self._relation_read(
                        "blocks",
                        str(item.get("target_type") or "target"),
                        target,
                        item,
                    )
                )
        if loaded.replacement_choice_id:
            relations.append(
                ChoiceRelationRead(
                    kind="superseded_by",
                    target_type="choice",
                    target_id=loaded.replacement_choice_id,
                )
            )
        relations.extend(
            ChoiceRelationRead(
                kind="supersedes",
                target_type="choice",
                target_id=choice_id,
                derived=True,
            )
            for choice_id in supersedes
        )
        relations.sort(
            key=lambda item: (
                item.kind,
                item.target_type,
                item.target_id,
                item.relationship or "",
                item.status or "",
            )
        )
        return relations

    @staticmethod
    def _relation_read(
        kind: str,
        target_type: str,
        target_id: str,
        item: Mapping[str, object],
    ) -> ChoiceRelationRead:
        def optional(name: str) -> str | None:
            value = str(item.get(name) or "").strip()
            return value or None

        return ChoiceRelationRead(
            kind=kind,
            target_type=target_type,
            target_id=target_id,
            relationship=optional("relationship"),
            rationale=optional("rationale"),
            status=optional("status"),
            reason=optional("reason"),
            recorded_on=optional("recorded_on"),
            cleared_on=optional("cleared_on"),
            cleared_by=optional("cleared_by"),
            clearing_reason=optional("clearing_reason"),
        )

    def discover(self) -> list[ChoiceDiscoveryFinding]:
        findings: list[ChoiceDiscoveryFinding] = []
        project_choices = self.statuses()
        project_choice_ids = {choice.choice_id for choice in project_choices}
        for record in self.choice_registry_records():
            choice_id = str(record.get("id") or "")
            status = str(record.get("status") or "unknown")
            if choice_id.startswith("CHOICE-PROP-") and choice_id not in project_choice_ids:
                proposal_id = str(record.get("proposal") or choice_id.removeprefix("CHOICE-"))
                findings.append(
                    ChoiceDiscoveryFinding(
                        finding_id=f"DISCOVERY-{len(findings) + 1:03d}",
                        kind="proposal_local_choice_candidate",
                        target=choice_id,
                        severity="medium" if status in {"open", "draft", "pending"} and not record.get("selected_option") else "low",
                        reason=f"{choice_id} is proposal-local vote metadata for {proposal_id}, not a project choice managed by p2p choice commands.",
                        suggested_command=f"p2p proposal show {proposal_id}",
                    )
                )
        for choice in project_choices:
            if choice.terminal:
                continue
            active_blocks = [item for item in self.show(choice.choice_id).blocks if item.get("status", "active") == "active"]
            findings.append(
                ChoiceDiscoveryFinding(
                    finding_id=f"DISCOVERY-{len(findings) + 1:03d}",
                    kind="active_choice_blocker" if active_blocks else "open_project_choice",
                    target=choice.choice_id,
                    severity="high" if active_blocks else "medium",
                    reason=(
                        f"{choice.choice_id} is open and has active blockers."
                        if active_blocks
                        else f"{choice.choice_id} is a project choice without a terminal outcome."
                    ),
                    suggested_command=f"p2p choice show {choice.choice_id}",
                )
            )
        return findings

    def validation_findings(self) -> list[tuple[str, str, Path, str, str]]:
        findings: list[tuple[str, str, Path, str, str]] = []
        loaded: list[_LoadedChoice] = []
        for path in self._choice_dirs():
            try:
                item = self._load_dir(path)
                loaded.append(item)
            except ValueError as exc:
                findings.append(
                    (
                        "P2P_CHOICE_INVALID",
                        "error",
                        path.relative_to(self.root),
                        str(exc),
                        "p2p choice show CHOICE-XXX",
                    )
                )
                continue
            if is_terminal_choice_state(item.status) and any(
                block.get("status", "active") == "active"
                for block in self._mapping_list(item.links_payload, "blocks")
            ):
                findings.append(
                    (
                        "P2P_CHOICE_TERMINAL_BLOCKER_ACTIVE",
                        "error",
                        item.choice_dir.relative_to(self.root) / "links.yml",
                        "Terminal Choice retains an active blocker.",
                        f"p2p choice unblock {self._choice_id(item)} --proposal PROP-XXX",
                    )
                )

        ids = {self._choice_id(item) for item in loaded}
        edges = {
            self._choice_id(item): item.replacement_choice_id
            for item in loaded
            if item.replacement_choice_id
        }
        for source, replacement in edges.items():
            if replacement not in ids:
                item = next(candidate for candidate in loaded if self._choice_id(candidate) == source)
                findings.append(
                    (
                        "P2P_CHOICE_REPLACEMENT_INVALID",
                        "error",
                        item.choice_dir.relative_to(self.root) / "lifecycle.yml",
                        f"Replacement Choice does not exist: {replacement}",
                        f"p2p choice show {source}",
                    )
                )
        try:
            validate_supersession_graph(edges)  # type: ignore[arg-type]
        except ValueError as exc:
            findings.append(
                (
                    "P2P_CHOICE_REPLACEMENT_CYCLE",
                    "error",
                    Path(".p2p/choices"),
                    str(exc),
                    "p2p choice status",
                )
            )
        return findings

    def block(self, choice_id: str, target: str, target_type: str, reason: str) -> ChoiceDetail:
        loaded = self._load(choice_id)
        if not is_active_choice_state(loaded.status):
            raise ValueError("P2P_CHOICE_TERMINAL: blockers can be added only to open Choices")
        normalize_definition_text(reason, "blocker reason")
        if target_type == "change":
            self.find_change_dir(target)
        elif target_type == "proposal":
            self.find_proposal_dir(target)
        else:
            raise ValueError("target_type must be `change` or `proposal`.")
        links = dict(loaded.links_payload)
        blocks = links.setdefault("blocks", [])
        if not isinstance(blocks, list):
            raise ValueError("Invalid links.yml: expected `blocks` list.")
        current = next(
            (
                item for item in blocks
                if isinstance(item, dict)
                and item.get("target") == target
                and item.get("target_type") == target_type
                and item.get("status", "active") == "active"
            ),
            None,
        )
        if current is None:
            blocks.append({"target": target, "target_type": target_type, "status": "active", "reason": reason, "recorded_on": date.today().isoformat()})
        else:
            current["reason"] = reason
            current["recorded_on"] = date.today().isoformat()
        self._write_links_atomically(loaded, links, "choice_block")
        return self.show(choice_id)

    def unblock(self, choice_id: str, target: str, target_type: str) -> ChoiceDetail:
        loaded = self._load(choice_id)
        links = dict(loaded.links_payload)
        blocks = links.get("blocks", [])
        if not isinstance(blocks, list):
            raise ValueError("Invalid links.yml: expected `blocks` list.")
        changed = False
        for block in blocks:
            if (
                isinstance(block, dict)
                and block.get("target") == target
                and block.get("target_type") == target_type
                and block.get("status", "active") == "active"
            ):
                block["status"] = "inactive"
                block["cleared_on"] = date.today().isoformat()
                block["clearing_reason"] = "explicit_unblock"
                changed = True
        if not changed:
            raise ValueError(f"Active blocker not found for {target_type}: {target}")
        self._write_links_atomically(loaded, links, "choice_unblock")
        return self.show(choice_id)

    def transition_preview(
        self,
        choice_id: str,
        *,
        transition: str,
        reason: str,
        actor_id: str,
        operation_key: str,
        option: str | None = None,
        replacement_choice_id: str | None = None,
        executor_id: str | None = None,
        executor_kind: str = "person",
        effective_on: str | None = None,
        blocker_override: bool = False,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
    ) -> ChoiceTransitionPlan:
        validate_idempotency_key(operation_key)
        try:
            kind = ChoiceTransitionKind(transition)
        except ValueError as exc:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: transition must be decide, withdraw, or supersede") from exc
        reason = normalize_definition_text(reason, "terminal reason")
        loaded = self._load(choice_id)
        require_transition_allowed(loaded.status, kind)
        if kind == ChoiceTransitionKind.decide and loaded.definition is None:
            raise ValueError("P2P_CHOICE_DEFINITION_INCOMPLETE: an incomplete legacy Choice cannot be decided")
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id or actor_id,
            executor_kind=executor_kind,
            required_capabilities=(CHOICE_TRANSITION_CAPABILITY,),
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        selected: ChoiceOptionDefinition | None = None
        if kind == ChoiceTransitionKind.decide:
            assert loaded.definition is not None
            selected = loaded.definition.option(option or "")
        elif option:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: only decide accepts an option")
        replacement: _LoadedChoice | None = None
        if kind == ChoiceTransitionKind.supersede:
            replacement = self._validated_replacement(loaded, replacement_choice_id or "")
        elif replacement_choice_id:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: only supersede accepts a replacement")
        active_blocks = [
            item for item in self._mapping_list(loaded.links_payload, "blocks")
            if item.get("status", "active") == "active"
        ]
        if kind == ChoiceTransitionKind.decide and active_blocks and not blocker_override:
            raise ValueError("P2P_CHOICE_ACTIVE_BLOCKERS: deciding requires --override-blockers when active blockers exist")
        governance_codes: list[str] = []
        governance_warnings: list[str] = []
        if kind == ChoiceTransitionKind.decide and self.governance_preflight is not None:
            preflight = self.governance_preflight(
                choice_id,
                option=selected.option_id if selected else "",
                actor=actor_id,
            )
            errors = list(getattr(preflight, "blocking_errors", ()))
            unhandled = [
                item
                for item in errors
                if not (
                    blocker_override
                    and bool(getattr(item, "overrideable", False))
                    and getattr(item, "code", "") == "P2P_GOV_ACTIVE_BLOCKER"
                )
            ]
            governance_codes = [str(getattr(item, "code", "")) for item in errors]
            governance_warnings = [
                str(getattr(item, "code", ""))
                for item in getattr(preflight, "warnings", ())
            ]
            if unhandled:
                raise ValueError(
                    "P2P_CHOICE_GOVERNANCE_BLOCKED: "
                    + ", ".join(str(getattr(item, "code", "unknown")) for item in unhandled)
                )
        target = transition_target(kind)
        event = ChoiceTerminalEvent(
            kind=target,
            reason=reason,
            effective_on=effective_on or date.today().isoformat(),
            owner_actor=evidence.subject.identity_id,
            executor_actor=evidence.executor.identity_id,
            authority_mode=evidence.mode.value,
            source_channel=channel,
            operation_key_sha256=idempotency_key_sha256(operation_key),
            selected_option_id=selected.option_id if selected else None,
            replacement_choice_id=self._choice_id(replacement) if replacement else None,
            blocker_override=blocker_override,
        )
        candidates = self._terminal_candidates(loaded, event, selected, self._terminal_links(loaded.links_payload, event))
        receipt_path = self.receipts.relative_path(operation_key)
        sources = self._transition_sources(loaded, receipt_path, replacement)
        semantic = {
            "policy_version": CHOICE_TRANSITION_POLICY_VERSION,
            "choice_id": choice_id,
            "definition_digest": loaded.stored_digest or (loaded.definition.digest if loaded.definition else None),
            "transition": kind.value,
            "reason": reason,
            "effective_on": event.effective_on,
            "selected_option_id": selected.option_id if selected else None,
            "replacement_choice_id": self._choice_id(replacement) if replacement else None,
            "blocker_override": blocker_override,
            "blockers_cleared": len(active_blocks),
            "governance_blocking_codes": governance_codes,
            "governance_warning_codes": governance_warnings,
            "authority_context_sha256": context.digest_sha256,
        }
        preview = MutationPreviewService.build(
            operation_id=f"choice_{kind.value}",
            targets=tuple(sorted((*candidates, receipt_path))),
            actor=evidence.executor.identity_id,
            authority="governed_policy",
            sources=sources,
            candidate_semantics={"choice_terminal_transition": semantic},
            semantic_diff={
                "state_before": loaded.status.value,
                "state_after": target.value,
                "selected_option_id": selected.option_id if selected else None,
                "replacement_choice_id": self._choice_id(replacement) if replacement else None,
                "active_blockers_cleared": len(active_blocks),
            },
            token_context={
                "operation_key_sha256": idempotency_key_sha256(operation_key),
                "authority_context_sha256": context.digest_sha256,
            },
            policy_version=CHOICE_TRANSITION_POLICY_VERSION,
        )
        fingerprint = self.receipts.fingerprint(
            operation=preview.operation_id,
            actor=evidence.executor.identity_id,
            preview_token=preview.preview_token,
            semantic_inputs=semantic,
        )
        return ChoiceTransitionPlan(
            choice_id=choice_id,
            transition=kind.value,
            target_state=target.value,
            definition_digest=semantic["definition_digest"],
            selected_option=(f"{selected.option_id} - {selected.title}" if selected else None),
            replacement_choice_id=self._choice_id(replacement) if replacement else None,
            blockers_cleared=len(active_blocks),
            preview=preview,
            candidates=candidates,
            authority=evidence,
            request_fingerprint_sha256=fingerprint,
            replay_request_sha256=self._replay_request_sha256(choice_id, request={
                "transition": kind.value,
                "reason": reason,
                "actor_id": actor_id,
                "executor_id": executor_id or actor_id,
                "executor_kind": executor_kind,
                "operation_key": operation_key,
                "option": option,
                "replacement_choice_id": replacement_choice_id,
                "effective_on": effective_on,
                "blocker_override": blocker_override,
                "channel": channel,
                "authority_context": authority_context,
                "consent_id": consent_id,
                "consent_sha256": consent_sha256,
            }),
        )

    def transition_apply(self, choice_id: str, *, preview_token: str, confirm: bool, **request: object) -> ChoiceTransitionResult:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: pass --confirm to apply the reviewed Choice transition")
        operation_key = str(request.get("operation_key") or "")
        transition = str(request.get("transition") or "")
        validate_idempotency_key(operation_key)
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is not None:
            if receipt.preview_token_sha256 != hashlib.sha256(preview_token.encode()).hexdigest():
                raise ValueError("P2P_IDEMPOTENCY_CONFLICT: idempotency key was already used for a different preview")
            if receipt.result.get("choice_id") != choice_id or receipt.result.get("transition") != transition:
                raise ValueError("P2P_IDEMPOTENCY_CONFLICT: receipt does not match this Choice transition")
            if receipt.result.get("replay_request_sha256") != self._replay_request_sha256(
                choice_id, request=request
            ):
                raise ValueError(
                    "P2P_IDEMPOTENCY_CONFLICT: idempotency key was already used for a different request"
                )
            if self.receipts.status(operation_key).state != "applied":
                raise ValueError(
                    "P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: recorded Choice transition no longer matches project state"
                )
            return ChoiceTransitionResult(
                status="already_applied",
                choice=self._status(self._load(choice_id)),
                transition=transition,
                replayed=True,
            )
        plan = self.transition_preview(choice_id, **request)  # type: ignore[arg-type]
        if plan.preview.preview_token != preview_token:
            raise ValueError("P2P_PREVIEW_STALE: Choice state or reviewed transition changed after preview")
        result_payload = {
            "contract": "p2p-choice-transition-result/v1",
            "choice_id": choice_id,
            "transition": plan.transition,
            "target_state": plan.target_state,
            "selected_option": plan.selected_option,
            "replacement_choice_id": plan.replacement_choice_id,
            "definition_digest": plan.definition_digest,
            "blockers_cleared": plan.blockers_cleared,
            "replay_request_sha256": plan.replay_request_sha256,
            "changed_paths": sorted(plan.candidates),
        }
        receipt_path, receipt_bytes, _ = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=plan.preview.operation_id,
            actor=plan.authority.executor.identity_id,
            request_fingerprint_sha256=plan.request_fingerprint_sha256,
            preview_token=preview_token,
            result=result_payload,
            candidates=plan.candidates,
            authority=plan.authority,
        )
        mutation = self.atomic_writer.apply(
            operation_id=plan.preview.operation_id,
            candidates={**plan.candidates, receipt_path: receipt_bytes},
            sources=plan.preview.source_preconditions,
            preview_token=preview_token,
            actor=plan.authority.executor.identity_id,
        )
        if mutation.status != "applied":
            raise ValueError(f"P2P_CHOICE_TRANSITION_FAILED: {mutation.message}")
        return ChoiceTransitionResult(
            status="applied",
            choice=self._status(self._load(choice_id)),
            transition=plan.transition,
            mutation=mutation,
        )

    def decide(self, choice_id: str, option: str, reason: str, decider: str) -> ChoiceStatus:
        operation_key = "choice-decide-" + semantic_sha256(
            {"choice_id": choice_id, "option": option, "reason": reason, "decider": decider, "on": date.today().isoformat()}
        )[:24]
        plan = self.transition_preview(
            choice_id, transition="decide", reason=reason, actor_id=decider,
            operation_key=operation_key, option=option,
        )
        return self.transition_apply(
            choice_id, transition="decide", reason=reason, actor_id=decider,
            operation_key=operation_key, option=option,
            preview_token=plan.preview.preview_token, confirm=True,
        ).choice

    def withdraw(self, choice_id: str, *, reason: str, actor_id: str, operation_key: str) -> ChoiceStatus:
        plan = self.transition_preview(
            choice_id, transition="withdraw", reason=reason, actor_id=actor_id, operation_key=operation_key
        )
        return self.transition_apply(
            choice_id, transition="withdraw", reason=reason, actor_id=actor_id,
            operation_key=operation_key, preview_token=plan.preview.preview_token, confirm=True,
        ).choice

    def supersede(
        self, choice_id: str, *, replacement_choice_id: str, reason: str, actor_id: str, operation_key: str
    ) -> ChoiceStatus:
        plan = self.transition_preview(
            choice_id, transition="supersede", reason=reason, actor_id=actor_id,
            operation_key=operation_key, replacement_choice_id=replacement_choice_id,
        )
        return self.transition_apply(
            choice_id, transition="supersede", reason=reason, actor_id=actor_id,
            operation_key=operation_key, replacement_choice_id=replacement_choice_id,
            preview_token=plan.preview.preview_token, confirm=True,
        ).choice

    def _load(self, choice_id: str) -> _LoadedChoice:
        return self._load_dir(self._find_dir(choice_id))

    def _load_dir(self, choice_dir: Path) -> _LoadedChoice:
        if choice_dir.is_symlink() or not choice_dir.is_dir():
            raise ValueError("P2P_CHOICE_INVALID: Choice path is missing or unsafe")
        choice_text = _read_optional(choice_dir / "choice.md")
        decision_text = _read_optional(choice_dir / "decision.md")
        frontmatter = read_frontmatter(choice_text)
        choice_id = str(frontmatter.get("choice_id") or "-").strip()
        title = str(frontmatter.get("title") or read_title(choice_text) or "").strip()
        options_payload = self._load_yaml(choice_dir / "options.yml", default={"options": []})
        links_payload = self._load_yaml(choice_dir / "links.yml", default={})
        definition = self._parse_definition(choice_id, title, choice_text, options_payload)
        lifecycle_path = choice_dir / "lifecycle.yml"
        lifecycle_bytes = lifecycle_path.read_bytes() if lifecycle_path.exists() else None
        if lifecycle_bytes is None:
            status = normalize_choice_state(frontmatter.get("status") or "open")
            selected_id = self._legacy_selected_option_id(decision_text, definition)
            if status == ChoiceState.decided and selected_id is None:
                raise ValueError("P2P_CHOICE_PROJECTION_INVALID: decided legacy Choice has no coherent selection")
            if status != ChoiceState.decided and selected_id is not None:
                raise ValueError("P2P_CHOICE_PROJECTION_INVALID: active legacy Choice has a decision")
            event = None
            if status == ChoiceState.decided:
                event = {
                    "contract": "p2p-choice-terminal-event/v1",
                    "kind": "decided",
                    "evidence_origin": "legacy_projection",
                    "reason": read_markdown_section(decision_text, "Reason") or "Legacy decision",
                    "effective_on": read_markdown_section(decision_text, "Date") or "unknown",
                    "owner_actor": read_markdown_section(decision_text, "Decided By") or "unknown",
                    "executor_actor": read_markdown_section(decision_text, "Decided By") or "unknown",
                    "authority_mode": "legacy_unverified",
                    "source_channel": "legacy",
                    "operation_key_sha256": None,
                    "selected_option_id": selected_id,
                    "replacement_choice_id": None,
                    "blocker_override": False,
                }
            return _LoadedChoice(
                choice_dir, definition, status,
                "complete_unsealed" if definition else "incomplete_unsealed",
                "unsealed", None, selected_id, event, None,
                choice_text, options_payload, decision_text, links_payload, None,
            )
        lifecycle = self._parse_lifecycle(lifecycle_bytes, choice_id)
        status = normalize_choice_state(lifecycle.get("state"))
        if str(frontmatter.get("status") or "") != status.value:
            raise ValueError("P2P_CHOICE_PROJECTION_INVALID: choice.md status disagrees with lifecycle.yml")
        stored_digest = lifecycle.get("definition_digest")
        completeness = str(lifecycle.get("definition_completeness") or "")
        definition_contract = str(lifecycle.get("definition_contract") or "")
        if definition_contract == CHOICE_DEFINITION_CONTRACT:
            # Current contracts never tolerate lifecycle flags or unknown data
            # in immutable option definitions.
            self._definition_options(options_payload, strict=True)
            if completeness != "complete" or definition is None:
                raise ValueError("P2P_CHOICE_DEFINITION_INVALID: sealed definition is incomplete")
            if stored_digest != definition.digest:
                raise ValueError("P2P_CHOICE_DEFINITION_DIGEST_MISMATCH: immutable Choice definition changed")
            seal_status = "sealed"
        elif (
            definition_contract != "legacy"
            or completeness not in {"complete", "incomplete"}
            or stored_digest is not None
            or (completeness == "complete") != (definition is not None)
        ):
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: invalid definition completeness contract")
        else:
            seal_status = "complete_unsealed" if definition is not None else "incomplete_unsealed"
        raw_event = lifecycle.get("terminal_event")
        event = dict(raw_event) if isinstance(raw_event, Mapping) else None
        if status == ChoiceState.open and event is not None:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: open Choice cannot have terminal evidence")
        if status != ChoiceState.open and (event is None or event.get("kind") != status.value):
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: terminal Choice lacks matching evidence")
        if event is not None:
            allowed_event = {
                "contract", "kind", "evidence_origin", "reason", "effective_on",
                "owner_actor", "executor_actor", "authority_mode", "source_channel",
                "operation_key_sha256", "selected_option_id", "replacement_choice_id",
                "blocker_override",
            }
            if set(event) != allowed_event:
                raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: terminal event has unsupported fields")
            if event.get("contract") != "p2p-choice-terminal-event/v1":
                raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: unsupported terminal event contract")
            ChoiceTerminalEvent(
                kind=status,
                reason=str(event.get("reason") or ""),
                effective_on=str(event.get("effective_on") or ""),
                owner_actor=str(event.get("owner_actor") or ""),
                executor_actor=str(event.get("executor_actor") or ""),
                authority_mode=str(event.get("authority_mode") or ""),
                source_channel=str(event.get("source_channel") or ""),
                operation_key_sha256=str(event.get("operation_key_sha256") or ""),
                selected_option_id=(str(event.get("selected_option_id") or "") or None),
                replacement_choice_id=(str(event.get("replacement_choice_id") or "") or None),
                blocker_override=bool(event.get("blocker_override", False)),
                evidence_origin=str(event.get("evidence_origin") or ""),
            )
        selected_id = (str(event.get("selected_option_id") or "") or None) if event else None
        replacement_id = (str(event.get("replacement_choice_id") or "") or None) if event else None
        if status == ChoiceState.decided:
            if definition is None:
                raise ValueError("P2P_CHOICE_DEFINITION_INVALID: current decided Choice must be complete")
            definition.option(selected_id or "")
        elif selected_id is not None:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: non-decision terminal state selected an option")
        self._validate_decision_projection(decision_text, status, selected_id, definition)
        return _LoadedChoice(
            choice_dir, definition, status,
            seal_status,
            "valid", str(stored_digest) if stored_digest else None,
            selected_id, event, replacement_id,
            choice_text, options_payload, decision_text, links_payload, lifecycle_bytes,
        )

    def _parse_definition(
        self, choice_id: str, title: str, choice_text: str, options_payload: Mapping[str, object]
    ) -> ChoiceDefinition | None:
        try:
            options = self._definition_options(options_payload, strict=False)
            return ChoiceDefinition(
                choice_id=choice_id,
                title=title,
                problem=read_markdown_section(choice_text, "Problem") or "",
                context=read_markdown_section(choice_text, "Context") or "",
                governance_boundary=read_markdown_section(choice_text, "Governance Boundary") or "",
                options=tuple(ChoiceOptionDefinition(str(item["id"]), str(item["title"])) for item in options),
            )
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _definition_options(payload: Mapping[str, object], *, strict: bool) -> list[dict[str, object]]:
        options = payload.get("options", [])
        if not isinstance(options, list):
            raise ValueError("Invalid options.yml: expected `options` list.")
        result: list[dict[str, object]] = []
        for item in options:
            if not isinstance(item, Mapping):
                raise ValueError("P2P_CHOICE_DEFINITION_INVALID: every option must be a mapping")
            if strict and set(item) != {"id", "title"}:
                raise ValueError("P2P_CHOICE_DEFINITION_INVALID: sealed options contain lifecycle or unknown fields")
            result.append({"id": item.get("id"), "title": item.get("title")})
        return result

    @staticmethod
    def _load_yaml(path: Path, *, default: dict[str, object]) -> dict[str, object]:
        if not path.exists():
            return dict(default)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"P2P_CHOICE_INVALID: unsafe Choice artifact {path.name}")
        try:
            payload = load_yaml(path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT)
        except Exception as exc:
            raise ValueError(f"P2P_CHOICE_INVALID: cannot parse {path.name}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"P2P_CHOICE_INVALID: {path.name} root must be a mapping")
        return payload

    @staticmethod
    def _parse_lifecycle(content: bytes, choice_id: str) -> dict[str, object]:
        try:
            payload = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
        except Exception as exc:
            raise ValueError(f"P2P_CHOICE_LIFECYCLE_INVALID: {exc}") from exc
        if not isinstance(payload, Mapping) or set(payload) != {"choice_lifecycle"}:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: expected exact choice_lifecycle root")
        lifecycle = payload.get("choice_lifecycle")
        if not isinstance(lifecycle, Mapping):
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: choice_lifecycle must be a mapping")
        allowed = {"contract", "choice_id", "definition_contract", "definition_digest", "definition_completeness", "state", "terminal_event", "adoption"}
        if set(lifecycle) != allowed or lifecycle.get("contract") != CHOICE_LIFECYCLE_CONTRACT:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: unsupported or incomplete lifecycle contract")
        if lifecycle.get("choice_id") != choice_id:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: Choice ID mismatch")
        return dict(lifecycle)

    def _validated_replacement(self, source: _LoadedChoice, replacement_id: str) -> _LoadedChoice:
        if replacement_id == self._choice_id(source):
            raise ValueError("P2P_CHOICE_REPLACEMENT_INVALID: a Choice cannot supersede itself")
        replacement = self._load(replacement_id)
        if not is_active_choice_state(replacement.status):
            raise ValueError("P2P_CHOICE_REPLACEMENT_INVALID: replacement must be open")
        if replacement.seal_status != "sealed" or replacement.definition is None:
            raise ValueError("P2P_CHOICE_REPLACEMENT_INVALID: replacement must be a sealed current Choice")
        source_digest = source.stored_digest or (source.definition.digest if source.definition else None)
        if source_digest is not None and source_digest == replacement.stored_digest:
            raise ValueError("P2P_CHOICE_REPLACEMENT_INVALID: replacement must have a different definition")
        edges = {
            self._choice_id(item): item.replacement_choice_id
            for item in (self._load_dir(path) for path in self._choice_dirs())
            if item.replacement_choice_id
        }
        edges[self._choice_id(source)] = replacement_id
        validate_supersession_graph(edges)  # type: ignore[arg-type]
        return replacement

    def _transition_sources(
        self, loaded: _LoadedChoice, receipt_path: str, replacement: _LoadedChoice | None
    ) -> tuple[object, ...]:
        paths = [
            loaded.choice_dir / "choice.md", loaded.choice_dir / "options.yml",
            loaded.choice_dir / "decision.md", loaded.choice_dir / "links.yml",
            loaded.choice_dir / "lifecycle.yml", self.authority.path,
            self.authority.permissions.path(),
        ]
        if replacement is not None:
            paths.extend([replacement.choice_dir / "choice.md", replacement.choice_dir / "options.yml", replacement.choice_dir / "lifecycle.yml"])
        result = [
            source_precondition(_relative(self.root, path), path.read_bytes() if path.exists() else None)
            for path in paths
        ]
        result.append(source_precondition(receipt_path, None))
        return tuple(result)

    def _terminal_candidates(
        self, loaded: _LoadedChoice, event: ChoiceTerminalEvent,
        selected: ChoiceOptionDefinition | None, links: Mapping[str, object],
    ) -> dict[str, bytes]:
        choice_id = self._choice_id(loaded)
        frontmatter = read_frontmatter(loaded.choice_text)
        frontmatter["status"] = event.kind.value
        sealed = loaded.seal_status == "sealed"
        return {
            _relative(self.root, loaded.choice_dir / "choice.md"): replace_frontmatter(loaded.choice_text, frontmatter).encode("utf-8"),
            _relative(self.root, loaded.choice_dir / "decision.md"): self._decision_bytes(choice_id, event.kind, event, selected),
            _relative(self.root, loaded.choice_dir / "links.yml"): _yaml_dump(dict(links)).encode("utf-8"),
            _relative(self.root, loaded.choice_dir / "lifecycle.yml"): self._lifecycle_bytes(
                choice_id,
                loaded.stored_digest if sealed else None,
                "complete" if loaded.definition else "incomplete",
                event.kind,
                event,
                definition_contract=CHOICE_DEFINITION_CONTRACT if sealed else "legacy",
            ),
        }

    @staticmethod
    def _replay_request_sha256(choice_id: str, *, request: Mapping[str, object]) -> str:
        authority_context = request.get("authority_context")
        authority_digest = getattr(authority_context, "digest_sha256", None)
        return semantic_sha256(
            {
                "choice_id": choice_id,
                "transition": str(request.get("transition") or ""),
                "reason": str(request.get("reason") or ""),
                "actor_id": str(request.get("actor_id") or ""),
                "executor_id": str(request.get("executor_id") or request.get("actor_id") or ""),
                "executor_kind": str(request.get("executor_kind") or "person"),
                "operation_key_sha256": idempotency_key_sha256(
                    str(request.get("operation_key") or "")
                ),
                "option": str(request.get("option") or "") or None,
                "replacement_choice_id": str(request.get("replacement_choice_id") or "") or None,
                "effective_on": str(request.get("effective_on") or "") or None,
                "blocker_override": bool(request.get("blocker_override", False)),
                "channel": str(request.get("channel") or "cli"),
                "authority_context_sha256": authority_digest,
                "consent_id": str(request.get("consent_id") or "") or None,
            }
        )

    @staticmethod
    def _terminal_links(payload: Mapping[str, object], event: ChoiceTerminalEvent) -> dict[str, object]:
        links = dict(payload)
        blocks = links.get("blocks", [])
        if not isinstance(blocks, list):
            raise ValueError("Invalid links.yml: expected `blocks` list.")
        normalized: list[object] = []
        for raw in blocks:
            if isinstance(raw, Mapping):
                item = dict(raw)
                if item.get("status", "active") == "active":
                    item.update({"status": "inactive", "cleared_on": event.effective_on, "cleared_by": event.owner_actor, "clearing_reason": f"choice_{event.kind.value}"})
                normalized.append(item)
            else:
                normalized.append(raw)
        links["blocks"] = normalized
        return links

    @staticmethod
    def _lifecycle_bytes(
        choice_id: str, digest: str | None, completeness: str, state: ChoiceState,
        terminal_event: ChoiceTerminalEvent | None, *, definition_contract: str = CHOICE_DEFINITION_CONTRACT,
    ) -> bytes:
        return _yaml_dump({"choice_lifecycle": {
            "contract": CHOICE_LIFECYCLE_CONTRACT,
            "choice_id": choice_id,
            "definition_contract": definition_contract,
            "definition_digest": digest,
            "definition_completeness": completeness,
            "state": state.value,
            "terminal_event": terminal_event.to_dict() if terminal_event else None,
            "adoption": None,
        }}).encode("utf-8")

    @staticmethod
    def _decision_bytes(
        choice_id: str, state: ChoiceState, event: ChoiceTerminalEvent | None,
        selected: ChoiceOptionDefinition | None,
    ) -> bytes:
        if state == ChoiceState.open:
            values = ("pending", "Pending.", "Pending.", "Pending.", "Pending.")
        elif state == ChoiceState.decided:
            assert event is not None and selected is not None
            values = ("decided", f"{selected.option_id} - {selected.title}", event.reason, event.owner_actor, event.effective_on)
        else:
            assert event is not None
            values = (state.value, "No option selected.", event.reason, event.owner_actor, event.effective_on)
        status, selected_text, reason, actor, when = values
        return (
            f"# Decision - {choice_id}\n\n## Status\n\n`{status}`\n\n"
            f"## Selected Option\n\n{selected_text}\n\n## Reason\n\n{reason}\n\n"
            f"## Decided By\n\n{actor}\n\n## Date\n\n{when}\n"
        ).encode("utf-8")

    @staticmethod
    def _legacy_selected_option_id(decision_text: str, definition: ChoiceDefinition | None) -> str | None:
        selected = read_markdown_section(decision_text, "Selected Option")
        if not selected or selected in {"Pending.", "No option selected."}:
            return None
        option_id = selected.split(" - ", 1)[0].strip().upper()
        if definition is not None:
            definition.option(option_id)
        return option_id

    @staticmethod
    def _validate_decision_projection(
        decision_text: str, state: ChoiceState, selected_id: str | None,
        definition: ChoiceDefinition | None,
    ) -> None:
        projected_status = (read_markdown_section(decision_text, "Status") or "").strip("`").strip()
        expected = "pending" if state == ChoiceState.open else state.value
        if projected_status != expected:
            raise ValueError("P2P_CHOICE_PROJECTION_INVALID: decision.md status disagrees with lifecycle.yml")
        projected = read_markdown_section(decision_text, "Selected Option")
        if state == ChoiceState.decided:
            if definition is None or not projected or not projected.startswith(f"{selected_id} - "):
                raise ValueError("P2P_CHOICE_PROJECTION_INVALID: decision selection disagrees with lifecycle.yml")
        elif state in {ChoiceState.withdrawn, ChoiceState.superseded} and projected != "No option selected.":
            raise ValueError("P2P_CHOICE_PROJECTION_INVALID: non-decision state cannot project a selection")

    def _selected_display(self, loaded: _LoadedChoice) -> str | None:
        if not loaded.selected_option_id:
            return None
        if loaded.definition is not None:
            option = loaded.definition.option(loaded.selected_option_id)
            return f"{option.option_id} - {option.title}"
        return read_markdown_section(loaded.decision_text, "Selected Option")

    def _status(self, loaded: _LoadedChoice) -> ChoiceStatus:
        frontmatter = read_frontmatter(loaded.choice_text)
        choice_id = self._choice_id(loaded)
        return ChoiceStatus(
            choice_id=choice_id,
            title=str(frontmatter.get("title") or read_title(loaded.choice_text) or choice_id),
            status=loaded.status.value,
            path=loaded.choice_dir.relative_to(self.root),
            selected_option=self._selected_display(loaded),
            terminal=is_terminal_choice_state(loaded.status),
            seal_status=loaded.seal_status,
            integrity_status=loaded.integrity_status,
            definition_digest=loaded.stored_digest,
            replacement_choice_id=loaded.replacement_choice_id,
        )

    def _write_links_atomically(self, loaded: _LoadedChoice, links: Mapping[str, object], operation: str) -> None:
        path = loaded.choice_dir / "links.yml"
        relative = _relative(self.root, path)
        before = path.read_bytes() if path.exists() else None
        result = self.atomic_writer.apply(
            operation_id=operation,
            candidates={relative: _yaml_dump(dict(links)).encode("utf-8")},
            sources=(source_precondition(relative, before),),
            preview_token=semantic_sha256({"operation": operation, "choice_id": self._choice_id(loaded), "links": links}),
            actor="local",
        )
        if result.status != "applied":
            raise ValueError(f"P2P_CHOICE_BLOCKER_MUTATION_FAILED: {result.message}")

    @staticmethod
    def _mapping_list(payload: Mapping[str, object], key: str) -> list[dict[str, object]]:
        value = payload.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"P2P_CHOICE_INVALID: expected `{key}` list")
        return [dict(item) for item in value if isinstance(item, Mapping)]

    @staticmethod
    def _choice_id(loaded: _LoadedChoice) -> str:
        return str(read_frontmatter(loaded.choice_text).get("choice_id") or loaded.choice_dir.name.rsplit("-", 1)[0])

    def _choice_dirs(self) -> list[Path]:
        root = self.p2p_dir / "choices"
        return [item for item in sorted(root.iterdir()) if item.is_dir()] if root.exists() else []

    def _next_id(self) -> str:
        max_id = 0
        for path in self._choice_dirs():
            match = re.match(r"CHOICE-(\d{3,})-", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"CHOICE-{max_id + 1:03d}"

    def _find_dir(self, choice_id: str) -> Path:
        if not re.fullmatch(r"CHOICE-[0-9]{3,}", choice_id):
            raise ValueError(f"P2P_CHOICE_INVALID: invalid Choice ID `{choice_id}`")
        for path in self._choice_dirs():
            if path.name.startswith(f"{choice_id}-"):
                return path
        raise ValueError(f"P2P_CHOICE_NOT_FOUND: Choice not found: {choice_id}")

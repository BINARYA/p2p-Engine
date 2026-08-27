from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAuthorityResolution,
    ProposalDecisionBindingStatus,
    ProposalDecisionLifecycleView,
)
from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import read_frontmatter


class WorkExportValidation(Protocol):
    path: Path
    checked: list[Path]


@dataclass(frozen=True)
class WorkStatus:
    work_id: str
    status: str
    change_id: str
    target: str
    path: Path


@dataclass(frozen=True)
class WorkDetail:
    work_id: str
    status: str
    change_id: str
    target: str
    path: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class WorkSummary:
    work_id: str
    status: str
    change_id: str
    target: str
    next_action: str
    note: str
    path: Path


@dataclass(frozen=True)
class WorkRetire:
    work_id: str
    status: str
    reason: str
    path: Path


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


class WorkPlanningService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        export_targets: Callable[[], tuple[str, ...]],
        validate_export: Callable[[str, str], WorkExportValidation],
        find_change_dir: Callable[[str], Path],
        proposal_lifecycle_status: (
            Callable[[str], ProposalDecisionLifecycleView] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.export_targets = export_targets
        self.validate_export = validate_export
        self.find_change_dir = find_change_dir
        self.proposal_lifecycle_status = proposal_lifecycle_status

    def create_plan(self, change_id: str, target: str) -> WorkDetail:
        target = target.lower()
        if target not in self.export_targets():
            raise ValueError(f"Unsupported work handoff target: {target}")
        change_dir = self.find_change_dir(change_id)
        change_frontmatter = read_frontmatter(_read_optional(change_dir / "change.md"))
        source = change_frontmatter.get("source", {})
        if not isinstance(source, dict):
            source = {}
        source_proposals = _string_list(source.get("accepted_proposals"))
        source_decisions: list[dict[str, object]] = []
        if self.proposal_lifecycle_status is not None:
            for proposal_id in source_proposals:
                lifecycle = self.proposal_lifecycle_status(proposal_id)
                if (
                    lifecycle.authority_resolution
                    != ProposalDecisionAuthorityResolution.resolved
                    or not lifecycle.active
                    or lifecycle.proposal_binding_status
                    != ProposalDecisionBindingStatus.current
                ):
                    raise ValueError(
                        "Cannot create Work. Governing proposal "
                        f"{proposal_id} has no current active bound authority "
                        f"({lifecycle.effective_state.value}, "
                        f"{lifecycle.proposal_binding_status.value})."
                    )
                source_decisions.append(
                    {
                        "proposal": proposal_id,
                        "head_event_id": lifecycle.head_event_id,
                        "decision_semantic_sha256": lifecycle.decision_semantic_sha256,
                    }
                )
        validation = self.validate_export(change_id, target)
        work_id = self.next_id()
        work_dir = self.p2p_dir / "work" / work_id
        work_dir.mkdir(parents=True)
        manifest = work_manifest(
            work_id=work_id,
            change_id=change_id,
            target=target,
            export_path=str(validation.path),
            source_proposals=source_proposals,
            source_decisions=source_decisions,
            allowed_files=[str(path) for path in validation.checked],
        )
        (work_dir / "manifest.yml").write_text(_yaml_dump(manifest), encoding="utf-8")
        return self.show(work_id)

    def statuses(self) -> list[WorkStatus]:
        statuses: list[WorkStatus] = []
        for path in self._work_directories():
            manifest = _read_yaml_mapping(path / "manifest.yml", default={})
            source = manifest.get("source", {})
            handoff = manifest.get("handoff", {})
            statuses.append(
                WorkStatus(
                    work_id=str(manifest.get("work_id") or path.name),
                    status=str(manifest.get("status") or "unknown"),
                    change_id=str(
                        source.get("change") if isinstance(source, dict) else "unknown"
                    ),
                    target=str(
                        handoff.get("target") if isinstance(handoff, dict) else "none"
                    ),
                    path=path.relative_to(self.root),
                )
            )
        return statuses

    def summaries(self) -> list[WorkSummary]:
        return [
            self.summary_from_manifest(
                _read_yaml_mapping(path / "manifest.yml", default={}),
                path.relative_to(self.root),
            )
            for path in self._work_directories()
        ]

    def show(self, work_id: str) -> WorkDetail:
        work_dir = self.find_dir(work_id)
        manifest = _read_yaml_mapping(work_dir / "manifest.yml", default={})
        source = manifest.get("source", {})
        handoff = manifest.get("handoff", {})
        return WorkDetail(
            work_id=str(manifest.get("work_id") or work_id),
            status=str(manifest.get("status") or "unknown"),
            change_id=str(source.get("change") if isinstance(source, dict) else "unknown"),
            target=str(handoff.get("target") if isinstance(handoff, dict) else "none"),
            path=work_dir.relative_to(self.root),
            manifest=manifest,
        )

    def retire(self, work_id: str, reason: str) -> WorkRetire:
        reason = reason.strip()
        if not reason:
            raise ValueError("Work retire reason is required")
        work_dir = self.find_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "planned":
            raise ValueError(
                f"Work item must be planned before retire. Current status: {status}"
            )
        manifest["status"] = "retired"
        manifest["retirement"] = {
            "reason": reason,
            "retired_at": date.today().isoformat(),
            "mode": "metadata_only",
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")
        return WorkRetire(
            work_id=str(manifest.get("work_id") or work_id),
            status="retired",
            reason=reason,
            path=work_dir.relative_to(self.root),
        )

    def summary_from_manifest(
        self,
        manifest: dict[str, object],
        path: Path,
    ) -> WorkSummary:
        source = manifest.get("source", {})
        handoff = manifest.get("handoff", {})
        status = str(manifest.get("status") or "unknown")
        work_id = str(manifest.get("work_id") or path.name)
        next_action, note = work_next_action(work_id=work_id, status=status)
        return WorkSummary(
            work_id=work_id,
            status=status,
            change_id=str(source.get("change") if isinstance(source, dict) else "unknown"),
            target=str(handoff.get("target") if isinstance(handoff, dict) else "none"),
            next_action=next_action,
            note=note,
            path=path,
        )

    def next_id(self) -> str:
        max_id = 0
        for path in self._work_directories():
            match = re.match(r"WORK-(\d{3})$", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"WORK-{max_id + 1:03d}"

    def find_dir(self, work_id: str) -> Path:
        work_root = self.p2p_dir / "work"
        if not work_root.exists():
            raise ValueError("No .p2p/work directory found.")
        path = work_root / work_id
        if not path.is_dir():
            raise ValueError(f"Work item not found: {work_id}")
        return path

    def _work_directories(self) -> list[Path]:
        work_root = self.p2p_dir / "work"
        return [
            path
            for path in sorted(work_root.iterdir())
            if path.is_dir()
        ] if work_root.exists() else []


def work_manifest(
    *,
    work_id: str,
    change_id: str,
    target: str,
    export_path: str,
    source_proposals: list[str],
    source_decisions: list[dict[str, object]] | None = None,
    allowed_files: list[str],
) -> dict[str, object]:
    return {
        "work_id": work_id,
        "status": "planned",
        "visibility": "internal_project_state",
        "created_at": date.today().isoformat(),
        "source": {
            "change": change_id,
            "proposals": source_proposals,
            "decisions": source_decisions or [],
        },
        "handoff": {
            "target": target,
            "export_path": export_path,
            "export_validated": True,
        },
        "allowed_files": allowed_files,
        "next_steps": [
            "Inspect the validated handoff and complete delivery in an external implementation workflow.",
            "Record caller-supplied implementation references only as opaque traceability metadata.",
        ],
    }


def work_next_action(*, work_id: str, status: str) -> tuple[str, str]:
    if status == "planned":
        return f"p2p work show {work_id}", "inspect the logical handoff"
    if status == "retired":
        return "none", "retired"
    return f"p2p work show {work_id}", "inspect logical Work state"

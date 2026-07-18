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
    branch_name: str
    path: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class WorkSummary:
    work_id: str
    status: str
    change_id: str
    target: str
    branch_name: str
    base_branch: str
    remote: str | None
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
        scanned_work_items: Callable[[], list[dict[str, object]]],
        proposal_lifecycle_status: (
            Callable[[str], ProposalDecisionLifecycleView] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.export_targets = export_targets
        self.validate_export = validate_export
        self.find_change_dir = find_change_dir
        self.scanned_work_items = scanned_work_items
        self.proposal_lifecycle_status = proposal_lifecycle_status

    def create_plan(self, change_id: str, target: str) -> WorkDetail:
        target = target.lower()
        if target not in self.export_targets():
            raise ValueError(f"Unsupported work handoff target: {target}")
        change_dir = self.find_change_dir(change_id)
        change_text = _read_optional(change_dir / "change.md")
        change_frontmatter = read_frontmatter(change_text)
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
                        "decision_semantic_sha256": (
                            lifecycle.decision_semantic_sha256
                        ),
                    }
                )
        validation = self.validate_export(change_id, target)
        work_id = self.next_id()
        work_dir = self.p2p_dir / "work" / work_id
        work_dir.mkdir(parents=True)
        branch_name = f"p2p/work/{work_id.lower()}-{change_id.lower()}-{target}"
        manifest = work_manifest(
            work_id=work_id,
            change_id=change_id,
            target=target,
            branch_name=branch_name,
            export_path=str(validation.path),
            source_proposals=source_proposals,
            source_decisions=source_decisions,
            allowed_files=[str(path) for path in validation.checked],
        )
        (work_dir / "manifest.yml").write_text(_yaml_dump(manifest), encoding="utf-8")
        return self.show(work_id)

    def statuses(self) -> list[WorkStatus]:
        work_root = self.p2p_dir / "work"
        statuses: list[WorkStatus] = []
        for path in sorted(work_root.iterdir()) if work_root.exists() else []:
            if not path.is_dir():
                continue
            manifest = _read_yaml_mapping(path / "manifest.yml", default={})
            source = manifest.get("source", {})
            handoff = manifest.get("handoff", {})
            statuses.append(
                WorkStatus(
                    work_id=str(manifest.get("work_id") or path.name),
                    status=str(manifest.get("status") or "unknown"),
                    change_id=str(source.get("change") if isinstance(source, dict) else "unknown"),
                    target=str(handoff.get("target") if isinstance(handoff, dict) else "none"),
                    path=path.relative_to(self.root),
                )
            )
        for item in self.scanned_work_items():
            statuses.append(
                WorkStatus(
                    work_id=str(item.get("work_id") or "unknown"),
                    status=str(item.get("status") or "unknown"),
                    change_id=str(item.get("change") or "unknown"),
                    target=str(item.get("target") or "none"),
                    path=Path(str(item.get("path") or ".")),
                )
            )
        return statuses

    def summaries(self) -> list[WorkSummary]:
        summaries: list[WorkSummary] = []
        work_root = self.p2p_dir / "work"
        for path in sorted(work_root.iterdir()) if work_root.exists() else []:
            if not path.is_dir():
                continue
            manifest = _read_yaml_mapping(path / "manifest.yml", default={})
            summaries.append(self.summary_from_manifest(manifest, path.relative_to(self.root), scanned=False))
        for item in self.scanned_work_items():
            summaries.append(self.summary_from_scan(item))
        return summaries

    def show(self, work_id: str) -> WorkDetail:
        work_dir = self.find_dir(work_id)
        manifest = _read_yaml_mapping(work_dir / "manifest.yml", default={})
        source = manifest.get("source", {})
        handoff = manifest.get("handoff", {})
        git = manifest.get("git", {})
        return WorkDetail(
            work_id=str(manifest.get("work_id") or work_id),
            status=str(manifest.get("status") or "unknown"),
            change_id=str(source.get("change") if isinstance(source, dict) else "unknown"),
            target=str(handoff.get("target") if isinstance(handoff, dict) else "none"),
            branch_name=str(git.get("branch_name") if isinstance(git, dict) else ""),
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
            raise ValueError(f"Work item must be planned before retire. Current status: {status}")

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

    def summary_from_manifest(self, manifest: dict[str, object], path: Path, *, scanned: bool) -> WorkSummary:
        source = manifest.get("source", {})
        handoff = manifest.get("handoff", {})
        git = manifest.get("git", {})
        publish = manifest.get("publish", {})
        acceptance = manifest.get("acceptance", {})
        status = str(manifest.get("status") or "unknown")
        work_id = str(manifest.get("work_id") or path.name)
        branch_name = str(git.get("branch_name") if isinstance(git, dict) else "")
        base_branch = str(git.get("base_branch") if isinstance(git, dict) else "main")
        remote = None
        if isinstance(publish, dict):
            remote_value = publish.get("remote")
            if remote_value:
                remote = str(remote_value)
        if status == "accepted" and isinstance(acceptance, dict):
            pushed = bool(acceptance.get("pushed"))
        else:
            pushed = bool(publish.get("remote_branch")) if isinstance(publish, dict) else False
        next_action, note = work_next_action(
            work_id=work_id,
            status=status,
            base_branch=base_branch,
            pushed=pushed,
            accepted=bool(acceptance) if isinstance(acceptance, dict) else False,
            scanned=scanned,
        )
        return WorkSummary(
            work_id=work_id,
            status=status,
            change_id=str(source.get("change") if isinstance(source, dict) else "unknown"),
            target=str(handoff.get("target") if isinstance(handoff, dict) else "none"),
            branch_name=branch_name,
            base_branch=base_branch,
            remote=remote,
            next_action=next_action,
            note=note,
            path=path,
        )

    def summary_from_scan(self, item: dict[str, object]) -> WorkSummary:
        work_id = str(item.get("work_id") or "unknown")
        status = str(item.get("status") or "unknown")
        branch_name = str(item.get("branch_name") or item.get("branch") or "")
        next_action, note = work_next_action(
            work_id=work_id,
            status=status,
            base_branch="main",
            pushed=False,
            accepted=False,
            scanned=True,
        )
        return WorkSummary(
            work_id=work_id,
            status=status,
            change_id=str(item.get("change") or "unknown"),
            target=str(item.get("target") or "none"),
            branch_name=branch_name,
            base_branch="main",
            remote=None,
            next_action=next_action,
            note=note,
            path=Path(str(item.get("path") or ".")),
        )

    def next_id(self) -> str:
        max_id = 0
        work_root = self.p2p_dir / "work"
        for path in work_root.iterdir() if work_root.exists() else []:
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


def work_manifest(
    *,
    work_id: str,
    change_id: str,
    target: str,
    branch_name: str,
    export_path: str,
    source_proposals: list[str],
    source_decisions: list[dict[str, object]] | None = None,
    allowed_files: list[str],
) -> dict[str, object]:
    return {
        "work_id": work_id,
        "status": "planned",
        "visibility": "internal_git",
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
        "managed_git_levels": [
            {"level": 0, "name": "advisory", "enabled": True},
            {"level": 1, "name": "handoff_plan", "enabled": True},
            {"level": 2, "name": "managed_branch", "enabled": False},
            {"level": 3, "name": "managed_commit", "enabled": False},
            {"level": 4, "name": "managed_review", "enabled": False},
            {"level": 5, "name": "owner_controlled_merge", "enabled": False},
        ],
        "git": {
            "mode": "managed_branch_candidate",
            "base_branch": "main",
            "branch_name": branch_name,
            "base_commit": None,
            "head_commit": None,
        },
        "policy": {
            "expose_git_details": False,
            "auto_branch": False,
            "auto_commit": False,
            "auto_merge": False,
            "owner_approval_required": ["branch", "submit", "accept_merge"],
        },
        "allowed_files": allowed_files,
        "next_steps": [
            "Implement branch scan for p2p/work/* refs.",
            "Enable managed branch creation only after policy approval.",
            "Enable selected-file commits only after dirty worktree and recovery checks.",
            "Enable owner-controlled accept/merge only after review policy is defined.",
        ],
    }


def work_next_action(
    *,
    work_id: str,
    status: str,
    base_branch: str,
    pushed: bool,
    accepted: bool,
    scanned: bool,
) -> tuple[str, str]:
    if scanned:
        return "p2p work show {work_id}".format(work_id=work_id), "scanned from a managed branch registry"
    if status == "planned":
        return f"p2p work branch {work_id}", "create the managed implementation branch"
    if status == "retired":
        return "none", "retired"
    if status == "branched":
        return f"p2p work submit {work_id}", "submit actual work changes as a local commit"
    if status == "submitted":
        return f"p2p work review {work_id}", "request local owner review"
    if status == "review_requested":
        return f"p2p work publish {work_id}", "publish the managed branch to the remote"
    if status == "published":
        return f"checkout {base_branch}; p2p work accept {work_id}", "owner-controlled local merge"
    if status == "merge_conflict":
        return f"resolve conflicts; p2p work accept --continue {work_id}", "or abort with p2p work accept --abort"
    if status == "accepted":
        if accepted and not pushed:
            return "p2p work finalize {work_id}".format(work_id=work_id), "push the accepted base branch"
        return "none", "accepted"
    if status == "finalized":
        return "p2p work cleanup {work_id}".format(work_id=work_id), "delete finalized Work branches"
    if status == "cleaned":
        return "none", "cleaned"
    return "inspect", "unknown Work status"

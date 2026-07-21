from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionBindingStatus,
    ProposalDecisionLifecycleView,
)
from p2p_engine.foundation.markdown import read_frontmatter, read_markdown_section, read_title
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.lifecycle_authority import proposal_display_status


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_yaml(path: Path, default: object) -> object:
    if not path.exists():
        return default
    data = load_yaml(path.read_bytes())
    return data if data is not None else default


def _read_yaml_mapping(path: Path, default: dict[str, object]) -> dict[str, object]:
    data = _read_yaml(path, default)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML mapping: {path}")
    return data


def _read_proposal_status(path: Path) -> str:
    if not path.exists():
        return "unknown"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## Status\s+`([^`]+)`", text)
    return match.group(1) if match else "unknown"


def _clean_proposal_title(title: str, proposal_id: str) -> str:
    cleaned = title.strip()
    prefixes = [proposal_id, proposal_id.replace("-", " ")]
    for prefix in prefixes:
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix) :].lstrip(" -:")
    return cleaned or title


def _lifecycle_metadata(
    lifecycle: ProposalDecisionLifecycleView | None,
) -> dict[str, object]:
    if lifecycle is None:
        return {}
    return {
        "effective_state": lifecycle.effective_state.value,
        "head_event_type": (
            lifecycle.head_event_type.value
            if lifecycle.head_event_type is not None
            else None
        ),
        "head_event_id": lifecycle.head_event_id,
        "event_count": lifecycle.event_count,
        "authority_resolution": lifecycle.authority_resolution.value,
        "active": lifecycle.active,
        "ever_active": lifecycle.ever_active,
        "proposal_binding_status": lifecycle.proposal_binding_status.value,
        "decision_semantic_sha256": lifecycle.decision_semantic_sha256,
        "proposal_semantic_sha256": lifecycle.proposal_semantic_sha256,
        "lineage": lifecycle.lineage.to_dict(),
    }


class RegistryRecordBuilderService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        read_proposal_readiness: Callable[[str], Any],
        proposal_decision_lifecycles: (
            Callable[[], dict[str, ProposalDecisionLifecycleView]] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.read_proposal_readiness = read_proposal_readiness
        self.proposal_decision_lifecycles = proposal_decision_lifecycles

    def accepted_proposals(self) -> list[dict[str, object]]:
        proposals_dir = self.p2p_dir / "proposals"
        lifecycles = self._lifecycles()
        accepted: list[dict[str, object]] = []
        for path in sorted(proposals_dir.iterdir()) if proposals_dir.exists() else []:
            if not path.is_dir():
                continue
            proposal_path = path / "proposal.md"
            proposal_id = "-".join(path.name.split("-", 2)[:2])
            lifecycle = lifecycles.get(proposal_id)
            projected_status = _read_proposal_status(proposal_path)
            status = (
                proposal_display_status(
                    lifecycle,
                    undecided_fallback=projected_status,
                )
                if lifecycle is not None
                else projected_status
            )
            if (
                lifecycle is not None
                and (
                    not lifecycle.active
                    or lifecycle.proposal_binding_status
                    != ProposalDecisionBindingStatus.current
                )
            ) or (
                lifecycle is None
                and status not in {"accepted", "accepted_with_changes"}
            ):
                continue
            text = _read_optional(proposal_path)
            title = _clean_proposal_title(read_title(text) or path.name, proposal_id)
            accepted.append(
                {
                    "proposal_id": proposal_id,
                    "title": title,
                    "status": status,
                    "feature_id": _slugify(title.replace(proposal_id, "", 1)),
                    "path": path,
                    "source": str(path.relative_to(self.root)),
                    "problem": read_markdown_section(text, "Problem") or "Not provided.",
                    "goals": read_markdown_section(text, "Goals") or "- Not provided.",
                    "non_goals": read_markdown_section(text, "Non-Goals") or "- Not provided.",
                    "proposal": read_markdown_section(text, "Proposal") or "Not provided.",
                    "decision": _read_optional(path / "decision.md"),
                    "ledger_file": (
                        str((path / "decision-events.yml").relative_to(self.root))
                        if (path / "decision-events.yml").exists()
                        else None
                    ),
                    **_lifecycle_metadata(lifecycle),
                }
            )
        return accepted

    def proposal_records(
        self,
        changes: list[dict[str, object]] | None = None,
    ) -> list[dict[str, object]]:
        proposals_dir = self.p2p_dir / "proposals"
        changes_by_proposal = self._changes_by_proposal(
            changes if changes is not None else self.change_records()
        )
        lifecycles = self._lifecycles()
        records: list[dict[str, object]] = []
        for path in sorted(proposals_dir.iterdir()) if proposals_dir.exists() else []:
            if not path.is_dir():
                continue
            proposal_id = "-".join(path.name.split("-", 2)[:2])
            proposal_text = _read_optional(path / "proposal.md")
            lifecycle = lifecycles.get(proposal_id)
            projected_status = _read_proposal_status(path / "proposal.md")
            status = (
                proposal_display_status(
                    lifecycle,
                    undecided_fallback=projected_status,
                )
                if lifecycle is not None
                else projected_status
            )
            title = _clean_proposal_title(read_title(proposal_text) or path.name, proposal_id)
            records.append(
                {
                    "id": proposal_id,
                    "title": title,
                    "status": status,
                    "path": str(path.relative_to(self.root)),
                    "summary": read_markdown_section(proposal_text, "Proposal") or "",
                    "decision_file": str((path / "decision.md").relative_to(self.root)),
                    "related_changes": list(changes_by_proposal.get(proposal_id, ())),
                    "source_files": sorted(file.name for file in path.iterdir() if file.is_file()),
                    "ledger_file": (
                        str((path / "decision-events.yml").relative_to(self.root))
                        if (path / "decision-events.yml").exists()
                        else None
                    ),
                    **_lifecycle_metadata(lifecycle),
                }
            )
        return records

    def decision_records(self, proposals: list[dict[str, object]]) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        lifecycles = self._lifecycles()
        for proposal in proposals:
            decision_path = self.root / str(proposal["decision_file"])
            decision_text = _read_optional(decision_path)
            outcome = read_markdown_section(decision_text, "Outcome")
            if not outcome:
                status = read_markdown_section(decision_text, "Status")
                outcome = status.strip("`") if status else "pending"
            proposal_id = str(proposal["id"])
            lifecycle = lifecycles.get(proposal_id)
            if lifecycle is not None:
                outcome = lifecycle.effective_state.value
            records.append(
                {
                    "proposal": proposal_id,
                    "title": proposal["title"],
                    "outcome": outcome,
                    "status": proposal["status"],
                    "path": str(decision_path.relative_to(self.root)),
                    "reason": read_markdown_section(decision_text, "Reason") or "",
                    **_lifecycle_metadata(lifecycle),
                }
            )
        return records

    def _lifecycles(self) -> dict[str, ProposalDecisionLifecycleView]:
        if self.proposal_decision_lifecycles is None:
            return {}
        return dict(self.proposal_decision_lifecycles())

    def change_records(self) -> list[dict[str, object]]:
        changes_dir = self.p2p_dir / "changes"
        records: list[dict[str, object]] = []
        for path in sorted(changes_dir.iterdir()) if changes_dir.exists() else []:
            if not path.is_dir():
                continue
            change_text = _read_optional(path / "change.md")
            frontmatter = read_frontmatter(change_text)
            source = frontmatter.get("source", {})
            if not isinstance(source, dict):
                source = {}
            tasks_data = _read_yaml_mapping(path / "tasks.yml", default={"tasks": []})
            tasks = tasks_data.get("tasks", [])
            records.append(
                {
                    "id": str(frontmatter.get("change_id") or "-".join(path.name.split("-", 2)[:2])),
                    "title": str(frontmatter.get("title") or read_title(change_text) or path.name),
                    "status": str(frontmatter.get("status") or "unknown"),
                    "path": str(path.relative_to(self.root)),
                    "included_proposals": source.get("accepted_proposals", []),
                    "referenced_proposals": _read_yaml_mapping(
                        path / "referenced-proposals.yml",
                        default={"referenced_proposals": []},
                    ).get("referenced_proposals", []),
                    "execution_domains": frontmatter.get("execution_domains", []),
                    "implementation_targets": frontmatter.get("implementation_targets", []),
                    "spec_targets": frontmatter.get("spec_targets", []),
                    "export_targets": frontmatter.get("export_targets", []),
                    "task_count": len(tasks) if isinstance(tasks, list) else 0,
                }
            )
        return records

    def choice_records(self) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        choices_dir = self.p2p_dir / "choices"
        for path in sorted(choices_dir.iterdir()) if choices_dir.exists() else []:
            if not path.is_dir():
                continue
            choice_text = _read_optional(path / "choice.md")
            frontmatter = read_frontmatter(choice_text)
            options_data = _read_yaml_mapping(path / "options.yml", default={"options": []})
            options = options_data.get("options", [])
            decision_text = _read_optional(path / "decision.md")
            selected = read_markdown_section(decision_text, "Selected Option")
            selected_option = None if selected in {None, "Pending."} else selected
            records.append(
                {
                    "id": str(frontmatter.get("choice_id") or "-".join(path.name.split("-", 2)[:2])),
                    "title": str(frontmatter.get("title") or read_title(choice_text) or path.name),
                    "status": str(frontmatter.get("status") or "unknown"),
                    "options": [
                        option.get("id")
                        for option in options
                        if isinstance(option, dict) and option.get("id")
                    ]
                    if isinstance(options, list)
                    else [],
                    "selected_option": selected_option,
                    "path": str(path.relative_to(self.root)),
                }
            )

        proposals_dir = self.p2p_dir / "proposals"
        for path in sorted(proposals_dir.iterdir()) if proposals_dir.exists() else []:
            if not path.is_dir():
                continue
            votes_path = path / "votes.yml"
            if not votes_path.exists():
                continue
            proposal_id = "-".join(path.name.split("-", 2)[:2])
            data = _read_yaml_mapping(votes_path, default={})
            result = data.get("result", {})
            records.append(
                {
                    "id": f"CHOICE-{proposal_id}",
                    "proposal": proposal_id,
                    "status": data.get("status", "open"),
                    "options": sorted(
                        {
                            str(vote.get("choice"))
                            for vote in data.get("votes", [])
                            if isinstance(vote, dict) and vote.get("choice")
                        }
                    ),
                    "selected_option": result.get("winner") if isinstance(result, dict) else None,
                    "path": str(votes_path.relative_to(self.root)),
                }
            )
        return records

    def relation_records(
        self,
        proposals: list[dict[str, object]],
        changes: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for change in changes:
            for proposal_id in change.get("included_proposals", []):
                records.append(
                    {
                        "source": change["id"],
                        "target": proposal_id,
                        "type": "includes",
                        "rationale": "Change Set includes accepted proposal.",
                        "source_artifact": change["path"],
                    }
                )
            for proposal_id in change.get("referenced_proposals", []):
                records.append(
                    {
                        "source": change["id"],
                        "target": proposal_id,
                        "type": "references",
                        "rationale": "Change Set references proposal as context.",
                        "source_artifact": change["path"],
                    }
                )
        for proposal in proposals:
            for change_id in proposal.get("related_changes", []):
                records.append(
                    {
                        "source": proposal["id"],
                        "target": change_id,
                        "type": "implemented_by",
                        "rationale": "Proposal appears in Change Set source metadata.",
                        "source_artifact": proposal["path"],
                    }
                )
        return records

    def artifact_records(
        self,
        proposals: list[dict[str, object]],
        changes: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for proposal in proposals:
            proposal_dir = self.root / str(proposal["path"])
            for file in sorted(proposal_dir.iterdir()) if proposal_dir.exists() else []:
                if file.is_file():
                    records.append(
                        {
                            "path": str(file.relative_to(self.root)),
                            "artifact_type": file.name,
                            "owner_type": "proposal",
                            "owner": proposal["id"],
                            "generated": False,
                            "authority_role": (
                                "canonical_decision_ledger"
                                if file.name == "decision-events.yml"
                                else "decision_projection"
                                if file.name == "decision.md"
                                else "canonical_proposal_body"
                                if file.name == "proposal.md"
                                else "supporting_artifact"
                            ),
                        }
                    )
        for change in changes:
            change_dir = self.root / str(change["path"])
            for file in sorted(change_dir.iterdir()) if change_dir.exists() else []:
                if file.is_file():
                    records.append(
                        {
                            "path": str(file.relative_to(self.root)),
                            "artifact_type": file.name,
                            "owner_type": "change",
                            "owner": change["id"],
                            "generated": False,
                        }
                    )
        return records

    def readiness_records(self, proposals: list[dict[str, object]]) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for proposal in proposals:
            readiness = self.read_proposal_readiness(str(proposal["id"]))
            records.append(
                {
                    "proposal": proposal["id"],
                    "title": proposal["title"],
                    "proposal_status": proposal["status"],
                    "status": readiness.status,
                    "profile_id": readiness.profile_id,
                    "profile_version": readiness.profile_version,
                    "computed_score": readiness.computed_score,
                    "computed_label": readiness.computed_label,
                    "confidence": readiness.confidence,
                    "failed_gates": readiness.failed_gates,
                    "missing": readiness.missing,
                    "suggested_next": readiness.suggested_next,
                    "path": str(readiness.path),
                }
            )
        return records

    def changes_for_proposal(self, proposal_id: str) -> list[str]:
        return list(self._changes_by_proposal(self.change_records()).get(proposal_id, ()))

    @staticmethod
    def _changes_by_proposal(
        changes: list[dict[str, object]],
    ) -> dict[str, tuple[str, ...]]:
        related: dict[str, list[str]] = {}
        for change in changes:
            included = change.get("included_proposals", [])
            if not isinstance(included, list):
                continue
            for proposal_id in included:
                normalized = str(proposal_id)
                related.setdefault(normalized, []).append(str(change["id"]))
        return {
            proposal_id: tuple(sorted(set(change_ids)))
            for proposal_id, change_ids in sorted(related.items())
        }

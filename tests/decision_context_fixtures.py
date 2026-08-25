from __future__ import annotations

from pathlib import Path

import yaml

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAffectedDecision,
    ProposalDecisionCondition,
    ProposalDecisionEventType,
    ProposalDecisionImpactBinding,
    ProposalDecisionLineage,
    ProposalDecisionLineageKind,
    ProposalDecisionReadinessBinding,
)
from p2p_engine.services.lifecycle_authority import effective_state_for_event
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    decision_semantic_sha256,
    operation_key,
    proposal_semantic_sha256,
    render_decision_projection,
)
from p2p_engine.services.project_questions import ProjectQuestionStateService
from tests.proposal_decision_fixtures import authority as decision_authority


def initialize_project(root: Path) -> Path:
    proposals = root / ".p2p" / "proposals"
    proposals.mkdir(parents=True, exist_ok=True)
    questions_path = root / ".p2p" / "project" / "questions.yml"
    if not questions_path.exists():
        service = ProjectQuestionStateService(root=root, p2p_dir=root / ".p2p")
        artifact = service.empty_artifact(
            project_id="decision-context-fixture",
            vertical_id="binarya/base_project",
            vertical_version="2.0.0",
            lock_checksum="a" * 64,
            actor="owner",
            audit_at="2026-01-01T00:00:00Z",
        )
        questions_path.parent.mkdir(parents=True, exist_ok=True)
        questions_path.write_bytes(service.candidate_bytes(artifact))
    return proposals


def write_proposal(
    root: Path,
    proposal_id: str,
    *,
    title: str = "Example Proposal",
    status: str = "draft",
    problem: str = "The project loses relevant decision context.",
    goals: tuple[str, ...] = ("Preserve source evidence.",),
    non_goals: tuple[str, ...] = ("Replace canonical files.",),
    proposal: str = "Build a derived decision context index.",
    acceptance: tuple[str, ...] = ("Context retrieval is deterministic.",),
    decision_outcome: str | None = None,
    decision_reason: str = "The architecture direction is approved.",
    decision_date: str = "2026-07-15",
    approver: str = "owner",
    newline: str = "\n",
) -> Path:
    proposals_root = initialize_project(root)
    slug = proposal_id.lower() + "-example"
    proposal_dir = proposals_root / slug
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_text = newline.join(
        (
            f"# {proposal_id} - {title}",
            "",
            "## Status",
            "",
            f"`{status}`",
            "",
            "## Problem",
            "",
            problem,
            "",
            "## Goals",
            "",
            *[f"- {item}" for item in goals],
            "",
            "## Non-Goals",
            "",
            *[f"- {item}" for item in non_goals],
            "",
            "## Proposal",
            "",
            proposal,
            "",
            "## Acceptance Criteria",
            "",
            *[f"- {item}" for item in acceptance],
            "",
            "## Decision",
            "",
            "Pending.",
            "",
        )
    )
    (proposal_dir / "proposal.md").write_text(proposal_text, encoding="utf-8", newline="")
    codec = ProposalDecisionLedgerCodec()
    ledger = codec.empty(proposal_id)
    if decision_outcome is not None:
        event = None
        if decision_outcome not in {"pending", "draft"}:
            event_type = ProposalDecisionEventType(decision_outcome)
            state = effective_state_for_event(event_type)
            conditions = (
                (ProposalDecisionCondition("COND-001", decision_reason),)
                if event_type == ProposalDecisionEventType.accepted_with_changes
                else ()
            )
            lineage = {
                ProposalDecisionEventType.superseded: ProposalDecisionLineage(
                    ProposalDecisionLineageKind.supersedes, ("PROP-999",)
                ),
                ProposalDecisionEventType.split: ProposalDecisionLineage(
                    ProposalDecisionLineageKind.split, ("PROP-998", "PROP-999")
                ),
                ProposalDecisionEventType.merged_into_other: ProposalDecisionLineage(
                    ProposalDecisionLineageKind.merged_into, ("PROP-999",)
                ),
            }.get(event_type, ProposalDecisionLineage())
            proposal_sha = proposal_semantic_sha256(proposal_id, proposal_text)
            decision_sha = decision_semantic_sha256(
                proposal_sha256=proposal_sha,
                outcome=state,
                rationale=decision_reason,
                conditions=conditions,
            )
            event = codec.build_event(
                proposal_id=proposal_id,
                event_type=event_type,
                effective_state=state,
                rationale=decision_reason,
                conditions=conditions,
                decided_on=decision_date,
                authority=decision_authority(approver),
                predecessor=None,
                proposal_semantic_sha256=proposal_sha,
                decision_semantic_sha256=decision_sha,
                affected_decision=ProposalDecisionAffectedDecision(),
                lineage=lineage,
                impact=ProposalDecisionImpactBinding(),
                readiness=ProposalDecisionReadinessBinding(),
                preview_token=semantic_sha256({"fixture": proposal_id, "preview": decision_outcome}),
                request_fingerprint_sha256=semantic_sha256(
                    {"fixture": proposal_id, "request": decision_outcome}
                ),
                operation_key=operation_key(
                    {"fixture": proposal_id, "outcome": decision_outcome},
                    None,
                ),
            )
            ledger = codec.append(ledger, event)
        decision_text = render_decision_projection(proposal_id, event)
        (proposal_dir / "decision.md").write_text(decision_text, encoding="utf-8", newline="")
    (proposal_dir / "decision-events.yml").write_bytes(codec.dumps(ledger))
    return proposal_dir


def project_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_yaml(root: Path, relative_path: str, payload: object) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def write_markdown(
    root: Path,
    relative_path: str,
    *,
    title: str,
    frontmatter: dict[str, object] | None = None,
    sections: tuple[tuple[str, str], ...] = (),
) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if frontmatter is not None:
        lines.extend(("---", yaml.safe_dump(frontmatter, sort_keys=False).rstrip(), "---", ""))
    lines.extend((f"# {title}", ""))
    for label, text in sections:
        lines.extend((f"## {label}", "", text, ""))
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

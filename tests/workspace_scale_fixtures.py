from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionCondition,
    ProposalDecisionEffectiveState,
    ProposalDecisionEventType,
)
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    render_decision_projection,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import (
    append_event,
    write_current_proposal,
)


@dataclass(frozen=True)
class ScaleWorkspace:
    root: Path
    proposal_ids: tuple[str, ...]
    schema_version: int
    rich_proposals: int


def build_scale_workspace(
    root: Path,
    *,
    proposal_count: int,
    schema_version: int = 4,
    rich_proposals: int = 100,
    reverse_enumeration: bool = False,
) -> ScaleWorkspace:
    if proposal_count < 1:
        raise ValueError("proposal_count must be positive")
    if schema_version != 4:
        raise ValueError("schema_version must be 4")
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "Read Performance Fixture",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    authority_service = workspace._project_authority_service()
    descriptor = authority_service.new_local_descriptor(
        authority_id="p2p-test-project-authority",
        display_name="Read performance fixture authority",
    )
    authority_service.path.write_bytes(authority_service.descriptor_bytes(descriptor))

    proposal_ids = tuple(f"PROP-{number:03d}" for number in range(1, proposal_count + 1))
    iteration = reversed(proposal_ids) if reverse_enumeration else iter(proposal_ids)
    codec = ProposalDecisionLedgerCodec()
    for proposal_id in iteration:
        number = int(proposal_id.split("-", 1)[1])
        proposal_dir = root / ".p2p/proposals" / f"{proposal_id}-scale-fixture"
        state = _state_for(number)
        ledger = codec.empty(proposal_id)
        if state != ProposalDecisionEffectiveState.undecided:
            ledger, _ = append_event(
                ledger,
                event_type=ProposalDecisionEventType(state.value),
                effective_state=state,
                conditions=(
                    (
                        ProposalDecisionCondition(
                            condition_id=f"COND-{proposal_id}-001",
                            text="Complete the deterministic scale condition.",
                        ),
                    )
                    if state == ProposalDecisionEffectiveState.accepted_with_changes
                    else ()
                ),
            )
        write_current_proposal(proposal_dir, ledger)
        (proposal_dir / "decision.md").write_text(
            render_decision_projection(
                proposal_id,
                ledger.events[-1] if ledger.events else None,
                empty_state=ledger.effective_state,
            ),
            encoding="utf-8",
        )
        if number <= rich_proposals:
            _write_rich_artifacts(root, proposal_dir, proposal_id, number)

    _write_project_relations(root, proposal_ids)
    return ScaleWorkspace(
        root=root,
        proposal_ids=proposal_ids,
        schema_version=schema_version,
        rich_proposals=min(rich_proposals, proposal_count),
    )


def _state_for(number: int) -> ProposalDecisionEffectiveState:
    states = (
        ProposalDecisionEffectiveState.accepted,
        ProposalDecisionEffectiveState.accepted_with_changes,
        ProposalDecisionEffectiveState.rejected,
        ProposalDecisionEffectiveState.deferred,
        ProposalDecisionEffectiveState.undecided,
    )
    return states[(number - 1) % len(states)]


def _write_rich_artifacts(root: Path, proposal_dir: Path, proposal_id: str, number: int) -> None:
    if number % 3 == 0:
        coverage = {
            "vertical_coverage": {
                "schema_version": 2,
                "proposal_id": proposal_id,
                "vertical_id": "software_project",
                "sections": [
                    {
                        "id": "data_model" if number % 2 else "product_scope",
                        "relevance": "direct",
                        "rationale": "Deterministic declared scale evidence.",
                        "source": "owner_review",
                        "provenance": {"evidence": ["proposal.md"]},
                    }
                ],
                "provenance": {
                    "operation_id": f"proposal-vertical-coverage:{proposal_id}",
                    "actor": "owner",
                    "authority": "owner_confirmed",
                    "source": "owner_review",
                },
            }
        }
        (proposal_dir / "vertical-coverage.yml").write_text(
            yaml.safe_dump(coverage, sort_keys=False),
            encoding="utf-8",
        )
    (proposal_dir / "impact-map.yml").write_text(
        yaml.safe_dump(
            {
                "impact": {
                    "capabilities": [f"capability-{number:03d}"],
                    "surfaces": ["cli" if number % 2 else "mcp"],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_project_relations(root: Path, proposal_ids: tuple[str, ...]) -> None:
    if len(proposal_ids) < 2:
        return
    choice_dir = root / ".p2p/choices/CHOICE-001-scale"
    choice_dir.mkdir(parents=True, exist_ok=True)
    (choice_dir / "choice.md").write_text(
        "# CHOICE-001\n\n## Status\n\n`open`\n",
        encoding="utf-8",
    )
    changes_dir = root / ".p2p/changes/CHANGE-001-scale"
    changes_dir.mkdir(parents=True, exist_ok=True)
    (changes_dir / "change.md").write_text(
        "# CHANGE-001\n\n## Status\n\n`implementation_ready`\n",
        encoding="utf-8",
    )
    conflicts_path = root / ".p2p/project/conflicts.yml"
    conflicts_path.write_text(
        yaml.safe_dump(
            {
                "conflicts": [
                    {
                        "proposals": list(proposal_ids[:2]),
                        "status": "unresolved",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

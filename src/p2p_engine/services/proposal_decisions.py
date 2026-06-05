from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

from p2p_engine.core.decision import Decision, DecisionOutcome
from p2p_engine.foundation.markdown import replace_section


class ProposalDecisionService:
    def __init__(self, *, root: Path, p2p_dir: Path, find_proposal_dir: Callable[[str], Path]) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir

    def record(
        self,
        proposal_id: str,
        outcome: DecisionOutcome,
        reason: str,
        approver: str,
    ) -> Decision:
        proposal_dir = self.find_proposal_dir(proposal_id)
        decided_on = date.today()
        (proposal_dir / "decision.md").write_text(
            decision_markdown(
                proposal_id=proposal_id,
                outcome=outcome,
                reason=reason,
                approver=approver,
                decided_on=decided_on,
            ),
            encoding="utf-8",
        )
        proposal_path = proposal_dir / "proposal.md"
        proposal_path.write_text(
            replace_section(proposal_path.read_text(encoding="utf-8"), "Status", f"`{outcome.value}`"),
            encoding="utf-8",
        )
        return Decision(proposal_id, outcome, reason, approver, decided_on)


def decision_markdown(
    *,
    proposal_id: str,
    outcome: DecisionOutcome,
    reason: str,
    approver: str,
    decided_on: date,
) -> str:
    return (
        f"# Decision - {proposal_id}\n\n"
        "## Status\n\n"
        f"`{outcome.value}`\n\n"
        "## Outcome\n\n"
        f"{outcome.value}\n\n"
        "## Reason\n\n"
        f"{reason}\n\n"
        "## Date\n\n"
        f"{decided_on.isoformat()}\n\n"
        "## Approver\n\n"
        f"{approver}\n"
    )

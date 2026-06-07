from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

import yaml


@dataclass(frozen=True)
class GovernanceStatus:
    mode: str
    roles_count: int
    precedents_count: int
    governance_file: Path


@dataclass(frozen=True)
class VoteStatus:
    proposal_id: str
    counts: dict[str, int]
    total_votes: int
    winner: str | None
    tied: bool


def _yaml_dump(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def _read_yaml_mapping(path: Path, default: dict[str, object]) -> dict[str, object]:
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else default


class GovernanceService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir

    def init_governance(self, mode: str) -> list[Path]:
        allowed_modes = {"owner_decides", "open_consensus", "exclusive_vote"}
        if mode not in allowed_modes:
            raise ValueError(f"Unsupported governance mode: {mode}")
        governance_dir = self.p2p_dir / "governance"
        governance_dir.mkdir(parents=True, exist_ok=True)
        files: dict[Path, str] = {
            governance_dir / "governance.yml": _yaml_dump(
                {
                    "governance": {
                        "mode": mode,
                        "status": "active",
                        "enforcement": "audit_only",
                        "default_decision_type": mode,
                    }
                }
            ),
            governance_dir / "roles.yml": _yaml_dump(
                {
                    "roles": [
                        {
                            "id": "owner",
                            "description": "Project owner or maintainer",
                            "can_decide": True,
                        }
                    ]
                }
            ),
            governance_dir / "decision-precedents.yml": _yaml_dump({"precedents": []}),
        }
        written: list[Path] = []
        for path, content in files.items():
            path.write_text(content, encoding="utf-8")
            written.append(path.relative_to(self.root))
        return written

    def governance_status(self) -> GovernanceStatus:
        governance_file = self.p2p_dir / "governance" / "governance.yml"
        roles_file = self.p2p_dir / "governance" / "roles.yml"
        precedents_file = self.p2p_dir / "governance" / "decision-precedents.yml"

        governance = _read_yaml_mapping(governance_file, default={})
        roles = _read_yaml_mapping(roles_file, default={})
        precedents = _read_yaml_mapping(precedents_file, default={})

        governance_data = governance.get("governance", {})
        return GovernanceStatus(
            mode=governance_data.get("mode", "not_initialized") if isinstance(governance_data, dict) else "not_initialized",
            roles_count=len(roles.get("roles", [])) if isinstance(roles.get("roles"), list) else 0,
            precedents_count=(
                len(precedents.get("precedents", []))
                if isinstance(precedents.get("precedents"), list)
                else 0
            ),
            governance_file=governance_file.relative_to(self.root),
        )

    def record_vote(
        self,
        proposal_id: str,
        choice: str,
        reason: str,
        voter: str,
        role: str,
    ) -> VoteStatus:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "votes.yml"
        data = _read_yaml_mapping(path, default=self._default_votes_payload(proposal_id, result={"winner": None, "decided_on": None, "decision_precedent": None}))
        votes = data.setdefault("votes", [])
        if not isinstance(votes, list):
            raise ValueError("Invalid votes.yml: expected `votes` list.")
        votes.append(
            {
                "voter": voter,
                "role": role,
                "choice": choice,
                "reason": reason,
                "recorded_on": date.today().isoformat(),
            }
        )
        status = vote_status_from_data(proposal_id, data)
        result = data.setdefault("result", {})
        if not isinstance(result, dict):
            result = {}
            data["result"] = result
        result["winner"] = status.winner
        result["tied"] = status.tied
        path.write_text(_yaml_dump(data), encoding="utf-8")
        return status

    def vote_status(self, proposal_id: str) -> VoteStatus:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "votes.yml"
        data = _read_yaml_mapping(path, default=self._default_votes_payload(proposal_id, result={}))
        return vote_status_from_data(proposal_id, data)

    def record_precedent(self, proposal_id: str, title: str, reason: str) -> Path:
        self.find_proposal_dir(proposal_id)
        path = self.p2p_dir / "governance" / "decision-precedents.yml"
        data = _read_yaml_mapping(path, default={"precedents": []})
        precedents = data.setdefault("precedents", [])
        if not isinstance(precedents, list):
            raise ValueError("Invalid decision-precedents.yml: expected `precedents` list.")
        precedent_id = f"DP{len(precedents) + 1:03d}"
        precedents.append(
            {
                "id": precedent_id,
                "proposal": proposal_id,
                "title": title,
                "reason": reason,
                "recorded_on": date.today().isoformat(),
            }
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(data), encoding="utf-8")
        return path.relative_to(self.root)

    def _default_votes_payload(self, proposal_id: str, *, result: dict[str, object]) -> dict[str, object]:
        return {
            "proposal": proposal_id,
            "decision_type": "exclusive_vote",
            "status": "open",
            "votes": [],
            "result": result,
        }


def vote_status_from_data(proposal_id: str, data: object) -> VoteStatus:
    if not isinstance(data, dict):
        raise ValueError("Invalid votes.yml: expected YAML mapping.")
    votes = data.get("votes", [])
    if not isinstance(votes, list):
        raise ValueError("Invalid votes.yml: expected `votes` list.")
    counts: dict[str, int] = {}
    for vote in votes:
        if not isinstance(vote, dict):
            continue
        choice = str(vote.get("choice", "")).strip()
        if choice:
            counts[choice] = counts.get(choice, 0) + 1
    winner = None
    tied = False
    if counts:
        highest = max(counts.values())
        winners = sorted(choice for choice, count in counts.items() if count == highest)
        tied = len(winners) > 1
        winner = None if tied else winners[0]
    return VoteStatus(
        proposal_id=proposal_id,
        counts=counts,
        total_votes=sum(counts.values()),
        winner=winner,
        tied=tied,
    )

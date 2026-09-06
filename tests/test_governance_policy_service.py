from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

import yaml

from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Governance Policy Project")
    return workspace


def _create_choice(
    workspace: P2PWorkspace,
    *,
    related: list[str] | None = None,
) -> None:
    workspace.create_choice(
        "Deployment Strategy",
        ["Blue", "Green"],
        related=related,
        problem="Choose the deployment strategy.",
        context="Deployment needs one stable governed direction.",
    )


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _snapshot_files(root: Path) -> dict[Path, str]:
    p2p_dir = root / ".p2p"
    return {
        path.relative_to(root): path.read_text(encoding="utf-8")
        for path in sorted(p2p_dir.rglob("*"))
        if path.is_file()
    }


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def test_choice_governance_preflight_returns_versioned_contract_without_writes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace)
    before = _snapshot_files(tmp_path)

    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="owner")
    payload = _jsonable(result)

    assert payload["schema_version"] == "governance-preflight/v1"
    assert set(payload) == {
        "schema_version",
        "target",
        "governance",
        "actor",
        "selection",
        "result",
        "blocking_errors",
        "warnings",
        "vote_summary",
        "blockers",
        "precedents",
    }
    assert payload["result"]["status"] == "ready"
    assert payload["result"]["can_finalize_normally"] is True
    assert _snapshot_files(tmp_path) == before


def test_choice_governance_preflight_warns_on_advisory_vote_conflict(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Vote Target")
    _create_choice(workspace, related=[proposal.proposal_id])
    workspace.record_vote(proposal.proposal_id, choice="A", reason="Prefer blue", voter="owner", role="owner")

    result = workspace.choice_governance_preflight("CHOICE-001", option="B", actor="owner")

    assert result.vote_summary.alignment == "conflicts"
    assert "P2P_GOV_VOTE_CONFLICT" in [warning.code for warning in result.warnings]
    assert result.blocking_errors == []
    assert result.result.status == "ready"


def test_choice_governance_preflight_blocks_non_owner_actor(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace)

    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="contributor")

    assert result.actor.role == "contributor"
    assert [error.code for error in result.blocking_errors] == ["P2P_GOV_NON_OWNER_ACTOR"]
    assert result.result.status == "blocked"


def test_choice_governance_preflight_reports_active_blocker_as_override_required(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Blocked Target")
    _create_choice(workspace, related=[proposal.proposal_id])
    workspace.block_choice("CHOICE-001", target=proposal.proposal_id, target_type="proposal", reason="Resolve first.")

    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="owner")

    assert [error.code for error in result.blocking_errors] == ["P2P_GOV_ACTIVE_BLOCKER"]
    assert result.result.status == "requires_owner_override"
    assert result.result.owner_override_allowed is True
    assert result.result.override_rationale_required is True
    assert result.blockers[0].target == proposal.proposal_id


def test_precedent_search_matches_only_explicit_fields(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_yaml(
        tmp_path / ".p2p" / "governance" / "decision-precedents.yml",
        {
            "precedents": [
                {
                    "id": "DP001",
                    "title": "Deployment precedent",
                    "related_proposals": ["PROP-001"],
                    "related_choices": ["CHOICE-001"],
                    "tags": ["deployment"],
                },
                {
                    "id": "DP002",
                    "title": "Similar deployment title",
                    "related_proposals": ["PROP-002"],
                    "tags": ["release"],
                },
            ]
        },
    )

    by_choice = workspace.search_decision_precedents(choice_id="CHOICE-001")
    by_tag = workspace.search_decision_precedents(tag="deployment")
    fuzzy = workspace.search_decision_precedents(tag="deployments")

    assert [(match.precedent_id, match.match_reason) for match in by_choice] == [
        ("DP001", "related_choice")
    ]
    assert [(match.precedent_id, match.match_reason) for match in by_tag] == [
        ("DP001", "tag")
    ]
    assert fuzzy == []


def test_choice_governance_preflight_warns_when_related_precedents_are_found(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Precedent Target")
    _create_choice(workspace, related=[proposal.proposal_id])
    _write_yaml(
        tmp_path / ".p2p" / "governance" / "decision-precedents.yml",
        {"precedents": [{"id": "DP001", "related_choices": ["CHOICE-001"]}]},
    )

    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="owner")

    assert [match.precedent_id for match in result.precedents] == ["DP001"]
    assert "P2P_GOV_RELATED_PRECEDENTS" in [warning.code for warning in result.warnings]
    assert result.blocking_errors == []


def test_choice_governance_preflight_reports_malformed_precedents_without_crashing(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace)
    _write_yaml(tmp_path / ".p2p" / "governance" / "decision-precedents.yml", {"precedents": {}})

    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="owner")

    assert result.precedents == []
    assert [error.code for error in result.blocking_errors] == ["P2P_GOV_MALFORMED_PRECEDENTS"]
    assert result.result.status == "blocked"


def test_choice_governance_preflight_reports_malformed_present_governance_without_defaulting(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace)
    _write_yaml(tmp_path / ".p2p" / "governance" / "governance.yml", {"governance": []})

    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="owner")

    assert result.governance.mode == "invalid"
    assert [error.code for error in result.blocking_errors] == ["P2P_GOV_MALFORMED_GOVERNANCE"]
    assert result.result.status == "blocked"


def test_governance_only_validation_reports_invalid_artifacts(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_yaml(tmp_path / ".p2p" / "governance" / "governance.yml", {"governance": {"mode": "unknown"}})
    _write_yaml(
        tmp_path / ".p2p" / "governance" / "decision-precedents.yml",
        {"precedents": [{"id": "DP001"}, {"id": "DP001"}]},
    )

    result = workspace.validate_governance_policy()

    assert result.ok is False
    assert [finding.code for finding in result.findings] == [
        "P2P250_INVALID_GOVERNANCE_MODE",
        "P2P252_DUPLICATE_DECISION_PRECEDENT",
    ]


def test_choice_governance_preflight_uses_permissions_as_sole_actor_authority(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace)
    _write_yaml(
        tmp_path / ".p2p" / "governance" / "roles.yml",
        {"roles": [{"id": "owner", "role": "contributor"}]},
    )

    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="owner")

    assert result.actor.source == ".p2p/project/permissions.yml"
    assert result.actor.role == "owner"
    assert "P2P_GOV_ROLE_MISMATCH" not in [warning.code for warning in result.warnings]


def test_choice_governance_preflight_does_not_consult_governance_roles(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace)
    _write_yaml(
        tmp_path / ".p2p" / "governance" / "roles.yml",
        {"roles": [{"description": "missing id"}]},
    )

    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="owner")

    assert result.actor.role == "owner"
    assert "P2P_GOV_UNKNOWN_ACTOR" not in [error.code for error in result.blocking_errors]


def test_choice_governance_preflight_rejects_missing_permissions_without_role_fallback(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace)
    (tmp_path / ".p2p" / "project" / "permissions.yml").unlink()
    _write_yaml(
        tmp_path / ".p2p" / "governance" / "roles.yml",
        {"roles": [{"id": "owner", "role": "owner"}]},
    )

    before = _snapshot_files(tmp_path)
    result = workspace.choice_governance_preflight("CHOICE-001", option="A", actor="owner")

    assert "P2P_GOV_PERMISSIONS_REQUIRED" in [error.code for error in result.blocking_errors]
    assert result.actor.role == "unknown"
    assert _snapshot_files(tmp_path) == before

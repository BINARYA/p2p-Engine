from __future__ import annotations

from dataclasses import dataclass

import pytest

from p2p_engine.services.project_assessment import ProjectAssessmentService
from p2p_engine.storage.filesystem import P2PWorkspace


@dataclass(frozen=True)
class _Validation:
    errors: int = 0
    warnings: int = 0


@dataclass(frozen=True)
class _Registry:
    stale: bool = False


@dataclass(frozen=True)
class _Item:
    status: str
    selected_option: str | None = None
    command: str = ""
    operational_brief_available: bool = False


@dataclass(frozen=True)
class _Maturity:
    status: str
    score: int


def _service(
    tmp_path,
    *,
    validation=None,
    registry=None,
    proposals=None,
    choices=None,
    changes=None,
    works=None,
    project_status=None,
    next_actions=None,
    maturity=None,
):
    return ProjectAssessmentService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        validate=validation or (lambda: _Validation()),
        registry_status=registry or (lambda: _Registry()),
        proposal_summaries=proposals or (lambda: [_Item("draft")]),
        choice_statuses=choices or (lambda: []),
        change_set_statuses=changes or (lambda: []),
        work_summaries=works or (lambda: []),
        project_state_status=project_status
        or (lambda **_: _Item("project", operational_brief_available=False)),
        next_actions=next_actions or (lambda limit=3: [_Item("next", command="p2p registry refresh")]),
        maturity_exists=lambda: maturity is not None,
        show_maturity=lambda: maturity,
    )


def test_project_assessment_service_computes_draft_only_assessment(tmp_path) -> None:
    service = _service(tmp_path)

    assessment = service.compute()

    assert assessment.completion_score < 100
    assert assessment.completion_status in {"needs_review", "at_risk"}
    assert assessment.confidence == "high"
    assert "Accept at least one proposal when the project direction is clear." in assessment.gaps
    assert assessment.suggested_actions == ["p2p registry refresh"]
    assert any(item["id"] == "accepted_proposals" for item in assessment.factors)


def test_project_assessment_service_handles_validation_and_registry_confidence(tmp_path) -> None:
    blocked = _service(tmp_path, validation=lambda: _Validation(errors=1), registry=lambda: _Registry(stale=False)).compute()
    stale = _service(tmp_path, validation=lambda: _Validation(), registry=lambda: _Registry(stale=True)).compute()

    assert blocked.completion_status == "blocked"
    assert blocked.confidence == "low"
    assert stale.confidence == "medium"


def test_project_assessment_reuses_next_actions_for_project_status(tmp_path) -> None:
    next_action_calls = 0
    status_snapshots: list[list[_Item]] = []

    def next_actions(limit: int = 3) -> list[_Item]:
        nonlocal next_action_calls
        next_action_calls += 1
        assert limit == 3
        return [_Item("next", command="p2p registry refresh")]

    def project_status(*, next_actions_snapshot: list[_Item]) -> _Item:
        status_snapshots.append(next_actions_snapshot)
        return _Item("project", operational_brief_available=True)

    assessment = _service(
        tmp_path,
        next_actions=next_actions,
        project_status=project_status,
    ).compute()

    assert next_action_calls == 1
    assert status_snapshots == [
        [_Item("next", command="p2p registry refresh")]
    ]
    assert assessment.suggested_actions == ["p2p registry refresh"]


def test_project_assessment_service_persists_shows_and_includes_maturity(tmp_path) -> None:
    service = _service(tmp_path, maturity=_Maturity("ready", 87))

    refreshed = service.refresh()
    shown = service.show()

    assert refreshed.maturity_status == "ready"
    assert refreshed.maturity_score == 87
    assert shown.completion_score == refreshed.completion_score
    assert shown.path.as_posix() == ".p2p/project/assessment.yml"
    payload = (tmp_path / ".p2p" / "project" / "assessment.yml").read_text(encoding="utf-8")
    assert "assessment_type: deterministic_readiness" in payload
    assert "completion:" in payload
    assert "maturity:" in payload


def test_project_assessment_service_show_requires_refresh(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="Project assessment not found"):
        service.show()


def test_workspace_project_assessment_facade_delegates(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Assessment Facade")
    workspace.create_proposal("Draft Work")
    workspace.refresh_registries()

    refreshed = workspace.refresh_project_assessment()
    shown = workspace.show_project_assessment()

    assert refreshed.completion_score == shown.completion_score
    assert shown.path.as_posix() == ".p2p/project/assessment.yml"

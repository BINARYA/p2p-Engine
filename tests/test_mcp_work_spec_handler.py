from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from p2p_engine.mcp.handlers import work_specs
from p2p_engine.cli import app
from p2p_engine.mcp.handlers.work_specs import handle_work_spec_tool
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace, WorkAcceptConflict

runner = CliRunner()


@dataclass(frozen=True)
class FakeWorkBranch:
    work_id: str = "WORK-001"
    branch_name: str = "p2p/work/WORK-001-demo"
    base_branch: str = "main"
    base_commit: str = "base"
    head_commit: str = "head"
    path: Path = Path(".p2p/work/WORK-001")


@dataclass(frozen=True)
class FakeWorkSubmit:
    work_id: str = "WORK-001"
    branch_name: str = "p2p/work/WORK-001-demo"
    commit: str = "submit"
    changed_files: list[str] | None = None
    path: Path = Path(".p2p/work/WORK-001")


@dataclass(frozen=True)
class FakeWorkReview:
    work_id: str = "WORK-001"
    branch_name: str = "p2p/work/WORK-001-demo"
    review_commit: str = "review"
    metadata_commit: str = "review-meta"
    path: Path = Path(".p2p/work/WORK-001")


@dataclass(frozen=True)
class FakeWorkPublish:
    work_id: str = "WORK-001"
    branch_name: str = "p2p/work/WORK-001-demo"
    remote: str = "origin"
    remote_url: str = "/tmp/demo.git"
    publish_commit: str = "publish"
    path: Path = Path(".p2p/work/WORK-001")


@dataclass(frozen=True)
class FakeWorkReviewRequest:
    work_id: str = "WORK-001"
    branch_name: str = "p2p/work/WORK-001-demo"
    provider: str = "generic"
    remote: str = "origin"
    remote_url: str = "/tmp/demo.git"
    metadata_commit: str = "request-review"
    suggested_next: str = "Ask for external review."
    path: Path = Path(".p2p/work/WORK-001")


@dataclass(frozen=True)
class FakeWorkAccept:
    work_id: str = "WORK-001"
    branch_name: str = "p2p/work/WORK-001-demo"
    base_branch: str = "main"
    merge_commit: str = "merge"
    path: Path = Path(".p2p/work/WORK-001")


@dataclass(frozen=True)
class FakeWorkFinalize:
    work_id: str = "WORK-001"
    base_branch: str = "main"
    remote: str = "origin"
    remote_url: str = "/tmp/demo.git"
    finalize_commit: str = "finalize"
    path: Path = Path(".p2p/work/WORK-001")


@dataclass(frozen=True)
class FakeWorkCleanup:
    work_id: str = "WORK-001"
    branch_name: str = "p2p/work/WORK-001-demo"
    base_branch: str = "main"
    remote: str = "origin"
    cleanup_commit: str = "cleanup"
    local_deleted: bool = True
    remote_deleted: bool = False
    path: Path = Path(".p2p/work/WORK-001")


class FakeWorkLifecycleWorkspace:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.validations: list[tuple[str, str, str, str]] = []
        self.error_receipts: list[tuple[str, str, dict[str, object]]] = []
        self.accept_result: object = FakeWorkAccept()

    def branch_work(self, work_id: str) -> FakeWorkBranch:
        self.calls.append(("branch_work", work_id))
        return FakeWorkBranch(work_id=work_id)

    def submit_work(self, work_id: str) -> FakeWorkSubmit:
        self.calls.append(("submit_work", work_id))
        return FakeWorkSubmit(work_id=work_id, changed_files=["src/demo.py"])

    def review_work(self, work_id: str) -> FakeWorkReview:
        self.calls.append(("review_work", work_id))
        return FakeWorkReview(work_id=work_id)

    def publish_work(self, work_id: str, remote: str = "origin") -> FakeWorkPublish:
        self.calls.append(("publish_work", (work_id, remote)))
        return FakeWorkPublish(work_id=work_id, remote=remote)

    def request_external_work_review(
        self,
        work_id: str,
        provider: str | None = None,
    ) -> FakeWorkReviewRequest:
        self.calls.append(("request_external_work_review", (work_id, provider)))
        return FakeWorkReviewRequest(work_id=work_id, provider=provider or "generic")

    def accept_work(self, work_id: str) -> object:
        self.calls.append(("accept_work", work_id))
        return self.accept_result

    def finalize_work(self, work_id: str, remote: str = "origin") -> FakeWorkFinalize:
        self.calls.append(("finalize_work", (work_id, remote)))
        return FakeWorkFinalize(work_id=work_id, remote=remote)

    def cleanup_work(
        self,
        work_id: str,
        delete_remote: bool = False,
        remote: str = "origin",
    ) -> FakeWorkCleanup:
        self.calls.append(("cleanup_work", (work_id, delete_remote, remote)))
        return FakeWorkCleanup(work_id=work_id, remote=remote, remote_deleted=delete_remote)

    def consent_validate(
        self,
        consent_id: str,
        *,
        operation: str,
        target: str,
        actor_id: str,
    ) -> dict[str, object]:
        self.validations.append((consent_id, operation, target, actor_id))
        return {"consent_id": consent_id, "status": "granted"}

    def consent_mark_used_with_error(
        self,
        consent_id: str,
        *,
        error: str,
        result: dict[str, object],
    ) -> dict[str, object]:
        self.error_receipts.append((consent_id, error, result))
        return {"consent_id": consent_id, "status": "used_with_error", "result": result}


def _setup_project(tmp_path: Path) -> P2PWorkspace:
    call_tool("p2p_init_project", {"root": str(tmp_path), "name": "Demo Project", "domain": "software"})
    call_tool(
        "p2p_proposal_create",
        {
            "root": str(tmp_path),
            "title": "Work Spec Proposal",
            "problem": "Need work spec handler coverage.",
            "proposal": "Route spec and work tools outside the facade.",
            "acceptance_criteria": ["Spec export can be generated."],
        },
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    return P2PWorkspace(tmp_path)


def test_mcp_work_spec_handler_returns_none_for_other_domains(tmp_path: Path) -> None:
    workspace = _setup_project(tmp_path)

    assert handle_work_spec_tool(workspace, "p2p_context", {}) is None


def test_mcp_work_spec_handler_serves_prompts(tmp_path: Path) -> None:
    workspace = _setup_project(tmp_path)

    prompt = handle_work_spec_tool(workspace, "p2p_explore_prompt", {"proposal_id": "PROP-001"})
    spec_prompt = handle_work_spec_tool(workspace, "p2p_spec_prompt", {"change_id": "CHANGE-001"})

    assert prompt is not None
    assert prompt["explore_prompt"]["path"] == ".p2p/prompts/PROP-001/explore.prompt.md"
    assert spec_prompt is not None
    assert spec_prompt["spec_prompt"]["prompt_path"] == (
        ".p2p/outputs/software-spec/CHANGE-001/spec-refine.prompt.md"
    )


def test_mcp_work_spec_handler_serves_spec_export_and_work_flow(tmp_path: Path) -> None:
    workspace = _setup_project(tmp_path)

    lifecycle = handle_work_spec_tool(
        workspace,
        "p2p_spec_lifecycle",
        {"intent": "implementation_spec", "change_id": "CHANGE-001"},
    )
    spec = handle_work_spec_tool(workspace, "p2p_spec_refresh", {"change_id": "CHANGE-001"})
    export = handle_work_spec_tool(workspace, "p2p_spec_export", {"change_id": "CHANGE-001", "target": "generic"})
    validation = handle_work_spec_tool(
        workspace,
        "p2p_spec_export_validate",
        {"change_id": "CHANGE-001", "target": "generic"},
    )
    work = handle_work_spec_tool(workspace, "p2p_work_plan", {"change_id": "CHANGE-001", "target": "generic"})
    work_show = handle_work_spec_tool(workspace, "p2p_work_show", {"work_id": "WORK-001"})

    assert lifecycle is not None
    assert lifecycle["lifecycle"]["route"] == "preflight_change_set_then_refresh_software_spec"
    assert lifecycle["lifecycle"]["blockers"] == []
    assert lifecycle["lifecycle"]["advisories"][0]["code"] == "software_vertical_not_active"
    assert spec is not None
    assert spec["spec"]["status"] == "generated"
    assert spec["spec"]["lifecycle"]["route"] == "preflight_change_set_then_refresh_software_spec"
    assert export is not None
    assert export["export"]["status"] == "exported"
    assert export["export"]["lifecycle"]["route"] == "preflight_spec_then_export_target"
    assert validation is not None
    assert validation["validation"]["target"] == "generic"
    assert work is not None
    assert work["work"]["work_id"] == "WORK-001"
    assert work_show is not None
    assert work_show["work"]["change_id"] == "CHANGE-001"


def test_mcp_call_tool_uses_work_spec_handler(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    result = call_tool("p2p_change_show", {"root": str(tmp_path), "change_id": "CHANGE-001"})

    assert result["change"]["change_id"] == "CHANGE-001"


def test_mcp_work_lifecycle_preparatory_handlers_dispatch_and_return_governance() -> None:
    workspace = FakeWorkLifecycleWorkspace()

    branched = handle_work_spec_tool(workspace, "p2p_work_branch", {"work_id": "WORK-001"})
    submitted = handle_work_spec_tool(workspace, "p2p_work_submit", {"work_id": "WORK-001"})
    reviewed = handle_work_spec_tool(workspace, "p2p_work_review", {"work_id": "WORK-001"})

    assert branched is not None
    assert branched["work_branch"]["work_id"] == "WORK-001"
    assert branched["governance"]["owner_decision_required"] is False
    assert submitted is not None
    assert submitted["work_submit"]["changed_files"] == ["src/demo.py"]
    assert submitted["governance"]["merge_performed"] is False
    assert reviewed is not None
    assert reviewed["work_review"]["metadata_commit"] == "review-meta"
    assert reviewed["governance"]["cleanup_performed"] is False
    assert workspace.calls == [
        ("branch_work", "WORK-001"),
        ("submit_work", "WORK-001"),
        ("review_work", "WORK-001"),
    ]


def test_mcp_work_lifecycle_gated_handlers_validate_consent_and_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = FakeWorkLifecycleWorkspace()
    consumed: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_consume(
        _workspace: FakeWorkLifecycleWorkspace,
        consent_id: str,
        *,
        result: dict[str, object],
        push_remote: str | None = None,
        push_branch_name: str | None = None,
    ) -> dict[str, object]:
        consumed.append((consent_id, result, push_remote, push_branch_name))
        return {"consent_id": consent_id, "status": "consumed", "result": result}

    monkeypatch.setattr(work_specs, "safe_head", lambda _workspace: "head-before")
    monkeypatch.setattr(work_specs, "consume_consent_with_audit", fake_consume)

    published = handle_work_spec_tool(
        workspace,
        "p2p_work_publish",
        {"work_id": "WORK-001", "actor_id": "lorenzo", "consent_id": "CONSENT-001", "remote": "upstream"},
    )
    review_requested = handle_work_spec_tool(
        workspace,
        "p2p_work_request_review",
        {"work_id": "WORK-001", "actor_id": "lorenzo", "consent_id": "CONSENT-002", "provider": "github"},
    )
    accepted = handle_work_spec_tool(
        workspace,
        "p2p_work_accept",
        {"work_id": "WORK-001", "actor_id": "lorenzo", "consent_id": "CONSENT-003"},
    )
    finalized = handle_work_spec_tool(
        workspace,
        "p2p_work_finalize",
        {"work_id": "WORK-001", "actor_id": "lorenzo", "consent_id": "CONSENT-004", "remote": "upstream"},
    )
    cleaned = handle_work_spec_tool(
        workspace,
        "p2p_work_cleanup",
        {
            "work_id": "WORK-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-005",
            "delete_remote": True,
            "remote": "upstream",
        },
    )

    assert published is not None
    assert published["work_publish"]["remote"] == "upstream"
    assert published["governance"]["published"] is True
    assert review_requested is not None
    assert review_requested["work_review_request"]["provider"] == "github"
    assert review_requested["governance"]["external_review_requested"] is True
    assert accepted is not None
    assert accepted["work_accept"]["merge_commit"] == "merge"
    assert accepted["governance"]["merge_performed"] is True
    assert accepted["governance"]["finalized"] is False
    assert finalized is not None
    assert finalized["work_finalize"]["remote"] == "upstream"
    assert finalized["governance"]["finalized"] is True
    assert finalized["governance"]["cleanup_performed"] is False
    assert cleaned is not None
    assert cleaned["work_cleanup"]["remote_deleted"] is True
    assert cleaned["governance"]["cleanup_performed"] is True
    assert workspace.validations == [
        ("CONSENT-001", "work_publish", "WORK-001", "lorenzo"),
        ("CONSENT-002", "work_request_review", "WORK-001", "lorenzo"),
        ("CONSENT-003", "work_accept", "WORK-001", "lorenzo"),
        ("CONSENT-004", "work_finalize", "WORK-001", "lorenzo"),
        ("CONSENT-005", "work_cleanup", "WORK-001", "lorenzo"),
    ]
    assert [(item[0], item[2], item[3]) for item in consumed] == [
        ("CONSENT-001", "upstream", "p2p/work/WORK-001-demo"),
        ("CONSENT-002", "origin", "p2p/work/WORK-001-demo"),
        ("CONSENT-003", None, None),
        ("CONSENT-004", "upstream", "main"),
        ("CONSENT-005", "upstream", "main"),
    ]
    assert consumed[0][1]["operation"] == "work_publish"
    assert consumed[1][1]["opens_external_request"] is False
    assert consumed[2][1]["merge_commit"] == "merge"
    assert consumed[3][1]["finalize_commit"] == "finalize"
    assert consumed[4][1]["remote_deleted"] is True


def test_mcp_work_accept_conflict_marks_consent_used_with_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = FakeWorkLifecycleWorkspace()
    workspace.accept_result = WorkAcceptConflict(
        work_id="WORK-001",
        branch_name="p2p/work/WORK-001-demo",
        base_branch="main",
        conflicted_files=["src/demo.py"],
        path=Path(".p2p/work/WORK-001"),
    )
    heads = iter(["head-before", "head-after"])
    monkeypatch.setattr(work_specs, "safe_head", lambda _workspace: next(heads))

    result = handle_work_spec_tool(
        workspace,
        "p2p_work_accept",
        {"work_id": "WORK-001", "actor_id": "lorenzo", "consent_id": "CONSENT-001"},
    )

    assert result is not None
    assert result["work_accept_conflict"]["conflicted_files"] == ["src/demo.py"]
    assert result["governance"]["manual_resolution_required"] is True
    assert result["governance"]["merge_performed"] is False
    assert result["consent"]["status"] == "used_with_error"
    assert workspace.error_receipts == [
        (
            "CONSENT-001",
            "merge_conflict",
            {
                "operation": "work_accept",
                "target": "WORK-001",
                "actor_id": "lorenzo",
                "branch": "p2p/work/WORK-001-demo",
                "base_branch": "main",
                "conflicted_files": ["src/demo.py"],
                "head_before": "head-before",
                "head_after": "head-after",
            },
        )
    ]

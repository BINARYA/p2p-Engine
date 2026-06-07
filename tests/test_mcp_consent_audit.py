from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from p2p_engine.mcp import consent_audit


@dataclass(frozen=True)
class FakeSyncStatus:
    branch: str | None = "main"
    remote: str | None = "origin"


class FakeWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.sync = FakeSyncStatus()
        self.consumed: list[tuple[str, dict[str, object]]] = []
        self.errors: list[tuple[str, str, dict[str, object]]] = []

    def sync_status(self, _remote: str | None = None) -> FakeSyncStatus:
        return self.sync

    def consent_consume(self, consent_id: str, *, result: dict[str, object]) -> dict[str, object]:
        self.consumed.append((consent_id, result))
        return {"consent_id": consent_id, "status": "consumed", "result": result}

    def consent_mark_used_with_error(
        self,
        consent_id: str,
        *,
        error: str,
        result: dict[str, object],
    ) -> dict[str, object]:
        self.errors.append((consent_id, error, result))
        return {"consent_id": consent_id, "status": "used_with_error", "result": result}


def test_sync_consent_target_uses_selected_remote_and_branch(tmp_path: Path) -> None:
    workspace = FakeWorkspace(tmp_path)
    workspace.sync = FakeSyncStatus(branch="feature", remote="origin")

    assert consent_audit.sync_consent_target(workspace, "upstream") == "upstream/feature"


def test_sync_consent_target_rejects_detached_head(tmp_path: Path) -> None:
    workspace = FakeWorkspace(tmp_path)
    workspace.sync = FakeSyncStatus(branch=None, remote="origin")

    with pytest.raises(ValueError, match="Cannot resolve sync consent target from detached HEAD"):
        consent_audit.sync_consent_target(workspace, None)


def test_consume_consent_with_audit_commits_and_pushes_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = FakeWorkspace(tmp_path)
    commits: list[tuple[Path, str]] = []
    pushes: list[tuple[Path, str, str]] = []
    monkeypatch.setattr(consent_audit, "commit_all", lambda root, message: commits.append((root, message)) or "commit")
    monkeypatch.setattr(consent_audit, "push_branch", lambda root, branch, remote: pushes.append((root, branch, remote)) or True)

    consumed = consent_audit.consume_consent_with_audit(
        workspace,
        "CONSENT-001",
        result={"ok": True},
        push_remote="origin",
        push_branch_name="main",
    )

    assert consumed["status"] == "consumed"
    assert workspace.consumed == [("CONSENT-001", {"ok": True})]
    assert commits == [(tmp_path, "P2P consent consume CONSENT-001")]
    assert pushes == [(tmp_path, "main", "origin")]


def test_commit_and_push_consent_audit_reports_commit_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = FakeWorkspace(tmp_path)
    monkeypatch.setattr(consent_audit, "commit_all", lambda _root, _message: None)

    with pytest.raises(ValueError, match="Failed to commit consent consumption audit for CONSENT-001"):
        consent_audit.commit_and_push_consent_audit(workspace, "CONSENT-001")


def test_commit_and_push_consent_audit_reports_push_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = FakeWorkspace(tmp_path)
    monkeypatch.setattr(consent_audit, "commit_all", lambda _root, _message: "commit")
    monkeypatch.setattr(consent_audit, "push_branch", lambda _root, _branch, _remote: False)

    with pytest.raises(ValueError, match="Failed to push consent consumption audit for CONSENT-001"):
        consent_audit.commit_and_push_consent_audit(
            workspace,
            "CONSENT-001",
            push_remote="origin",
            push_branch_name="main",
        )


def test_mark_consent_error_on_head_change_marks_only_when_head_changed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = FakeWorkspace(tmp_path)
    monkeypatch.setattr(consent_audit, "safe_head", lambda _workspace: "after")

    consent_audit.mark_consent_error_on_head_change(
        workspace,
        "CONSENT-001",
        "before",
        "failed",
        "sync_push",
        "origin/main",
        "lorenzo",
    )

    assert workspace.errors == [
        (
            "CONSENT-001",
            "failed",
            {
                "operation": "sync_push",
                "target": "origin/main",
                "actor_id": "lorenzo",
                "head_before": "before",
                "head_after": "after",
            },
        )
    ]

    workspace.errors.clear()
    monkeypatch.setattr(consent_audit, "safe_head", lambda _workspace: "before")
    consent_audit.mark_consent_error_on_head_change(
        workspace,
        "CONSENT-001",
        "before",
        "failed",
        "sync_push",
        "origin/main",
        "lorenzo",
    )
    assert workspace.errors == []

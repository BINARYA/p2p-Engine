from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.authority import (
    AuthorityBasis,
    AuthorityClaim,
    AuthorityContext,
    AuthorityIdentity,
    AuthorityIdentityKind,
    AuthorityMode,
    AuthorityProjectBinding,
)
from p2p_engine.core.project_memory import (
    MEMORY_CLASSIFICATION_CONTRACT,
    PROJECT_MEMORY_SCOPE_CONTRACT,
    MemoryClassificationItem,
    MemoryClassificationSnapshot,
    ProjectMemoryScopeKind,
)
from p2p_engine.core.project_questions import (
    ProjectQuestionApplicability,
    ProjectQuestionState,
)
from p2p_engine.core.project_structure import with_project_structure_checksum
from p2p_engine.core.proposal_decision_events import ProposalDecisionEventType
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from tests.cli_assertions import cli_data


runner = CliRunner()


def _workspace(root: Path, *, starter: str = "generic") -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "Classified Memory",
        owner="owner",
        starter_id=starter,
    )
    return workspace


def _assign(
    workspace: P2PWorkspace,
    proposal_id: str,
    *,
    kind: str,
    section_ids: list[str] | None = None,
    key: str = "memory-scope-12345678",
    context: AuthorityContext | None = None,
):
    structure = workspace.project_structure(include_retired=True)
    actor = context.subject.identity_id if context is not None else "owner"
    executor = context.executor.identity_id if context is not None else "owner"
    executor_kind = context.executor.kind.value if context is not None else "person"
    return workspace.assign_proposal_memory_scope(
        proposal_id=proposal_id,
        kind=kind,
        section_ids=section_ids or [],
        operation_key=key,
        expected_memory_revision=workspace.project_memory_revision(),
        expected_structure_revision=structure.revision,
        actor_id=actor,
        executor_id=executor,
        executor_kind=executor_kind,
        authority_context=context,
    )


def _decision_preview(
    workspace: P2PWorkspace,
    proposal_id: str,
    event_type: ProposalDecisionEventType = ProposalDecisionEventType.accepted,
    *,
    context: AuthorityContext | None = None,
):
    actor = context.subject.identity_id if context is not None else "owner"
    executor = context.executor.identity_id if context is not None else actor
    executor_kind = context.executor.kind.value if context is not None else "person"
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal_id,
        event_type=event_type,
        reason="Explicitly governed outcome.",
        actor_id=actor,
        executor_actor_id=executor,
        executor_kind=executor_kind,
        authority_context=context,
    )
    return service.preview(request)


def _external_context(capability: str, *, decision_id: str) -> AuthorityContext:
    return AuthorityContext(
        mode=AuthorityMode.external_attestation,
        project_authority=AuthorityProjectBinding(
            authority_id="hosted-authority-01",
            generation=1,
            provider_id="hosted-provider",
            provider_policy_version="project-capabilities-v1",
        ),
        subject=AuthorityIdentity("hosted-owner-01", AuthorityIdentityKind.user),
        executor=AuthorityIdentity("hosted-client-01", AuthorityIdentityKind.mcp_client),
        authorization_decision_id=decision_id,
        authorized_at="2026-08-26T12:00:00Z",
        claims=(
            AuthorityClaim(
                capability=capability,
                basis=AuthorityBasis.root_authority,
                authority_generation=1,
            ),
        ),
    )


def test_empty_project_accepts_unassigned_proposal_and_reports_incomplete_memory(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    proposal = workspace.create_proposal("First unclassified idea")

    scope = workspace.proposal_memory_scope(proposal.proposal_id)
    classification = workspace.project_memory_classification()

    assert workspace.project_structure().sections == ()
    assert scope.contract == PROJECT_MEMORY_SCOPE_CONTRACT
    assert scope.kind == ProjectMemoryScopeKind.unassigned
    assert classification.status == "incomplete"
    assert classification.counts["active_total"] == 1
    assert classification.counts["unassigned"] == 1
    assert classification.counts["decision_blocking"] == 1
    assert classification.to_dict()["readiness_effect"] == "none"
    with pytest.raises(ValueError, match="P2P_PROJECT_MEMORY_SCOPE_DECISION_BLOCKED"):
        _decision_preview(workspace, proposal.proposal_id)


def test_missing_scope_is_invalid_instead_of_becoming_implicit_unassigned(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    proposal = workspace.create_proposal("Incomplete current memory")
    (tmp_path / proposal.path / "memory-scope.yml").unlink()

    with pytest.raises(ValueError, match="canonical scope or event ledger is missing"):
        workspace.proposal_memory_scope(proposal.proposal_id)

    classification = workspace.project_memory_classification()
    item = next(
        item
        for item in classification.items
        if item.object_id == proposal.proposal_id
    )
    assert classification.status == "unknown"
    assert item.state == "unknown"
    assert item.decision_blocking is True


def test_missing_scope_event_ledger_is_unknown_and_cannot_authorize(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Incomplete scope history")
    proposal_dir = tmp_path / proposal.path
    (proposal_dir / "memory-scope-events.yml").unlink()

    classification = workspace.project_memory_classification()
    item = next(
        item
        for item in classification.items
        if item.object_id == proposal.proposal_id
    )

    assert classification.status == "unknown"
    assert item.state == "unknown"
    with pytest.raises(ValueError, match="required decision source is missing"):
        _decision_preview(workspace, proposal.proposal_id)


def test_vertical_coverage_artifact_cannot_satisfy_current_scope_gate(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Old mapping is not scope authority")
    proposal_dir = tmp_path / proposal.path
    (proposal_dir / "vertical-coverage.yml").write_text(
        "vertical_coverage:\n  sections:\n    - section_id: vision\n",
        encoding="utf-8",
    )

    classification = workspace.project_memory_classification()
    item = next(
        item
        for item in classification.items
        if item.object_id == proposal.proposal_id
    )

    assert item.state == "unassigned"
    with pytest.raises(ValueError, match="P2P_PROJECT_MEMORY_SCOPE_DECISION_BLOCKED"):
        _decision_preview(workspace, proposal.proposal_id)


def test_multi_section_and_global_scope_are_atomic_and_unblock_decision(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Cross-cutting proposal")
    section_ids = list(workspace.project_structure().active_section_ids())[:2]
    before_progress = asdict(workspace.project_progress())

    assigned = _assign(
        workspace,
        proposal.proposal_id,
        kind="sections",
        section_ids=section_ids,
    )
    replay = workspace.assign_proposal_memory_scope(
        proposal_id=proposal.proposal_id,
        kind="sections",
        section_ids=section_ids,
        operation_key="memory-scope-12345678",
        expected_memory_revision=assigned.previous_memory_revision,
        expected_structure_revision=workspace.project_structure().revision,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    assert assigned.status == "applied"
    assert assigned.current.section_ids == tuple(section_ids)
    assert replay.status == "already_applied"
    assert workspace.project_memory_classification().status == "complete"
    assert _decision_preview(workspace, proposal.proposal_id).mutation.apply_allowed is True
    assert asdict(workspace.project_progress()) == before_progress

    global_result = _assign(
        workspace,
        proposal.proposal_id,
        kind="project_global",
        key="memory-global-12345678",
    )
    assert global_result.current.kind == ProjectMemoryScopeKind.project_global
    assert workspace.project_memory_classification().counts["project_global"] == 1


def test_authority_creating_decision_is_atomically_bound_to_scope_and_structure(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Scope-bound decision")
    _assign(workspace, proposal.proposal_id, kind="project_global")

    preview = _decision_preview(workspace, proposal.proposal_id)
    source_paths = {item.path for item in preview.mutation.source_preconditions}

    assert f"{proposal.path}/memory-scope.yml" in source_paths
    assert f"{proposal.path}/memory-scope-events.yml" in source_paths
    assert ".p2p/project/structure.yml" in source_paths

    _assign(
        workspace,
        proposal.proposal_id,
        kind="unassigned",
        key="memory-unassigned-12345678",
    )
    with pytest.raises(
        ValueError,
        match="P2P_PROJECT_MEMORY_SCOPE_DECISION_BLOCKED",
    ):
        workspace.apply_proposal_decision(
            preview.request,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )
    assert workspace.proposal_decision_status(proposal.proposal_id).effective_state.value == "undecided"


def test_scope_assignment_rejects_stale_revisions_and_divergent_replay(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Revision guarded proposal")
    old_memory = workspace.project_memory_revision()
    structure = workspace.project_structure()

    _assign(workspace, proposal.proposal_id, kind="project_global")
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        workspace.assign_proposal_memory_scope(
            proposal_id=proposal.proposal_id,
            kind="unassigned",
            section_ids=[],
            operation_key="memory-scope-12345678",
            expected_memory_revision=old_memory,
            expected_structure_revision=structure.revision,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )
    with pytest.raises(ValueError, match="P2P_PROJECT_MEMORY_SCOPE_STALE_MEMORY"):
        workspace.assign_proposal_memory_scope(
            proposal_id=proposal.proposal_id,
            kind="unassigned",
            section_ids=[],
            operation_key="memory-stale-12345678",
            expected_memory_revision=old_memory,
            expected_structure_revision=structure.revision,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )
    assert workspace.proposal_memory_scope(proposal.proposal_id).kind == ProjectMemoryScopeKind.project_global


def test_scope_assignment_rejects_stale_structure_revision(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Structure revision guarded proposal")

    with pytest.raises(ValueError, match="P2P_PROJECT_MEMORY_SCOPE_STALE_STRUCTURE"):
        workspace.assign_proposal_memory_scope(
            proposal_id=proposal.proposal_id,
            kind="project_global",
            section_ids=[],
            operation_key="memory-stale-structure-12345678",
            expected_memory_revision=workspace.project_memory_revision(),
            expected_structure_revision=workspace.project_structure().revision + 1,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )


def test_scope_assignment_rejects_structure_change_during_atomic_apply(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Concurrent structure guard")
    structure_path = tmp_path / ".p2p/project/structure.yml"
    changed = False

    def change_structure_after_first_check(stage: str, _target: str) -> None:
        nonlocal changed
        if stage == "after_source_recheck" and not changed:
            changed = True
            structure_path.write_bytes(structure_path.read_bytes() + b"\n")

    service = workspace._project_memory_service()
    service.atomic_writer = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=change_structure_after_first_check,
    )

    with pytest.raises(
        ValueError,
        match="P2P_PROJECT_MEMORY_SCOPE_MUTATION_FAILED",
    ):
        _assign(
            workspace,
            proposal.proposal_id,
            kind="project_global",
            key="memory-structure-race-12345678",
        )

    assert (
        workspace.proposal_memory_scope(proposal.proposal_id).kind
        == ProjectMemoryScopeKind.unassigned
    )
    assert workspace._mutation_receipt_service().read(
        idempotency_key="memory-structure-race-12345678"
    ) is None


def test_scope_mutation_failure_rolls_back_scope_event_and_receipt(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Atomic classification")
    proposal_dir = tmp_path / proposal.path
    scope_path = proposal_dir / "memory-scope.yml"
    events_path = proposal_dir / "memory-scope-events.yml"
    before_scope = scope_path.read_bytes()
    before_events = events_path.read_bytes()
    injected = False

    def fail_after_first_replace(stage: str, _target: str) -> None:
        nonlocal injected
        if stage == "after_replace" and not injected:
            injected = True
            raise RuntimeError("injected project-memory failure")

    service = workspace._project_memory_service()
    service.atomic_writer = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=fail_after_first_replace,
    )

    with pytest.raises(ValueError, match="P2P_PROJECT_MEMORY_SCOPE_MUTATION_FAILED"):
        _assign(
            workspace,
            proposal.proposal_id,
            kind="project_global",
            key="memory-failure-12345678",
        )

    assert scope_path.read_bytes() == before_scope
    assert events_path.read_bytes() == before_events
    assert workspace._mutation_receipt_service().read(
        idempotency_key="memory-failure-12345678"
    ) is None


def test_terminal_unassigned_proposal_is_historical_not_classification_debt(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    proposal = workspace.create_proposal("Rejected unclassified idea")
    preview = _decision_preview(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.rejected,
    )
    workspace.apply_proposal_decision(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    classification = workspace.project_memory_classification()

    assert classification.status == "not_applicable"
    assert classification.counts["active_total"] == 0
    assert classification.counts["historical"] == 1
    assert classification.counts["unassigned"] == 0


def test_active_scope_against_retired_section_requires_reassignment(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Retired target")
    current = workspace.project_structure(include_retired=True)
    target = current.active_section_ids()[0]
    _assign(
        workspace,
        proposal.proposal_id,
        kind="sections",
        section_ids=[target],
    )
    next_active_order = 0
    retired_sections = []
    for section in current.sections:
        if section.section_id == target:
            retired_sections.append(replace(section, lifecycle="retired"))
            continue
        retired_sections.append(replace(section, order=next_active_order))
        next_active_order += 1
    retired_sections.sort(
        key=lambda section: (section.lifecycle != "active", section.order, section.section_id)
    )
    retired = with_project_structure_checksum(
        replace(
            current,
            revision=current.revision + 1,
            checksum="0" * 64,
            sections=tuple(retired_sections),
        )
    )
    service = workspace._project_memory_service()
    service.project_structure = lambda: retired
    service.invalidate()

    classification = service.classification()
    item = next(item for item in classification.items if item.object_id == proposal.proposal_id)

    assert classification.status == "incomplete"
    assert item.state == "requires_reassignment"
    assert item.retired_section_ids == (target,)
    assert item.decision_blocking is True


def test_formal_question_uses_its_existing_structure_reference(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    question_service = workspace._project_question_state_service()
    artifact = workspace.project_questions()
    assert artifact.questions
    original = artifact.questions[0]
    question = replace(
        original,
        state=ProjectQuestionState.TO_ANSWER,
        applicability=ProjectQuestionApplicability.ACTIVE,
        answers=(),
        applications=(),
    )
    artifact = replace(
        artifact,
        questions=(question, *artifact.questions[1:]),
    )
    question_service.path.write_bytes(question_service.candidate_bytes(artifact))
    workspace._project_memory_service().invalidate()

    classification = workspace.project_memory_classification()
    item = next(
        item
        for item in classification.items
        if item.object_type == "formal_question"
    )

    assert item.object_id == question.question_id
    assert item.state == "section_classified"
    assert item.section_ids == (question.section_id,)
    assert item.decision_blocking is False
    assert classification.per_type["formal_question"]["section_classified"] >= 1


def test_classification_marks_result_stale_when_structure_changes_during_read(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Concurrent structure change")
    service = workspace._project_memory_service()
    current = workspace.project_structure(include_retired=True)
    changed = with_project_structure_checksum(
        replace(current, revision=current.revision + 1, checksum="0" * 64)
    )
    calls = 0

    def changing_structure():
        nonlocal calls
        calls += 1
        return current if calls == 1 else changed

    service.project_structure = changing_structure
    service.invalidate()

    classification = service.classification()

    assert classification.status == "stale"
    assert classification.diagnostics[-1]["code"] == "P2P_MEMORY_CLASSIFICATION_STALE"


def test_classification_public_collections_are_bounded() -> None:
    items = tuple(
        MemoryClassificationItem(
            object_type="proposal",
            object_id=f"PROP-{index + 1:03d}",
            lifecycle="undecided",
            state="unassigned",
            scope_kind="unassigned",
            decision_blocking=True,
        )
        for index in range(101)
    )
    snapshot = MemoryClassificationSnapshot(
        status="incomplete",
        structure_id="bounded-structure",
        structure_revision=1,
        structure_checksum="0" * 64,
        memory_revision="1" * 64,
        counts={"active_total": 101, "unassigned": 101},
        per_type={"proposal": {"active_total": 101, "unassigned": 101}},
        items=items,
    )

    payload = snapshot.to_dict(limit=10)

    assert payload["contract"] == MEMORY_CLASSIFICATION_CONTRACT
    assert payload["collections"]["unassigned"] == {
        "items": [item.to_dict() for item in items[:10]],
        "total": 101,
        "returned": 10,
        "truncated": True,
    }
    assert payload["truncated"] is True


def test_cli_snapshot_and_mcp_expose_the_same_scope_and_classification(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Public contract")
    consent = workspace.consent_grant(
        "project_memory_scope_set",
        f"proposal:{proposal.proposal_id}",
        "owner",
        approved_by="owner",
    )
    arguments = {
        "root": str(tmp_path),
        "proposal_id": proposal.proposal_id,
        "kind": "project_global",
        "section_ids": [],
        "expected_memory_revision": workspace.project_memory_revision(),
        "expected_structure_revision": workspace.project_structure().revision,
        "actor_id": "owner",
        "consent_id": consent.consent_id,
        "operation_key": "memory-mcp-12345678",
    }

    applied = call_tool("p2p_proposal_scope_set", arguments)
    replay = call_tool("p2p_proposal_scope_set", arguments)
    mcp_scope = call_tool(
        "p2p_proposal_scope_show",
        {"root": str(tmp_path), "proposal_id": proposal.proposal_id},
    )
    mcp_classification = call_tool(
        "p2p_project_memory_classification",
        {"root": str(tmp_path), "limit": 10},
    )
    cli_scope = runner.invoke(
        app,
        ["proposal", "scope", "show", proposal.proposal_id, "--format", "json", "--root", str(tmp_path)],
    )
    cli_classification = runner.invoke(
        app,
        ["project", "memory", "classification", "--limit", "10", "--format", "json", "--root", str(tmp_path)],
    )
    snapshot = workspace.project_snapshot(limit=10)

    assert applied["project_memory_scope_mutation"]["status"] == "applied"
    assert replay["project_memory_scope_mutation"]["status"] == "already_applied"
    assert cli_data(cli_scope, operation="proposal.scope.show")["project_memory_scope"] == mcp_scope["project_memory_scope"]
    assert cli_data(cli_classification, operation="project.memory.classification")["memory_classification"] == mcp_classification["memory_classification"]
    assert snapshot["memory_classification"]["contract"] == MEMORY_CLASSIFICATION_CONTRACT
    assert snapshot["memory_classification"]["counts"]["project_global"] == 1


def test_cli_scope_and_classification_match_sanitized_golden_contract(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Memory Golden", starter_id="empty")
    proposal = workspace.create_proposal("Unclassified contract")
    scope_result = runner.invoke(
        app,
        [
            "proposal",
            "scope",
            "show",
            proposal.proposal_id,
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    classification_result = runner.invoke(
        app,
        [
            "project",
            "memory",
            "classification",
            "--limit",
            "10",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    scope = cli_data(scope_result, operation="proposal.scope.show")[
        "project_memory_scope"
    ]
    classification = cli_data(
        classification_result,
        operation="project.memory.classification",
    )["memory_classification"]
    scope["updated_at"] = "<timestamp>"
    classification["memory_revision"] = "<sha256>"
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "project_memory"
        / "current-contract-v1.json"
    )

    assert {"scope": scope, "classification": classification} == json.loads(
        fixture_path.read_text(encoding="utf-8")
    )


def test_cli_scope_set_uses_versioned_receipt_backed_contract(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("CLI classified proposal")
    result = runner.invoke(
        app,
        [
            "proposal",
            "scope",
            "set",
            proposal.proposal_id,
            "--kind",
            "project_global",
            "--expected-memory-revision",
            workspace.project_memory_revision(),
            "--expected-structure-revision",
            str(workspace.project_structure().revision),
            "--operation-key",
            "memory-cli-12345678",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    mutation = cli_data(result, operation="proposal.scope.set")[
        "project_memory_scope_mutation"
    ]

    assert mutation["status"] == "applied"
    assert mutation["current_scope"]["kind"] == "project_global"
    assert "changed_paths" not in mutation
    assert workspace.mutation_status(
        idempotency_key="memory-cli-12345678"
    ).state == "applied"


def test_classification_authority_cannot_authorize_decision_or_readiness_override(
    tmp_path: Path,
) -> None:
    bootstrap = _external_context("project.initialize", decision_id="init-decision-01")
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Authority separation",
        owner="local-maintainer",
        authority_context=bootstrap,
    )
    proposal = workspace.create_proposal("Classified but not decided")
    classify = _external_context("project.memory.classify", decision_id="classify-decision-01")
    _assign(
        workspace,
        proposal.proposal_id,
        kind="project_global",
        key="external-memory-12345678",
        context=classify,
    )

    with pytest.raises(ValueError, match="P2P_CAPABILITY_MISMATCH"):
        _decision_preview(workspace, proposal.proposal_id, context=classify)
    with pytest.raises(ValueError, match="P2P_CAPABILITY_MISMATCH"):
        workspace._project_authority_service().resolve(
            supplied_context=classify,
            subject_id=classify.subject.identity_id,
            executor_id=classify.executor.identity_id,
            executor_kind=classify.executor.kind.value,
            required_capabilities=("proposal.readiness.override",),
            channel="cli",
        )
    status = workspace.mutation_status(idempotency_key="external-memory-12345678")
    assert status.authority is not None
    assert [claim["capability"] for claim in status.authority["claims"]] == [
        "project.memory.classify"
    ]

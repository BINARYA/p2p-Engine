from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner

from p2p_engine.core.authority import (
    AuthorityBasis,
    AuthorityClaim,
    AuthorityContext,
    AuthorityIdentity,
    AuthorityIdentityKind,
    AuthorityMode,
    AuthorityProjectBinding,
)
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionEventType,
)
from p2p_engine.cli import app
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data


runner = CliRunner()


def _external_context(
    capability_claims: tuple[AuthorityClaim, ...],
    *,
    subject_id: str = "wavekit-user-42",
    executor_id: str = "wavekit-mcp-client-7",
    decision_id: str = "wavekit-authz-decision-42",
) -> AuthorityContext:
    return AuthorityContext(
        mode=AuthorityMode.external_attestation,
        project_authority=AuthorityProjectBinding(
            authority_id="wavekit-project-authority-42",
            generation=1,
            provider_id="wavekit",
            provider_policy_version="wavekit-capabilities-v1",
        ),
        subject=AuthorityIdentity(subject_id, AuthorityIdentityKind.user),
        executor=AuthorityIdentity(executor_id, AuthorityIdentityKind.mcp_client),
        authorization_decision_id=decision_id,
        claims=capability_claims,
        authorized_at="2026-08-25T15:00:00Z",
    )


def _workspace(root: Path) -> tuple[P2PWorkspace, str]:
    bootstrap = _external_context(
        (
            AuthorityClaim(
                capability="project.initialize",
                basis=AuthorityBasis.root_authority,
                authority_generation=1,
            ),
        ),
        subject_id="wavekit-project-root-42",
        executor_id="wavekit-bootstrap-client-42",
        decision_id="wavekit-bootstrap-decision-42",
    )
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "External authority decision",
        owner="local-maintainer",
        authority_context=bootstrap,
    )
    proposal = workspace.create_proposal("Delegated decision")
    scope_context = _external_context(
        (
            AuthorityClaim(
                capability="project.memory.classify",
                basis=AuthorityBasis.root_authority,
                authority_generation=1,
            ),
        ),
        decision_id="wavekit-classification-decision-42",
    )
    workspace.assign_proposal_memory_scope(
        proposal_id=proposal.proposal_id,
        kind="project_global",
        section_ids=[],
        operation_key="external-decision-test-scope-12345678",
        expected_memory_revision=workspace.project_memory_revision(),
        expected_structure_revision=workspace.project_structure().revision,
        actor_id=scope_context.subject.identity_id,
        executor_id=scope_context.executor.identity_id,
        executor_kind=scope_context.executor.kind.value,
        authority_context=scope_context,
    )
    return workspace, proposal.proposal_id


def _delegated_context(*, grant_generation: int = 1) -> AuthorityContext:
    return _external_context(
        (
            AuthorityClaim(
                capability="proposal.decide",
                basis=AuthorityBasis.capability_grant,
                grant_ref="wavekit-grant-decision-42",
                grant_generation=grant_generation,
            ),
        )
    )


def test_external_delegated_decision_records_subject_executor_and_receipt(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    context = _delegated_context()
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="The delegated decision capability authorizes this outcome.",
        actor_id=context.subject.identity_id,
        executor_actor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        authority_context=context,
    )

    preview = service.preview(request)
    result = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert result.event.authority.subject.identity_id == "wavekit-user-42"
    assert result.event.authority.executor.identity_id == "wavekit-mcp-client-7"
    assert result.event.authority.claims[0].basis == AuthorityBasis.capability_grant
    status = workspace.mutation_status(
        idempotency_key=preview.request.operation_key
    )
    assert status.state == "applied"
    assert status.authority == result.event.authority.to_dict()


def test_external_readiness_override_requires_root_override_claim(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    context = _external_context(
        (
            AuthorityClaim(
                capability="proposal.decide",
                basis=AuthorityBasis.capability_grant,
                grant_ref="wavekit-grant-decision-42",
                grant_generation=1,
            ),
            AuthorityClaim(
                capability="proposal.readiness.override",
                basis=AuthorityBasis.capability_grant,
                grant_ref="wavekit-grant-override-42",
                grant_generation=1,
            ),
        )
    )
    request = workspace._proposal_decision_service().request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="Attempt a delegated readiness override.",
        actor_id=context.subject.identity_id,
        executor_actor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        readiness_override=True,
        authority_context=context,
    )

    with pytest.raises(ValueError, match="P2P_AUTHORIZATION_DENIED"):
        workspace.preview_proposal_decision(request)

    assert workspace.proposal_decision_status(proposal_id).event_count == 0


def test_external_root_can_combine_delegated_decision_with_readiness_override(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    context = _external_context(
        (
            AuthorityClaim(
                capability="proposal.decide",
                basis=AuthorityBasis.capability_grant,
                grant_ref="wavekit-grant-decision-42",
                grant_generation=1,
            ),
            AuthorityClaim(
                capability="proposal.readiness.override",
                basis=AuthorityBasis.root_authority,
                authority_generation=1,
            ),
        )
    )
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="The authority root explicitly overrides the readiness gate.",
        actor_id=context.subject.identity_id,
        executor_actor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        readiness_override=True,
        authority_context=context,
    )

    preview = service.preview(request)
    result = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert result.event.readiness.owner_override is True
    assert {
        claim.capability: claim.basis
        for claim in result.event.authority.claims
    }["proposal.readiness.override"] == AuthorityBasis.root_authority


def test_changed_grant_generation_invalidates_apply_without_writing(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    context = _delegated_context(grant_generation=1)
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="Bind grant generation one.",
        actor_id=context.subject.identity_id,
        executor_actor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        authority_context=context,
    )
    preview = service.preview(request)
    changed = replace(
        preview.request,
        authority_context=_delegated_context(grant_generation=2),
    )

    result = service.apply(
        changed,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "stale_preview"
    assert workspace.proposal_decision_status(proposal_id).event_count == 0


def test_changed_grant_generation_conflicts_after_original_apply(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    context = _delegated_context(grant_generation=1)
    request = service.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="Bind the original external grant generation.",
        actor_id=context.subject.identity_id,
        executor_actor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        authority_context=context,
    )
    preview = service.preview(request)
    applied = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    changed = replace(
        preview.request,
        authority_context=_delegated_context(grant_generation=2),
    )

    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        service.apply(
            changed,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )

    assert applied.status == "applied"
    assert workspace.proposal_decision_status(proposal_id).event_count == 1


def test_external_exact_replay_returns_original_authority_evidence(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    context = _delegated_context()
    request = service.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="Persist the externally attested decision once.",
        actor_id=context.subject.identity_id,
        executor_actor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        authority_context=context,
    )
    preview = service.preview(request)
    first = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    replay = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert first.status == "applied"
    assert replay.status == "already_applied"
    assert replay.event.authority == first.event.authority
    assert replay.event.authority.authorization_decision_id == (
        "wavekit-authz-decision-42"
    )


def test_local_exact_replay_survives_subject_revocation(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Local replay", owner="owner")
    proposal = workspace.create_proposal("Replay after permission change")
    workspace.assign_proposal_memory_scope(
        proposal_id=proposal.proposal_id,
        kind="project_global",
        section_ids=[],
        operation_key="local-replay-test-scope-12345678",
        expected_memory_revision=workspace.project_memory_revision(),
        expected_structure_revision=workspace.project_structure().revision,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal.proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="Commit before local permission replacement.",
        actor_id="owner",
    )
    preview = service.preview(request)
    first = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    permissions = workspace.permissions_show()
    permissions["identities"]["replacement-owner"] = {
        "role": "owner",
        "kind": "person",
        "display_name": "Replacement",
    }
    permissions["identities"]["owner"]["role"] = "contributor"
    workspace._permissions_service().validate_policy_payload(permissions)
    workspace._permissions_service().write_policy(permissions)

    replay = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert first.status == "applied"
    assert replay.status == "already_applied"
    assert replay.event.authority.subject.identity_id == "owner"


def test_external_decision_cli_json_input_matches_service_contract(
    tmp_path: Path,
) -> None:
    _workspace_instance, proposal_id = _workspace(tmp_path)
    context = _delegated_context()
    context_path = tmp_path / "authority-context.json"
    context_path.write_text(json.dumps(context.to_dict()), encoding="utf-8")
    common = [
        proposal_id,
        "--event-type",
        "accepted",
        "--reason",
        "Approve through external authority.",
        "--actor",
        context.subject.identity_id,
        "--executor-actor",
        context.executor.identity_id,
        "--executor-kind",
        context.executor.kind.value,
        "--authority-context",
        str(context_path),
        "--format",
        "json",
        "--root",
        str(tmp_path),
    ]
    preview_result = runner.invoke(app, ["decision", "preview", *common])
    assert preview_result.exit_code == 0, preview_result.output
    preview = cli_data(preview_result)
    request = preview["request"]

    apply_result = runner.invoke(
        app,
        [
            "decision",
            "apply",
            *common,
            "--decided-on",
            request["decided_on"],
            "--operation-key",
            request["operation_key"],
            "--preview-token",
            preview["preview"]["preview_token"],
            "--confirm",
        ],
    )

    assert apply_result.exit_code == 0, apply_result.output
    assert cli_data(apply_result)["status"] == "applied"


def test_external_decision_mcp_carries_typed_authority_and_local_consent(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    context = _delegated_context()
    workspace.permissions_actor_add(
        context.executor.identity_id,
        role="contributor",
        kind="client",
    )
    for arguments in (
        ("init",),
        ("config", "user.email", "test@example.com"),
        ("config", "user.name", "Test User"),
        ("add", "."),
        ("commit", "-m", "baseline"),
    ):
        subprocess.run(
            ["git", *arguments],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
    base = {
        "root": str(tmp_path),
        "proposal_id": proposal_id,
        "event_type": "accepted",
        "reason": "Approve through an authenticated hosted client.",
        "owner_id": context.subject.identity_id,
        "actor_id": context.executor.identity_id,
        "executor_kind": context.executor.kind.value,
        "authority_context": context.to_dict(),
    }
    preview = call_tool("p2p_proposal_decision_preview", base)[
        "proposal_decision_preview"
    ]
    token = preview["preview"]["preview_token"]
    consent = workspace.consent_grant(
        "proposal_decision_apply",
        f"{proposal_id}@{token}",
        context.executor.identity_id,
        approved_by="local-maintainer",
    )
    request = preview["request"]

    result = call_tool(
        "p2p_proposal_decision_apply",
        {
            **base,
            "decided_on": request["decided_on"],
            "operation_key": request["operation_key"],
            "source_head_event_id": request["source_head_event_id"],
            "preview_token": token,
            "confirm": True,
            "consent_id": consent.consent_id,
        },
    )

    assert result["proposal_decision"]["status"] == "applied"
    assert result["governance"]["subject_id"] == context.subject.identity_id
    assert result["governance"]["executor_id"] == context.executor.identity_id
    assert result["governance"]["authority_mode"] == "external_attestation"

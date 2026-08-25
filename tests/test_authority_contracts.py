from __future__ import annotations

from pathlib import Path
import socket

import pytest

from p2p_engine.core.authority import (
    AuthorityBasis,
    AuthorityClaim,
    AuthorityContext,
    AuthorityIdentity,
    AuthorityIdentityKind,
    AuthorityMode,
    AuthorityProjectBinding,
    ProjectAuthorityDescriptor,
)
from p2p_engine.core.governed_capabilities import (
    GOVERNED_CAPABILITIES,
    governed_capability,
    governed_capability_registry_payload,
)
from p2p_engine.services.authority import (
    AUTHORITY_CONTEXT_MAX_BYTES,
    AuthorityContractCodec,
    ProjectAuthorityService,
)
from p2p_engine.storage.filesystem import P2PWorkspace


def _external_context(
    *,
    capability: str = "proposal.decide",
    basis: AuthorityBasis = AuthorityBasis.capability_grant,
    authority_generation: int | None = None,
    grant_generation: int | None = 3,
) -> AuthorityContext:
    return AuthorityContext(
        mode=AuthorityMode.external_attestation,
        project_authority=AuthorityProjectBinding(
            authority_id="wk-project-authority-R7K3",
            generation=2,
            provider_id="wavekit",
            provider_policy_version="wavekit-project-capabilities/v1",
        ),
        subject=AuthorityIdentity("wk-project-actor-A91", AuthorityIdentityKind.user),
        executor=AuthorityIdentity("wk-project-client-C52", AuthorityIdentityKind.mcp_client),
        authorization_decision_id="wk-authz-D44",
        authorized_at="2026-08-25T12:00:00Z",
        claims=(
            AuthorityClaim(
                capability=capability,
                basis=basis,
                authority_generation=authority_generation,
                grant_ref=("wk-grant-G18" if basis == AuthorityBasis.capability_grant else None),
                grant_generation=grant_generation,
            ),
        ),
    )


def _external_descriptor() -> ProjectAuthorityDescriptor:
    return ProjectAuthorityDescriptor(
        authority_id="wk-project-authority-R7K3",
        mode=AuthorityMode.external_attestation,
        generation=2,
        provider_id="wavekit",
        provider_policy_version="wavekit-project-capabilities/v1",
    )


def _external_bootstrap_context() -> AuthorityContext:
    return AuthorityContext(
        mode=AuthorityMode.external_attestation,
        project_authority=AuthorityProjectBinding(
            authority_id="hosted-project-authority-01",
            generation=1,
            provider_id="hosted-provider",
            provider_policy_version="project-capabilities-v1",
        ),
        subject=AuthorityIdentity(
            "hosted-project-root-01",
            AuthorityIdentityKind.user,
        ),
        executor=AuthorityIdentity(
            "hosted-bootstrap-client-01",
            AuthorityIdentityKind.client,
        ),
        authorization_decision_id="hosted-init-decision-01",
        authorized_at="2026-08-25T12:00:00Z",
        claims=(
            AuthorityClaim(
                capability="project.initialize",
                basis=AuthorityBasis.root_authority,
                authority_generation=1,
            ),
        ),
    )


def test_governed_capability_registry_is_unique_and_transport_neutral() -> None:
    names = [item.capability for item in GOVERNED_CAPABILITIES]

    assert names == list(dict.fromkeys(names))
    assert governed_capability("proposal.decide").external_root_required is False
    assert governed_capability("project.structure.edit").external_root_required is True
    payload = governed_capability_registry_payload()
    assert payload["schema"] == "p2p-governed-capabilities/v1"
    assert "wavekit_role" not in str(payload).lower()


def test_external_authority_context_round_trips_with_deterministic_digest() -> None:
    codec = AuthorityContractCodec()
    context = _external_context()

    parsed = codec.context_from_mapping(context.to_dict())

    assert parsed == context
    assert parsed.digest_sha256 == context.digest_sha256
    assert len(parsed.digest_sha256) == 64


def test_authority_context_rejects_duplicate_json_keys_and_secret_like_ids() -> None:
    codec = AuthorityContractCodec()

    with pytest.raises(ValueError, match="P2P_AUTHORITY_CONTEXT_INVALID.*duplicate JSON key"):
        codec.context_from_bytes(b'{"schema":"a","schema":"b"}')

    payload = _external_context().to_dict()
    payload["authorization_decision_id"] = "sk-secret-value"
    with pytest.raises(ValueError, match="resembles secret material"):
        codec.context_from_mapping(payload)


def test_authority_context_rejects_oversized_payload() -> None:
    codec = AuthorityContractCodec()

    with pytest.raises(ValueError, match="authority context exceeds size limit"):
        codec.context_from_bytes(b"{" + (b" " * AUTHORITY_CONTEXT_MAX_BYTES) + b"}")


def test_external_context_requires_exact_capability_and_current_generation(
    tmp_path: Path,
) -> None:
    service = ProjectAuthorityService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    descriptor = _external_descriptor()

    with pytest.raises(ValueError, match="P2P_CAPABILITY_MISMATCH"):
        service.validate_context(
            _external_context(),
            required_capabilities=("project.structure.edit",),
            descriptor=descriptor,
        )

    stale = _external_context()
    stale = AuthorityContext(
        **{
            **stale.__dict__,
            "project_authority": AuthorityProjectBinding(
                authority_id=stale.project_authority.authority_id,
                generation=1,
                provider_id=stale.project_authority.provider_id,
                provider_policy_version=stale.project_authority.provider_policy_version,
            ),
        }
    )
    with pytest.raises(ValueError, match="P2P_AUTHORITY_GENERATION_STALE"):
        service.validate_context(
            stale,
            required_capabilities=("proposal.decide",),
            descriptor=descriptor,
        )


def test_external_context_rejects_mode_and_executor_mismatch(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Local authority", owner="owner")
    service = workspace._project_authority_service()

    with pytest.raises(ValueError, match="mode does not match"):
        service.validate_context(
            _external_context(),
            required_capabilities=("proposal.decide",),
        )

    external_root = tmp_path / "external"
    external_root.mkdir()
    external_service = ProjectAuthorityService(
        root=external_root,
        p2p_dir=external_root / ".p2p",
    )
    external_service.path.parent.mkdir(parents=True)
    external_service.path.write_bytes(
        external_service.descriptor_bytes(_external_descriptor())
    )
    with pytest.raises(ValueError, match="submitted executor does not match"):
        external_service.resolve(
            supplied_context=_external_context(),
            subject_id="wk-project-actor-A91",
            executor_id="different-client",
            executor_kind="mcp_client",
            required_capabilities=("proposal.decide",),
            channel="cli",
        )


def test_external_validation_has_no_network_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("authority validation attempted network access")

    monkeypatch.setattr(socket.socket, "connect", fail_network)
    service = ProjectAuthorityService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    validated = service.validate_context(
        _external_context(),
        required_capabilities=("proposal.decide",),
        descriptor=_external_descriptor(),
    )

    assert validated == _external_context()


def test_external_initialization_persists_matching_descriptor_and_receipt(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    operation_key = "hosted-project-init-01"
    context = _external_bootstrap_context()

    result = workspace.init_project_with_operation_key(
        "Hosted project",
        operation_key=operation_key,
        owner="local-maintainer",
        authority_context=context,
    )

    descriptor = workspace.project_authority()
    status = workspace.mutation_status(idempotency_key=operation_key)
    assert result["mutation"]["status"] == "applied"
    assert descriptor.authority_id == context.project_authority.authority_id
    assert descriptor.mode == AuthorityMode.external_attestation
    assert descriptor.generation == 1
    assert status.state == "applied"
    assert status.authority is not None
    assert status.authority["authority_context_sha256"] == context.digest_sha256
    assert len(list((tmp_path / ".p2p/project").glob("authority.yml"))) == 1


def test_external_root_only_capability_rejects_delegated_claim(tmp_path: Path) -> None:
    service = ProjectAuthorityService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    with pytest.raises(ValueError, match="P2P_AUTHORIZATION_DENIED"):
        service.validate_context(
            _external_context(capability="project.structure.edit"),
            required_capabilities=("project.structure.edit",),
            descriptor=_external_descriptor(),
        )


def test_local_policy_resolver_preserves_owner_and_executor_semantics(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Authority fixture", owner="Davide")
    service = ProjectAuthorityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        permissions=workspace._permissions_service(),
    )
    descriptor = service.read_descriptor()

    context, permission_sha = service.local_context(
        subject_id="davide",
        executor_id="davide",
        executor_kind="person",
        required_capabilities=("proposal.decide",),
        channel="cli",
    )

    assert descriptor.mode == AuthorityMode.local_policy
    assert context.subject.identity_id == "davide"
    assert context.executor.identity_id == "davide"
    assert context.claims[0].basis == AuthorityBasis.local_policy
    assert len(permission_sha) == 64


def test_schema4_rejects_legacy_owner_shaped_authority_id() -> None:
    codec = AuthorityContractCodec()

    with pytest.raises(ValueError, match="legacy wk-owner"):
        codec.descriptor_from_mapping(
            {
                "project_authority": {
                    "schema": "p2p-project-authority/v1",
                    "id": "wk-owner-123",
                    "mode": "external_attestation",
                    "generation": 1,
                    "provider_id": "wavekit",
                    "provider_policy_version": "v1",
                }
            }
        )

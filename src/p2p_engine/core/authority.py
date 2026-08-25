from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.mutation_preview import MutationPreview, MutationResult


PROJECT_AUTHORITY_SCHEMA = "p2p-project-authority/v1"
AUTHORITY_CONTEXT_SCHEMA = "p2p-authority-context/v1"
AUTHORITY_EVIDENCE_SCHEMA = "p2p-authority-evidence/v1"
LOCAL_AUTHORITY_POLICY_VERSION = "p2p-local-authority/v1"


class AuthorityMode(StrEnum):
    local_policy = "local_policy"
    external_attestation = "external_attestation"


class AuthorityBasis(StrEnum):
    root_authority = "root_authority"
    local_policy = "local_policy"
    capability_grant = "capability_grant"


class AuthorityIdentityKind(StrEnum):
    person = "person"
    user = "user"
    agent = "agent"
    mcp_client = "mcp_client"
    client = "client"
    service = "service"


@dataclass(frozen=True)
class ProjectAuthorityDescriptor:
    authority_id: str
    mode: AuthorityMode
    generation: int
    display_name: str = ""
    local_policy_version: str | None = None
    provider_id: str | None = None
    provider_policy_version: str | None = None
    schema: str = PROJECT_AUTHORITY_SCHEMA

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "id": self.authority_id,
            "mode": self.mode.value,
            "generation": self.generation,
        }
        if self.display_name:
            payload["display_name"] = self.display_name
        if self.mode == AuthorityMode.local_policy:
            payload["local_policy_version"] = self.local_policy_version
        else:
            payload["provider_id"] = self.provider_id
            payload["provider_policy_version"] = self.provider_policy_version
        return payload

    def to_payload(self) -> dict[str, object]:
        return {"project_authority": self.to_dict()}


@dataclass(frozen=True)
class AuthorityIdentity:
    identity_id: str
    kind: AuthorityIdentityKind

    def to_dict(self) -> dict[str, str]:
        return {"id": self.identity_id, "kind": self.kind.value}


@dataclass(frozen=True)
class AuthorityProjectBinding:
    authority_id: str
    generation: int
    local_policy_version: str | None = None
    provider_id: str | None = None
    provider_policy_version: str | None = None

    def to_dict(self, *, mode: AuthorityMode) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.authority_id,
            "generation": self.generation,
        }
        if mode == AuthorityMode.local_policy:
            payload["local_policy_version"] = self.local_policy_version
        else:
            payload["provider_id"] = self.provider_id
            payload["provider_policy_version"] = self.provider_policy_version
        return payload


@dataclass(frozen=True)
class AuthorityClaim:
    capability: str
    basis: AuthorityBasis
    authority_generation: int | None = None
    grant_ref: str | None = None
    grant_generation: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "capability": self.capability,
            "basis": self.basis.value,
        }
        if self.basis == AuthorityBasis.root_authority:
            payload["authority_generation"] = self.authority_generation
        elif self.basis == AuthorityBasis.capability_grant:
            payload["grant_ref"] = self.grant_ref
            payload["grant_generation"] = self.grant_generation
        return payload


@dataclass(frozen=True)
class AuthorityContext:
    mode: AuthorityMode
    project_authority: AuthorityProjectBinding
    subject: AuthorityIdentity
    executor: AuthorityIdentity
    authorization_decision_id: str
    claims: tuple[AuthorityClaim, ...]
    authorized_at: str | None = None
    schema: str = AUTHORITY_CONTEXT_SCHEMA

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "mode": self.mode.value,
            "project_authority": self.project_authority.to_dict(mode=self.mode),
            "subject": self.subject.to_dict(),
            "executor": self.executor.to_dict(),
            "authorization_decision_id": self.authorization_decision_id,
            "claims": [item.to_dict() for item in self.claims],
        }
        if self.authorized_at is not None:
            payload["authorized_at"] = self.authorized_at
        return payload

    @property
    def digest_sha256(self) -> str:
        return semantic_sha256(self.to_dict())

    def claim_for(self, capability: str) -> AuthorityClaim | None:
        return next(
            (item for item in self.claims if item.capability == capability),
            None,
        )


@dataclass(frozen=True)
class AuthorityEvidence:
    mode: AuthorityMode
    authority_id: str
    authority_generation: int
    subject: AuthorityIdentity
    executor: AuthorityIdentity
    claims: tuple[AuthorityClaim, ...]
    authorization_decision_id: str
    authority_context_sha256: str
    channel: str
    provider_id: str | None = None
    provider_policy_version: str | None = None
    local_policy_version: str | None = None
    authorized_at: str | None = None
    permission_policy_sha256: str | None = None
    consent_id: str | None = None
    consent_sha256: str | None = None
    schema: str = AUTHORITY_EVIDENCE_SCHEMA

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "mode": self.mode.value,
            "authority_id": self.authority_id,
            "authority_generation": self.authority_generation,
            "subject": self.subject.to_dict(),
            "executor": self.executor.to_dict(),
            "claims": [item.to_dict() for item in self.claims],
            "authorization_decision_id": self.authorization_decision_id,
            "authority_context_sha256": self.authority_context_sha256,
            "channel": self.channel,
            "provider_id": self.provider_id,
            "provider_policy_version": self.provider_policy_version,
            "local_policy_version": self.local_policy_version,
            "authorized_at": self.authorized_at,
            "permission_policy_sha256": self.permission_policy_sha256,
            "consent_id": self.consent_id,
            "consent_sha256": self.consent_sha256,
        }
        return payload


def authority_evidence_from_context(
    context: AuthorityContext,
    *,
    channel: str,
    permission_policy_sha256: str | None = None,
    consent_id: str | None = None,
    consent_sha256: str | None = None,
) -> AuthorityEvidence:
    return AuthorityEvidence(
        mode=context.mode,
        authority_id=context.project_authority.authority_id,
        authority_generation=context.project_authority.generation,
        subject=context.subject,
        executor=context.executor,
        claims=context.claims,
        authorization_decision_id=context.authorization_decision_id,
        authority_context_sha256=context.digest_sha256,
        channel=channel,
        provider_id=context.project_authority.provider_id,
        provider_policy_version=context.project_authority.provider_policy_version,
        local_policy_version=context.project_authority.local_policy_version,
        authorized_at=context.authorized_at,
        permission_policy_sha256=permission_policy_sha256,
        consent_id=consent_id,
        consent_sha256=consent_sha256,
    )


def authority_evidence_from_mapping(value: Mapping[str, object]) -> AuthorityEvidence:
    """Compatibility-free adapter used by receipt and event codecs."""
    from p2p_engine.services.authority import AuthorityContractCodec

    return AuthorityContractCodec().evidence_from_mapping(value)


def authority_context_from_evidence(evidence: AuthorityEvidence) -> AuthorityContext:
    context = AuthorityContext(
        mode=evidence.mode,
        project_authority=AuthorityProjectBinding(
            authority_id=evidence.authority_id,
            generation=evidence.authority_generation,
            local_policy_version=evidence.local_policy_version,
            provider_id=evidence.provider_id,
            provider_policy_version=evidence.provider_policy_version,
        ),
        subject=evidence.subject,
        executor=evidence.executor,
        authorization_decision_id=evidence.authorization_decision_id,
        claims=evidence.claims,
        authorized_at=evidence.authorized_at,
    )
    if context.digest_sha256 != evidence.authority_context_sha256:
        raise ValueError(
            "P2P_AUTHORITY_CONTEXT_INVALID: authority evidence digest does not "
            "match its reconstructable context"
        )
    return context


@dataclass(frozen=True)
class AuthorityRotationPreview:
    previous_descriptor: ProjectAuthorityDescriptor
    new_descriptor: ProjectAuthorityDescriptor
    authority: AuthorityEvidence
    mutation: MutationPreview
    rotation_request: Mapping[str, object]
    candidate_bytes: Mapping[str, bytes]

    def to_dict(self) -> dict[str, object]:
        return {
            "previous_descriptor": self.previous_descriptor.to_dict(),
            "new_descriptor": self.new_descriptor.to_dict(),
            "authority": self.authority.to_dict(),
            "rotation_request": dict(self.rotation_request),
            "preview": self.mutation.to_dict(),
        }


@dataclass(frozen=True)
class AuthorityRotationResult:
    status: str
    previous_descriptor: ProjectAuthorityDescriptor
    new_descriptor: ProjectAuthorityDescriptor
    authority: AuthorityEvidence
    event_id: str
    mutation: MutationResult | None = None
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "previous_descriptor": self.previous_descriptor.to_dict(),
            "new_descriptor": self.new_descriptor.to_dict(),
            "authority": self.authority.to_dict(),
            "event_id": self.event_id,
            "mutation": self.mutation.to_dict() if self.mutation is not None else None,
            "message": self.message,
        }

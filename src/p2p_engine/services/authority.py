from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
from typing import Mapping, Sequence

import yaml

from p2p_engine.core.authority import (
    AUTHORITY_CONTEXT_SCHEMA,
    AUTHORITY_EVIDENCE_SCHEMA,
    LOCAL_AUTHORITY_POLICY_VERSION,
    PROJECT_AUTHORITY_SCHEMA,
    AuthorityBasis,
    AuthorityClaim,
    AuthorityContext,
    AuthorityEvidence,
    AuthorityIdentity,
    AuthorityIdentityKind,
    AuthorityMode,
    AuthorityProjectBinding,
    ProjectAuthorityDescriptor,
    authority_context_from_evidence,
    authority_evidence_from_context,
)
from p2p_engine.core.governed_capabilities import governed_capability
from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.permissions import PermissionsService


PROJECT_AUTHORITY_PATH = Path(".p2p/project/authority.yml")
AUTHORITY_CONTEXT_MAX_BYTES = 65_536
AUTHORITY_DESCRIPTOR_MAX_BYTES = 16_384
AUTHORITY_ID_MAX_BYTES = 256
AUTHORITY_DISPLAY_MAX_BYTES = 256
AUTHORITY_CLAIM_MAX_COUNT = 16

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+-]{0,255}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SECRET_PREFIXES = (
    "sk-",
    "ghp_",
    "github_pat_",
    "bearer-",
    "session-",
)
_DESCRIPTOR_KEYS = frozenset(
    {
        "schema",
        "id",
        "mode",
        "generation",
        "display_name",
        "local_policy_version",
        "provider_id",
        "provider_policy_version",
    }
)
_CONTEXT_KEYS = frozenset(
    {
        "schema",
        "mode",
        "project_authority",
        "subject",
        "executor",
        "authorization_decision_id",
        "authorized_at",
        "claims",
    }
)
_PROJECT_BINDING_KEYS = frozenset(
    {
        "id",
        "generation",
        "local_policy_version",
        "provider_id",
        "provider_policy_version",
    }
)
_IDENTITY_KEYS = frozenset({"id", "kind"})
_CLAIM_KEYS = frozenset(
    {
        "capability",
        "basis",
        "authority_generation",
        "grant_ref",
        "grant_generation",
    }
)
_EVIDENCE_KEYS = frozenset(
    {
        "schema",
        "mode",
        "authority_id",
        "authority_generation",
        "subject",
        "executor",
        "claims",
        "authorization_decision_id",
        "authority_context_sha256",
        "channel",
        "provider_id",
        "provider_policy_version",
        "local_policy_version",
        "authorized_at",
        "permission_policy_sha256",
        "consent_id",
        "consent_sha256",
    }
)


class AuthorityContractCodec:
    def descriptor_from_mapping(
        self,
        payload: Mapping[str, object],
    ) -> ProjectAuthorityDescriptor:
        raw: object = payload.get("project_authority", payload)
        if not isinstance(raw, Mapping):
            raise _context_invalid("project_authority must be a mapping")
        _closed_keys(raw, _DESCRIPTOR_KEYS, "project_authority")
        schema = _required_text(raw, "schema")
        if schema != PROJECT_AUTHORITY_SCHEMA:
            raise _context_invalid(f"unsupported project authority schema `{schema}`")
        authority_id = _safe_identifier(raw.get("id"), "project_authority.id")
        if authority_id.startswith("wk-owner-"):
            raise _context_invalid("legacy wk-owner-* authority identifiers are forbidden")
        mode = _mode(raw.get("mode"))
        generation = _positive_int(raw.get("generation"), "project_authority.generation")
        display_name = _optional_display(raw.get("display_name"))
        local_policy = _optional_identifier(
            raw.get("local_policy_version"),
            "project_authority.local_policy_version",
        )
        provider_id = _optional_identifier(
            raw.get("provider_id"),
            "project_authority.provider_id",
        )
        provider_policy = _optional_identifier(
            raw.get("provider_policy_version"),
            "project_authority.provider_policy_version",
        )
        if mode == AuthorityMode.local_policy:
            if local_policy is None:
                raise _context_invalid("local authority requires local_policy_version")
            if provider_id is not None or provider_policy is not None:
                raise _context_invalid("local authority forbids provider fields")
        else:
            if provider_id is None or provider_policy is None:
                raise _context_invalid(
                    "external authority requires provider_id and provider_policy_version"
                )
            if local_policy is not None:
                raise _context_invalid("external authority forbids local_policy_version")
        return ProjectAuthorityDescriptor(
            schema=schema,
            authority_id=authority_id,
            mode=mode,
            generation=generation,
            display_name=display_name,
            local_policy_version=local_policy,
            provider_id=provider_id,
            provider_policy_version=provider_policy,
        )

    def descriptor_from_bytes(self, content: bytes) -> ProjectAuthorityDescriptor:
        if len(content) > AUTHORITY_DESCRIPTOR_MAX_BYTES:
            raise _context_invalid("project authority descriptor exceeds size limit")
        try:
            payload = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
        except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
            raise _context_invalid(f"cannot parse project authority descriptor: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise _context_invalid("project authority document must be a mapping")
        if set(payload) != {"project_authority"}:
            raise _context_invalid("project authority document has invalid root fields")
        return self.descriptor_from_mapping(payload)

    def descriptor_bytes(self, descriptor: ProjectAuthorityDescriptor) -> bytes:
        validated = self.descriptor_from_mapping(descriptor.to_payload())
        return yaml_dump(validated.to_payload()).encode("ascii")

    def context_from_mapping(self, raw: Mapping[str, object]) -> AuthorityContext:
        _closed_keys(raw, _CONTEXT_KEYS, "authority context")
        schema = _required_text(raw, "schema")
        if schema != AUTHORITY_CONTEXT_SCHEMA:
            raise _context_invalid(f"unsupported authority context schema `{schema}`")
        mode = _mode(raw.get("mode"))
        binding_raw = _required_mapping(raw, "project_authority")
        _closed_keys(binding_raw, _PROJECT_BINDING_KEYS, "project_authority")
        binding = AuthorityProjectBinding(
            authority_id=_safe_identifier(binding_raw.get("id"), "project_authority.id"),
            generation=_positive_int(
                binding_raw.get("generation"),
                "project_authority.generation",
            ),
            local_policy_version=_optional_identifier(
                binding_raw.get("local_policy_version"),
                "project_authority.local_policy_version",
            ),
            provider_id=_optional_identifier(
                binding_raw.get("provider_id"),
                "project_authority.provider_id",
            ),
            provider_policy_version=_optional_identifier(
                binding_raw.get("provider_policy_version"),
                "project_authority.provider_policy_version",
            ),
        )
        if binding.authority_id.startswith("wk-owner-"):
            raise _context_invalid("legacy wk-owner-* authority identifiers are forbidden")
        if mode == AuthorityMode.local_policy:
            if binding.local_policy_version is None:
                raise _context_invalid("local context requires local_policy_version")
            if binding.provider_id is not None or binding.provider_policy_version is not None:
                raise _context_invalid("local context forbids provider fields")
        else:
            if binding.provider_id is None or binding.provider_policy_version is None:
                raise _context_invalid("external context requires provider fields")
            if binding.local_policy_version is not None:
                raise _context_invalid("external context forbids local_policy_version")
        subject = self._identity(_required_mapping(raw, "subject"), "subject")
        executor = self._identity(_required_mapping(raw, "executor"), "executor")
        if executor.kind == AuthorityIdentityKind.service:
            raise _context_invalid(
                "executor must identify the initiating person, agent, or client, not a worker service"
            )
        decision_id = _safe_identifier(
            raw.get("authorization_decision_id"),
            "authorization_decision_id",
        )
        claims_raw = raw.get("claims")
        if not isinstance(claims_raw, list) or not claims_raw:
            raise _context_invalid("claims must be a non-empty sequence")
        if len(claims_raw) > AUTHORITY_CLAIM_MAX_COUNT:
            raise _context_invalid("claims exceed the bounded maximum")
        claims = tuple(self._claim(item) for item in claims_raw)
        capabilities = [item.capability for item in claims]
        if len(set(capabilities)) != len(capabilities):
            raise _context_invalid("claims contain duplicate capabilities")
        if capabilities != sorted(capabilities):
            raise _context_invalid("claims must be sorted by capability")
        authorized_at = _optional_timestamp(raw.get("authorized_at"))
        if mode == AuthorityMode.external_attestation and authorized_at is None:
            raise _context_invalid("external context requires authorized_at")
        if mode == AuthorityMode.local_policy and authorized_at is not None:
            raise _context_invalid("local context forbids authorized_at")
        return AuthorityContext(
            schema=schema,
            mode=mode,
            project_authority=binding,
            subject=subject,
            executor=executor,
            authorization_decision_id=decision_id,
            claims=claims,
            authorized_at=authorized_at,
        )

    def context_from_bytes(self, content: bytes) -> AuthorityContext:
        if len(content) > AUTHORITY_CONTEXT_MAX_BYTES:
            raise _context_invalid("authority context exceeds size limit")
        try:
            payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_json_object)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            if isinstance(exc, ValueError) and str(exc).startswith("P2P_AUTHORITY_CONTEXT_INVALID"):
                raise
            raise _context_invalid(f"cannot parse authority context JSON: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise _context_invalid("authority context JSON root must be an object")
        return self.context_from_mapping(payload)

    def context_from_path(self, path: Path) -> AuthorityContext:
        try:
            if path.is_symlink() or not path.is_file():
                raise _context_invalid("authority context path must be a regular file")
            return self.context_from_bytes(path.read_bytes())
        except OSError as exc:
            raise _context_invalid(f"cannot read authority context: {exc}") from exc

    def evidence_from_mapping(self, raw: Mapping[str, object]) -> AuthorityEvidence:
        _closed_keys(raw, _EVIDENCE_KEYS, "authority evidence")
        schema = _required_text(raw, "schema")
        if schema != AUTHORITY_EVIDENCE_SCHEMA:
            raise _context_invalid(f"unsupported authority evidence schema `{schema}`")
        mode = _mode(raw.get("mode"))
        claims_raw = raw.get("claims")
        if not isinstance(claims_raw, list) or not claims_raw:
            raise _context_invalid("authority evidence claims must be a non-empty sequence")
        claims = tuple(self._claim(item) for item in claims_raw)
        digest = _required_text(raw, "authority_context_sha256")
        _require_sha256(digest, "authority_context_sha256")
        permission_sha = _optional_text(raw.get("permission_policy_sha256"))
        consent_sha = _optional_text(raw.get("consent_sha256"))
        for value, field in (
            (permission_sha, "permission_policy_sha256"),
            (consent_sha, "consent_sha256"),
        ):
            if value is not None:
                _require_sha256(value, field)
        evidence = AuthorityEvidence(
            schema=schema,
            mode=mode,
            authority_id=_safe_identifier(raw.get("authority_id"), "authority_id"),
            authority_generation=_positive_int(
                raw.get("authority_generation"),
                "authority_generation",
            ),
            subject=self._identity(_required_mapping(raw, "subject"), "subject"),
            executor=self._identity(_required_mapping(raw, "executor"), "executor"),
            claims=claims,
            authorization_decision_id=_safe_identifier(
                raw.get("authorization_decision_id"),
                "authorization_decision_id",
            ),
            authority_context_sha256=digest,
            channel=_safe_identifier(raw.get("channel"), "channel"),
            provider_id=_optional_identifier(raw.get("provider_id"), "provider_id"),
            provider_policy_version=_optional_identifier(
                raw.get("provider_policy_version"),
                "provider_policy_version",
            ),
            local_policy_version=_optional_identifier(
                raw.get("local_policy_version"),
                "local_policy_version",
            ),
            authorized_at=_optional_timestamp(raw.get("authorized_at")),
            permission_policy_sha256=permission_sha,
            consent_id=_optional_identifier(raw.get("consent_id"), "consent_id"),
            consent_sha256=consent_sha,
        )
        if evidence.mode == AuthorityMode.local_policy:
            if evidence.local_policy_version is None or evidence.provider_id is not None:
                raise _context_invalid("local evidence has contradictory policy fields")
        elif (
            evidence.provider_id is None
            or evidence.provider_policy_version is None
            or evidence.authorized_at is None
            or evidence.local_policy_version is not None
        ):
            raise _context_invalid("external evidence has contradictory policy fields")
        authority_context_from_evidence(evidence)
        return evidence

    def _identity(self, raw: Mapping[str, object], field: str) -> AuthorityIdentity:
        _closed_keys(raw, _IDENTITY_KEYS, field)
        try:
            kind = AuthorityIdentityKind(_required_text(raw, "kind"))
        except ValueError as exc:
            raise _context_invalid(f"{field}.kind is unsupported") from exc
        return AuthorityIdentity(
            identity_id=_safe_identifier(raw.get("id"), f"{field}.id"),
            kind=kind,
        )

    def _claim(self, raw: object) -> AuthorityClaim:
        if not isinstance(raw, Mapping):
            raise _context_invalid("each authority claim must be a mapping")
        _closed_keys(raw, _CLAIM_KEYS, "authority claim")
        capability = _safe_identifier(raw.get("capability"), "claim.capability")
        governed_capability(capability)
        try:
            basis = AuthorityBasis(_required_text(raw, "basis"))
        except ValueError as exc:
            raise _context_invalid("claim.basis is unsupported") from exc
        authority_generation = _optional_positive_int(
            raw.get("authority_generation"),
            "claim.authority_generation",
        )
        grant_ref = _optional_identifier(raw.get("grant_ref"), "claim.grant_ref")
        grant_generation = _optional_positive_int(
            raw.get("grant_generation"),
            "claim.grant_generation",
        )
        if basis == AuthorityBasis.root_authority:
            if authority_generation is None or grant_ref is not None or grant_generation is not None:
                raise _context_invalid(
                    "root_authority claim requires only authority_generation"
                )
        elif basis == AuthorityBasis.capability_grant:
            if grant_ref is None or grant_generation is None or authority_generation is not None:
                raise _context_invalid(
                    "capability_grant claim requires only grant_ref and grant_generation"
                )
        elif any(value is not None for value in (authority_generation, grant_ref, grant_generation)):
            raise _context_invalid("local_policy claim forbids generation and grant fields")
        return AuthorityClaim(
            capability=capability,
            basis=basis,
            authority_generation=authority_generation,
            grant_ref=grant_ref,
            grant_generation=grant_generation,
        )


class ProjectAuthorityService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        permissions: PermissionsService | None = None,
        codec: AuthorityContractCodec | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.path = self.root / PROJECT_AUTHORITY_PATH
        self.permissions = permissions or PermissionsService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.codec = codec or AuthorityContractCodec()

    def new_local_descriptor(
        self,
        *,
        display_name: str = "",
        authority_id: str | None = None,
    ) -> ProjectAuthorityDescriptor:
        return ProjectAuthorityDescriptor(
            authority_id=(
                _safe_identifier(authority_id, "project_authority.id")
                if authority_id is not None
                else f"p2p-project-authority-{secrets.token_hex(16)}"
            ),
            mode=AuthorityMode.local_policy,
            generation=1,
            display_name=display_name or "Local project authority",
            local_policy_version=LOCAL_AUTHORITY_POLICY_VERSION,
        )

    def read_descriptor(self) -> ProjectAuthorityDescriptor:
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise _context_invalid("project authority descriptor is missing or unsafe")
            return self.codec.descriptor_from_bytes(self.path.read_bytes())
        except OSError as exc:
            raise _context_invalid(f"cannot read project authority descriptor: {exc}") from exc

    def descriptor_bytes(self, descriptor: ProjectAuthorityDescriptor) -> bytes:
        return self.codec.descriptor_bytes(descriptor)

    def descriptor_from_bootstrap_context(
        self,
        context: AuthorityContext,
        *,
        display_name: str = "",
    ) -> ProjectAuthorityDescriptor:
        binding = context.project_authority
        descriptor = ProjectAuthorityDescriptor(
            authority_id=binding.authority_id,
            mode=context.mode,
            generation=binding.generation,
            display_name=display_name,
            local_policy_version=binding.local_policy_version,
            provider_id=binding.provider_id,
            provider_policy_version=binding.provider_policy_version,
        )
        self.codec.descriptor_from_mapping(descriptor.to_payload())
        self.validate_context(
            context,
            required_capabilities=("project.initialize",),
            descriptor=descriptor,
            bootstrap=True,
        )
        return descriptor

    def local_context(
        self,
        *,
        subject_id: str,
        executor_id: str,
        executor_kind: str,
        required_capabilities: Sequence[str],
        channel: str,
        descriptor: ProjectAuthorityDescriptor | None = None,
        permission_payload: Mapping[str, object] | None = None,
    ) -> tuple[AuthorityContext, str]:
        selected = descriptor or self.read_descriptor()
        if selected.mode != AuthorityMode.local_policy:
            raise _authorization_denied(
                "local actor resolution cannot authorize an external-attestation project"
            )
        payload = dict(permission_payload or self.permissions.show())
        subject_actor = self.permissions.resolve_actor_payload(subject_id, payload)
        if subject_actor.role != "owner":
            raise _authorization_denied(
                "local governed mutation requires a current project owner"
            )
        executor_actor = self.permissions.resolve_actor_payload(executor_id, payload)
        if executor_actor.kind != executor_kind:
            raise _authorization_denied(
                "executor kind does not match local project permissions"
            )
        capabilities = _normalize_required_capabilities(required_capabilities)
        claims = tuple(
            AuthorityClaim(
                capability=name,
                basis=(
                    AuthorityBasis.root_authority
                    if governed_capability(name).external_root_required
                    else AuthorityBasis.local_policy
                ),
                authority_generation=(
                    selected.generation
                    if governed_capability(name).external_root_required
                    else None
                ),
            )
            for name in capabilities
        )
        permission_sha = semantic_sha256(payload)
        decision_id = "p2p-local-authz-" + semantic_sha256(
            {
                "authority_id": selected.authority_id,
                "authority_generation": selected.generation,
                "subject": subject_actor.actor_id,
                "executor": executor_actor.actor_id,
                "capabilities": list(capabilities),
                "permission_policy_sha256": permission_sha,
                "channel": channel,
            }
        )[:24]
        context = AuthorityContext(
            mode=AuthorityMode.local_policy,
            project_authority=AuthorityProjectBinding(
                authority_id=selected.authority_id,
                generation=selected.generation,
                local_policy_version=selected.local_policy_version,
            ),
            subject=AuthorityIdentity(
                identity_id=subject_actor.actor_id,
                kind=_local_kind(subject_actor.kind),
            ),
            executor=AuthorityIdentity(
                identity_id=executor_actor.actor_id,
                kind=_local_kind(executor_actor.kind),
            ),
            authorization_decision_id=decision_id,
            claims=claims,
        )
        self.validate_context(
            context,
            required_capabilities=capabilities,
            descriptor=selected,
        )
        return context, permission_sha

    def validate_context(
        self,
        context: AuthorityContext,
        *,
        required_capabilities: Sequence[str],
        descriptor: ProjectAuthorityDescriptor | None = None,
        bootstrap: bool = False,
    ) -> AuthorityContext:
        canonical = self.codec.context_from_mapping(context.to_dict())
        selected = descriptor or self.read_descriptor()
        if canonical.mode != selected.mode:
            raise _context_invalid("authority context mode does not match project authority")
        binding = canonical.project_authority
        if binding.authority_id != selected.authority_id:
            raise _context_invalid("authority context targets a different project authority")
        if binding.generation != selected.generation:
            raise ValueError(
                "P2P_AUTHORITY_GENERATION_STALE: authority context generation "
                "does not match the current project authority"
            )
        if canonical.mode == AuthorityMode.local_policy:
            if binding.local_policy_version != selected.local_policy_version:
                raise _context_invalid("local authority policy version mismatch")
        elif (
            binding.provider_id != selected.provider_id
            or binding.provider_policy_version != selected.provider_policy_version
        ):
            raise _context_invalid("external provider or policy version mismatch")
        required = _normalize_required_capabilities(required_capabilities)
        supplied = tuple(item.capability for item in canonical.claims)
        if supplied != required:
            raise ValueError(
                "P2P_CAPABILITY_MISMATCH: authority claims must match the exact "
                "required capability set"
            )
        for claim in canonical.claims:
            definition = governed_capability(claim.capability)
            if canonical.mode.value not in definition.supported_authority_modes:
                raise _authorization_denied(
                    f"capability `{claim.capability}` does not support authority mode"
                )
            if claim.basis == AuthorityBasis.root_authority:
                if claim.authority_generation != selected.generation:
                    raise ValueError(
                        "P2P_AUTHORITY_GENERATION_STALE: root claim generation is stale"
                    )
            if canonical.mode == AuthorityMode.external_attestation:
                if definition.external_root_required and claim.basis != AuthorityBasis.root_authority:
                    raise _authorization_denied(
                        f"capability `{claim.capability}` requires root-authority basis"
                    )
                if not definition.external_root_required and claim.basis not in {
                    AuthorityBasis.root_authority,
                    AuthorityBasis.capability_grant,
                }:
                    raise _authorization_denied(
                        "external capability requires root or capability-grant basis"
                    )
            elif claim.basis not in {
                AuthorityBasis.local_policy,
                AuthorityBasis.root_authority,
            }:
                raise _authorization_denied(
                    "local policy cannot consume an external capability grant"
                )
        if bootstrap and selected.generation != 1:
            raise _context_invalid("bootstrap authority generation must be 1")
        return canonical

    def resolve(
        self,
        *,
        supplied_context: AuthorityContext | None,
        subject_id: str,
        executor_id: str,
        executor_kind: str,
        required_capabilities: Sequence[str],
        channel: str,
        permission_payload: Mapping[str, object] | None = None,
        consent_id: str | None = None,
        consent_sha256: str | None = None,
    ) -> tuple[AuthorityContext, AuthorityEvidence]:
        if supplied_context is None:
            context, permission_sha = self.local_context(
                subject_id=subject_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                required_capabilities=required_capabilities,
                channel=channel,
                permission_payload=permission_payload,
            )
        else:
            context = self.validate_context(
                supplied_context,
                required_capabilities=required_capabilities,
            )
            permission_sha = None
            if subject_id and subject_id != context.subject.identity_id:
                raise _context_invalid("submitted subject does not match actor input")
            if executor_id and executor_id != context.executor.identity_id:
                raise _context_invalid("submitted executor does not match executor input")
            if executor_kind and executor_kind != context.executor.kind.value:
                raise _context_invalid("submitted executor kind does not match context")
            if context.mode == AuthorityMode.local_policy:
                current_context, permission_sha = self.local_context(
                    subject_id=context.subject.identity_id,
                    executor_id=context.executor.identity_id,
                    executor_kind=context.executor.kind.value,
                    required_capabilities=required_capabilities,
                    channel=channel,
                    permission_payload=permission_payload,
                )
                if current_context.digest_sha256 != context.digest_sha256:
                    raise _authorization_denied(
                        "local authority policy changed after preview"
                    )
        return context, authority_evidence_from_context(
            context,
            channel=channel,
            permission_policy_sha256=permission_sha,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )


def _normalize_required_capabilities(values: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(sorted(set(str(item).strip() for item in values)))
    if not normalized or any(not item for item in normalized):
        raise ValueError("P2P_CAPABILITY_MISMATCH: at least one capability is required")
    for item in normalized:
        governed_capability(item)
    return normalized


def _local_kind(value: str) -> AuthorityIdentityKind:
    aliases = {
        "person": AuthorityIdentityKind.person,
        "user": AuthorityIdentityKind.user,
        "agent": AuthorityIdentityKind.agent,
        "mcp_client": AuthorityIdentityKind.mcp_client,
        "client": AuthorityIdentityKind.client,
    }
    try:
        return aliases[value]
    except KeyError as exc:
        raise _authorization_denied(f"unsupported local actor kind `{value}`") from exc


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _context_invalid(f"duplicate JSON key `{key}`")
        result[key] = value
    return result


def _closed_keys(
    value: Mapping[object, object],
    allowed: frozenset[str],
    field: str,
) -> None:
    unknown = sorted(str(key) for key in value if key not in allowed)
    if unknown:
        raise _context_invalid(f"{field} has unknown fields: {', '.join(unknown)}")


def _required_mapping(value: Mapping[str, object], field: str) -> Mapping[str, object]:
    raw = value.get(field)
    if not isinstance(raw, Mapping):
        raise _context_invalid(f"{field} must be a mapping")
    return raw


def _required_text(value: Mapping[str, object], field: str) -> str:
    raw = value.get(field)
    if not isinstance(raw, str) or not raw.strip():
        raise _context_invalid(f"{field} must be non-empty text")
    return raw.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _context_invalid("optional text field must be non-empty or null")
    return value.strip()


def _safe_identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _context_invalid(f"{field} must be a non-empty identifier")
    normalized = value.strip()
    if len(normalized.encode("utf-8")) > AUTHORITY_ID_MAX_BYTES or not _IDENTIFIER.fullmatch(normalized):
        raise _context_invalid(f"{field} is not a bounded log-safe identifier")
    lowered = normalized.lower()
    if lowered.startswith(_SECRET_PREFIXES) or "token=" in lowered or "cookie=" in lowered:
        raise _context_invalid(f"{field} resembles secret material")
    if (
        len(normalized) >= 48
        and normalized.count(".") == 2
        and all(len(part) >= 8 for part in normalized.split("."))
    ):
        raise _context_invalid(f"{field} resembles a bearer token")
    return normalized


def _optional_identifier(value: object, field: str) -> str | None:
    return None if value is None else _safe_identifier(value, field)


def _optional_display(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise _context_invalid("display_name must be text")
    normalized = value.strip()
    if len(normalized.encode("utf-8")) > AUTHORITY_DISPLAY_MAX_BYTES:
        raise _context_invalid("display_name exceeds size limit")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise _context_invalid("display_name contains control characters")
    return normalized


def _mode(value: object) -> AuthorityMode:
    try:
        return AuthorityMode(str(value))
    except ValueError as exc:
        raise _context_invalid("authority mode is unsupported") from exc


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _context_invalid(f"{field} must be a positive integer")
    return value


def _optional_positive_int(value: object, field: str) -> int | None:
    return None if value is None else _positive_int(value, field)


def _optional_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _context_invalid("authorized_at must be a timestamp or null")
    normalized = value.strip()
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _context_invalid("authorized_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _context_invalid("authorized_at must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _require_sha256(value: str, field: str) -> None:
    if _SHA256.fullmatch(value) is None:
        raise _context_invalid(f"{field} must be a lowercase SHA-256 digest")


def _context_invalid(message: str) -> ValueError:
    return ValueError(f"P2P_AUTHORITY_CONTEXT_INVALID: {message}")


def _authorization_denied(message: str) -> ValueError:
    return ValueError(f"P2P_AUTHORIZATION_DENIED: {message}")

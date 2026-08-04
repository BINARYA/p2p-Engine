from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from pathlib import Path

from p2p_engine.foundation.files import (
    identity_slug as _identity_slug,
    read_yaml_mapping_or_default as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)

PERMISSION_ROLES = {"owner", "maintainer", "contributor", "agent", "readonly"}
ACTOR_KINDS = {"person", "agent", "client"}


@dataclass(frozen=True)
class PermissionActor:
    actor_id: str
    role: str
    kind: str
    display_name: str
    path: Path


class PermissionsService:
    def __init__(self, *, root: Path, p2p_dir: Path) -> None:
        self.root = root
        self.p2p_dir = p2p_dir

    def path(self) -> Path:
        return self.p2p_dir / "project" / "permissions.yml"

    def default_policy_payload(self, owner_name: str | None, repository_mode: str) -> dict[str, object]:
        owner_id = self.identity_slug(owner_name or "owner")
        owner_display = owner_name or "owner"
        return {
            "permissions": {
                "version": 1,
                "model": "role_plus_consent_receipt",
                "identity_strength": "project_declared",
                "repository_mode": repository_mode,
                "cloud_enforcement": [
                    "git_provider_permissions",
                    "branch_protection",
                    "required_approvals",
                    "token_scopes",
                ],
            },
            "identities": {
                owner_id: {
                    "role": "owner",
                    "kind": "person",
                    "display_name": owner_display,
                },
                "contributor": {
                    "role": "contributor",
                    "kind": "person",
                    "display_name": "contributor",
                },
            },
            "roles": {
                "owner": {
                    "can_grant_consent": True,
                    "can_manage_permissions": True,
                },
                "maintainer": {
                    "can_request_privileged_operations": True,
                },
                "contributor": {
                    "can_create_local_branches": True,
                    "can_request_review": True,
                },
                "agent": {
                    "can_use_safe_tools": True,
                },
                "readonly": {
                    "can_read": True,
                },
            },
            "tool_classes": {
                "safe_read": {"consent_required": False},
                "write_safe_preparatory": {"consent_required": False, "audit_required": True},
                "privileged_publish": {"consent_required": True},
                "owner_controlled_governance": {"consent_required": True, "owner_required": True},
                "destructive_or_external": {"consent_required": True, "single_use_required": True},
            },
        }

    def validate_policy_payload(
        self,
        payload: Mapping[str, object],
        *,
        require_single_owner: bool = False,
    ) -> None:
        identities = payload.get("identities")
        if not isinstance(identities, Mapping) or not identities:
            raise ValueError("Invalid permissions policy: identities must be a non-empty mapping")
        owners: list[str] = []
        for actor_id, identity in identities.items():
            if not isinstance(actor_id, str) or not actor_id.strip() or not isinstance(identity, Mapping):
                raise ValueError("Invalid permissions policy identity entry")
            role = self.normalize_role(str(identity.get("role") or ""))
            self.normalize_actor_kind(str(identity.get("kind") or ""))
            if role == "owner":
                owners.append(actor_id)
        if not owners:
            raise ValueError("Invalid permissions policy: one owner identity is required")
        if require_single_owner and len(owners) != 1:
            raise ValueError("Invalid permissions policy: exactly one owner identity is required")

    def write_policy(self, payload: dict[str, object]) -> None:
        path = self.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(payload), encoding="utf-8")

    def show(self, *, repository_mode: str = "local") -> dict[str, object]:
        path = self.path()
        if not path.exists():
            raise ValueError(
                "P2P355_PERMISSIONS_REQUIRED: current projects require .p2p/project/permissions.yml"
            )
        payload = _read_yaml_mapping(path, default={})
        self.validate_policy_payload(payload)
        return payload

    def resolve_actor(
        self,
        actor_id: str,
        *,
        repository_mode: str = "local",
    ) -> PermissionActor:
        return self.resolve_actor_payload(
            actor_id,
            self.show(repository_mode=repository_mode),
        )

    def resolve_actor_payload(
        self,
        actor_id: str,
        payload: Mapping[str, object],
    ) -> PermissionActor:
        actor_slug = self.identity_slug(actor_id)
        identities = payload.get("identities")
        identity = identities.get(actor_slug) if isinstance(identities, Mapping) else None
        if not isinstance(identity, Mapping):
            raise ValueError(f"Unknown project actor: {actor_id}")
        return PermissionActor(
            actor_id=actor_slug,
            role=self.normalize_role(str(identity.get("role") or "")),
            kind=self.normalize_actor_kind(str(identity.get("kind") or "")),
            display_name=str(identity.get("display_name") or actor_id),
            path=self.path().relative_to(self.root),
        )

    def require_role(
        self,
        actor_id: str,
        role: str,
        *,
        operation: str,
        repository_mode: str = "local",
    ) -> PermissionActor:
        actor = self.resolve_actor(actor_id, repository_mode=repository_mode)
        expected = self.normalize_role(role)
        if actor.role != expected:
            raise ValueError(
                f"P2P343_PROJECT_QUESTION_OWNER_REQUIRED: operation `{operation}` requires "
                f"role `{expected}`; actor `{actor.actor_id}` has role `{actor.role}`"
            )
        return actor

    def actor_add(
        self,
        actor_id: str,
        role: str = "contributor",
        kind: str = "person",
        display_name: str | None = None,
        *,
        repository_mode: str = "local",
    ) -> PermissionActor:
        actor_slug = self.identity_slug(actor_id)
        role = self.normalize_role(role)
        kind = self.normalize_actor_kind(kind)
        path = self.path()
        payload = self.show(repository_mode=repository_mode)
        identities = payload.setdefault("identities", {})
        if not isinstance(identities, dict):
            raise ValueError("Invalid permissions policy: identities must be a mapping")
        identities[actor_slug] = {
            "role": role,
            "kind": kind,
            "display_name": display_name or actor_id,
        }
        self.write_policy(payload)
        return PermissionActor(
            actor_id=actor_slug,
            role=role,
            kind=kind,
            display_name=display_name or actor_id,
            path=path.relative_to(self.root),
        )

    def identity_slug(self, value: str) -> str:
        return _identity_slug(value)

    def normalize_role(self, role: str) -> str:
        role = str(role or "").strip().lower()
        if role not in PERMISSION_ROLES:
            allowed = ", ".join(sorted(PERMISSION_ROLES))
            raise ValueError(f"Invalid permission role: {role}. Allowed: {allowed}")
        return role

    def normalize_actor_kind(self, kind: str) -> str:
        kind = str(kind or "").strip().lower()
        if kind not in ACTOR_KINDS:
            allowed = ", ".join(sorted(ACTOR_KINDS))
            raise ValueError(f"Invalid actor kind: {kind}. Allowed: {allowed}")
        return kind

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


LOCAL_POLICY_OWNER = "project_owner"
LOCAL_POLICY_PROJECT_ACTOR = "project_actor"
LOCAL_POLICY_READ_ONLY = "read_only"


@dataclass(frozen=True)
class GovernedCapability:
    capability: str
    operation_family: str
    local_policy_rule: str
    supported_authority_modes: tuple[str, ...]
    external_root_required: bool
    mutation_surface: str

    def to_dict(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "operation_family": self.operation_family,
            "local_policy_rule": self.local_policy_rule,
            "supported_authority_modes": list(self.supported_authority_modes),
            "external_root_required": self.external_root_required,
            "mutation_surface": self.mutation_surface,
        }


_BOTH_MODES = ("local_policy", "external_attestation")

GOVERNED_CAPABILITIES: Final[tuple[GovernedCapability, ...]] = (
    GovernedCapability(
        "project.initialize",
        "project_lifecycle",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.authority.rotate",
        "project_lifecycle",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.identity.adopt",
        "project_lifecycle",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.identity.derive",
        "project_lifecycle",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.vertical.install",
        "project_vertical",
        LOCAL_POLICY_OWNER,
        ("local_policy",),
        False,
        "existing_unintegrated",
    ),
    GovernedCapability(
        "project.vertical.adopt",
        "project_vertical",
        LOCAL_POLICY_OWNER,
        ("local_policy",),
        False,
        "existing_unintegrated",
    ),
    GovernedCapability(
        "project.vertical.migrate",
        "project_vertical",
        LOCAL_POLICY_OWNER,
        ("local_policy",),
        False,
        "existing_unintegrated",
    ),
    GovernedCapability(
        "project.domain.change",
        "project_domain",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.structure.edit",
        "project_structure",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.memory.classify",
        "project_memory",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.structure.retire",
        "project_structure",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.structure.replace",
        "project_structure",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "project.structure.merge",
        "project_structure",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented_cli_apply_mcp_read_only",
    ),
    GovernedCapability(
        "project.structure.restore",
        "project_structure",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented_cli_apply_mcp_read_only",
    ),
    GovernedCapability(
        "project.vertical.export",
        "vertical_authoring",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
    GovernedCapability(
        "proposal.create",
        "proposal_authoring",
        LOCAL_POLICY_PROJECT_ACTOR,
        ("local_policy",),
        False,
        "existing_unintegrated",
    ),
    GovernedCapability(
        "proposal.update",
        "proposal_authoring",
        LOCAL_POLICY_PROJECT_ACTOR,
        ("local_policy",),
        False,
        "existing_unintegrated",
    ),
    GovernedCapability(
        "proposal.contribution.add",
        "proposal_authoring",
        LOCAL_POLICY_PROJECT_ACTOR,
        ("local_policy",),
        False,
        "existing_unintegrated",
    ),
    GovernedCapability(
        "proposal.readiness.assess",
        "proposal_readiness",
        LOCAL_POLICY_PROJECT_ACTOR,
        ("local_policy",),
        False,
        "existing_unintegrated",
    ),
    GovernedCapability(
        "proposal.decide",
        "proposal_decision",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        False,
        "implemented",
    ),
    GovernedCapability(
        "proposal.decision.repair",
        "proposal_decision",
        LOCAL_POLICY_OWNER,
        ("local_policy",),
        False,
        "existing_unintegrated",
    ),
    GovernedCapability(
        "proposal.readiness.override",
        "proposal_decision",
        LOCAL_POLICY_OWNER,
        _BOTH_MODES,
        True,
        "implemented",
    ),
)

_BY_NAME: Final[dict[str, GovernedCapability]] = {
    item.capability: item for item in GOVERNED_CAPABILITIES
}


def governed_capability(name: str) -> GovernedCapability:
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise ValueError(
            f"P2P_CAPABILITY_MISMATCH: unknown governed capability `{name}`"
        ) from exc


def governed_capability_registry_payload() -> dict[str, object]:
    return {
        "schema": "p2p-governed-capabilities/v1",
        "capabilities": [item.to_dict() for item in GOVERNED_CAPABILITIES],
        "read_only_exemption": {
            "authority_context_required": False,
            "note": (
                "Read-only inspection is authorized by the calling transport or "
                "application and does not carry a mutation AuthorityContext."
            ),
        },
    }

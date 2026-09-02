from __future__ import annotations

from dataclasses import dataclass

from p2p_engine import __version__
from p2p_engine.core.authority_transfer import AUTHORITY_TRANSFER_PROTOCOL
from p2p_engine.core.canonical_memory import (
    DOMAIN_CONTRACT,
    MEMORY_SCHEMA_VERSION,
    PROJECT_BUNDLE_SCHEMA,
)

PROJECT_INTEGRATION_CONTRACT = "p2p-project-integration/v1"
PROJECT_INTEGRATION_MANIFEST_VERSION = 1
PROJECT_INTEGRATION_SECTION_ID = "p2p-project-access"
PROJECT_INTEGRATION_GUIDE_PATH = "P2P-INTEGRATION.md"

STANDALONE_PROFILE = "standalone"
LINKED_LOCAL_PROFILE = "linked-local"
REMOTE_ONLY_PROFILE = "remote-only"
PROJECT_ACCESS_PROFILES = (
    STANDALONE_PROFILE,
    LINKED_LOCAL_PROFILE,
    REMOTE_ONLY_PROFILE,
)

# Transfer and replica synchronization are deliberately not implemented by
# this feature.  Keeping an explicit, nullable dimension prevents callers from
# confusing the integration-artifact contract with a future sync protocol.
SYNC_PROTOCOL_VERSION: str | None = None


@dataclass(frozen=True)
class ProjectAccessProfile:
    profile: str
    supported: bool
    local_memory: bool
    authority: str
    surfaces: tuple[str, ...]
    capabilities: tuple[str, ...]
    unavailable_capabilities: tuple[str, ...] = ()
    offline_reads: str = "authoritative"
    offline_mutations: str = "allowed"
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "supported": self.supported,
            "local_memory": self.local_memory,
            "authority": self.authority,
            "surfaces": list(self.surfaces),
            "capabilities": list(self.capabilities),
            "unavailable_capabilities": list(self.unavailable_capabilities),
            "offline_reads": self.offline_reads,
            "offline_mutations": self.offline_mutations,
            "reason": self.reason,
        }


def normalize_access_profile(value: str) -> str:
    profile = str(value or "").strip().lower().replace("_", "-")
    if profile not in PROJECT_ACCESS_PROFILES:
        raise ValueError(
            "P2P_INTEGRATION_PROFILE_INVALID: profile must be one of "
            + ", ".join(PROJECT_ACCESS_PROFILES)
        )
    return profile


def access_profile(value: str) -> ProjectAccessProfile:
    profile = normalize_access_profile(value)
    if profile == STANDALONE_PROFILE:
        return ProjectAccessProfile(
            profile=profile,
            supported=True,
            local_memory=True,
            authority="local",
            surfaces=("cli", "mcp-stdio"),
            capabilities=(
                "local-authoritative-memory",
                "local-cli",
                "local-mcp-stdio",
                "governed-local-mutations",
                "offline-authoritative-reads",
                "offline-governed-mutations",
            ),
        )
    if profile == LINKED_LOCAL_PROFILE:
        return ProjectAccessProfile(
            profile=profile,
            supported=True,
            local_memory=True,
            authority="wavekit",
            surfaces=("cli", "mcp-stdio"),
            capabilities=(
                "wavekit-project-binding",
                "local-replica-reads",
                "authority-transfer-recovery",
                "local-governed-mutations-blocked",
            ),
            unavailable_capabilities=(
                "replica-catch-up",
                "replica-freshness",
                "online-authoritative-write",
            ),
            offline_reads="potentially-stale",
            offline_mutations="blocked",
            reason=(
                "authority is remote; replica catch-up and online mutation arrive in later "
                "linked-replica features"
            ),
        )
    return ProjectAccessProfile(
        profile=profile,
        supported=False,
        local_memory=False,
        authority="wavekit",
        surfaces=("web", "api", "mcp-http"),
        capabilities=(),
        unavailable_capabilities=(
            "wavekit-authenticated-actor",
            "wavekit-web-project",
            "wavekit-api-project",
            "wavekit-mcp-http",
        ),
        offline_reads="unavailable",
        offline_mutations="blocked",
        reason=(
            "remote-only rendering is disabled until authenticated WaveKit web, API, "
            "and MCP HTTP capabilities are implemented"
        ),
    )


def require_supported_profile(value: str) -> ProjectAccessProfile:
    profile = access_profile(value)
    if not profile.supported:
        missing = ", ".join(profile.unavailable_capabilities)
        raise ValueError(
            f"P2P_INTEGRATION_PROFILE_UNSUPPORTED: {profile.profile}: "
            f"{profile.reason}; missing capabilities: {missing}"
        )
    return profile


def current_integration_versions() -> dict[str, object]:
    return {
        "runtime": {"version": __version__, "compatibility": "exact-generator"},
        "local_memory": {
            "schema_version": MEMORY_SCHEMA_VERSION,
            "compatibility": "exact-schema",
        },
        "domain": {"contract": DOMAIN_CONTRACT, "compatibility": "same-major"},
        "bundle": {"contract": PROJECT_BUNDLE_SCHEMA, "compatibility": "same-major"},
        "authority_transfer": {
            "protocol": AUTHORITY_TRANSFER_PROTOCOL,
            "status": "client-implemented",
            "compatibility": "exact-major",
        },
        "sync": {
            "protocol": SYNC_PROTOCOL_VERSION,
            "status": "unavailable",
            "compatibility": "not-negotiated",
        },
        "integration": {
            "contract": PROJECT_INTEGRATION_CONTRACT,
            "manifest_version": PROJECT_INTEGRATION_MANIFEST_VERSION,
            "compatibility": "same-major",
        },
    }


def integration_contract_major(value: object) -> int | None:
    text = str(value or "")
    prefix = "p2p-project-integration/v"
    if not text.startswith(prefix):
        return None
    suffix = text.removeprefix(prefix)
    return int(suffix) if suffix.isdigit() else None


def managed_section_markers(profile: str) -> tuple[str, str]:
    normalized = normalize_access_profile(profile)
    start = (
        "<!-- P2P:BEGIN managed-section "
        f"id={PROJECT_INTEGRATION_SECTION_ID} "
        f"contract={PROJECT_INTEGRATION_CONTRACT} "
        f"runtime={__version__} profile={normalized} ownership=managed-section -->"
    )
    end = f"<!-- P2P:END managed-section id={PROJECT_INTEGRATION_SECTION_ID} -->"
    return start, end

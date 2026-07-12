from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from p2p_engine.services.agent_templates import (
    BUILT_IN_AGENT_ADAPTERS,
    expanded_agent_profiles,
    normalize_agent_profile,
)


_DETECTION_ENV_KEYS = ("P2P_CURRENT_AGENT", "P2P_AGENT_PROFILE", "P2P_AGENT")


@dataclass(frozen=True)
class AgentProfileSelection:
    requested_profile: str | None
    effective_profile: str
    effective_adapters: list[str]
    detected_adapter: str | None
    selection_source: str
    fallback_used: bool
    warning: str


def detect_current_agent(env: Mapping[str, str] | None = None) -> str | None:
    values = env if env is not None else os.environ
    for key in _DETECTION_ENV_KEYS:
        value = values.get(key)
        if not value:
            continue
        try:
            normalized = normalize_agent_profile(value)
        except ValueError:
            return None
        if normalized in BUILT_IN_AGENT_ADAPTERS and normalized != "generic":
            return normalized
    return None


def select_agent_profile(
    requested_profile: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> AgentProfileSelection:
    if requested_profile and requested_profile.strip():
        effective_profile = normalize_agent_profile(requested_profile)
        return AgentProfileSelection(
            requested_profile=requested_profile,
            effective_profile=effective_profile,
            effective_adapters=expanded_agent_profiles(effective_profile),
            detected_adapter=None,
            selection_source="explicit",
            fallback_used=False,
            warning="",
        )

    detected = detect_current_agent(env)
    if detected is not None:
        return AgentProfileSelection(
            requested_profile=None,
            effective_profile=detected,
            effective_adapters=expanded_agent_profiles(detected),
            detected_adapter=detected,
            selection_source="detected",
            fallback_used=False,
            warning="",
        )

    effective_profile = "all"
    return AgentProfileSelection(
        requested_profile=None,
        effective_profile=effective_profile,
        effective_adapters=expanded_agent_profiles(effective_profile),
        detected_adapter=None,
        selection_source="fallback",
        fallback_used=True,
        warning=(
            "Could not reliably detect the current agent. Falling back to all built-in "
            "adapters for compatibility. This creates files or registry records for all "
            "built-in adapters. You can narrow integrations later with "
            "`p2p agent uninstall <adapter>`."
        ),
    )

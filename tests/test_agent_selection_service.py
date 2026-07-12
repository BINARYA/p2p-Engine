from __future__ import annotations

from p2p_engine.services.agent_selection import select_agent_profile


def test_agent_selection_preserves_explicit_single_adapter() -> None:
    selection = select_agent_profile("codex", env={})

    assert selection.requested_profile == "codex"
    assert selection.effective_profile == "codex"
    assert selection.effective_adapters == ["generic", "codex"]
    assert selection.detected_adapter is None
    assert selection.selection_source == "explicit"
    assert selection.fallback_used is False
    assert selection.warning == ""


def test_agent_selection_preserves_explicit_multi_adapter() -> None:
    selection = select_agent_profile("codex,claude", env={})

    assert selection.effective_profile == "claude,codex"
    assert selection.effective_adapters == ["claude", "codex", "generic"]
    assert selection.selection_source == "explicit"


def test_agent_selection_preserves_explicit_all() -> None:
    selection = select_agent_profile("all", env={})

    assert selection.effective_profile == "all"
    assert selection.effective_adapters == [
        "generic",
        "codex",
        "claude",
        "cursor",
        "copilot",
        "gemini",
        "opencode",
    ]
    assert selection.selection_source == "explicit"


def test_agent_selection_uses_reliable_detected_agent() -> None:
    selection = select_agent_profile(None, env={"P2P_CURRENT_AGENT": "codex"})

    assert selection.requested_profile is None
    assert selection.effective_profile == "codex"
    assert selection.effective_adapters == ["generic", "codex"]
    assert selection.detected_adapter == "codex"
    assert selection.selection_source == "detected"
    assert selection.fallback_used is False
    assert selection.warning == ""


def test_agent_selection_unknown_detection_falls_back_to_all_with_warning() -> None:
    selection = select_agent_profile(None, env={})

    assert selection.effective_profile == "all"
    assert selection.effective_adapters == [
        "generic",
        "codex",
        "claude",
        "cursor",
        "copilot",
        "gemini",
        "opencode",
    ]
    assert selection.detected_adapter is None
    assert selection.selection_source == "fallback"
    assert selection.fallback_used is True
    assert "Could not reliably detect the current agent" in selection.warning
    assert "all built-in adapters" in selection.warning


def test_agent_selection_ignores_unsupported_detection_values() -> None:
    selection = select_agent_profile(None, env={"P2P_CURRENT_AGENT": "unsupported"})

    assert selection.effective_profile == "all"
    assert selection.detected_adapter is None
    assert selection.fallback_used is True

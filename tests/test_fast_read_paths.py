from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.storage.filesystem import P2PWorkspace


def _provider_executions(calls: int, cache_hits: int) -> int:
    return calls - cache_hits


@pytest.mark.integration
def test_small_context_uses_one_request_context_and_skips_deep_providers(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Read Context Project", project_domain="software")
    context = workspace.read_context()

    packet = workspace.context_packet(read_context=context)
    counters = context.counters

    assert packet.current_state["verification"]["validation"] == "not_run"
    assert packet.current_state["verification"]["freshness"] == "not_run"
    assert packet.current_state["derived_freshness"]["verification"] == "fast_checked"
    for provider in (
        "project_name",
        "registry_status",
        "proposal_summaries",
        "vertical_memory_status",
        "vertical_memory",
        "project_readiness",
        "next_actions",
    ):
        assert _provider_executions(
            counters.provider_calls.get(provider, 0),
            counters.provider_cache_hits.get(provider, 0),
        ) <= 1
    assert counters.provider_calls.get("complete_validation", 0) == 0
    assert counters.provider_calls.get("complete_freshness", 0) == 0
    assert context.finalize().current is True


@pytest.mark.integration
def test_public_context_retries_after_captured_source_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Read Context Project", project_domain="software")
    service = workspace._context_packet_service()
    original = service.context_packet
    project_path = tmp_path / ".p2p" / "project.yml"
    calls = 0

    def mutating_context_packet(*args, **kwargs):
        nonlocal calls
        calls += 1
        packet = original(*args, **kwargs)
        if calls == 1:
            payload = yaml.safe_load(project_path.read_text(encoding="utf-8"))
            payload["project"]["name"] = "Updated During Read"
            project_path.write_text(
                yaml.safe_dump(payload, sort_keys=False),
                encoding="utf-8",
            )
        return packet

    monkeypatch.setattr(service, "context_packet", mutating_context_packet)

    packet = workspace.context_packet()

    assert calls == 2
    assert packet.current_state["project"] == "Updated During Read"


@pytest.mark.integration
def test_next_and_progress_accept_caller_owned_read_contexts(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Caller Context Project", project_domain="software")

    next_context = workspace.read_context()
    workspace.next_actions(limit=3, read_context=next_context)
    next_counters = next_context.counters
    assert next_counters.provider_calls.get("complete_validation", 0) == 0
    assert next_counters.provider_calls.get("complete_freshness", 0) == 0
    assert next_context.finalize().current is True

    progress_context = workspace.read_context()
    progress = workspace.project_progress(read_context=progress_context)
    assert progress.vertical_id
    assert _provider_executions(
        progress_context.counters.provider_calls.get("vertical_memory", 0),
        progress_context.counters.provider_cache_hits.get("vertical_memory", 0),
    ) == 1
    assert progress_context.finalize().current is True

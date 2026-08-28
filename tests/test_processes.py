from __future__ import annotations

import os

import pytest

import p2p_engine.foundation.processes as processes


def test_pid_liveness_probe_handles_current_missing_and_invalid_processes() -> None:
    assert processes.pid_is_running(os.getpid()) is True
    assert processes.pid_is_running(2**31 - 1) is False
    assert processes.pid_is_running(0) is False
    assert processes.pid_is_running(-1) is False


def test_windows_pid_liveness_never_uses_os_kill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[int] = []

    def fake_windows_probe(pid: int) -> bool:
        observed.append(pid)
        return True

    def unexpected_kill(pid: int, signal: int) -> None:
        raise AssertionError((pid, signal))

    monkeypatch.setattr(processes, "_IS_WINDOWS", True)
    monkeypatch.setattr(processes, "_windows_pid_is_running", fake_windows_probe)
    monkeypatch.setattr(processes.os, "kill", unexpected_kill)

    assert processes.pid_is_running(1234) is True
    assert observed == [1234]


def test_posix_pid_liveness_preserves_missing_and_permission_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(processes, "_IS_WINDOWS", False)

    def missing(pid: int, signal: int) -> None:
        raise ProcessLookupError(pid, signal)

    monkeypatch.setattr(processes.os, "kill", missing)
    assert processes.pid_is_running(1234) is False

    def inaccessible(pid: int, signal: int) -> None:
        raise PermissionError(pid, signal)

    monkeypatch.setattr(processes.os, "kill", inaccessible)
    assert processes.pid_is_running(1234) is True

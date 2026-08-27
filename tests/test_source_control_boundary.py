from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_source_boundary_guard_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "scripts/check-source-boundary.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_runtime_ignores_source_control_sentinel_and_opaque_metadata(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    opaque = project / ".git"
    opaque.mkdir()
    sentinel_bytes = b"opaque-source-control-metadata\n"
    (opaque / "HEAD").write_bytes(sentinel_bytes)

    sentinel_bin = tmp_path / "bin"
    sentinel_bin.mkdir()
    invocation_log = tmp_path / "invocations.log"
    executable = sentinel_bin / "git"
    executable.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$P2P_GIT_SENTINEL_LOG\"\nexit 97\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = f"{sentinel_bin}:{environment['PATH']}"
    environment["P2P_GIT_SENTINEL_LOG"] = str(invocation_log)

    for command in (
        ("init", "Sentinel Project", "--agent", "generic", "--root", str(project)),
        ("doctor", "--root", str(project)),
        ("validate", "--root", str(project)),
    ):
        completed = subprocess.run(
            [sys.executable, "-m", "p2p_engine", *command],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr

    assert not (project / ".gitignore").exists()
    assert (opaque / "HEAD").read_bytes() == sentinel_bytes
    assert not invocation_log.exists() or invocation_log.read_bytes() == b""


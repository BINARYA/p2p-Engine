from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _fake_pytest(path: Path) -> Path:
    path.write_text(
        "#!/usr/bin/env sh\n"
        'printf "%s\\n" "$@" > "$PYTEST_CAPTURE"\n'
        'if [ -n "${PYTHONPATH_CAPTURE:-}" ]; then printf "%s" "${PYTHONPATH-}" > "$PYTHONPATH_CAPTURE"; fi\n',
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


@pytest.mark.adapter
@pytest.mark.parametrize(
    ("script_name", "expected_args"),
    [
        ("test-public.sh", ["-m", "cli or mcp", "--sentinel"]),
        ("test-full.sh", ["--sentinel"]),
        ("test-focused.sh", ["--sentinel"]),
        ("test-smoke.sh", ["-m", "smoke", "--sentinel"]),
    ],
)
def test_test_scripts_fall_back_to_pytest_on_path(
    tmp_path: Path,
    script_name: str,
    expected_args: list[str],
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_pytest(bin_dir / "pytest")
    capture = tmp_path / "args.txt"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PYTEST_CAPTURE": str(capture),
    }
    env.pop("PYTEST_BIN", None)

    result = subprocess.run(
        [str(ROOT / "scripts" / script_name), "--sentinel"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == expected_args


@pytest.mark.adapter
@pytest.mark.parametrize(
    "script_name",
    ["test-focused.sh", "test-public.sh", "test-full.sh", "test-smoke.sh"],
)
def test_source_test_scripts_prepend_checkout_src(tmp_path: Path, script_name: str) -> None:
    explicit_pytest = _fake_pytest(tmp_path / "explicit-pytest")
    capture = tmp_path / "args.txt"
    pythonpath_capture = tmp_path / "pythonpath.txt"
    env = {
        **os.environ,
        "PYTEST_BIN": str(explicit_pytest),
        "PYTEST_CAPTURE": str(capture),
        "PYTHONPATH_CAPTURE": str(pythonpath_capture),
        "PYTHONPATH": str(tmp_path / "existing"),
    }

    result = subprocess.run(
        [str(ROOT / "scripts" / script_name), "--sentinel"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    values = pythonpath_capture.read_text(encoding="utf-8").split(os.pathsep)
    assert values == [str(ROOT / "src"), str(tmp_path / "existing")]


@pytest.mark.adapter
def test_installed_test_script_owns_isolation_and_removes_pythonpath() -> None:
    script = (ROOT / "scripts" / "test-installed.sh").read_text(encoding="utf-8")

    assert 'wheel_path=""' in script
    assert "expected exactly one wheel" in script
    assert 'python_bin="${PYTHON_BIN:-python3}"' in script
    assert '"$python_bin" -m venv "$venv_root"' in script
    assert "unset PYTHONPATH" in script
    assert "PYTHONNOUSERSITE=1" in script
    assert '"$venv_root/bin/python" -m pytest -m smoke' in script
    assert "P2P_NETWORK_SENTINEL_LOG" in script
    assert "outbound network denied during installed smoke" in script
    assert '[[ ! -s "$network_log" ]]' in script
    assert "binarya/software_project@2.0.0" in script
    assert "project_structure_export_preview" in script
    assert "json.loads(completed.stdout)" in script
    assert "timeout = 20" in script
    assert "trap cleanup EXIT" in script
    assert "trap abort INT TERM" in script
    for failure_mode in (
        "install-failure",
        "missing-dependency",
        "malformed-cli-json",
        "mcp-timeout",
        "git-invocation",
        "interrupted-smoke",
    ):
        assert failure_mode in script


@pytest.mark.adapter
def test_installed_script_rejects_wrong_wheel_before_environment_creation(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "wrong-name.whl"
    wheel.write_bytes(b"not a wheel")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    env = {
        **os.environ,
        "PYTHON_BIN": sys.executable,
        "P2P_TEST_TMPDIR": str(scratch),
    }

    result = subprocess.run(
        [str(ROOT / "scripts" / "test-installed.sh"), "--wheel", str(wheel)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 2
    assert "wrong wheel identity" in result.stderr
    assert list(scratch.iterdir()) == []


@pytest.mark.adapter
def test_installed_script_cleans_environment_after_install_failure(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "p2p_engine-0.5.0-py3-none-any.whl"
    wheel.write_bytes(b"not a wheel")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    env = {
        **os.environ,
        "PYTHON_BIN": sys.executable,
        "P2P_TEST_TMPDIR": str(scratch),
    }

    result = subprocess.run(
        [str(ROOT / "scripts" / "test-installed.sh"), "--wheel", str(wheel)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode != 0
    assert list(scratch.iterdir()) == []


@pytest.mark.adapter
def test_installed_script_cleans_environment_when_interrupted(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "p2p_engine-0.5.0-py3-none-any.whl"
    wheel.write_bytes(b"not a wheel")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    env = {
        **os.environ,
        "PYTHON_BIN": sys.executable,
        "P2P_TEST_TMPDIR": str(scratch),
    }
    process = subprocess.Popen(
        [str(ROOT / "scripts" / "test-installed.sh"), "--wheel", str(wheel)],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not list(scratch.iterdir()):
        if process.poll() is not None:
            break
        time.sleep(0.02)
    assert list(scratch.iterdir()), "script did not create its temporary environment"

    os.killpg(process.pid, signal.SIGTERM)
    process.communicate(timeout=10)

    assert process.returncode != 0
    assert list(scratch.iterdir()) == []


@pytest.mark.adapter
def test_test_scripts_honor_explicit_pytest_bin(tmp_path: Path) -> None:
    explicit_pytest = _fake_pytest(tmp_path / "explicit-pytest")
    capture = tmp_path / "args.txt"
    env = {
        **os.environ,
        "PYTEST_BIN": str(explicit_pytest),
        "PYTEST_CAPTURE": str(capture),
    }

    result = subprocess.run(
        [str(ROOT / "scripts" / "test-full.sh"), "--sentinel"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == ["--sentinel"]

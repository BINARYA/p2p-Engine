from __future__ import annotations

import os
from pathlib import Path
import subprocess

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
        ("test-installed.sh", ["-m", "smoke", "--sentinel"]),
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
def test_installed_test_script_removes_pythonpath(tmp_path: Path) -> None:
    explicit_pytest = _fake_pytest(tmp_path / "explicit-pytest")
    capture = tmp_path / "args.txt"
    pythonpath_capture = tmp_path / "pythonpath.txt"
    env = {
        **os.environ,
        "PYTEST_BIN": str(explicit_pytest),
        "PYTEST_CAPTURE": str(capture),
        "PYTHONPATH_CAPTURE": str(pythonpath_capture),
        "PYTHONPATH": str(tmp_path / "source"),
    }

    result = subprocess.run(
        [str(ROOT / "scripts" / "test-installed.sh"), "--sentinel"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert pythonpath_capture.read_text(encoding="utf-8") == ""


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

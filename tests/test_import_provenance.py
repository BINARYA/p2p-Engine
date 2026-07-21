from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _package(path: Path, version: str) -> Path:
    package = path / "p2p_engine"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )
    return package


def _run(root: Path, pythonpath: Path, *, expect_source: bool) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "import-provenance.py"),
        "--root",
        str(root),
        "--format",
        "json",
    ]
    if expect_source:
        command.append("--expect-source")
    return subprocess.run(
        command,
        cwd=root,
        env={
            **os.environ,
            "PYTHONPATH": str(pythonpath),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.adapter
def test_import_provenance_distinguishes_source_and_installed_copy(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    source_root = root / "src"
    installed_root = tmp_path / "site-packages"
    source_package = _package(source_root, "1.0.0")
    installed_package = _package(installed_root, "1.0.0")

    source = _run(root, source_root, expect_source=True)
    installed = _run(root, installed_root, expect_source=True)

    assert source.returncode == 0, source.stderr
    source_payload = json.loads(source.stdout)
    assert source_payload["uses_source_checkout"] is True
    assert source_payload["module_path"] == (source_package / "__init__.py").as_posix()
    assert installed.returncode == 2
    installed_payload = json.loads(installed.stdout)
    assert installed_payload["uses_source_checkout"] is False
    assert installed_payload["module_path"] == (installed_package / "__init__.py").as_posix()


@pytest.mark.adapter
def test_import_provenance_tolerates_missing_git_executable(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    source_root = root / "src"
    _package(source_root, "1.0.0")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "import-provenance.py"),
            "--root",
            str(root),
            "--format",
            "json",
        ],
        cwd=root,
        env={
            **os.environ,
            "PATH": "",
            "PYTHONPATH": str(source_root),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["git_revision"] is None

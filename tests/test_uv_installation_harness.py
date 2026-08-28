from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "test-uv-installed.py"
SPEC = importlib.util.spec_from_file_location("p2p_test_uv_installed", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _wheel(path: Path, *, version: str = "0.5.0") -> Path:
    wheel = path / f"p2p_engine-{version}-py3-none-any.whl"
    metadata = f"Metadata-Version: 2.4\nName: p2p-engine\nVersion: {version}\n"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"p2p_engine-{version}.dist-info/METADATA", metadata)
    return wheel


def test_harness_accepts_one_literal_matching_wheel_and_records_digest(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)

    identity = MODULE.inspect_wheel(wheel)

    assert identity.version == "0.5.0"
    assert identity.path == wheel.resolve()
    assert len(identity.sha256) == 64


@pytest.mark.parametrize("name", ["*.whl", "missing.whl"])
def test_harness_rejects_glob_or_missing_wheel(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError):
        MODULE.inspect_wheel(tmp_path / name)


def test_harness_rejects_directory_and_wrong_identity(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        MODULE.inspect_wheel(tmp_path)

    wheel = tmp_path / "other-0.5.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "other-0.5.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: other\nVersion: 0.5.0\n",
        )
    with pytest.raises(ValueError):
        MODULE.inspect_wheel(wheel)


def test_harness_layout_is_fully_isolated_and_rejects_external_project(tmp_path: Path) -> None:
    isolated = tmp_path / "isolated"
    isolated.mkdir()

    layout = MODULE.make_layout(isolated)
    environment = layout.environment({"PATH": "/usr/bin", "PYTHONPATH": "/source"})

    assert layout.project.is_relative_to(isolated)
    assert environment["UV_TOOL_DIR"] == str(layout.tools)
    assert environment["UV_TOOL_BIN_DIR"] == str(layout.binaries)
    assert environment["UV_PYTHON_INSTALL_DIR"] == str(layout.python)
    assert environment["UV_CACHE_DIR"] == str(layout.cache)
    assert "PYTHONPATH" not in environment
    with pytest.raises(ValueError):
        MODULE.make_layout(isolated, project_root=tmp_path / "external")


def test_harness_project_digest_tracks_names_and_bytes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    first = project / "state.yml"
    first.write_text("version: 1\n", encoding="utf-8")
    initial = MODULE.project_digest(project)

    first.write_text("version: 2\n", encoding="utf-8")

    assert MODULE.project_digest(project) != initial


def test_github_failure_annotation_is_multiline_safe(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    MODULE.report_failure("failed 100%\r\nsecond line")

    stderr = capsys.readouterr().err.splitlines()
    assert stderr == [
        "failed 100%",
        "second line",
        "::error title=uv installed-wheel qualification failed::"
        "failed 100%25%0D%0Asecond line",
    ]


def test_github_failure_annotation_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    MODULE.report_failure("prefix-" + "x" * 7000)

    annotation = capsys.readouterr().err.splitlines()[-1]
    assert annotation.startswith(
        "::error title=uv installed-wheel qualification failed::"
    )
    assert annotation.endswith("x" * 6000)
    assert "prefix-" not in annotation

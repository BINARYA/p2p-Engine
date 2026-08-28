from __future__ import annotations

import importlib.util
import os
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
METADATA_SCRIPT = ROOT / "scripts" / "verify-release-metadata.py"
SPEC = importlib.util.spec_from_file_location("verify_release_metadata", METADATA_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
METADATA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(METADATA)

CHECKOUT_SHA = "11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP_PYTHON_SHA = "a26af69be951a213d495a4c3e4e4022e16d87065"
UPLOAD_ARTIFACT_SHA = "ea165f8d65b6e75b540449e92b4886f43607fa02"
DOWNLOAD_ARTIFACT_SHA = "d3f86a106a0bac45b974a628896c90dbdf5c8093"
ATTEST_SHA = "508db95dd578ae2727ebd6217d5ba78e4fbda05d"
SETUP_UV_SHA = "c771a70e6277c0a99b617c7a806ffedaca235ff9"


def _workflow(name: str) -> tuple[dict[str, object], str]:
    text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    return yaml.safe_load(text), text


def test_ci_is_pre_tag_and_reuses_one_wheel_across_supported_uv_matrix() -> None:
    workflow, text = _workflow("ci.yml")
    source = workflow["jobs"]["source"]
    uv_wheel = workflow["jobs"]["uv-wheel"]
    uv_installed = workflow["jobs"]["uv-installed"]

    assert source["strategy"]["matrix"]["python-version"] == ["3.11", "3.14"]
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request:" in text
    assert "branches:\n      - main" in text
    assert "workflow_dispatch:" in text
    assert uv_wheel["needs"] == "source"
    assert uv_installed["needs"] == "uv-wheel"
    assert [item["target"] for item in uv_installed["strategy"]["matrix"]["include"]] == [
        "linux-x86_64",
        "macos-x86_64",
        "windows-x86_64",
        "macos-arm64",
    ]
    assert text.count("p2p-engine-uv-candidate-${{ github.sha }}") == 2
    assert text.count("p2p-engine-uv-previous-0.5.0-${{ github.sha }}") == 2
    assert "99c43fa51ba78a01dfdc153c9821d5f2bf6890156a03447eeeb159ee894a6768" in text
    assert "--previous-wheel" in text
    assert "version: \"0.12.6\"" in text
    assert "--managed-python" in (ROOT / "scripts" / "test-uv-installed.py").read_text(
        encoding="utf-8"
    )
    assert all("dist/" not in str(step.get("run", "")) for step in source["steps"])
    assert "coverage" not in text.lower()


def test_runner_temp_is_bound_only_after_each_matrix_runner_exists() -> None:
    for workflow_name, job_name in (
        ("ci.yml", "uv-installed"),
        ("release-candidate.yml", "uv-installed-matrix"),
    ):
        workflow, _ = _workflow(workflow_name)
        job = workflow["jobs"][job_name]
        assert "runner.temp" not in str(job.get("env", {}))
        qualification = next(
            step
            for step in job["steps"]
            if step.get("name") == "Qualify managed-Python uv installation"
        )
        assert qualification["env"]["P2P_UV_TEST_TMPDIR"] == "${{ runner.temp }}"


def test_staged_mypy_gate_is_import_bounded_and_cache_independent() -> None:
    configuration = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["tool"]["mypy"]
    script = (ROOT / "scripts" / "check-static.sh").read_text(encoding="utf-8")

    assert configuration["follow_imports"] == "silent"
    assert '"$python_bin" -m mypy --no-incremental' in script


def test_candidate_is_exact_read_only_non_publishing_gate() -> None:
    workflow, text = _workflow("release-candidate.yml")

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["source-matrix"]["strategy"]["matrix"][
        "python-version"
    ] == ["3.11", "3.14"]
    assert "ref: ${{ inputs.ref }}" in text
    assert "git rev-parse HEAD" in text
    assert "build-release-candidate.sh" in text
    assert "test-installed.sh --wheel" in text
    assert "audit-wheel.sh --wheel" in text
    assert "actions/upload-artifact@" + UPLOAD_ARTIFACT_SHA in text
    uv_matrix = workflow["jobs"]["uv-installed-matrix"]
    assert uv_matrix["needs"] == "artifact"
    assert [item["target"] for item in uv_matrix["strategy"]["matrix"]["include"]] == [
        "linux-x86_64",
        "macos-x86_64",
        "windows-x86_64",
        "macos-arm64",
    ]
    assert "test-uv-installed.py" in text
    assert "--previous-wheel" in text
    assert "p2p-engine-previous-0.5.0-${{ inputs.ref }}" in text
    assert "99c43fa51ba78a01dfdc153c9821d5f2bf6890156a03447eeeb159ee894a6768" in text
    assert "release create" not in text
    assert "publish-release.sh" not in text
    assert "coverage" not in text.lower()


def test_tag_workflow_reuses_candidate_and_grants_write_only_to_publish() -> None:
    workflow, text = _workflow("release.yml")
    jobs = workflow["jobs"]

    assert jobs["candidate"]["uses"] == "./.github/workflows/release-candidate.yml"
    assert jobs["candidate"]["with"]["ref"] == "${{ github.sha }}"
    assert jobs["candidate"]["permissions"] == {"contents": "read"}
    assert jobs["attest"]["needs"] == "candidate"
    assert jobs["attest"]["permissions"] == {
        "actions": "read",
        "artifact-metadata": "write",
        "attestations": "write",
        "contents": "read",
        "id-token": "write",
    }
    assert jobs["publish"]["permissions"] == {
        "actions": "read",
        "contents": "write",
    }
    assert jobs["publish"]["needs"] == "attest"
    assert "actions/attest@" + ATTEST_SHA in text
    assert text.count("actions/download-artifact@" + DOWNLOAD_ARTIFACT_SHA) == 2
    assert "build-release-candidate.sh" not in text
    assert "--clobber" not in text
    assert "publish-release.sh" in text
    assert "coverage" not in text.lower()


def test_third_party_actions_are_full_sha_pinned() -> None:
    for name in ("ci.yml", "release-candidate.yml", "release.yml"):
        _, text = _workflow(name)
        for line in text.splitlines():
            if "uses: actions/checkout@" in line:
                assert line.split("@", 1)[1].split()[0] == CHECKOUT_SHA
            if "uses: actions/setup-python@" in line:
                assert line.split("@", 1)[1].split()[0] == SETUP_PYTHON_SHA
            if "uses: actions/upload-artifact@" in line:
                assert line.split("@", 1)[1].split()[0] == UPLOAD_ARTIFACT_SHA
            if "uses: actions/download-artifact@" in line:
                assert line.split("@", 1)[1].split()[0] == DOWNLOAD_ARTIFACT_SHA
            if "uses: actions/attest@" in line:
                assert line.split("@", 1)[1].split()[0] == ATTEST_SHA
            if "uses: astral-sh/setup-uv@" in line:
                assert line.split("@", 1)[1].split()[0] == SETUP_UV_SHA


def test_candidate_builder_compares_clean_builds_before_checksums() -> None:
    text = (ROOT / "scripts" / "build-release-candidate.sh").read_text(
        encoding="utf-8"
    )

    assert "SOURCE_DATE_EPOCH is required" in text
    assert 'cmp -s "$artifact" "$peer"' in text
    assert "non-reproducible member:" in text
    assert text.index('cmp -s "$artifact" "$peer"') < text.index("sha256sum")


def test_owner_approved_package_metadata_is_complete() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert METADATA.validate_release_metadata(ROOT) == []
    assert project["license"] == "GPL-3.0-or-later"
    assert project["license-files"] == ["LICENSE"]
    assert project["authors"] == [{"name": "mrjungle"}]
    assert project["maintainers"] == [{"name": "mrjungle"}]
    assert project["urls"] == METADATA.APPROVED_URLS
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "GPL-3.0-or-later" in readme
    assert "mrjungle and contributors" in readme


def test_release_finalization_gate_accepts_owner_finalized_state() -> None:
    assert METADATA.validate_release_metadata(ROOT, require_release=True) == []


def test_candidate_builder_requires_finalized_metadata_before_build() -> None:
    text = (ROOT / "scripts" / "build-release-candidate.sh").read_text(
        encoding="utf-8"
    )

    assert "metadata_args+=(--release)" in text
    assert text.index("verify-release-metadata.py") < text.index('"$python_bin" -m build')


def test_security_audit_exception_schema_rejects_expired_or_incomplete_entries(
    tmp_path: Path,
) -> None:
    script = ROOT / "scripts" / "verify-audit-exceptions.py"
    for name, payload, message in (
        (
            "expired.yml",
            "schema_version: 1\nexceptions:\n- advisory_id: PYSEC-1\n"
            "  owner: release-owner\n  rationale: temporary\n  expires_on: 2026-08-26\n",
            "expired on 2026-08-26",
        ),
        (
            "missing-owner.yml",
            "schema_version: 1\nexceptions:\n- advisory_id: PYSEC-2\n"
            "  rationale: temporary\n  expires_on: 2026-08-28\n",
            "is missing: owner",
        ),
        (
            "duplicate.yml",
            "schema_version: 1\nschema_version: 1\nexceptions: []\n",
            "Duplicate YAML key",
        ),
    ):
        source = tmp_path / name
        source.write_text(payload, encoding="utf-8")
        result = subprocess.run(
            [
                os.sys.executable,
                str(script),
                "--file",
                str(source),
                "--today",
                "2026-08-27",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1
        assert message in result.stdout


@pytest.mark.parametrize(
    ("repository", "expected_command"),
    (
        (None, "release view v0.5.0"),
        (
            "BINARYA/p2p-Engine",
            "release view v0.5.0 --repo BINARYA/p2p-Engine",
        ),
    ),
)
def test_publish_script_refuses_existing_release_before_create(
    tmp_path: Path,
    repository: str | None,
    expected_command: str,
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in (
        "p2p_engine-0.5.0-py3-none-any.whl",
        "p2p_engine-0.5.0.tar.gz",
        "SHA256SUMS",
    ):
        (dist / name).write_bytes(b"artifact")
    notes = tmp_path / "notes.md"
    notes.write_text("P2P Engine 0.5.0\n", encoding="utf-8")
    log = tmp_path / "gh.log"
    fake = tmp_path / "gh"
    fake.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$*\" >> \"$FAKE_GH_LOG\"\n"
        "test \"$1 $2\" = 'release view' && exit 0\n"
        "exit 91\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    env = os.environ.copy()
    env.update({"GH_BIN": str(fake), "FAKE_GH_LOG": str(log)})
    if repository is None:
        env.pop("GITHUB_REPOSITORY", None)
    else:
        env["GITHUB_REPOSITORY"] = repository

    result = subprocess.run(
        [
            str(ROOT / "scripts" / "publish-release.sh"),
            "--tag",
            "v0.5.0",
            "--dist",
            str(dist),
            "--notes",
            str(notes),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )

    assert result.returncode == 1
    assert "create-only publication refused" in result.stderr
    assert log.read_text(encoding="utf-8").splitlines() == [expected_command]

from __future__ import annotations

import importlib.util
import os
import subprocess
import tomllib
from pathlib import Path

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


def _workflow(name: str) -> tuple[dict[str, object], str]:
    text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    return yaml.safe_load(text), text


def test_ci_is_pre_tag_and_uses_supported_matrix_without_dist_sharing() -> None:
    workflow, text = _workflow("ci.yml")
    source = workflow["jobs"]["source"]

    assert source["strategy"]["matrix"]["python-version"] == ["3.11", "3.14"]
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request:" in text
    assert "branches:\n      - main" in text
    assert "workflow_dispatch:" in text
    assert "dist/" not in text
    assert "coverage" not in text.lower()


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


def test_candidate_builder_compares_clean_builds_before_checksums() -> None:
    text = (ROOT / "scripts" / "build-release-candidate.sh").read_text(
        encoding="utf-8"
    )

    assert "SOURCE_DATE_EPOCH is required" in text
    assert 'cmp -s "$artifact" "$peer"' in text
    assert "non-reproducible member:" in text
    assert text.index('cmp -s "$artifact" "$peer"') < text.index("sha256sum")


def test_owner_approved_package_metadata_is_complete_and_unreleased_is_allowed() -> None:
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


def test_release_finalization_gate_rejects_intentional_unreleased_state() -> None:
    issues = METADATA.validate_release_metadata(ROOT, require_release=True)

    assert "CHANGELOG.md requires a dated 0.5.0 section" in issues
    assert "CHANGELOG.md still marks 0.5.0 as Unreleased" in issues
    assert "release notes are still marked Unreleased" in issues
    assert all("license" not in issue.lower() for issue in issues)
    assert all("identity" not in issue.lower() for issue in issues)
    assert all("urls" not in issue.lower() for issue in issues)


def test_candidate_build_fails_cleanly_before_build_while_release_is_unreleased(
    tmp_path: Path,
) -> None:
    output = tmp_path / "candidate"
    env = os.environ.copy()
    env.update({"PYTHON_BIN": os.fspath(Path(os.sys.executable)), "SOURCE_DATE_EPOCH": "1"})

    result = subprocess.run(
        [
            str(ROOT / "scripts" / "build-release-candidate.sh"),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )

    assert result.returncode == 1
    assert "CHANGELOG.md requires a dated 0.5.0 section" in result.stdout
    assert not output.exists() or not any(output.iterdir())


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


def test_publish_script_refuses_existing_release_before_create(tmp_path: Path) -> None:
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
    assert log.read_text(encoding="utf-8").splitlines() == ["release view v0.5.0"]

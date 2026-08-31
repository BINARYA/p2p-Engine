#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
import zipfile
from dataclasses import dataclass
from email.parser import Parser
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WheelIdentity:
    path: Path
    distribution: str
    version: str
    sha256: str


@dataclass(frozen=True)
class IsolatedUvLayout:
    root: Path
    tools: Path
    binaries: Path
    python: Path
    cache: Path
    home: Path
    project: Path

    def environment(self, base: dict[str, str] | None = None) -> dict[str, str]:
        environment = dict(base or os.environ)
        environment.update(
            {
                "UV_TOOL_DIR": str(self.tools),
                "UV_TOOL_BIN_DIR": str(self.binaries),
                "UV_PYTHON_INSTALL_DIR": str(self.python),
                "UV_CACHE_DIR": str(self.cache),
                "HOME": str(self.home),
                "USERPROFILE": str(self.home),
                "APPDATA": str(self.home / "AppData" / "Roaming"),
                "LOCALAPPDATA": str(self.home / "AppData" / "Local"),
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Keyring",
            }
        )
        environment.pop("PYTHONPATH", None)
        environment["PATH"] = os.pathsep.join(
            [str(self.binaries), environment.get("PATH", "")]
        )
        return environment


def inspect_wheel(path: Path) -> WheelIdentity:
    raw_path = str(path)
    if any(character in raw_path for character in "*?[]"):
        raise ValueError("--wheel must name one literal file, not a glob")
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file() or resolved.suffix != ".whl":
        raise ValueError(f"--wheel must name one existing .whl file: {resolved}")

    metadata_members: list[str]
    with zipfile.ZipFile(resolved) as archive:
        metadata_members = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_members) != 1:
            raise ValueError(
                f"wheel must contain exactly one dist-info/METADATA: {resolved}"
            )
        metadata = Parser().parsestr(
            archive.read(metadata_members[0]).decode("utf-8", errors="strict")
        )

    distribution = str(metadata.get("Name", "")).strip()
    version = str(metadata.get("Version", "")).strip()
    expected_filename = f"p2p_engine-{version}-py3-none-any.whl"
    if distribution != "p2p-engine" or resolved.name != expected_filename:
        raise ValueError(
            "wrong wheel identity: expected p2p-engine metadata and "
            f"{expected_filename}, got {distribution!r} and {resolved.name!r}"
        )
    return WheelIdentity(
        path=resolved,
        distribution=distribution,
        version=version,
        sha256=_file_sha256(resolved),
    )


def make_layout(root: Path, *, project_root: Path | None = None) -> IsolatedUvLayout:
    resolved = Path(root).resolve()
    if not resolved.is_dir():
        raise ValueError(f"isolated root must already exist: {resolved}")
    project = (project_root or resolved / "projects" / "candidate").resolve()
    if not project.is_relative_to(resolved):
        raise ValueError("project root must stay inside the isolated temporary root")
    if project.exists() and any(project.iterdir()):
        raise ValueError(f"project root must be absent or empty: {project}")

    layout = IsolatedUvLayout(
        root=resolved,
        tools=resolved / "uv" / "tools",
        binaries=resolved / "uv" / "bin",
        python=resolved / "uv" / "python",
        cache=resolved / "uv" / "cache",
        home=resolved / "home",
        project=project,
    )
    for directory in (
        layout.tools,
        layout.binaries,
        layout.python,
        layout.cache,
        layout.home,
        layout.project.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return layout


def project_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


class Harness:
    def __init__(
        self,
        *,
        uv: str,
        python_request: str,
        layout: IsolatedUvLayout,
        source_root: Path,
    ) -> None:
        self.uv = str(Path(uv).resolve()) if Path(uv).is_file() else uv
        self.python_request = python_request
        self.layout = layout
        self.source_root = source_root.resolve()
        self.environment = layout.environment()

    def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        expected_codes: tuple[int, ...] = (0,),
        environment: dict[str, str] | None = None,
        timeout: int = 120,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            command,
            cwd=cwd or self.layout.root,
            env=environment or self.environment,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        if completed.returncode not in expected_codes:
            raise AssertionError(
                json.dumps(
                    {
                        "command": command,
                        "returncode": completed.returncode,
                        "stdout": completed.stdout,
                        "stderr": completed.stderr,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return completed

    def install(self, wheel: WheelIdentity, *, force: bool) -> None:
        command = [
            self.uv,
            "tool",
            "install",
            "--managed-python",
            "--python",
            self.python_request,
            "--no-config",
        ]
        if force:
            command.append("--force")
        command.append(str(wheel.path))
        self.run(command, timeout=300)
        self.assert_entry_points(wheel.version)

    def uninstall(self) -> None:
        self.run([self.uv, "tool", "uninstall", "p2p-engine"])
        for name in ("p2p", "p2p-mcp-server"):
            if _entry_point(self.layout.binaries, name, required=False) is not None:
                raise AssertionError(f"uv uninstall left entry point installed: {name}")

    def assert_entry_points(self, expected_version: str) -> None:
        p2p = _entry_point(self.layout.binaries, "p2p")
        mcp = _entry_point(self.layout.binaries, "p2p-mcp-server")
        self.run([str(p2p), "--help"], cwd=self.layout.root)
        self.run([str(mcp), "--help"], cwd=self.layout.root)
        payload = self.run_json([str(p2p), "version", "--format", "json"])
        if payload["data"]["engine_version"] != expected_version:
            raise AssertionError(payload)

    def run_json(
        self,
        command: list[str],
        *,
        expected_codes: tuple[int, ...] = (0,),
    ) -> dict[str, Any]:
        completed = self.run(command, expected_codes=expected_codes)
        payload = json.loads(completed.stdout)
        if payload.get("contract_version") != "p2p-cli/v1":
            raise AssertionError(payload)
        return payload

    def initialize_and_smoke(self, wheel: WheelIdentity) -> str:
        p2p = _entry_point(self.layout.binaries, "p2p")
        project = self.layout.project
        initialized = self.run_json(
            [
                str(p2p),
                "init",
                "uv installed smoke",
                "--starter",
                "generic",
                "--agent",
                "codex",
                "--format",
                "json",
                "--operation-key",
                "uv-installed-smoke-init-v1",
                "--root",
                str(project),
            ]
        )
        if not initialized.get("ok"):
            raise AssertionError(initialized)
        if (project / ".venv").exists():
            raise AssertionError("uv qualification project unexpectedly contains .venv")

        self.run([str(p2p), "doctor", "--root", str(project)])
        runtime = self.run_json(
            [str(p2p), "runtime", "status", "--format", "json", "--root", str(project)]
        )
        if not runtime["data"]["compatible"]:
            raise AssertionError(runtime)
        self.run([str(p2p), "agent", "doctor", "all", "--root", str(project)])
        self.run(
            [
                str(p2p),
                "agent",
                "instructions",
                "refresh",
                "--profile",
                "codex",
                "--root",
                str(project),
            ]
        )
        validated = self.run_json(
            [str(p2p), "validate", "--format", "json", "--root", str(project)]
        )
        if not validated.get("ok"):
            raise AssertionError(validated)

        self.assert_import_provenance(wheel)
        self.assert_mcp_stdio([str(_entry_point(self.layout.binaries, "p2p-mcp-server"))])
        return project_digest(project)

    def initialize_sqlite_smoke(self) -> None:
        p2p = _entry_point(self.layout.binaries, "p2p")
        project = self.layout.root / "projects" / "sqlite-candidate"
        bundle = project / "candidate.p2pbundle"
        initialized = self.run_json(
            [
                str(p2p),
                "init",
                "uv installed SQLite smoke",
                "--starter",
                "generic",
                "--agent",
                "codex",
                "--storage-adapter",
                "sqlite",
                "--format",
                "json",
                "--operation-key",
                "uv-installed-sqlite-smoke-init-v1",
                "--root",
                str(project),
            ]
        )
        if not initialized.get("ok"):
            raise AssertionError(initialized)
        database = project / ".p2p" / "local" / "project.sqlite3"
        if not database.is_file() or (project / ".p2p" / "project.yml").exists():
            raise AssertionError("SQLite candidate did not activate one authoritative backend")
        exported = self.run_json(
            [
                str(p2p),
                "project",
                "memory",
                "bundle-export",
                "--output",
                str(bundle),
                "--format",
                "json",
                "--root",
                str(project),
            ]
        )
        if not exported.get("ok") or not bundle.is_file():
            raise AssertionError(exported)
        validated = self.run_json(
            [str(p2p), "validate", "--format", "json", "--root", str(project)]
        )
        if not validated.get("ok"):
            raise AssertionError(validated)
        self.assert_sqlite_mcp_read(project)

    def assert_sqlite_mcp_read(self, project: Path) -> None:
        requests = (
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "p2p_project_bundle_export_metadata",
                    "arguments": {"root": str(project)},
                },
            },
        )
        completed = self.run(
            [
                str(_entry_point(self.layout.binaries, "p2p-mcp-server")),
                "--root",
                str(project),
            ],
            input_text="".join(json.dumps(request) + "\n" for request in requests),
            timeout=30,
        )
        responses = [
            json.loads(line) for line in completed.stdout.splitlines() if line.strip()
        ]
        if [response.get("id") for response in responses] != [1, 2]:
            raise AssertionError(responses)
        if "error" in responses[1] or responses[1].get("result", {}).get("isError"):
            raise AssertionError(responses[1])

    def assert_import_provenance(self, wheel: WheelIdentity) -> None:
        tool_python = _tool_python(self.layout.tools)
        program = """
from importlib import metadata, resources
from pathlib import Path
import json
import keyring
import p2p_engine
import sys

expected_version, source_root = sys.argv[1:]
module_path = Path(p2p_engine.__file__).resolve()
assert metadata.version('p2p-engine') == expected_version
assert p2p_engine.__version__ == expected_version
assert not module_path.is_relative_to(Path(source_root).resolve())
assert resources.files('p2p_engine.resources.contracts').joinpath(
    'wavekit-cli-fixtures-v1.json'
).is_file()
assert resources.files('p2p_engine.resources.verticals.base_project').joinpath(
    'manifest.yml'
).is_file()
assert keyring.get_keyring().__class__.__module__.startswith('keyring.backends.null')
print(json.dumps({'python': sys.version.split()[0], 'module': str(module_path)}))
"""
        self.run(
            [
                str(tool_python),
                "-c",
                program,
                wheel.version,
                str(self.source_root),
            ],
            cwd=self.layout.root,
        )

    def assert_mcp_stdio(self, command: list[str]) -> None:
        requests = (
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        completed = self.run(
            [*command, "--root", str(self.layout.project)],
            input_text="".join(json.dumps(request) + "\n" for request in requests),
            timeout=30,
        )
        responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
        if [response.get("id") for response in responses] != [1, 2]:
            raise AssertionError(responses)
        names = {tool["name"] for tool in responses[1]["result"]["tools"]}
        if "p2p_context" not in names or "p2p_work_plan" not in names:
            raise AssertionError(sorted(names))

    def assert_exact_and_cache_modes(self, wheel: WheelIdentity) -> None:
        base = [
            self.uv,
            "tool",
            "run",
            "--isolated",
            "--managed-python",
            "--python",
            self.python_request,
            "--no-config",
            "--from",
            str(wheel.path),
        ]
        warm = self.run([*base, "p2p", "version", "--format", "json"], timeout=300)
        if json.loads(warm.stdout)["data"]["engine_version"] != wheel.version:
            raise AssertionError(warm.stdout)

        offline = [*base[:3], "--offline", *base[3:]]
        cached = self.run([*offline, "p2p", "version", "--format", "json"])
        if json.loads(cached.stdout)["data"]["engine_version"] != wheel.version:
            raise AssertionError(cached.stdout)
        self.assert_mcp_stdio([*offline, "p2p-mcp-server"])

        cold_environment = dict(self.environment)
        cold_environment["UV_CACHE_DIR"] = str(self.layout.root / "uv" / "cold-cache")
        cold_environment["UV_TOOL_DIR"] = str(self.layout.root / "uv" / "cold-tools")
        cold_environment["UV_TOOL_BIN_DIR"] = str(self.layout.root / "uv" / "cold-bin")
        failed = self.run(
            [*offline, "p2p", "version", "--format", "json"],
            expected_codes=tuple(range(1, 256)),
            environment=cold_environment,
        )
        failure_text = f"{failed.stdout}\n{failed.stderr}".lower()
        if not any(term in failure_text for term in ("offline", "cache", "not found")):
            raise AssertionError(failure_text)

    def lifecycle(
        self,
        previous: WheelIdentity,
        candidate: WheelIdentity,
    ) -> None:
        lifecycle_project = self.layout.root / "projects" / "lifecycle"
        self.install(previous, force=True)
        p2p = _entry_point(self.layout.binaries, "p2p")
        self.run_json(
            [
                str(p2p),
                "init",
                "uv lifecycle smoke",
                "--starter",
                "generic",
                "--agent",
                "generic",
                "--format",
                "json",
                "--operation-key",
                "uv-lifecycle-init-v1",
                "--root",
                str(lifecycle_project),
            ]
        )
        stable_digest = project_digest(lifecycle_project)

        self.install(candidate, force=True)
        p2p = _entry_point(self.layout.binaries, "p2p")
        incompatible = self.run_json(
            [
                str(p2p),
                "runtime",
                "status",
                "--format",
                "json",
                "--root",
                str(lifecycle_project),
            ],
            expected_codes=(0, 1),
        )
        if previous.version != candidate.version and incompatible["data"]["compatible"]:
            raise AssertionError(incompatible)
        if project_digest(lifecycle_project) != stable_digest:
            raise AssertionError("candidate replacement mutated lifecycle project state")

        self.install(previous, force=True)
        p2p = _entry_point(self.layout.binaries, "p2p")
        rolled_back = self.run_json(
            [
                str(p2p),
                "runtime",
                "status",
                "--format",
                "json",
                "--root",
                str(lifecycle_project),
            ]
        )
        if not rolled_back["data"]["compatible"]:
            raise AssertionError(rolled_back)
        self.install(candidate, force=True)
        if project_digest(lifecycle_project) != stable_digest:
            raise AssertionError("rollback/reinstall mutated lifecycle project state")


def _entry_point(directory: Path, name: str, *, required: bool = True) -> Path | None:
    for candidate_name in (name, f"{name}.exe", f"{name}.cmd"):
        candidate = directory / candidate_name
        if candidate.is_file():
            return candidate.resolve()
    if required:
        raise AssertionError(f"missing uv tool entry point {name!r} under {directory}")
    return None


def _tool_python(tool_directory: Path) -> Path:
    candidates = (
        tool_directory / "p2p-engine" / "bin" / "python",
        tool_directory / "p2p-engine" / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            # The tool interpreter is commonly a symlink to uv's managed base
            # Python. Executing the resolved target would lose the tool venv.
            return candidate.absolute()
    raise AssertionError(f"missing p2p-engine tool Python under {tool_directory}")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def report_failure(message: str) -> None:
    print(message, file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS", "").lower() != "true":
        return
    annotation = " | ".join(message.splitlines())
    escaped = annotation.replace("%", "%25")[-3000:]
    print(
        f"::error title=uv installed-wheel qualification failed::{escaped}",
        flush=True,
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qualify one immutable P2P Engine wheel in isolated uv directories."
    )
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--previous-wheel", type=Path)
    parser.add_argument("--python", default="3.12", dest="python_request")
    parser.add_argument("--uv", default="uv")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Optional empty path below the temporary harness root.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        candidate = inspect_wheel(args.wheel)
        previous = inspect_wheel(args.previous_wheel) if args.previous_wheel else None
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        report_failure(f"uv installed-wheel input error: {exc}")
        return 2

    temporary_parent = Path(os.environ.get("P2P_UV_TEST_TMPDIR", tempfile.gettempdir()))
    temporary_parent = temporary_parent.expanduser().resolve()
    if not temporary_parent.is_dir():
        report_failure(f"temporary parent is not a directory: {temporary_parent}")
        return 2

    source_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="p2p-uv-installed-", dir=temporary_parent) as raw:
        isolated_root = Path(raw).resolve()
        requested_project = None
        if args.project_root is not None:
            requested = args.project_root.expanduser()
            requested_project = (
                requested.resolve()
                if requested.is_absolute()
                else (isolated_root / requested).resolve()
            )
        try:
            layout = make_layout(isolated_root, project_root=requested_project)
            harness = Harness(
                uv=args.uv,
                python_request=args.python_request,
                layout=layout,
                source_root=source_root,
            )
            uv_version = harness.run([harness.uv, "--version"]).stdout.strip()
            if previous is not None:
                harness.lifecycle(previous, candidate)
            harness.install(candidate, force=True)
            before_uninstall = harness.initialize_and_smoke(candidate)
            harness.initialize_sqlite_smoke()
            harness.assert_exact_and_cache_modes(candidate)
            harness.uninstall()
            after_uninstall = project_digest(layout.project)
            if after_uninstall != before_uninstall:
                raise AssertionError("uv uninstall mutated candidate project state")
            harness.install(candidate, force=True)
            if project_digest(layout.project) != before_uninstall:
                raise AssertionError("uv reinstall mutated candidate project state")
            tool_python = _tool_python(layout.tools)
            python_version = harness.run(
                [str(tool_python), "-c", "import platform; print(platform.python_version())"]
            ).stdout.strip()
        except (AssertionError, OSError, subprocess.SubprocessError, ValueError) as exc:
            report_failure(f"uv installed-wheel qualification failed: {exc}")
            return 1

    evidence = {
        "schema": "p2p-uv-installation-evidence/v1",
        "wheel": str(candidate.path),
        "wheel_filename": candidate.path.name,
        "wheel_version": candidate.version,
        "wheel_sha256": candidate.sha256,
        "previous_wheel_version": previous.version if previous else None,
        "uv": uv_version,
        "managed_python_request": args.python_request,
        "managed_python_version": python_version,
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "source_checkout_imported": False,
        "project_venv_created": False,
        "project_digest_preserved_across_uninstall": True,
    }
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception:
        report_failure(
            "uv installed-wheel qualification raised an unexpected exception:\n"
            f"{traceback.format_exc()}"
        )
        raise
    raise SystemExit(exit_code)

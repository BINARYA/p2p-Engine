from __future__ import annotations

import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version

P2P_DISTRIBUTION_NAME = "p2p-engine"
P2P_GITHUB_REPOSITORY = "https://github.com/BINARYA/p2p-Engine"
P2P_MANAGED_PYTHON = "3.12"
SUPPORTED_UV_VERSION = "0.12.6"


@dataclass(frozen=True)
class RuntimeInvocation:
    mode: str
    executable: str
    args: tuple[str, ...]
    version: str | None = None
    source: str | None = None
    reason: str = ""
    available: bool = True

    @property
    def command(self) -> list[str]:
        if not self.executable:
            return []
        return [self.executable, *self.args]


def exact_release_version(version: str) -> str:
    candidate = str(version or "").strip()
    try:
        parsed = Version(candidate)
    except InvalidVersion as exc:
        raise ValueError(f"Invalid exact P2P Engine version: {candidate or '<empty>'}") from exc
    if not candidate or parsed.local is not None or str(parsed) != candidate:
        raise ValueError(f"P2P Engine release version must be canonical and exact: {candidate or '<empty>'}")
    return candidate


def github_release_wheel_url(version: str) -> str:
    exact = exact_release_version(version)
    return (
        f"{P2P_GITHUB_REPOSITORY}/releases/download/v{exact}/"
        f"p2p_engine-{exact}-py3-none-any.whl"
    )


def persistent_install_invocation(
    version: str,
    *,
    uv_executable: str = "uv",
    force: bool = False,
) -> RuntimeInvocation:
    exact = exact_release_version(version)
    args = [
        "tool",
        "install",
        "--managed-python",
        "--python",
        P2P_MANAGED_PYTHON,
        "--no-config",
    ]
    if force:
        args.append("--force")
    args.append(github_release_wheel_url(exact))
    return RuntimeInvocation(
        mode="uv-persistent",
        executable=str(uv_executable),
        args=tuple(args),
        version=exact,
        source="github-release-wheel",
        reason="Recommended persistent user-level P2P Engine tool.",
    )


def verified_local_wheel_install_invocation(
    wheel: Path,
    *,
    uv_executable: str = "uv",
    force: bool = False,
) -> RuntimeInvocation:
    resolved = Path(wheel).expanduser().resolve()
    if not resolved.is_file() or resolved.suffix != ".whl":
        raise ValueError(f"Verified wheel must be one existing .whl file: {resolved}")
    args = [
        "tool",
        "install",
        "--managed-python",
        "--python",
        P2P_MANAGED_PYTHON,
        "--no-config",
    ]
    if force:
        args.append("--force")
    args.append(str(resolved))
    return RuntimeInvocation(
        mode="verified-local-wheel",
        executable=str(uv_executable),
        args=tuple(args),
        source="verified-local-wheel",
        reason="Install owner-verified local release bytes.",
    )


def exact_version_invocation(
    version: str,
    entry_point: str,
    *entry_args: str,
    uv_executable: str = "uv",
    uvx: bool = False,
) -> RuntimeInvocation:
    exact = exact_release_version(version)
    if entry_point not in {"p2p", "p2p-mcp-server"}:
        raise ValueError(f"Unsupported P2P Engine entry point: {entry_point}")
    if uvx:
        args = [
            "--isolated",
            "--managed-python",
            "--python",
            P2P_MANAGED_PYTHON,
            "--no-config",
            "--from",
            github_release_wheel_url(exact),
            entry_point,
            *entry_args,
        ]
    else:
        args = [
            "tool",
            "run",
            "--isolated",
            "--managed-python",
            "--python",
            P2P_MANAGED_PYTHON,
            "--no-config",
            "--from",
            github_release_wheel_url(exact),
            entry_point,
            *entry_args,
        ]
    return RuntimeInvocation(
        mode="uv-exact",
        executable=str(uv_executable),
        args=tuple(args),
        version=exact,
        source="github-release-wheel",
        reason="Owner-run exact-version runtime for an incompatible project.",
    )


def future_index_invocation(version: str) -> RuntimeInvocation:
    exact = exact_release_version(version)
    return RuntimeInvocation(
        mode="public-index-future",
        executable="",
        args=(),
        version=exact,
        source="public-index-future",
        reason="Unavailable until the exact package version is verified on a public index.",
        available=False,
    )


def standalone_binary_invocation() -> RuntimeInvocation:
    return RuntimeInvocation(
        mode="standalone-binary",
        executable="",
        args=(),
        reason="P2P Engine does not currently publish a standalone compiled binary.",
        available=False,
    )


def project_cli_candidates(root: Path) -> tuple[Path, ...]:
    resolved = Path(root).resolve()
    return (
        resolved / ".venv" / "bin" / "p2p",
        resolved / ".venv" / "Scripts" / "p2p.exe",
        resolved / ".venv" / "Scripts" / "p2p",
    )


def project_python_candidates(root: Path) -> tuple[Path, ...]:
    resolved = Path(root).resolve()
    return (
        resolved / ".venv" / "bin" / "python",
        resolved / ".venv" / "Scripts" / "python.exe",
        resolved / ".venv" / "Scripts" / "python",
    )


def first_existing(candidates: Sequence[Path]) -> Path | None:
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def render_shell_command(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


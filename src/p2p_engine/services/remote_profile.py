from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RemoteProjectProfile:
    mode: str
    provider: str
    remote: str | None
    url: str | None
    review_request_mode: str
    opens_external_request: bool
    path: Path


def _yaml_dump(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def _read_yaml_mapping(path: Path, default: dict[str, object] | None = None) -> dict[str, object]:
    if not path.exists():
        return default or {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else (default or {})


class RemoteProfileService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        remote_url_resolver: Callable[[Path, str], str | None],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.remote_url_resolver = remote_url_resolver

    def project_path(self) -> Path:
        return self.p2p_dir / "project.yml"

    def default_payload(
        self,
        *,
        repository_mode: str,
        provider: str | None,
        remote: str,
        url: str | None,
    ) -> dict[str, object]:
        if repository_mode == "local":
            if provider or url:
                raise ValueError("Remote provider and URL options require --repository cloud")
            return self._payload(mode="local", provider="local", remote=None, url=None)

        selected_provider = (provider or "generic").strip().lower()
        if selected_provider not in {"generic", "github", "gitlab"}:
            raise ValueError("Remote provider must be generic, github, or gitlab")
        selected_remote = (remote or "origin").strip()
        if not selected_remote:
            raise ValueError("Remote name is required for cloud-backed projects")
        resolved_url = url or self.remote_url_resolver(self.root, selected_remote)
        return self._payload(
            mode="remote",
            provider=selected_provider,
            remote=selected_remote,
            url=resolved_url,
        )

    def show(self) -> RemoteProjectProfile:
        project_file = self.project_path()
        data = _read_yaml_mapping(project_file, default={})
        remote_data = data.get("remote", {})
        if not isinstance(remote_data, dict):
            remote_data = {}
        review_data = remote_data.get("review_request", {})
        if not isinstance(review_data, dict):
            review_data = {}
        mode = str(remote_data.get("mode") or "local")
        provider = str(remote_data.get("provider") or ("local" if mode == "local" else "generic"))
        remote = remote_data.get("remote")
        url = remote_data.get("url")
        return RemoteProjectProfile(
            mode=mode,
            provider=provider,
            remote=str(remote) if remote else None,
            url=str(url) if url else None,
            review_request_mode=str(review_data.get("mode") or "advisory"),
            opens_external_request=bool(review_data.get("opens_external_request", False)),
            path=project_file.relative_to(self.root),
        )

    def configure(
        self,
        *,
        mode: str,
        provider: str | None = None,
        remote: str = "origin",
        url: str | None = None,
    ) -> RemoteProjectProfile:
        mode = mode.strip().lower()
        if mode not in {"local", "remote"}:
            raise ValueError("Remote project mode must be local or remote")

        provider = (provider or ("local" if mode == "local" else "generic")).strip().lower()
        if provider not in {"local", "generic", "github", "gitlab"}:
            raise ValueError("Remote provider must be local, generic, github, or gitlab")
        if mode == "local":
            provider = "local"
            remote = ""
            url = None
        else:
            if provider == "local":
                raise ValueError("Remote-backed projects cannot use provider local")
            if not url:
                url = self.remote_url_resolver(self.root, remote)
            if not url:
                raise ValueError(f"Remote URL is required and Git remote was not found: {remote}")

        project_file = self.project_path()
        data = _read_yaml_mapping(project_file, default={})
        data["remote"] = self._payload(
            mode=mode,
            provider=provider,
            remote=remote or None,
            url=url,
        )
        project_file.parent.mkdir(parents=True, exist_ok=True)
        project_file.write_text(_yaml_dump(data), encoding="utf-8")
        return self.show()

    def _payload(
        self,
        *,
        mode: str,
        provider: str,
        remote: str | None,
        url: str | None,
    ) -> dict[str, object]:
        return {
            "mode": mode,
            "provider": provider,
            "remote": remote,
            "url": url,
            "review_request": {
                "mode": "advisory",
                "opens_external_request": False,
            },
        }

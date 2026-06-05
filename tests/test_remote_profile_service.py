from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.services.remote_profile import RemoteProfileService


def _service(root: Path, urls: dict[str, str | None] | None = None) -> RemoteProfileService:
    return RemoteProfileService(
        root=root,
        p2p_dir=root / ".p2p",
        remote_url_resolver=lambda _root, remote: (urls or {}).get(remote),
    )


def test_remote_profile_service_default_payloads(tmp_path: Path) -> None:
    service = _service(tmp_path, {"origin": "git@example.com:demo.git"})

    local = service.default_payload(repository_mode="local", provider=None, remote="origin", url=None)
    remote = service.default_payload(repository_mode="cloud", provider="github", remote="origin", url=None)

    assert local == {
        "mode": "local",
        "provider": "local",
        "remote": None,
        "url": None,
        "review_request": {
            "mode": "advisory",
            "opens_external_request": False,
        },
    }
    assert remote["mode"] == "remote"
    assert remote["provider"] == "github"
    assert remote["remote"] == "origin"
    assert remote["url"] == "git@example.com:demo.git"
    assert remote["review_request"]["opens_external_request"] is False


def test_remote_profile_service_read_fallback_and_configure_local(tmp_path: Path) -> None:
    service = _service(tmp_path)

    fallback = service.show()

    assert fallback.mode == "local"
    assert fallback.provider == "local"
    assert fallback.remote is None
    assert fallback.url is None
    assert fallback.path == Path(".p2p/project.yml")

    (tmp_path / ".p2p").mkdir()
    (tmp_path / ".p2p" / "project.yml").write_text(
        yaml.safe_dump({"remote": {"mode": "remote", "review_request": []}}, sort_keys=False),
        encoding="utf-8",
    )
    malformed = service.show()
    assert malformed.mode == "remote"
    assert malformed.provider == "generic"
    assert malformed.review_request_mode == "advisory"
    assert malformed.opens_external_request is False

    configured = service.configure(mode="local", provider="github", remote="origin", url="git@example.com:demo.git")

    assert configured.mode == "local"
    assert configured.provider == "local"
    assert configured.remote is None
    assert configured.url is None

    stored = yaml.safe_load((tmp_path / ".p2p" / "project.yml").read_text(encoding="utf-8"))
    assert stored["remote"]["mode"] == "local"
    assert stored["remote"]["provider"] == "local"
    assert stored["remote"]["remote"] is None
    assert stored["remote"]["url"] is None


def test_remote_profile_service_configure_remote_explicit_and_git_fallback(tmp_path: Path) -> None:
    service = _service(tmp_path, {"origin": "git@example.com:fallback.git"})

    explicit = service.configure(
        mode="remote",
        provider="github",
        remote="origin",
        url="git@example.com:explicit.git",
    )
    fallback = service.configure(mode="remote", provider="generic", remote="origin", url=None)

    assert explicit.mode == "remote"
    assert explicit.provider == "github"
    assert explicit.url == "git@example.com:explicit.git"
    assert fallback.mode == "remote"
    assert fallback.provider == "generic"
    assert fallback.remote == "origin"
    assert fallback.url == "git@example.com:fallback.git"


def test_remote_profile_service_rejects_invalid_init_payloads(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="Remote provider and URL options require --repository cloud"):
        service.default_payload(repository_mode="local", provider="github", remote="origin", url=None)
    with pytest.raises(ValueError, match="Remote provider and URL options require --repository cloud"):
        service.default_payload(repository_mode="local", provider=None, remote="origin", url="git@example.com:demo.git")
    with pytest.raises(ValueError, match="Remote provider must be generic, github, or gitlab"):
        service.default_payload(repository_mode="cloud", provider="bitbucket", remote="origin", url="x")
    payload = service.default_payload(repository_mode="cloud", provider="github", remote="", url="x")
    assert payload["remote"] == "origin"


def test_remote_profile_service_rejects_invalid_configure_inputs(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="Remote project mode must be local or remote"):
        service.configure(mode="cloud")
    with pytest.raises(ValueError, match="Remote provider must be local, generic, github, or gitlab"):
        service.configure(mode="remote", provider="bitbucket", remote="origin", url="x")
    with pytest.raises(ValueError, match="Remote-backed projects cannot use provider local"):
        service.configure(mode="remote", provider="local", remote="origin", url="x")
    with pytest.raises(ValueError, match="Remote URL is required and Git remote was not found: origin"):
        service.configure(mode="remote", provider="generic", remote="origin", url=None)

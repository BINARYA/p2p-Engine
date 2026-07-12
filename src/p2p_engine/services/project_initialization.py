from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from p2p_engine.services.agent_instructions import AgentInstructionsResult
from p2p_engine.services.agent_selection import AgentProfileSelection, select_agent_profile
from p2p_engine.services.gitignore_hygiene import GitignoreHygieneResult, apply_gitignore_hygiene
from p2p_engine.services.mcp_hints import McpHint, build_mcp_hint
from p2p_engine.services.project_maturity import (
    PROJECT_DOMAIN_TEMPLATES,
    domain_setup_next_actions_payload,
    domain_state_payload,
    normalize_project_domain,
    rubrics_payload,
)
from p2p_engine.services.readiness import DEFAULT_READINESS_PROFILE_ID

REPOSITORY_MODES = {"local", "cloud"}


def normalize_repository_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in REPOSITORY_MODES:
        raise ValueError("Repository mode must be local or cloud")
    return normalized


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def _yaml_dump(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


@dataclass(frozen=True)
class ProjectInitializationResult:
    created: list[Path]
    agent_selection: AgentProfileSelection
    agent_instructions: AgentInstructionsResult
    mcp_hint: McpHint
    gitignore_hygiene: GitignoreHygieneResult


class ProjectInitializationService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        remote_profile_default_payload: Callable[..., dict[str, object]],
        readiness_default_profile_payload: Callable[[], dict[str, object]],
        permissions_default_policy_payload: Callable[..., dict[str, object]],
        refresh_agent_instructions: Callable[..., AgentInstructionsResult],
        select_agent_profile_fn: Callable[[str | None], AgentProfileSelection] = select_agent_profile,
        build_mcp_hint_fn: Callable[..., McpHint] = build_mcp_hint,
        apply_gitignore_hygiene_fn: Callable[[Path], GitignoreHygieneResult] = apply_gitignore_hygiene,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.remote_profile_default_payload = remote_profile_default_payload
        self.readiness_default_profile_payload = readiness_default_profile_payload
        self.permissions_default_policy_payload = permissions_default_policy_payload
        self.refresh_agent_instructions = refresh_agent_instructions
        self.select_agent_profile = select_agent_profile_fn
        self.build_mcp_hint = build_mcp_hint_fn
        self.apply_gitignore_hygiene = apply_gitignore_hygiene_fn

    def init_project(
        self,
        name: str,
        agent_profile: str | None = None,
        repository_mode: str = "local",
        project_domain: str = "none",
        rubric_enabled: dict[str, bool] | None = None,
        owner: str | None = None,
        remote_provider: str | None = None,
        remote_name: str = "origin",
        remote_url_value: str | None = None,
    ) -> list[Path]:
        return self.init_project_with_summary(
            name=name,
            agent_profile=agent_profile,
            repository_mode=repository_mode,
            project_domain=project_domain,
            rubric_enabled=rubric_enabled,
            owner=owner,
            remote_provider=remote_provider,
            remote_name=remote_name,
            remote_url_value=remote_url_value,
        ).created

    def init_project_with_summary(
        self,
        name: str,
        agent_profile: str | None = None,
        repository_mode: str = "local",
        project_domain: str = "none",
        rubric_enabled: dict[str, bool] | None = None,
        owner: str | None = None,
        remote_provider: str | None = None,
        remote_name: str = "origin",
        remote_url_value: str | None = None,
    ) -> ProjectInitializationResult:
        agent_selection = self.select_agent_profile(agent_profile)
        repository_mode = normalize_repository_mode(repository_mode)
        project_domain = normalize_project_domain(project_domain)
        remote_profile = self.remote_profile_default_payload(
            repository_mode=repository_mode,
            provider=remote_provider,
            remote=remote_name,
            url=remote_url_value,
        )
        files = self._bootstrap_files(
            name=name,
            repository_mode=repository_mode,
            project_domain=project_domain,
            rubric_enabled=rubric_enabled,
            owner=owner,
            remote_profile=remote_profile,
        )
        created = self._write_missing_files(files)
        created.extend(self._create_missing_directories())
        gitignore_hygiene = self.apply_gitignore_hygiene(self.root)
        if gitignore_hygiene.status == "applied" and gitignore_hygiene.path not in created:
            created.append(gitignore_hygiene.path)
        mcp_hint = self.build_mcp_hint(self.root, project_name=name)
        instructions = self.refresh_agent_instructions(
            profile=agent_selection.effective_profile,
            repository_mode=repository_mode,
        )
        for path in [*instructions.created, *instructions.updated]:
            if path not in created:
                created.append(path)
        return ProjectInitializationResult(
            created=created,
            agent_selection=agent_selection,
            agent_instructions=instructions,
            mcp_hint=mcp_hint,
            gitignore_hygiene=gitignore_hygiene,
        )

    def _bootstrap_files(
        self,
        *,
        name: str,
        repository_mode: str,
        project_domain: str,
        rubric_enabled: dict[str, bool] | None,
        owner: str | None,
        remote_profile: dict[str, object],
    ) -> dict[Path, str]:
        files: dict[Path, str] = {
            self.p2p_dir / "project.yml": _yaml_dump(
                {
                    "project": {
                        "id": _slugify(name),
                        "name": name,
                        "version": "0.1.0",
                        "status": "active",
                        "domain": project_domain,
                    },
                    "storage": {
                        "mode": "file_based",
                        "documents_format": "markdown",
                        "structured_data_format": "yaml",
                    },
                    "workflow": {"current_phase": "cli_managed"},
                    "ai": {"mode": "prompt_only", "direct_invocation": False},
                    "repository": {
                        "mode": repository_mode,
                        "managed_by_p2p": False,
                    },
                    "remote": remote_profile,
                }
            ),
            self.p2p_dir / "project" / "domain.yml": _yaml_dump(domain_state_payload(project_domain)),
            self.p2p_dir / "governance" / "constitution.md": "# Constitution\n\nPending.\n",
            self.p2p_dir / "governance" / "decision-rules.md": "# Decision Rules\n\nPending.\n",
            self.p2p_dir / "governance" / "relevance-criteria.md": "# Relevance Criteria\n\nPending.\n",
            self.p2p_dir / "templates" / "proposal-template.md": "# {{ proposal_id }} - {{ title }}\n",
            self.p2p_dir / "templates" / "decision-template.md": "# Decision - {{ proposal_id }}\n",
            self.p2p_dir / "templates" / "execution-plan-template.md": "# Execution Plan - {{ proposal_id }}\n",
            self.p2p_dir / "templates" / "tasks-template.yml": "tasks: []\n",
            self.p2p_dir
            / "config"
            / "readiness-profiles"
            / f"{DEFAULT_READINESS_PROFILE_ID}.yml": _yaml_dump(self.readiness_default_profile_payload()),
            self.p2p_dir / "project" / "rubrics.yml": _yaml_dump(
                rubrics_payload(project_domain, rubric_enabled=rubric_enabled)
            ),
            self.p2p_dir / "project" / "permissions.yml": _yaml_dump(
                self.permissions_default_policy_payload(
                    owner_name=owner,
                    repository_mode=repository_mode,
                )
            ),
        }
        if project_domain not in PROJECT_DOMAIN_TEMPLATES:
            files[self.p2p_dir / "project" / "next-actions.yml"] = _yaml_dump(
                domain_setup_next_actions_payload(project_domain)
            )
        return files

    def _write_missing_files(self, files: dict[Path, str]) -> list[Path]:
        created: list[Path] = []
        for path, content in files.items():
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                created.append(path.relative_to(self.root))
        return created

    def _create_missing_directories(self) -> list[Path]:
        created: list[Path] = []
        for directory in (self.p2p_dir / "proposals", self.p2p_dir / "prompts"):
            if not directory.exists():
                directory.mkdir(parents=True)
                created.append(directory.relative_to(self.root))
        return created

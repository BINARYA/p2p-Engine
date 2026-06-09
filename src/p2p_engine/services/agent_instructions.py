from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)


@dataclass(frozen=True)
class AgentInstructionsResult:
    profile: str
    created: list[Path]
    updated: list[Path]
    policy_path: Path


@dataclass(frozen=True)
class AgentIntegrationResult:
    target: str
    created: list[Path]
    updated: list[Path]
    removed: list[Path]
    skipped: list[dict[str, object]]
    registry_path: Path


class AgentInstructionService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        project_name: Callable[[], str],
        repository_mode: Callable[[str], str],
        set_repository_mode: Callable[[str], None],
        normalize_profile: Callable[[str], str],
        normalize_repository_mode: Callable[[str], str],
        expanded_profiles: Callable[[str], list[str]],
        instruction_files: Callable[[str, list[str], str, Any], dict[Path, str]],
        adapter_files: Callable[[str, str, list[str], str], list[tuple[Path, str, bool, str]]],
        adapter_capabilities: Callable[[str], dict[str, object]],
        agent_policy: Callable[[str, list[str], str, Any], dict[str, object]],
        built_in_adapters: tuple[str, ...],
        interaction_style: Callable[[], Any] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.project_name = project_name
        self.repository_mode = repository_mode
        self.set_repository_mode = set_repository_mode
        self.normalize_profile = normalize_profile
        self.normalize_repository_mode = normalize_repository_mode
        self.expanded_profiles = expanded_profiles
        self.instruction_files = instruction_files
        self.adapter_files = adapter_files
        self.adapter_capabilities = adapter_capabilities
        self.agent_policy = agent_policy
        self.built_in_adapters = built_in_adapters
        self.interaction_style = interaction_style

    def refresh_instructions(
        self,
        profile: str = "generic",
        repository_mode: str | None = None,
    ) -> AgentInstructionsResult:
        profile = self.normalize_profile(profile)
        project_name = self.project_name()
        repository_mode = self.normalize_repository_mode(repository_mode or self.repository_mode("local"))
        profiles = self.expanded_profiles(profile)
        interaction_style = self.interaction_style() if self.interaction_style is not None else None
        policy_path = self.policy_path()
        existing_policy = _read_yaml_mapping(policy_path, default={}) if policy_path.exists() else {}
        existing_profiles = existing_policy.get("agent_profiles", [])
        if not isinstance(existing_profiles, list):
            existing_profiles = []
        merged_profiles = sorted({str(item) for item in existing_profiles} | set(profiles))
        files = self.instruction_files(project_name, merged_profiles, repository_mode, interaction_style)
        created: list[Path] = []
        updated: list[Path] = []

        for relative_path, content in files.items():
            path = self.root / relative_path
            relative = path.relative_to(self.root)
            if path.exists() and path.read_text(encoding="utf-8") == content:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            path.write_text(content, encoding="utf-8")
            if existed:
                updated.append(relative)
            else:
                created.append(relative)

        policy = self.agent_policy(project_name, merged_profiles, repository_mode, interaction_style)
        policy_content = _yaml_dump(policy)
        relative_policy = policy_path.relative_to(self.root)
        if not policy_path.exists():
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(policy_content, encoding="utf-8")
            created.append(relative_policy)
        elif policy_path.read_text(encoding="utf-8") != policy_content:
            policy_path.write_text(policy_content, encoding="utf-8")
            updated.append(relative_policy)

        self.set_repository_mode(repository_mode)
        self.write_registry(self.build_registry(merged_profiles, repository_mode))
        return AgentInstructionsResult(
            profile=profile,
            created=created,
            updated=updated,
            policy_path=relative_policy,
        )

    def list_integrations(self) -> dict[str, object]:
        registry = self.registry()
        adapters = registry.get("adapters", {})
        if not isinstance(adapters, dict):
            adapters = {}
        return {
            "registry_path": str(self.path().relative_to(self.root)),
            "baseline_profile": registry.get("baseline_profile", "generic"),
            "adapters": [
                self.integration_status(adapter_id, adapters.get(adapter_id, {}))
                for adapter_id in self.built_in_adapters
            ],
        }

    def show_integration(self, adapter: str) -> dict[str, object]:
        adapter = self.normalize_profile(adapter)
        if adapter == "all":
            raise ValueError("Use a specific adapter for show.")
        registry = self.registry()
        adapters = registry.get("adapters", {})
        if not isinstance(adapters, dict):
            adapters = {}
        return self.integration_status(adapter, adapters.get(adapter, {}), include_files=True)

    def install_integrations(
        self,
        target: str = "all",
        repository_mode: str | None = None,
        *,
        force: bool = False,
    ) -> AgentIntegrationResult:
        target = self.normalize_profile(target)
        repository_mode = self.normalize_repository_mode(repository_mode or self.repository_mode("local"))
        project_name = self.project_name()
        interaction_style = self.interaction_style() if self.interaction_style is not None else None
        registry = self.registry()
        existing_adapters = registry.get("adapters", {})
        existing_profiles = (
            [str(adapter_id) for adapter_id in existing_adapters.keys()]
            if isinstance(existing_adapters, dict)
            else []
        )
        profiles = sorted(set(existing_profiles) | set(self.expanded_profiles(target)))
        files = self.instruction_files(project_name, profiles, repository_mode, interaction_style)
        current_files = self.registry_file_map(registry)
        created: list[Path] = []
        updated: list[Path] = []
        skipped: list[dict[str, object]] = []

        for relative_path, content in files.items():
            path = self.root / relative_path
            relative = path.relative_to(self.root)
            existing_record = current_files.get(str(relative_path))
            if path.exists():
                current_hash = _sha256_file(path)
                if existing_record and existing_record.get("sha256") != current_hash and not force:
                    skipped.append({"path": str(relative), "reason": "drifted"})
                    continue
                if not existing_record and path.read_text(encoding="utf-8") != content and not force:
                    skipped.append({"path": str(relative), "reason": "unmanaged_exists"})
                    continue
                if path.read_text(encoding="utf-8") == content:
                    continue
                path.write_text(content, encoding="utf-8")
                updated.append(relative)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                created.append(relative)

        policy = self.agent_policy(project_name, profiles, repository_mode, interaction_style)
        policy_path = self.policy_path()
        policy_content = _yaml_dump(policy)
        relative_policy = policy_path.relative_to(self.root)
        if not policy_path.exists():
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(policy_content, encoding="utf-8")
            created.append(relative_policy)
        elif policy_path.read_text(encoding="utf-8") != policy_content:
            policy_path.write_text(policy_content, encoding="utf-8")
            updated.append(relative_policy)

        new_registry = self.build_registry(profiles, repository_mode)
        if skipped:
            old_records = self.registry_file_map(registry)
            skipped_paths = {str(item["path"]) for item in skipped}
            for adapter_record in new_registry.get("adapters", {}).values():
                if not isinstance(adapter_record, dict):
                    continue
                file_records = adapter_record.get("files", [])
                if not isinstance(file_records, list):
                    continue
                for index, record in enumerate(file_records):
                    if not isinstance(record, dict):
                        continue
                    path_key = str(record.get("path", ""))
                    if path_key in skipped_paths and path_key in old_records:
                        preserved = {**old_records[path_key]}
                        current_path = self.root / path_key
                        preserved["drift"] = (
                            "drifted"
                            if current_path.exists() and preserved.get("sha256") != _sha256_file(current_path)
                            else "missing"
                        )
                        file_records[index] = preserved
                    elif path_key in skipped_paths:
                        current_path = self.root / path_key
                        record["managed"] = False
                        record["sha256"] = _sha256_file(current_path) if current_path.exists() else ""
                        record["drift"] = "unmanaged" if current_path.exists() else "missing"
        registry = new_registry
        self.write_registry(registry)
        self.set_repository_mode(repository_mode)
        return AgentIntegrationResult(
            target=target,
            created=created,
            updated=updated,
            removed=[],
            skipped=skipped,
            registry_path=self.path().relative_to(self.root),
        )

    def uninstall_integration(self, adapter: str) -> AgentIntegrationResult:
        adapter = self.normalize_profile(adapter)
        if adapter in {"all", "generic"}:
            raise ValueError("generic cannot be uninstalled.")
        registry = self.registry()
        adapters = registry.get("adapters", {})
        if not isinstance(adapters, dict) or adapter not in adapters:
            raise ValueError(f"Agent integration is not installed: {adapter}")
        adapter_record = adapters.get(adapter, {})
        files = adapter_record.get("files", []) if isinstance(adapter_record, dict) else []
        removed: list[Path] = []
        skipped: list[dict[str, object]] = []
        for record in files if isinstance(files, list) else []:
            if not isinstance(record, dict):
                continue
            relative = Path(str(record.get("path", "")))
            if record.get("shared") is True:
                skipped.append({"path": str(relative), "reason": "shared"})
                continue
            path = self.root / relative
            if not path.exists():
                skipped.append({"path": str(relative), "reason": "missing"})
                continue
            if record.get("sha256") != _sha256_file(path):
                skipped.append({"path": str(relative), "reason": "drifted"})
                continue
            path.unlink()
            removed.append(relative)
            _remove_empty_parents(path.parent, stop_at=self.root)

        adapters.pop(adapter, None)
        registry["adapters"] = adapters
        remaining_profiles = sorted({"generic"} | {str(item) for item in adapters.keys()})
        project_name = self.project_name()
        repository_mode = self.repository_mode("local")
        interaction_style = self.interaction_style() if self.interaction_style is not None else None
        shared_files = self.instruction_files(project_name, remaining_profiles, repository_mode, interaction_style)
        for relative_path in (Path("AGENTS.md"),):
            content = shared_files.get(relative_path)
            if content is None:
                continue
            path = self.root / relative_path
            path.write_text(content, encoding="utf-8")
        policy_path = self.policy_path()
        policy_path.write_text(
            _yaml_dump(self.agent_policy(project_name, remaining_profiles, repository_mode, interaction_style)),
            encoding="utf-8",
        )
        registry = self.build_registry(remaining_profiles, repository_mode)
        self.write_registry(registry)
        return AgentIntegrationResult(
            target=adapter,
            created=[],
            updated=[],
            removed=removed,
            skipped=skipped,
            registry_path=self.path().relative_to(self.root),
        )

    def path(self) -> Path:
        return self.p2p_dir / "agent-integrations.yml"

    def policy_path(self) -> Path:
        return self.p2p_dir / "agent-policy.yml"

    def registry(self) -> dict[str, object]:
        path = self.path()
        if not path.exists():
            return {
                "schema_version": 1,
                "baseline_profile": "generic",
                "adapters": {},
            }
        return _read_yaml_mapping(path, default={})

    def write_registry(self, registry: dict[str, object]) -> None:
        path = self.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(registry), encoding="utf-8")

    def registry_file_map(self, registry: dict[str, object]) -> dict[str, dict[str, object]]:
        adapters = registry.get("adapters", {})
        records: dict[str, dict[str, object]] = {}
        if not isinstance(adapters, dict):
            return records
        for adapter in adapters.values():
            if not isinstance(adapter, dict):
                continue
            files = adapter.get("files", [])
            if not isinstance(files, list):
                continue
            for record in files:
                if isinstance(record, dict) and "path" in record:
                    records[str(record["path"])] = record
        return records

    def build_registry(self, profiles: list[str], repository_mode: str) -> dict[str, object]:
        project_name = self.project_name()
        installed = sorted(set(self.expanded_profiles("generic")) | set(profiles))
        adapters: dict[str, object] = {}
        for adapter_id in installed:
            files = self.adapter_files(project_name, adapter_id, installed, repository_mode)
            file_records = []
            for relative_path, template_id, shared, owner in files:
                path = self.root / relative_path
                file_records.append(
                    {
                        "path": str(relative_path),
                        "shared": shared,
                        "owner": owner,
                        "managed": path.exists(),
                        "template_id": template_id,
                        "sha256": _sha256_file(path) if path.exists() else "",
                        "drift": "clean" if path.exists() else "missing",
                    }
                )
            adapters[adapter_id] = {
                "status": "installed",
                "maturity": "stable",
                "template_version": "agent-template-v1",
                "capabilities": self.adapter_capabilities(adapter_id),
                "files": file_records,
            }
        return {
            "schema_version": 1,
            "baseline_profile": "generic",
            "generated_at": date.today().isoformat(),
            "adapters": adapters,
        }

    def integration_status(
        self,
        adapter_id: str,
        record: object,
        *,
        include_files: bool = False,
    ) -> dict[str, object]:
        installed = isinstance(record, dict) and record.get("status") == "installed"
        files = record.get("files", []) if isinstance(record, dict) else []
        file_statuses: list[dict[str, object]] = []
        if isinstance(files, list):
            for file_record in files:
                if not isinstance(file_record, dict):
                    continue
                path = self.root / str(file_record.get("path", ""))
                drift = "missing"
                if path.exists():
                    drift = "clean" if file_record.get("sha256") == _sha256_file(path) else "drifted"
                file_status = {**file_record, "drift": drift}
                file_statuses.append(file_status)
        status = {
            "adapter": adapter_id,
            "supported": adapter_id in self.built_in_adapters,
            "installed": installed,
            "maturity": record.get("maturity", "stable") if isinstance(record, dict) else "stable",
            "drift": "drifted" if any(item.get("drift") == "drifted" for item in file_statuses) else "clean",
        }
        if include_files:
            status["files"] = file_statuses
            status["capabilities"] = self.adapter_capabilities(adapter_id)
        return status


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _remove_empty_parents(path: Path, *, stop_at: Path) -> None:
    path = path.resolve()
    stop_at = stop_at.resolve()
    while path != stop_at and stop_at in path.parents:
        try:
            path.rmdir()
        except OSError:
            return
        path = path.parent

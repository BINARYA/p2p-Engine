from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    write_text_atomic as _write_text_atomic,
    write_yaml_atomic as _write_yaml_atomic,
    yaml_dump as _yaml_dump,
)


@dataclass(frozen=True)
class AgentInstructionsResult:
    profile: str
    created: list[Path]
    updated: list[Path]
    policy_path: Path
    skipped: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class AgentIntegrationResult:
    target: str
    created: list[Path]
    updated: list[Path]
    removed: list[Path]
    skipped: list[dict[str, object]]
    registry_path: Path


@dataclass(frozen=True)
class AgentDoctorFinding:
    code: str
    severity: str
    adapter: str
    path: Path
    message: str
    suggested_command: str = ""


@dataclass(frozen=True)
class AgentDoctorResult:
    target: str
    health: str
    registry_path: Path
    findings: list[AgentDoctorFinding]


_ERROR_FILE_STATUSES = {"missing", "modified", "conflicted"}
_WARNING_FILE_STATUSES = {"unmanaged", "stale_template"}
_REGISTRY_FILE_STATUSES = _ERROR_FILE_STATUSES | _WARNING_FILE_STATUSES | {"clean"}
_FILE_STATUS_FINDING_CODES = {
    "missing": "P2P_AGENT_FILE_MISSING",
    "modified": "P2P_AGENT_FILE_MODIFIED",
    "unmanaged": "P2P_AGENT_FILE_UNMANAGED",
    "conflicted": "P2P_AGENT_FILE_CONFLICTED",
    "stale_template": "P2P_AGENT_TEMPLATE_STALE",
}


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
        registry = self.registry()
        files, relative_policy = self._managed_instruction_files(
            project_name,
            merged_profiles,
            repository_mode,
            interaction_style,
        )
        created, updated, skipped = self._write_generated_files_safely(
            files,
            self.registry_file_map(registry),
        )

        self.set_repository_mode(repository_mode)
        new_registry = self.build_registry(merged_profiles, repository_mode)
        self.write_registry(self._with_skipped_file_records(registry, new_registry, skipped))
        return AgentInstructionsResult(
            profile=profile,
            created=created,
            updated=updated,
            policy_path=relative_policy,
            skipped=skipped,
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

    def doctor(self, target: str | None = "all") -> AgentDoctorResult:
        target = self.normalize_profile(target or "all")
        registry = self.registry()
        registry_path = self.path().relative_to(self.root)
        findings: list[AgentDoctorFinding] = []
        adapters = registry.get("adapters", {})
        if not self.path().exists():
            findings.append(
                AgentDoctorFinding(
                    code="P2P_AGENT_REGISTRY_MISSING",
                    severity="warning",
                    adapter="all",
                    path=registry_path,
                    message="Agent integration registry is missing.",
                    suggested_command="p2p agent install all",
                )
            )
            return AgentDoctorResult(
                target=target,
                health="warning",
                registry_path=registry_path,
                findings=findings,
            )
        if registry.get("baseline_profile") != "generic":
            findings.append(
                AgentDoctorFinding(
                    code="P2P_AGENT_BASELINE_INVALID",
                    severity="error",
                    adapter="generic",
                    path=registry_path,
                    message="Agent integration registry baseline_profile must be generic.",
                    suggested_command="p2p agent install generic --force",
                )
            )
        if not isinstance(adapters, dict):
            findings.append(
                AgentDoctorFinding(
                    code="P2P_AGENT_REGISTRY_INVALID",
                    severity="error",
                    adapter="all",
                    path=registry_path,
                    message="Agent integration registry adapters must be a mapping.",
                    suggested_command="p2p agent install all --force",
                )
            )
            return AgentDoctorResult(
                target=target,
                health="error",
                registry_path=registry_path,
                findings=findings,
            )
        if "generic" not in adapters:
            findings.append(
                AgentDoctorFinding(
                    code="P2P_AGENT_GENERIC_MISSING",
                    severity="error",
                    adapter="generic",
                    path=registry_path,
                    message="Mandatory generic adapter is missing from the registry.",
                    suggested_command="p2p agent install generic --force",
                )
            )
        for adapter_id in adapters:
            if adapter_id not in self.built_in_adapters:
                findings.append(
                    AgentDoctorFinding(
                        code="P2P_AGENT_UNKNOWN_ADAPTER",
                        severity="error",
                        adapter=str(adapter_id),
                        path=registry_path,
                        message=f"Unknown agent adapter in registry: {adapter_id}.",
                        suggested_command="p2p validate",
                    )
                )

        targets = list(self.built_in_adapters) if target == "all" else [target]
        for adapter_id in targets:
            record = adapters.get(adapter_id, {})
            status = self.integration_status(adapter_id, record, include_files=True)
            if not status["installed"]:
                if target != "all":
                    findings.append(
                        AgentDoctorFinding(
                            code="P2P_AGENT_NOT_INSTALLED",
                            severity="warning",
                            adapter=adapter_id,
                            path=registry_path,
                            message=f"Agent adapter is not installed: {adapter_id}.",
                            suggested_command=f"p2p agent install {adapter_id}",
                        )
                    )
                continue
            for file_status in status.get("files", []):
                if not isinstance(file_status, dict):
                    continue
                self._append_file_doctor_finding(findings, adapter_id, file_status)
                self._append_shared_file_doctor_finding(findings, adapter_id, file_status, adapters)

        health = _findings_health(findings)
        return AgentDoctorResult(
            target=target,
            health=health,
            registry_path=registry_path,
            findings=findings,
        )

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
        old_registry = registry
        existing_adapters = registry.get("adapters", {})
        existing_profiles = (
            [str(adapter_id) for adapter_id in existing_adapters.keys()]
            if isinstance(existing_adapters, dict)
            else []
        )
        profiles = sorted(set(existing_profiles) | set(self.expanded_profiles(target)))
        current_files = self.registry_file_map(registry)
        all_files, _relative_policy = self._managed_instruction_files(
            project_name,
            profiles,
            repository_mode,
            interaction_style,
        )
        writable_paths = self._operation_file_paths(project_name, target, profiles, repository_mode)
        files = {path: content for path, content in all_files.items() if path in writable_paths}
        created, updated, skipped = self._write_generated_files_safely(
            files,
            current_files,
            force=force,
        )

        new_registry = self.build_registry(profiles, repository_mode)
        preserved_paths = {str(path) for path in all_files if path not in writable_paths}
        registry = self._with_preserved_file_records(old_registry, new_registry, preserved_paths)
        registry = self._with_skipped_file_records(old_registry, registry, skipped)
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
            relative = self._safe_relative_path(record.get("path", ""), label="Agent registry path")
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
            _write_text_atomic(path, content)
        policy_path = self.policy_path()
        _write_text_atomic(
            policy_path,
            _yaml_dump(self.agent_policy(project_name, remaining_profiles, repository_mode, interaction_style)),
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
        _write_yaml_atomic(self.path(), registry)

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
                relative_path = self._safe_relative_path(relative_path, label="Agent adapter path")
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

    def _managed_instruction_files(
        self,
        project_name: str,
        profiles: list[str],
        repository_mode: str,
        interaction_style: Any,
    ) -> tuple[dict[Path, str], Path]:
        files = dict(self.instruction_files(project_name, profiles, repository_mode, interaction_style))
        relative_policy = self.policy_path().relative_to(self.root)
        files[relative_policy] = _yaml_dump(
            self.agent_policy(project_name, profiles, repository_mode, interaction_style)
        )
        safe_files = {
            self._safe_relative_path(relative_path, label="Agent instruction path"): content
            for relative_path, content in files.items()
        }
        return safe_files, relative_policy

    def _operation_file_paths(
        self,
        project_name: str,
        target: str,
        profiles: list[str],
        repository_mode: str,
    ) -> set[Path]:
        target_profiles = self.built_in_adapters if target == "all" else tuple(self.expanded_profiles(target))
        writable: set[Path] = set()
        for adapter_id in target_profiles:
            for relative_path, _template_id, _shared, _owner in self.adapter_files(
                project_name,
                adapter_id,
                profiles,
                repository_mode,
            ):
                writable.add(self._safe_relative_path(relative_path, label="Agent adapter path"))
        return writable

    def _write_generated_files_safely(
        self,
        files: dict[Path, str],
        current_files: dict[str, dict[str, object]],
        *,
        force: bool = False,
    ) -> tuple[list[Path], list[Path], list[dict[str, object]]]:
        created: list[Path] = []
        updated: list[Path] = []
        skipped: list[dict[str, object]] = []
        for relative_path, content in files.items():
            relative_path = self._safe_relative_path(relative_path, label="Agent instruction path")
            path = self.root / relative_path
            relative = path.relative_to(self.root)
            existing_record = current_files.get(str(relative))
            if path.exists():
                existing_content = path.read_text(encoding="utf-8")
                current_hash = _sha256_file(path)
                if existing_record and existing_record.get("sha256") != current_hash and not force:
                    skipped.append({"path": str(relative), "reason": "drifted"})
                    continue
                if not existing_record and existing_content != content and not force:
                    skipped.append({"path": str(relative), "reason": "unmanaged_exists"})
                    continue
                if existing_content == content:
                    continue
                _write_text_atomic(path, content)
                updated.append(relative)
            else:
                _write_text_atomic(path, content)
                created.append(relative)
        return created, updated, skipped

    def _with_skipped_file_records(
        self,
        old_registry: dict[str, object],
        new_registry: dict[str, object],
        skipped: list[dict[str, object]],
    ) -> dict[str, object]:
        if not skipped:
            return new_registry
        return self._with_preserved_file_records(
            old_registry,
            new_registry,
            {str(item["path"]) for item in skipped},
        )

    def _with_preserved_file_records(
        self,
        old_registry: dict[str, object],
        new_registry: dict[str, object],
        preserved_paths: set[str],
    ) -> dict[str, object]:
        if not preserved_paths:
            return new_registry
        old_records = self.registry_file_map(old_registry)
        adapters = new_registry.get("adapters", {})
        if not isinstance(adapters, dict):
            return new_registry
        for adapter_record in adapters.values():
            if not isinstance(adapter_record, dict):
                continue
            file_records = adapter_record.get("files", [])
            if not isinstance(file_records, list):
                continue
            for index, record in enumerate(file_records):
                if not isinstance(record, dict):
                    continue
                path_key = str(record.get("path", ""))
                if path_key not in preserved_paths:
                    continue
                current_path = self.root / path_key
                if path_key in old_records:
                    preserved = {**old_records[path_key]}
                    if not current_path.exists():
                        preserved["drift"] = "missing"
                    elif preserved.get("sha256") != _sha256_file(current_path):
                        preserved["drift"] = "drifted"
                    else:
                        preserved["drift"] = "clean"
                    file_records[index] = preserved
                else:
                    record["managed"] = False
                    record["sha256"] = _sha256_file(current_path) if current_path.exists() else ""
                    record["drift"] = "unmanaged" if current_path.exists() else "missing"
        return new_registry

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
                status_value = self.file_status(file_record)
                file_status = {
                    **file_record,
                    "status": status_value,
                    "drift": "clean" if status_value == "clean" else "drifted",
                }
                file_statuses.append(file_status)
        health = self.adapter_health(file_statuses) if installed else "clean"
        status = {
            "adapter": adapter_id,
            "supported": adapter_id in self.built_in_adapters,
            "installed": installed,
            "maturity": record.get("maturity", "stable") if isinstance(record, dict) else "stable",
            "health": health,
            "drift": "drifted" if any(item.get("status") != "clean" for item in file_statuses) else "clean",
        }
        if include_files:
            status["files"] = file_statuses
            status["capabilities"] = self.adapter_capabilities(adapter_id)
        return status

    def file_status(self, file_record: dict[str, object]) -> str:
        path = self.root / str(file_record.get("path", ""))
        registry_status = str(file_record.get("drift") or "clean")
        if not path.exists():
            return "missing"
        if file_record.get("managed") is False:
            return "unmanaged"
        if registry_status in _REGISTRY_FILE_STATUSES and registry_status != "clean":
            return registry_status
        return "clean" if file_record.get("sha256") == _sha256_file(path) else "modified"

    def adapter_health(self, file_statuses: list[dict[str, object]]) -> str:
        statuses = {str(item.get("status") or "clean") for item in file_statuses}
        if statuses & _ERROR_FILE_STATUSES:
            return "error"
        if statuses & _WARNING_FILE_STATUSES:
            return "warning"
        return "clean"

    def _safe_relative_path(self, value: object, *, label: str) -> Path:
        raw_path = str(value or "").strip()
        if not raw_path:
            raise ValueError(f"{label} is required.")
        relative_path = Path(raw_path)
        if relative_path.is_absolute():
            raise ValueError(f"{label} must be relative: {raw_path}")
        if ".." in relative_path.parts:
            raise ValueError(f"{label} must not escape project root: {raw_path}")
        resolved_root = self.root.resolve()
        resolved_path = (resolved_root / relative_path).resolve()
        if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
            raise ValueError(f"{label} must not escape project root: {raw_path}")
        return relative_path

    def _append_file_doctor_finding(
        self,
        findings: list[AgentDoctorFinding],
        adapter_id: str,
        file_status: dict[str, object],
    ) -> None:
        status = str(file_status.get("status") or "clean")
        if status == "clean":
            return
        relative = Path(str(file_status.get("path") or ""))
        severity = "error" if status in _ERROR_FILE_STATUSES else "warning"
        code = _FILE_STATUS_FINDING_CODES.get(status, "P2P_AGENT_FILE_INVALID")
        suggested = "p2p agent update {adapter}".format(adapter=adapter_id)
        if status in {"modified", "unmanaged"}:
            suggested = f"review {relative}, then run p2p agent update {adapter_id} --force if appropriate"
        findings.append(
            AgentDoctorFinding(
                code=code,
                severity=severity,
                adapter=adapter_id,
                path=relative,
                message=f"Agent file {relative} is {status}.",
                suggested_command=suggested,
            )
        )

    def _append_shared_file_doctor_finding(
        self,
        findings: list[AgentDoctorFinding],
        adapter_id: str,
        file_status: dict[str, object],
        adapters: dict[str, object],
    ) -> None:
        if file_status.get("shared") is not True:
            return
        owner = str(file_status.get("owner") or "")
        if owner in adapters:
            return
        relative = Path(str(file_status.get("path") or ""))
        findings.append(
            AgentDoctorFinding(
                code="P2P_AGENT_SHARED_OWNER_MISSING",
                severity="error",
                adapter=adapter_id,
                path=relative,
                message=f"Shared agent file {relative} references missing owner adapter: {owner}.",
                suggested_command="p2p validate",
            )
        )


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


def _findings_health(findings: list[AgentDoctorFinding]) -> str:
    severities = {finding.severity for finding in findings}
    if "error" in severities:
        return "error"
    if "warning" in severities:
        return "warning"
    return "clean"

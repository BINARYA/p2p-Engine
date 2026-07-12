from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from p2p_engine import __version__ as P2P_ENGINE_VERSION
from p2p_engine.core.runtime_contract import (
    RUNTIME_CONTRACT_INSTALLER_FIELD,
    RUNTIME_CONTRACT_INVALID,
    RUNTIME_CONTRACT_INVALID_VERSION,
    RUNTIME_CONTRACT_LEGACY_UNDECLARED,
    RUNTIME_CONTRACT_MISSING,
    RUNTIME_CONTRACT_MISSING_FIELD,
    RUNTIME_CONTRACT_RECOMMENDED_OUT_OF_RANGE,
    RUNTIME_CONTRACT_UNSUPPORTED,
    RUNTIME_SETUP_GUIDE_DRIFT,
    RUNTIME_SETUP_GUIDE_MARKER,
    RUNTIME_SETUP_GUIDE_UNMANAGED,
    RUNTIME_STATUS_COMPATIBLE,
    RUNTIME_STATUS_INCOMPATIBLE,
    RUNTIME_STATUS_INVALID_CONTRACT,
    RUNTIME_STATUS_LEGACY_UNDECLARED,
    RUNTIME_STATUS_MISSING_CONTRACT,
    RUNTIME_STATUS_UNSUPPORTED_CONTRACT,
    P2PRuntimeRequirement,
    RuntimeContract,
    RuntimeFinding,
    RuntimeStatus,
    RuntimeWritePreflight,
)
from p2p_engine.foundation.files import read_yaml_mapping, relative_to_root, write_text_atomic, write_yaml_atomic

RUNTIME_CONTRACT_SCHEMA_VERSION = 1
RUNTIME_CONTRACT_REQUIRED_MARKER = {"runtime_contract": {"required": True}}

FORBIDDEN_CONTRACT_FIELDS = {
    "command",
    "commands",
    "digest",
    "digests",
    "download",
    "downloads",
    "installer",
    "install",
    "repository",
    "repositories",
    "release",
    "releases",
    "sha256",
    "source",
    "sources",
    "tag",
    "tags",
    "url",
    "urls",
    "wheel",
    "wheels",
}


class RuntimeContractService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        current_version: str = P2P_ENGINE_VERSION,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.current_version = current_version

    @property
    def project_manifest_path(self) -> Path:
        return self.p2p_dir / "project.yml"

    @property
    def contract_path(self) -> Path:
        return self.p2p_dir / "project" / "runtime.yml"

    @property
    def setup_guide_path(self) -> Path:
        return self.root / "P2P-SETUP.md"

    def default_contract_payload(self) -> dict[str, object]:
        return {
            "runtime_contract": {"schema_version": RUNTIME_CONTRACT_SCHEMA_VERSION},
            "runtime": {
                "p2p": {
                    "requires": f"=={self.current_version}",
                    "recommended": self.current_version,
                }
            },
        }

    def write_default_contract(self) -> Path:
        write_yaml_atomic(self.contract_path, self.default_contract_payload())
        return relative_to_root(self.contract_path, self.root)

    def render_setup_guide(self, contract: RuntimeContract | None = None) -> str:
        contract = contract or self._contract_from_payload(self.default_contract_payload())
        return "\n".join(
            [
                RUNTIME_SETUP_GUIDE_MARKER,
                "",
                "# P2P Setup",
                "",
                "This project declares its required P2P Engine runtime in `.p2p/project/runtime.yml`.",
                "",
                f"- Compatible runtime range: `{contract.p2p.requires}`",
                f"- Recommended runtime version: `{contract.p2p.recommended}`",
                "- Source of truth: `.p2p/project/runtime.yml`",
                "",
                "Install the recommended P2P Engine version using the official installation guidance.",
                "After installation, run `p2p runtime status` from the project root.",
                "",
            ]
        )

    def write_default_setup_guide(self) -> Path:
        write_text_atomic(self.setup_guide_path, self.render_setup_guide())
        return relative_to_root(self.setup_guide_path, self.root)

    def setup_guide_is_managed(self) -> bool:
        if not self.setup_guide_path.exists():
            return False
        return RUNTIME_SETUP_GUIDE_MARKER in self.setup_guide_path.read_text(encoding="utf-8")

    def project_requires_contract(self) -> bool:
        data = read_yaml_mapping(self.project_manifest_path, default={})
        marker = data.get("runtime_contract", {})
        return isinstance(marker, dict) and marker.get("required") is True

    def status(self) -> RuntimeStatus:
        if not self.contract_path.exists():
            return self._missing_status()

        try:
            data = yaml.safe_load(self.contract_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            return self._invalid_status(RUNTIME_CONTRACT_INVALID, f"Invalid runtime contract YAML: {exc}")

        if data is None or not isinstance(data, dict):
            return self._invalid_status(RUNTIME_CONTRACT_INVALID, "Runtime contract must be a YAML mapping.")

        forbidden = sorted(_forbidden_keys(data))
        if forbidden:
            return self._invalid_status(
                RUNTIME_CONTRACT_INSTALLER_FIELD,
                "Runtime contract must not declare installer/source fields: " + ", ".join(forbidden),
            )

        try:
            contract = self._contract_from_payload(data)
        except _UnsupportedContract as exc:
            return self._unsupported_status(str(exc))
        except _InvalidContract as exc:
            return self._invalid_status(exc.code, str(exc))

        try:
            specifier = SpecifierSet(contract.p2p.requires)
        except InvalidSpecifier as exc:
            return self._invalid_status(
                RUNTIME_CONTRACT_INVALID_VERSION,
                f"Invalid runtime compatibility range: {exc}",
                requires=contract.p2p.requires,
                recommended=contract.p2p.recommended,
            )
        try:
            recommended = Version(contract.p2p.recommended)
        except InvalidVersion as exc:
            return self._invalid_status(
                RUNTIME_CONTRACT_INVALID_VERSION,
                f"Invalid recommended runtime version: {exc}",
                requires=contract.p2p.requires,
                recommended=contract.p2p.recommended,
            )
        if recommended not in specifier:
            return self._invalid_status(
                RUNTIME_CONTRACT_RECOMMENDED_OUT_OF_RANGE,
                "Recommended runtime version does not satisfy the compatible runtime range.",
                requires=contract.p2p.requires,
                recommended=contract.p2p.recommended,
            )

        try:
            current = Version(self.current_version)
        except InvalidVersion as exc:
            return self._invalid_status(
                RUNTIME_CONTRACT_INVALID_VERSION,
                f"Invalid current runtime version: {exc}",
                requires=contract.p2p.requires,
                recommended=contract.p2p.recommended,
            )

        compatible = current in specifier
        if compatible:
            return RuntimeStatus(
                contract_path=relative_to_root(self.contract_path, self.root),
                state=RUNTIME_STATUS_COMPATIBLE,
                compatible=True,
                requires=contract.p2p.requires,
                recommended=contract.p2p.recommended,
                current_version=self.current_version,
                findings=[],
                suggested_command="p2p runtime status",
            )
        finding = RuntimeFinding(
            code=RUNTIME_STATUS_INCOMPATIBLE,
            severity="error",
            path=relative_to_root(self.contract_path, self.root),
            message=(
                f"Current P2P Engine runtime {self.current_version} does not satisfy "
                f"project requirement {contract.p2p.requires}."
            ),
            suggested_command="install the recommended P2P Engine version, then run p2p runtime status",
        )
        return RuntimeStatus(
            contract_path=relative_to_root(self.contract_path, self.root),
            state=RUNTIME_STATUS_INCOMPATIBLE,
            compatible=False,
            requires=contract.p2p.requires,
            recommended=contract.p2p.recommended,
            current_version=self.current_version,
            findings=[finding],
            suggested_command="install the recommended P2P Engine version, then run p2p runtime status",
        )

    def validation_findings(self) -> list[RuntimeFinding]:
        status = self.status()
        findings = list(status.findings)
        findings.extend(self._setup_guide_findings(status))
        return findings

    def write_preflight(self, operation: str) -> RuntimeWritePreflight:
        status = self.status()
        allowed = status.state in {RUNTIME_STATUS_COMPATIBLE, RUNTIME_STATUS_LEGACY_UNDECLARED}
        if allowed:
            message = "Runtime contract preflight passed."
        else:
            message = (
                f"Runtime contract preflight blocked {operation}: {status.state}. "
                f"Run `p2p runtime status` before mutating P2P-managed state."
            )
        return RuntimeWritePreflight(operation=operation, allowed=allowed, status=status, message=message)

    def _missing_status(self) -> RuntimeStatus:
        path = relative_to_root(self.contract_path, self.root)
        if self.project_requires_contract():
            finding = RuntimeFinding(
                code=RUNTIME_CONTRACT_MISSING,
                severity="error",
                path=path,
                message=(
                    "Runtime contract is required by .p2p/project.yml but "
                    ".p2p/project/runtime.yml is missing."
                ),
                suggested_command="restore .p2p/project/runtime.yml from project history",
            )
            return RuntimeStatus(
                contract_path=path,
                state=RUNTIME_STATUS_MISSING_CONTRACT,
                compatible=False,
                current_version=self.current_version,
                findings=[finding],
                suggested_command="restore .p2p/project/runtime.yml from project history",
            )
        finding = RuntimeFinding(
            code=RUNTIME_CONTRACT_LEGACY_UNDECLARED,
            severity="warning",
            path=path,
            message="Project has no runtime contract; compatibility cannot be inferred.",
            suggested_command="p2p runtime status",
        )
        return RuntimeStatus(
            contract_path=path,
            state=RUNTIME_STATUS_LEGACY_UNDECLARED,
            compatible=True,
            current_version=self.current_version,
            findings=[finding],
            suggested_command="p2p runtime status",
        )

    def _invalid_status(
        self,
        code: str,
        message: str,
        *,
        requires: str | None = None,
        recommended: str | None = None,
    ) -> RuntimeStatus:
        finding = RuntimeFinding(
            code=code,
            severity="error",
            path=relative_to_root(self.contract_path, self.root),
            message=message,
            suggested_command="fix .p2p/project/runtime.yml, then run p2p validate",
        )
        return RuntimeStatus(
            contract_path=relative_to_root(self.contract_path, self.root),
            state=RUNTIME_STATUS_INVALID_CONTRACT,
            compatible=False,
            requires=requires,
            recommended=recommended,
            current_version=self.current_version,
            findings=[finding],
            suggested_command="fix .p2p/project/runtime.yml, then run p2p validate",
        )

    def _unsupported_status(self, message: str) -> RuntimeStatus:
        finding = RuntimeFinding(
            code=RUNTIME_CONTRACT_UNSUPPORTED,
            severity="error",
            path=relative_to_root(self.contract_path, self.root),
            message=message,
            suggested_command="use a P2P Engine runtime that supports this contract schema",
        )
        return RuntimeStatus(
            contract_path=relative_to_root(self.contract_path, self.root),
            state=RUNTIME_STATUS_UNSUPPORTED_CONTRACT,
            compatible=False,
            current_version=self.current_version,
            findings=[finding],
            suggested_command="use a P2P Engine runtime that supports this contract schema",
        )

    def _setup_guide_findings(self, status: RuntimeStatus) -> list[RuntimeFinding]:
        if not self.setup_guide_path.exists():
            return []
        relative_path = relative_to_root(self.setup_guide_path, self.root)
        content = self.setup_guide_path.read_text(encoding="utf-8")
        if RUNTIME_SETUP_GUIDE_MARKER not in content:
            return [
                RuntimeFinding(
                    code=RUNTIME_SETUP_GUIDE_UNMANAGED,
                    severity="warning",
                    path=relative_path,
                    message="P2P-SETUP.md exists but is not marked as P2P-managed; it will not be overwritten.",
                    suggested_command="review P2P-SETUP.md and .p2p/project/runtime.yml",
                )
            ]
        if not status.requires or not status.recommended:
            return []
        expected = self.render_setup_guide(
            RuntimeContract(
                schema_version=RUNTIME_CONTRACT_SCHEMA_VERSION,
                p2p=P2PRuntimeRequirement(requires=status.requires, recommended=status.recommended),
            )
        )
        if _normalize_newlines(content) == _normalize_newlines(expected):
            return []
        return [
            RuntimeFinding(
                code=RUNTIME_SETUP_GUIDE_DRIFT,
                severity="warning",
                path=relative_path,
                message="Managed P2P-SETUP.md no longer matches the deterministic runtime setup guide.",
                suggested_command="refresh P2P-SETUP.md from .p2p/project/runtime.yml",
            )
        ]

    def _contract_from_payload(self, data: dict[str, Any]) -> RuntimeContract:
        contract_data = _mapping(data.get("runtime_contract"))
        if "schema_version" not in contract_data:
            raise _InvalidContract(RUNTIME_CONTRACT_MISSING_FIELD, "Runtime contract missing runtime_contract.schema_version.")
        schema_version = contract_data.get("schema_version")
        if schema_version != RUNTIME_CONTRACT_SCHEMA_VERSION:
            raise _UnsupportedContract(f"Unsupported runtime contract schema version: {schema_version}")
        runtime = _mapping(data.get("runtime"))
        p2p = _mapping(runtime.get("p2p"))
        requires = _required_string(p2p, "requires", "runtime.p2p.requires")
        recommended = _required_string(p2p, "recommended", "runtime.p2p.recommended")
        return RuntimeContract(
            schema_version=RUNTIME_CONTRACT_SCHEMA_VERSION,
            p2p=P2PRuntimeRequirement(requires=requires, recommended=recommended),
        )


class _InvalidContract(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _UnsupportedContract(ValueError):
    pass


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _InvalidContract(RUNTIME_CONTRACT_MISSING_FIELD, "Runtime contract missing required mapping.")
    return value


def _required_string(data: dict[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _InvalidContract(RUNTIME_CONTRACT_MISSING_FIELD, f"Runtime contract missing {label}.")
    return value.strip()


def _forbidden_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in FORBIDDEN_CONTRACT_FIELDS:
                found.add(str(key))
            found.update(_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_forbidden_keys(child))
    return found


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")

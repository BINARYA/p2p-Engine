from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from p2p_engine import __version__ as P2P_ENGINE_VERSION
from p2p_engine.core.runtime_contract import (
    RUNTIME_CONTRACT_BLOCKER_CONFIRMATION_REQUIRED,
    RUNTIME_CONTRACT_BLOCKER_INVALID_PROPOSED_CONTRACT,
    RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
    RUNTIME_CONTRACT_BLOCKER_REASON_REQUIRED,
    RUNTIME_CONTRACT_BLOCKER_STALE_PREVIEW,
    RUNTIME_CONTRACT_BLOCKER_UNMANAGED_SETUP_GUIDE,
    RUNTIME_CONTRACT_BLOCKER_UNSUPPORTED_CURRENT_STATE,
    RUNTIME_CONTRACT_BLOCKER_UNTRUSTED_CURRENT_CONTRACT,
    RUNTIME_CONTRACT_ADOPTION_STATUS_ADOPTED,
    RUNTIME_CONTRACT_ADOPTION_STATUS_BLOCKED,
    RUNTIME_CONTRACT_ADOPTION_STATUS_PARTIAL_FAILURE,
    RUNTIME_CONTRACT_UPDATE_STATUS_APPLICABLE,
    RUNTIME_CONTRACT_UPDATE_STATUS_BLOCKED,
    RUNTIME_CONTRACT_UPDATE_STATUS_NO_CHANGE,
    RUNTIME_CONTRACT_UPDATE_STATUS_PARTIAL_FAILURE,
    RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED,
    RUNTIME_CONTRACT_UPDATE_STATUS_UPDATED,
    RUNTIME_CONTRACT_IMPACT_CURRENT_RUNTIME_EXCLUDED,
    RUNTIME_CONTRACT_IMPACT_RANGE_TIGHTENING,
    RUNTIME_CONTRACT_IMPACT_RANGE_WIDENING,
    RUNTIME_CONTRACT_IMPACT_RECOMMENDED_ONLY,
    RUNTIME_CONTRACT_IMPACT_RUNTIME_LINE_CHANGE,
    RUNTIME_CONTRACT_INSTALLER_FIELD,
    RUNTIME_CONTRACT_INVALID,
    RUNTIME_CONTRACT_INVALID_VERSION,
    RUNTIME_CONTRACT_LEGACY_UNDECLARED,
    RUNTIME_CONTRACT_MISSING,
    RUNTIME_CONTRACT_MISSING_FIELD,
    RUNTIME_CONTRACT_RECOMMENDED_OUT_OF_RANGE,
    RUNTIME_CONTRACT_UNSUPPORTED,
    RUNTIME_SETUP_GUIDE_DRIFT,
    RUNTIME_SETUP_GUIDE_ACTION_BLOCKED,
    RUNTIME_SETUP_GUIDE_ACTION_GENERATE,
    RUNTIME_SETUP_GUIDE_ACTION_NONE,
    RUNTIME_SETUP_GUIDE_ACTION_REGENERATE,
    RUNTIME_SETUP_GUIDE_MARKER,
    RUNTIME_SETUP_GUIDE_STATE_MANAGED_ALIGNED,
    RUNTIME_SETUP_GUIDE_STATE_MANAGED_DRIFTED,
    RUNTIME_SETUP_GUIDE_STATE_MISSING,
    RUNTIME_SETUP_GUIDE_STATE_UNMANAGED,
    RUNTIME_SETUP_GUIDE_UNMANAGED,
    RUNTIME_STATUS_COMPATIBLE,
    RUNTIME_STATUS_INCOMPATIBLE,
    RUNTIME_STATUS_INVALID_CONTRACT,
    RUNTIME_STATUS_LEGACY_UNDECLARED,
    RUNTIME_STATUS_MISSING_CONTRACT,
    RUNTIME_STATUS_UNSUPPORTED_CONTRACT,
    P2PRuntimeRequirement,
    RuntimeContract,
    RuntimeContractAdoptionResult,
    RuntimeContractUpdateAuthority,
    RuntimeContractUpdatePreview,
    RuntimeContractUpdateResult,
    RuntimeFinding,
    RuntimeStatus,
    RuntimeWritePreflight,
)
from p2p_engine.foundation.files import (
    identity_slug,
    read_yaml_mapping,
    relative_to_root,
    write_text_atomic,
    write_yaml_atomic,
)

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

    def preview_update(
        self,
        *,
        requires: str,
        recommended: str,
        reason: str = "",
        decision: str = "",
        actor: str = "owner",
    ) -> RuntimeContractUpdatePreview:
        requires = str(requires or "").strip()
        recommended = str(recommended or "").strip()
        reason = str(reason or "").strip()
        decision = str(decision or "").strip()
        status = self.status()
        authority = self._authority_for(actor)
        proposal = self._validate_update_proposal(requires, recommended)
        proposed_range = proposal.range
        active_satisfies = self._active_satisfies(proposed_range) if proposed_range else None
        setup_guide = self._setup_guide_state(status)
        audit = {
            "audit_mode": "external",
            "reason_persisted": False,
            "decision": decision,
        }

        if not proposal.valid:
            return RuntimeContractUpdatePreview(
                status=RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED,
                current_state=status.state,
                proposed_requires=requires or None,
                proposed_recommended=recommended or None,
                proposed_valid=False,
                validation_errors=proposal.errors,
                release_availability="unverified",
                active_runtime_satisfies_proposed_range=active_satisfies,
                setup_guide=setup_guide,
                authority=authority,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_INVALID_PROPOSED_CONTRACT,
                audit=audit,
            )

        trusted_states = {RUNTIME_STATUS_COMPATIBLE, RUNTIME_STATUS_INCOMPATIBLE}
        if status.state not in trusted_states:
            return RuntimeContractUpdatePreview(
                status=RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED,
                current_state=status.state,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                proposed_valid=True,
                comparison_available=False,
                release_availability="unverified",
                active_runtime_satisfies_proposed_range=active_satisfies,
                setup_guide=setup_guide,
                authority=authority,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_UNTRUSTED_CURRENT_CONTRACT,
                required_workflow=_required_workflow_for_state(status.state),
                audit=audit,
            )

        current_contract = self._contract_from_current_status(status)
        current_range = self._supported_range(current_contract.p2p.requires)
        if current_range is None:
            return RuntimeContractUpdatePreview(
                status=RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED,
                current_state=status.state,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                proposed_valid=True,
                validation_errors=["Current runtime range is outside the supported update grammar."],
                comparison_available=False,
                release_availability="unverified",
                active_runtime_satisfies_proposed_range=active_satisfies,
                setup_guide=setup_guide,
                authority=authority,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_UNTRUSTED_CURRENT_CONTRACT,
                audit=audit,
            )

        impact = self._classify_update(
            current_contract=current_contract,
            current_range=current_range,
            proposed_requires=proposal.requires,
            proposed_recommended=proposal.recommended,
            proposed_range=proposal.range,
        )
        reason_required = any(
            label
            in {
                RUNTIME_CONTRACT_IMPACT_RANGE_TIGHTENING,
                RUNTIME_CONTRACT_IMPACT_RUNTIME_LINE_CHANGE,
                RUNTIME_CONTRACT_IMPACT_CURRENT_RUNTIME_EXCLUDED,
            }
            for label in impact.labels
        )
        if not impact.labels and setup_guide["state"] != RUNTIME_SETUP_GUIDE_STATE_MANAGED_DRIFTED:
            return RuntimeContractUpdatePreview(
                status=RUNTIME_CONTRACT_UPDATE_STATUS_NO_CHANGE,
                current_state=status.state,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                proposed_valid=True,
                comparison_available=True,
                impact_labels=[],
                reason_required=False,
                confirmation_required=False,
                release_availability="unverified",
                active_runtime_satisfies_proposed_range=active_satisfies,
                range_comparison=impact.range_comparison,
                setup_guide={**setup_guide, "planned_action": RUNTIME_SETUP_GUIDE_ACTION_NONE},
                authority=authority,
                apply_allowed=False,
                apply_would_be_blocked=False,
                expected_state_token=None,
                files_changed=[],
                audit=audit,
            )
        if not impact.labels and setup_guide["state"] == RUNTIME_SETUP_GUIDE_STATE_MANAGED_DRIFTED:
            return RuntimeContractUpdatePreview(
                status=RUNTIME_CONTRACT_UPDATE_STATUS_NO_CHANGE,
                current_state=status.state,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                proposed_valid=True,
                comparison_available=True,
                impact_labels=[],
                reason_required=False,
                confirmation_required=False,
                release_availability="unverified",
                active_runtime_satisfies_proposed_range=active_satisfies,
                range_comparison=impact.range_comparison,
                setup_guide={**setup_guide, "planned_action": RUNTIME_SETUP_GUIDE_ACTION_NONE},
                authority=authority,
                apply_allowed=False,
                apply_would_be_blocked=False,
                expected_state_token=None,
                files_changed=[],
                audit=audit,
            )

        if setup_guide["state"] == RUNTIME_SETUP_GUIDE_STATE_UNMANAGED:
            return RuntimeContractUpdatePreview(
                status=RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED,
                current_state=status.state,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                proposed_valid=True,
                comparison_available=True,
                impact_labels=impact.labels,
                reason_required=reason_required,
                confirmation_required=True,
                release_availability="unverified",
                active_runtime_satisfies_proposed_range=active_satisfies,
                range_comparison=impact.range_comparison,
                setup_guide=setup_guide,
                authority=authority,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_UNMANAGED_SETUP_GUIDE,
                audit=audit,
            )

        planned_setup_guide = self._planned_setup_guide(setup_guide)
        files_changed = [str(relative_to_root(self.contract_path, self.root))]
        if planned_setup_guide["planned_action"] != RUNTIME_SETUP_GUIDE_ACTION_NONE:
            files_changed.insert(0, str(relative_to_root(self.setup_guide_path, self.root)))
        token = self._expected_state_token(
            status=status,
            proposed_requires=proposal.requires,
            proposed_recommended=proposal.recommended,
            reason=reason,
            decision=decision,
            impact_labels=impact.labels,
            setup_guide=setup_guide,
        )
        apply_allowed = authority.apply_authorized and (not reason_required or bool(reason))
        blocked_reason = ""
        if not authority.apply_authorized:
            blocked_reason = RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED
        elif reason_required and not reason:
            blocked_reason = RUNTIME_CONTRACT_BLOCKER_REASON_REQUIRED
        return RuntimeContractUpdatePreview(
            status=RUNTIME_CONTRACT_UPDATE_STATUS_APPLICABLE,
            current_state=status.state,
            proposed_requires=proposal.requires,
            proposed_recommended=proposal.recommended,
            proposed_valid=True,
            comparison_available=True,
            impact_labels=impact.labels,
            reason_required=reason_required,
            confirmation_required=True,
            release_availability="unverified",
            active_runtime_satisfies_proposed_range=active_satisfies,
            range_comparison=impact.range_comparison,
            setup_guide=planned_setup_guide,
            authority=authority,
            apply_allowed=apply_allowed,
            apply_would_be_blocked=not apply_allowed,
            blocked_reason=blocked_reason,
            expected_state_token=token,
            files_changed=files_changed,
            audit=audit,
        )

    def apply_update(
        self,
        *,
        requires: str,
        recommended: str,
        expected_state_token: str = "",
        confirm: bool = False,
        reason: str = "",
        decision: str = "",
        actor: str = "owner",
    ) -> RuntimeContractUpdateResult:
        preview = self.preview_update(
            requires=requires,
            recommended=recommended,
            reason=reason,
            decision=decision,
            actor=actor,
        )
        if preview.status == RUNTIME_CONTRACT_UPDATE_STATUS_NO_CHANGE:
            return RuntimeContractUpdateResult(
                status=RUNTIME_CONTRACT_UPDATE_STATUS_NO_CHANGE,
                current_state=preview.current_state,
                proposed_requires=preview.proposed_requires,
                proposed_recommended=preview.proposed_recommended,
                files_changed=[],
                message="Runtime contract already matches the proposed values.",
                impact_labels=preview.impact_labels,
                setup_guide=preview.setup_guide,
                authority=preview.authority,
                active_runtime_compatible_after_update=preview.active_runtime_satisfies_proposed_range,
                audit=preview.audit,
            )
        if preview.status != RUNTIME_CONTRACT_UPDATE_STATUS_APPLICABLE:
            return self._blocked_result(preview, preview.blocked_reason or RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED)
        if not preview.authority or not preview.authority.apply_authorized:
            return self._blocked_result(preview, RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED)
        if not confirm:
            return self._blocked_result(preview, RUNTIME_CONTRACT_BLOCKER_CONFIRMATION_REQUIRED)
        if preview.reason_required and not str(reason or "").strip():
            return self._blocked_result(preview, RUNTIME_CONTRACT_BLOCKER_REASON_REQUIRED)
        if not expected_state_token or expected_state_token != preview.expected_state_token:
            return self._blocked_result(preview, RUNTIME_CONTRACT_BLOCKER_STALE_PREVIEW)

        proposed_contract = RuntimeContract(
            schema_version=RUNTIME_CONTRACT_SCHEMA_VERSION,
            p2p=P2PRuntimeRequirement(
                requires=preview.proposed_requires or "",
                recommended=preview.proposed_recommended or "",
            ),
        )
        files_changed: list[str] = []
        setup_action = str(preview.setup_guide.get("planned_action") or RUNTIME_SETUP_GUIDE_ACTION_NONE)
        try:
            if setup_action in {RUNTIME_SETUP_GUIDE_ACTION_GENERATE, RUNTIME_SETUP_GUIDE_ACTION_REGENERATE}:
                write_text_atomic(self.setup_guide_path, self.render_setup_guide(proposed_contract))
                files_changed.append(str(relative_to_root(self.setup_guide_path, self.root)))
            write_yaml_atomic(
                self.contract_path,
                self._contract_payload(preview.proposed_requires or "", preview.proposed_recommended or ""),
            )
            files_changed.append(str(relative_to_root(self.contract_path, self.root)))
        except OSError as exc:
            return RuntimeContractUpdateResult(
                status=RUNTIME_CONTRACT_UPDATE_STATUS_PARTIAL_FAILURE,
                current_state=preview.current_state,
                proposed_requires=preview.proposed_requires,
                proposed_recommended=preview.proposed_recommended,
                files_changed=files_changed,
                blocked_reason=RUNTIME_CONTRACT_UPDATE_STATUS_PARTIAL_FAILURE,
                message=f"Runtime contract update write failed: {exc}",
                impact_labels=preview.impact_labels,
                setup_guide=preview.setup_guide,
                authority=preview.authority,
                active_runtime_compatible_after_update=preview.active_runtime_satisfies_proposed_range,
                audit=preview.audit,
            )

        active_compatible = preview.active_runtime_satisfies_proposed_range
        return RuntimeContractUpdateResult(
            status=RUNTIME_CONTRACT_UPDATE_STATUS_UPDATED,
            current_state=preview.current_state,
            proposed_requires=preview.proposed_requires,
            proposed_recommended=preview.proposed_recommended,
            files_changed=files_changed,
            message="Runtime contract updated.",
            impact_labels=preview.impact_labels,
            setup_guide=preview.setup_guide,
            authority=preview.authority,
            active_runtime_compatible_after_update=active_compatible,
            subsequent_governed_writes_blocked=active_compatible is False,
            post_update_mutations_performed=False,
            full_validation_deferred=active_compatible is False,
            audit=preview.audit,
        )

    def adopt_contract(
        self,
        *,
        requires: str,
        recommended: str,
        confirm: bool = False,
        actor: str = "owner",
    ) -> RuntimeContractAdoptionResult:
        requires = str(requires or "").strip()
        recommended = str(recommended or "").strip()
        status = self.status()
        authority = self._authority_for(actor)
        proposal = self._validate_update_proposal(requires, recommended)
        setup_guide = self._planned_setup_guide(self._setup_guide_state(status))
        active_satisfies = self._active_satisfies(proposal.range) if proposal.range else None

        if not proposal.valid:
            return self._adoption_blocked_result(
                status=status,
                proposed_requires=requires or None,
                proposed_recommended=recommended or None,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_INVALID_PROPOSED_CONTRACT,
                setup_guide=setup_guide,
                authority=authority,
                validation_errors=proposal.errors,
                active_runtime_compatible_after_adoption=active_satisfies,
            )
        if status.state != RUNTIME_STATUS_LEGACY_UNDECLARED:
            return self._adoption_blocked_result(
                status=status,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_UNSUPPORTED_CURRENT_STATE,
                setup_guide=setup_guide,
                authority=authority,
                active_runtime_compatible_after_adoption=active_satisfies,
            )
        if setup_guide["state"] == RUNTIME_SETUP_GUIDE_STATE_UNMANAGED:
            return self._adoption_blocked_result(
                status=status,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_UNMANAGED_SETUP_GUIDE,
                setup_guide=setup_guide,
                authority=authority,
                active_runtime_compatible_after_adoption=active_satisfies,
            )
        if not authority.apply_authorized:
            return self._adoption_blocked_result(
                status=status,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
                setup_guide=setup_guide,
                authority=authority,
                active_runtime_compatible_after_adoption=active_satisfies,
            )
        if not confirm:
            return self._adoption_blocked_result(
                status=status,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                blocked_reason=RUNTIME_CONTRACT_BLOCKER_CONFIRMATION_REQUIRED,
                setup_guide=setup_guide,
                authority=authority,
                active_runtime_compatible_after_adoption=active_satisfies,
            )

        files_changed: list[str] = []
        proposed_contract = RuntimeContract(
            schema_version=RUNTIME_CONTRACT_SCHEMA_VERSION,
            p2p=P2PRuntimeRequirement(requires=proposal.requires, recommended=proposal.recommended),
        )
        try:
            write_yaml_atomic(self.contract_path, self._contract_payload(proposal.requires, proposal.recommended))
            files_changed.append(str(relative_to_root(self.contract_path, self.root)))
            if setup_guide["planned_action"] in {RUNTIME_SETUP_GUIDE_ACTION_GENERATE, RUNTIME_SETUP_GUIDE_ACTION_REGENERATE}:
                write_text_atomic(self.setup_guide_path, self.render_setup_guide(proposed_contract))
                files_changed.append(str(relative_to_root(self.setup_guide_path, self.root)))
            self._write_required_contract_marker()
            files_changed.append(str(relative_to_root(self.project_manifest_path, self.root)))
        except OSError as exc:
            return RuntimeContractAdoptionResult(
                status=RUNTIME_CONTRACT_ADOPTION_STATUS_PARTIAL_FAILURE,
                current_state=status.state,
                proposed_requires=proposal.requires,
                proposed_recommended=proposal.recommended,
                files_changed=files_changed,
                blocked_reason=RUNTIME_CONTRACT_ADOPTION_STATUS_PARTIAL_FAILURE,
                message=f"Runtime contract adoption write failed: {exc}",
                setup_guide=setup_guide,
                authority=authority,
                active_runtime_compatible_after_adoption=active_satisfies,
            )

        return RuntimeContractAdoptionResult(
            status=RUNTIME_CONTRACT_ADOPTION_STATUS_ADOPTED,
            current_state=status.state,
            proposed_requires=proposal.requires,
            proposed_recommended=proposal.recommended,
            files_changed=files_changed,
            message="Runtime contract adopted.",
            setup_guide=setup_guide,
            authority=authority,
            active_runtime_compatible_after_adoption=active_satisfies,
        )

    def _blocked_result(self, preview: RuntimeContractUpdatePreview, blocked_reason: str) -> RuntimeContractUpdateResult:
        return RuntimeContractUpdateResult(
            status=RUNTIME_CONTRACT_UPDATE_STATUS_BLOCKED,
            current_state=preview.current_state,
            proposed_requires=preview.proposed_requires,
            proposed_recommended=preview.proposed_recommended,
            files_changed=[],
            blocked_reason=blocked_reason,
            message=f"Runtime contract update blocked: {blocked_reason}.",
            impact_labels=preview.impact_labels,
            setup_guide=preview.setup_guide,
            authority=preview.authority,
            active_runtime_compatible_after_update=preview.active_runtime_satisfies_proposed_range,
            audit=preview.audit,
        )

    def _adoption_blocked_result(
        self,
        *,
        status: RuntimeStatus,
        proposed_requires: str | None,
        proposed_recommended: str | None,
        blocked_reason: str,
        setup_guide: dict[str, Any],
        authority: RuntimeContractUpdateAuthority,
        validation_errors: list[str] | None = None,
        active_runtime_compatible_after_adoption: bool | None = None,
    ) -> RuntimeContractAdoptionResult:
        return RuntimeContractAdoptionResult(
            status=RUNTIME_CONTRACT_ADOPTION_STATUS_BLOCKED,
            current_state=status.state,
            proposed_requires=proposed_requires,
            proposed_recommended=proposed_recommended,
            files_changed=[],
            blocked_reason=blocked_reason,
            message=f"Runtime contract adoption blocked: {blocked_reason}.",
            setup_guide=setup_guide,
            authority=authority,
            validation_errors=validation_errors or [],
            active_runtime_compatible_after_adoption=active_runtime_compatible_after_adoption,
        )

    def _validate_update_proposal(self, requires: str, recommended: str) -> "_ProposedRuntimeContract":
        errors: list[str] = []
        if not requires:
            errors.append("runtime.p2p.requires is required.")
        if not recommended:
            errors.append("runtime.p2p.recommended is required.")
        runtime_range = self._supported_range(requires) if requires else None
        if requires and runtime_range is None:
            errors.append("runtime.p2p.requires must be ==VERSION or >=LOWER,<UPPER.")
        try:
            recommended_version = Version(recommended) if recommended else None
        except InvalidVersion as exc:
            recommended_version = None
            errors.append(f"Invalid recommended runtime version: {exc}")
        if runtime_range and recommended_version and not runtime_range.contains(recommended_version):
            errors.append("runtime.p2p.recommended must satisfy runtime.p2p.requires.")
        return _ProposedRuntimeContract(
            requires=requires,
            recommended=recommended,
            range=runtime_range,
            valid=not errors,
            errors=errors,
        )

    def _contract_from_current_status(self, status: RuntimeStatus) -> RuntimeContract:
        return RuntimeContract(
            schema_version=RUNTIME_CONTRACT_SCHEMA_VERSION,
            p2p=P2PRuntimeRequirement(
                requires=status.requires or "",
                recommended=status.recommended or "",
            ),
        )

    def _contract_payload(self, requires: str, recommended: str) -> dict[str, object]:
        return {
            "runtime_contract": {"schema_version": RUNTIME_CONTRACT_SCHEMA_VERSION},
            "runtime": {
                "p2p": {
                    "requires": requires,
                    "recommended": recommended,
                }
            },
        }

    def _active_satisfies(self, runtime_range: "_SupportedRuntimeRange | None") -> bool | None:
        if runtime_range is None:
            return None
        try:
            return runtime_range.contains(Version(self.current_version))
        except InvalidVersion:
            return None

    def _classify_update(
        self,
        *,
        current_contract: RuntimeContract,
        current_range: "_SupportedRuntimeRange",
        proposed_requires: str,
        proposed_recommended: str,
        proposed_range: "_SupportedRuntimeRange",
    ) -> "_ImpactClassification":
        labels: list[str] = []
        range_relation = current_range.relation_to(proposed_range)
        if range_relation["compatible_versions_added"]:
            labels.append(RUNTIME_CONTRACT_IMPACT_RANGE_WIDENING)
        if range_relation["compatible_versions_removed"]:
            labels.append(RUNTIME_CONTRACT_IMPACT_RANGE_TIGHTENING)
        if current_contract.p2p.requires == proposed_requires and current_contract.p2p.recommended != proposed_recommended:
            labels.append(RUNTIME_CONTRACT_IMPACT_RECOMMENDED_ONLY)
        if _runtime_line(current_contract.p2p.recommended) != _runtime_line(proposed_recommended):
            labels.append(RUNTIME_CONTRACT_IMPACT_RUNTIME_LINE_CHANGE)
        active_satisfies = self._active_satisfies(proposed_range)
        if active_satisfies is False:
            labels.append(RUNTIME_CONTRACT_IMPACT_CURRENT_RUNTIME_EXCLUDED)
        return _ImpactClassification(labels=_dedupe(labels), range_comparison=range_relation)

    def _setup_guide_state(self, status: RuntimeStatus) -> dict[str, Any]:
        path = str(relative_to_root(self.setup_guide_path, self.root))
        if not self.setup_guide_path.exists():
            return {
                "path": path,
                "state": RUNTIME_SETUP_GUIDE_STATE_MISSING,
                "planned_action": RUNTIME_SETUP_GUIDE_ACTION_GENERATE,
                "drift_repair": False,
                "blocked_reason": "",
                "content_sha256": None,
            }
        content = self.setup_guide_path.read_text(encoding="utf-8")
        content_sha256 = _sha256_text(content)
        if RUNTIME_SETUP_GUIDE_MARKER not in content:
            return {
                "path": path,
                "state": RUNTIME_SETUP_GUIDE_STATE_UNMANAGED,
                "planned_action": RUNTIME_SETUP_GUIDE_ACTION_BLOCKED,
                "drift_repair": False,
                "blocked_reason": RUNTIME_CONTRACT_BLOCKER_UNMANAGED_SETUP_GUIDE,
                "content_sha256": content_sha256,
            }
        if not status.requires or not status.recommended:
            return {
                "path": path,
                "state": RUNTIME_SETUP_GUIDE_STATE_MANAGED_DRIFTED,
                "planned_action": RUNTIME_SETUP_GUIDE_ACTION_REGENERATE,
                "drift_repair": True,
                "blocked_reason": "",
                "content_sha256": content_sha256,
            }
        expected = self.render_setup_guide(
            RuntimeContract(
                schema_version=RUNTIME_CONTRACT_SCHEMA_VERSION,
                p2p=P2PRuntimeRequirement(requires=status.requires, recommended=status.recommended),
            )
        )
        drifted = _normalize_newlines(content) != _normalize_newlines(expected)
        return {
            "path": path,
            "state": RUNTIME_SETUP_GUIDE_STATE_MANAGED_DRIFTED
            if drifted
            else RUNTIME_SETUP_GUIDE_STATE_MANAGED_ALIGNED,
            "planned_action": RUNTIME_SETUP_GUIDE_ACTION_REGENERATE,
            "drift_repair": drifted,
            "blocked_reason": "",
            "content_sha256": content_sha256,
        }

    def _planned_setup_guide(self, setup_guide: dict[str, Any]) -> dict[str, Any]:
        state = str(setup_guide.get("state") or "")
        if state == RUNTIME_SETUP_GUIDE_STATE_MISSING:
            return {**setup_guide, "planned_action": RUNTIME_SETUP_GUIDE_ACTION_GENERATE}
        if state in {RUNTIME_SETUP_GUIDE_STATE_MANAGED_ALIGNED, RUNTIME_SETUP_GUIDE_STATE_MANAGED_DRIFTED}:
            return {**setup_guide, "planned_action": RUNTIME_SETUP_GUIDE_ACTION_REGENERATE}
        return setup_guide

    def _expected_state_token(
        self,
        *,
        status: RuntimeStatus,
        proposed_requires: str,
        proposed_recommended: str,
        reason: str,
        decision: str,
        impact_labels: list[str],
        setup_guide: dict[str, Any],
    ) -> str:
        token_payload = {
            "schema": "p2p-runtime-contract-update-token/v1",
            "current_contract": self._file_token(self.contract_path),
            "project_manifest": self._file_token(self.project_manifest_path),
            "current_state": status.state,
            "current_requires": status.requires,
            "current_recommended": status.recommended,
            "setup_guide": {
                "state": setup_guide.get("state"),
                "content_sha256": setup_guide.get("content_sha256"),
                "marker_present": setup_guide.get("state")
                in {RUNTIME_SETUP_GUIDE_STATE_MANAGED_ALIGNED, RUNTIME_SETUP_GUIDE_STATE_MANAGED_DRIFTED},
            },
            "proposed": {
                "requires": proposed_requires,
                "recommended": proposed_recommended,
                "reason": reason,
                "decision": decision,
                "impact_labels": list(impact_labels),
            },
        }
        encoded = json.dumps(token_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "runtime-contract-update-v1:" + hashlib.sha256(encoded).hexdigest()

    def _file_token(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"exists": False, "sha256": None}
        return {"exists": True, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def _write_required_contract_marker(self) -> None:
        data = read_yaml_mapping(self.project_manifest_path, default={})
        marker = data.get("runtime_contract")
        if not isinstance(marker, dict):
            marker = {}
        marker["required"] = True
        data["runtime_contract"] = marker
        write_yaml_atomic(self.project_manifest_path, data)

    def _authority_for(self, actor: str) -> RuntimeContractUpdateAuthority:
        actor_text = str(actor or "").strip()
        if not actor_text:
            return RuntimeContractUpdateAuthority(
                required_for_apply=True,
                actor_resolved=False,
                apply_authorized=False,
                status=RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
            )
        try:
            actor_slug = identity_slug(actor_text)
        except ValueError:
            return RuntimeContractUpdateAuthority(
                required_for_apply=True,
                actor_resolved=False,
                apply_authorized=False,
                status=RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
                actor=actor_text,
            )
        path = self.p2p_dir / "project" / "permissions.yml"
        if path.exists():
            try:
                payload = read_yaml_mapping(path, default={})
            except (ValueError, yaml.YAMLError):
                return RuntimeContractUpdateAuthority(
                    required_for_apply=True,
                    actor_resolved=False,
                    apply_authorized=False,
                    status=RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
                    actor=actor_slug,
                    source=str(relative_to_root(path, self.root)),
                )
            identities = payload.get("identities", {})
            identity = identities.get(actor_slug) if isinstance(identities, dict) else None
            if not isinstance(identity, dict):
                return RuntimeContractUpdateAuthority(
                    required_for_apply=True,
                    actor_resolved=False,
                    apply_authorized=False,
                    status=RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
                    actor=actor_slug,
                    source=str(relative_to_root(path, self.root)),
                )
            role = str(identity.get("role") or "")
            authorized = role == "owner"
            return RuntimeContractUpdateAuthority(
                required_for_apply=True,
                actor_resolved=True,
                apply_authorized=authorized,
                status="authorized" if authorized else RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
                actor=actor_slug,
                role=role,
                source=str(relative_to_root(path, self.root)),
            )
        authorized = actor_slug == "owner"
        return RuntimeContractUpdateAuthority(
            required_for_apply=True,
            actor_resolved=authorized,
            apply_authorized=authorized,
            status="authorized" if authorized else RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED,
            actor=actor_slug,
            role="owner" if authorized else "unknown",
            source=str(relative_to_root(path, self.root)),
        )

    def _supported_range(self, value: str) -> "_SupportedRuntimeRange | None":
        value = str(value or "").strip()
        try:
            SpecifierSet(value)
        except InvalidSpecifier:
            return None
        if value.startswith("=="):
            version_text = value[2:].strip()
            if not version_text:
                return None
            try:
                return _SupportedRuntimeRange(kind="exact", exact=Version(version_text))
            except InvalidVersion:
                return None
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 2 or not parts[0].startswith(">=") or not parts[1].startswith("<"):
            return None
        lower_text = parts[0][2:].strip()
        upper_text = parts[1][1:].strip()
        try:
            lower = Version(lower_text)
            upper = Version(upper_text)
        except InvalidVersion:
            return None
        if lower >= upper:
            return None
        return _SupportedRuntimeRange(kind="range", lower=lower, upper=upper)

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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _runtime_line(version: str) -> str:
    try:
        parsed = Version(str(version or "").strip())
    except InvalidVersion:
        return str(version or "").strip()
    if len(parsed.release) >= 2:
        return f"{parsed.release[0]}.{parsed.release[1]}"
    if parsed.release:
        return str(parsed.release[0])
    return str(parsed)


def _required_workflow_for_state(state: str) -> str:
    return {
        RUNTIME_STATUS_INVALID_CONTRACT: "contract_repair",
        RUNTIME_STATUS_UNSUPPORTED_CONTRACT: "contract_schema_migration",
        RUNTIME_STATUS_MISSING_CONTRACT: "contract_recovery",
        RUNTIME_STATUS_LEGACY_UNDECLARED: "contract_adoption",
    }.get(state, "")


@dataclass(frozen=True)
class _ProposedRuntimeContract:
    requires: str
    recommended: str
    range: "_SupportedRuntimeRange | None"
    valid: bool
    errors: list[str]


@dataclass(frozen=True)
class _ImpactClassification:
    labels: list[str]
    range_comparison: dict[str, Any]


@dataclass(frozen=True)
class _SupportedRuntimeRange:
    kind: str
    exact: Version | None = None
    lower: Version | None = None
    upper: Version | None = None

    def contains(self, version: Version) -> bool:
        if self.kind == "exact":
            return self.exact == version
        if self.lower is None or self.upper is None:
            return False
        return self.lower <= version < self.upper

    def relation_to(self, proposed: "_SupportedRuntimeRange") -> dict[str, Any]:
        added = not proposed.is_subset_of(self)
        removed = not self.is_subset_of(proposed)
        return {
            "compatible_versions_added": added,
            "compatible_versions_removed": removed,
            "ranges_overlap": self.overlaps(proposed),
        }

    def is_subset_of(self, other: "_SupportedRuntimeRange") -> bool:
        if self.kind == "exact":
            return self.exact is not None and other.contains(self.exact)
        if other.kind == "exact":
            return False
        if self.lower is None or self.upper is None or other.lower is None or other.upper is None:
            return False
        return other.lower <= self.lower and self.upper <= other.upper

    def overlaps(self, other: "_SupportedRuntimeRange") -> bool:
        if self.kind == "exact":
            return self.exact is not None and other.contains(self.exact)
        if other.kind == "exact":
            return other.exact is not None and self.contains(other.exact)
        if self.lower is None or self.upper is None or other.lower is None or other.upper is None:
            return False
        return max(self.lower, other.lower) < min(self.upper, other.upper)

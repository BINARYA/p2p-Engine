from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Mapping

import yaml

from p2p_engine.core.authority import AuthorityEvidence
from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.mutation_receipts import (
    MUTATION_RECEIPT_MAX_FILE_BYTES,
    MUTATION_RECEIPT_MAX_KEY_BYTES,
    MUTATION_RECEIPT_ROOT,
    MUTATION_RECEIPT_SCHEMA_VERSION,
    MutationPostcondition,
    MutationReceipt,
    MutationReceiptStatus,
)
from p2p_engine.core.vertical_transition_impact import VERTICAL_TRANSITION_IMPACT_CONTRACT
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.workspace_transactions import physical_sha256

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_idempotency_key(value: str) -> str:
    if not isinstance(value, str) or not value or not value.strip():
        raise ValueError("P2P_IDEMPOTENCY_KEY_REQUIRED: a non-empty idempotency key is required")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("P2P_IDEMPOTENCY_KEY_INVALID: key must be valid UTF-8") from exc
    if len(encoded) > MUTATION_RECEIPT_MAX_KEY_BYTES:
        raise ValueError(
            f"P2P_IDEMPOTENCY_KEY_INVALID: key exceeds {MUTATION_RECEIPT_MAX_KEY_BYTES} UTF-8 bytes"
        )
    return value


def idempotency_key_sha256(value: str) -> str:
    return hashlib.sha256(validate_idempotency_key(value).encode("utf-8")).hexdigest()


def preview_token_sha256(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def mutation_request_fingerprint(
    *,
    operation: str,
    actor: str,
    preview_token: str,
    semantic_inputs: Mapping[str, object],
) -> str:
    return semantic_sha256(
        {
            "fingerprint_version": 1,
            "operation": str(operation),
            "actor": str(actor),
            "preview_token_sha256": preview_token_sha256(preview_token),
            "semantic_inputs": dict(semantic_inputs),
        }
    )


class MutationReceiptService:
    def __init__(self, *, root: Path, p2p_dir: Path) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.receipt_root = self.root / MUTATION_RECEIPT_ROOT
        self.transaction_root = self.p2p_dir / ".internal" / "workspace-transactions" / "transactions"

    def relative_path(self, idempotency_key: str) -> str:
        return f"{MUTATION_RECEIPT_ROOT}/{idempotency_key_sha256(idempotency_key)}.yml"

    def fingerprint(
        self,
        *,
        operation: str,
        actor: str,
        preview_token: str,
        semantic_inputs: Mapping[str, object],
    ) -> str:
        return mutation_request_fingerprint(
            operation=operation,
            actor=actor,
            preview_token=preview_token,
            semantic_inputs=semantic_inputs,
        )

    def prepare(
        self,
        *,
        idempotency_key: str,
        operation: str,
        actor: str,
        request_fingerprint_sha256: str,
        preview_token: str,
        result: Mapping[str, object],
        candidates: Mapping[str, bytes],
        authority: AuthorityEvidence | None = None,
    ) -> tuple[str, bytes, MutationReceipt]:
        key_hash = idempotency_key_sha256(idempotency_key)
        _require_sha256(request_fingerprint_sha256, "request fingerprint")
        postconditions = tuple(
            MutationPostcondition(
                path=path,
                physical_sha256=hashlib.sha256(content).hexdigest(),
            )
            for path, content in sorted(candidates.items())
        )
        receipt = MutationReceipt(
            key_sha256=key_hash,
            operation=operation,
            actor=actor,
            request_fingerprint_sha256=request_fingerprint_sha256,
            preview_token_sha256=preview_token_sha256(preview_token),
            completion_status="applied",
            completed_at=_utc_now_iso(),
            result=dict(result),
            postconditions=postconditions,
            authority=(authority.to_dict() if authority is not None else None),
        )
        content = yaml_dump(receipt.to_payload()).encode("utf-8")
        if len(content) > MUTATION_RECEIPT_MAX_FILE_BYTES:
            raise ValueError(
                "P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED: mutation receipt exceeds "
                f"{MUTATION_RECEIPT_MAX_FILE_BYTES} bytes"
            )
        return (
            f"{MUTATION_RECEIPT_ROOT}/{key_hash}.yml",
            content,
            receipt,
        )

    def replay(
        self,
        *,
        idempotency_key: str,
        request_fingerprint_sha256: str,
    ) -> MutationReceipt | None:
        key_hash = idempotency_key_sha256(idempotency_key)
        relative = f"{MUTATION_RECEIPT_ROOT}/{key_hash}.yml"
        incomplete = self._incomplete_status(relative)
        if incomplete is not None:
            raise ValueError(
                "P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION: "
                f"workspace transaction {incomplete.transaction_id or 'unknown'} requires recovery"
            )
        path = self.root / relative
        if not path.exists():
            return None
        receipt = self._read_receipt(path, expected_key_sha256=key_hash)
        if receipt.request_fingerprint_sha256 != request_fingerprint_sha256:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: idempotency key was already used for a different request"
            )
        if not self._postconditions_match(receipt):
            raise ValueError(
                "P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: recorded mutation postconditions no longer match"
            )
        return receipt

    def read(self, *, idempotency_key: str) -> MutationReceipt | None:
        """Read an immutable outcome without re-authorizing or requiring current state."""
        key_hash = idempotency_key_sha256(idempotency_key)
        relative = f"{MUTATION_RECEIPT_ROOT}/{key_hash}.yml"
        incomplete = self._incomplete_status(relative)
        if incomplete is not None:
            raise ValueError(
                "P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION: "
                f"workspace transaction {incomplete.transaction_id or 'unknown'} requires recovery"
            )
        path = self.root / relative
        if not path.exists():
            return None
        return self._read_receipt(path, expected_key_sha256=key_hash)

    def status(self, idempotency_key: str) -> MutationReceiptStatus:
        key_hash = idempotency_key_sha256(idempotency_key)
        relative = f"{MUTATION_RECEIPT_ROOT}/{key_hash}.yml"
        incomplete = self._incomplete_status(relative)
        if incomplete is not None:
            return incomplete
        path = self.root / relative
        if not path.exists():
            return MutationReceiptStatus(
                state="not_found",
                message="No mutation receipt exists for the supplied idempotency key.",
            )
        receipt = self._read_receipt(path, expected_key_sha256=key_hash)
        postconditions_match = self._postconditions_match(receipt)
        return MutationReceiptStatus(
            state="applied" if postconditions_match else "postcondition_drift",
            operation=receipt.operation,
            actor=receipt.actor,
            completion_status=receipt.completion_status,
            result=_public_result(receipt.result),
            authority=receipt.authority,
            postconditions_match=postconditions_match,
            message=(
                "Mutation receipt is complete and its postconditions match."
                if postconditions_match
                else "Mutation receipt is complete but its postconditions have drifted."
            ),
        )

    def _read_receipt(self, path: Path, *, expected_key_sha256: str) -> MutationReceipt:
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("receipt path is not a regular file")
            if path.stat().st_size > MUTATION_RECEIPT_MAX_FILE_BYTES:
                raise ValueError("receipt exceeds the size limit")
            payload = load_yaml(
                path.read_bytes(),
                loader_contract=UNIQUE_LOADER_CONTRACT,
            )
            receipt = _receipt_from_payload(payload)
        except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
            raise ValueError(f"P2P_IDEMPOTENCY_RECEIPT_CORRUPT: {exc}") from exc
        if receipt.key_sha256 != expected_key_sha256:
            raise ValueError(
                "P2P_IDEMPOTENCY_RECEIPT_CORRUPT: receipt key hash does not match its path"
            )
        return receipt

    def _postconditions_match(self, receipt: MutationReceipt) -> bool:
        try:
            return all(
                physical_sha256(self.root / item.path) == item.physical_sha256
                for item in receipt.postconditions
            )
        except (OSError, ValueError):
            return False

    def _incomplete_status(self, receipt_relative: str) -> MutationReceiptStatus | None:
        if not self.transaction_root.exists():
            return None
        matches: list[tuple[str, dict[str, object] | None]] = []
        for transaction_dir in sorted(self.transaction_root.iterdir()):
            if not transaction_dir.is_dir() or transaction_dir.is_symlink():
                continue
            staged = transaction_dir / "candidates" / receipt_relative
            if not staged.is_file() or staged.is_symlink():
                continue
            journal: dict[str, object] | None = None
            journal_path = transaction_dir / "journal.yml"
            if journal_path.is_file() and not journal_path.is_symlink():
                try:
                    loaded = load_yaml(journal_path.read_bytes())
                    journal = loaded if isinstance(loaded, dict) else None
                except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError):
                    journal = None
            matches.append((transaction_dir.name, journal))
        if not matches:
            return None
        transaction_id, journal = matches[0]
        operation = str(journal.get("operation_id") or "") if journal else ""
        actor = str(journal.get("actor") or "") if journal else ""
        state = str(journal.get("state") or "incomplete") if journal else "invalid"
        return MutationReceiptStatus(
            state="incomplete",
            operation=operation,
            actor=actor,
            completion_status=state,
            postconditions_match=None,
            recovery_required=True,
            transaction_id=transaction_id,
            message="The receipt belongs to an incomplete workspace transaction.",
        )


def _receipt_from_payload(payload: object) -> MutationReceipt:
    if not isinstance(payload, dict) or not isinstance(payload.get("mutation_receipt"), dict):
        raise ValueError("receipt document must contain mutation_receipt mapping")
    data = payload["mutation_receipt"]
    assert isinstance(data, dict)
    if data.get("schema_version") != MUTATION_RECEIPT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported receipt schema {data.get('schema_version')!r}; expected {MUTATION_RECEIPT_SCHEMA_VERSION}"
        )
    key_hash = _required_sha256(data, "key_sha256")
    request_fingerprint = _required_sha256(data, "request_fingerprint_sha256")
    token_hash = _required_sha256(data, "preview_token_sha256")
    operation = _required_text(data, "operation")
    if operation not in {
        "init",
        "install",
        "adopt",
        "migrate",
        "proposal_create",
        "proposal_contribution_add",
        "proposal_readiness_assess",
        "proposal_update",
        "proposal_decision_apply",
        "project_authority_rotate",
        "project_identity_adopt",
        "project_identity_derive",
        "project_domain_change",
        "project_memory_scope_change",
        "project_structure_change",
        "project_structure_merge",
        "project_structure_replacement",
        "project_structure_restore",
        "project_structure_retirement",
        "project_structure_export",
    }:
        raise ValueError(f"unsupported receipt operation: {operation}")
    actor = _required_text(data, "actor")
    completion_status = _required_text(data, "completion_status")
    if completion_status != "applied":
        raise ValueError("receipt completion_status must be applied")
    completed_at = _required_text(data, "completed_at")
    result = data.get("result")
    if not isinstance(result, dict):
        raise ValueError("receipt result must be a mapping")
    _validate_result(result, operation=operation)
    raw_authority = data.get("authority")
    authority: Mapping[str, object] | None = None
    if raw_authority is not None:
        if not isinstance(raw_authority, Mapping):
            raise ValueError("receipt authority must be a mapping or null")
        from p2p_engine.services.authority import AuthorityContractCodec

        authority = AuthorityContractCodec().evidence_from_mapping(raw_authority).to_dict()
    if operation in {
        "init",
        "project_authority_rotate",
        "project_identity_adopt",
        "project_identity_derive",
        "project_domain_change",
        "project_memory_scope_change",
        "project_structure_change",
        "project_structure_merge",
        "project_structure_replacement",
        "project_structure_restore",
        "project_structure_retirement",
        "project_structure_export",
        "proposal_decision_apply",
    } and authority is None:
        raise ValueError(f"receipt operation {operation} requires authority evidence")
    raw_postconditions = data.get("postconditions")
    if not isinstance(raw_postconditions, list) or not raw_postconditions:
        raise ValueError("receipt postconditions must be a non-empty sequence")
    postconditions: list[MutationPostcondition] = []
    seen: set[str] = set()
    for raw in raw_postconditions:
        if not isinstance(raw, dict):
            raise ValueError("receipt postcondition must be a mapping")
        path = _validated_postcondition_path(
            _required_text(raw, "path"),
            operation=operation,
        )
        if path in seen:
            raise ValueError(f"duplicate receipt postcondition path: {path}")
        seen.add(path)
        postconditions.append(
            MutationPostcondition(
                path=path,
                physical_sha256=_required_sha256(raw, "physical_sha256"),
            )
        )
    if result["changed_paths"] != [item.path for item in postconditions]:
        raise ValueError("receipt result paths do not match receipt postconditions")
    return MutationReceipt(
        key_sha256=key_hash,
        operation=operation,
        actor=actor,
        request_fingerprint_sha256=request_fingerprint,
        preview_token_sha256=token_hash,
        completion_status=completion_status,
        completed_at=completed_at,
        result=result,
        postconditions=tuple(postconditions),
        authority=authority,
    )


def _validate_result(result: Mapping[str, object], *, operation: str) -> None:
    if operation == "init":
        _validate_init_result(result)
        return
    if operation in {"proposal_create", "proposal_update", "proposal_contribution_add"}:
        _validate_proposal_result(result, operation=operation)
        return
    if operation == "proposal_readiness_assess":
        _validate_proposal_readiness_result(result)
        return
    if operation == "project_authority_rotate":
        _validate_authority_rotation_result(result)
        return
    if operation in {"project_identity_adopt", "project_identity_derive"}:
        _validate_project_identity_result(result, operation=operation)
        return
    if operation == "project_domain_change":
        _validate_project_domain_result(result)
        return
    if operation == "project_memory_scope_change":
        _validate_project_memory_scope_result(result)
        return
    if operation == "project_structure_change":
        _validate_project_structure_result(result)
        return
    if operation == "project_structure_retirement":
        _validate_project_structure_retirement_result(result)
        return
    if operation == "project_structure_replacement":
        _validate_project_structure_replacement_result(result)
        return
    if operation in {"project_structure_merge", "project_structure_restore"}:
        _validate_project_structure_transition_result(result, operation=operation)
        return
    if operation == "project_structure_export":
        _validate_project_structure_export_result(result)
        return
    if operation == "proposal_decision_apply":
        _validate_proposal_decision_result(result)
        return
    allowed = {
        "impact_contract",
        "operation",
        "operation_id",
        "coordinate",
        "analysis_fingerprint_sha256",
        "plan_fingerprint_sha256",
        "semantic_postconditions",
        "decision_summary",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            f"receipt result contains unsupported fields: {', '.join(unknown)}"
        )
    if result.get("operation") != operation:
        raise ValueError("receipt result operation does not match receipt operation")
    if result.get("impact_contract") != VERTICAL_TRANSITION_IMPACT_CONTRACT:
        raise ValueError("receipt result impact_contract is unsupported")
    _required_text(result, "operation_id")
    _required_text(result, "coordinate")
    _required_sha256(result, "analysis_fingerprint_sha256")
    plan_fingerprint = result.get("plan_fingerprint_sha256")
    if plan_fingerprint is not None:
        if not isinstance(plan_fingerprint, str):
            raise ValueError("receipt result plan_fingerprint_sha256 must be text or null")
        _require_sha256(plan_fingerprint, "plan_fingerprint_sha256")
    semantic_postconditions = result.get("semantic_postconditions")
    if operation == "install":
        expected_postconditions = {
            "installed_coordinate",
            "installed_semantic_checksum",
            "installed_artifact_checksum",
        }
        identity_field = "installed_coordinate"
    else:
        expected_postconditions = {
            "active_coordinate",
            "lock_semantic_checksum",
            "lock_artifact_checksum",
            "definition_semantic_sha256",
            "questions_semantic_sha256",
            "rubrics_semantic_sha256",
        }
        identity_field = "active_coordinate"
    if not isinstance(semantic_postconditions, dict) or set(semantic_postconditions) != expected_postconditions:
        raise ValueError("receipt result semantic_postconditions has invalid fields")
    if semantic_postconditions.get(identity_field) != result.get("coordinate"):
        raise ValueError(f"receipt {identity_field} does not match coordinate")
    for field in expected_postconditions - {identity_field}:
        value = semantic_postconditions.get(field)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"receipt semantic postcondition {field} must be text or null")
            _require_sha256(value, field)
    decision_summary = result.get("decision_summary")
    if not isinstance(decision_summary, list) or len(decision_summary) > 128:
        raise ValueError("receipt result decision_summary must be a bounded sequence")
    seen_decisions: set[str] = set()
    for item in decision_summary:
        if not isinstance(item, dict) or not {"id", "action", "source"} <= set(item):
            raise ValueError("receipt result decision summary entry is invalid")
        if set(item) - {"id", "action", "source", "target"}:
            raise ValueError("receipt result decision summary entry has unknown fields")
        decision_id = str(item.get("id") or "")
        if not decision_id.startswith("VTD-") or decision_id in seen_decisions:
            raise ValueError("receipt result decision summary id is invalid or duplicate")
        source = item.get("source")
        if not isinstance(source, dict) or set(source) != {"kind", "ref"}:
            raise ValueError("receipt result decision summary source is invalid")
        action = item.get("action")
        if action not in {"map", "preserve_as_orphan"}:
            raise ValueError("receipt result decision summary action is invalid")
        target = item.get("target")
        if action == "map":
            if not isinstance(target, dict) or set(target) != {"kind", "ref"}:
                raise ValueError("receipt result mapped decision target is invalid")
        elif target is not None:
            raise ValueError("receipt result orphan decision forbids target")
        seen_decisions.add(decision_id)
    changed_paths = result.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        raise ValueError("receipt result changed_paths must be a non-empty sequence")
    normalized = [
        _validated_postcondition_path(str(path), operation=operation)
        for path in changed_paths
    ]
    if normalized != sorted(set(normalized)):
        raise ValueError("receipt result changed_paths must be unique and sorted")


def _validate_init_result(result: Mapping[str, object]) -> None:
    allowed = {
        "operation",
        "operation_id",
        "project",
        "project_identity",
        "domain",
        "structure_source",
        "structure_origin",
        "structure_revision",
        "structure_checksum",
        "authority",
        "created_paths",
        "created_file_paths",
        "agent_selection",
        "agent_instructions",
        "vertical",
        "warnings",
        "mcp_hint",
        "next_steps",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(f"receipt result contains unsupported fields: {', '.join(unknown)}")
    if result.get("operation") != "init":
        raise ValueError("receipt result operation does not match receipt operation")
    if result.get("operation_id") != "project.init":
        raise ValueError("receipt result operation_id is unsupported")
    for field in (
        "project",
        "project_identity",
        "authority",
        "agent_selection",
        "agent_instructions",
        "vertical",
        "mcp_hint",
        "structure_source",
        "structure_origin",
    ):
        if not isinstance(result.get(field), Mapping):
            raise ValueError(f"receipt result {field} must be a mapping")
    from p2p_engine.core.project_identity import project_identity_from_mapping

    identity = project_identity_from_mapping(result.get("project_identity"))
    project = result.get("project")
    if not isinstance(project, Mapping) or project.get("uuid") != identity.project_uuid.value:
        raise ValueError("receipt init project and project identity UUIDs diverge")
    domain = result.get("domain")
    if domain is not None and not isinstance(domain, Mapping):
        raise ValueError("receipt result domain must be a mapping or null")
    structure_revision = result.get("structure_revision")
    if (
        isinstance(structure_revision, bool)
        or not isinstance(structure_revision, int)
        or structure_revision < 1
    ):
        raise ValueError("receipt result structure_revision must be positive")
    structure_checksum = result.get("structure_checksum")
    if (
        not isinstance(structure_checksum, str)
        or len(structure_checksum) != 64
        or any(character not in "0123456789abcdef" for character in structure_checksum)
    ):
        raise ValueError("receipt result structure_checksum must be SHA-256")
    for field in (
        "created_paths",
        "created_file_paths",
        "warnings",
        "next_steps",
        "changed_paths",
    ):
        if not isinstance(result.get(field), list):
            raise ValueError(f"receipt result {field} must be a list")
    changed_paths = result.get("changed_paths")
    assert isinstance(changed_paths, list)
    if not changed_paths:
        raise ValueError("receipt result changed_paths must be a non-empty sequence")
    normalized = [
        _validated_postcondition_path(str(path), operation="init")
        for path in changed_paths
    ]
    if normalized != sorted(set(normalized)):
        raise ValueError("receipt result changed_paths must be unique and sorted")


def _validate_proposal_result(result: Mapping[str, object], *, operation: str) -> None:
    if operation == "proposal_create":
        allowed = {
            "operation",
            "operation_id",
            "proposal",
            "created_paths",
            "changed_paths",
            "next_steps",
        }
        expected_operation_id = "proposal.create"
    elif operation == "proposal_update":
        allowed = {
            "operation",
            "operation_id",
            "proposal_id",
            "path",
            "updated_sections",
            "changed_paths",
        }
        expected_operation_id = "proposal.update"
    else:
        allowed = {
            "operation",
            "operation_id",
            "proposal_id",
            "path",
            "contribution",
            "changed_paths",
            "review_capability",
        }
        expected_operation_id = "proposal.contribution.add"
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(f"receipt result contains unsupported fields: {', '.join(unknown)}")
    if result.get("operation") != operation:
        raise ValueError("receipt result operation does not match receipt operation")
    if result.get("operation_id") != expected_operation_id:
        raise ValueError("receipt result operation_id is unsupported")
    changed_paths = result.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        raise ValueError("receipt result changed_paths must be a non-empty sequence")
    normalized = [
        _validated_postcondition_path(str(path), operation=operation)
        for path in changed_paths
    ]
    if normalized != sorted(set(normalized)):
        raise ValueError("receipt result changed_paths must be unique and sorted")
    if operation == "proposal_create":
        proposal = result.get("proposal")
        if not isinstance(proposal, Mapping):
            raise ValueError("receipt result proposal must be a mapping")
        if set(proposal) != {"proposal_id", "title", "slug", "status", "path"}:
            raise ValueError("receipt result proposal has invalid fields")
        proposal_id = _required_text(proposal, "proposal_id")
        proposal_path = _required_text(proposal, "path")
        if not proposal_id.startswith("PROP-"):
            raise ValueError("receipt result proposal_id is invalid")
        if not proposal_path.startswith(f".p2p/proposals/{proposal_id}-"):
            raise ValueError("receipt result proposal path is invalid")
        created_paths = result.get("created_paths")
        if not isinstance(created_paths, list) or created_paths != changed_paths:
            raise ValueError("receipt result created_paths must match changed_paths")
        next_steps = result.get("next_steps")
        if not isinstance(next_steps, list):
            raise ValueError("receipt result next_steps must be a list")
        return
    if operation == "proposal_contribution_add":
        proposal_id = _required_text(result, "proposal_id")
        path = _required_text(result, "path")
        if not proposal_id.startswith("PROP-"):
            raise ValueError("receipt result proposal_id is invalid")
        if not path.startswith(f".p2p/proposals/{proposal_id}-") or not path.endswith("/contributions.yml"):
            raise ValueError("receipt result contribution path is invalid")
        if changed_paths != [path]:
            raise ValueError("receipt result contribution changed_paths must contain contributions.yml")
        contribution = result.get("contribution")
        if not isinstance(contribution, Mapping):
            raise ValueError("receipt result contribution must be a mapping")
        if set(contribution) != {"contribution_id", "type", "author", "relevance_hint", "text"}:
            raise ValueError("receipt result contribution has invalid fields")
        contribution_id = _required_text(contribution, "contribution_id")
        if not contribution_id.startswith("C"):
            raise ValueError("receipt result contribution_id is invalid")
        _required_text(contribution, "type")
        _required_text(contribution, "text")
        review = result.get("review_capability")
        if not isinstance(review, Mapping) or review.get("supported") is not False:
            raise ValueError("receipt result review_capability must declare unsupported review")
        return
    proposal_id = _required_text(result, "proposal_id")
    proposal_path = _required_text(result, "path")
    if not proposal_id.startswith("PROP-"):
        raise ValueError("receipt result proposal_id is invalid")
    if not proposal_path.startswith(f".p2p/proposals/{proposal_id}-"):
        raise ValueError("receipt result path is invalid")
    if changed_paths != [proposal_path]:
        raise ValueError("receipt result update changed_paths must contain the proposal path")
    updated_sections = result.get("updated_sections")
    if not isinstance(updated_sections, list) or not updated_sections:
        raise ValueError("receipt result updated_sections must be a non-empty list")
    allowed_sections = {
        "problem",
        "context",
        "goals",
        "non_goals",
        "proposal",
        "acceptance_criteria",
    }
    if any(str(section) not in allowed_sections for section in updated_sections):
        raise ValueError("receipt result updated_sections contains an invalid section")


def _validate_proposal_readiness_result(result: Mapping[str, object]) -> None:
    allowed = {
        "operation",
        "operation_id",
        "proposal_id",
        "path",
        "readiness",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt readiness result contains unsupported fields: "
            + ", ".join(unknown)
        )
    if result.get("operation") != "proposal_readiness_assess":
        raise ValueError("receipt readiness result operation is unsupported")
    if result.get("operation_id") != "proposal.readiness.assess":
        raise ValueError("receipt readiness result operation_id is unsupported")
    proposal_id = _required_text(result, "proposal_id")
    if not re.fullmatch(r"PROP-\d{3,}", proposal_id):
        raise ValueError("receipt readiness result proposal_id is invalid")
    path = _required_text(result, "path")
    if not path.startswith(f".p2p/proposals/{proposal_id}-") or not path.endswith(
        "/readiness.yml"
    ):
        raise ValueError("receipt readiness result path is invalid")
    changed_paths = result.get("changed_paths")
    if changed_paths != [path]:
        raise ValueError(
            "receipt readiness changed_paths must contain only readiness.yml"
        )
    readiness = result.get("readiness")
    if not isinstance(readiness, Mapping):
        raise ValueError("receipt readiness result must contain readiness mapping")
    expected_fields = {
        "status",
        "profile_id",
        "profile_version",
        "computed_score",
        "computed_label",
        "confidence",
        "failed_gates",
        "missing",
        "suggested_next",
        "owner_question_state",
        "freshness",
        "assessment_policy_version",
        "source_fingerprint_sha256",
    }
    if set(readiness) != expected_fields:
        raise ValueError("receipt readiness summary has invalid fields")
    if readiness.get("status") != "assessed":
        raise ValueError("receipt readiness status must be assessed")
    _required_text(readiness, "profile_id")
    _required_text(readiness, "profile_version")
    score = readiness.get("computed_score")
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("receipt readiness computed_score must be 0..100")
    if readiness.get("computed_label") not in {
        "weak",
        "partial",
        "strong",
        "decision_ready",
    }:
        raise ValueError("receipt readiness computed_label is invalid")
    if readiness.get("confidence") not in {"low", "medium", "high"}:
        raise ValueError("receipt readiness confidence is invalid")
    if readiness.get("freshness") != "current":
        raise ValueError("receipt readiness freshness must be current")
    policy_version = readiness.get("assessment_policy_version")
    if isinstance(policy_version, bool) or not isinstance(policy_version, int) or policy_version < 1:
        raise ValueError("receipt readiness assessment policy is invalid")
    _required_sha256(readiness, "source_fingerprint_sha256")
    for field in ("failed_gates", "missing", "suggested_next"):
        _validate_bounded_receipt_sequence(readiness.get(field), field=field)
    owner_question_state = readiness.get("owner_question_state")
    if not isinstance(owner_question_state, Mapping):
        raise ValueError("receipt readiness owner_question_state must be a mapping")
    _validate_bounded_receipt_value(
        owner_question_state,
        field="owner_question_state",
        depth=0,
    )


def _validate_project_identity_result(
    result: Mapping[str, object],
    *,
    operation: str,
) -> None:
    allowed = {
        "operation",
        "operation_id",
        "kind",
        "request",
        "previous_identity",
        "current_identity",
        "source_revision",
        "backup_path",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt project-identity result contains unsupported fields: "
            + ", ".join(unknown)
        )
    expected_kind = "adopt" if operation == "project_identity_adopt" else "derive"
    expected_operation_id = f"project-identity-{expected_kind}"
    if result.get("operation") != operation:
        raise ValueError("receipt project-identity operation is unsupported")
    if result.get("operation_id") != expected_operation_id:
        raise ValueError("receipt project-identity operation_id is invalid")
    if result.get("kind") != expected_kind:
        raise ValueError("receipt project-identity kind is invalid")
    request = result.get("request")
    if not isinstance(request, Mapping) or set(request) != {
        "display_name",
        "retain_lineage",
        "lineage_visibility",
    }:
        raise ValueError("receipt project-identity request is invalid")
    if not isinstance(request.get("display_name"), str):
        raise ValueError("receipt project-identity display_name must be text")
    if not isinstance(request.get("retain_lineage"), bool):
        raise ValueError("receipt project-identity retain_lineage must be boolean")
    if request.get("lineage_visibility") not in {"preserved", "private"}:
        raise ValueError("receipt project-identity lineage_visibility is invalid")
    from p2p_engine.core.project_identity import project_identity_from_mapping

    current = project_identity_from_mapping(result.get("current_identity"))
    previous_raw = result.get("previous_identity")
    previous = (
        project_identity_from_mapping(previous_raw)
        if isinstance(previous_raw, Mapping)
        else None
    )
    if expected_kind == "adopt" and previous_raw is not None:
        raise ValueError("receipt identity adoption cannot have a previous identity")
    if expected_kind == "derive":
        if previous is None or previous.project_uuid == current.project_uuid:
            raise ValueError("receipt identity derivation must create a new project UUID")
        if current.remote_binding is not None or current.mode.value != "standalone":
            raise ValueError("receipt identity derivation must remove active remote binding")
    source = result.get("source_revision")
    if not isinstance(source, Mapping) or set(source) != {"namespace", "sha256"}:
        raise ValueError("receipt project-identity source revision is invalid")
    if source.get("namespace") != "source_memory":
        raise ValueError("receipt project-identity source revision namespace is invalid")
    _require_sha256(str(source.get("sha256") or ""), "source_revision.sha256")
    backup = result.get("backup_path")
    if expected_kind == "adopt":
        if (
            not isinstance(backup, str)
            or not backup.startswith(".p2p/.internal/identity-adoption-backups/")
            or not backup.endswith("/project.yml")
        ):
            raise ValueError("receipt identity adoption backup path is invalid")
    elif backup is not None:
        raise ValueError("receipt identity derivation cannot claim an adoption backup")
    changed = result.get("changed_paths")
    if not isinstance(changed, list) or changed != sorted(set(changed)):
        raise ValueError("receipt project-identity changed paths must be unique and sorted")
    required = {
        ".p2p/project.yml",
        ".p2p/project/identity.yml",
        ".p2p/local/replica.yml",
    }
    if expected_kind == "adopt":
        required.add(str(backup))
        accepted_changed_paths = {
            frozenset(required),
            frozenset({*required, ".p2p/local/storage.yml"}),
        }
        if frozenset(changed) not in accepted_changed_paths:
            raise ValueError("receipt project-identity changed paths are invalid")


def _validate_authority_rotation_result(result: Mapping[str, object]) -> None:
    allowed = {
        "operation",
        "operation_id",
        "previous_descriptor",
        "new_descriptor",
        "rotation_request",
        "event_id",
        "event_path",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt authority rotation result contains unsupported fields: "
            + ", ".join(unknown)
        )
    if result.get("operation") != "project_authority_rotate":
        raise ValueError("receipt authority rotation operation is unsupported")
    if result.get("operation_id") != "project.authority.rotate":
        raise ValueError("receipt authority rotation operation_id is unsupported")
    from p2p_engine.services.authority import AuthorityContractCodec

    codec = AuthorityContractCodec()
    previous = result.get("previous_descriptor")
    target = result.get("new_descriptor")
    if not isinstance(previous, Mapping) or not isinstance(target, Mapping):
        raise ValueError("receipt authority rotation descriptors must be mappings")
    previous_descriptor = codec.descriptor_from_mapping(previous)
    new_descriptor = codec.descriptor_from_mapping(target)
    if new_descriptor.generation != previous_descriptor.generation + 1:
        raise ValueError("receipt authority rotation generation must advance exactly once")
    request = result.get("rotation_request")
    if not isinstance(request, Mapping) or set(request) != {
        "target_mode",
        "replacement_authority_id",
        "provider_id",
        "provider_policy_version",
        "display_name",
        "rotated_at",
    }:
        raise ValueError("receipt authority rotation request has invalid fields")
    _required_text(result, "event_id")
    event_path = _required_text(result, "event_path")
    if event_path != ".p2p/project/authority-events.yml":
        raise ValueError("receipt authority rotation event path is invalid")
    changed_paths = result.get("changed_paths")
    expected_paths = [
        ".p2p/project/authority-events.yml",
        ".p2p/project/authority.yml",
    ]
    if changed_paths != expected_paths:
        raise ValueError("receipt authority rotation changed paths are invalid")


def _validate_project_domain_result(result: Mapping[str, object]) -> None:
    allowed = {
        "contract",
        "operation",
        "operation_id",
        "requested_operation",
        "previous",
        "current",
        "project_memory_revision",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt project-domain result contains unsupported fields: "
            + ", ".join(unknown)
        )
    if result.get("operation") != "project_domain_change":
        raise ValueError("receipt project-domain operation is unsupported")
    requested = result.get("requested_operation")
    if requested not in {"set", "clear"}:
        raise ValueError("receipt project-domain requested operation is invalid")
    if result.get("operation_id") != f"project.domain.{requested}":
        raise ValueError("receipt project-domain operation_id is invalid")
    from p2p_engine.core.project_domain import PROJECT_DOMAIN_CONTRACT
    from p2p_engine.services.project_domain import project_domain_state_from_mapping

    if result.get("contract") != PROJECT_DOMAIN_CONTRACT:
        raise ValueError("receipt project-domain contract is unsupported")
    previous = project_domain_state_from_mapping(result.get("previous"))
    current = project_domain_state_from_mapping(result.get("current"))
    if current.revision != previous.revision + 1:
        raise ValueError("receipt project-domain revision must advance exactly once")
    if requested == "set" and current.descriptor is None:
        raise ValueError("receipt project-domain set requires a descriptor")
    if requested == "clear" and current.descriptor is not None:
        raise ValueError("receipt project-domain clear requires a null descriptor")
    memory_revision = _required_sha256(result, "project_memory_revision")
    if memory_revision != current.project_memory_revision:
        raise ValueError("receipt project-domain memory revision is inconsistent")
    if result.get("changed_paths") != [".p2p/project/domain.yml"]:
        raise ValueError("receipt project-domain path is invalid")


def _validate_project_structure_result(result: Mapping[str, object]) -> None:
    allowed = {
        "contract",
        "operation",
        "operation_id",
        "requested_operation",
        "request",
        "expected_revision",
        "previous_revision",
        "previous_checksum",
        "current",
        "event",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt project-structure result contains unsupported fields: "
            + ", ".join(unknown)
        )
    if result.get("operation") != "project_structure_change":
        raise ValueError("receipt project-structure operation is unsupported")
    requested = result.get("requested_operation")
    if requested not in {"add_section", "update_metadata", "reorder_sections"}:
        raise ValueError("receipt project-structure requested operation is invalid")
    if result.get("operation_id") != f"project.structure.{requested}":
        raise ValueError("receipt project-structure operation_id is invalid")
    from p2p_engine.core.project_structure import (
        PROJECT_STRUCTURE_CONTRACT,
        PROJECT_STRUCTURE_MUTATION_CONTRACT,
        normalize_structure_id,
        project_structure_event_from_mapping,
    )

    if result.get("contract") != PROJECT_STRUCTURE_MUTATION_CONTRACT:
        raise ValueError("receipt project-structure contract is unsupported")
    request = result.get("request")
    if not isinstance(request, Mapping):
        raise ValueError("receipt project-structure request must be a mapping")
    current = result.get("current")
    if not isinstance(current, Mapping) or set(current) != {
        "contract",
        "structure_id",
        "revision",
        "checksum",
    }:
        raise ValueError("receipt project-structure current summary is invalid")
    if current.get("contract") != PROJECT_STRUCTURE_CONTRACT:
        raise ValueError("receipt project-structure current contract is unsupported")
    normalize_structure_id(current.get("structure_id"), field_name="structure_id")
    current_revision = current.get("revision")
    current_checksum = _required_sha256(current, "checksum")
    event = project_structure_event_from_mapping(result.get("event"))
    expected_revision = result.get("expected_revision")
    previous_revision = result.get("previous_revision")
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 1
        or previous_revision != expected_revision
        or current_revision != expected_revision + 1
    ):
        raise ValueError("receipt project-structure revision transition is invalid")
    previous_checksum = _required_sha256(result, "previous_checksum")
    if previous_checksum == current_checksum:
        raise ValueError("receipt project-structure mutation did not change semantics")
    if event.revision != current_revision or event.checksum != current_checksum:
        raise ValueError("receipt project-structure event does not match current structure")
    expected_paths = [
        ".p2p/project/structure-events.yml",
        ".p2p/project/structure-snapshots.yml",
        ".p2p/project/structure.yml",
    ]
    if result.get("changed_paths") != expected_paths:
        raise ValueError("receipt project-structure changed paths are invalid")


def _validate_project_structure_retirement_result(result: Mapping[str, object]) -> None:
    allowed = {
        "contract",
        "operation",
        "operation_id",
        "request",
        "resolved_targets",
        "previous_revision",
        "previous_checksum",
        "current",
        "previous_memory_revision",
        "current_memory_revision",
        "event",
        "applied_dispositions",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt project-structure-retirement result contains unsupported fields: "
            + ", ".join(unknown)
        )
    from p2p_engine.core.project_structure import (
        PROJECT_STRUCTURE_CONTRACT,
        normalize_structure_id,
        project_structure_event_from_mapping,
    )
    from p2p_engine.core.project_structure_retirement import (
        STRUCTURE_RETIREMENT_PLAN_CONTRACT,
        STRUCTURE_RETIREMENT_RESULT_CONTRACT,
    )

    if result.get("contract") != STRUCTURE_RETIREMENT_RESULT_CONTRACT:
        raise ValueError("receipt project-structure-retirement contract is unsupported")
    if result.get("operation") != "project_structure_retirement":
        raise ValueError("receipt project-structure-retirement operation is unsupported")
    if result.get("operation_id") != "project.structure.retire.apply":
        raise ValueError("receipt project-structure-retirement operation_id is invalid")
    request = result.get("request")
    if not isinstance(request, Mapping) or set(request) != {
        "contract",
        "expected_structure_revision",
        "expected_memory_revision",
        "targets",
        "plan",
    }:
        raise ValueError("receipt project-structure-retirement request is invalid")
    if request.get("contract") != STRUCTURE_RETIREMENT_PLAN_CONTRACT:
        raise ValueError("receipt project-structure-retirement request contract is unsupported")
    _required_sha256(request, "expected_memory_revision")
    expected_revision = request.get("expected_structure_revision")
    previous_revision = result.get("previous_revision")
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 1
        or isinstance(previous_revision, bool)
        or not isinstance(previous_revision, int)
        or previous_revision != expected_revision
    ):
        raise ValueError("receipt project-structure-retirement previous revision is invalid")
    request_targets = request.get("targets")
    if not isinstance(request_targets, list) or not request_targets:
        raise ValueError("receipt project-structure-retirement request targets are invalid")
    _validate_bounded_receipt_value(
        request_targets,
        field="request.targets",
        depth=0,
    )
    applied_dispositions = result.get("applied_dispositions")
    if not isinstance(applied_dispositions, list):
        raise ValueError("receipt project-structure-retirement applied_dispositions must be a list")
    _validate_bounded_receipt_value(
        applied_dispositions,
        field="applied_dispositions",
        depth=0,
    )
    resolved_targets = result.get("resolved_targets")
    if not isinstance(resolved_targets, list) or not resolved_targets:
        raise ValueError("receipt project-structure-retirement resolved targets are invalid")
    for target in resolved_targets:
        if not isinstance(target, Mapping):
            raise ValueError("receipt project-structure-retirement target must be a mapping")
        normalize_structure_id(target.get("id"), field_name="target.id")
    plan = request.get("plan")
    if not isinstance(plan, Mapping) or plan.get("contract") != STRUCTURE_RETIREMENT_PLAN_CONTRACT:
        raise ValueError("receipt project-structure-retirement plan is invalid")
    dispositions = plan.get("dispositions")
    if not isinstance(dispositions, list):
        raise ValueError("receipt project-structure-retirement dispositions must be a list")
    current = result.get("current")
    if not isinstance(current, Mapping) or set(current) != {
        "contract",
        "structure_id",
        "revision",
        "checksum",
    }:
        raise ValueError("receipt project-structure-retirement current summary is invalid")
    if current.get("contract") != PROJECT_STRUCTURE_CONTRACT:
        raise ValueError("receipt project-structure-retirement current contract is unsupported")
    normalize_structure_id(current.get("structure_id"), field_name="structure_id")
    current_revision = current.get("revision")
    current_checksum = _required_sha256(current, "checksum")
    previous_checksum = _required_sha256(result, "previous_checksum")
    if (
        isinstance(current_revision, bool)
        or not isinstance(current_revision, int)
        or current_revision != previous_revision + 1
        or current_checksum == previous_checksum
    ):
        raise ValueError("receipt project-structure-retirement revision transition is invalid")
    previous_memory = _required_sha256(result, "previous_memory_revision")
    current_memory = _required_sha256(result, "current_memory_revision")
    if request.get("expected_memory_revision") != previous_memory:
        raise ValueError("receipt project-structure-retirement memory precondition is invalid")
    _require_sha256(current_memory, "current_memory_revision")
    event = project_structure_event_from_mapping(result.get("event"))
    if (
        event.event_type != "elements_retired"
        or event.revision != current_revision
        or event.checksum != current_checksum
    ):
        raise ValueError("receipt project-structure-retirement event is inconsistent")
    changed_paths = result.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        raise ValueError("receipt project-structure-retirement changed_paths must be non-empty")
    normalized = [
        _validated_postcondition_path(str(path), operation="project_structure_retirement")
        for path in changed_paths
    ]
    if normalized != sorted(set(normalized)):
        raise ValueError("receipt project-structure-retirement changed_paths must be unique and sorted")
    required_structure_paths = {
        ".p2p/project/structure-events.yml",
        ".p2p/project/structure.yml",
    }
    if not required_structure_paths <= set(normalized):
        raise ValueError("receipt project-structure-retirement changed_paths miss structure files")


def _validate_project_structure_replacement_result(result: Mapping[str, object]) -> None:
    allowed = {
        "contract",
        "status",
        "operation",
        "operation_id",
        "request",
        "target",
        "previous_revision",
        "previous_checksum",
        "current",
        "previous_memory_revision",
        "current_memory_revision",
        "event",
        "applied_dispositions",
        "readiness_identity",
        "classification_identity",
        "receipt",
        "detached_copy",
        "active_release_subscription",
        "remote_publication",
        "publisher_ownership_granted",
        "moderation_rights_granted",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt project-structure-replacement result contains unsupported fields: "
            + ", ".join(unknown)
        )
    from p2p_engine.core.portable_verticals import (
        PORTABLE_VERTICAL_SCHEMA_VERSION,
        VerticalCoordinate,
    )
    from p2p_engine.core.project_structure import (
        PROJECT_STRUCTURE_CONTRACT,
        normalize_structure_id,
        project_structure_event_from_mapping,
    )
    from p2p_engine.core.project_structure_replacement import (
        PROJECT_STRUCTURE_REPLACEMENT_CAPABILITY,
        PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
        PROJECT_STRUCTURE_REPLACEMENT_OPERATION_ID,
        STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
        STRUCTURE_REPLACEMENT_RESULT_CONTRACT,
    )

    if result.get("contract") != STRUCTURE_REPLACEMENT_RESULT_CONTRACT:
        raise ValueError("receipt project-structure-replacement contract is unsupported")
    if result.get("status") != "applied":
        raise ValueError("receipt project-structure-replacement status is invalid")
    if result.get("operation") != PROJECT_STRUCTURE_REPLACEMENT_OPERATION:
        raise ValueError("receipt project-structure-replacement operation is unsupported")
    if result.get("operation_id") != PROJECT_STRUCTURE_REPLACEMENT_OPERATION_ID:
        raise ValueError("receipt project-structure-replacement operation_id is invalid")
    request = result.get("request")
    if not isinstance(request, Mapping) or set(request) != {
        "contract",
        "expected_structure_revision",
        "expected_memory_revision",
        "plan",
    }:
        raise ValueError("receipt project-structure-replacement request is invalid")
    if request.get("contract") != STRUCTURE_REPLACEMENT_PLAN_CONTRACT:
        raise ValueError("receipt project-structure-replacement request contract is unsupported")
    _required_sha256(request, "expected_memory_revision")
    plan = request.get("plan")
    if not isinstance(plan, Mapping) or plan.get("contract") != STRUCTURE_REPLACEMENT_PLAN_CONTRACT:
        raise ValueError("receipt project-structure-replacement plan is invalid")
    plan_target = plan.get("target")
    if not isinstance(plan_target, Mapping):
        raise ValueError("receipt project-structure-replacement plan target is invalid")
    plan_coordinate = _required_text(plan_target, "coordinate")
    plan_checksum = _required_sha256(plan_target, "semantic_checksum")
    VerticalCoordinate.parse(plan_coordinate)
    dispositions = plan.get("dispositions")
    if not isinstance(dispositions, list):
        raise ValueError("receipt project-structure-replacement dispositions must be a list")
    _validate_bounded_receipt_value(dispositions, field="plan.dispositions", depth=0)
    target = result.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("receipt project-structure-replacement target is invalid")
    coordinate = _required_text(target, "coordinate")
    VerticalCoordinate.parse(coordinate)
    target_checksum = _required_sha256(target, "semantic_checksum")
    if coordinate != plan_coordinate or target_checksum != plan_checksum:
        raise ValueError("receipt project-structure-replacement target and plan diverge")
    schema_version = target.get("schema_version")
    if schema_version != PORTABLE_VERTICAL_SCHEMA_VERSION:
        raise ValueError("receipt project-structure-replacement target schema is unsupported")
    current = result.get("current")
    if not isinstance(current, Mapping) or set(current) != {
        "contract",
        "structure_id",
        "revision",
        "checksum",
    }:
        raise ValueError("receipt project-structure-replacement current summary is invalid")
    if current.get("contract") != PROJECT_STRUCTURE_CONTRACT:
        raise ValueError("receipt project-structure-replacement current contract is unsupported")
    normalize_structure_id(current.get("structure_id"), field_name="structure_id")
    expected_revision = request.get("expected_structure_revision")
    previous_revision = result.get("previous_revision")
    current_revision = current.get("revision")
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 1
        or isinstance(previous_revision, bool)
        or not isinstance(previous_revision, int)
        or previous_revision != expected_revision
        or isinstance(current_revision, bool)
        or not isinstance(current_revision, int)
        or current_revision != previous_revision + 1
    ):
        raise ValueError("receipt project-structure-replacement revision transition is invalid")
    current_checksum = _required_sha256(current, "checksum")
    previous_checksum = _required_sha256(result, "previous_checksum")
    if current_checksum == previous_checksum:
        raise ValueError("receipt project-structure-replacement did not change semantics")
    previous_memory = _required_sha256(result, "previous_memory_revision")
    current_memory = _required_sha256(result, "current_memory_revision")
    if request.get("expected_memory_revision") != previous_memory:
        raise ValueError("receipt project-structure-replacement memory precondition is invalid")
    event = project_structure_event_from_mapping(result.get("event"))
    if (
        event.event_type != "structure_replaced"
        or event.revision != current_revision
        or event.checksum != current_checksum
    ):
        raise ValueError("receipt project-structure-replacement event is inconsistent")
    if event.details.get("detached_copy") is not True:
        raise ValueError("receipt project-structure-replacement event is not detached")
    applied_dispositions = result.get("applied_dispositions")
    if not isinstance(applied_dispositions, list):
        raise ValueError("receipt project-structure-replacement applied_dispositions must be a list")
    _validate_bounded_receipt_value(
        applied_dispositions,
        field="applied_dispositions",
        depth=0,
    )
    for field in ("readiness_identity", "classification_identity"):
        identity = result.get(field)
        if not isinstance(identity, Mapping) or set(identity) != {
            "structure_id",
            "structure_revision",
            "structure_checksum",
            "memory_revision",
        }:
            raise ValueError(f"receipt project-structure-replacement {field} is invalid")
        if identity.get("structure_id") != current.get("structure_id"):
            raise ValueError(f"receipt project-structure-replacement {field} structure id diverges")
        if identity.get("structure_revision") != current_revision:
            raise ValueError(f"receipt project-structure-replacement {field} revision diverges")
        if identity.get("structure_checksum") != current_checksum:
            raise ValueError(f"receipt project-structure-replacement {field} checksum diverges")
        if identity.get("memory_revision") != current_memory:
            raise ValueError(f"receipt project-structure-replacement {field} memory diverges")
    receipt = result.get("receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("receipt project-structure-replacement receipt summary is invalid")
    if receipt.get("capability") != PROJECT_STRUCTURE_REPLACEMENT_CAPABILITY:
        raise ValueError("receipt project-structure-replacement capability is invalid")
    _required_sha256(receipt, "operation_key_sha256")
    if result.get("detached_copy") is not True:
        raise ValueError("receipt project-structure-replacement must be detached")
    for field in (
        "active_release_subscription",
        "remote_publication",
        "publisher_ownership_granted",
        "moderation_rights_granted",
    ):
        if result.get(field) is not False:
            raise ValueError(f"receipt project-structure-replacement {field} must be false")
    changed_paths = result.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        raise ValueError("receipt project-structure-replacement changed_paths must be non-empty")
    normalized = [
        _validated_postcondition_path(str(path), operation="project_structure_replacement")
        for path in changed_paths
    ]
    if normalized != sorted(set(normalized)):
        raise ValueError("receipt project-structure-replacement changed_paths must be unique and sorted")
    required_structure_paths = {
        ".p2p/project/structure-events.yml",
        ".p2p/project/structure.yml",
    }
    if not required_structure_paths <= set(normalized):
        raise ValueError("receipt project-structure-replacement changed_paths miss structure files")


def _validate_project_structure_transition_result(
    result: Mapping[str, object],
    *,
    operation: str,
) -> None:
    from p2p_engine.core.project_structure import project_structure_event_from_mapping
    from p2p_engine.core.project_structure_merge_restore import (
        StructureSourceIdentity,
        structure_merge_plan_from_mapping,
        structure_restore_plan_from_mapping,
    )

    expected = {
        "contract",
        "operation",
        "operation_id",
        "status",
        "request",
        "source",
        "previous",
        "current",
        "previous_memory_revision",
        "current_memory_revision",
        "event",
        "changed_entities",
        "detached_copy",
        "active_release_subscription",
        "second_authority_created",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in set(result) - expected)
    missing = sorted(expected - set(result))
    if unknown or missing:
        raise ValueError(
            "receipt project-structure-transition fields are not exact: "
            f"missing={missing}, unsupported={unknown}"
        )
    if result.get("contract") != "p2p-structure-transition-receipt/v1":
        raise ValueError("receipt project-structure-transition contract is unsupported")
    if result.get("operation") != operation or result.get("status") != "applied":
        raise ValueError("receipt project-structure-transition operation/status is invalid")
    suffix = "merge" if operation == "project_structure_merge" else "restore"
    if result.get("operation_id") != f"project.structure.{suffix}.apply":
        raise ValueError("receipt project-structure-transition operation_id is invalid")
    request = result.get("request")
    if not isinstance(request, Mapping) or set(request) != {"contract", "plan"}:
        raise ValueError("receipt project-structure-transition request is invalid")
    if suffix == "merge":
        structure_merge_plan_from_mapping(request.get("plan"))
    else:
        structure_restore_plan_from_mapping(request.get("plan"))
    source = result.get("source")
    if not isinstance(source, Mapping) or set(source) != {
        "kind",
        "identity",
        "digest",
        "schema_version",
    }:
        raise ValueError("receipt project-structure-transition source is invalid")
    StructureSourceIdentity(
        kind=str(source.get("kind") or ""),
        identity=str(source.get("identity") or ""),
        digest=str(source.get("digest") or ""),
        schema_version=int(source.get("schema_version") or 0),
    )
    summaries: dict[str, Mapping[str, object]] = {}
    for field in ("previous", "current"):
        value = result.get(field)
        if not isinstance(value, Mapping) or set(value) != {
            "structure_id",
            "revision",
            "checksum",
        }:
            raise ValueError(f"receipt project-structure-transition {field} is invalid")
        _require_sha256(str(value.get("checksum") or ""), f"{field}.checksum")
        revision = value.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValueError(f"receipt project-structure-transition {field} revision is invalid")
        summaries[field] = value
    if summaries["current"]["revision"] != summaries["previous"]["revision"] + 1:
        raise ValueError("receipt project-structure-transition is not forward-only")
    if summaries["current"]["structure_id"] != summaries["previous"]["structure_id"]:
        raise ValueError("receipt project-structure-transition changed structure identity")
    for field in ("previous_memory_revision", "current_memory_revision"):
        _require_sha256(str(result.get(field) or ""), field)
    event = project_structure_event_from_mapping(result.get("event"))
    if event.event_type != f"structure_{'merged' if suffix == 'merge' else 'restored'}":
        raise ValueError("receipt project-structure-transition event type is invalid")
    if event.revision != summaries["current"]["revision"] or event.checksum != summaries["current"]["checksum"]:
        raise ValueError("receipt project-structure-transition event diverges")
    changed_entities = result.get("changed_entities")
    if not isinstance(changed_entities, list) or changed_entities != sorted(set(changed_entities)):
        raise ValueError("receipt project-structure-transition changed entities are invalid")
    required_entities = {
        "project.mutation_receipt",
        "project.structure",
        "project.structure_events",
        "project.structure_snapshots",
    }
    if set(changed_entities) != required_entities:
        raise ValueError("receipt project-structure-transition changed entities are incomplete")
    for field in (
        "detached_copy",
        "active_release_subscription",
        "second_authority_created",
    ):
        expected_value = field == "detached_copy"
        if result.get(field) is not expected_value:
            raise ValueError(f"receipt project-structure-transition {field} is invalid")
    changed_paths = result.get("changed_paths")
    if not isinstance(changed_paths, list) or changed_paths != sorted(set(changed_paths)):
        raise ValueError("receipt project-structure-transition changed paths are invalid")
    for path in changed_paths:
        _validated_postcondition_path(str(path), operation=operation)
    required_paths = {
        ".p2p/project/structure.yml",
        ".p2p/project/structure-events.yml",
        ".p2p/project/structure-snapshots.yml",
    }
    if not required_paths <= set(changed_paths):
        raise ValueError("receipt project-structure-transition changed paths are incomplete")


def _validate_project_structure_export_result(result: Mapping[str, object]) -> None:
    allowed = {
        "contract",
        "status",
        "operation",
        "operation_id",
        "request",
        "source",
        "lineage",
        "domain_metadata",
        "draft",
        "package",
        "receipt",
        "remote_publication",
        "publisher_ownership_granted",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt project-structure-export result contains unsupported fields: "
            + ", ".join(unknown)
        )
    from p2p_engine.core.project_structure_export import (
        PROJECT_STRUCTURE_EXPORT_CAPABILITY,
        PROJECT_STRUCTURE_EXPORT_OPERATION,
        PROJECT_STRUCTURE_EXPORT_OPERATION_ID,
        PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT,
    )

    if result.get("contract") != PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT:
        raise ValueError("receipt project-structure-export contract is unsupported")
    if result.get("status") != "applied":
        raise ValueError("receipt project-structure-export status is invalid")
    if result.get("operation") != PROJECT_STRUCTURE_EXPORT_OPERATION:
        raise ValueError("receipt project-structure-export operation is unsupported")
    if result.get("operation_id") != PROJECT_STRUCTURE_EXPORT_OPERATION_ID:
        raise ValueError("receipt project-structure-export operation_id is invalid")
    request = result.get("request")
    if not isinstance(request, Mapping):
        raise ValueError("receipt project-structure-export request must be a mapping")
    source = result.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("receipt project-structure-export source must be a mapping")
    _required_text(source, "structure_id")
    for field in ("checksum", "active_semantic_hash"):
        _required_sha256(source, field)
    revision = source.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("receipt project-structure-export source revision is invalid")
    lineage = result.get("lineage")
    if not isinstance(lineage, Mapping) or lineage.get("mode") not in {"derived", "independent"}:
        raise ValueError("receipt project-structure-export lineage is invalid")
    domain_metadata = result.get("domain_metadata")
    if not isinstance(domain_metadata, Mapping):
        raise ValueError("receipt project-structure-export domain metadata is invalid")
    draft = result.get("draft")
    if not isinstance(draft, Mapping):
        raise ValueError("receipt project-structure-export draft is invalid")
    draft_id = _required_text(draft, "draft_id")
    if not draft_id.startswith("VDRAFT-"):
        raise ValueError("receipt project-structure-export draft ID is invalid")
    draft_revision = draft.get("revision")
    if isinstance(draft_revision, bool) or not isinstance(draft_revision, int) or draft_revision < 1:
        raise ValueError("receipt project-structure-export draft revision is invalid")
    _required_sha256(draft, "document_hash")
    package = result.get("package")
    if not isinstance(package, Mapping):
        raise ValueError("receipt project-structure-export package is invalid")
    coordinate = _required_text(package, "coordinate")
    if coordinate != request.get("coordinate"):
        raise ValueError("receipt project-structure-export coordinate mismatch")
    _required_sha256(package, "semantic_checksum")
    _required_sha256(package, "artifact_checksum")
    size = package.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ValueError("receipt project-structure-export package size is invalid")
    entries = package.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("receipt project-structure-export package entries are invalid")
    receipt = result.get("receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("receipt project-structure-export receipt summary is invalid")
    if receipt.get("capability") != PROJECT_STRUCTURE_EXPORT_CAPABILITY:
        raise ValueError("receipt project-structure-export capability is invalid")
    _required_sha256(receipt, "operation_key_sha256")
    marker_path = _required_text(receipt, "marker_path")
    changed_paths = result.get("changed_paths")
    if not isinstance(changed_paths, list) or changed_paths != [marker_path]:
        raise ValueError("receipt project-structure-export changed_paths are invalid")
    normalized = [
        _validated_postcondition_path(str(path), operation="project_structure_export")
        for path in changed_paths
    ]
    if normalized != [marker_path]:
        raise ValueError("receipt project-structure-export marker path is invalid")
    if result.get("remote_publication") is not False:
        raise ValueError("receipt project-structure-export cannot imply publication")
    if result.get("publisher_ownership_granted") is not False:
        raise ValueError("receipt project-structure-export cannot grant publisher ownership")


def _validate_project_memory_scope_result(result: Mapping[str, object]) -> None:
    allowed = {
        "contract",
        "operation",
        "operation_id",
        "request",
        "previous_scope",
        "current_scope",
        "previous_memory_revision",
        "current_memory_revision",
        "event",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt project-memory-scope result contains unsupported fields: "
            + ", ".join(unknown)
        )
    from p2p_engine.core.project_memory import (
        PROJECT_MEMORY_SCOPE_MUTATION_CONTRACT,
        project_memory_scope_from_mapping,
    )
    from p2p_engine.services.project_memory import _event_from_mapping

    if result.get("contract") != PROJECT_MEMORY_SCOPE_MUTATION_CONTRACT:
        raise ValueError("receipt project-memory-scope contract is unsupported")
    if result.get("operation") != "project_memory_scope_change":
        raise ValueError("receipt project-memory-scope operation is unsupported")
    if result.get("operation_id") != "project.memory.scope.set":
        raise ValueError("receipt project-memory-scope operation_id is invalid")
    request = result.get("request")
    if not isinstance(request, Mapping) or set(request) != {
        "proposal_id",
        "kind",
        "section_ids",
        "expected_memory_revision",
        "expected_structure_revision",
    }:
        raise ValueError("receipt project-memory-scope request is invalid")
    previous = project_memory_scope_from_mapping(result.get("previous_scope"))
    current = project_memory_scope_from_mapping(result.get("current_scope"))
    if current.object_id != previous.object_id or current.revision != previous.revision + 1:
        raise ValueError("receipt project-memory-scope revision must advance exactly once")
    if request.get("proposal_id") != current.object_id or request.get("kind") != current.kind.value:
        raise ValueError("receipt project-memory-scope request and result diverge")
    if request.get("section_ids") != list(current.section_ids):
        raise ValueError("receipt project-memory-scope section targets diverge")
    previous_memory = _required_sha256(result, "previous_memory_revision")
    current_memory = _required_sha256(result, "current_memory_revision")
    if request.get("expected_memory_revision") != previous_memory or previous_memory == current_memory:
        raise ValueError("receipt project-memory-scope memory revisions are invalid")
    expected_structure = request.get("expected_structure_revision")
    if (
        isinstance(expected_structure, bool)
        or not isinstance(expected_structure, int)
        or expected_structure < 1
        or current.structure_revision != expected_structure
    ):
        raise ValueError("receipt project-memory-scope structure revision is invalid")
    event = _event_from_mapping(result.get("event"))
    if event.scope_revision != current.revision or event.scope_sha256 != current.semantic_sha256:
        raise ValueError("receipt project-memory-scope event is inconsistent")
    prefix = f".p2p/proposals/{current.object_id}-"
    changed_paths = result.get("changed_paths")
    if (
        not isinstance(changed_paths, list)
        or len(changed_paths) != 2
        or changed_paths != sorted(changed_paths)
        or not all(str(path).startswith(prefix) for path in changed_paths)
        or {str(path).rsplit("/", 1)[-1] for path in changed_paths}
        != {"memory-scope.yml", "memory-scope-events.yml"}
    ):
        raise ValueError("receipt project-memory-scope changed paths are invalid")


def _validate_proposal_decision_result(result: Mapping[str, object]) -> None:
    allowed = {
        "operation",
        "status",
        "proposal_id",
        "event",
        "lifecycle",
        "changed_paths",
    }
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(
            "receipt proposal decision result contains unsupported fields: "
            + ", ".join(unknown)
        )
    if result.get("operation") != "proposal_decision_apply":
        raise ValueError("receipt proposal decision operation is unsupported")
    if result.get("status") != "applied":
        raise ValueError("receipt proposal decision status must be applied")
    proposal_id = _required_text(result, "proposal_id")
    if re.fullmatch(r"PROP-\d{3,}", proposal_id) is None:
        raise ValueError("receipt proposal decision proposal_id is invalid")
    event = result.get("event")
    lifecycle = result.get("lifecycle")
    if not isinstance(event, Mapping) or not isinstance(lifecycle, Mapping):
        raise ValueError("receipt proposal decision read models must be mappings")
    if event.get("proposal_id") != proposal_id:
        raise ValueError("receipt proposal decision event targets another proposal")
    event_id = _required_text(event, "event_id")
    if lifecycle.get("head_event_id") != event_id:
        raise ValueError("receipt proposal decision lifecycle head is inconsistent")
    authority = event.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("receipt proposal decision event authority is missing")
    from p2p_engine.services.authority import AuthorityContractCodec

    AuthorityContractCodec().evidence_from_mapping(authority)
    changed_paths = result.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        raise ValueError("receipt proposal decision changed_paths must be non-empty")
    normalized = [
        _validated_postcondition_path(str(path), operation="proposal_decision_apply")
        for path in changed_paths
    ]
    if normalized != sorted(set(normalized)):
        raise ValueError("receipt proposal decision changed_paths must be unique and sorted")


def _validate_bounded_receipt_sequence(value: object, *, field: str) -> None:
    if not isinstance(value, list) or len(value) > 128:
        raise ValueError(f"receipt readiness {field} must be a bounded sequence")
    for item in value:
        if not isinstance(item, str) or len(item.encode("utf-8")) > 2048:
            raise ValueError(f"receipt readiness {field} contains an invalid item")


def _validate_bounded_receipt_value(
    value: object,
    *,
    field: str,
    depth: int,
) -> None:
    if depth > 4:
        raise ValueError(f"receipt readiness {field} exceeds nesting limit")
    if isinstance(value, Mapping):
        if len(value) > 32:
            raise ValueError(f"receipt readiness {field} exceeds mapping limit")
        for key, item in value.items():
            if not isinstance(key, str) or len(key.encode("utf-8")) > 128:
                raise ValueError(f"receipt readiness {field} contains an invalid key")
            _validate_bounded_receipt_value(
                item,
                field=field,
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        if len(value) > 128:
            raise ValueError(f"receipt readiness {field} exceeds sequence limit")
        for item in value:
            _validate_bounded_receipt_value(
                item,
                field=field,
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        if len(value.encode("utf-8")) > 2048:
            raise ValueError(f"receipt readiness {field} contains oversized text")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise ValueError(f"receipt readiness {field} contains unsupported data")


def _public_result(result: Mapping[str, object]) -> dict[str, object]:
    if result.get("operation") == "init":
        return {
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "project": dict(result.get("project", {}))
            if isinstance(result.get("project"), Mapping)
            else {},
            "project_identity": dict(result.get("project_identity", {}))
            if isinstance(result.get("project_identity"), Mapping)
            else {},
            "authority": dict(result.get("authority", {}))
            if isinstance(result.get("authority"), Mapping)
            else {},
            "created_paths": list(result.get("created_paths", []))
            if isinstance(result.get("created_paths"), list)
            else [],
            "created_file_paths": list(result.get("created_file_paths", []))
            if isinstance(result.get("created_file_paths"), list)
            else [],
            "agent_selection": dict(result.get("agent_selection", {}))
            if isinstance(result.get("agent_selection"), Mapping)
            else {},
            "agent_instructions": dict(result.get("agent_instructions", {}))
            if isinstance(result.get("agent_instructions"), Mapping)
            else {},
            "vertical": dict(result.get("vertical", {}))
            if isinstance(result.get("vertical"), Mapping)
            else {},
            "warnings": list(result.get("warnings", []))
            if isinstance(result.get("warnings"), list)
            else [],
            "mcp_hint": dict(result.get("mcp_hint", {}))
            if isinstance(result.get("mcp_hint"), Mapping)
            else {},
            "next_steps": list(result.get("next_steps", []))
            if isinstance(result.get("next_steps"), list)
            else [],
        }
    if result.get("operation") in {
        "project_identity_adopt",
        "project_identity_derive",
    }:
        return {
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "kind": result.get("kind"),
            "previous_identity": (
                dict(result["previous_identity"])
                if isinstance(result.get("previous_identity"), Mapping)
                else None
            ),
            "current_identity": (
                dict(result["current_identity"])
                if isinstance(result.get("current_identity"), Mapping)
                else {}
            ),
            "source_revision": (
                dict(result["source_revision"])
                if isinstance(result.get("source_revision"), Mapping)
                else {}
            ),
            "changed_paths": list(result.get("changed_paths", []))
            if isinstance(result.get("changed_paths"), list)
            else [],
        }
    if result.get("operation") == "proposal_create":
        return {
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "proposal": dict(result.get("proposal", {}))
            if isinstance(result.get("proposal"), Mapping)
            else {},
            "created_paths": list(result.get("created_paths", []))
            if isinstance(result.get("created_paths"), list)
            else [],
            "next_steps": list(result.get("next_steps", []))
            if isinstance(result.get("next_steps"), list)
            else [],
        }
    if result.get("operation") == "proposal_contribution_add":
        return {
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "proposal_id": result.get("proposal_id"),
            "path": result.get("path"),
            "contribution": dict(result.get("contribution", {}))
            if isinstance(result.get("contribution"), Mapping)
            else {},
            "review_capability": dict(result.get("review_capability", {}))
            if isinstance(result.get("review_capability"), Mapping)
            else {},
        }
    if result.get("operation") == "proposal_update":
        return {
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "proposal_id": result.get("proposal_id"),
            "path": result.get("path"),
            "updated_sections": list(result.get("updated_sections", []))
            if isinstance(result.get("updated_sections"), list)
            else [],
        }
    if result.get("operation") == "proposal_readiness_assess":
        return {
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "proposal_id": result.get("proposal_id"),
            "path": result.get("path"),
            "readiness": dict(result.get("readiness", {}))
            if isinstance(result.get("readiness"), Mapping)
            else {},
        }
    if result.get("operation") == "project_authority_rotate":
        return {
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "previous_descriptor": dict(result.get("previous_descriptor", {}))
            if isinstance(result.get("previous_descriptor"), Mapping)
            else {},
            "new_descriptor": dict(result.get("new_descriptor", {}))
            if isinstance(result.get("new_descriptor"), Mapping)
            else {},
            "rotation_request": dict(result.get("rotation_request", {}))
            if isinstance(result.get("rotation_request"), Mapping)
            else {},
            "event_id": result.get("event_id"),
            "event_path": result.get("event_path"),
        }
    if result.get("operation") == "project_domain_change":
        return {
            "contract": result.get("contract"),
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "requested_operation": result.get("requested_operation"),
            "previous": dict(result.get("previous", {}))
            if isinstance(result.get("previous"), Mapping)
            else {},
            "current": dict(result.get("current", {}))
            if isinstance(result.get("current"), Mapping)
            else {},
            "project_memory_revision": result.get("project_memory_revision"),
        }
    if result.get("operation") == "project_memory_scope_change":
        return {
            "contract": result.get("contract"),
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "request": dict(result.get("request", {}))
            if isinstance(result.get("request"), Mapping)
            else {},
            "previous_scope": dict(result.get("previous_scope", {}))
            if isinstance(result.get("previous_scope"), Mapping)
            else {},
            "current_scope": dict(result.get("current_scope", {}))
            if isinstance(result.get("current_scope"), Mapping)
            else {},
            "previous_memory_revision": result.get("previous_memory_revision"),
            "current_memory_revision": result.get("current_memory_revision"),
            "event": dict(result.get("event", {}))
            if isinstance(result.get("event"), Mapping)
            else {},
        }
    if result.get("operation") == "project_structure_change":
        return {
            "contract": result.get("contract"),
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "requested_operation": result.get("requested_operation"),
            "expected_revision": result.get("expected_revision"),
            "previous_revision": result.get("previous_revision"),
            "previous_checksum": result.get("previous_checksum"),
            "current": dict(result.get("current", {}))
            if isinstance(result.get("current"), Mapping)
            else {},
            "event": dict(result.get("event", {}))
            if isinstance(result.get("event"), Mapping)
            else {},
        }
    if result.get("operation") == "project_structure_retirement":
        return {
            "contract": result.get("contract"),
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "request": dict(result.get("request", {}))
            if isinstance(result.get("request"), Mapping)
            else {},
            "resolved_targets": list(result.get("resolved_targets", []))
            if isinstance(result.get("resolved_targets"), list)
            else [],
            "previous_revision": result.get("previous_revision"),
            "previous_checksum": result.get("previous_checksum"),
            "current": dict(result.get("current", {}))
            if isinstance(result.get("current"), Mapping)
            else {},
            "previous_memory_revision": result.get("previous_memory_revision"),
            "current_memory_revision": result.get("current_memory_revision"),
            "event": dict(result.get("event", {}))
            if isinstance(result.get("event"), Mapping)
            else {},
            "applied_dispositions": list(result.get("applied_dispositions", []))
            if isinstance(result.get("applied_dispositions"), list)
            else [],
        }
    if result.get("operation") == "project_structure_replacement":
        return {
            "contract": result.get("contract"),
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "status": result.get("status"),
            "target": dict(result.get("target", {}))
            if isinstance(result.get("target"), Mapping)
            else {},
            "previous_revision": result.get("previous_revision"),
            "previous_checksum": result.get("previous_checksum"),
            "current": dict(result.get("current", {}))
            if isinstance(result.get("current"), Mapping)
            else {},
            "previous_memory_revision": result.get("previous_memory_revision"),
            "current_memory_revision": result.get("current_memory_revision"),
            "event": dict(result.get("event", {}))
            if isinstance(result.get("event"), Mapping)
            else {},
            "applied_dispositions": list(result.get("applied_dispositions", []))
            if isinstance(result.get("applied_dispositions"), list)
            else [],
            "readiness_identity": dict(result.get("readiness_identity", {}))
            if isinstance(result.get("readiness_identity"), Mapping)
            else {},
            "classification_identity": dict(result.get("classification_identity", {}))
            if isinstance(result.get("classification_identity"), Mapping)
            else {},
            "detached_copy": result.get("detached_copy"),
            "active_release_subscription": result.get("active_release_subscription"),
            "remote_publication": result.get("remote_publication"),
            "publisher_ownership_granted": result.get("publisher_ownership_granted"),
            "moderation_rights_granted": result.get("moderation_rights_granted"),
        }
    if result.get("operation") in {
        "project_structure_merge",
        "project_structure_restore",
    }:
        return {
            "contract": result.get("contract"),
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "status": result.get("status"),
            "source": dict(result.get("source", {}))
            if isinstance(result.get("source"), Mapping)
            else {},
            "previous": dict(result.get("previous", {}))
            if isinstance(result.get("previous"), Mapping)
            else {},
            "current": dict(result.get("current", {}))
            if isinstance(result.get("current"), Mapping)
            else {},
            "previous_memory_revision": result.get("previous_memory_revision"),
            "current_memory_revision": result.get("current_memory_revision"),
            "event": dict(result.get("event", {}))
            if isinstance(result.get("event"), Mapping)
            else {},
            "changed_entities": list(result.get("changed_entities", []))
            if isinstance(result.get("changed_entities"), list)
            else [],
            "detached_copy": result.get("detached_copy"),
            "active_release_subscription": result.get("active_release_subscription"),
            "second_authority_created": result.get("second_authority_created"),
        }
    if result.get("operation") == "project_structure_export":
        return {
            "contract": result.get("contract"),
            "operation": result.get("operation"),
            "operation_id": result.get("operation_id"),
            "status": result.get("status"),
            "source": dict(result.get("source", {}))
            if isinstance(result.get("source"), Mapping)
            else {},
            "lineage": dict(result.get("lineage", {}))
            if isinstance(result.get("lineage"), Mapping)
            else {},
            "domain_metadata": dict(result.get("domain_metadata", {}))
            if isinstance(result.get("domain_metadata"), Mapping)
            else {},
            "draft": dict(result.get("draft", {}))
            if isinstance(result.get("draft"), Mapping)
            else {},
            "package": dict(result.get("package", {}))
            if isinstance(result.get("package"), Mapping)
            else {},
            "receipt": dict(result.get("receipt", {}))
            if isinstance(result.get("receipt"), Mapping)
            else {},
            "remote_publication": result.get("remote_publication"),
            "publisher_ownership_granted": result.get("publisher_ownership_granted"),
        }
    if result.get("operation") == "proposal_decision_apply":
        return {
            "operation": result.get("operation"),
            "status": result.get("status"),
            "proposal_id": result.get("proposal_id"),
            "event": dict(result.get("event", {}))
            if isinstance(result.get("event"), Mapping)
            else {},
            "lifecycle": dict(result.get("lifecycle", {}))
            if isinstance(result.get("lifecycle"), Mapping)
            else {},
        }
    return {
        "impact_contract": result.get("impact_contract"),
        "operation": result.get("operation"),
        "operation_id": result.get("operation_id"),
        "coordinate": result.get("coordinate"),
        "analysis_fingerprint_sha256": result.get("analysis_fingerprint_sha256"),
        "plan_fingerprint_sha256": result.get("plan_fingerprint_sha256"),
        "semantic_postconditions": dict(result.get("semantic_postconditions", {}))
        if isinstance(result.get("semantic_postconditions"), Mapping)
        else {},
        "decision_summary": list(result.get("decision_summary", []))
        if isinstance(result.get("decision_summary"), list)
        else [],
    }


def _validated_postcondition_path(value: str, *, operation: str) -> str:
    pure = PurePosixPath(value.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe receipt postcondition path: {value}")
    normalized = pure.as_posix()
    if operation == "init" and _is_init_postcondition_path(normalized):
        return normalized
    if (
        operation == "project_identity_adopt"
        and normalized.startswith(".p2p/.internal/identity-adoption-backups/")
        and normalized.endswith("/project.yml")
    ):
        return normalized
    if (
        operation == "project_structure_export"
        and normalized.startswith(".p2p/.internal/project-structure-exports/")
        and normalized.endswith(".yml")
    ):
        return normalized
    if not normalized.startswith(".p2p/") or normalized.startswith(".p2p/.internal/"):
        raise ValueError(f"receipt postcondition path is not canonical project state: {value}")
    return normalized


def _is_init_postcondition_path(value: str) -> bool:
    return (
        (value.startswith(".p2p/") and not value.startswith(".p2p/.internal/"))
        or value.startswith(".agents/")
        or value
        in {
            ".cursor/rules/p2p.mdc",
            ".github/copilot-instructions.md",
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "P2P-SETUP.md",
        }
    )


def _required_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"receipt field {field} must be non-empty text")
    return value


def _required_sha256(payload: Mapping[str, object], field: str) -> str:
    value = _required_text(payload, field)
    _require_sha256(value, field)
    return value


def _require_sha256(value: str, field: str) -> None:
    if _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

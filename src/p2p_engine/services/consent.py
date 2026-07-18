from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from p2p_engine.foundation.files import (
    read_yaml_mapping_or_default as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.services.permissions import PermissionsService

CONSENT_OPERATIONS = {
    "proposal_decision_apply",
    "proposal_accept",
    "proposal_reject",
    "proposal_defer",
    "proposal_publish",
    "proposal_request_review",
    "proposal_retire_branch",
    "proposal_accept_branch",
    "proposal_reject_branch",
    "proposal_merge",
    "proposal_finalize",
    "proposal_cleanup",
    "sync_pull",
    "sync_push",
    "work_publish",
    "work_request_review",
    "work_accept",
    "work_finalize",
    "work_cleanup",
}


@dataclass(frozen=True)
class ConsentReceipt:
    consent_id: str
    operation: str
    target: str
    actor_id: str
    approved_by: str
    status: str
    single_use: bool
    expires_on: str | None
    path: Path


class ConsentService:
    def __init__(self, *, root: Path, p2p_dir: Path, permissions: PermissionsService) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.permissions = permissions

    def path(self, consent_id: str) -> Path:
        consent_id = self.normalize_consent_id(consent_id)
        return self.p2p_dir / "consents" / consent_id / "consent.yml"

    def next_consent_id(self) -> str:
        consents_dir = self.p2p_dir / "consents"
        used: set[int] = set()
        if consents_dir.exists():
            for path in consents_dir.iterdir():
                if not path.is_dir():
                    continue
                match = re.match(r"^CONSENT-(\d{3})$", path.name)
                if match:
                    used.add(int(match.group(1)))
        return f"CONSENT-{max(used or {0}) + 1:03d}"

    def grant(
        self,
        operation: str,
        target: str,
        actor_id: str,
        approved_by: str = "owner",
        *,
        expires_on: str | None = None,
        single_use: bool = True,
        scope: str | None = None,
    ) -> ConsentReceipt:
        operation = self.normalize_operation(operation)
        target = target.strip()
        if not target:
            raise ValueError("Consent target is required")
        actor_slug = self.permissions.identity_slug(actor_id)
        approved_by_slug = self.permissions.identity_slug(approved_by)
        identities = self._identities()
        if actor_slug not in identities:
            raise ValueError(f"Unknown consent actor: {actor_slug}. Add it with `p2p permissions actor add`.")
        if approved_by_slug not in identities:
            raise ValueError(f"Unknown consent approver: {approved_by_slug}. Add it with `p2p permissions actor add`.")
        approver = identities[approved_by_slug]
        if not isinstance(approver, dict) or str(approver.get("role") or "") != "owner":
            raise ValueError("Only an owner identity can approve consent receipts in the MVP")

        consent_id = self.next_consent_id()
        receipt = self._receipt_payload(
            consent_id=consent_id,
            status="granted",
            operation=operation,
            target=target,
            actor_slug=actor_slug,
            requested_by=actor_slug,
            approved_by=approved_by_slug,
            scope=scope,
            single_use=single_use,
            expires_on=expires_on,
        )
        path = self._write_new_receipt(consent_id, receipt)
        return self.receipt_from_payload(receipt, path.relative_to(self.root))

    def request(
        self,
        operation: str,
        target: str,
        actor_id: str,
        *,
        requested_by: str | None = None,
        scope: str | None = None,
        expires_on: str | None = None,
    ) -> ConsentReceipt:
        operation = self.normalize_operation(operation)
        target = target.strip()
        if not target:
            raise ValueError("Consent target is required")
        actor_slug = self.permissions.identity_slug(actor_id)
        requested_by_slug = self.permissions.identity_slug(requested_by or actor_id)
        identities = self._identities()
        if actor_slug not in identities:
            raise ValueError(f"Unknown consent actor: {actor_slug}. Add it with `p2p permissions actor add`.")

        consent_id = self.next_consent_id()
        receipt = self._receipt_payload(
            consent_id=consent_id,
            status="requested",
            operation=operation,
            target=target,
            actor_slug=actor_slug,
            requested_by=requested_by_slug,
            approved_by=None,
            scope=scope,
            single_use=True,
            expires_on=expires_on,
        )
        path = self._write_new_receipt(consent_id, receipt)
        return self.receipt_from_payload(receipt, path.relative_to(self.root))

    def show(self, consent_id: str) -> ConsentReceipt:
        path = self.path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        return self.receipt_from_payload(payload, path.relative_to(self.root))

    def statuses(self) -> list[ConsentReceipt]:
        consents_dir = self.p2p_dir / "consents"
        if not consents_dir.exists():
            return []
        receipts: list[ConsentReceipt] = []
        for path in sorted(consents_dir.glob("CONSENT-*/consent.yml")):
            receipts.append(self.receipt_from_payload(_read_yaml_mapping(path, default={}), path.relative_to(self.root)))
        return receipts

    def revoke(self, consent_id: str, reason: str = "") -> ConsentReceipt:
        path = self.path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        if str(payload.get("status") or "") == "consumed":
            raise ValueError(f"Cannot revoke consumed consent receipt: {consent_id}")
        payload["status"] = "revoked"
        payload["revoked_at"] = date.today().isoformat()
        payload["revocation_reason"] = reason or "Not provided."
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return self.receipt_from_payload(payload, path.relative_to(self.root))

    def validate(
        self,
        consent_id: str,
        *,
        operation: str,
        target: str,
        actor_id: str,
    ) -> ConsentReceipt:
        path = self.path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        expected_operation = self.normalize_operation(operation)
        expected_actor = self.permissions.identity_slug(actor_id)
        if str(payload.get("status") or "") != "granted":
            raise ValueError(f"Consent receipt is not granted: {consent_id}")
        if str(payload.get("operation") or "") != expected_operation:
            raise ValueError(
                f"Consent receipt operation mismatch: expected {expected_operation}, got {payload.get('operation')}"
            )
        if str(payload.get("target") or "") != target:
            raise ValueError(f"Consent receipt target mismatch: expected {target}, got {payload.get('target')}")
        if str(payload.get("actor_id") or "") != expected_actor:
            raise ValueError(
                f"Consent receipt actor mismatch: expected {expected_actor}, got {payload.get('actor_id')}"
            )
        expires_on = payload.get("expires_on")
        if expires_on:
            try:
                expiry = date.fromisoformat(str(expires_on))
            except ValueError as exc:
                raise ValueError(f"Invalid consent expiry date: {expires_on}") from exc
            if expiry < date.today():
                payload["status"] = "expired"
                path.write_text(_yaml_dump(payload), encoding="utf-8")
                raise ValueError(f"Consent receipt expired: {consent_id}")
        return self.receipt_from_payload(payload, path.relative_to(self.root))

    def consume(self, consent_id: str, *, result: dict[str, object]) -> ConsentReceipt:
        path = self.path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        if str(payload.get("status") or "") != "granted":
            raise ValueError(f"Consent receipt is not granted: {consent_id}")
        payload["status"] = "consumed"
        payload["consumed_at"] = date.today().isoformat()
        payload["result"] = result
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return self.receipt_from_payload(payload, path.relative_to(self.root))

    def mark_used_with_error(
        self,
        consent_id: str,
        *,
        error: str,
        result: dict[str, object] | None = None,
    ) -> ConsentReceipt:
        path = self.path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        if str(payload.get("status") or "") != "granted":
            return self.receipt_from_payload(payload, path.relative_to(self.root))
        payload["status"] = "used_with_error"
        payload["consumed_at"] = date.today().isoformat()
        payload["result"] = result or {}
        payload["error"] = error
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return self.receipt_from_payload(payload, path.relative_to(self.root))

    def normalize_operation(self, operation: str) -> str:
        operation = str(operation or "").strip().lower().replace("-", "_")
        if operation not in CONSENT_OPERATIONS:
            allowed = ", ".join(sorted(CONSENT_OPERATIONS))
            raise ValueError(f"Invalid consent operation: {operation}. Allowed: {allowed}")
        return operation

    def normalize_consent_id(self, consent_id: str) -> str:
        consent_id = str(consent_id or "").strip().upper()
        if not re.match(r"^CONSENT-\d{3}$", consent_id):
            raise ValueError(f"Invalid consent ID: {consent_id}")
        return consent_id

    def receipt_from_payload(self, payload: dict[str, object], path: Path) -> ConsentReceipt:
        return ConsentReceipt(
            consent_id=str(payload.get("consent_id") or ""),
            operation=str(payload.get("operation") or ""),
            target=str(payload.get("target") or ""),
            actor_id=str(payload.get("actor_id") or ""),
            approved_by=str(payload.get("approved_by") or ""),
            status=str(payload.get("status") or "unknown"),
            single_use=bool(payload.get("single_use")),
            expires_on=str(payload.get("expires_on")) if payload.get("expires_on") else None,
            path=path,
        )

    def _identities(self) -> dict[str, object]:
        permissions = self.permissions.show()
        identities = permissions.get("identities", {})
        if not isinstance(identities, dict):
            raise ValueError("Invalid permissions policy: identities must be a mapping")
        return identities

    def _receipt_payload(
        self,
        *,
        consent_id: str,
        status: str,
        operation: str,
        target: str,
        actor_slug: str,
        requested_by: str,
        approved_by: str | None,
        scope: str | None,
        single_use: bool,
        expires_on: str | None,
    ) -> dict[str, object]:
        return {
            "consent_id": consent_id,
            "status": status,
            "operation": operation,
            "target": target,
            "actor_id": actor_slug,
            "requested_by": requested_by,
            "approved_by": approved_by,
            "scope": scope or "single_target",
            "single_use": bool(single_use),
            "expires_on": expires_on,
            "created_at": date.today().isoformat(),
            "consumed_at": None,
            "revoked_at": None,
            "result": None,
            "provider": None,
        }

    def _write_new_receipt(self, consent_id: str, payload: dict[str, object]) -> Path:
        receipt_dir = self.p2p_dir / "consents" / consent_id
        receipt_dir.mkdir(parents=True, exist_ok=False)
        path = receipt_dir / "consent.yml"
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return path

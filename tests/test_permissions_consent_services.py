from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

from p2p_engine.services.consent import ConsentService
from p2p_engine.services.permissions import PermissionsService


def _services(root: Path) -> tuple[PermissionsService, ConsentService]:
    p2p_dir = root / ".p2p"
    permissions = PermissionsService(root=root, p2p_dir=p2p_dir)
    permissions.write_policy(permissions.default_policy_payload(owner_name="matteo"))
    consent = ConsentService(root=root, p2p_dir=p2p_dir, permissions=permissions)
    return permissions, consent


def test_permissions_service_default_payload_and_actor_add(tmp_path: Path) -> None:
    permissions = PermissionsService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    payload = permissions.default_policy_payload(owner_name="Matteo Rossi")

    assert payload["permissions"]["model"] == "role_plus_consent_receipt"
    assert payload["permissions"]["enforcement_scope"] == "project_state_authority"
    assert payload["identities"]["matteo-rossi"]["role"] == "owner"
    assert payload["identities"]["matteo-rossi"]["display_name"] == "Matteo Rossi"
    assert payload["identities"]["contributor"]["role"] == "contributor"

    permissions.write_policy(payload)
    actor = permissions.actor_add("Lorenzo Bianchi", role="maintainer", kind="person")

    assert actor.actor_id == "lorenzo-bianchi"
    assert actor.role == "maintainer"
    assert actor.kind == "person"
    assert actor.display_name == "Lorenzo Bianchi"
    assert actor.path == Path(".p2p/project/permissions.yml")

    stored = yaml.safe_load((tmp_path / ".p2p" / "project" / "permissions.yml").read_text(encoding="utf-8"))
    assert stored["identities"]["lorenzo-bianchi"]["role"] == "maintainer"
    assert permissions.show()["identities"]["matteo-rossi"]["role"] == "owner"


def test_permissions_service_normalization_and_invalid_policy(tmp_path: Path) -> None:
    permissions = PermissionsService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    assert permissions.identity_slug("  Matteo Rossi  ") == "matteo-rossi"
    assert permissions.normalize_role("OWNER") == "owner"
    assert permissions.normalize_actor_kind("AGENT") == "agent"

    with pytest.raises(ValueError, match="Actor identity is required"):
        permissions.identity_slug("")
    with pytest.raises(ValueError, match="Invalid permission role"):
        permissions.normalize_role("superuser")
    with pytest.raises(ValueError, match="Invalid actor kind"):
        permissions.normalize_actor_kind("robot")

    permissions.write_policy({"identities": []})

    with pytest.raises(ValueError, match="Invalid permissions policy: identities must be a non-empty mapping"):
        permissions.actor_add("lorenzo")


def test_permissions_require_current_authority_file(tmp_path: Path) -> None:
    permissions = PermissionsService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    with pytest.raises(ValueError, match="P2P355_PERMISSIONS_REQUIRED"):
        permissions.show()


def test_permission_policy_requires_exactly_one_owner_when_requested(tmp_path: Path) -> None:
    permissions = PermissionsService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    duplicate = permissions.default_policy_payload(owner_name="Davide")
    duplicate["identities"]["other"] = {
        "role": "owner",
        "kind": "person",
        "display_name": "Other",
    }
    with pytest.raises(ValueError, match="exactly one owner"):
        permissions.validate_policy_payload(duplicate, require_single_owner=True)


def test_consent_service_grant_request_status_revoke_and_consume(tmp_path: Path) -> None:
    permissions, consent = _services(tmp_path)
    permissions.actor_add("lorenzo", role="contributor")

    granted = consent.grant("proposal-decision-apply", "PROP-001", "lorenzo", approved_by="matteo")
    requested = consent.request("proposal_decision_apply", "PROP-002", "lorenzo", requested_by="lorenzo")

    assert granted.consent_id == "CONSENT-001"
    assert granted.operation == "proposal_decision_apply"
    assert granted.status == "granted"
    assert requested.consent_id == "CONSENT-002"
    assert requested.status == "requested"

    statuses = consent.statuses()
    assert [item.consent_id for item in statuses] == ["CONSENT-001", "CONSENT-002"]

    validated = consent.validate(
        "CONSENT-001",
        operation="proposal_decision_apply",
        target="PROP-001",
        actor_id="lorenzo",
    )
    assert validated.status == "granted"

    consumed = consent.consume("CONSENT-001", result={"outcome": "accepted"})
    assert consumed.status == "consumed"

    receipt = yaml.safe_load((tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml").read_text(encoding="utf-8"))
    assert receipt["result"]["outcome"] == "accepted"

    revoked = consent.revoke("CONSENT-002", reason="No longer needed.")
    assert revoked.status == "revoked"


def test_consent_service_rejects_requested_and_mismatched_receipts_without_consuming(tmp_path: Path) -> None:
    permissions, consent = _services(tmp_path)
    permissions.actor_add("lorenzo", role="contributor")
    permissions.actor_add("giulia", role="contributor")
    consent.request("proposal_decision_apply", "PROP-001", "lorenzo")
    consent.grant("proposal_decision_apply", "PROP-002", "lorenzo", approved_by="matteo")

    with pytest.raises(ValueError, match="Consent receipt is not granted"):
        consent.validate("CONSENT-001", operation="proposal_decision_apply", target="PROP-001", actor_id="lorenzo")

    with pytest.raises(ValueError, match="Consent receipt actor mismatch"):
        consent.validate("CONSENT-002", operation="proposal_decision_apply", target="PROP-002", actor_id="giulia")

    assert consent.show("CONSENT-002").status == "granted"

    with pytest.raises(ValueError, match="Consent receipt operation mismatch"):
        consent.validate("CONSENT-002", operation="project_domain_set", target="PROP-002", actor_id="lorenzo")

    with pytest.raises(ValueError, match="Consent receipt target mismatch"):
        consent.validate("CONSENT-002", operation="proposal_decision_apply", target="PROP-999", actor_id="lorenzo")


def test_consent_service_expiry_consumed_revoked_and_used_with_error_guards(tmp_path: Path) -> None:
    permissions, consent = _services(tmp_path)
    permissions.actor_add("lorenzo", role="contributor")
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    consent.grant("proposal_decision_apply", "PROP-001", "lorenzo", approved_by="matteo", expires_on=yesterday)
    with pytest.raises(ValueError, match="Consent receipt expired"):
        consent.validate("CONSENT-001", operation="proposal_decision_apply", target="PROP-001", actor_id="lorenzo")
    assert consent.show("CONSENT-001").status == "expired"

    consent.grant("proposal_decision_apply", "PROP-002", "lorenzo", approved_by="matteo")
    consent.consume("CONSENT-002", result={"ok": True})
    with pytest.raises(ValueError, match="Consent receipt is not granted"):
        consent.validate("CONSENT-002", operation="proposal_decision_apply", target="PROP-002", actor_id="lorenzo")
    with pytest.raises(ValueError, match="Consent receipt is not granted"):
        consent.consume("CONSENT-002", result={"ok": True})
    with pytest.raises(ValueError, match="Cannot revoke consumed consent receipt"):
        consent.revoke("CONSENT-002")

    consent.grant("proposal_decision_apply", "PROP-003", "lorenzo", approved_by="matteo")
    consent.revoke("CONSENT-003")
    with pytest.raises(ValueError, match="Consent receipt is not granted"):
        consent.validate("CONSENT-003", operation="proposal_decision_apply", target="PROP-003", actor_id="lorenzo")

    consent.grant("proposal_decision_apply", "PROP-004", "lorenzo", approved_by="matteo")
    errored = consent.mark_used_with_error("CONSENT-004", error="head changed", result={"step": "audit"})
    assert errored.status == "used_with_error"
    with pytest.raises(ValueError, match="Consent receipt is not granted"):
        consent.validate("CONSENT-004", operation="proposal_decision_apply", target="PROP-004", actor_id="lorenzo")

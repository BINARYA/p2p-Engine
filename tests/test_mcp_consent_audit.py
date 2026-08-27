from __future__ import annotations

from p2p_engine.mcp.consent_audit import consume_consent_with_audit


class FakeWorkspace:
    def __init__(self) -> None:
        self.consumed: list[tuple[str, dict[str, object]]] = []

    def consent_consume(
        self,
        consent_id: str,
        *,
        result: dict[str, object],
    ) -> dict[str, object]:
        self.consumed.append((consent_id, result))
        return {"consent_id": consent_id, "status": "consumed", "result": result}


def test_consume_consent_with_audit_persists_receipt_without_external_coupling() -> None:
    workspace = FakeWorkspace()

    consumed = consume_consent_with_audit(  # type: ignore[arg-type]
        workspace,
        "CONSENT-001",
        result={"operation": "proposal_decision_apply", "status": "applied"},
    )

    assert consumed == {
        "consent_id": "CONSENT-001",
        "status": "consumed",
        "result": {"operation": "proposal_decision_apply", "status": "applied"},
    }
    assert workspace.consumed == [
        (
            "CONSENT-001",
            {"operation": "proposal_decision_apply", "status": "applied"},
        )
    ]

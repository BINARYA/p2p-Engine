from __future__ import annotations

from p2p_engine.services.project_application import ProjectApplicationService as P2PWorkspace


def consume_consent_with_audit(
    workspace: P2PWorkspace,
    consent_id: str,
    *,
    result: dict[str, object],
) -> object:
    """Persist consent consumption through the project-state receipt service."""

    return workspace.consent_consume(consent_id, result=result)

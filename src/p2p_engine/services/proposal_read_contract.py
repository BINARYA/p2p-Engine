from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from p2p_engine.core.contribution import allowed_contribution_type_values
from p2p_engine.services.proposal_review_view import ProposalFullView
from p2p_engine.services.workspace_status import ProposalSummary


ProposalListPayload = dict[str, object]
ProposalDetailPayload = dict[str, object]


class ProposalReadContractService:
    def __init__(
        self,
        *,
        proposal_summaries: Callable[..., list[ProposalSummary]],
        proposal_full_view: Callable[[str], ProposalFullView],
    ) -> None:
        self.proposal_summaries = proposal_summaries
        self.proposal_full_view = proposal_full_view

    def list_proposals(
        self,
        *,
        status: str | None = None,
        decision_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProposalListPayload:
        _validate_page(limit=limit, offset=offset)
        all_proposals = sorted(
            self.proposal_summaries(status=None),
            key=lambda item: item.proposal_id,
        )
        filtered = [
            proposal
            for proposal in all_proposals
            if (status is None or proposal.status == status)
            and (
                decision_state is None
                or proposal.effective_state == decision_state
            )
        ]
        page = _page(filtered, limit=limit, offset=offset)
        return {
            "contract_version": "p2p-proposal-list/v1",
            "filters": {
                "status": status,
                "decision_state": decision_state,
            },
            "counts": {
                "unfiltered": _proposal_counts(all_proposals),
                "filtered": _proposal_counts(filtered),
            },
            **page,
            "items": [_proposal_summary_payload(item) for item in page["items"]],
        }

    def proposal_detail(
        self,
        proposal_id: str,
        *,
        contribution_limit: int = 50,
    ) -> ProposalDetailPayload:
        _validate_page(limit=contribution_limit, offset=0)
        view = self.proposal_full_view(proposal_id)
        all_contributions = list(view.contributions.contributions)
        contribution_page = _page(all_contributions, limit=contribution_limit, offset=0)
        contribution_counts = Counter(
            contribution.contribution_type.value
            for contribution in all_contributions
        )
        return {
            "contract_version": "p2p-proposal-detail/v1",
            "proposal_id": view.proposal_id,
            "title": view.title,
            "status": view.status,
            "path": view.path,
            "lifecycle": {
                "effective_state": view.effective_state,
                "head_event_type": view.head_event_type,
                "head_event_id": view.head_event_id,
                "event_count": view.event_count,
                "authority_resolution": view.authority_resolution,
                "ever_active": view.ever_active,
                "active": view.active,
                "proposal_binding_status": view.proposal_binding_status,
                "decision_semantic_sha256": view.decision_semantic_sha256,
            },
            "core_sections": view.core_sections,
            "decision": view.decision,
            "readiness": _readiness_payload(view.readiness),
            "artifact_state": _artifact_state_payload(view.artifact_status),
            "contributions": {
                "counts_by_type": {
                    key: contribution_counts.get(key, 0)
                    for key in allowed_contribution_type_values()
                },
                **contribution_page,
                "items": [
                    _contribution_payload(item)
                    for item in contribution_page["items"]
                ],
                "groups": _contribution_groups(
                    all_contributions,
                    limit=contribution_limit,
                ),
            },
            "questions": {
                "proposal_id": view.questions.proposal_id,
                "status": view.questions.status,
                "path": view.questions.path,
                "owner_questions": _collection(
                    view.questions.owner_questions,
                    item_mapper=_payload,
                ),
                "analytical_open_questions": _collection(
                    view.questions.analytical_open_questions,
                    item_mapper=_contribution_payload,
                ),
                "narrative_question_artifacts": _collection(
                    view.questions.narrative_question_artifacts,
                    item_mapper=_artifact_payload,
                ),
            },
            "narrative_artifacts": _collection(
                view.narrative_artifacts,
                item_mapper=_artifact_payload,
            ),
            "next_actions": list(view.next_actions),
            "limits": {
                "contribution_limit": contribution_limit,
            },
        }


def _validate_page(*, limit: int, offset: int) -> None:
    if limit < 1 or limit > 100:
        raise ValueError("P2P_INVALID_LIMIT: limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("P2P_INVALID_OFFSET: offset must be zero or greater")


def _page(items: list[Any], *, limit: int, offset: int) -> dict[str, object]:
    returned = items[offset : offset + limit]
    next_offset = offset + limit if offset + limit < len(items) else None
    return {
        "total": len(items),
        "returned": len(returned),
        "truncated": next_offset is not None,
        "offset": offset,
        "next_offset": next_offset,
        "items": returned,
    }


def _collection(
    items: list[Any],
    *,
    item_mapper: Callable[[Any], object],
) -> dict[str, object]:
    return {
        "total": len(items),
        "returned": len(items),
        "truncated": False,
        "items": [item_mapper(item) for item in items],
    }


def _proposal_counts(proposals: list[ProposalSummary]) -> dict[str, object]:
    return {
        "by_status": dict(
            sorted(Counter(item.status for item in proposals).items())
        ),
        "by_effective_state": dict(
            sorted(Counter(item.effective_state for item in proposals).items())
        ),
    }


def _proposal_summary_payload(proposal: ProposalSummary) -> dict[str, object]:
    return {
        "proposal_id": proposal.proposal_id,
        "slug": proposal.slug,
        "title": proposal.title,
        "status": proposal.status,
        "decision_state": proposal.effective_state,
        "effective_state": proposal.effective_state,
        "head_event_type": proposal.head_event_type,
        "head_event_id": proposal.head_event_id,
        "event_count": proposal.event_count,
        "authority_resolution": proposal.authority_resolution,
        "ever_active": proposal.ever_active,
        "active": proposal.active,
        "proposal_binding_status": proposal.proposal_binding_status,
        "decision_semantic_sha256": proposal.decision_semantic_sha256,
    }


def _readiness_payload(readiness: object) -> dict[str, object]:
    return {
        "proposal_id": str(getattr(readiness, "proposal_id", "")),
        "status": str(getattr(readiness, "status", "")),
        "path": getattr(readiness, "path", None),
        "profile_id": getattr(readiness, "profile_id", None),
        "profile_version": getattr(readiness, "profile_version", None),
        "computed_score": getattr(readiness, "computed_score", None),
        "computed_label": getattr(readiness, "computed_label", None),
        "confidence": getattr(readiness, "confidence", None),
        "failed_gates": list(getattr(readiness, "failed_gates", ()) or ()),
        "missing": list(getattr(readiness, "missing", ()) or ()),
        "suggested_next": list(getattr(readiness, "suggested_next", ()) or ()),
        "owner_question_state": _payload(
            getattr(readiness, "owner_question_state", {}) or {}
        ),
    }


def _artifact_state_payload(artifacts: list[object]) -> dict[str, object]:
    counts = Counter(str(getattr(item, "status", "unknown")) for item in artifacts)
    return {
        "total": len(artifacts),
        "counts_by_status": dict(sorted(counts.items())),
        "items": [_artifact_payload(item) for item in artifacts],
    }


def _artifact_payload(artifact: object) -> dict[str, object]:
    return {
        "key": str(getattr(artifact, "key", "")),
        "label": str(getattr(artifact, "label", "")),
        "filename": str(getattr(artifact, "filename", "")),
        "expectation": _payload(getattr(artifact, "expectation", "")),
        "status": _payload(getattr(artifact, "status", "")),
        "materialization_kind": str(
            getattr(artifact, "materialization_kind", "")
        ),
        "source_hint": str(getattr(artifact, "source_hint", "")),
        "provenance_confidence": str(
            getattr(artifact, "provenance_confidence", "")
        ),
        "path": getattr(artifact, "path", None),
        "summary": str(getattr(artifact, "summary", "")),
        "next_action": str(getattr(artifact, "next_action", "")),
    }


def _contribution_payload(contribution: object) -> dict[str, object]:
    contribution_type = getattr(contribution, "contribution_type", "")
    return {
        "contribution_id": str(getattr(contribution, "contribution_id", "")),
        "type": _payload(contribution_type),
        "author": str(getattr(contribution, "author", "")),
        "relevance_hint": str(getattr(contribution, "relevance_hint", "")),
        "text": str(getattr(contribution, "text", "")),
    }


def _contribution_groups(
    contributions: list[object],
    *,
    limit: int,
) -> dict[str, object]:
    grouped: dict[str, list[object]] = {
        key: [] for key in allowed_contribution_type_values()
    }
    for contribution in contributions:
        key = str(_payload(getattr(contribution, "contribution_type", "")))
        grouped.setdefault(key, []).append(contribution)
    return {
        key: {
            **_page(items, limit=limit, offset=0),
            "items": [_contribution_payload(item) for item in items[:limit]],
        }
        for key, items in grouped.items()
    }


def _payload(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _payload(value.to_dict())
    if is_dataclass(value):
        return _payload(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_payload(item) for item in value]
    return value

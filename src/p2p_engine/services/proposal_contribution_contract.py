from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

from p2p_engine.core.contribution import (
    Contribution,
    ContributionType,
    allowed_contribution_type_values,
)
from p2p_engine.services.proposals import ProposalContributionList


ProposalContributionListPayload = dict[str, object]

CONTRIBUTION_REVIEW_CAPABILITY = {
    "supported": False,
    "code": "P2P_CONTRIBUTION_REVIEW_UNSUPPORTED",
    "message": (
        "Contribution review/promote/reject state is not modeled in "
        "p2p-engine 0.4.11. Consumers must not store shadow project-memory "
        "review state outside .p2p."
    ),
}


class ProposalContributionContractService:
    def __init__(
        self,
        *,
        list_contributions: Callable[[str], ProposalContributionList],
    ) -> None:
        self.list_contributions = list_contributions

    def list_payload(
        self,
        proposal_id: str,
        *,
        contribution_type: ContributionType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProposalContributionListPayload:
        _validate_page(limit=limit, offset=offset)
        contribution_list = self.list_contributions(proposal_id)
        all_items = list(contribution_list.contributions)
        filtered = [
            item
            for item in all_items
            if contribution_type is None or item.contribution_type == contribution_type
        ]
        page = _page(filtered, limit=limit, offset=offset)
        return {
            "contract_version": "p2p-proposal-contribution-list/v1",
            "proposal_id": proposal_id,
            "path": contribution_list.path,
            "filters": {
                "type": contribution_type.value if contribution_type is not None else None,
            },
            "counts": {
                "unfiltered_by_type": _counts_by_type(all_items),
                "filtered_by_type": _counts_by_type(filtered),
            },
            **page,
            "items": [_contribution_payload(item) for item in page["items"]],
            "review_capability": dict(CONTRIBUTION_REVIEW_CAPABILITY),
        }


def contribution_payload(contribution: Contribution) -> dict[str, object]:
    return _contribution_payload(contribution)


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


def _counts_by_type(contributions: list[Contribution]) -> dict[str, int]:
    counts = Counter(item.contribution_type.value for item in contributions)
    return {
        key: counts.get(key, 0)
        for key in allowed_contribution_type_values()
    }


def _contribution_payload(contribution: Contribution) -> dict[str, object]:
    return {
        "contribution_id": contribution.contribution_id,
        "type": contribution.contribution_type.value,
        "author": contribution.author,
        "relevance_hint": contribution.relevance_hint,
        "text": contribution.text,
    }

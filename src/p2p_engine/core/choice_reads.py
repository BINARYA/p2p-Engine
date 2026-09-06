from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

CHOICE_LIST_CONTRACT = "p2p-choice-list/v1"
CHOICE_DETAIL_CONTRACT = "p2p-choice-detail/v1"
CHOICE_READ_DEFAULT_LIMIT = 50
CHOICE_READ_MAX_LIMIT = 100


def validate_choice_read_page(*, limit: int, offset: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("P2P_CHOICE_READ_LIMIT_INVALID: limit must be an integer")
    if not 1 <= limit <= CHOICE_READ_MAX_LIMIT:
        raise ValueError(
            f"P2P_CHOICE_READ_LIMIT_INVALID: limit must be between 1 and {CHOICE_READ_MAX_LIMIT}"
        )
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("P2P_CHOICE_READ_OFFSET_INVALID: offset must be a non-negative integer")


@dataclass(frozen=True)
class ChoiceSelectionRead:
    option_id: str
    title: str | None

    def to_dict(self) -> dict[str, object]:
        return {"id": self.option_id, "title": self.title}


@dataclass(frozen=True)
class ChoiceSummaryRead:
    choice_id: str
    title: str
    state: str
    terminal: bool
    definition_contract: str
    definition_completeness: str
    definition_digest: str | None
    seal_status: str
    integrity_status: str
    selected_option: ChoiceSelectionRead | None
    replacement_choice_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "choice_id": self.choice_id,
            "title": self.title,
            "state": self.state,
            "terminal": self.terminal,
            "definition_contract": self.definition_contract,
            "definition_completeness": self.definition_completeness,
            "definition_digest": self.definition_digest,
            "seal_status": self.seal_status,
            "integrity_status": self.integrity_status,
            "selected_option": (
                self.selected_option.to_dict() if self.selected_option is not None else None
            ),
            "replacement_choice_id": self.replacement_choice_id,
        }


@dataclass(frozen=True)
class ChoicePageMetadata:
    limit: int
    offset: int
    returned: int
    has_more: bool
    next_offset: int | None

    @classmethod
    def build(cls, *, limit: int, offset: int, returned: int, has_more: bool) -> ChoicePageMetadata:
        validate_choice_read_page(limit=limit, offset=offset)
        if returned < 0 or returned > limit:
            raise ValueError(
                "P2P_CHOICE_READ_PAGE_INVALID: returned count must be within the requested limit"
            )
        return cls(
            limit=limit,
            offset=offset,
            returned=returned,
            has_more=has_more,
            next_offset=(offset + returned) if has_more else None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "limit": self.limit,
            "offset": self.offset,
            "returned": self.returned,
            "has_more": self.has_more,
            "next_offset": self.next_offset,
        }


@dataclass(frozen=True)
class ChoiceListRead:
    items: tuple[ChoiceSummaryRead, ...]
    page: ChoicePageMetadata
    contract: str = CHOICE_LIST_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "items": [item.to_dict() for item in self.items],
            "page": self.page.to_dict(),
        }


@dataclass(frozen=True)
class ChoiceOptionRead:
    option_id: str
    title: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.option_id, "title": self.title}


@dataclass(frozen=True)
class ChoiceDefinitionRead:
    source_contract: str
    completeness: str
    digest: str | None
    choice_id: str
    title: str
    problem: str | None
    context: str | None
    governance_boundary: str | None
    options: tuple[ChoiceOptionRead, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_contract": self.source_contract,
            "completeness": self.completeness,
            "digest": self.digest,
            "choice_id": self.choice_id,
            "title": self.title,
            "problem": self.problem,
            "context": self.context,
            "governance_boundary": self.governance_boundary,
            "options": [option.to_dict() for option in self.options],
        }


@dataclass(frozen=True)
class ChoiceLifecycleRead:
    source_contract: str
    state: str
    terminal: bool
    selected_option: ChoiceSelectionRead | None
    terminal_event: Mapping[str, object] | None
    replacement_choice_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "source_contract": self.source_contract,
            "state": self.state,
            "terminal": self.terminal,
            "selected_option": (
                self.selected_option.to_dict() if self.selected_option is not None else None
            ),
            "terminal_event": (
                dict(self.terminal_event) if self.terminal_event is not None else None
            ),
            "replacement_choice_id": self.replacement_choice_id,
        }


@dataclass(frozen=True)
class ChoiceIntegrityRead:
    seal_status: str
    integrity_status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "seal_status": self.seal_status,
            "integrity_status": self.integrity_status,
        }


@dataclass(frozen=True)
class ChoiceRelationRead:
    kind: str
    target_type: str
    target_id: str
    relationship: str | None = None
    rationale: str | None = None
    status: str | None = None
    reason: str | None = None
    recorded_on: str | None = None
    cleared_on: str | None = None
    cleared_by: str | None = None
    clearing_reason: str | None = None
    derived: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "rationale": self.rationale,
            "status": self.status,
            "reason": self.reason,
            "recorded_on": self.recorded_on,
            "cleared_on": self.cleared_on,
            "cleared_by": self.cleared_by,
            "clearing_reason": self.clearing_reason,
            "derived": self.derived,
        }


@dataclass(frozen=True)
class ChoiceRelationPageRead:
    items: tuple[ChoiceRelationRead, ...]
    page: ChoicePageMetadata

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [item.to_dict() for item in self.items],
            "page": self.page.to_dict(),
        }


@dataclass(frozen=True)
class ChoiceDetailRead:
    choice_id: str
    definition: ChoiceDefinitionRead
    lifecycle: ChoiceLifecycleRead
    integrity: ChoiceIntegrityRead
    relations: ChoiceRelationPageRead
    contract: str = CHOICE_DETAIL_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "choice_id": self.choice_id,
            "definition": self.definition.to_dict(),
            "lifecycle": self.lifecycle.to_dict(),
            "integrity": self.integrity.to_dict(),
            "relations": self.relations.to_dict(),
        }

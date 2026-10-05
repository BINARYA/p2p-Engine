from __future__ import annotations

from p2p_engine.core.choices import ChoiceDefinition

CHOICE_CREATE_RESULT_CONTRACT = "p2p-choice-create-result/v1"
CHOICE_CREATE_FIELD_LIMITS = {
    "title": 200,
    "problem": 4000,
    "context": 8000,
    "governance_boundary": 2000,
    "option": 500,
    "source": 256,
}
CHOICE_CREATE_MAX_RELATED_PROPOSALS = 32


def validate_choice_creation_bounds(
    definition: ChoiceDefinition, *, related_count: int, source: str | None,
) -> None:
    """Machine creation limits count normalized Unicode characters."""
    fields = {
        "title": definition.title,
        "problem": definition.problem,
        "context": definition.context,
        "governance_boundary": definition.governance_boundary,
        "source": source or "",
    }
    for field, value in fields.items():
        if len(value) > CHOICE_CREATE_FIELD_LIMITS[field]:
            raise ValueError(
                f"P2P_CHOICE_CREATE_INVALID: {field} exceeds "
                f"{CHOICE_CREATE_FIELD_LIMITS[field]} characters"
            )
    if any(len(item.title) > CHOICE_CREATE_FIELD_LIMITS["option"] for item in definition.options):
        raise ValueError("P2P_CHOICE_CREATE_INVALID: option title exceeds 500 characters")
    if related_count > CHOICE_CREATE_MAX_RELATED_PROPOSALS:
        raise ValueError("P2P_CHOICE_CREATE_INVALID: related proposals exceed 32 entries")

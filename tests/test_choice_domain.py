from __future__ import annotations

import pytest

from p2p_engine.core.choices import (
    ChoiceDefinition,
    ChoiceState,
    is_active_choice_state,
    is_terminal_choice_state,
    require_supersession_replacement_state,
    require_transition_allowed,
    validate_supersession_graph,
)


def _definition(*, title: str = "Runtime", options: list[str] | None = None) -> ChoiceDefinition:
    return ChoiceDefinition.build(
        choice_id="CHOICE-001",
        title=title,
        problem="Choose a runtime.",
        context="The project requires one stable answer.",
        governance_boundary="The owner decides.",
        option_titles=options or ["Keep", "Replace"],
    )


def test_choice_definition_digest_is_semantic_and_lifecycle_independent() -> None:
    first = _definition(title="Cafe\u0301")
    second = _definition(title="Caf\u00e9")

    assert first.digest == second.digest
    assert first.digest.startswith("sha256:")
    assert len(first.digest) == 71


@pytest.mark.parametrize("state", tuple(ChoiceState))
@pytest.mark.parametrize("transition", ("decide", "withdraw", "supersede"))
def test_choice_transition_matrix_allows_only_open_closure_and_decided_supersession(
    state: ChoiceState, transition: str
) -> None:
    allowed = state == ChoiceState.open or (
        state == ChoiceState.decided and transition == "supersede"
    )
    if allowed:
        require_transition_allowed(state, transition)
    else:
        with pytest.raises(ValueError, match="P2P_CHOICE_TERMINAL"):
            require_transition_allowed(state, transition)


@pytest.mark.parametrize("source", (ChoiceState.open, ChoiceState.decided))
@pytest.mark.parametrize("replacement", tuple(ChoiceState))
def test_choice_supersession_requires_matching_open_or_decided_replacement(
    source: ChoiceState, replacement: ChoiceState
) -> None:
    if replacement == source:
        require_supersession_replacement_state(source, replacement)
    else:
        with pytest.raises(ValueError, match="P2P_CHOICE_REPLACEMENT_INVALID"):
            require_supersession_replacement_state(source, replacement)


@pytest.mark.parametrize("source", (ChoiceState.withdrawn, ChoiceState.superseded))
def test_choice_supersession_replacement_cannot_reopen_terminal_source(
    source: ChoiceState,
) -> None:
    with pytest.raises(ValueError, match="P2P_CHOICE_TERMINAL"):
        require_supersession_replacement_state(source, ChoiceState.decided)


def test_choice_state_predicates_normalize_legacy_active_aliases() -> None:
    assert is_active_choice_state("draft") is True
    assert is_active_choice_state("pending") is True
    assert is_terminal_choice_state(ChoiceState.withdrawn) is True
    with pytest.raises(ValueError, match="unknown state"):
        is_active_choice_state("mystery")


def test_choice_definition_rejects_duplicate_normalized_options() -> None:
    with pytest.raises(ValueError, match="distinct"):
        _definition(options=["Keep runtime", "  KEEP   RUNTIME "])


def test_choice_supersession_graph_rejects_direct_and_transitive_cycles() -> None:
    validate_supersession_graph({"CHOICE-001": "CHOICE-002", "CHOICE-002": "CHOICE-003"})
    with pytest.raises(ValueError, match="P2P_CHOICE_REPLACEMENT_CYCLE"):
        validate_supersession_graph(
            {
                "CHOICE-001": "CHOICE-002",
                "CHOICE-002": "CHOICE-003",
                "CHOICE-003": "CHOICE-001",
            }
        )

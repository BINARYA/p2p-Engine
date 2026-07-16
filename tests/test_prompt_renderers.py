from __future__ import annotations

import pytest

from p2p_engine.prompts.common import render_nearby_decision_context


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", [None, "", "  \n"])
def test_nearby_decision_context_uses_stable_fallback(value: str | None) -> None:
    context = {} if value is None else {"nearby_decision_context": value}

    assert render_nearby_decision_context(context) == (
        "## Nearby Decision Context\n\nNot available."
    )


def test_nearby_decision_context_strips_provided_value() -> None:
    assert render_nearby_decision_context(
        {"nearby_decision_context": "  ## Nearby Decision Context\n\nDecision A.  "}
    ) == "## Nearby Decision Context\n\nDecision A."

from __future__ import annotations

import pytest

from p2p_engine.foundation.markdown import (
    markdown_has_section,
    read_frontmatter,
    read_markdown_section,
    read_title,
    replace_frontmatter,
    replace_section,
    strip_markdown_title,
)
from p2p_engine.foundation.validators import validate_tasks_yaml, validate_yaml_key


def test_markdown_title_sections_and_pending_suppression() -> None:
    text = (
        "# PROP-001 - Demo\n\n"
        "Intro\n\n"
        "## Problem\n\n"
        "A real problem.\n\n"
        "## Context\n\n"
        "Pending.\n\n"
        "## Goals\n\n"
        "- Pending.\n"
    )

    assert read_title(text) == "PROP-001 - Demo"
    assert read_title("No title") is None
    assert read_markdown_section(text, "Problem") == "A real problem."
    assert read_markdown_section(text, "Context") is None
    assert read_markdown_section(text, "Goals") is None
    assert read_markdown_section(text, "Missing") is None
    assert markdown_has_section(text, "Problem") is True
    assert markdown_has_section(text, "Missing") is False


def test_markdown_replace_section_preserves_existing_contract() -> None:
    text = "# Demo\n\n## Problem\n\nOld.\n\n## Proposal\n\nKeep.\n"

    updated = replace_section(text, "Problem", "New.")
    unchanged = replace_section(text, "Missing", "New.")

    assert updated == "# Demo\n\n## Problem\n\nNew.\n\n## Proposal\n\nKeep.\n"
    assert unchanged == text


def test_frontmatter_read_replace_and_invalid_fallback() -> None:
    text = "---\ntitle: Demo\nitems:\n  - one\n---\n\n# Demo\n"

    assert read_frontmatter(text) == {"title": "Demo", "items": ["one"]}
    assert read_frontmatter("# Demo\n") == {}
    assert read_frontmatter("---\n: invalid\n---\n# Demo\n") == {}
    assert read_frontmatter("---\n- one\n---\n# Demo\n") == {}

    replaced = replace_frontmatter(text, {"status": "accepted"})
    inserted = replace_frontmatter("# Demo\n", {"status": "draft"})

    assert replaced == "---\nstatus: accepted\n---\n\n# Demo\n"
    assert inserted == "---\nstatus: draft\n---\n# Demo\n"


def test_strip_markdown_title() -> None:
    assert strip_markdown_title("# Title\n\nBody\n") == "Body"
    assert strip_markdown_title("# Title\nBody\n") == "Body"
    assert strip_markdown_title("Body\n") == "Body"
    assert strip_markdown_title("") == ""


def test_validate_tasks_yaml_and_top_level_key() -> None:
    validate_tasks_yaml("tasks: []\n")
    validate_yaml_key("impact:\n  level: low\n", "impact")

    with pytest.raises(ValueError, match="Invalid tasks YAML"):
        validate_tasks_yaml("tasks: [\n")
    with pytest.raises(ValueError, match="Invalid tasks YAML: expected top-level `tasks` list."):
        validate_tasks_yaml("tasks: {}\n")
    with pytest.raises(ValueError, match="Invalid YAML"):
        validate_yaml_key("impact: [\n", "impact")
    with pytest.raises(ValueError, match="Invalid YAML: expected top-level `impact` key."):
        validate_yaml_key("other: true\n", "impact")

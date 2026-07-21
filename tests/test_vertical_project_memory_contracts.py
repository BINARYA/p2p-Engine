from __future__ import annotations

from dataclasses import replace

import pytest

from p2p_engine.core.vertical_memory import (
    VerticalProjectMemoryView,
    validate_vertical_memory_owned_path,
    validate_vertical_memory_view,
    vertical_memory_section_path,
)


def test_vertical_memory_owned_paths_are_bounded() -> None:
    assert vertical_memory_section_path("data_model") == (
        ".p2p/project/vertical-memory/sections/data_model.yml"
    )
    validate_vertical_memory_owned_path(".p2p/project/vertical-memory/project.yml")
    with pytest.raises(ValueError, match="Unsafe vertical-memory section ID"):
        vertical_memory_section_path("../outside")
    with pytest.raises(ValueError, match="escapes owned root"):
        validate_vertical_memory_owned_path(".p2p/project/definition.yml")


def test_vertical_memory_view_rejects_duplicate_sections_and_invalid_hash() -> None:
    view = VerticalProjectMemoryView(
        vertical_id="software_project",
        vertical_version="1.0",
        vertical_checksum="a" * 64,
        sections=(),
        unmapped_active_proposals=(),
        diagnostics=(),
        source_fingerprint_sha256="bad",
    )
    with pytest.raises(ValueError, match="source fingerprint"):
        validate_vertical_memory_view(view)

    valid = replace(view, source_fingerprint_sha256="b" * 64)
    validate_vertical_memory_view(valid)

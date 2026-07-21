from __future__ import annotations

import pytest
import yaml

from p2p_engine.foundation.yaml_loaders import (
    DuplicateYamlKeyError,
    c_loader_available,
    load_yaml,
    load_yaml_mapping,
    load_yaml_sequence,
)


@pytest.mark.parametrize(
    "content",
    [
        "mapping: {one: 1, two: 2}\nsequence: [a, b]\nscalar: yes\nnull: null\n",
        "base: &base\n  one: 1\nmerged:\n  <<: *base\n  two: 2\n",
        "unicode: \"café\"\n",
    ],
)
def test_safe_loader_python_and_c_parity(content: str) -> None:
    python_value = load_yaml(content, force_python=True)
    accelerated_value = load_yaml(content, force_python=False)

    assert accelerated_value == python_value


def test_unique_loader_rejects_duplicates_in_both_modes() -> None:
    content = "value: 1\nvalue: 2\n"

    for force_python in (True, False):
        with pytest.raises(DuplicateYamlKeyError, match="Duplicate YAML key: value"):
            load_yaml(
                content,
                loader_contract="unique-v1",
                force_python=force_python,
            )


def test_yaml_shape_helpers_and_unsupported_contract() -> None:
    assert load_yaml_mapping("value: 1\n") == {"value": 1}
    assert load_yaml_sequence("- one\n- two\n") == ["one", "two"]
    with pytest.raises(ValueError, match="expected a mapping"):
        load_yaml_mapping("- one\n")
    with pytest.raises(ValueError, match="expected a sequence"):
        load_yaml_sequence("value: one\n")
    with pytest.raises(ValueError, match="Unsupported YAML loader contract"):
        load_yaml("value: one\n", loader_contract="unknown")


def test_yaml_loader_rejects_malformed_and_multiple_documents() -> None:
    for force_python in (True, False):
        with pytest.raises(yaml.YAMLError):
            load_yaml("value: [\n", force_python=force_python)
        with pytest.raises(yaml.YAMLError):
            load_yaml("one: 1\n---\ntwo: 2\n", force_python=force_python)


def test_c_loader_capability_is_explicit() -> None:
    assert isinstance(c_loader_available(), bool)


@pytest.mark.parametrize(
    "content, expected",
    [
        ("plain text\n", "plain text"),
        ("null\n", None),
        ("true\n", True),
        ("42\n", 42),
        ("[one, two]\n", ["one", "two"]),
    ],
)
def test_safe_loader_scalar_and_sequence_parity(content: str, expected: object) -> None:
    assert load_yaml(content, force_python=True) == expected
    assert load_yaml(content, force_python=False) == expected


def test_safe_loader_rejects_unsafe_tags_in_both_modes() -> None:
    content = "!!python/object/apply:os.system ['echo unsafe']\n"

    for force_python in (True, False):
        with pytest.raises(yaml.YAMLError):
            load_yaml(content, force_python=force_python)


def test_safe_loader_large_mapping_parity() -> None:
    content = "\n".join(f"key_{index}: {index}" for index in range(10_000))

    assert load_yaml(content, force_python=False) == load_yaml(
        content,
        force_python=True,
    )

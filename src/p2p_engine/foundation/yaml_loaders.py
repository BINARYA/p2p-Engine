from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from typing import Any

import yaml


SAFE_LOADER_CONTRACT = "safe-v1"
UNIQUE_LOADER_CONTRACT = "unique-v1"


class DuplicateYamlKeyError(ValueError):
    def __init__(self, key: object) -> None:
        self.key = key
        super().__init__(f"Duplicate YAML key: {key}")


class PythonUniqueSafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: yaml.SafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise DuplicateYamlKeyError(key)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


PythonUniqueSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


if hasattr(yaml, "CSafeLoader"):
    class CUniqueSafeLoader(yaml.CSafeLoader):  # type: ignore[misc]
        pass

    CUniqueSafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_unique_mapping,
    )
else:  # pragma: no cover - depends on the PyYAML build
    CUniqueSafeLoader = PythonUniqueSafeLoader


def c_loader_available() -> bool:
    return hasattr(yaml, "CSafeLoader")


def load_yaml(
    content: str | bytes,
    *,
    loader_contract: str = SAFE_LOADER_CONTRACT,
    force_python: bool | None = None,
) -> object:
    if force_python is None:
        force_python = os.environ.get("P2P_YAML_FORCE_PYTHON", "").strip() == "1"
    if loader_contract == SAFE_LOADER_CONTRACT:
        loader = yaml.SafeLoader if force_python or not c_loader_available() else yaml.CSafeLoader
    elif loader_contract == UNIQUE_LOADER_CONTRACT:
        loader = PythonUniqueSafeLoader if force_python or not c_loader_available() else CUniqueSafeLoader
    else:
        raise ValueError(f"Unsupported YAML loader contract: {loader_contract}")
    return yaml.load(content, Loader=loader)


def load_yaml_mapping(
    content: str | bytes,
    *,
    loader_contract: str = SAFE_LOADER_CONTRACT,
    force_python: bool | None = None,
) -> dict[str, Any]:
    value = load_yaml(
        content,
        loader_contract=loader_contract,
        force_python=force_python,
    )
    if not isinstance(value, Mapping):
        raise ValueError("Invalid YAML: expected a mapping")
    return dict(value)


def load_yaml_sequence(
    content: str | bytes,
    *,
    loader_contract: str = SAFE_LOADER_CONTRACT,
    force_python: bool | None = None,
) -> list[Any]:
    value = load_yaml(
        content,
        loader_contract=loader_contract,
        force_python=force_python,
    )
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("Invalid YAML: expected a sequence")
    return list(value)

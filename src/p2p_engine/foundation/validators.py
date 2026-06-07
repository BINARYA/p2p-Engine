from __future__ import annotations

import yaml


def validate_tasks_yaml(content: str) -> None:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid tasks YAML: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise ValueError("Invalid tasks YAML: expected top-level `tasks` list.")


def validate_yaml_key(content: str, key: str) -> None:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict) or key not in data:
        raise ValueError(f"Invalid YAML: expected top-level `{key}` key.")

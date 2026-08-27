from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import typer
import yaml

from p2p_engine.cli_contract import print_json


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return to_plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def emit_structured(value: Any, output_format: str) -> bool:
    normalized = output_format.strip().lower()
    if normalized == "text":
        return False
    payload = to_plain(value)
    if normalized == "json":
        print_json(payload)
        return True
    if normalized == "yaml":
        print(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False).rstrip())
        return True
    raise typer.BadParameter("Output format must be text, json, or yaml.")

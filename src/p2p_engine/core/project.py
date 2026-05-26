from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    project_id: str
    name: str
    status: str = "active"


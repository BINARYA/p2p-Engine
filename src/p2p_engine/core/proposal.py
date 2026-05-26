from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    title: str
    slug: str
    status: str
    path: Path


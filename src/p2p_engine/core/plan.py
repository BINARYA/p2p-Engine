from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Workstream:
    workstream_id: str
    name: str
    domain: str
    outcome: str


@dataclass(frozen=True)
class ExecutionPlan:
    proposal_id: str
    objective: str
    workstreams: list[Workstream] = field(default_factory=list)


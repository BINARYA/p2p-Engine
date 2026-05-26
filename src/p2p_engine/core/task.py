from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Action:
    action_id: str
    title: str
    status: str = "todo"


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    workstream: str
    task_type: str
    status: str = "todo"
    priority: str = "medium"
    dependencies: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)


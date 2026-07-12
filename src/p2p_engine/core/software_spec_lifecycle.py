from __future__ import annotations

from dataclasses import dataclass, field


SPEC_LIFECYCLE_INTENTS = (
    "chat_exploration",
    "project_definition",
    "architecture_comparison",
    "implementation_spec",
    "downstream_export",
    "exact_file_request",
)


@dataclass(frozen=True)
class SpecLifecycleRoute:
    intent: str
    route: str
    write_class: str
    persistent_artifact: str
    canonical_status: str
    writes_state: bool
    preconditions: list[str] = field(default_factory=list)
    suggested_commands: list[str] = field(default_factory=list)
    next_step: str = ""


@dataclass(frozen=True)
class SpecLifecycleDiagnostic:
    code: str
    severity: str
    message: str
    artifact_id: str = ""
    suggested_command: str = ""
    recoverable: bool = True


@dataclass(frozen=True)
class SpecLifecycleView:
    intent: str
    route: str
    write_class: str
    persistent_artifact: str
    canonical_status: str
    writes_state: bool
    change_id: str = ""
    target: str = ""
    blockers: list[SpecLifecycleDiagnostic] = field(default_factory=list)
    advisories: list[SpecLifecycleDiagnostic] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    suggested_commands: list[str] = field(default_factory=list)
    next_step: str = ""

    @property
    def blocked(self) -> bool:
        return bool(self.blockers)

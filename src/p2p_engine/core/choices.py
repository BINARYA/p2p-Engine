from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Mapping, Sequence

CHOICE_DEFINITION_CONTRACT = "p2p-choice-definition/v1"
CHOICE_LIFECYCLE_CONTRACT = "p2p-choice-lifecycle/v1"
CHOICE_TERMINAL_EVENT_CONTRACT = "p2p-choice-terminal-event/v1"
CHOICE_TRANSITION_PREVIEW_CONTRACT = "p2p-choice-transition-preview/v1"
CHOICE_TRANSITION_RESULT_CONTRACT = "p2p-choice-transition-result/v1"
DEFAULT_GOVERNANCE_BOUNDARY = (
    "This choice is advisory until decided through P2P governance."
)

_CHOICE_ID = re.compile(r"^CHOICE-[0-9]{3,}$")
_OPTION_ID = re.compile(r"^[A-Z]$")


class ChoiceState(StrEnum):
    open = "open"
    decided = "decided"
    withdrawn = "withdrawn"
    superseded = "superseded"


class ChoiceTransitionKind(StrEnum):
    decide = "decide"
    withdraw = "withdraw"
    supersede = "supersede"


TERMINAL_CHOICE_STATES = frozenset(
    {ChoiceState.decided, ChoiceState.withdrawn, ChoiceState.superseded}
)


def normalize_choice_state(value: object) -> ChoiceState:
    normalized = str(value or "").strip().lower()
    if normalized in {"open", "draft", "pending"}:
        return ChoiceState.open
    try:
        return ChoiceState(normalized)
    except ValueError as exc:
        raise ValueError(f"P2P_CHOICE_LIFECYCLE_INVALID: unknown state `{normalized}`") from exc


def is_active_choice_state(value: object) -> bool:
    return normalize_choice_state(value) == ChoiceState.open


def is_terminal_choice_state(value: object) -> bool:
    return normalize_choice_state(value) in TERMINAL_CHOICE_STATES


def transition_target(kind: ChoiceTransitionKind | str) -> ChoiceState:
    selected = ChoiceTransitionKind(str(kind))
    return {
        ChoiceTransitionKind.decide: ChoiceState.decided,
        ChoiceTransitionKind.withdraw: ChoiceState.withdrawn,
        ChoiceTransitionKind.supersede: ChoiceState.superseded,
    }[selected]


def require_transition_allowed(state: ChoiceState | str, kind: ChoiceTransitionKind | str) -> None:
    current = normalize_choice_state(state)
    selected = ChoiceTransitionKind(str(kind))
    if current != ChoiceState.open:
        raise ValueError(
            "P2P_CHOICE_TERMINAL: terminal Choices cannot be reopened, "
            f"re-decided or rewritten (state={current.value}, transition={selected.value})"
        )


def normalize_definition_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"P2P_CHOICE_DEFINITION_INVALID: {field} must be text")
    normalized = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
    if not normalized or normalized.casefold() in {"pending", "pending."}:
        raise ValueError(f"P2P_CHOICE_DEFINITION_INCOMPLETE: {field} is required")
    return normalized


@dataclass(frozen=True)
class ChoiceOptionDefinition:
    option_id: str
    title: str

    def __post_init__(self) -> None:
        option_id = str(self.option_id).strip().upper()
        if not _OPTION_ID.fullmatch(option_id):
            raise ValueError("P2P_CHOICE_DEFINITION_INVALID: option ID must be A-Z")
        object.__setattr__(self, "option_id", option_id)
        object.__setattr__(self, "title", normalize_definition_text(self.title, "option title"))

    def to_dict(self) -> dict[str, str]:
        return {"id": self.option_id, "title": self.title}


@dataclass(frozen=True)
class ChoiceDefinition:
    choice_id: str
    title: str
    problem: str
    context: str
    governance_boundary: str
    options: tuple[ChoiceOptionDefinition, ...]

    def __post_init__(self) -> None:
        choice_id = str(self.choice_id).strip().upper()
        if not _CHOICE_ID.fullmatch(choice_id):
            raise ValueError("P2P_CHOICE_DEFINITION_INVALID: invalid Choice ID")
        object.__setattr__(self, "choice_id", choice_id)
        object.__setattr__(self, "title", normalize_definition_text(self.title, "title"))
        object.__setattr__(self, "problem", normalize_definition_text(self.problem, "Problem"))
        object.__setattr__(self, "context", normalize_definition_text(self.context, "Context"))
        object.__setattr__(
            self,
            "governance_boundary",
            normalize_definition_text(self.governance_boundary, "Governance Boundary"),
        )
        if not 2 <= len(self.options) <= 26:
            raise ValueError("P2P_CHOICE_DEFINITION_INVALID: a Choice requires 2-26 options")
        ids = [item.option_id for item in self.options]
        expected = [chr(ord("A") + index) for index in range(len(self.options))]
        if ids != expected:
            raise ValueError("P2P_CHOICE_DEFINITION_INVALID: option IDs must be ordered A-Z")
        titles = [" ".join(item.title.casefold().split()) for item in self.options]
        if len(titles) != len(set(titles)):
            raise ValueError("P2P_CHOICE_DEFINITION_INVALID: option titles must be distinct")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": CHOICE_DEFINITION_CONTRACT,
            "choice_id": self.choice_id,
            "title": self.title,
            "problem": self.problem,
            "context": self.context,
            "governance_boundary": self.governance_boundary,
            "options": [item.to_dict() for item in self.options],
        }

    @property
    def digest(self) -> str:
        content = json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(content).hexdigest()

    def option(self, value: str) -> ChoiceOptionDefinition:
        wanted = str(value).strip().casefold()
        for option in self.options:
            if wanted in {option.option_id.casefold(), option.title.casefold()}:
                return option
        raise ValueError(f"P2P_CHOICE_OPTION_NOT_FOUND: Choice option not found: {value}")

    @classmethod
    def build(
        cls,
        *,
        choice_id: str,
        title: str,
        problem: str,
        context: str,
        governance_boundary: str,
        option_titles: Sequence[str],
    ) -> "ChoiceDefinition":
        return cls(
            choice_id=choice_id,
            title=title,
            problem=problem,
            context=context,
            governance_boundary=governance_boundary,
            options=tuple(
                ChoiceOptionDefinition(chr(ord("A") + index), option)
                for index, option in enumerate(option_titles)
            ),
        )


@dataclass(frozen=True)
class ChoiceTerminalEvent:
    kind: ChoiceState
    reason: str
    effective_on: str
    owner_actor: str
    executor_actor: str
    authority_mode: str
    source_channel: str
    operation_key_sha256: str
    selected_option_id: str | None = None
    replacement_choice_id: str | None = None
    blocker_override: bool = False
    evidence_origin: str = "current_governed_transition"

    def __post_init__(self) -> None:
        if self.kind not in TERMINAL_CHOICE_STATES:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: event kind must be terminal")
        normalize_definition_text(self.reason, "terminal reason")
        try:
            date.fromisoformat(self.effective_on)
        except ValueError as exc:
            raise ValueError(
                "P2P_CHOICE_LIFECYCLE_INVALID: effective_on must be YYYY-MM-DD"
            ) from exc
        for field, value in (
            ("owner_actor", self.owner_actor),
            ("executor_actor", self.executor_actor),
            ("authority_mode", self.authority_mode),
            ("source_channel", self.source_channel),
            ("operation_key_sha256", self.operation_key_sha256),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"P2P_CHOICE_LIFECYCLE_INVALID: {field} is required")
        if not re.fullmatch(r"[0-9a-f]{64}", self.operation_key_sha256):
            raise ValueError(
                "P2P_CHOICE_LIFECYCLE_INVALID: operation key digest is invalid"
            )
        if self.kind == ChoiceState.decided:
            if self.selected_option_id is None or self.replacement_choice_id is not None:
                raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: decided requires one selected option")
            if not _OPTION_ID.fullmatch(self.selected_option_id):
                raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: selected option ID is invalid")
        elif self.kind == ChoiceState.withdrawn:
            if self.selected_option_id is not None or self.replacement_choice_id is not None:
                raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: withdrawn cannot select or replace")
        elif self.selected_option_id is not None or not self.replacement_choice_id:
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: superseded requires one replacement")
        elif not _CHOICE_ID.fullmatch(self.replacement_choice_id):
            raise ValueError("P2P_CHOICE_LIFECYCLE_INVALID: replacement Choice ID is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": CHOICE_TERMINAL_EVENT_CONTRACT,
            "kind": self.kind.value,
            "evidence_origin": self.evidence_origin,
            "reason": self.reason,
            "effective_on": self.effective_on,
            "owner_actor": self.owner_actor,
            "executor_actor": self.executor_actor,
            "authority_mode": self.authority_mode,
            "source_channel": self.source_channel,
            "operation_key_sha256": self.operation_key_sha256,
            "selected_option_id": self.selected_option_id,
            "replacement_choice_id": self.replacement_choice_id,
            "blocker_override": self.blocker_override,
        }


def validate_supersession_graph(edges: Mapping[str, str]) -> None:
    for source in edges:
        seen: set[str] = set()
        current = source
        while current in edges:
            if current in seen:
                raise ValueError("P2P_CHOICE_REPLACEMENT_CYCLE: supersession lineage contains a cycle")
            seen.add(current)
            current = edges[current]

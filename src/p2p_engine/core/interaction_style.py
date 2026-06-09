from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

INTERACTION_STYLE_SCHEMA_VERSION = 1
INTERACTION_STYLE_SCOPE = "project"
INTERACTION_STYLE_SCALE_MIN = 0
INTERACTION_STYLE_SCALE_MAX = 5

TECHNICAL_VERBOSITY = "technical_verbosity"
FORMALITY = "formality"
ASSERTIVENESS = "assertiveness"
INTERACTION_STYLE_SCALE_NAMES = (TECHNICAL_VERBOSITY, FORMALITY, ASSERTIVENESS)

DEFAULT_TECHNICAL_VERBOSITY = 2
DEFAULT_FORMALITY = 2
DEFAULT_ASSERTIVENESS = 0


@dataclass(frozen=True)
class InteractionStyle:
    technical_verbosity: int = DEFAULT_TECHNICAL_VERBOSITY
    formality: int = DEFAULT_FORMALITY
    assertiveness: int = DEFAULT_ASSERTIVENESS


@dataclass(frozen=True)
class InteractionStyleScale:
    name: str
    value: int
    label: str
    description: str


@dataclass(frozen=True)
class InteractionStyleUpdate:
    technical_verbosity: int | None = None
    formality: int | None = None
    assertiveness: int | None = None

    def has_changes(self) -> bool:
        return any(value is not None for value in (self.technical_verbosity, self.formality, self.assertiveness))


@dataclass(frozen=True)
class InteractionStyleView:
    schema_version: int
    scope: str
    configured: bool
    source: str
    path: Path
    technical_verbosity: InteractionStyleScale
    formality: InteractionStyleScale
    assertiveness: InteractionStyleScale
    updated_at: str = ""
    updated_by: str = ""


TECHNICAL_VERBOSITY_DESCRIPTORS: dict[int, tuple[str, str]] = {
    0: ("plain", "Avoid engine and technical workflow terms unless required for correctness."),
    1: ("minimal", "Use minimal operational terms and put plain-language summaries first."),
    2: ("balanced", "Use light engine vocabulary when useful."),
    3: ("specific", "Name relevant commands, artifacts, and state when they clarify the work."),
    4: ("detailed", "Usually name commands, files, artifacts, and verification steps."),
    5: ("exhaustive", "Provide command-by-command and file/state level explanation when relevant."),
}

FORMALITY_DESCRIPTORS: dict[int, tuple[str, str]] = {
    0: ("colloquial", "Use a highly informal and colloquial tone while staying respectful."),
    1: ("casual", "Use a casual and direct tone."),
    2: ("direct", "Use a direct, human, and professional tone for normal project work."),
    3: ("professional", "Use a clearly professional and measured tone."),
    4: ("formal", "Use a formal and reserved tone."),
    5: ("detached", "Use a highly formal, detached, and precise tone."),
}

ASSERTIVENESS_DESCRIPTORS: dict[int, tuple[str, str]] = {
    0: ("baseline", "Use current baseline follow-up behavior without extra pressure."),
    1: ("light", "Use light nudges for important gaps."),
    2: ("regular", "Follow up regularly on missing evidence and unclear decisions."),
    3: ("proactive", "Challenge weak assumptions and incomplete artifacts proactively."),
    4: ("strict", "Enforce ordering and repeat next questions until the owner stops, defers, mutes, or decides."),
    5: ("exacting", "Persistently close gaps and enforce order while staying bounded by owner authority."),
}

DESCRIPTORS_BY_SCALE: dict[str, dict[int, tuple[str, str]]] = {
    TECHNICAL_VERBOSITY: TECHNICAL_VERBOSITY_DESCRIPTORS,
    FORMALITY: FORMALITY_DESCRIPTORS,
    ASSERTIVENESS: ASSERTIVENESS_DESCRIPTORS,
}


def default_interaction_style() -> InteractionStyle:
    return InteractionStyle()


def normalize_scale_value(name: str, value: Any) -> int:
    if name not in INTERACTION_STYLE_SCALE_NAMES:
        raise ValueError(f"Unknown interaction style scale: {name}")
    if isinstance(value, bool) or value is None:
        raise ValueError(_invalid_value_message(name, value))
    if isinstance(value, int):
        normalized = value
    elif isinstance(value, str):
        text = value.strip()
        if not text or not text.isdigit():
            raise ValueError(_invalid_value_message(name, value))
        normalized = int(text)
    else:
        raise ValueError(_invalid_value_message(name, value))
    if normalized < INTERACTION_STYLE_SCALE_MIN or normalized > INTERACTION_STYLE_SCALE_MAX:
        raise ValueError(
            f"Invalid interaction style value for {name}: {normalized}. "
            f"Allowed range: {INTERACTION_STYLE_SCALE_MIN}..{INTERACTION_STYLE_SCALE_MAX}."
        )
    return normalized


def scale_view(name: str, value: Any) -> InteractionStyleScale:
    normalized = normalize_scale_value(name, value)
    descriptors = DESCRIPTORS_BY_SCALE[name]
    label, description = descriptors[normalized]
    return InteractionStyleScale(
        name=name,
        value=normalized,
        label=label,
        description=description,
    )


def interaction_style_from_payload(payload: dict[str, object]) -> InteractionStyle:
    return InteractionStyle(
        technical_verbosity=normalize_scale_value(TECHNICAL_VERBOSITY, payload.get(TECHNICAL_VERBOSITY)),
        formality=normalize_scale_value(FORMALITY, payload.get(FORMALITY)),
        assertiveness=normalize_scale_value(ASSERTIVENESS, payload.get(ASSERTIVENESS)),
    )


def validate_interaction_style_payload(payload: dict[str, object]) -> None:
    state = payload.get("interaction_style")
    if not isinstance(state, dict):
        raise ValueError("Interaction style must define top-level `interaction_style` mapping.")
    schema_version = state.get("schema_version")
    if schema_version != INTERACTION_STYLE_SCHEMA_VERSION:
        raise ValueError(f"Unsupported interaction style schema_version: {schema_version}")
    scope = str(state.get("scope") or "").strip()
    if scope != INTERACTION_STYLE_SCOPE:
        raise ValueError(f"Interaction style scope must be `{INTERACTION_STYLE_SCOPE}`.")
    for scale_name in INTERACTION_STYLE_SCALE_NAMES:
        if scale_name not in state:
            raise ValueError(f"Interaction style missing required scale: {scale_name}")
        normalize_scale_value(scale_name, state.get(scale_name))


def interaction_style_policy_payload() -> dict[str, object]:
    return {
        "source": "p2p_project_interaction_style",
        "scope": "project",
        "defaults": {
            TECHNICAL_VERBOSITY: DEFAULT_TECHNICAL_VERBOSITY,
            FORMALITY: DEFAULT_FORMALITY,
            ASSERTIVENESS: DEFAULT_ASSERTIVENESS,
        },
        "commands": {
            "show": "p2p project interaction-style show",
            "set": "p2p project interaction-style set",
        },
        "mcp_tools": {
            "show": "p2p_project_interaction_style_show",
            "set": "p2p_project_interaction_style_set",
        },
        "scales": {
            name: [
                {
                    "value": value,
                    "label": label,
                    "description": description,
                }
                for value, (label, description) in DESCRIPTORS_BY_SCALE[name].items()
            ]
            for name in INTERACTION_STYLE_SCALE_NAMES
        },
        "affects": ["owner_facing_wording", "detail_level", "follow_up_pressure"],
        "does_not_affect": [
            "governance_authority",
            "readiness_scores",
            "validation_truth",
            "permissions",
            "consent",
            "factual_claims",
        ],
    }


def _invalid_value_message(name: str, value: Any) -> str:
    return (
        f"Invalid interaction style value for {name}: {value!r}. "
        f"Expected integer {INTERACTION_STYLE_SCALE_MIN}..{INTERACTION_STYLE_SCALE_MAX}."
    )

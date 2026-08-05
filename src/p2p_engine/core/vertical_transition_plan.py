from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.vertical_transition_impact import DomainReference, EvidenceKind


VERTICAL_TRANSITION_PLAN_SCHEMA_VERSION = 1
VERTICAL_TRANSITION_PLAN_CONTRACT = "p2p-vertical-transition-plan/v1"
VERTICAL_TRANSITION_PLAN_MAX_DECISIONS = 128

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class TransitionDecision:
    decision_id: str
    action: str
    source: DomainReference
    target: DomainReference | None = None

    def __post_init__(self) -> None:
        if self.action not in {"map", "preserve_as_orphan"}:
            raise ValueError(f"unsupported transition decision action: {self.action}")
        if self.action == "map" and self.target is None:
            raise ValueError("map transition decision requires target")
        if self.action == "preserve_as_orphan" and self.target is not None:
            raise ValueError("preserve_as_orphan transition decision forbids target")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.decision_id,
            "action": self.action,
            "source": self.source.to_dict(),
        }
        if self.target is not None:
            payload["target"] = self.target.to_dict()
        return payload


@dataclass(frozen=True)
class VerticalTransitionPlan:
    analysis_fingerprint_sha256: str
    decisions: tuple[TransitionDecision, ...]
    schema_version: int = VERTICAL_TRANSITION_PLAN_SCHEMA_VERSION
    contract_version: str = VERTICAL_TRANSITION_PLAN_CONTRACT

    @property
    def fingerprint_sha256(self) -> str:
        return semantic_sha256(self.to_dict()["vertical_transition_plan"])

    def to_dict(self) -> dict[str, object]:
        return {
            "vertical_transition_plan": {
                "schema_version": self.schema_version,
                "contract_version": self.contract_version,
                "analysis_fingerprint_sha256": self.analysis_fingerprint_sha256,
                "decisions": [item.to_dict() for item in sorted(self.decisions, key=lambda item: item.decision_id)],
            }
        }


def parse_transition_plan(payload: Mapping[str, object]) -> VerticalTransitionPlan:
    if set(payload) != {"vertical_transition_plan"}:
        raise _invalid("document must contain only vertical_transition_plan")
    raw = payload.get("vertical_transition_plan")
    if not isinstance(raw, Mapping):
        raise _invalid("vertical_transition_plan must be a mapping")
    allowed = {"schema_version", "contract_version", "analysis_fingerprint_sha256", "decisions"}
    unknown = sorted(str(key) for key in raw if key not in allowed)
    missing = sorted(key for key in allowed if key not in raw)
    if unknown or missing:
        detail = f"unknown fields: {', '.join(unknown)}" if unknown else f"missing fields: {', '.join(missing)}"
        raise _invalid(detail)
    if raw.get("schema_version") != VERTICAL_TRANSITION_PLAN_SCHEMA_VERSION:
        raise _invalid(f"schema_version must be {VERTICAL_TRANSITION_PLAN_SCHEMA_VERSION}")
    if raw.get("contract_version") != VERTICAL_TRANSITION_PLAN_CONTRACT:
        raise _invalid(f"contract_version must be {VERTICAL_TRANSITION_PLAN_CONTRACT}")
    analysis = str(raw.get("analysis_fingerprint_sha256") or "")
    if _SHA256.fullmatch(analysis) is None:
        raise _invalid("analysis_fingerprint_sha256 must be a lowercase SHA-256 digest")
    raw_decisions = raw.get("decisions")
    if not isinstance(raw_decisions, list):
        raise _invalid("decisions must be a sequence")
    if len(raw_decisions) > VERTICAL_TRANSITION_PLAN_MAX_DECISIONS:
        raise ValueError(
            "P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED: transition plan exceeds "
            f"{VERTICAL_TRANSITION_PLAN_MAX_DECISIONS} decisions"
        )
    decisions: list[TransitionDecision] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    for index, item in enumerate(raw_decisions):
        if not isinstance(item, Mapping):
            raise _invalid(f"decisions[{index}] must be a mapping")
        item_allowed = {"id", "action", "source", "target"}
        item_unknown = sorted(str(key) for key in item if key not in item_allowed)
        if item_unknown:
            raise _invalid(f"decisions[{index}] has unknown fields: {', '.join(item_unknown)}")
        decision_id = str(item.get("id") or "")
        if not decision_id.startswith("VTD-"):
            raise _invalid(f"decisions[{index}].id must start with VTD-")
        if decision_id in seen_ids:
            raise _invalid(f"duplicate decision id: {decision_id}")
        action = str(item.get("action") or "")
        source = _parse_reference(item.get("source"), field=f"decisions[{index}].source")
        if source.ref in seen_sources:
            raise _invalid(f"duplicate decision source: {source.ref}")
        target = None
        if "target" in item:
            target = _parse_reference(item.get("target"), field=f"decisions[{index}].target")
        try:
            decision = TransitionDecision(decision_id, action, source, target)
        except ValueError as exc:
            raise _invalid(f"decisions[{index}]: {exc}") from exc
        seen_ids.add(decision_id)
        seen_sources.add(source.ref)
        decisions.append(decision)
    return VerticalTransitionPlan(
        analysis_fingerprint_sha256=analysis,
        decisions=tuple(sorted(decisions, key=lambda item: item.decision_id)),
    )


def _parse_reference(value: object, *, field: str) -> DomainReference:
    if not isinstance(value, Mapping) or set(value) != {"kind", "ref"}:
        raise _invalid(f"{field} must contain exactly kind and ref")
    try:
        return DomainReference(
            kind=EvidenceKind(str(value.get("kind") or "")),
            ref=str(value.get("ref") or ""),
        )
    except ValueError as exc:
        raise _invalid(f"{field}: {exc}") from exc


def _invalid(message: str) -> ValueError:
    return ValueError(f"P2P_VERTICAL_TRANSITION_PLAN_INVALID: {message}")

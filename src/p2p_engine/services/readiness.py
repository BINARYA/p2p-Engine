from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import read_markdown_section

DEFAULT_READINESS_PROFILE_ID = "default-readiness-v0.1"
DEFAULT_READINESS_PROFILE_VERSION = "0.1"
READINESS_ARTIFACT_QUALITY_STATES = {
    "missing",
    "placeholder",
    "thin",
    "meaningful",
    "needs_owner_input",
    "ready",
}
READINESS_CONFIDENCE_LEVELS = {"low", "medium", "high"}
READINESS_TIERS = {"small", "medium", "architectural", "governance-critical"}
READINESS_LABELS = {"weak", "partial", "strong", "decision_ready"}


@dataclass(frozen=True)
class ReadinessProfile:
    path: Path
    profile_id: str
    version: str
    criteria: dict[str, int]
    thresholds: dict[str, int]
    tier_requirements: dict[str, dict[str, object]]
    artifact_quality_caps: dict[str, dict[str, object]]
    gates: dict[str, object]
    override_policy: dict[str, object]


@dataclass(frozen=True)
class ProposalReadiness:
    proposal_id: str
    status: str
    path: Path
    profile_id: str | None
    profile_version: str | None
    computed_score: int | None
    computed_label: str | None
    confidence: str | None
    failed_gates: list[str]
    missing: list[str]
    suggested_next: list[str]


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def default_readiness_profile_payload() -> dict[str, object]:
    return {
        "readiness_profile": {
            "id": DEFAULT_READINESS_PROFILE_ID,
            "version": DEFAULT_READINESS_PROFILE_VERSION,
            "criteria": {
                "problem_clarity": 10,
                "goal_clarity": 10,
                "scope_boundaries": 10,
                "alternatives_quality": 15,
                "tradeoff_analysis": 10,
                "risk_coverage": 10,
                "assumptions_clarity": 10,
                "owner_questions_resolution": 10,
                "acceptance_criteria_quality": 10,
                "impact_overlap_analysis": 5,
            },
            "thresholds": {
                "weak": 0,
                "partial": 70,
                "strong": 85,
                "decision_ready": 95,
            },
            "tier_requirements": {
                "small": {"required_score_for_decision": 70},
                "medium": {
                    "required_score_for_decision": 85,
                    "minimum_gates": {
                        "alternatives_quality": 50,
                        "risk_coverage": 50,
                        "acceptance_criteria_quality": 50,
                    },
                },
                "architectural": {
                    "required_score_for_decision": 95,
                    "minimum_gates": {
                        "alternatives_quality": 75,
                        "tradeoff_analysis": 75,
                        "risk_coverage": 75,
                        "impact_overlap_analysis": 75,
                    },
                },
                "governance-critical": {
                    "required_score_for_decision": 95,
                    "required_confidence": "medium",
                    "minimum_gates": {
                        "alternatives_quality": 75,
                        "owner_questions_resolution": 75,
                        "acceptance_criteria_quality": 75,
                        "impact_overlap_analysis": 75,
                    },
                },
            },
            "artifact_quality_caps": {
                "missing": {"max_score_percent": 0},
                "placeholder": {"max_score_percent": 0},
                "thin": {"max_score_percent": 50},
                "meaningful": {"max_score_percent": 75},
                "needs_owner_input": {"max_score_percent": 75, "blocks_ready_for_decision": True},
                "ready": {"max_score_percent": 100},
            },
            "gates": {},
            "override_policy": {
                "override_reason_required": True,
                "preserve_computed_score": True,
            },
        }
    }


class ReadinessService:
    def __init__(self, *, root: Path, p2p_dir: Path, find_proposal_dir: Callable[[str], Path]) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir

    def default_profile_payload(self) -> dict[str, object]:
        return default_readiness_profile_payload()

    def profile(self, profile_id: str = DEFAULT_READINESS_PROFILE_ID) -> ReadinessProfile:
        path = self.p2p_dir / "config" / "readiness-profiles" / f"{profile_id}.yml"
        if profile_id == DEFAULT_READINESS_PROFILE_ID and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_yaml_dump(self.default_profile_payload()), encoding="utf-8")
        data = _read_yaml_mapping(path, default={})
        validate_readiness_profile_payload(data)
        profile = data["readiness_profile"]
        return ReadinessProfile(
            path=path.relative_to(self.root),
            profile_id=str(profile["id"]),
            version=str(profile["version"]),
            criteria={str(key): int(value) for key, value in dict(profile["criteria"]).items()},
            thresholds={str(key): int(value) for key, value in dict(profile["thresholds"]).items()},
            tier_requirements=dict(profile.get("tier_requirements") or {}),
            artifact_quality_caps=dict(profile.get("artifact_quality_caps") or {}),
            gates=dict(profile.get("gates") or {}),
            override_policy=dict(profile.get("override_policy") or {}),
        )

    def read(self, proposal_id: str) -> ProposalReadiness:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "readiness.yml"
        if not path.exists():
            return ProposalReadiness(
                proposal_id=proposal_id,
                status="not_assessed",
                path=path.relative_to(self.root),
                profile_id=None,
                profile_version=None,
                computed_score=None,
                computed_label=None,
                confidence=None,
                failed_gates=[],
                missing=[],
                suggested_next=[],
            )
        data = _read_yaml_mapping(path, default={})
        validate_readiness_assessment_payload(data)
        readiness = data["readiness"]
        return ProposalReadiness(
            proposal_id=proposal_id,
            status=str(readiness.get("status") or "assessed"),
            path=path.relative_to(self.root),
            profile_id=str(readiness.get("profile_id") or ""),
            profile_version=str(readiness.get("profile_version") or ""),
            computed_score=int(readiness["computed_score"]) if "computed_score" in readiness else None,
            computed_label=str(readiness.get("computed_label") or ""),
            confidence=str(readiness.get("confidence") or ""),
            failed_gates=[str(item) for item in readiness.get("failed_gates") or []],
            missing=[str(item) for item in readiness.get("missing") or []],
            suggested_next=[str(item) for item in readiness.get("suggested_next") or []],
        )

    def write(self, proposal_id: str, readiness: dict[str, object]) -> Path:
        proposal_dir = self.find_proposal_dir(proposal_id)
        payload = {"readiness": readiness}
        validate_readiness_assessment_payload(payload)
        path = proposal_dir / "readiness.yml"
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return path.relative_to(self.root)

    def record_override(self, proposal_id: str, reason: str, approver: str) -> Path:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "readiness.yml"
        if path.exists():
            data = _read_yaml_mapping(path, default={})
            validate_readiness_assessment_payload(data)
            readiness = dict(data["readiness"])
        else:
            readiness = {"status": "not_assessed", "reason": "readiness assessment has not been created yet"}
        readiness["owner_override"] = True
        readiness["effective_status"] = "forced_ready"
        readiness["effective_score"] = 100
        readiness["override_reason"] = reason
        readiness["override_approver"] = approver
        readiness["override_recorded_at"] = date.today().isoformat()
        return self.write(proposal_id, readiness)

    def refresh(self, proposal_id: str) -> ProposalReadiness:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "readiness.yml"
        if path.exists():
            data = _read_yaml_mapping(path, default={})
            validate_readiness_assessment_payload(data)
            readiness = dict(data["readiness"])
            if readiness.get("status") != "not_assessed":
                profile_id = str(readiness.get("profile_id") or DEFAULT_READINESS_PROFILE_ID)
                refreshed = refresh_readiness_payload(readiness, self.profile(profile_id))
                self.write(proposal_id, refreshed)
                return self.read(proposal_id)
        self.write(proposal_id, {"status": "not_assessed", "reason": "readiness assessment has not been created yet"})
        return self.read(proposal_id)

    def initialize(self, proposal_id: str) -> ProposalReadiness:
        proposal_dir = self.find_proposal_dir(proposal_id)
        profile = self.profile()
        proposal_text = _read_optional(proposal_dir / "proposal.md")
        criteria: dict[str, object] = {}
        missing: list[str] = []
        suggested_next: list[str] = []
        failed_gates: list[str] = []

        def add_criterion(
            criterion: str,
            artifact: str,
            section: str | None,
            text: str | None,
            *,
            quality_override: str | None = None,
        ) -> None:
            max_points = profile.criteria[criterion]
            quality = quality_override or readiness_text_quality(text)
            awarded_points = initial_readiness_points(max_points, quality)
            assessment: dict[str, object] = {
                "max_points": max_points,
                "awarded_points": awarded_points,
                "artifact_quality": quality,
                "evidence": [{"artifact": artifact}],
            }
            if section:
                assessment["evidence"] = [{"artifact": artifact, "section": section}]
            if quality in {"missing", "placeholder"}:
                missing.append(criterion)
                suggested_next.append(f"add_{criterion}")
            elif quality == "thin":
                suggested_next.append(f"strengthen_{criterion}")
            elif quality == "needs_owner_input":
                failed_gates.append(f"{criterion}:needs_owner_input")
                suggested_next.append(f"resolve_{criterion}")
            criteria[criterion] = assessment

        add_criterion("problem_clarity", "proposal.md", "Problem", read_markdown_section(proposal_text, "Problem"))
        add_criterion("goal_clarity", "proposal.md", "Goals", read_markdown_section(proposal_text, "Goals"))
        scope_text = "\n".join(
            item
            for item in (
                read_markdown_section(proposal_text, "Non-Goals"),
                _read_optional(proposal_dir / "suggested-scope.md"),
            )
            if item
        )
        add_criterion("scope_boundaries", "proposal.md", "Non-Goals", scope_text)
        alternatives_text = _read_optional(proposal_dir / "alternatives.md")
        add_criterion("alternatives_quality", "alternatives.md", None, alternatives_text)
        add_criterion("tradeoff_analysis", "alternatives.md", None, alternatives_text + "\n" + _read_optional(proposal_dir / "findings.md"))
        add_criterion("risk_coverage", "risks.md", None, _read_optional(proposal_dir / "risks.md"))
        add_criterion("assumptions_clarity", "assumptions.md", None, _read_optional(proposal_dir / "assumptions.md"))
        questions_text = _read_optional(proposal_dir / "open-questions.md")
        question_quality = readiness_text_quality(questions_text)
        if question_quality in {"meaningful", "ready"} and count_open_questions(questions_text) > 0:
            question_quality = "needs_owner_input"
        add_criterion("owner_questions_resolution", "open-questions.md", None, questions_text, quality_override=question_quality)
        acceptance_text = "\n".join(
            item
            for item in (
                read_markdown_section(proposal_text, "Acceptance Criteria"),
                _read_optional(proposal_dir / "execution-plan.md"),
            )
            if item
        )
        add_criterion("acceptance_criteria_quality", "proposal.md", "Acceptance Criteria", acceptance_text)
        add_criterion("impact_overlap_analysis", "impact-map.yml", None, _read_optional(proposal_dir / "impact-map.yml"))

        readiness = {
            "status": "assessed",
            "profile_id": profile.profile_id,
            "profile_version": profile.version,
            "tier": "medium",
            "confidence": "low",
            "confidence_reasons": [
                "Initial readiness was bootstrapped from proposal artifacts.",
                "Review criterion evidence before using it for acceptance.",
            ],
            "missing": unique_strings(missing),
            "suggested_next": unique_strings(suggested_next),
            "failed_gates": unique_strings(failed_gates),
            "criteria": criteria,
        }
        self.write(proposal_id, refresh_readiness_payload(readiness, profile))
        return self.read(proposal_id)


def validate_readiness_profile_payload(data: dict[str, object]) -> None:
    profile = data.get("readiness_profile")
    if not isinstance(profile, dict):
        raise ValueError("Readiness profile must define top-level `readiness_profile` mapping.")
    profile_id = str(profile.get("id") or "").strip()
    version = str(profile.get("version") or "").strip()
    if not profile_id:
        raise ValueError("Readiness profile missing id.")
    if not version:
        raise ValueError("Readiness profile missing version.")
    criteria = profile.get("criteria")
    if not isinstance(criteria, dict) or not criteria:
        raise ValueError("Readiness profile must define criteria.")
    total = 0
    for criterion, points in criteria.items():
        if not str(criterion).strip():
            raise ValueError("Readiness profile contains empty criterion name.")
        if not isinstance(points, int) or points <= 0:
            raise ValueError(f"Readiness criterion must have positive integer points: {criterion}")
        total += points
    if total != 100:
        raise ValueError(f"Readiness criteria must total 100 points, got {total}.")
    thresholds = profile.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("Readiness profile must define thresholds.")
    for label in READINESS_LABELS:
        value = thresholds.get(label)
        if not isinstance(value, int) or value < 0 or value > 100:
            raise ValueError(f"Readiness threshold must be 0-100 integer: {label}")
    for tier, requirement in dict(profile.get("tier_requirements") or {}).items():
        if tier not in READINESS_TIERS:
            raise ValueError(f"Invalid readiness tier: {tier}")
        if not isinstance(requirement, dict):
            raise ValueError(f"Readiness tier requirement must be a mapping: {tier}")
        confidence = requirement.get("required_confidence")
        if confidence is not None and confidence not in READINESS_CONFIDENCE_LEVELS:
            raise ValueError(f"Invalid readiness confidence for tier {tier}: {confidence}")
    for state, cap in dict(profile.get("artifact_quality_caps") or {}).items():
        if state not in READINESS_ARTIFACT_QUALITY_STATES:
            raise ValueError(f"Invalid artifact quality state: {state}")
        if not isinstance(cap, dict):
            raise ValueError(f"Artifact quality cap must be a mapping: {state}")


def validate_readiness_assessment_payload(data: dict[str, object]) -> None:
    readiness = data.get("readiness")
    if not isinstance(readiness, dict):
        raise ValueError("Readiness assessment must define top-level `readiness` mapping.")
    status = str(readiness.get("status") or "assessed")
    if status == "not_assessed":
        return
    if not str(readiness.get("profile_id") or "").strip():
        raise ValueError("Readiness assessment missing profile_id.")
    if not str(readiness.get("profile_version") or "").strip():
        raise ValueError("Readiness assessment missing profile_version.")
    if "computed_score" in readiness:
        score = readiness["computed_score"]
        if not isinstance(score, int) or score < 0 or score > 100:
            raise ValueError("Readiness computed_score must be an integer from 0 to 100.")
    label = readiness.get("computed_label")
    if label is not None and label not in READINESS_LABELS:
        raise ValueError(f"Invalid readiness computed_label: {label}")
    confidence = readiness.get("confidence")
    if confidence is not None and confidence not in READINESS_CONFIDENCE_LEVELS:
        raise ValueError(f"Invalid readiness confidence: {confidence}")
    tier = readiness.get("tier")
    if tier is not None and tier not in READINESS_TIERS:
        raise ValueError(f"Invalid readiness tier: {tier}")
    for key in ("failed_gates", "missing", "suggested_next", "confidence_reasons"):
        value = readiness.get(key, [])
        if value is not None and not isinstance(value, list):
            raise ValueError(f"Readiness field must be a list: {key}")
    criteria = readiness.get("criteria") or {}
    if criteria and not isinstance(criteria, dict):
        raise ValueError("Readiness criteria must be a mapping.")
    for criterion, assessment in dict(criteria).items():
        if not str(criterion).strip():
            raise ValueError("Readiness criteria contains empty criterion name.")
        if not isinstance(assessment, dict):
            raise ValueError(f"Readiness criterion assessment must be a mapping: {criterion}")
        artifact_quality = assessment.get("artifact_quality")
        if artifact_quality is not None and artifact_quality not in READINESS_ARTIFACT_QUALITY_STATES:
            raise ValueError(f"Invalid artifact quality for criterion {criterion}: {artifact_quality}")
        awarded = assessment.get("awarded_points")
        if awarded is not None and (not isinstance(awarded, int) or awarded < 0):
            raise ValueError(f"Readiness awarded_points must be a non-negative integer: {criterion}")


def refresh_readiness_payload(readiness: dict[str, object], profile: ReadinessProfile) -> dict[str, object]:
    criteria = readiness.get("criteria") or {}
    if not isinstance(criteria, dict):
        criteria = {}
    refreshed_criteria: dict[str, object] = {}
    missing = [str(item) for item in readiness.get("missing") or []]
    suggested_next = [str(item) for item in readiness.get("suggested_next") or []]
    failed_gates = [str(item) for item in readiness.get("failed_gates") or []]
    computed_score = 0
    for criterion, max_points in profile.criteria.items():
        assessment = dict(criteria.get(criterion) or {})
        if criterion not in criteria:
            missing.append(criterion)
            suggested_next.append(f"assess_{criterion}")
            assessment = {"max_points": max_points, "awarded_points": 0, "artifact_quality": "missing"}
        artifact_quality = str(assessment.get("artifact_quality") or "missing")
        awarded_points = assessment.get("awarded_points")
        if not isinstance(awarded_points, int):
            awarded_points = 0
        effective_points = readiness_effective_points(
            awarded_points=awarded_points,
            max_points=max_points,
            artifact_quality=artifact_quality,
            profile=profile,
        )
        if artifact_quality == "needs_owner_input":
            failed_gates.append(f"{criterion}:needs_owner_input")
        assessment["max_points"] = max_points
        assessment["effective_points"] = effective_points
        refreshed_criteria[criterion] = assessment
        computed_score += effective_points
    refreshed = dict(readiness)
    refreshed["status"] = "assessed"
    refreshed["profile_id"] = profile.profile_id
    refreshed["profile_version"] = profile.version
    refreshed["computed_score"] = min(computed_score, 100)
    refreshed["computed_label"] = readiness_label(computed_score, profile.thresholds)
    refreshed["missing"] = unique_strings(missing)
    refreshed["suggested_next"] = unique_strings(suggested_next)
    refreshed["failed_gates"] = unique_strings(failed_gates)
    refreshed["criteria"] = refreshed_criteria
    refreshed["computed_at"] = date.today().isoformat()
    return refreshed


def readiness_effective_points(*, awarded_points: int, max_points: int, artifact_quality: str, profile: ReadinessProfile) -> int:
    cap = profile.artifact_quality_caps.get(artifact_quality) if isinstance(profile.artifact_quality_caps, dict) else None
    cap_percent = cap.get("max_score_percent") if isinstance(cap, dict) else 0
    cap_points = int(max_points * int(cap_percent or 0) / 100)
    return max(0, min(awarded_points, max_points, cap_points))


def readiness_label(score: int, thresholds: dict[str, int]) -> str:
    label = "weak"
    for candidate, threshold in sorted(thresholds.items(), key=lambda item: item[1]):
        if score >= threshold:
            label = candidate
    return label


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def readiness_text_quality(text: str | None) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return "missing"
    lower = stripped.lower()
    placeholders = (
        "not provided.",
        "not explored yet.",
        "none identified yet.",
        "not suggested yet.",
        "findings: []",
        "pending.",
        "not generated yet.",
        "none recorded yet.",
        "tasks: []",
    )
    if any(placeholder in lower for placeholder in placeholders):
        return "placeholder"
    content_lines = [line.strip() for line in stripped.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    content_text = " ".join(content_lines)
    if len(content_text) < 80:
        return "thin"
    return "meaningful"


def initial_readiness_points(max_points: int, quality: str) -> int:
    if quality in {"missing", "placeholder"}:
        return 0
    if quality == "thin":
        return max(1, int(max_points * 0.5))
    if quality in {"meaningful", "needs_owner_input"}:
        return max(1, int(max_points * 0.75))
    if quality == "ready":
        return max_points
    return 0


def count_open_questions(text: str) -> int:
    count = 0
    for line in text.splitlines():
        if re.match(r"^(\d+\.|-|\*)\s+.+\?", line.strip()):
            count += 1
    return count

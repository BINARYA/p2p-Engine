from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import read_markdown_section, read_title
from p2p_engine.core.proposal_artifact_state import (
    ProposalArtifactConfirmation,
    ProposalArtifactExpectation,
    ProposalArtifactStatus,
)
from p2p_engine.services.proposal_artifact_state import (
    ARTIFACT_STATE_FILENAME,
    validate_proposal_artifact_state_payload,
)
from p2p_engine.services.proposal_questions import QUESTION_STATE_FILENAME, validate_proposal_questions_payload

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
    owner_question_state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ProposalReadinessReview:
    proposal_id: str
    readiness: ProposalReadiness
    question_state_status: str
    owner_question_state: dict[str, object]
    challenge_points: list[str]
    owner_questions: list[str]
    thin_artifact_warnings: list[str]
    alternative_prompts: list[str]
    tradeoff_prompts: list[str]
    acceptance_cautions: list[str]
    assertiveness_guidance: list[str]
    suggested_next: list[str]
    merge_candidates: list[str]


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
                suggested_next=[f"p2p proposal readiness init {proposal_id}"],
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
            owner_question_state=_readiness_owner_question_state(readiness),
        )

    def write(self, proposal_id: str, readiness: dict[str, object]) -> Path:
        proposal_dir = self.find_proposal_dir(proposal_id)
        payload = {"readiness": readiness}
        validate_readiness_assessment_payload(payload)
        path = proposal_dir / "readiness.yml"
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return path.relative_to(self.root)

    def record_override(self, proposal_id: str, reason: str, approver: str) -> Path:
        candidate = self.render_override_candidate(
            proposal_id,
            reason=reason,
            approver=approver,
            recorded_on=date.today().isoformat(),
        )
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "readiness.yml"
        path.write_bytes(candidate)
        return path.relative_to(self.root)

    def render_override_candidate(
        self,
        proposal_id: str,
        *,
        reason: str,
        approver: str,
        recorded_on: str,
    ) -> bytes:
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
        readiness["override_recorded_at"] = recorded_on
        payload = {"readiness": readiness}
        validate_readiness_assessment_payload(payload)
        return _yaml_dump(payload).encode("utf-8")

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
        add_criterion(
            "scope_boundaries",
            "proposal.md",
            "Non-Goals",
            scope_text,
            quality_override=readiness_evidence_quality(
                read_markdown_section(proposal_text, "Non-Goals"),
                _read_optional(proposal_dir / "suggested-scope.md"),
            ),
        )
        alternatives_text = _read_optional(proposal_dir / "alternatives.md")
        add_criterion("alternatives_quality", "alternatives.md", None, alternatives_text)
        findings_text = _read_optional(proposal_dir / "findings.md")
        add_criterion(
            "tradeoff_analysis",
            "alternatives.md",
            None,
            alternatives_text + "\n" + findings_text,
            quality_override=readiness_evidence_quality(alternatives_text, findings_text),
        )
        add_criterion("risk_coverage", "risks.md", None, _read_optional(proposal_dir / "risks.md"))
        add_criterion("assumptions_clarity", "assumptions.md", None, _read_optional(proposal_dir / "assumptions.md"))
        owner_question_state = _owner_question_state(proposal_dir)
        if owner_question_state.get("source") == "structured":
            question_quality = "needs_owner_input" if _owner_question_blockers(owner_question_state) else "meaningful"
            question_evidence_text = _owner_question_state_text(owner_question_state)
        else:
            question_quality = "missing"
            question_evidence_text = ""
        add_criterion(
            "owner_questions_resolution",
            "questions.yml",
            None,
            question_evidence_text,
            quality_override=question_quality,
        )
        acceptance_primary = read_markdown_section(proposal_text, "Acceptance Criteria")
        acceptance_supplemental = _read_optional(proposal_dir / "execution-plan.md")
        acceptance_text = "\n".join(
            item
            for item in (acceptance_primary, acceptance_supplemental)
            if item
        )
        add_criterion(
            "acceptance_criteria_quality",
            "proposal.md",
            "Acceptance Criteria",
            acceptance_text,
            quality_override=readiness_evidence_quality(acceptance_primary, acceptance_supplemental),
        )
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
            "owner_question_state": owner_question_state,
        }
        self.write(proposal_id, refresh_readiness_payload(readiness, profile))
        return self.read(proposal_id)

    def assess(self, proposal_id: str) -> ProposalReadiness:
        existing_override = self._owner_override_fields(proposal_id)
        initialized = self.initialize(proposal_id)
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "readiness.yml"
        data = _read_yaml_mapping(path, default={})
        validate_readiness_assessment_payload(data)
        readiness = dict(data["readiness"])
        criteria = dict(readiness.get("criteria") or {})
        owner_question_state = _owner_question_state(proposal_dir)
        blocking_owner_questions = _owner_question_blockers(owner_question_state)
        soft_owner_question_notes = _owner_question_soft_notes(owner_question_state)
        owner_question_suggested = _owner_question_suggested_next(owner_question_state, proposal_id)
        artifact_gaps, artifact_warnings, artifact_suggested = _artifact_state_readiness_gaps(proposal_dir)
        has_blockers = bool(initialized.missing or initialized.failed_gates or blocking_owner_questions or artifact_gaps)

        if not has_blockers:
            for criterion, assessment_value in criteria.items():
                assessment = dict(assessment_value)
                if assessment.get("artifact_quality") == "meaningful":
                    assessment["artifact_quality"] = "ready"
                    assessment["awarded_points"] = int(assessment.get("max_points") or 0)
                    evidence = list(assessment.get("evidence") or [])
                    evidence.append({"artifact": "questions.yml", "reason": "artifact evidence assessed with no unresolved blocking questions"})
                    assessment["evidence"] = evidence
                criteria[criterion] = assessment
            readiness["confidence"] = "medium" if soft_owner_question_notes else "high"
            readiness["confidence_reasons"] = unique_strings(
                [
                    "Evidence-aware assessment found no missing criteria, failed gates, blocking owner questions, or artifact coverage gaps.",
                    "Criterion evidence was recalculated from current proposal artifacts.",
                    *soft_owner_question_notes,
                ]
            )
        else:
            readiness["confidence"] = "medium" if not initialized.missing and not initialized.failed_gates else "low"
            reasons = ["Evidence-aware assessment recalculated current artifacts."]
            if blocking_owner_questions:
                failed_gates = list(readiness.get("failed_gates") or [])
                failed_gates.append("owner_questions_resolution:needs_owner_input")
                readiness["failed_gates"] = unique_strings([str(item) for item in failed_gates])
                reasons.append(
                    "Blocking owner questions remain: "
                    + ", ".join(str(item.get("id") or "") for item in blocking_owner_questions)
                    + "."
                )
            reasons.extend(soft_owner_question_notes)
            if artifact_gaps:
                reasons.append("Artifact-aware coverage has unresolved required or applicable gaps.")
            readiness["confidence_reasons"] = unique_strings(reasons)

        readiness["assessment_source"] = "evidence_aware"
        readiness["assessed_at"] = date.today().isoformat()
        readiness["criteria"] = criteria
        readiness["missing"] = unique_strings([*list(readiness.get("missing") or []), *artifact_gaps])
        readiness["suggested_next"] = unique_strings(
            [*list(readiness.get("suggested_next") or []), *owner_question_suggested, *artifact_suggested]
        )
        readiness["artifact_coverage_warnings"] = unique_strings(artifact_warnings)
        readiness["owner_question_state"] = owner_question_state
        readiness.update(existing_override)
        self.write(proposal_id, refresh_readiness_payload(readiness, self.profile(str(readiness.get("profile_id") or DEFAULT_READINESS_PROFILE_ID))))
        return self.read(proposal_id)

    def review(self, proposal_id: str) -> ProposalReadinessReview:
        readiness = self.read(proposal_id)
        proposal_dir = self.find_proposal_dir(proposal_id)
        question_state_status = "not_initialized"
        questions_path = proposal_dir / QUESTION_STATE_FILENAME
        if questions_path.exists():
            validate_proposal_questions_payload(_read_yaml_mapping(questions_path, default={}))
            question_state_status = "initialized"
        owner_question_state = _owner_question_state(proposal_dir)

        challenge_points = [f"Resolve readiness gap: {item}" for item in readiness.missing]
        challenge_points.extend(f"Resolve failed gate: {gate}" for gate in readiness.failed_gates)
        owner_questions: list[str] = []
        if question_state_status == "not_initialized" and _readiness_needs_guidance(readiness):
            owner_questions.append(
                f"Question state is not initialized. Run `p2p proposal questions init {proposal_id}` "
                "and add focused questions for the highest-impact readiness gaps."
            )
        for item in owner_question_state.get("blocking_owner_questions") or []:
            if isinstance(item, dict):
                owner_questions.append(
                    f"{item.get('id')} ({item.get('priority')}/{item.get('state')}): {item.get('question')}"
                )
        for item in owner_question_state.get("residual_follow_up") or []:
            if isinstance(item, dict):
                owner_questions.append(
                    f"Residual follow-up {item.get('id')} ({item.get('priority')}/{item.get('state')}): {item.get('question')}"
                )
        for item in owner_question_state.get("answered_not_applied") or []:
            if isinstance(item, dict):
                challenge_points.append(f"Apply answered proposal question: {item.get('id')}")
        for item in readiness.missing:
            owner_questions.append(f"What information is needed to close `{item}` for {proposal_id}?")

        thin_artifact_warnings: list[str] = []
        if readiness.confidence == "low":
            thin_artifact_warnings.append("Readiness confidence is low; do not treat this proposal as methodologically ready.")
        thin_artifact_warnings.extend(str(item) for item in owner_question_state.get("confidence_notes") or [])
        artifact_gaps, artifact_warnings, artifact_suggested = _artifact_state_readiness_gaps(proposal_dir)
        challenge_points.extend(f"Resolve artifact coverage gap: {gap}" for gap in artifact_gaps)
        thin_artifact_warnings.extend(artifact_warnings)
        alternative_prompts = []
        if "alternatives_quality" in readiness.missing:
            alternative_prompts.append("Identify at least two viable alternatives and explain why one should be preferred.")
        tradeoff_prompts = []
        if "tradeoff_analysis" in readiness.missing:
            tradeoff_prompts.append("Compare benefits, costs, risks, and compatibility impact for each alternative.")
        acceptance_cautions = []
        if _readiness_needs_guidance(readiness):
            acceptance_cautions.append(
                "Do not recommend acceptance without either resolving these gaps or recording an explicit owner readiness override."
            )

        suggested_next = list(readiness.suggested_next)
        if question_state_status == "not_initialized" and _readiness_needs_guidance(readiness):
            suggested_next.insert(0, f"p2p proposal questions init {proposal_id}")
        assertiveness_guidance = stepped_assertiveness_guidance(readiness, question_state_status)
        if _readiness_needs_guidance(readiness):
            suggested_next.append(f"p2p proposal readiness assess {proposal_id}")
        suggested_next.extend(_owner_question_suggested_next(owner_question_state, proposal_id))
        suggested_next.extend(artifact_suggested)
        suggested_next.append(f"p2p proposal questions next {proposal_id}")
        return ProposalReadinessReview(
            proposal_id=proposal_id,
            readiness=readiness,
            question_state_status=question_state_status,
            owner_question_state=owner_question_state,
            challenge_points=unique_strings(challenge_points),
            owner_questions=unique_strings(owner_questions),
            thin_artifact_warnings=unique_strings(thin_artifact_warnings),
            alternative_prompts=unique_strings(alternative_prompts),
            tradeoff_prompts=unique_strings(tradeoff_prompts),
            acceptance_cautions=unique_strings(acceptance_cautions),
            assertiveness_guidance=unique_strings(assertiveness_guidance),
            suggested_next=unique_strings(suggested_next),
            merge_candidates=_merge_candidates(proposal_id, proposal_dir, self.p2p_dir),
        )

    def _owner_override_fields(self, proposal_id: str) -> dict[str, object]:
        path = self.find_proposal_dir(proposal_id) / "readiness.yml"
        if not path.exists():
            return {}
        data = _read_yaml_mapping(path, default={})
        validate_readiness_assessment_payload(data)
        readiness = data.get("readiness", {})
        if not isinstance(readiness, dict) or not readiness.get("owner_override"):
            return {}
        keys = (
            "owner_override",
            "effective_status",
            "effective_score",
            "override_reason",
            "override_approver",
            "override_recorded_at",
        )
        return {key: readiness[key] for key in keys if key in readiness}


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


def readiness_evidence_quality(primary: str | None, *supplemental: str | None) -> str:
    primary_quality = readiness_text_quality(primary)
    supplemental_qualities = [readiness_text_quality(item) for item in supplemental]
    return aggregate_readiness_qualities(primary_quality, supplemental_qualities)


def aggregate_readiness_qualities(primary_quality: str, supplemental_qualities: list[str]) -> str:
    qualities = [primary_quality, *supplemental_qualities]
    if primary_quality in {"meaningful", "ready"}:
        return primary_quality
    if any(quality in {"meaningful", "ready"} for quality in supplemental_qualities):
        return "meaningful"
    if primary_quality == "thin" or any(quality == "thin" for quality in supplemental_qualities):
        return "thin"
    if any(quality == "placeholder" for quality in qualities):
        return "placeholder"
    return "missing"


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


def _readiness_owner_question_state(readiness: dict[str, object]) -> dict[str, object]:
    state = readiness.get("owner_question_state")
    if isinstance(state, dict):
        return _normalized_owner_question_state(state)
    return _empty_owner_question_state()


def _empty_owner_question_state(*, source: str = "none") -> dict[str, object]:
    return {
        "source": source,
        "blocking_owner_questions": [],
        "answered_not_applied": [],
        "residual_follow_up": [],
        "closed_questions": [],
        "confidence_notes": [],
        "suggested_next": [],
    }


def _normalized_owner_question_state(state: dict[str, object]) -> dict[str, object]:
    normalized = _empty_owner_question_state(source=str(state.get("source") or "none"))
    for key in (
        "blocking_owner_questions",
        "answered_not_applied",
        "residual_follow_up",
        "closed_questions",
        "confidence_notes",
        "suggested_next",
    ):
        value = state.get(key) or []
        normalized[key] = value if isinstance(value, list) else []
    return normalized


def _owner_question_state(proposal_dir: Path) -> dict[str, object]:
    questions_path = proposal_dir / QUESTION_STATE_FILENAME
    if not questions_path.exists():
        return _empty_owner_question_state(source="missing")

    data = _read_yaml_mapping(questions_path, default={})
    validate_proposal_questions_payload(data)
    state = data.get("proposal_questions", {})
    if not isinstance(state, dict):
        return _empty_owner_question_state(source="structured")

    summary = _empty_owner_question_state(source="structured")
    groups_by_id = {
        str(group.get("id") or ""): group
        for group in state.get("groups") or []
        if isinstance(group, dict)
    }
    for question in state.get("questions") or []:
        if not isinstance(question, dict):
            continue
        group = groups_by_id.get(str(question.get("group_id") or ""), {})
        _classify_structured_question(summary, question, group if isinstance(group, dict) else {})
    return summary


def _classify_structured_question(summary: dict[str, object], question: dict[str, object], group: dict[str, object]) -> None:
    state = str(question.get("state") or "to_answer")
    group_state = str(group.get("state") or "to_answer")
    priority = str(question.get("priority") or "medium")
    question_id = str(question.get("id") or "")
    if state == "answered" and question.get("applied_to_proposal") is True and str(question.get("applied_at") or "").strip():
        summary["closed_questions"].append(
            _question_ref(question, group, reason="Answered question already has a durable applied marker.")
        )
        return
    if state in {"applied", "retired", "superseded"}:
        summary["closed_questions"].append(
            _question_ref(question, group, reason=f"Question is closed with state `{state}`.")
        )
        return
    if state == "answered":
        summary["answered_not_applied"].append(
            _question_ref(question, group, reason="Owner answer exists and still needs application to proposal artifacts.")
        )
        summary["confidence_notes"].append(f"Answered proposal question needs application: {question_id}.")
        summary["suggested_next"].append("apply_answered_questions")
        return
    if group_state in {"muted", "defer"}:
        summary["residual_follow_up"].append(
            _question_ref(question, group, reason=f"Question group is `{group_state}` and is non-blocking.")
        )
        summary["confidence_notes"].append(f"Question {question_id} is non-blocking because group is {group_state}.")
        return
    if state in {"muted", "defer"}:
        summary["residual_follow_up"].append(
            _question_ref(question, group, reason=f"Question state is `{state}` and is non-blocking.")
        )
        summary["confidence_notes"].append(f"Question {question_id} is non-blocking because state is {state}.")
        return
    if state == "to_answer" and priority == "high":
        summary["blocking_owner_questions"].append(
            _question_ref(question, group, reason="High-priority structured question is still to_answer.")
        )
        summary["confidence_notes"].append(f"High-priority owner question remains to_answer: {question_id}.")
        summary["suggested_next"].append("ask_blocking_owner_question")
        return
    if state == "to_answer":
        summary["residual_follow_up"].append(
            _question_ref(question, group, reason="Medium/low structured question is residual follow-up by default.")
        )
        summary["confidence_notes"].append(f"Residual owner follow-up remains: {question_id}.")
        summary["suggested_next"].append("ask_residual_owner_question")


def _question_ref(question: dict[str, object], group: dict[str, object], *, reason: str) -> dict[str, object]:
    return {
        "id": str(question.get("id") or ""),
        "group_id": str(question.get("group_id") or ""),
        "priority": str(question.get("priority") or "medium"),
        "state": str(question.get("state") or "to_answer"),
        "group_state": str(group.get("state") or ""),
        "criterion": str(question.get("criterion") or ""),
        "gap": str(question.get("gap") or ""),
        "question": str(question.get("question") or ""),
        "reason": reason,
    }


def _owner_question_blockers(owner_question_state: dict[str, object]) -> list[dict[str, object]]:
    return [
        item
        for item in owner_question_state.get("blocking_owner_questions") or []
        if isinstance(item, dict)
    ]


def _owner_question_soft_notes(owner_question_state: dict[str, object]) -> list[str]:
    return [str(item) for item in owner_question_state.get("confidence_notes") or []]


def _owner_question_suggested_next(owner_question_state: dict[str, object], proposal_id: str) -> list[str]:
    suggestions: list[str] = []
    for item in owner_question_state.get("suggested_next") or []:
        key = str(item)
        if key == "apply_answered_questions":
            suggestions.append(f"p2p proposal questions apply {proposal_id}")
        elif key in {"ask_blocking_owner_question", "ask_residual_owner_question"}:
            suggestions.append(f"p2p proposal questions next {proposal_id}")
        elif key == "resolve_owner_questions_resolution":
            suggestions.append("resolve_owner_questions_resolution")
        elif key:
            suggestions.append(key)
    return unique_strings(suggestions)


def _owner_question_state_text(owner_question_state: dict[str, object]) -> str:
    lines = [
        f"source: {owner_question_state.get('source')}",
    ]
    for key in (
        "blocking_owner_questions",
        "answered_not_applied",
        "residual_follow_up",
        "closed_questions",
    ):
        values = [item for item in owner_question_state.get(key) or [] if isinstance(item, dict)]
        if not values:
            lines.append(f"{key}: none")
            continue
        lines.append(f"{key}:")
        lines.extend(
            f"- {item.get('id')} {item.get('priority')}/{item.get('state')}: {item.get('reason')}"
            for item in values
        )
    notes = [str(item) for item in owner_question_state.get("confidence_notes") or []]
    if notes:
        lines.append("confidence_notes:")
        lines.extend(f"- {item}" for item in notes)
    return "\n".join(lines)


def stepped_assertiveness_guidance(readiness: ProposalReadiness, question_state_status: str) -> list[str]:
    score = readiness.computed_score
    if score is None or readiness.failed_gates or (score is not None and score < 70):
        guidance = [
            "assertiveness: high",
            "Agent must challenge missing evidence, initialize or resume proposal questions, ask the next focused question, and avoid recommending acceptance without owner override.",
        ]
    elif score < 85 or readiness.confidence == "low":
        guidance = [
            "assertiveness: focused",
            "Agent should continue targeted follow-up on high-impact gaps, apply answered questions to artifacts, and run readiness assess after changes.",
        ]
    elif score < 95 or readiness.confidence == "medium":
        guidance = [
            "assertiveness: residual",
            "Agent should ask only residual high-value questions or request confirmation before recommending owner decision.",
        ]
    else:
        guidance = [
            "assertiveness: confirmation",
            "Agent may summarize evidence and remind that the owner still controls accept, reject, defer, merge, and override decisions.",
        ]
    if question_state_status == "not_initialized" and (score is None or score < 85 or readiness.confidence == "low"):
        guidance.append("question_state: initialize proposal questions before returning a passive summary.")
    return guidance


def _artifact_state_readiness_gaps(proposal_dir: Path) -> tuple[list[str], list[str], list[str]]:
    path = proposal_dir / ARTIFACT_STATE_FILENAME
    proposal_id = _proposal_id_from_path(proposal_dir)
    if not path.exists():
        return (
            ["Current proposal artifact state is missing."],
            [],
            [f"p2p proposal artifact init {proposal_id}"],
        )
    data = _read_yaml_mapping(path, default={})
    validate_proposal_artifact_state_payload(data)
    state = data.get("proposal_artifacts", {})
    if not isinstance(state, dict):
        return [], [], []
    gaps: list[str] = []
    warnings: list[str] = []
    suggested: list[str] = []
    artifacts = state.get("artifacts") or []
    if not isinstance(artifacts, list):
        return [], [], []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        artifact_id = str(item.get("id") or "")
        expectation = str(item.get("expectation") or "")
        status = str(item.get("status") or "")
        reason = str(item.get("reason") or "")
        confirmation = str(item.get("confirmation") or "")
        is_required = expectation == ProposalArtifactExpectation.required.value
        is_applicable = expectation == ProposalArtifactExpectation.required_when_applicable.value
        if (is_required or is_applicable) and status in {
            ProposalArtifactStatus.unknown.value,
            ProposalArtifactStatus.missing.value,
            ProposalArtifactStatus.weak.value,
            ProposalArtifactStatus.deferred.value,
        }:
            gaps.append(f"artifact:{artifact_id}:{status}")
            suggested.append(f"p2p proposal artifact status {proposal_id}")
        if is_required and status in {
            ProposalArtifactStatus.deferred.value,
            ProposalArtifactStatus.not_applicable.value,
        } and confirmation != ProposalArtifactConfirmation.owner_confirmed.value:
            warnings.append(
                f"Artifact {artifact_id} is {status} for a required artifact and is not owner-confirmed. Reason: {reason or 'none'}"
            )
            suggested.append(f"p2p proposal artifact confirm {proposal_id} {artifact_id} --actor owner")
    return unique_strings(gaps), unique_strings(warnings), unique_strings(suggested)


def _proposal_id_from_path(proposal_dir: Path) -> str:
    match = re.match(r"^(PROP-\d{3})-", proposal_dir.name)
    return match.group(1) if match else "PROP-XXX"


def _merge_candidates(proposal_id: str, proposal_dir: Path, p2p_dir: Path) -> list[str]:
    proposals_dir = p2p_dir / "proposals"
    proposal_text = _read_optional(proposal_dir / "proposal.md")
    target_tokens = _proposal_similarity_tokens(proposal_text)
    if not target_tokens or not proposals_dir.exists():
        return []
    candidates: list[str] = []
    for other_dir in sorted(proposals_dir.iterdir()):
        if not other_dir.is_dir() or other_dir == proposal_dir:
            continue
        other_id = "-".join(other_dir.name.split("-", 2)[:2])
        if other_id == proposal_id:
            continue
        other_text = _read_optional(other_dir / "proposal.md")
        other_tokens = _proposal_similarity_tokens(other_text)
        shared = sorted(target_tokens & other_tokens)
        if len(shared) < 4:
            continue
        title = read_title(other_text) or other_dir.name
        candidates.append(f"{other_id}: possible overlap with {title} (shared terms: {', '.join(shared[:6])})")
    return candidates


def _proposal_similarity_tokens(text: str) -> set[str]:
    title = read_title(text) or ""
    proposal = read_markdown_section(text, "Proposal") or ""
    problem = read_markdown_section(text, "Problem") or ""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{4,}", f"{title} {problem} {proposal}".lower())
    stopwords = {
        "proposal",
        "project",
        "system",
        "should",
        "would",
        "could",
        "there",
        "their",
        "state",
        "readiness",
        "engine",
        "p2p",
    }
    return {word for word in words if word not in stopwords}


def _readiness_needs_guidance(readiness: ProposalReadiness) -> bool:
    return (
        readiness.computed_score is None
        or readiness.computed_score < 85
        or bool(readiness.failed_gates)
        or bool(readiness.missing)
        or readiness.confidence == "low"
    )

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from p2p_engine.foundation.files import identity_slug, read_yaml_mapping, relative_to_root
from p2p_engine.services.choices import ChoiceDetail
from p2p_engine.services.governance import VoteStatus, vote_status_from_data
from p2p_engine.services.permissions import ACTOR_KINDS, PERMISSION_ROLES, PermissionsService

PREFLIGHT_SCHEMA_VERSION = "governance-preflight/v1"
GOVERNANCE_MODES = {"owner_decides", "open_consensus", "exclusive_vote"}


@dataclass(frozen=True)
class GovernanceDiagnostic:
    code: str
    severity: str
    message: str
    source: str = ""
    overrideable: bool = False
    suggested_command: str = ""


@dataclass(frozen=True)
class GovernanceTarget:
    type: str
    id: str
    title: str
    path: str


@dataclass(frozen=True)
class GovernanceContext:
    mode: str
    source: str
    defaulted: bool


@dataclass(frozen=True)
class ResolvedGovernanceActor:
    id: str
    role: str
    kind: str
    display_name: str
    source: str
    fallback: bool = False


@dataclass(frozen=True)
class GovernanceSelection:
    requested_option: str
    resolved_option: str | None
    valid: bool


@dataclass(frozen=True)
class GovernanceDecisionResult:
    status: str
    owner_final: bool
    can_finalize_normally: bool
    owner_override_allowed: bool
    override_rationale_required: bool


@dataclass(frozen=True)
class VoteSummary:
    proposal_id: str | None
    counts: dict[str, int]
    total_votes: int
    winner: str | None
    tied: bool
    alignment: str


@dataclass(frozen=True)
class ExplicitBlockerSummary:
    source: str
    target_type: str
    target: str
    reason: str
    status: str


@dataclass(frozen=True)
class PrecedentMatch:
    precedent_id: str
    source: str
    match_reason: str
    related_target: str
    title: str
    proposal: str


@dataclass(frozen=True)
class GovernancePreflightResult:
    schema_version: str
    target: GovernanceTarget
    governance: GovernanceContext
    actor: ResolvedGovernanceActor
    selection: GovernanceSelection
    result: GovernanceDecisionResult
    blocking_errors: list[GovernanceDiagnostic]
    warnings: list[GovernanceDiagnostic]
    vote_summary: VoteSummary
    blockers: list[ExplicitBlockerSummary]
    precedents: list[PrecedentMatch]


@dataclass(frozen=True)
class GovernanceValidationFinding:
    code: str
    severity: str
    path: Path
    message: str
    suggested_command: str = ""


@dataclass(frozen=True)
class GovernanceValidationResult:
    ok: bool
    errors: int
    warnings: int
    infos: int
    findings: list[GovernanceValidationFinding]


class GovernancePolicyService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        permissions: PermissionsService,
        show_choice: Callable[[str], ChoiceDetail],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.permissions = permissions
        self.show_choice = show_choice

    def choice_preflight(
        self,
        choice_id: str,
        *,
        option: str,
        actor: str,
        precedent_id: str | None = None,
        tag: str | None = None,
    ) -> GovernancePreflightResult:
        diagnostics: list[GovernanceDiagnostic] = []
        warnings: list[GovernanceDiagnostic] = []
        choice = self.show_choice(choice_id)
        governance = self._governance_context(diagnostics, warnings)
        actor_context = self._resolve_actor(actor, diagnostics, warnings)
        selection = self._resolve_selection(choice, option, diagnostics)
        vote_summary = self._vote_summary(choice, selection, diagnostics, warnings)
        blockers = self._active_blockers(choice, diagnostics)
        try:
            precedents = self.search_precedents(
                precedent_id=precedent_id,
                proposal_id=vote_summary.proposal_id,
                choice_id=choice.choice_id,
                tag=tag,
            )
        except (ValueError, yaml.YAMLError) as exc:
            diagnostics.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_MALFORMED_PRECEDENTS",
                    severity="error",
                    message=str(exc),
                    source=str(relative_to_root(self.p2p_dir / "governance" / "decision-precedents.yml", self.root)),
                )
            )
            precedents = []
        if precedents:
            warnings.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_RELATED_PRECEDENTS",
                    severity="warning",
                    message="Explicit related decision precedents were found.",
                    source=precedents[0].source,
                )
            )

        if actor_context.role != "owner":
            diagnostics.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_NON_OWNER_ACTOR",
                    severity="error",
                    message=f"Actor is not allowed to make owner-controlled decisions: {actor_context.id}",
                    source=actor_context.source,
                    suggested_command="p2p permissions show",
                )
            )

        if blockers:
            diagnostics.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_ACTIVE_BLOCKER",
                    severity="error",
                    message="Active explicit blockers prevent normal finalization.",
                    source=blockers[0].source,
                    overrideable=True,
                    suggested_command=f"p2p choice show {choice.choice_id}",
                )
            )

        blocking_errors = sorted(diagnostics, key=lambda item: (item.code, item.source, item.message))
        warnings = sorted(warnings, key=lambda item: (item.code, item.source, item.message))
        result = self._decision_result(blocking_errors, actor_context)
        return GovernancePreflightResult(
            schema_version=PREFLIGHT_SCHEMA_VERSION,
            target=GovernanceTarget(
                type="choice",
                id=choice.choice_id,
                title=choice.title,
                path=str(choice.path),
            ),
            governance=governance,
            actor=actor_context,
            selection=selection,
            result=result,
            blocking_errors=blocking_errors,
            warnings=warnings,
            vote_summary=vote_summary,
            blockers=blockers,
            precedents=precedents,
        )

    def search_precedents(
        self,
        *,
        precedent_id: str | None = None,
        proposal_id: str | None = None,
        choice_id: str | None = None,
        tag: str | None = None,
    ) -> list[PrecedentMatch]:
        path = self.p2p_dir / "governance" / "decision-precedents.yml"
        data = read_yaml_mapping(path, default={"precedents": []})
        precedents = data.get("precedents", [])
        if not isinstance(precedents, list):
            raise ValueError("Invalid decision-precedents.yml: expected `precedents` list.")

        matches: list[PrecedentMatch] = []
        for precedent in precedents:
            if not isinstance(precedent, dict):
                continue
            current_id = str(precedent.get("id") or "").strip()
            reasons = self._precedent_match_reasons(
                precedent,
                precedent_id=precedent_id,
                proposal_id=proposal_id,
                choice_id=choice_id,
                tag=tag,
            )
            for reason, target in reasons:
                matches.append(
                    PrecedentMatch(
                        precedent_id=current_id,
                        source=str(relative_to_root(path, self.root)),
                        match_reason=reason,
                        related_target=target,
                        title=str(precedent.get("title") or ""),
                        proposal=str(precedent.get("proposal") or ""),
                    )
                )
        return sorted(matches, key=lambda item: (item.precedent_id, item.match_reason, item.related_target))

    def validate_governance(self) -> GovernanceValidationResult:
        findings: list[GovernanceValidationFinding] = []

        def add(code: str, severity: str, path: Path, message: str, suggested_command: str = "") -> None:
            findings.append(
                GovernanceValidationFinding(
                    code=code,
                    severity=severity,
                    path=relative_to_root(path, self.root),
                    message=message,
                    suggested_command=suggested_command,
                )
            )

        self._validate_governance_file(add)
        self._validate_roles_file(add)
        self._validate_precedents_file(add)
        self._validate_votes(add)

        findings = sorted(findings, key=lambda item: (item.code, str(item.path), item.message))
        errors = sum(1 for finding in findings if finding.severity == "error")
        warnings = sum(1 for finding in findings if finding.severity == "warning")
        infos = sum(1 for finding in findings if finding.severity == "info")
        return GovernanceValidationResult(
            ok=errors == 0,
            errors=errors,
            warnings=warnings,
            infos=infos,
            findings=findings,
        )

    def validation_findings(self) -> list[tuple[str, str, Path, str, str]]:
        return [
            (
                finding.code,
                finding.severity,
                self.root / finding.path if not finding.path.is_absolute() else finding.path,
                finding.message,
                finding.suggested_command,
            )
            for finding in self.validate_governance().findings
        ]

    def _governance_context(
        self,
        diagnostics: list[GovernanceDiagnostic],
        warnings: list[GovernanceDiagnostic],
    ) -> GovernanceContext:
        path = self.p2p_dir / "governance" / "governance.yml"
        if not path.exists():
            warnings.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_MISSING_OPTIONAL_GOVERNANCE",
                    severity="warning",
                    message="Governance mode is not configured; defaulting to owner_decides.",
                    source=str(relative_to_root(path, self.root)),
                )
            )
            return GovernanceContext(mode="owner_decides", source=str(relative_to_root(path, self.root)), defaulted=True)
        try:
            payload = read_yaml_mapping(path, default={})
        except (ValueError, yaml.YAMLError) as exc:
            diagnostics.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_MALFORMED_GOVERNANCE",
                    severity="error",
                    message=str(exc),
                    source=str(relative_to_root(path, self.root)),
                )
            )
            return GovernanceContext(mode="invalid", source=str(relative_to_root(path, self.root)), defaulted=False)
        governance = payload.get("governance", {})
        if not isinstance(governance, dict):
            diagnostics.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_MALFORMED_GOVERNANCE",
                    severity="error",
                    message="governance.yml must define governance mapping.",
                    source=str(relative_to_root(path, self.root)),
                )
            )
            return GovernanceContext(mode="invalid", source=str(relative_to_root(path, self.root)), defaulted=False)
        mode = str(governance.get("mode") or "owner_decides")
        if mode not in GOVERNANCE_MODES:
            diagnostics.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_UNSUPPORTED_MODE",
                    severity="error",
                    message=f"Unsupported governance mode: {mode}",
                    source=str(relative_to_root(path, self.root)),
                )
            )
        return GovernanceContext(mode=mode, source=str(relative_to_root(path, self.root)), defaulted=False)

    def _resolve_actor(
        self,
        actor: str,
        diagnostics: list[GovernanceDiagnostic],
        warnings: list[GovernanceDiagnostic],
    ) -> ResolvedGovernanceActor:
        actor_id = identity_slug(actor)
        permissions_path = self.permissions.path()
        legacy_role = self._legacy_role_for_actor(actor_id)
        if permissions_path.exists():
            try:
                payload = self.permissions.show()
            except (ValueError, yaml.YAMLError) as exc:
                diagnostics.append(
                    GovernanceDiagnostic(
                        code="P2P_GOV_MALFORMED_PERMISSIONS",
                        severity="error",
                        message=str(exc),
                        source=str(relative_to_root(permissions_path, self.root)),
                    )
                )
                return self._unknown_actor(actor_id, str(relative_to_root(permissions_path, self.root)))
            identities = payload.get("identities", {})
            identity = identities.get(actor_id) if isinstance(identities, dict) else None
            if not isinstance(identity, dict):
                diagnostics.append(
                    GovernanceDiagnostic(
                        code="P2P_GOV_UNKNOWN_ACTOR",
                        severity="error",
                        message=f"Actor not found in permissions policy: {actor_id}",
                        source=str(relative_to_root(permissions_path, self.root)),
                        suggested_command=f"p2p permissions actor add {actor_id}",
                    )
                )
                return self._unknown_actor(actor_id, str(relative_to_root(permissions_path, self.root)))
            role = str(identity.get("role") or "")
            kind = str(identity.get("kind") or "")
            if role not in PERMISSION_ROLES:
                diagnostics.append(
                    GovernanceDiagnostic(
                        code="P2P_GOV_INVALID_PERMISSION_ROLE",
                        severity="error",
                        message=f"Invalid permission role for {actor_id}: {role}",
                        source=str(relative_to_root(permissions_path, self.root)),
                    )
                )
            if kind not in ACTOR_KINDS:
                diagnostics.append(
                    GovernanceDiagnostic(
                        code="P2P_GOV_INVALID_ACTOR_KIND",
                        severity="error",
                        message=f"Invalid actor kind for {actor_id}: {kind}",
                        source=str(relative_to_root(permissions_path, self.root)),
                    )
                )
            if legacy_role and legacy_role != role:
                warnings.append(
                    GovernanceDiagnostic(
                        code="P2P_GOV_ROLE_MISMATCH",
                        severity="warning",
                        message=(
                            f"Legacy governance role for {actor_id} is {legacy_role}, "
                            f"but permissions.yml says {role}."
                        ),
                        source=str(relative_to_root(self.p2p_dir / "governance" / "roles.yml", self.root)),
                    )
                )
            return ResolvedGovernanceActor(
                id=actor_id,
                role=role,
                kind=kind,
                display_name=str(identity.get("display_name") or actor_id),
                source=str(relative_to_root(permissions_path, self.root)),
            )

        if legacy_role:
            warnings.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_LEGACY_ROLE_FALLBACK",
                    severity="warning",
                    message="Actor role resolved from legacy governance roles because permissions.yml is absent.",
                    source=str(relative_to_root(self.p2p_dir / "governance" / "roles.yml", self.root)),
                )
            )
            return ResolvedGovernanceActor(
                id=actor_id,
                role=legacy_role,
                kind="person",
                display_name=actor_id,
                source=str(relative_to_root(self.p2p_dir / "governance" / "roles.yml", self.root)),
                fallback=True,
            )
        diagnostics.append(
            GovernanceDiagnostic(
                code="P2P_GOV_UNKNOWN_ACTOR",
                severity="error",
                message=f"Actor cannot be resolved: {actor_id}",
                source=str(relative_to_root(permissions_path, self.root)),
                suggested_command=f"p2p permissions actor add {actor_id}",
            )
        )
        return self._unknown_actor(actor_id, str(relative_to_root(permissions_path, self.root)))

    def _unknown_actor(self, actor_id: str, source: str) -> ResolvedGovernanceActor:
        return ResolvedGovernanceActor(
            id=actor_id,
            role="unknown",
            kind="unknown",
            display_name=actor_id,
            source=source,
        )

    def _legacy_role_for_actor(self, actor_id: str) -> str | None:
        path = self.p2p_dir / "governance" / "roles.yml"
        if not path.exists():
            return None
        try:
            payload = read_yaml_mapping(path, default={"roles": []})
        except (ValueError, yaml.YAMLError):
            return None
        roles = payload.get("roles", [])
        if not isinstance(roles, list):
            return None
        for role in roles:
            if not isinstance(role, dict):
                continue
            role_id = str(role.get("id") or "").strip()
            if not role_id:
                continue
            if identity_slug(role_id) == actor_id:
                return str(role.get("role") or role.get("id") or "")
        return None

    def _resolve_selection(
        self,
        choice: ChoiceDetail,
        requested_option: str,
        diagnostics: list[GovernanceDiagnostic],
    ) -> GovernanceSelection:
        requested = str(requested_option or "").strip()
        resolved = self._choice_option_id(choice, requested)
        valid = resolved is not None
        if not valid:
            diagnostics.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_INVALID_SELECTION",
                    severity="error",
                    message=f"Choice option not found: {requested}",
                    source=str(choice.path / "options.yml"),
                )
            )
        return GovernanceSelection(requested_option=requested, resolved_option=resolved, valid=valid)

    def _choice_option_id(self, choice: ChoiceDetail, value: str) -> str | None:
        wanted = str(value or "").strip().lower()
        for option in choice.options:
            if not isinstance(option, dict):
                continue
            option_id = str(option.get("id") or "").strip()
            option_title = str(option.get("title") or "").strip()
            if wanted in {option_id.lower(), option_title.lower(), f"{option_id} - {option_title}".lower()}:
                return option_id
        return None

    def _vote_summary(
        self,
        choice: ChoiceDetail,
        selection: GovernanceSelection,
        diagnostics: list[GovernanceDiagnostic],
        warnings: list[GovernanceDiagnostic],
    ) -> VoteSummary:
        proposal_id = self._first_related_proposal(choice)
        if proposal_id is None:
            return VoteSummary(
                proposal_id=None,
                counts={},
                total_votes=0,
                winner=None,
                tied=False,
                alignment="not_applicable",
            )
        votes_path = self._proposal_votes_path(proposal_id)
        try:
            data = read_yaml_mapping(
                votes_path,
                default={"proposal": proposal_id, "votes": [], "result": {}},
            )
            status = vote_status_from_data(proposal_id, data)
        except (ValueError, yaml.YAMLError) as exc:
            diagnostics.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_MALFORMED_VOTES",
                    severity="error",
                    message=str(exc),
                    source=str(relative_to_root(votes_path, self.root)),
                )
            )
            status = VoteStatus(proposal_id=proposal_id, counts={}, total_votes=0, winner=None, tied=False)
        alignment = self._vote_alignment(status, selection)
        if alignment == "conflicts":
            warnings.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_VOTE_CONFLICT",
                    severity="warning",
                    message="Selected option differs from advisory vote winner.",
                    source=str(relative_to_root(votes_path, self.root)),
                )
            )
        elif alignment == "tied":
            warnings.append(
                GovernanceDiagnostic(
                    code="P2P_GOV_VOTE_TIE",
                    severity="warning",
                    message="Advisory votes are tied.",
                    source=str(relative_to_root(votes_path, self.root)),
                )
            )
        return VoteSummary(
            proposal_id=proposal_id,
            counts={key: status.counts[key] for key in sorted(status.counts)},
            total_votes=status.total_votes,
            winner=status.winner,
            tied=status.tied,
            alignment=alignment,
        )

    def _vote_alignment(self, status: VoteStatus, selection: GovernanceSelection) -> str:
        if status.total_votes == 0:
            return "no_votes"
        if status.tied:
            return "tied"
        if not selection.resolved_option or not status.winner:
            return "not_applicable"
        return "aligned" if selection.resolved_option == status.winner else "conflicts"

    def _first_related_proposal(self, choice: ChoiceDetail) -> str | None:
        for item in choice.related_proposals:
            if isinstance(item, dict):
                proposal_id = str(item.get("proposal") or item.get("id") or "").strip()
                if proposal_id:
                    return proposal_id
        return None

    def _proposal_votes_path(self, proposal_id: str) -> Path:
        proposals_dir = self.p2p_dir / "proposals"
        for path in sorted(proposals_dir.iterdir()) if proposals_dir.exists() else []:
            if path.is_dir() and path.name.startswith(f"{proposal_id}-"):
                return path / "votes.yml"
        return proposals_dir / proposal_id / "votes.yml"

    def _active_blockers(
        self,
        choice: ChoiceDetail,
        diagnostics: list[GovernanceDiagnostic],
    ) -> list[ExplicitBlockerSummary]:
        blockers: list[ExplicitBlockerSummary] = []
        for block in choice.blocks:
            if not isinstance(block, dict):
                diagnostics.append(
                    GovernanceDiagnostic(
                        code="P2P_GOV_MALFORMED_BLOCKER",
                        severity="error",
                        message="Choice blocker must be a mapping.",
                        source=str(choice.path / "links.yml"),
                    )
                )
                continue
            if str(block.get("status") or "active") != "active":
                continue
            blockers.append(
                ExplicitBlockerSummary(
                    source=str(choice.path / "links.yml"),
                    target_type=str(block.get("target_type") or ""),
                    target=str(block.get("target") or ""),
                    reason=str(block.get("reason") or ""),
                    status=str(block.get("status") or "active"),
                )
            )
        return sorted(blockers, key=lambda item: (item.target_type, item.target, item.reason))

    def _decision_result(
        self,
        blocking_errors: list[GovernanceDiagnostic],
        actor: ResolvedGovernanceActor,
    ) -> GovernanceDecisionResult:
        non_overrideable = [item for item in blocking_errors if not item.overrideable]
        overrideable = [item for item in blocking_errors if item.overrideable]
        if non_overrideable:
            status = "blocked"
        elif overrideable and actor.role == "owner":
            status = "requires_owner_override"
        elif overrideable:
            status = "blocked"
        else:
            status = "ready"
        return GovernanceDecisionResult(
            status=status,
            owner_final=True,
            can_finalize_normally=status == "ready",
            owner_override_allowed=status == "requires_owner_override",
            override_rationale_required=status == "requires_owner_override",
        )

    def _precedent_match_reasons(
        self,
        precedent: dict[str, object],
        *,
        precedent_id: str | None,
        proposal_id: str | None,
        choice_id: str | None,
        tag: str | None,
    ) -> list[tuple[str, str]]:
        reasons: list[tuple[str, str]] = []
        current_id = str(precedent.get("id") or "").strip()
        if precedent_id and current_id == precedent_id:
            reasons.append(("precedent_id", precedent_id))
        proposal_refs = self._string_refs(precedent, "proposal", "proposals", "related_proposals")
        if proposal_id and proposal_id in proposal_refs:
            reasons.append(("related_proposal", proposal_id))
        choice_refs = self._string_refs(precedent, "choice", "choices", "related_choices")
        if choice_id and choice_id in choice_refs:
            reasons.append(("related_choice", choice_id))
        tag_refs = self._string_refs(precedent, "tag", "tags")
        if tag and tag in tag_refs:
            reasons.append(("tag", tag))
        return reasons

    def _string_refs(self, data: dict[str, object], *keys: str) -> set[str]:
        refs: set[str] = set()
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                refs.add(value.strip())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.strip():
                        refs.add(item.strip())
                    elif isinstance(item, dict):
                        ref = str(item.get("id") or item.get("proposal") or item.get("choice") or "").strip()
                        if ref:
                            refs.add(ref)
        return refs

    def _validate_governance_file(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        path = self.p2p_dir / "governance" / "governance.yml"
        if not path.exists():
            return
        try:
            payload = read_yaml_mapping(path, default={})
        except (ValueError, yaml.YAMLError) as exc:
            add("P2P250_INVALID_GOVERNANCE_MODE", "error", path, str(exc), "")
            return
        governance = payload.get("governance", {})
        if not isinstance(governance, dict):
            add("P2P250_INVALID_GOVERNANCE_MODE", "error", path, "governance.yml must define governance mapping.", "")
            return
        mode = str(governance.get("mode") or "owner_decides")
        if mode not in GOVERNANCE_MODES:
            add("P2P250_INVALID_GOVERNANCE_MODE", "error", path, f"Unsupported governance mode: {mode}", "")

    def _validate_roles_file(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        path = self.p2p_dir / "governance" / "roles.yml"
        if not path.exists():
            return
        try:
            payload = read_yaml_mapping(path, default={"roles": []})
        except (ValueError, yaml.YAMLError) as exc:
            add("P2P251_INVALID_GOVERNANCE_ROLES", "error", path, str(exc), "")
            return
        roles = payload.get("roles", [])
        if not isinstance(roles, list):
            add("P2P251_INVALID_GOVERNANCE_ROLES", "error", path, "roles.yml must define roles list.", "")
            return
        for role in roles:
            if not isinstance(role, dict) or not str(role.get("id") or "").strip():
                add("P2P251_INVALID_GOVERNANCE_ROLES", "error", path, "Each role must be a mapping with id.", "")

    def _validate_precedents_file(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        path = self.p2p_dir / "governance" / "decision-precedents.yml"
        if not path.exists():
            return
        try:
            payload = read_yaml_mapping(path, default={"precedents": []})
        except (ValueError, yaml.YAMLError) as exc:
            add("P2P252_INVALID_DECISION_PRECEDENTS", "error", path, str(exc), "")
            return
        precedents = payload.get("precedents", [])
        if not isinstance(precedents, list):
            add("P2P252_INVALID_DECISION_PRECEDENTS", "error", path, "decision-precedents.yml must define precedents list.", "")
            return
        seen: set[str] = set()
        for precedent in precedents:
            if not isinstance(precedent, dict):
                add("P2P252_INVALID_DECISION_PRECEDENTS", "error", path, "Each precedent must be a mapping.", "")
                continue
            precedent_id = str(precedent.get("id") or "").strip()
            if not precedent_id:
                add("P2P252_INVALID_DECISION_PRECEDENTS", "error", path, "Each precedent must define id.", "")
                continue
            if precedent_id in seen:
                add("P2P252_DUPLICATE_DECISION_PRECEDENT", "error", path, f"Duplicate decision precedent id: {precedent_id}", "")
            seen.add(precedent_id)

    def _validate_votes(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        for path in sorted(self.p2p_dir.glob("proposals/*/votes.yml")):
            try:
                payload = read_yaml_mapping(path, default={})
                proposal_id = str(payload.get("proposal") or _artifact_id_from_dir(path.parent.name))
                vote_status_from_data(proposal_id, payload)
            except (ValueError, yaml.YAMLError) as exc:
                add("P2P253_INVALID_GOVERNANCE_VOTES", "error", path, str(exc), "")


def _artifact_id_from_dir(name: str) -> str:
    parts = name.split("-", 2)
    if len(parts) >= 2 and parts[0].isalpha() and parts[1].isdigit():
        return f"{parts[0]}-{parts[1]}"
    return name

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from p2p_engine.core.choices import is_terminal_choice_state
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAuthorityResolution,
    ProposalDecisionBindingStatus,
    ProposalDecisionLifecycleView,
)
from p2p_engine.core.software_spec_lifecycle import (
    SPEC_LIFECYCLE_INTENTS,
    SpecLifecycleDiagnostic,
    SpecLifecycleRoute,
    SpecLifecycleView,
)
from p2p_engine.foundation.markdown import read_frontmatter

ROUTES: dict[str, SpecLifecycleRoute] = {
    "chat_exploration": SpecLifecycleRoute(
        intent="chat_exploration",
        route="discuss_missing_fields",
        write_class="chat_only",
        persistent_artifact="none",
        canonical_status="not_persisted",
        writes_state=False,
        preconditions=["No persistent write is required."],
        suggested_commands=["p2p project context --format json"],
        next_step="Discuss missing specification ingredients before writing durable files.",
    ),
    "project_definition": SpecLifecycleRoute(
        intent="project_definition",
        route="use_vertical_context_and_definition_state",
        write_class="p2p_canonical",
        persistent_artifact="project_definition_or_proposal_artifacts",
        canonical_status="governed_p2p_state",
        writes_state=True,
        preconditions=["Inspect active vertical and project definition state."],
        suggested_commands=[
            "p2p project context --format json",
            "p2p project definition show --format json",
        ],
        next_step="Capture missing project definition through supported P2P primitives.",
    ),
    "architecture_comparison": SpecLifecycleRoute(
        intent="architecture_comparison",
        route="create_choices_or_competing_proposals",
        write_class="p2p_canonical",
        persistent_artifact="choice_or_proposal_artifacts",
        canonical_status="governed_p2p_state",
        writes_state=True,
        preconditions=["Alternatives need explicit proposal or choice records before they become project memory."],
        suggested_commands=["p2p choice discover", "p2p proposal create \"Architecture Option\""],
        next_step="Represent alternatives as choices or competing proposals.",
    ),
    "implementation_spec": SpecLifecycleRoute(
        intent="implementation_spec",
        route="preflight_change_set_then_refresh_software_spec",
        write_class="p2p_generated_narrative",
        persistent_artifact="p2p_native_software_spec",
        canonical_status="downstream_from_governed_p2p_state",
        writes_state=True,
        preconditions=[
            "A Change Set exists.",
            "The Change Set references accepted or explicitly provisional P2P sources.",
            "Known blocking choices are resolved.",
        ],
        suggested_commands=["p2p change show CHANGE-XXX", "p2p spec refresh --change CHANGE-XXX"],
        next_step="Run preflight, then refresh the P2P-native software spec.",
    ),
    "downstream_export": SpecLifecycleRoute(
        intent="downstream_export",
        route="preflight_spec_then_export_target",
        write_class="generated_export",
        persistent_artifact="target_export",
        canonical_status="derived_export",
        writes_state=True,
        preconditions=[
            "A P2P-native software spec exists.",
            "Implementation-spec preflight has no blockers.",
        ],
        suggested_commands=[
            "p2p spec refresh --change CHANGE-XXX",
            "p2p spec export --change CHANGE-XXX --target TARGET",
        ],
        next_step="Generate the target export from the P2P-native software spec.",
    ),
    "exact_file_request": SpecLifecycleRoute(
        intent="exact_file_request",
        route="write_exact_requested_file_with_policy_preview",
        write_class="stable_documentation",
        persistent_artifact="explicit_repository_or_external_file",
        canonical_status="not_p2p_governed_unless_imported_or_declared",
        writes_state=True,
        preconditions=["The owner specified exact operation, path, artifact kind, and durable destination."],
        suggested_commands=["p2p explore import --help"],
        next_step="Write only the exact requested file or route through a supported P2P import.",
    ),
}


class SoftwareSpecLifecycleService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_change_dir: Callable[[str], Path],
        show_proposal: Callable[[str], Any],
        active_project_vertical: Callable[[], Any],
        project_definition_view: Callable[[], Any],
        choice_statuses: Callable[[], list[Any]],
        show_choice: Callable[[str], Any],
        proposal_lifecycle_status: (
            Callable[[str], ProposalDecisionLifecycleView] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_change_dir = find_change_dir
        self.show_proposal = show_proposal
        self.active_project_vertical = active_project_vertical
        self.project_definition_view = project_definition_view
        self.choice_statuses = choice_statuses
        self.show_choice = show_choice
        self.proposal_lifecycle_status = proposal_lifecycle_status

    def lifecycle(
        self,
        intent: str = "implementation_spec",
        *,
        change_id: str | None = None,
        target: str | None = None,
    ) -> SpecLifecycleView:
        route = self._route(intent)
        blockers: list[SpecLifecycleDiagnostic] = []
        advisories: list[SpecLifecycleDiagnostic] = []
        commands = list(route.suggested_commands)
        normalized_change = (change_id or "").strip()
        normalized_target = (target or "").strip()

        if route.intent in {"implementation_spec", "downstream_export"}:
            if not normalized_change:
                blockers.append(
                    SpecLifecycleDiagnostic(
                        code="missing_change_id",
                        severity="blocker",
                        message="A Change Set ID is required for implementation spec lifecycle preflight.",
                        suggested_command="p2p change status",
                    )
                )
            else:
                blockers.extend(self._change_source_blockers(normalized_change))
                blockers.extend(self._choice_blockers(normalized_change))
                advisories.extend(self._software_vertical_advisories())
                commands = self._commands_for_change(route.intent, normalized_change, normalized_target)

        return SpecLifecycleView(
            intent=route.intent,
            route=route.route,
            write_class=route.write_class,
            persistent_artifact=route.persistent_artifact,
            canonical_status=route.canonical_status,
            writes_state=route.writes_state,
            change_id=normalized_change,
            target=normalized_target,
            blockers=blockers,
            advisories=advisories,
            preconditions=list(route.preconditions),
            suggested_commands=commands,
            next_step=route.next_step,
        )

    def ensure_can_write(
        self,
        intent: str,
        *,
        change_id: str,
        target: str | None = None,
    ) -> SpecLifecycleView:
        view = self.lifecycle(intent, change_id=change_id, target=target)
        if view.blockers:
            first = view.blockers[0]
            raise ValueError(
                f"Software spec lifecycle preflight failed: {first.code}: {first.message}"
                + (f" Suggested command: {first.suggested_command}" if first.suggested_command else "")
            )
        return view

    def _route(self, intent: str) -> SpecLifecycleRoute:
        normalized = intent.strip().lower()
        if normalized not in ROUTES:
            raise ValueError(f"Unsupported software spec lifecycle intent `{intent}`. Allowed: {', '.join(SPEC_LIFECYCLE_INTENTS)}")
        return ROUTES[normalized]

    def _change_source_blockers(self, change_id: str) -> list[SpecLifecycleDiagnostic]:
        try:
            change_dir = self.find_change_dir(change_id)
        except ValueError:
            return [
                SpecLifecycleDiagnostic(
                    code="change_not_found",
                    severity="blocker",
                    message=f"Change Set {change_id} does not exist.",
                    artifact_id=change_id,
                    suggested_command="p2p change status",
                )
            ]

        text = (change_dir / "change.md").read_text(encoding="utf-8") if (change_dir / "change.md").exists() else ""
        frontmatter = read_frontmatter(text)
        source = frontmatter.get("source")
        if not isinstance(source, dict):
            source = {}
        accepted_proposals = [str(item) for item in source.get("accepted_proposals", []) if str(item).strip()] if isinstance(source.get("accepted_proposals"), list) else []
        if not accepted_proposals:
            return [
                SpecLifecycleDiagnostic(
                    code="missing_governed_source",
                    severity="blocker",
                    message=f"Change Set {change_id} has no accepted proposal source.",
                    artifact_id=change_id,
                    suggested_command=f"p2p change show {change_id}",
                )
            ]

        blockers: list[SpecLifecycleDiagnostic] = []
        for proposal_id in accepted_proposals:
            if self.proposal_lifecycle_status is not None:
                try:
                    lifecycle = self.proposal_lifecycle_status(proposal_id)
                except ValueError:
                    lifecycle = None
                if lifecycle is None:
                    blockers.append(
                        SpecLifecycleDiagnostic(
                            code="source_proposal_not_found",
                            severity="blocker",
                            message=(
                                f"Source proposal {proposal_id} referenced by "
                                f"{change_id} was not found."
                            ),
                            artifact_id=proposal_id,
                            suggested_command=f"p2p proposal show {proposal_id}",
                        )
                    )
                    continue
                if (
                    lifecycle.authority_resolution
                    != ProposalDecisionAuthorityResolution.resolved
                ):
                    blockers.append(
                        SpecLifecycleDiagnostic(
                            code="source_authority_unresolved",
                            severity="blocker",
                            message=(
                                f"Source proposal {proposal_id} authority is "
                                f"{lifecycle.authority_resolution.value}."
                            ),
                            artifact_id=proposal_id,
                            suggested_command=(
                                f"p2p decision status {proposal_id}"
                            ),
                        )
                    )
                    continue
                if not lifecycle.active:
                    blockers.append(
                        SpecLifecycleDiagnostic(
                            code="source_decision_inactive",
                            severity="blocker",
                            message=(
                                f"Source proposal {proposal_id} is now "
                                f"`{lifecycle.effective_state.value}`; existing "
                                "spec artifacts remain historical and must not "
                                "be overwritten by normal refresh."
                            ),
                            artifact_id=proposal_id,
                            suggested_command=f"p2p change show {change_id}",
                        )
                    )
                    continue
                if (
                    lifecycle.proposal_binding_status
                    != ProposalDecisionBindingStatus.current
                ):
                    blockers.append(
                        SpecLifecycleDiagnostic(
                            code="source_proposal_binding_diverged",
                            severity="blocker",
                            message=(
                                f"Source proposal {proposal_id} semantic binding "
                                f"is {lifecycle.proposal_binding_status.value}."
                            ),
                            artifact_id=proposal_id,
                            suggested_command=(
                                f"p2p decision status {proposal_id}"
                            ),
                        )
                    )
                continue
            try:
                proposal = self.show_proposal(proposal_id)
            except ValueError:
                blockers.append(
                    SpecLifecycleDiagnostic(
                        code="source_proposal_not_found",
                        severity="blocker",
                        message=f"Source proposal {proposal_id} referenced by {change_id} was not found.",
                        artifact_id=proposal_id,
                        suggested_command=f"p2p proposal show {proposal_id}",
                    )
                )
                continue
            if getattr(proposal, "status", "") not in {
                "accepted",
                "accepted_with_changes",
            }:
                blockers.append(
                    SpecLifecycleDiagnostic(
                        code="source_not_accepted",
                        severity="blocker",
                        message=f"Source proposal {proposal_id} is `{getattr(proposal, 'status', 'unknown')}`, not accepted.",
                        artifact_id=proposal_id,
                        suggested_command=f"p2p proposal show {proposal_id}",
                    )
                )
        return blockers

    def _choice_blockers(self, change_id: str) -> list[SpecLifecycleDiagnostic]:
        blockers: list[SpecLifecycleDiagnostic] = []
        for choice in self.choice_statuses():
            if is_terminal_choice_state(getattr(choice, "status", "")):
                continue
            detail = self.show_choice(getattr(choice, "choice_id"))
            for block in getattr(detail, "blocks", []):
                if not isinstance(block, dict):
                    continue
                if block.get("status", "active") != "active":
                    continue
                if block.get("target_type") == "change" and block.get("target") == change_id:
                    choice_id = getattr(choice, "choice_id")
                    blockers.append(
                        SpecLifecycleDiagnostic(
                            code="blocking_choice_unresolved",
                            severity="blocker",
                            message=f"{choice_id} blocks {change_id}: {block.get('reason') or 'choice must be resolved first'}.",
                            artifact_id=choice_id,
                            suggested_command=f"p2p choice show {choice_id}",
                        )
                    )
        return blockers

    def _software_vertical_advisories(self) -> list[SpecLifecycleDiagnostic]:
        advisories: list[SpecLifecycleDiagnostic] = []
        try:
            active = self.active_project_vertical()
        except ValueError as exc:
            return [
                SpecLifecycleDiagnostic(
                    code="project_vertical_unavailable",
                    severity="advisory",
                    message=str(exc),
                    suggested_command="p2p project vertical list",
                )
            ]
        if getattr(active, "vertical_id", "") != "software_project":
            advisories.append(
                SpecLifecycleDiagnostic(
                    code="software_vertical_not_active",
                    severity="advisory",
                    message="The active project vertical is not `software_project`; software spec ingredients may be incomplete.",
                    artifact_id=str(getattr(active, "vertical_id", "")),
                    suggested_command="p2p project vertical select software_project --actor owner",
                )
            )

        definition = self.project_definition_view()
        state = getattr(definition, "state", None)
        if not getattr(definition, "exists", False) or state is None:
            advisories.append(
                SpecLifecycleDiagnostic(
                    code="project_definition_missing",
                    severity="advisory",
                    message="Project definition state is not initialized.",
                    suggested_command="p2p project definition show --format json",
                )
            )
            return advisories
        missing = sum(len(getattr(section, "missing_required_fields", [])) for section in getattr(state, "sections", []))
        if missing:
            advisories.append(
                SpecLifecycleDiagnostic(
                    code="project_definition_incomplete",
                    severity="advisory",
                    message=f"Project definition has {missing} missing required field(s).",
                    suggested_command="p2p project definition show --format json",
                )
            )
        return advisories

    def _commands_for_change(self, intent: str, change_id: str, target: str) -> list[str]:
        commands = [f"p2p change show {change_id}"]
        if intent == "downstream_export":
            commands.append(f"p2p spec refresh --change {change_id}")
            commands.append(f"p2p spec export --change {change_id} --target {target or 'TARGET'}")
        else:
            commands.append(f"p2p spec refresh --change {change_id}")
        return commands

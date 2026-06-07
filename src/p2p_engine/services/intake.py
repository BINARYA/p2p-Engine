from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from p2p_engine.core.contribution import ContributionType
from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.validators import validate_yaml_key
from p2p_engine.foundation.markdown import read_title


@dataclass(frozen=True)
class IntakePrompt:
    intake_id: str
    path: Path
    prompt_path: Path


@dataclass(frozen=True)
class IntakeStatus:
    intake_id: str
    status: str
    path: Path
    recommendation: str


@dataclass(frozen=True)
class IntakeApplyPlan:
    intake_id: str
    path: Path
    actions: list[dict[str, object]]


@dataclass(frozen=True)
class IntakeAppliedAction:
    applied_id: str
    plan_action: str
    action_type: str
    target: str
    command: str
    path: Path


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _has_meaningful_intake_recommendation(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    normalized = re.sub(r"^#.*$", "", stripped, flags=re.MULTILINE).strip().lower()
    return bool(normalized and normalized != "pending.")


def _find_apply_plan_action(actions: list[object], action_id: str) -> dict[str, object] | None:
    for action in actions:
        if isinstance(action, dict) and action.get("id") == action_id:
            return action
    return None


def _intake_prompt_markdown(intake_id: str, idea: str, context: str) -> str:
    return (
        f"# P2P Intake Prompt - {intake_id}\n\n"
        "You are helping classify a raw idea against the current P2P project memory.\n\n"
        "## Governance Boundary\n\n"
        "Do not accept, reject, defer, merge or supersede proposals. "
        "Recommend next actions only. Final decisions must be recorded through P2P governance commands.\n\n"
        "## Raw Idea\n\n"
        f"{idea.strip()}\n\n"
        "## Project Context\n\n"
        f"{context}\n\n"
        "## Required Output\n\n"
        "Return artifacts with these shapes:\n\n"
        "### recommendation.md\n\n"
        "- classify the idea as new, duplicate, overlap, alternative, conflict, or unclear;\n"
        "- explain the rationale;\n"
        "- recommend exactly one primary next action.\n\n"
        "### related-proposals.yml\n\n"
        "```yaml\n"
        "related_proposals:\n"
        "  - proposal: PROP-000\n"
        "    relationship: related_to\n"
        "    rationale: Short reason.\n"
        "```\n\n"
        "### suggested-actions.yml\n\n"
        "```yaml\n"
        "suggested_actions:\n"
        "  - type: create_proposal | add_contribution | open_choice | record_conflict | defer | duplicate\n"
        "    target: PROP-000\n"
        "    rationale: Short reason.\n"
        "```\n"
    )


class IntakeLifecycleService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        registry_status: Callable[[], Any],
        intake_context: Callable[[Any], str],
        add_contribution: Callable[..., Any],
        create_choice: Callable[..., Any],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.registry_status = registry_status
        self.intake_context = intake_context
        self.add_contribution = add_contribution
        self.create_choice = create_choice

    def create_prompt(self, idea: str) -> IntakePrompt:
        intake_id = self._next_id()
        intake_dir = self.p2p_dir / "intake" / intake_id
        intake_dir.mkdir(parents=True, exist_ok=False)

        registry_status = self.registry_status()
        context = self.intake_context(registry_status)
        input_path = intake_dir / "input.md"
        context_path = intake_dir / "context.md"
        prompt_path = intake_dir / "intake.prompt.md"

        input_path.write_text(f"# Intake Input - {intake_id}\n\n{idea.strip()}\n", encoding="utf-8")
        context_path.write_text(context, encoding="utf-8")
        prompt_path.write_text(
            _intake_prompt_markdown(intake_id=intake_id, idea=idea, context=context),
            encoding="utf-8",
        )
        (intake_dir / "related-proposals.yml").write_text(
            _yaml_dump({"related_proposals": []}),
            encoding="utf-8",
        )
        (intake_dir / "suggested-actions.yml").write_text(
            _yaml_dump(
                {
                    "suggested_actions": [
                        {
                            "type": "needs_analysis",
                            "target": None,
                            "rationale": "Import intake output to populate recommendations.",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (intake_dir / "recommendation.md").write_text(
            f"# Recommendation - {intake_id}\n\nPending.\n",
            encoding="utf-8",
        )
        return IntakePrompt(
            intake_id=intake_id,
            path=intake_dir.relative_to(self.root),
            prompt_path=prompt_path.relative_to(self.root),
        )

    def import_output(self, intake_id: str, source: Path) -> list[Path]:
        intake_dir = self._find_dir(intake_id)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            mappings = {
                "recommendation.md": None,
                "related-proposals.yml": "related_proposals",
                "suggested-actions.yml": "suggested_actions",
                "context.md": None,
            }
            for filename, key in mappings.items():
                source_path = source / filename
                if source_path.exists():
                    if key is not None:
                        validate_yaml_key(source_path.read_text(encoding="utf-8"), key)
                    target = intake_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            target = intake_dir / "recommendation.md"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Intake source not found: {source}")
        if not imported:
            raise ValueError(f"No intake artifacts found in: {source}")
        return imported

    def statuses(self) -> list[IntakeStatus]:
        intake_dir = self.p2p_dir / "intake"
        statuses: list[IntakeStatus] = []
        for path in sorted(intake_dir.iterdir()) if intake_dir.exists() else []:
            if not path.is_dir():
                continue
            recommendation = _read_optional(path / "recommendation.md")
            has_recommendation = _has_meaningful_intake_recommendation(recommendation)
            statuses.append(
                IntakeStatus(
                    intake_id=path.name,
                    status="analyzed" if has_recommendation else "pending",
                    path=path.relative_to(self.root),
                    recommendation=read_title(recommendation) or "Recommendation pending",
                )
            )
        return statuses

    def create_apply_plan(self, intake_id: str) -> IntakeApplyPlan:
        intake_dir = self._find_dir(intake_id)
        suggested_path = intake_dir / "suggested-actions.yml"
        data = _read_yaml_mapping(suggested_path, default={"suggested_actions": []})
        suggested_actions = data.get("suggested_actions", [])
        if not isinstance(suggested_actions, list):
            raise ValueError("Invalid suggested-actions.yml: expected `suggested_actions` list.")

        plan_actions: list[dict[str, object]] = []
        for index, action in enumerate(suggested_actions, start=1):
            if not isinstance(action, dict):
                continue
            action_type = str(action.get("type") or "unknown")
            target = action.get("target")
            rationale = str(action.get("rationale") or "")
            support, status, command_preview, required_inputs = self._action_metadata(
                intake_id=intake_id,
                action_type=action_type,
                target=str(target) if target is not None else None,
                rationale=rationale,
            )
            plan_actions.append(
                {
                    "id": f"APPLY-{len(plan_actions) + 1:03d}",
                    "source_action_index": index,
                    "type": action_type,
                    "target": target,
                    "support": support,
                    "status": status,
                    "reason": rationale,
                    "command_preview": command_preview,
                    "required_inputs": required_inputs,
                }
            )

        plan_path = intake_dir / "apply-plan.yml"
        plan_path.write_text(
            _yaml_dump(
                {
                    "intake": intake_id,
                    "generated_on": date.today().isoformat(),
                    "apply_plan": plan_actions,
                }
            ),
            encoding="utf-8",
        )
        return IntakeApplyPlan(intake_id=intake_id, path=plan_path.relative_to(self.root), actions=plan_actions)

    def show_apply_plan(self, intake_id: str) -> IntakeApplyPlan:
        intake_dir = self._find_dir(intake_id)
        plan_path = intake_dir / "apply-plan.yml"
        if not plan_path.exists():
            raise ValueError("Intake apply plan not found. Run `p2p intake apply plan` first.")
        data = _read_yaml_mapping(plan_path, default={"apply_plan": []})
        actions = data.get("apply_plan", [])
        if not isinstance(actions, list):
            raise ValueError("Invalid apply-plan.yml: expected `apply_plan` list.")
        return IntakeApplyPlan(
            intake_id=intake_id,
            path=plan_path.relative_to(self.root),
            actions=[action for action in actions if isinstance(action, dict)],
        )

    def run_apply_action(
        self,
        intake_id: str,
        action_id: str,
        options: list[str] | None = None,
    ) -> IntakeAppliedAction:
        intake_dir = self._find_dir(intake_id)
        plan_path = intake_dir / "apply-plan.yml"
        if not plan_path.exists():
            raise ValueError("Intake apply plan not found. Run `p2p intake apply plan` first.")
        data = _read_yaml_mapping(plan_path, default={"apply_plan": []})
        plan_actions = data.get("apply_plan", [])
        if not isinstance(plan_actions, list):
            raise ValueError("Invalid apply-plan.yml: expected `apply_plan` list.")
        action = _find_apply_plan_action(plan_actions, action_id)
        if action is None:
            raise ValueError(f"Apply action not found: {action_id}")
        if action.get("status") == "applied":
            raise ValueError(f"Apply action already applied: {action_id}")

        action_type = str(action.get("type") or "")
        target = str(action.get("target") or "")
        reason = str(action.get("reason") or "")
        if action_type == "add_contribution":
            if not target.startswith("PROP-"):
                raise ValueError("add_contribution apply action requires a proposal target.")
            self.add_contribution(
                proposal_id=target,
                contribution_type=ContributionType.suggestion,
                text=reason or f"Applied from {intake_id}.",
                relevance_hint="medium",
                author=f"intake:{intake_id}",
            )
            command = f'p2p contribution add {target} "{reason}" --type suggestion --relevance medium'
        elif action_type == "open_choice":
            cleaned_options = [option.strip() for option in options or [] if option.strip()]
            if len(cleaned_options) < 2:
                raise ValueError("open_choice apply action requires at least two --option values.")
            related = [target] if target.startswith("PROP-") else []
            choice = self.create_choice(
                title=f"Intake {intake_id} choice for {target or 'project'}",
                options=cleaned_options,
                related=related,
                source=intake_id,
            )
            command = (
                "p2p choice create "
                f'--title "Intake {intake_id} choice for {target or "project"}" '
                + " ".join(f'--option "{option}"' for option in cleaned_options)
            )
            if related:
                command += f" --related {target}"
            command += f" --source {intake_id}"
            action["created_choice"] = choice.choice_id
        else:
            support = str(action.get("support") or "unsupported")
            raise ValueError(f"Apply action {action_id} is {support} and cannot be run by intake apply.")

        action["status"] = "applied"
        action["applied_on"] = date.today().isoformat()
        plan_path.write_text(_yaml_dump(data), encoding="utf-8")

        applied_path = intake_dir / "applied-actions.yml"
        applied_data = _read_yaml_mapping(applied_path, default={"applied_actions": []})
        applied_actions = applied_data.setdefault("applied_actions", [])
        if not isinstance(applied_actions, list):
            raise ValueError("Invalid applied-actions.yml: expected `applied_actions` list.")
        applied_id = f"APPLIED-{len(applied_actions) + 1:03d}"
        applied_record = {
            "id": applied_id,
            "intake": intake_id,
            "plan_action": action_id,
            "type": action_type,
            "target": target,
            "status": "applied",
            "command": command,
            "applied_on": date.today().isoformat(),
        }
        applied_actions.append(applied_record)
        applied_path.write_text(_yaml_dump(applied_data), encoding="utf-8")
        return IntakeAppliedAction(
            applied_id=applied_id,
            plan_action=action_id,
            action_type=action_type,
            target=target,
            command=command,
            path=applied_path.relative_to(self.root),
        )

    def _action_metadata(
        self,
        intake_id: str,
        action_type: str,
        target: str | None,
        rationale: str,
    ) -> tuple[str, str, str, list[str]]:
        if action_type == "add_contribution":
            command = (
                f'p2p contribution add {target or "PROP-000"} "{rationale}" '
                "--type suggestion --relevance medium"
            )
            return ("supported", "pending", command, [])
        if action_type == "open_choice":
            command = (
                "p2p choice create "
                f'--title "Intake {intake_id} choice for {target or "project"}" '
                '--option "..." --option "..."'
            )
            if target:
                command += f" --related {target}"
            command += f" --source {intake_id}"
            return ("requires_input", "pending", command, ["option", "option"])
        if action_type in {"accept", "reject", "defer"}:
            command = f"p2p proposal {action_type} {target or 'PROP-000'} --reason \"{rationale}\""
            return ("governance_only", "pending", command, [])
        if action_type in {"duplicate", "record_conflict"}:
            return ("preview_only", "pending", "Manual review required.", [])
        return ("unsupported", "pending", "Unsupported intake apply action.", [])

    def _next_id(self) -> str:
        max_id = 0
        intake_dir = self.p2p_dir / "intake"
        for path in intake_dir.iterdir() if intake_dir.exists() else []:
            match = re.match(r"INTAKE-(\d{3})$", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"INTAKE-{max_id + 1:03d}"

    def _find_dir(self, intake_id: str) -> Path:
        intake_dir = self.p2p_dir / "intake"
        if not intake_dir.exists():
            raise ValueError("No .p2p/intake directory found.")
        path = intake_dir / intake_id
        if not path.is_dir():
            raise ValueError(f"Intake not found: {intake_id}")
        return path

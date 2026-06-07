# P2PWorkspace Intake Lifecycle Service Extraction Requirements

## Purpose

Extract intake prompt/import/status/apply behavior from `P2PWorkspace` into a
cohesive service while preserving existing CLI, MCP, next-action, and context
behavior.

This is local software-development planning. It is not P2P governance state.

## Current Behavior To Preserve

- `p2p intake prompt` creates `.p2p/intake/INTAKE-XXX/` artifacts and generated
  context.
- `p2p intake import` imports recommendation, related proposals, suggested
  actions, and context artifacts from a directory, or imports a file as
  `recommendation.md`.
- `p2p intake status` reports pending/analyzed state from recommendation
  content.
- `p2p intake apply plan` converts suggested actions into a controlled apply
  plan.
- `p2p intake apply show` reads an existing apply plan.
- `p2p intake apply run` applies only supported explicit actions:
  `add_contribution` and `open_choice`.
- Governance-only and preview-only actions remain non-executable through intake
  apply.
- MCP `p2p_intake_prompt` and `p2p_intake_status` keep the same JSON response
  shapes.
- Next actions continue to inspect intake statuses through the
  `P2PWorkspace.intake_statuses()` facade.

## Functional Requirements

1. The service MUST own intake ID allocation, intake directory lookup, artifact
   creation, import, status, apply plan creation, apply plan show, and apply
   action execution.
2. The service MUST keep the `.p2p/intake` file layout unchanged.
3. The service MUST preserve validation messages for missing intake sources,
   empty imports, missing apply plans, invalid `suggested_actions`,
   `apply_plan`, and `applied_actions` lists, missing apply actions, already
   applied actions, unsupported actions, invalid contribution targets, and
   missing choice options.
4. The service MUST preserve generated command preview text.
5. The service MUST preserve date behavior for `generated_on` and `applied_on`.
6. The service MUST avoid direct CLI and MCP imports.
7. `P2PWorkspace` MUST remain the compatibility facade for public callers.

## Compatibility Requirements

- Public method names on `P2PWorkspace` remain:
  `create_intake_prompt`, `import_intake`, `intake_statuses`,
  `create_intake_apply_plan`, `show_intake_apply_plan`, and
  `run_intake_apply_action`.
- Existing imports of `IntakePrompt`, `IntakeStatus`, `IntakeApplyPlan`, and
  `IntakeAppliedAction` from `p2p_engine.storage.filesystem` remain valid.
- No CLI command, CLI output, MCP tool name, or MCP response key changes are
  allowed.
- Existing choice and contribution behavior remains delegated through existing
  workspace facades.

## Non-Goals

- Do not change proposal contribution semantics.
- Do not change choice lifecycle semantics.
- Do not execute governance-only intake recommendations.
- Do not extract Change Set lifecycle in this slice.

## Acceptance Criteria

- `src/p2p_engine/services/intake.py` contains the extracted service and intake
  models.
- `src/p2p_engine/storage/filesystem.py` delegates intake public behavior to the
  service and no longer contains inline intake lifecycle implementation.
- Existing CLI, MCP, and next-action tests for intake pass unchanged.
- New service-level tests cover prompt/status, import, apply plan/show,
  supported run actions, and error paths.

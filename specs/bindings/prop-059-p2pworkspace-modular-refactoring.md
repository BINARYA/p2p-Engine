# PROP-059 P2PWorkspace Modular Refactoring Binding

## Inputs

- Proposal: `PROP-059 - P2PWorkspace Modular Refactoring Plan`
- Status: accepted
- P2P proposal source:
  `.p2p/proposals/PROP-059-p2pworkspace-modular-refactoring-plan/`
- Refreshed project feature:
  `.p2p/project/features/p2pworkspace-modular-refactoring-plan/feature.md`
- Contributions: `C001` through `C014`
- Binding date: 2026-06-05

No `spec-export generic` output was generated for this binding. The accepted
proposal and refreshed project state are the source of truth because the current
export command is Change Set based, while `PROP-059` is an accepted architecture
direction that has not yet been converted into a Change Set.

## Classification

### Steering Context

- `P2PWorkspace` is a compatibility facade, not the long-term home for all
  behavior.
- Target architecture separates domain rules, application services, adapters,
  CLI presentation, and MCP transport/schema handling.
- `cli.py`, `storage/filesystem.py`, and `mcp/tools.py` should become thinner
  compatibility/orchestration surfaces.
- Breaking changes to CLI, MCP, storage layout, consent, validation, registry
  refresh, Git/sync, or owner-controlled governance require a separate proposal.

### Feature Candidate

- `p2pworkspace-modular-refactoring-contract`

### Accepted First Deliverable

- Update `AGENTS.md` with short non-negotiable agent rules.
- Create `docs/DEVELOPMENT-GUIDELINES.md`.
- Define a prioritized refactoring roadmap.
- Do not change runtime behavior.

### Future Direction

- After accepted-proposal binding into local specs, use consent/permissions as
  the preferred first code extraction.
- Extract services/use cases before splitting CLI modules.

## Steering Updates

- `specs/steering/structure.md` now records the target architecture direction,
  facade rule, anti-monolith rule, and compatibility boundary.
- `specs/steering/tech.md` now records the accepted refactoring direction,
  first future extraction candidate, and verification expectations.
- `specs/README.md` now documents binding accepted P2P proposals when a Change
  Set generic export is not the right input.

## Feature Specs

Created:

- `specs/features/p2pworkspace-modular-refactoring-contract/requirements.md`
- `specs/features/p2pworkspace-modular-refactoring-contract/design.md`
- `specs/features/p2pworkspace-modular-refactoring-contract/tasks.md`

## Evidence Matrix

| Requirement | Expected Behavior | Evidence | Status | Notes |
| --- | --- | --- | --- | --- |
| R001 | Agent rules prevent new monolithic behavior by default. | `AGENTS.md` does not yet contain the PROP-059-specific anti-monolith rules. | not_implemented | Existing AGENTS rules cover P2P governance but not this development contract. |
| R002 | Full development guidelines document exists. | `docs/DEVELOPMENT-GUIDELINES.md` is absent. | not_implemented | First deliverable still pending. |
| R003 | Refactoring roadmap is recorded. | No roadmap document exists yet. | not_implemented | Should be created with guidelines or as a separate doc. |
| R004 | P2PWorkspace remains compatibility facade. | Existing runtime uses `P2PWorkspace`; no new guidance document yet enforces this. | partially_implemented | Current code has the facade; accepted contract still needs docs. |
| R005 | Large runtime files become compatibility/orchestration surfaces. | Current files still contain broad behavior. | not_implemented | This is a guidance and future extraction requirement. |
| R006 | Consent/permissions is selected as first future extraction. | Captured in PROP-059 and local specs. | docs_only | Not implemented; selection is recorded. |
| R007 | Runtime behavior remains unchanged by first deliverable. | No first deliverable has been implemented yet. | not_implemented | This binding changed only specs, but the accepted first deliverable is still pending. |

## Task Completion Decisions

No implementation tasks are marked complete. The accepted proposal defines the
direction and first deliverable, but the deliverable has not yet been performed.

## Gaps

- `AGENTS.md` needs concise architecture rules for agents.
- `docs/DEVELOPMENT-GUIDELINES.md` needs to be created.
- A prioritized refactoring roadmap needs to be created or included in the
  guidelines.
- Consent/permissions extraction needs a later feature binding after the
  architecture contract is implemented.

## Owner Questions

- Should the roadmap live inside `docs/DEVELOPMENT-GUIDELINES.md`, or should it
  be split into `docs/REFACTORING-ROADMAP.md`?
- Should Claude-specific instructions mirror the new architecture rules in
  `CLAUDE.md`, or should Claude rely on `AGENTS.md` plus the guidelines?

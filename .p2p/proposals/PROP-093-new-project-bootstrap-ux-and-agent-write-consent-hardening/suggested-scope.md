# Suggested Scope

## Semantic Core Scope

- Canonical write surfaces for proposal and governance state.
- Persistent write classes and action-preview guidance.
- Clear boundaries between P2P canonical state, generated narrative, imported artifacts, generated exports, stable documentation, scratch files, and external side effects.
- Proposal authoring flow based on structured inputs, synthesis/import, full review, and owner decision.
- Deterministic logical proposal artifact status independent from physical file materialization.
- Owner-friendly full proposal view.
- Compact agent request-routing playbook.

## Operational Core Scope

- Explicit decision root through CLI, MCP, and generated agent instructions.
- Root-aware MCP and runtime hints.
- Agent instructions that explain how to find and use the governed P2P root when the current working directory differs.

## Bootstrap UX Scope

- Adaptive init default: install `generic`; add the detected current agent when reliable; fallback to `all` when detection is unavailable.
- Visible lifecycle commands for agent integrations: list, install, update, doctor, refresh, and uninstall.

## Opportunistic Hygiene Scope

- Non-destructive `.gitignore` protection for fresh projects or an explicit guided option.
- Init summary grouped by purpose.

## Out Of Scope

- Sibling repository product model or any recommended repository topology.
- Software-specific spec artifact structure as a core P2P concept.
- Generic `specs` as a core primitive outside explicit verticals or import/export/catalog contracts.
- External artifact registry MVP.
- Remote collaboration authorization.
- Provider PR/MR automation.
- Destructive migration of existing workspaces or generated agent files.

## Implementation Constraint

Implement PROP-093 in additive slices:

- 093-A canonical proposal authoring;
- 093-B artifact status and owner view;
- 093-C agent persistence policy;
- 093-D bootstrap and integration lifecycle;
- 093-E root, MCP, and hygiene hardening.

The semantic and operational core should not depend on completing opportunistic hygiene work. Decision-root and MCP hardening are core operational work, while repository hygiene remains independently releasable. Existing workspaces initialized with the current release must remain readable, valid, and non-destructively upgradable.

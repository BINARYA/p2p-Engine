# PROP-056 - Project Definition Maturity Rubrics

## Status

`accepted`

## Problem

P2P assess currently measures deterministic structural readiness: validation, registries, proposal status, choices, changes, work items, and operational brief availability. This is useful, but it does not evaluate whether the planned project definition covers the important topics for its domain. For P2P exports, the main question is not whether implementation is complete, but whether the project has been sufficiently defined through proposals, decisions, tradeoffs, risks, requirements, and acceptance criteria.

## Context

P2P Engine aims to export a project definition toward downstream generators, agents, OpenSpec/Spec Kit, or implementation workflows. Different project domains require different definition criteria: software, grant/bid documents, board games, documents, hardware, services, and other domains need different rubrics. The init wizard can ask for a project domain and create a rubric checklist that becomes the deterministic driver for future maturity assessment.

## Goals

- Separate structural readiness from project definition maturity.
- Introduce extensible domain rubrics stored as project state.
- Evaluate whether important project topics have been covered by proposals and decisions.
- Allow future domains to add their own criteria without changing the assessment model.
- Prepare init/wizard flow to select a project domain and generate an editable rubric checklist.

## Non-Goals

- Do not evaluate implemented code quality in this proposal.
- Do not require AI semantic scoring for the MVP.
- Do not make maturity assessment decide project governance outcomes.

## Proposal

Add Project Definition Maturity Rubrics. A project may define a domain and an enabled list of criteria under .p2p/project/rubrics.yml. The first MVP ships deterministic built-in rubrics for at least generic and software domains, with an architecture that can add grant_document, board_game, hardware, service, and other domains later. The init flow should be able to create an initial rubric profile, and a dedicated command should refresh/show maturity assessment. The assessment should scan P2P project artifacts conservatively and report each criterion as covered, partial, or missing, with evidence IDs when available. Scores represent definition maturity: whether the planned project has treated relevant topics enough for export, not whether implementation has been completed.

## Acceptance Criteria

- Project rubrics are stored in .p2p/project/rubrics.yml as editable project state.
- The rubric model supports multiple domains and enabled/disabled criteria.
- A software-domain rubric includes criteria such as problem definition, scope, user workflows, functional requirements, non-functional requirements, security/privacy, data model, integration boundaries, deployment/operations, testing strategy, UX/accessibility, risks/tradeoffs, and acceptance criteria.
- A maturity assessment reports per-criterion status, score, evidence, and suggested next action.
- The maturity score is explicitly project definition maturity, not implementation completeness.
- CLI and MCP expose the maturity assessment without requiring broad file scans by agents.

## Decision

Pending.

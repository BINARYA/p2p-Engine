# PROP-064 - Spec Kit Three-Prompt Export Model

## Status

`accepted`

## Problem

The current P2P export model produces downstream-shaped file bundles for generic, OpenSpec, and Spec Kit targets. That makes P2P look like a folder generator and creates low-value handoff files. The intended value is different: P2P should synthesize accepted project memory into a robust project definition, then derive small agent-consumable prompt/document outputs for downstream systems.

## Context

Accepted PROP-027 and PROP-028 implemented conservative file bundle exports from P2P-native software specs. User review showed this does not match the desired integration contract. Spec Kit starts from three agent prompts: constitution, specify, and plan. OpenSpec starts from a proposal-oriented input. Generic export should be a readable full project definition and a project/proposal initialization input. Therefore project.md should become the canonical generic synthesis artifact, and downstream exports should be deterministic views derived from it and its P2P evidence.

## Goals

- Define project.md as the canonical synthesized project definition derived from accepted P2P memory.
- Define a core project coverage checklist that every project.md must cover.
- Allow domain-specific section extensions for software, grant documents, board games, environmental impact assessment, one-day projects, and future verticals.
- Derive generic, OpenSpec, and Spec Kit outputs from project.md instead of mirroring downstream folder layouts.
- Preserve P2P source traceability so agents and humans can see which accepted artifacts support each major section.

## Non-Goals

- Invoke downstream tools directly.
- Treat draft proposals as accepted truth.
- Generate downstream folder structures as the primary export UX.
- Replace P2P governance decisions with export-time synthesis.

## Proposal

Implement an agent-first project definition export pipeline. Step 1 synthesizes accepted P2P memory into project.md using a required core checklist, domain extensions, evidence labels, and explicit missing-information markers. Step 2 derives target-specific outputs from project.md: generic exports project.md and propose.md; OpenSpec exports propose.md aligned with OpenSpec proposal principles; Spec Kit exports speckit.constitution.md, speckit.specify.md, and speckit.plan.md aligned with the three starting Spec Kit prompts. Legacy bundle-style exports may remain temporarily under a legacy/ or bundle/ path, but they must be labeled secondary and not documented as the primary flow.

## Acceptance Criteria

- Generic export writes project.md and propose.md as the primary output.
- project.md includes the required core sections: executive summary, vision, domain, problem, goals, non-goals, stakeholders, workflows, accepted decisions, requirements, constraints, assumptions, dependencies, operating model or architecture, data or knowledge model, priorities, success criteria, validation method, risks and tradeoffs, open questions, pending proposals, and source traceability.
- project.md includes domain-specific sections based on project rubrics or detected/declared domain.
- Every major project.md section distinguishes accepted evidence, pending/draft material, and missing information.
- Spec Kit export writes exactly speckit.constitution.md, speckit.specify.md, and speckit.plan.md as primary output.
- OpenSpec export writes propose.md as primary output.
- Exports avoid creating synthetic downstream folder layouts as the primary UX.
- Export validation checks required files, required project.md sections, target-specific files, and source traceability metadata.
- Docs explain that P2P exports are agent cognition and downstream initialization artifacts, not downstream tool execution.

## Decision

Pending.

# PROP-054 - Project Readiness and Maturity Assessment

## Status

`accepted`

## Problem

P2P can track proposals, choices, changes, work, validation and MCP workflows, but it does not yet provide a structured assessment of how complete or mature a project is. Users need a way to understand whether a project is ready to proceed and which gaps matter most in the project context.

## Context

Recent MCP tests show that agents can now create and refine draft proposals safely. The next product layer should help owners and agents reason about project readiness without pretending that subjective quality is fully objective. Different project domains need different maturity criteria, such as software security/usability/maintainability or non-software domain-specific criteria.

## Goals

- Define a readiness and maturity assessment model that separates deterministic completion from domain-specific quality assessment.
- Provide scores and gaps that are explainable, versioned and grounded in explicit criteria.
- Keep P2P Core deterministic while allowing optional AI-assisted maturity review through prompt/import workflows.

## Non-Goals

- Do not let P2P automatically decide that a project is ready or block work solely from a maturity score.
- Do not produce a single opaque score without criteria, confidence and known gaps.

## Proposal

Adopt a hybrid assessment model. Level 1 computes a deterministic completion/readiness score from P2P state: validation results, stale registries, draft proposals, accepted proposals, open choices, blockers, change/work lifecycle status and operational brief availability. Level 2 adds domain maturity rubrics through explicit criteria files and prompt/import workflows. Software rubrics may cover architecture, security, usability, testability, maintainability, packaging and documentation. Generic or non-software rubrics can be added per supported project type. Assessment output must include score, confidence, factors, gaps and suggested next actions.

## Acceptance Criteria

- A future MVP can implement p2p assess refresh and p2p assess show for deterministic completion; later rubric prompt/import can estimate domain maturity; scores are explainable and never treated as owner decisions; MCP exposure remains advisory or write-safe only.

## Decision

Pending.

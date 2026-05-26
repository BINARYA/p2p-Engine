# PROP-028 - Spec Kit Export Mapping MVP

## Status

`accepted`

## Problem

P2P can export generic and OpenSpec-oriented bundles from P2P-native software specs, but the declared Spec Kit export target still has no concrete mapping.

## Context

CHANGE-013 added generic and OpenSpec-oriented software spec exports. Spec Kit expects a specification-driven feature directory with spec, plan, supporting design artifacts and tasks.

## Goals

- Define and implement a conservative Spec Kit export mapping from P2P-native software specs without invoking Spec Kit or creating branches.

## Non-Goals

- Pending.

## Proposal

Add speckit as a supported p2p spec export target. Export to .p2p/outputs/spec-export/CHANGE-XXX/speckit/specs/CHANGE-XXX-slug/ with spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md, contracts/README.md, and manifest.yml. The mapping should preserve P2P provenance and mark unresolved implementation details as NEEDS CLARIFICATION instead of inventing them.

## Acceptance Criteria

- p2p spec export --change CHANGE-XXX --target speckit writes a Spec Kit-oriented feature directory. Export status and show include the speckit target. The export is generated only from the P2P-native software spec and provenance. Tests cover successful speckit export and required artifacts.

## Decision

Pending.

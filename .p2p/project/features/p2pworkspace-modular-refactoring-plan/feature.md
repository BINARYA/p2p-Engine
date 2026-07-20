# P2PWorkspace Modular Refactoring Plan

## Provenance

- Proposal: PROP-059
- Source: .p2p/proposals/PROP-059-p2pworkspace-modular-refactoring-plan

## Problem

P2PWorkspace has grown into a large monolithic class that contains initialization, proposals, governance, project state, assessment, context, specs, Change Sets, Work lifecycle, registry, and Git-related behavior. This is functional for the MVP but increases cognitive load, regression risk, and difficulty for contributors.

## Proposal

Adopt a conservative modular refactoring program. P2PWorkspace remains the stable compatibility facade, but new behavior should move into dedicated services and adapters. cli.py, storage/filesystem.py, and mcp/tools.py become thinner orchestration/facade layers rather than the default home for new domain logic. The first deliverable is documentation and development contract only: update AGENTS.md with short non-negotiable agent rules, create docs/DEVELOPMENT-GUIDELINES.md as the full architecture guide, and define a prioritized refactoring roadmap. Alternatives considered are: keep the monolith and document conventions; split large files mechanically; introduce internal managers behind the stable P2PWorkspace facade; or redesign public APIs. The preferred option is internal managers behind the facade because it improves maintainability while preserving CLI, MCP, storage, governance, and agent compatibility. After acceptance and local specs binding, the recommended first code extraction is consent/permissions because it has a clear boundary, high safety value, lower presentation exposure than CLI, and can establish the extraction pattern before more central proposal/readiness workflows are touched. Services/use cases should be extracted before CLI modularization. Any breaking change requires a separate proposal.

## Decision

# Decision - PROP-059

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner accepts the modular refactoring direction after consolidating scope, alternatives, compatibility constraints, first deliverable, first future extraction, and specs binding boundary. This is an explicit owner decision despite the automated readiness score remaining weak.

## Date

2026-06-05

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-f6946a3894334b7cbd16107a

## Decision Fingerprint

0032b6e1e6b3071afbc0333aeb7c6fd0bc8adaacbcabf969fd5db2c676e68f67

## Lineage

None.

## Canonical Source

decision-events.yml

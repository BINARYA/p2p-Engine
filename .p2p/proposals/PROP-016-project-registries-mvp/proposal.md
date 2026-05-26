# PROP-016 - Project Registries MVP

## Status

`accepted`

## Problem

P2P Engine stores proposals, decisions, project state, conflicts and change sets, but it lacks explicit global registries for indexing and relating these artifacts.

## Context

PROP-010 introduced .p2p/project, PROP-012 introduced conflict memory, and PROP-014/015 introduced Change Sets. The next step is making global navigation and provenance explicit.

## Goals

- Define registry files for proposals, decisions, changes, choices and relations.
- Keep registries as derived/index artifacts generated from source .p2p artifacts.
- Prepare CLI commands to refresh and inspect registries.
- Support future proposal intake, overlap analysis and exporter workflows.

## Non-Goals

- Replace proposal, decision or change source artifacts.
- Implement a database or web backend.

## Proposal

Add .p2p/registries as a generated index layer for proposals, decisions, changes, choices and relations.

## Acceptance Criteria

- The proposal defines .p2p/registries structure.
- The proposal distinguishes primary sources from generated registries.
- The proposal defines initial registry refresh/status commands.
- The proposal explains how registries support intake, impact, conflicts and exports.

## Decision

Pending.

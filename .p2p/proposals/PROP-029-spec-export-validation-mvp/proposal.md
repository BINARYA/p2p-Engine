# PROP-029 - Spec Export Validation MVP

## Status

`accepted`

## Problem

P2P can generate generic, OpenSpec-oriented, and Spec Kit-oriented export bundles, but it cannot yet validate whether an existing export bundle is complete and internally consistent before downstream use.

## Context

CHANGE-013 and CHANGE-014 added software spec export targets. Downstream handoff should not rely only on generation success; agents need a read-only validation command.

## Goals

- Provide a read-only CLI validator for generated software spec export bundles.

## Non-Goals

- Pending.

## Proposal

Add p2p spec export-validate CHANGE-XXX --target TARGET. The command validates that the export directory exists, manifest.yml is valid and coherent, index.md exists, and target-specific required files are present for generic, openspec, and speckit bundles.

## Acceptance Criteria

- p2p spec export-validate CHANGE-XXX --target generic validates generic bundles. The same command validates openspec and speckit bundles. Missing files or manifest mismatches fail explicitly. Tests cover valid bundles and invalid/missing export artifacts.

## Decision

Pending.

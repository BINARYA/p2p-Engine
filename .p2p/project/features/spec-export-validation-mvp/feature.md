# Spec Export Validation MVP

## Provenance

- Proposal: PROP-029
- Source: .p2p/proposals/PROP-029-spec-export-validation-mvp

## Problem

P2P can generate generic, OpenSpec-oriented, and Spec Kit-oriented export bundles, but it cannot yet validate whether an existing export bundle is complete and internally consistent before downstream use.

## Proposal

Add p2p spec export-validate CHANGE-XXX --target TARGET. The command validates that the export directory exists, manifest.yml is valid and coherent, index.md exists, and target-specific required files are present for generic, openspec, and speckit bundles.

## Decision

# Decision - PROP-029

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to add read-only validation before downstream use of generated export bundles.

## Date

2026-05-26

## Approver

local

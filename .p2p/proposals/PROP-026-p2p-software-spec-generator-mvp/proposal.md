# PROP-026 - P2P Software Spec Generator MVP

## Status

`accepted`

## Problem

P2P can model proposals, decisions and Change Sets, but it cannot yet generate a normalized software specification suitable for downstream OpenSpec, Spec Kit, or code generation workflows.

## Context

CHANGE-001 established Change Set as the operational unit and separated execution_domains, implementation_targets, spec_targets and export_targets. PROP-010 already selected a P2P-native software spec before downstream export.

## Goals

- Generate deterministic P2P-native software specs from Change Sets.
- Store specs under .p2p/outputs/software-spec/CHANGE-XXX/.
- Provide optional prompt/import workflow for AI-refined specs.
- Validate imported spec artifact shape before replacing generated artifacts.
- Preserve provenance from spec to Change Set, proposals, decisions and source files.

## Non-Goals

- Do not implement OpenSpec or Spec Kit export in this MVP.
- Do not invoke AI directly.
- Do not invent missing requirements beyond source artifacts.

## Proposal

Add p2p spec refresh/status/show/prompt/import. The refresh command deterministically generates a minimal software spec from a Change Set. The prompt command generates an AI/human refinement prompt from the deterministic spec and source context. The import command validates and imports refined spec artifacts.

## Acceptance Criteria

- p2p spec refresh --change CHANGE-XXX generates index.md, requirements.md, design.md, commands.yml, data-model.yml, acceptance.md and provenance.yml.
- p2p spec status lists generated specs.
- p2p spec show CHANGE-XXX prints index.md.
- p2p spec prompt --change CHANGE-XXX writes a refinement prompt.
- p2p spec import CHANGE-XXX spec-output/ validates required files and YAML keys.

## Decision

Pending.

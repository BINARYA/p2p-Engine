# P2P Software Spec Refinement Prompt - CHANGE-012

You are refining a P2P-native software specification for implementation and downstream export.

## Governance Boundary

Do not add requirements that are not supported by accepted proposals, decisions, or the Change Set. Mark missing information as open questions instead of inventing it.

## Required Output

Return a directory containing exactly these artifacts:

- index.md
- requirements.md
- design.md
- commands.yml with top-level `commands`
- data-model.yml with top-level `entities`
- acceptance.md
- provenance.yml with top-level `source`

## Current Deterministic Spec Context

# Software Spec - CHANGE-012 - P2P Software Spec Generator MVP

## Summary

Add p2p spec refresh/status/show/prompt/import. The refresh command deterministically generates a minimal software spec from a Change Set. The prompt command generates an AI/human refinement prompt from the deterministic spec and source context. The import command validates and imports refined spec artifacts.

## Source

- Change Set: `CHANGE-012`
- Change path: `.p2p/changes/CHANGE-012-p2p-software-spec-generator-mvp`
- Included proposals: PROP-026

## Targets

- execution_domains: software
- implementation_targets: local_cli
- spec_targets: p2p_spec
- export_targets: openspec, speckit


# Requirements

## Functional Requirements

### PROP-026 - P2P Software Spec Generator MVP

Add p2p spec refresh/status/show/prompt/import. The refresh command deterministically generates a minimal software spec from a Change Set. The prompt command generates an AI/human refinement prompt from the deterministic spec and source context. The import command validates and imports refined spec artifacts.

## Non-Goals / Exclusions

- Automatic Git commits, branches, tags, or merges.

## Constraints

Do not treat raw proposal discussion as implementation requirements without accepted scope.

## Open Questions

Not specified yet.


# Design

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- Top-level `p2p spec` command group.
- Deterministic software spec generation from Change Sets.
- Software spec status and show commands.
- Optional prompt/import refinement workflow.
- Required artifact validation for imported specs.
- P2P skill guidance and tests.


# Acceptance

## Criteria

- `p2p spec refresh --change CHANGE-XXX` generates required artifacts under `.p2p/outputs/software-spec/CHANGE-XXX/`.
- `p2p spec status` lists generated specs.
- `p2p spec show CHANGE-XXX` prints `index.md`.
- `p2p spec prompt --change CHANGE-XXX` writes a refinement prompt.
- `p2p spec import CHANGE-XXX output-dir/` validates required files and YAML keys.
- Tests cover deterministic generation, prompt creation, status/show, and import.

## Tests / Verification

- T001: Generate deterministic software spec (completed)
- T002: Inspect generated software specs (completed)
- T003: Generate refinement prompt (completed)
- T004: Import refined software spec (completed)
- T005: Update skill and tests (completed)


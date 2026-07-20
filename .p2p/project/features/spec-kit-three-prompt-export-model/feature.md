# Spec Kit Three-Prompt Export Model

## Provenance

- Proposal: PROP-064
- Source: .p2p/proposals/PROP-064-spec-kit-three-prompt-export-model

## Problem

The current P2P export model produces downstream-shaped file bundles for generic, OpenSpec, and Spec Kit targets. That makes P2P look like a folder generator and creates low-value handoff files. The intended value is different: P2P should synthesize accepted project memory into a robust project definition, then derive small agent-consumable prompt/document outputs for downstream systems.

## Proposal

Implement an agent-first project definition export pipeline. Step 1 synthesizes accepted P2P memory into project.md using a required core checklist, domain extensions, evidence labels, and explicit missing-information markers. Step 2 derives target-specific outputs from project.md: generic exports project.md and propose.md; OpenSpec exports propose.md aligned with OpenSpec proposal principles; Spec Kit exports speckit.constitution.md, speckit.specify.md, and speckit.plan.md aligned with the three starting Spec Kit prompts. Legacy bundle-style exports may remain temporarily under a legacy/ or bundle/ path, but they must be labeled secondary and not documented as the primary flow.

## Decision

# Decision - PROP-064

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted fully. P2P should not imitate downstream tool domains or generate downstream-shaped folder bundles. Its vocation is to turn confused, distributed, discontinuous ideas and contributions into an organized project definition while supporting the decision flow. Exports should therefore be agent-first project definition and prompt/document outputs derived from accepted P2P memory.

## Date

2026-05-29

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-609d507c972355fea54acd3c

## Decision Fingerprint

c7ea963d4220f29c97a7059a0b0e981f65325eb41d3773fcfa110d47e11308b3

## Lineage

None.

## Canonical Source

decision-events.yml

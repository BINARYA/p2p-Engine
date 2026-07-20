# Guided Init Wizard MVP

## Provenance

- Proposal: PROP-047
- Source: .p2p/proposals/PROP-047-guided-init-wizard-mvp

## Problem

P2P init can now generate safe project and agent boundaries, but non-technical users still need to know which flags to pass for project name, agent profile, repository mode, and MCP setup hints.

## Proposal

When p2p init is called without a project name, run a small interactive wizard that asks project name, initial agent profile, repository mode, and whether to show an MCP setup hint. Keep p2p init NAME --agent ... --repository ... as the scriptable path. Print concrete next steps after initialization.

## Decision

# Decision - PROP-047

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to make the newly hardened init path usable for first-time users before broadening MCP mutations.

## Date

2026-05-27

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-18cd7fc4ed3e9f1c61a19139

## Decision Fingerprint

f5a440a2f7c5c5d76469442d1139ab3ebd1801034b989decd08c3351a896aa53

## Lineage

None.

## Canonical Source

decision-events.yml

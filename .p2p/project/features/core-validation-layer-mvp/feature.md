# Core Validation Layer MVP

## Provenance

- Proposal: PROP-053
- Source: .p2p/proposals/PROP-053-core-validation-layer-mvp

## Problem

P2P projects can now be manipulated through CLI and MCP, but there is no deeper read-only validation layer to detect malformed YAML, missing proposal sections, stale registries, or basic status inconsistencies before agents, CI, or future packaging workflows rely on the state.

## Proposal

Implement p2p validate with stable findings. The MVP validates required project structure, YAML readability for known structured files, proposal directory naming, required proposal sections, decision status presence, proposal/decision status consistency, and registry freshness. Findings have severity error/warning/info, stable codes, paths, messages, and optional suggested commands. Add --format text/json and exit code 1 when errors exist. Add p2p_validate MCP as read-only/advisory. Keep p2p check as minimal bootstrap validation.

## Decision

# Decision - PROP-053

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to harden the deterministic core before packaging, Rust migration planning, or owner-gated MCP mutations.

## Date

2026-05-28

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-b3ff0dbff17a424fc4908a11

## Decision Fingerprint

684d77a79b9793a60e5656935a1bf35edd746ab9a0e359fe14a9882131803bd8

## Lineage

None.

## Canonical Source

decision-events.yml

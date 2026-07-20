# Agent Runtime Bootstrap Robustness

## Provenance

- Proposal: PROP-074
- Source: .p2p/proposals/PROP-074-agent-runtime-bootstrap-robustness

## Problem

A P2P-managed repository can be shared with a cloud agent environment where project instructions require p2p CLI mutations, but the p2p executable is not installed or available in PATH. The agent correctly stops because direct .p2p edits are forbidden, but the workflow becomes unusable: it cannot create proposals, refresh registries, read context, or proceed through the documented P2P source-of-truth path.

## Proposal

Introduce an Agent Runtime Bootstrap Robustness model. Generated AGENTS.md, agent policy, and docs should include a runtime discovery sequence: try p2p, try repository-local virtualenv paths when present, try python -m p2p_engine if the package is importable, then check MCP availability. Add a diagnostic command or script such as p2p doctor, p2p agent doctor, or a lightweight repo-local bootstrap hint that reports whether p2p CLI, MCP server, Git, and project root are usable. For cloud environments, provide a documented install/bootstrap path that agents can request from the owner rather than stopping with only p2p command not found. The Missing Primitive Rule remains valid, but the error should include actionable recovery steps.

## Decision

# Decision - PROP-074

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to make P2P-managed repositories usable in local and cloud agent runtimes when the p2p executable is missing or not on PATH, by adding runtime diagnostics, documented discovery fallbacks, and actionable recovery while preserving the Missing Primitive Rule.

## Date

2026-06-03

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-4e2cc6ff61af6eefc51307ba

## Decision Fingerprint

3ada67365ca647d7d4549a414325e957b3a6322538f416f7b364141d86334927

## Lineage

None.

## Canonical Source

decision-events.yml

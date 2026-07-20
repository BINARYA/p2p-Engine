# Ergonomic Remote Project Initialization

## Provenance

- Proposal: PROP-073
- Source: .p2p/proposals/PROP-073-ergonomic-remote-project-initialization

## Problem

Initializing a cloud-backed P2P project currently requires separate mental steps: p2p init declares repository mode, raw Git config creates or attaches the Git remote, and p2p project remote configure records the P2P remote profile. This is workable for experienced users but too implicit for owners, contributors, and agents who should not need to understand raw Git setup details.

## Proposal

Extend p2p init and remote profile setup with an ergonomic remote initialization flow. Add init options such as --repository cloud, --provider, --remote, and --remote-url. During init, P2P should write the project remote profile, detect whether the named Git remote exists, compare its URL when present, and print actionable follow-up commands when Git state is missing or mismatched. The command should not create provider resources in the MVP. Existing p2p project remote configure remains available for later edits, and p2p sync status remains the validation command after setup.

## Decision

# Decision - PROP-073

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to fix dogfooding gaps in remote/cloud project initialization: init must validate repository mode, configure P2P remote profile ergonomically, detect Git origin/profile divergence, and provide actionable recovery without requiring raw Git knowledge.

## Date

2026-06-03

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-360e17a4067a1365afbfde03

## Decision Fingerprint

277f779d51411290c496a200baa7df894cfb798f7b886e605eb4a17700a20389

## Lineage

None.

## Canonical Source

decision-events.yml

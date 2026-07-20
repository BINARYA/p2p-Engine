# P2P Software Spec Generator MVP

## Provenance

- Proposal: PROP-026
- Source: .p2p/proposals/PROP-026-p2p-software-spec-generator-mvp

## Problem

P2P can model proposals, decisions and Change Sets, but it cannot yet generate a normalized software specification suitable for downstream OpenSpec, Spec Kit, or code generation workflows.

## Proposal

Add p2p spec refresh/status/show/prompt/import. The refresh command deterministically generates a minimal software spec from a Change Set. The prompt command generates an AI/human refinement prompt from the deterministic spec and source context. The import command validates and imports refined spec artifacts.

## Decision

# Decision - PROP-026

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to introduce the P2P-native software spec layer before downstream OpenSpec or Spec Kit export.

## Date

2026-05-26

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-3eb96abd79945af2e84644ea

## Decision Fingerprint

c0ab66d785edf5a647386edfbb06d7a536ba5ada4e334b175e30dde36e01da9b

## Lineage

None.

## Canonical Source

decision-events.yml

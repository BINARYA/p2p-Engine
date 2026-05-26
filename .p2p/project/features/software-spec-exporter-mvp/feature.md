# Software Spec Exporter MVP

## Provenance

- Proposal: PROP-027
- Source: .p2p/proposals/PROP-027-software-spec-exporter-mvp

## Problem

P2P can generate and refine P2P-native software specs, but it cannot yet export those specs into downstream code-generation or specification tool formats.

## Proposal

Add p2p spec export/status/show support for software spec export bundles. The MVP should export from .p2p/outputs/software-spec/CHANGE-XXX/ into .p2p/outputs/spec-export/CHANGE-XXX/TARGET/, starting with generic and openspec targets. Spec Kit remains a downstream target but is not implemented in this MVP unless the mapping becomes explicit.

## Decision

# Decision - PROP-027

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to add the first downstream export layer after the refined P2P-native software spec MVP.

## Date

2026-05-26

## Approver

local

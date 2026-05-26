# PROP-027 - Software Spec Exporter MVP

## Status

`accepted`

## Problem

P2P can generate and refine P2P-native software specs, but it cannot yet export those specs into downstream code-generation or specification tool formats.

## Context

CHANGE-012 introduced the P2P-native software spec layer. The next step is to export from that normalized layer instead of reading raw proposal folders.

## Goals

- Provide a conservative exporter MVP that writes generic and OpenSpec-oriented export bundles from an existing P2P software spec.

## Non-Goals

- Pending.

## Proposal

Add p2p spec export/status/show support for software spec export bundles. The MVP should export from .p2p/outputs/software-spec/CHANGE-XXX/ into .p2p/outputs/spec-export/CHANGE-XXX/TARGET/, starting with generic and openspec targets. Spec Kit remains a downstream target but is not implemented in this MVP unless the mapping becomes explicit.

## Acceptance Criteria

- p2p spec export --change CHANGE-XXX --target generic writes an export bundle from the refined P2P spec. p2p spec export --change CHANGE-XXX --target openspec writes an OpenSpec-oriented bundle. p2p spec export-status lists export bundles. p2p spec export-show CHANGE-XXX --target TARGET prints the export index. Tests cover successful export and unsupported targets.

## Decision

Pending.

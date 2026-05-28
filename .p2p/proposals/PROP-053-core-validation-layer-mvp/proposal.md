# PROP-053 - Core Validation Layer MVP

## Status

`accepted`

## Problem

P2P projects can now be manipulated through CLI and MCP, but there is no deeper read-only validation layer to detect malformed YAML, missing proposal sections, stale registries, or basic status inconsistencies before agents, CI, or future packaging workflows rely on the state.

## Context

The current p2p check command only verifies minimal bootstrap files. Before packaging and before owner-gated MCP mutations, the core should expose a semantic validation pass with stable finding codes, severities, JSON output, and MCP access.

## Goals

- Add a read-only core validation layer and CLI/MCP entry points that report project-state issues without mutating files.

## Non-Goals

- Pending.

## Proposal

Implement p2p validate with stable findings. The MVP validates required project structure, YAML readability for known structured files, proposal directory naming, required proposal sections, decision status presence, proposal/decision status consistency, and registry freshness. Findings have severity error/warning/info, stable codes, paths, messages, and optional suggested commands. Add --format text/json and exit code 1 when errors exist. Add p2p_validate MCP as read-only/advisory. Keep p2p check as minimal bootstrap validation.

## Acceptance Criteria

- p2p validate reports no errors on a fresh valid project; invalid YAML or missing required files produce errors; stale registries produce warnings with p2p registry refresh suggestion; --format json emits machine-readable findings; exit code is 1 only for errors; MCP p2p_validate returns the same structured validation result; tests cover CLI and MCP behavior.

## Decision

Pending.

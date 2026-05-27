# PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

## Status

`accepted`

## Problem

Agents can now initialize projects and refresh registries through MCP, but cannot create draft proposals or intake prompts without a local p2p CLI in PATH. This keeps common contribution workflows dependent on shell setup and can push agents toward stopping even for safe draft creation.

## Context

The tested Codex/Codium workflow now correctly stops instead of editing .p2p by hand. The next safe MCP increment should expose draft creation primitives while keeping proposal acceptance and governance decisions owner-controlled.

## Goals

- Allow MCP clients to create draft proposals and intake prompts through explicit write-safe tools.

## Non-Goals

- Pending.

## Proposal

Add MCP tools p2p_proposal_create, p2p_intake_prompt, and p2p_intake_status. These tools may create draft proposals and intake prompts using existing core methods, and may list intake records. They must not accept, reject, defer, decide choices, apply intake recommendations, or manage work merges.

## Acceptance Criteria

- MCP exposes proposal/intake draft tools; p2p_proposal_create returns a draft proposal with path and does not create an accepted decision; p2p_intake_prompt creates intake prompt artifacts; p2p_intake_status lists intake state; tests cover tool behavior and confirm governance tools remain absent.

## Decision

Pending.

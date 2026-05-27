# PROP-047 - Guided Init Wizard MVP

## Status

`accepted`

## Problem

P2P init can now generate safe project and agent boundaries, but non-technical users still need to know which flags to pass for project name, agent profile, repository mode, and MCP setup hints.

## Context

After the MCP local test, the product direction is to make project bootstrap safe and understandable before expanding MCP mutations. The CLI should guide first-time users while keeping scriptable flags available.

## Goals

- Make p2p init usable without memorizing flags, while preserving non-interactive CLI usage.

## Non-Goals

- Pending.

## Proposal

When p2p init is called without a project name, run a small interactive wizard that asks project name, initial agent profile, repository mode, and whether to show an MCP setup hint. Keep p2p init NAME --agent ... --repository ... as the scriptable path. Print concrete next steps after initialization.

## Acceptance Criteria

- p2p init without a name prompts for project name, agent profile, repository mode, and MCP hint; p2p init NAME remains non-interactive; output includes next commands and optional MCP setup guidance; tests cover interactive and scriptable paths.

## Decision

Pending.

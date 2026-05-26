# PROP-020 - Proposal Inspection CLI MVP

## Status

`accepted`

## Problem

Users and agents can inspect proposals through p2p status or registries, but there are no dedicated p2p proposal list/show commands.

## Context

Agent skills need simple, stable commands for checking proposal state before creating intake, choices or decisions.

## Goals

- Add p2p proposal list with optional status filtering.
- Add p2p proposal show PROP-ID for compact proposal inspection.
- Improve p2p registry show choices output readability.

## Non-Goals

- Add semantic search or advanced proposal queries.

## Proposal

Expose proposal inspection through dedicated CLI commands and make choice registry output stable for humans and agents.

## Acceptance Criteria

- Users can list proposals with statuses and titles.
- Users can filter proposals by status.
- Users can show a proposal summary.
- Choice registry output is not printed as raw Python dictionaries.

## Decision

Pending.

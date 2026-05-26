# PROP-019 - Proposal Decision Shortcut Commands

## Status

`accepted`

## Problem

Users and agents must use p2p decision record with explicit outcomes to accept, reject, or defer proposals, which makes the workflow less natural.

## Context

Choice and intake workflows now produce recommended actions that require clear proposal lifecycle commands.

## Goals

- Add p2p proposal accept.
- Add p2p proposal reject.
- Add p2p proposal defer.

## Non-Goals

- Replace the lower-level p2p decision record command.

## Proposal

Implement dedicated proposal decision shortcut commands that call the existing decision recording mechanism.

## Acceptance Criteria

- A user can accept a proposal with a reason.
- A user can reject a proposal with a reason.
- A user can defer a proposal with a reason.

## Decision

Pending.

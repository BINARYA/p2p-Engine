# PROP-024 - Choice Blocking and Discovery MVP

## Status

`accepted`

## Problem

Choices can be created and decided, but they do not expose operational discovery, proposal-local choice candidates, or formal blockers for proposals and Change Sets.

## Context

The project now has p2p next and operational brief artifacts. The next intelligence step is to distinguish related choices, discovered candidate blockers, and formal blocks without letting the CLI decide on behalf of the owner.

## Goals

- Phase 1: add advisory choice show/status/discover commands.
- Phase 2: add explicit choice block/unblock commands backed by links.yml.
- Expose project choices and proposal-local vote choices consistently.
- Allow p2p next to prioritize unresolved formal choice blockers.

## Non-Goals

- Do not automatically decide choices.
- Do not automatically convert proposal-local votes into project choices.
- Do not invoke AI directly.

## Proposal

Implement choice blocking and discovery in two steps. First add deterministic advisory inspection commands that surface project choices, proposal-local choice candidates, and unresolved discovery findings. Then add formal block/unblock commands that write links.yml for project choices, distinguishing related metadata from active blockers.

## Acceptance Criteria

- p2p choice show CHOICE-XXX shows project choice details and links.
- p2p choice status lists project choices and proposal-local choice candidates.
- p2p choice discover reports advisory findings without modifying state.
- p2p choice block/unblock records and deactivates explicit blockers in links.yml.
- p2p next prioritizes active unresolved choice blockers before generic continue_change actions.

## Decision

Pending.

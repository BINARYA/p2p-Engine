# PROP-018 - Choice Management CLI MVP

## Status

`accepted`

## Problem

P2P Engine can represent a choice manually, but the CLI cannot yet create, list, or decide choices.

## Context

INTAKE-001 suggested opening CHOICE-001. The choice was created manually, proving the artifact model but exposing the need for CLI commands.

## Goals

- Implement p2p choice create.
- Implement p2p choice list.
- Implement p2p choice decide.

## Non-Goals

- Implement full voting or permission enforcement.
- Automatically apply intake suggested-actions.

## Proposal

Add first-class CLI commands for project choices under .p2p/choices/.

## Acceptance Criteria

- Users can create a choice with multiple options.
- Users can list existing choices.
- Users can decide a choice and preserve the selected option and rationale.

## Decision

Pending.

# Choice Blocking and Discovery MVP

## Provenance

- Proposal: PROP-024
- Source: .p2p/proposals/PROP-024-choice-blocking-and-discovery-mvp

## Problem

Choices can be created and decided, but they do not expose operational discovery, proposal-local choice candidates, or formal blockers for proposals and Change Sets.

## Proposal

Implement choice blocking and discovery in two steps. First add deterministic advisory inspection commands that surface project choices, proposal-local choice candidates, and unresolved discovery findings. Then add formal block/unblock commands that write links.yml for project choices, distinguishing related metadata from active blockers.

## Decision

# Decision - PROP-024

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to make choices operational through advisory discovery first and explicit owner-controlled blockers second.

## Date

2026-05-25

## Approver

local

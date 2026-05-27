# Remote Project Profile and Review Request Policy

## Provenance

- Proposal: PROP-041
- Source: .p2p/proposals/PROP-041-remote-project-profile-and-review-request-policy

## Problem

P2P can publish managed Work branches, but it does not yet distinguish local-only projects from remote-backed projects or express external review handoff without binding the core workflow to GitHub PRs.

## Proposal

Add a Remote Project Profile and a provider-agnostic review-request command. The profile records mode, provider, remote name, and remote URL. p2p work request-review WORK-XXX records that a published Work item is ready for external review, emits provider-specific guidance, and leaves merge/accept owner-controlled.

## Decision

# Decision - PROP-041

## Status

`accepted`

## Outcome

accepted

## Reason

Remote review must remain optional and provider-agnostic; publish should stay separate from PR/MR handoff.

## Date

2026-05-27

## Approver

local

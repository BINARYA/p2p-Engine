# PROP-041 - Remote Project Profile and Review Request Policy

## Status

`accepted`

## Problem

P2P can publish managed Work branches, but it does not yet distinguish local-only projects from remote-backed projects or express external review handoff without binding the core workflow to GitHub PRs.

## Context

The owner wants GitHub/GitLab support to remain optional and adapter-based while keeping Git invisible under P2P Work commands.

## Goals

- Record whether a P2P project is local-only or remote-backed.
- Keep p2p work publish separate from external review/PR creation.
- Introduce an advisory request-review step that can later be implemented by provider adapters.

## Non-Goals

- Create GitHub Pull Requests automatically in this MVP.
- Require PRs for P2P accept/finalize/cleanup.

## Proposal

Add a Remote Project Profile and a provider-agnostic review-request command. The profile records mode, provider, remote name, and remote URL. p2p work request-review WORK-XXX records that a published Work item is ready for external review, emits provider-specific guidance, and leaves merge/accept owner-controlled.

## Acceptance Criteria

- p2p project remote configure/show can manage a local or remote-backed profile.
- p2p work request-review WORK-XXX works only after publish and records review-request metadata without opening a PR.
- The agent skill documents that publish does not create PRs and external provider adapters are future extensions.

## Decision

Pending.

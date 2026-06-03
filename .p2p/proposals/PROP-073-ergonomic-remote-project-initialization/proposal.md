# PROP-073 - Ergonomic Remote Project Initialization

## Status

`accepted`

## Problem

Initializing a cloud-backed P2P project currently requires separate mental steps: p2p init declares repository mode, raw Git config creates or attaches the Git remote, and p2p project remote configure records the P2P remote profile. This is workable for experienced users but too implicit for owners, contributors, and agents who should not need to understand raw Git setup details.

## Context

Pending.

## Goals

- Let users declare remote project intent during init with provider, remote name, and remote URL options.
- Guide users when the Git remote is missing, mismatched, or not reachable, without requiring raw Git knowledge.
- Keep local and cloud project semantics unified: cloud mode only adds remote profile validation and managed sync guidance.
- Preserve provider-neutral behavior and avoid creating external repositories in the MVP.
- Generate agent instructions and next-step hints that match the selected repository mode.

## Non-Goals

- Automatically create GitHub/GitLab repositories or provider PR/MR resources.
- Replace Git provider authentication, SSH setup, branch protection, or IAM.
- Make local actor identities into strong authentication.

## Proposal

Extend p2p init and remote profile setup with an ergonomic remote initialization flow. Add init options such as --repository cloud, --provider, --remote, and --remote-url. During init, P2P should write the project remote profile, detect whether the named Git remote exists, compare its URL when present, and print actionable follow-up commands when Git state is missing or mismatched. The command should not create provider resources in the MVP. Existing p2p project remote configure remains available for later edits, and p2p sync status remains the validation command after setup.

## Acceptance Criteria

- p2p init accepts remote profile options for cloud-backed projects without requiring a separate p2p project remote configure command.
- p2p init validates whether the configured Git remote exists and reports clear recovery guidance when it is missing or mismatched.
- p2p project remote configure remains available to modify mode, provider, remote name, and URL after init.
- p2p sync status reflects the initialized remote profile and explains readiness or blockers.
- Generated AGENTS.md and agent policy explain the selected repository mode and the no-raw-Git boundary.
- The MVP does not create external provider repositories; it only records profile metadata and validates local Git remote configuration.

## Decision

Pending.

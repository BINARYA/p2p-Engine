# PROP-074 - Agent Runtime Bootstrap Robustness

## Status

`accepted`

## Problem

A P2P-managed repository can be shared with a cloud agent environment where project instructions require p2p CLI mutations, but the p2p executable is not installed or available in PATH. The agent correctly stops because direct .p2p edits are forbidden, but the workflow becomes unusable: it cannot create proposals, refresh registries, read context, or proceed through the documented P2P source-of-truth path.

## Context

Pending.

## Goals

- Make P2P-managed repositories self-diagnosing for agents when the p2p runtime is missing.
- Provide clear fallback guidance for PATH, virtualenv, module execution, MCP tools, or installation.
- Prevent agents from bypassing governance while still making the next recovery step obvious.
- Support cloud agent environments where the repository is mounted but the Python package is not installed.

## Non-Goals

- Allow agents to create or edit .p2p files manually when the CLI is missing.
- Bundle a hosted P2P service or require a global package manager.
- Grant cloud agents repository write permissions or provider credentials automatically.

## Proposal

Introduce an Agent Runtime Bootstrap Robustness model. Generated AGENTS.md, agent policy, and docs should include a runtime discovery sequence: try p2p, try repository-local virtualenv paths when present, try python -m p2p_engine if the package is importable, then check MCP availability. Add a diagnostic command or script such as p2p doctor, p2p agent doctor, or a lightweight repo-local bootstrap hint that reports whether p2p CLI, MCP server, Git, and project root are usable. For cloud environments, provide a documented install/bootstrap path that agents can request from the owner rather than stopping with only p2p command not found. The Missing Primitive Rule remains valid, but the error should include actionable recovery steps.

## Acceptance Criteria

- Generated AGENTS.md explains what to do when p2p is not found in PATH.
- Docs include cloud-agent setup and recovery steps for installing or invoking p2p.
- A diagnostic command or documented script can report p2p CLI, MCP server, Git repository, project root, and remote profile readiness.
- When p2p is unavailable, the recommended behavior remains stop-and-report, but the report includes exact recovery commands.
- Tests cover repository mode validation and runtime hint generation where practical.

## Decision

Pending.

# PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

## Status

`draft`

## Problem

When a collaborator clones a P2P-managed repository, Git contains the project state but not the P2P Engine runtime normally installed in the project-local virtualenv. This creates friction and ambiguity: the collaborator must know which P2P Engine version to install, how to recreate the local environment, and how to handle runtime upgrades when the project evolves.

## Context

Pending.

## Goals

- Define a project-local bootstrap and upgrade model so a cloned P2P-managed project can restore the required P2P Engine runtime in a predictable, versioned, agent-safe way without committing the virtualenv itself.

## Non-Goals

- Pending.

## Proposal

Introduce a dedicated collaborator bootstrap flow. A P2P initialization may generate project-local bootstrap metadata and/or an installer wrapper that records the required P2P Engine version, creates or reuses the project-local virtualenv, installs the expected runtime, verifies the CLI/MCP server, and detects when the project requires a newer runtime. The flow should support human execution and agent-assisted execution, while keeping owner-controlled governance boundaries intact.

## Acceptance Criteria

- A draft proposal exists that frames collaborator runtime bootstrap as distinct from P2P project state. It captures the alternatives of generated installer, version metadata, agent-assisted install, and upgrade detection. It explicitly avoids committing .venv and leaves the final operating model open for later exploration.

## Decision

Pending.

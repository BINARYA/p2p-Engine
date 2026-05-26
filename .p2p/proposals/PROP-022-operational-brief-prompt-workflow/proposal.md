# PROP-022 - Operational Brief Prompt Workflow

## Status

`accepted`

## Problem

Project status is currently technical and descriptive; agents can summarize it in chat, but the project lacks a versioned prompt/import workflow for operational synthesis.

## Context

The project uses prompt-only workflows for exploration, impact, and intake. The same pattern should introduce intelligence without making the CLI decide on behalf of the owner.

## Goals

- Generate a project brief prompt from registries and project state.
- Import AI or human operational brief output into .p2p/project artifacts.
- Keep the skill as method guidance while the CLI remains the source of repeatable context and stored output.

## Non-Goals

- Direct AI invocation from the CLI.
- Automatic owner decisions or automatic application of recommendations.

## Proposal

Add a prompt-only operational brief workflow under project commands: the CLI gathers project state, registries, conflicts, choices, intake and changes into a context file, generates instructions for an AI/human synthesis, and imports the resulting operational brief and optional next-actions YAML.

## Acceptance Criteria

- p2p project brief prompt creates a prompt and context file.
- p2p project brief import stores operational-brief.md and optional next-actions.yml.
- p2p project brief show prints the stored operational brief.

## Decision

Pending.

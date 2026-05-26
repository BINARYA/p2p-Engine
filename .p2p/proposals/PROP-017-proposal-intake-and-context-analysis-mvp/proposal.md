# PROP-017 - Proposal Intake and Context Analysis MVP

## Status

`accepted`

## Problem

P2P Engine can store proposals and registries, but it does not yet help agents or users decide whether a new idea should become a new proposal, enrich an existing one, open a choice, or be marked as overlapping/conflicting.

## Context

PROP-016 introduced generated registries. The next step is using those registries to analyze incoming ideas against existing project memory.

## Goals

- Analyze new ideas against proposal, change and relation registries.
- Suggest whether to create a new proposal, add a contribution, open a choice, or record a conflict.
- Provide prompt-only intake analysis before direct AI adapters or MCP.

## Non-Goals

- Automatically decide whether a proposal is accepted.
- Replace owner governance.
- Implement semantic embeddings or a database in the MVP.

## Proposal

Introduce a proposal intake and context analysis workflow backed by generated registries and prompt-only AI output.

## Acceptance Criteria

- The proposal defines intake analysis inputs and outputs.
- The proposal defines initial CLI commands for intake prompt/status/import or analysis.
- The proposal explains how intake supports multi-user and multi-agent collaboration.

## Decision

Pending.

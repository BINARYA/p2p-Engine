# PROP-083 - Domain-Aware Visible Project Definition Export

## Status

`draft`

## Problem

P2P Engine currently routes accepted project intent through Change Set software-spec and spec-export outputs. This makes every project look like a software implementation workflow, even when the project domain is not software. A project such as la scatola perfetta would still be pushed toward .p2p/outputs/software-spec and OpenSpec or Spec Kit shaped exports, which is conceptually wrong. P2P Engine is not meant to develop software with its release workflow; it is meant to define a project in detail and export that definition for humans and downstream tools. The current output location under hidden .p2p/outputs also makes the generated project definition hard for normal users to find.

## Context

Pending.

## Goals

- Pending.

## Non-Goals

- Pending.

## Proposal

Replace the Change Set software-spec centered export workflow with a domain-aware project definition export workflow. P2P should generate a complete generic project definition for every domain from accepted P2P memory and project state. OpenSpec and Spec Kit exports should be available only when the project domain or selected export profile is software-compatible. Non-software domains must not generate software-spec, OpenSpec, or Spec Kit outputs by default. The primary generic output must be written to a visible output directory at the project root, not hidden under .p2p/outputs, so humans who install and use P2P Engine can easily find the project definition. .p2p may retain provenance, indexes, or internal metadata, but the human-facing export must live outside the hidden P2P state directory.

## Acceptance Criteria

- A project can generate a detailed generic project definition without creating a Change Set or software-spec. Non-software domains do not expose or recommend OpenSpec or Spec Kit exports by default. Software-compatible projects may explicitly export OpenSpec and Spec Kit targets from the project definition layer. Generated human-facing project outputs are written to a visible root-level output directory. CLI, MCP, skills, and docs stop directing agents to use software-spec as the default path for project definition export.

## Decision

Pending.

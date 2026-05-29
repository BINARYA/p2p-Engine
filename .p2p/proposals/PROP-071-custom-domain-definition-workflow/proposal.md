# PROP-071 - Custom Domain Definition Workflow

## Status

`accepted`

## Problem

P2P currently treats project domains as a fixed set of hardcoded identities. This makes predefined domains look authoritative at init time and makes custom domains an exception, even though P2P's broader model is that projects often start from unclear intent and become defined through user-agent collaboration.

## Context

Domain and rubric setup should be modeled consistently for every project. Predefined domains should be optional templates that pre-populate domain/rubric metadata, not proof that the project is already semantically well-defined. Custom or no-template projects should start with explicit unresolved domain/rubric state and recommended setup activities.

## Goals

- Represent domain and rubric state explicitly for all projects.
- Treat predefined domains as optional initialization templates.
- Make custom/none initialization a first-class unresolved setup path rather than a special-case error path.
- Base maturity assessability on rubric availability and status, not hardcoded domain identity.

## Non-Goals

- Implement a mediator or AI semantic review inside core.
- Hardcode every possible vertical in P2P Engine.

## Proposal

Refactor domain initialization around optional templates. Every project has explicit domain state and rubric state. At init, the user may choose no template, a predefined template such as generic/software/grant_document/board_game, or a custom unresolved path. Applying a template pre-populates domain metadata and rubric criteria. Choosing custom or none leaves domain/rubric setup unresolved and creates or recommends first activities for defining the domain and defining the rubric with the user and agent. Maturity assessment becomes assessable only when an enabled rubric exists; unresolved or empty rubrics report a missing/unresolved rubric state instead of well_defined.

## Acceptance Criteria

- p2p init can represent no-template/custom initialization without forcing the project into a predefined domain.
- All projects store explicit domain state and rubric state.
- Predefined domains are treated as templates that populate initial domain/rubric metadata.
- Custom or no-template initialization records unresolved domain/rubric setup.
- Custom or no-template initialization creates or recommends first activities: define the domain, then define the rubric.
- Maturity assessment does not report well_defined when rubric state is unresolved or criteria are missing.
- The workflow keeps mediator/agent domain synthesis outside core while preserving deterministic state in .p2p/.

## Decision

Pending.

# PROP-062 - README Product Landing Page Refinement

## Status

`accepted`

## Problem

The README should work as the public landing page for P2P Engine, but the current structure is still repository-oriented and does not lead with why the project exists, who it is for, a 5-minute demo, and a concise glossary.

## Context

The repository is being made public. README should explain P2P Engine as the engine, not future hosted products, and route detailed material to docs.

## Goals

- Make README.md a concise product-style landing page for the engine.
- Explain why P2P Engine exists and who it serves.
- Add a 5-minute demo with commands and expected output.
- Keep install instructions short and link to docs/INSTALL.md.
- Clearly mark stable and work-in-progress docs.

## Non-Goals

- Do not expand detailed CLI/API/MCP documentation in this change.
- Do not describe mediator or web as part of this repository.

## Proposal

Rewrite README.md with sections: pitch, why, what it does, who it is for, status, 5-minute demo, install, core concepts, docs, roadmap, development. Use HTTPS clone first and keep future hosted product scope out of the engine README.

## Acceptance Criteria

- README starts with a one-line pitch.
- README contains Why, What it does, Who it is for, Status, 5-minute demo, Install, Core concepts, Docs, and Roadmap sections.
- README install example uses HTTPS clone first.
- README marks detailed docs as stable or WIP.

## Decision

Pending.

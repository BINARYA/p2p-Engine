# PROP-078 - Project-Local Wheel Installation and Upgrade Model

## Status

`accepted`

## Problem

P2P Engine is currently practical to update only when the operator understands a separate source checkout or external path. Existing P2P projects need a coherent project-local installation and upgrade path that does not require referencing another folder, cloning the engine inside every project, or rerunning p2p init.

## Context

Pending.

## Goals

- Make P2P Engine installable and upgradeable inside each project's own virtual environment, starting with GitHub Release wheel artifacts and explicitly preserving a future migration path to a public package registry.

## Non-Goals

- Pending.

## Proposal

Introduce a packaging and installation model based on versioned wheel artifacts attached to GitHub Releases as the first distribution channel. Project setup documentation should install P2P Engine into the project-local .venv from a release wheel URL, and project upgrade documentation should use python -m pip install --upgrade <wheel-url>, followed by p2p doctor, p2p agent doctor, p2p registry refresh, p2p agent instructions refresh, and p2p validate. This is a transitional distribution model: the long-term target remains a public package such as PyPI, where installation becomes python -m pip install p2p-engine and upgrade becomes python -m pip install --upgrade p2p-engine. The proposal should avoid requiring users to reference external source checkout paths during normal project use.

## Acceptance Criteria

- A user can initialize or update a project-local .venv using a GitHub Release .whl without cloning or referencing a separate p2p-Engine source directory; docs clearly distinguish engine runtime upgrade from project repository sync; docs state GitHub wheel distribution is transitional and future public package publication is planned; post-upgrade refresh and validation commands are documented; no guidance suggests rerunning p2p init for existing projects.

## Decision

Pending.

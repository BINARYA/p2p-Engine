# PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

## Status

`accepted`

## Problem

P2P Engine is intentionally a local CLI/core/MCP engine, but future cloud/web product work needs a clear execution boundary. Without an explicit boundary, proposals may drift toward embedding public web APIs, multi-tenant auth, workflow orchestration, or long-running SaaS responsibilities directly inside P2P Engine.

## Context

Pending.

## Goals

- Keep P2P Engine focused on local deterministic automation: CLI, filesystem .p2p state, Git audit, and local MCP.
- Define P2P Cloud as a separate product layer that owns web/API, auth, UI, database, workflow orchestration, and multi-tenant state.
- Define a containerized P2P runner model for cloud workflows that invokes the p2p CLI in isolated Git checkouts.
- Make cloud execution auditable through .p2p artifacts and Git history without turning the engine into a hosted API service.
- Clarify which future proposals should be rejected, accepted, or reformulated based on this boundary.

## Non-Goals

- Implement P2P Cloud inside this repository as part of P2P Engine core.
- Add a public FastAPI/Django/NestJS API server to P2P Engine.
- Make P2P Engine responsible for users, organizations, billing, sessions, OAuth, cloud IAM, or multi-tenant authorization.
- Keep one long-running P2P server container per project as the default execution model.
- Create provider PR/MR automation in the engine core.

## Proposal

Adopt a strict boundary: P2P Engine exposes stable local automation primitives through CLI, local project files, Git, and local MCP. P2P Cloud is a separate web/API product that uses P2P Engine by launching isolated runner jobs. The cloud stack may use Caddy, a web/API framework such as Django/DRF or NestJS, PostgreSQL for users/projects/jobs/permissions, Redis or equivalent queues, Prefect or equivalent workflow orchestration, and ephemeral p2p-runner containers. Each runner gets a temporary workspace, checks out or initializes the target Git repository, executes p2p CLI commands, records .p2p state, commits/pushes through Git, emits logs/artifacts, and exits. P2P Engine must not become a public multi-tenant API server, IAM system, web UI, workflow scheduler, provider PR automation service, or hosted database-backed application.

## Acceptance Criteria

- Architecture documentation states that P2P Engine remains CLI/filesystem/Git/local-MCP, while P2P Cloud owns web/API/auth/UI/workflows/database.
- Cloud workflows are modeled as isolated runner jobs that invoke p2p CLI against a temporary Git checkout.
- Future proposals that add public web APIs or multi-tenant IAM directly to P2P Engine are rejected or reformulated as P2P Cloud proposals.
- The runner image requirements are clear: p2p engine installed, git installed, credentials injected per job, workspace mounted or cloned, no long-lived project daemon required.
- The boundary preserves Git and .p2p as the project audit/source-of-truth layer while allowing cloud DB indexing and job orchestration outside the engine.

## Decision

Pending.

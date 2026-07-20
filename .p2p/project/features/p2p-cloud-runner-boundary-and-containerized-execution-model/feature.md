# P2P Cloud Runner Boundary and Containerized Execution Model

## Provenance

- Proposal: PROP-076
- Source: .p2p/proposals/PROP-076-p2p-cloud-runner-boundary-and-containerized-execution-model

## Problem

P2P Engine is intentionally a local CLI/core/MCP engine, but future cloud/web product work needs a clear execution boundary. Without an explicit boundary, proposals may drift toward embedding public web APIs, multi-tenant auth, workflow orchestration, or long-running SaaS responsibilities directly inside P2P Engine.

## Proposal

Adopt a strict boundary: P2P Engine exposes stable local automation primitives through CLI, local project files, Git, and local MCP. P2P Cloud is a separate web/API product that uses P2P Engine by launching isolated runner jobs. The cloud stack may use Caddy, a web/API framework such as Django/DRF or NestJS, PostgreSQL for users/projects/jobs/permissions, Redis or equivalent queues, Prefect or equivalent workflow orchestration, and ephemeral p2p-runner containers. Each runner gets a temporary workspace, checks out or initializes the target Git repository, executes p2p CLI commands, records .p2p state, commits/pushes through Git, emits logs/artifacts, and exits. P2P Engine must not become a public multi-tenant API server, IAM system, web UI, workflow scheduler, provider PR automation service, or hosted database-backed application.

## Decision

# Decision - PROP-076

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted as the architectural boundary for future cloud work: P2P Engine remains local CLI/filesystem/Git/local-MCP, while P2P Cloud owns web/API/auth/UI/workflows/database and invokes P2P through isolated runner containers.

## Date

2026-06-03

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-3d548bebf715932a059ace7c

## Decision Fingerprint

71bd1a857a7e3ede66405d9d430647f03deaa962f6d7fc85985da4b2ea3ee9ce

## Lineage

None.

## Canonical Source

decision-events.yml

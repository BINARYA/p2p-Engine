# Agent-First Setup Documentation Split

## Provenance

- Proposal: PROP-067
- Source: .p2p/proposals/PROP-067-agent-first-setup-documentation-split

## Problem

Public setup documentation still mixes two workflows: using P2P Engine for a new project and contributing to the P2P Engine repository itself. This can make users think they should operate the CLI manually or initialize work inside the engine repository when the normal workflow is to install P2P once and let an agent use it on a separate target project.

## Proposal

Revise README and INSTALL around an agent-first new-project setup model. Add or update agent setup guidance so the P2P Engine checkout, target project, and agent client are clearly separated. Move repository-contributor instructions for installing P2P and enabling an agent against the P2P Engine repository into CONTRIBUTING.md, and keep README limited to a concise contribution pointer.

## Decision

# Decision - PROP-067

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to align public setup documentation with the agent-first new-project workflow and move P2P Engine contributor setup into CONTRIBUTING.md.

## Date

2026-05-29

## Approver

local

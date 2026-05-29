# PROP-059 - P2PWorkspace Modular Refactoring Plan

## Status

`draft`

## Problem

P2PWorkspace has grown into a large monolithic class that contains initialization, proposals, governance, project state, assessment, context, specs, Change Sets, Work lifecycle, registry, and Git-related behavior. This is functional for the MVP but increases cognitive load, regression risk, and difficulty for contributors.

## Context

The current priority is to keep the engine stable while planning a medium-term refactor. The refactor should not be rushed because many CLI and MCP flows depend on the current P2PWorkspace facade.

## Goals

- Plan a modular refactor of the monolithic P2PWorkspace implementation.
- Preserve the public core facade until tests and migration paths are ready.
- Identify manager boundaries such as ProposalManager, ChangeSetManager, WorkManager, RegistryManager, AssessmentManager, SpecManager, and AgentInstructionManager.

## Non-Goals

- Do not perform the refactor in this proposal.
- Do not change CLI or MCP behavior as part of the planning proposal.

## Proposal

Create a refactoring plan that maps current P2PWorkspace methods to cohesive internal managers while keeping P2PWorkspace as the stable facade. Define migration phases, test requirements, risk areas, and rollback strategy before moving code.

## Acceptance Criteria

- A refactor plan maps public P2PWorkspace methods to proposed managers.
- The plan identifies migration phases and regression risks.
- The plan preserves CLI/MCP behavior during migration.
- No large code movement happens before the plan is reviewed.

## Decision

Pending.

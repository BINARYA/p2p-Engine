# Roadmap

This roadmap summarizes public direction. P2P proposals and Change Sets remain
the detailed source of truth for project intent.

## Current Status

P2P Engine is Alpha / MVP+.

Implemented:

- filesystem-backed P2P workspace;
- CLI;
- local stdio MCP server;
- proposals, decisions, choices, Change Sets, Work metadata;
- registries and validation;
- compact context packets for agents;
- project rubrics and maturity assessment;
- software spec generation and export MVP;
- guided project init and agent instruction generation.

## Near Term

- Expand practical CLI and MCP documentation.
- Add more real-client MCP verification.
- Improve coverage reporting.
- Continue hardening validation and recovery paths.
- Clarify extension points for project-domain rubrics.

## Later

- Package or compile the CLI for easier installation.
- Strengthen spec/export workflows.
- Split the large internal workspace facade into smaller managers while
  preserving public behavior.
- Explore hosted mediator or web layers outside this engine repository.

## Out Of Scope For This Repository

- Hosted SaaS product implementation.
- Provider-specific AI orchestration.
- Replacing Git, issue trackers, or downstream spec tools.

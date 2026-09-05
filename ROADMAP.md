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
- raw, width-independent CLI JSON for machine consumers;
- path-free bundled vertical locks and strict portable-package YAML parsing;
- deterministic WaveKit transition fixtures for the current engine release;
- logical Work planning with source-control lifecycle outside the runtime;
- reproducible wheel/sdist candidate automation with installed-wheel smoke.

## Near Term

- Qualify linked-project lifecycle and drift recovery against the verified
  0.6.5 release artifact and downstream WaveKit integration.
- Continue hardening validation and recovery paths.

## Later

- Add a public package-registry distribution channel when ready.
- Strengthen spec/export workflows.
- Split the large internal workspace facade into smaller managers while
  preserving public behavior.
- Explore hosted mediator or web layers outside this engine repository.

## Out Of Scope For This Repository

- Hosted SaaS product implementation.
- Provider-specific AI orchestration.
- Replacing Git, issue trackers, or downstream spec tools.

Source-control, review, CI and publication remain external repository tooling.
P2P Engine may store inert traceability references, but it does not own branch,
commit, synchronization, merge or release lifecycles.

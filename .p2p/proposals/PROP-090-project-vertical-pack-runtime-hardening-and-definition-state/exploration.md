# Exploration - PROP-090

## Source

Extracted from the consolidated proposal text for PROP-090 and the owner
answers Q001-Q006. No additional owner decision is inferred here.

## Core Finding

PROP-090 is not a new vertical system. It is the production-hardening layer for
the accepted and partially implemented PROP-085 vertical MVP.

The proposal turns verticals from useful templates into a durable runtime
contract by adding:

- canonical multi-file pack structure;
- compatibility loading for current single-file packs;
- deterministic resolver precedence;
- vertical.lock.yml;
- definition.yml;
- narrow structured definition-state writes;
- JSON context surfaces for agents;
- progressive agent guidance rules;
- safety validation for pack content;
- explicit migration and upgrade behavior.

## Hidden Decisions Surfaced

- Keep p2p project vertical as the primary namespace instead of introducing a
  required top-level p2p vertical namespace in the first implementation.
- Keep .p2p/project/verticals as the project-local pack path.
- Keep base_project as the canonical fallback vertical.
- Do not introduce generic_project in the first implementation.
- Implement definition-state writes in the first production slice, but only
  through a narrow structured patch/update contract.
- Defer the full next-action engine until definition-state semantics are stable.
- Resolve installed packs from both P2P_HOME/verticals and ~/.p2p/verticals,
  with P2P_HOME precedence.
- Use severity-dependent validation for unsafe guidance text.
- Generate lockfiles automatically for new init/select flows, but require
  explicit repair/migration for existing projects.

## Architectural Implications

- Project vertical pack loading must move from a compact MVP shape to a
  normalized model that accepts both single-file and multi-file packs.
- Resolver behavior becomes part of the public contract because lockfiles pin
  the exact selected source.
- definition.yml becomes project state and must be written only through
  supported CLI/service/MCP paths.
- Agent guidance depends on structured data surfaces rather than embedded
  domain knowledge.
- Maturity remains based on rubrics.yml and enabled criteria; verticals provide
  structured inputs, not a parallel maturity engine.

## Execution Domains

- software
- p2p_governance
- documentation
- testing

## Expected Implementation Areas

- project vertical core models;
- ProjectVerticalService;
- project initialization service;
- project maturity/rubric services;
- validation service;
- CLI project command modules;
- MCP project handlers/catalog;
- generated agent instructions;
- public docs;
- regression tests;
- visible project export, if vertical/definition summaries are included.


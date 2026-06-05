# Domain Steering

## Core Concepts

- **Project memory**: durable record of proposals, decisions, choices, and
  readiness.
- **Project state**: rationalized view generated from accepted project memory.
- **Project definition**: human-facing export that describes the project in
  enough detail for people and tools to act on it.
- **Domain**: the kind of project being defined, such as software, product,
  board game, physical object, event, or another custom domain.
- **Generic export**: domain-neutral project definition that every project can
  generate.
- **Software export**: target-specific output for software-compatible domains,
  such as OpenSpec or Spec Kit.
- **Local development specs**: repository-local implementation planning files
  under `specs/`.
- **Binding evidence**: direct proof from `src/`, `tests`, `docs`, or observed
  command behavior that a theoretical requirement is implemented.

## Invariants

- P2P governance state is not implementation task state.
- Every project can produce a generic project definition.
- Only software-compatible projects should produce software-specific exports by
  default.
- Human-facing exported output should be easy to find from the project root.
- `.p2p/` may hold internal state, provenance, and indexes, but should not be
  the only location for user-facing project output.
- Generated project definitions must be classified before being imported into
  specs: stable steering, feature candidates, current export focus, and gaps.
- Task completion is an implementation claim and requires binding evidence.

## Non-Domain-Specific Rule

P2P Engine must not assume that every project is software. A project such as
`la scatola perfetta` should receive a detailed generic project definition, not
software-spec, OpenSpec, or Spec Kit outputs unless the owner explicitly selects
a software-compatible export profile.

For this repository, the domain is software, but local implementation still
flows through `specs/`, source code, tests, and review. P2P outputs do not
replace that workflow.

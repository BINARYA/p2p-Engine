# Execution Plan - PROP-090

## Implementation Strategy

Implement PROP-090 as the production hardening layer for PROP-085, not as a
replacement for the existing MVP. The work should preserve the current `p2p
project vertical` command namespace, keep the single-file `vertical.yml`
compatibility path, and add the production contracts required for multi-file
vertical packs, deterministic lock state, durable project definition state,
JSON-ready agent context, and safe pack validation.

The first implementation should be delivered as a local development feature
derived from this proposal after governance acceptance. Coding tasks belong in
`specs/`, while `.p2p/` remains governance state.

## Implementation Slices

### Slice 1 - Pack Contract And Loader Compatibility

- Define the canonical multi-file vertical pack layout with `manifest.yml`,
  `vertical.yml`, `sections/`, `rubrics.yml`, and optional `profiles/`,
  `modules/`, `artifacts/`, and `examples/`.
- Keep current single-file `vertical.yml` packs loadable.
- Normalize single-file and multi-file packs into the same typed runtime model.
- Validate required metadata, section identifiers, field identifiers, rubric
  criteria, profile references, module references, and artifact template
  references.
- Keep `base_project` as the canonical default vertical id.
- Do not introduce `generic_project` in the first production slice.

### Slice 2 - Resolver Precedence And Lockfile State

- Extend vertical resolution across internal seed packs, project-local packs,
  `P2P_HOME/verticals`, and `~/.p2p/verticals`.
- Preserve project-local pack support at `.p2p/project/verticals/`.
- Apply `P2P_HOME/verticals` precedence over `~/.p2p/verticals` when
  `P2P_HOME` is configured.
- Record effective source type, resolved source path or package coordinate,
  vertical id, version, checksum, and resolver metadata in
  `.p2p/project/vertical.lock.yml`.
- Generate lockfiles deterministically for new init/select flows.
- Do not create or mutate lockfiles implicitly during validation, readiness,
  export, or ordinary reads for existing projects.

### Slice 3 - Explicit Repair And Migration Flow

- Detect existing active vertical state without `vertical.lock.yml`.
- Emit actionable validation diagnostics for missing, stale, or unresolved
  lock state.
- Add an explicit repair or migration command that can generate a lockfile for
  existing active vertical state.
- Fail without writing when a locked vertical cannot be resolved.
- Never silently fall back to `base_project` after a lockfile has been created.
- Make upgrade and migration behavior explicit and reviewable before writing.

### Slice 4 - Project Definition State

- Introduce `.p2p/project/definition.yml` as durable project definition state.
- Store schema version, vertical id, vertical version, selected profile,
  optional lock reference, per-section status, structured field data, missing
  required fields, assumptions, open questions, blockers, decisions where
  relevant, next suggested action when deterministic, and history/provenance.
- Use section statuses such as `missing`, `partial`, `assumed`, `complete`,
  `blocked`, and `not_applicable`.
- Use assumption statuses such as `to_validate`, `validated`, `rejected`, and
  `superseded`.
- Validate definition state against the active vertical pack.

### Slice 5 - Structured Definition-State Writes

- Implement definition-state writes through a narrow structured patch/update
  contract.
- Reject unknown section ids, field ids, invalid section statuses, invalid
  assumption statuses, inconsistent completion states, and unsafe provenance.
- Write atomically through service, CLI, and MCP-compatible paths.
- Do not expose arbitrary YAML editing as a production write interface.
- Defer full interactive editing and complex long-answer merge behavior.

### Slice 6 - JSON-Ready Agent Surfaces

- Expose project context, selected vertical, section list, section detail,
  rubrics, and definition state through JSON-ready CLI or MCP surfaces.
- Include enough structured data for agents to ask one owner question at a
  time, record assumptions explicitly, and report remaining gaps.
- Allow optional `next_suggested_action` when it is deterministic.
- Defer the full `p2p project next-action --json` engine from the first
  production slice.

### Slice 7 - Init, Profile, Module, And Rubric Integration

- Keep `p2p init` lightweight and deterministic.
- Allow interactive init to select vertical, profile, optional sections or
  modules, and rubric customization.
- Generate `vertical.yml`, `vertical.lock.yml`, initial `definition.yml`, and
  `rubrics.yml` from vertical defaults for new flows.
- Run PROP-057 guided rubric selection after rubric generation.
- Preserve existing enabled rubric flags by stable criterion id during
  regeneration.
- Treat removed criteria as orphaned or confirmation-required removals.
- Distinguish selected project rubric maturity from full default vertical
  baseline coverage.

### Slice 8 - Pack Safety And Trust Boundary

- Validate vertical pack content as domain data, not authoritative agent
  instruction.
- Treat explicit attempts to override system, developer, governance,
  repository, safety, or tool-permission rules as hard errors.
- Treat path escapes, code execution instructions, forced tool execution, and
  permission changes as hard errors.
- Treat ambiguous instruction-like wording in examples or templates as
  warnings when severity policy allows it.
- Require internal seed packs to validate cleanly.
- Allow project-local packs with warning-level diagnostics where policy permits.
- Leave future remote or Wavekit pack trust policy as deferred work.

### Slice 9 - Documentation, Tests, And Regression Coverage

- Document pack layout, compatibility rules, resolver precedence, lockfile
  semantics, `definition.yml`, agent guidance, explicit repair or migration,
  and deferred next-action or Wavekit behavior.
- Add service tests for loader normalization, resolver precedence, lockfiles,
  definition-state validation, and structured updates.
- Add CLI tests for JSON surfaces, init integration, lock inspection, explicit
  repair or migration, and definition-state read/update behavior.
- Add MCP parity tests where a matching MCP surface exists.
- Add validation tests for malformed packs, unsafe paths or content, stale
  locks, orphaned rubrics, and inconsistent definition state.
- Add regression tests for existing `p2p project vertical` behavior and
  single-file packs.
- Require `p2p validate` to pass with zero errors after implementation.

## Deferred Work

- Full `p2p project next-action --json` engine.
- Interactive definition editor beyond the structured patch/update contract.
- Sophisticated long-answer merge semantics.
- Advanced state migrations.
- Remote or Wavekit vertical registry trust policy.
- Executable vertical plugins.


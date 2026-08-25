# Requirements - Converge Project Structure Surfaces

## Scope

Audit and converge every maintained public, agent-facing and packaged surface
after the new authority, domain, project structure, memory classification,
readiness, registry-domain discovery, structure export and structure
replacement contracts are implemented. This feature is the P2P Engine 0.5.0
release gate; it adds no independent domain behavior.

## Origin

- Source: owner-approved P2P Engine 0.5.0 convergence requirement.
- Release dependencies: P1-P7 except deferred P8,
  `support-typed-authority-context-in-governed-mutations` and
  `extend-remote-registry-client-with-domain-discovery`.
- Deferred P8 merge/restore must update its own surfaces and trigger a later
  convergence audit when implemented.

## In Scope

- Removal of current-runtime schema-3 domain/vertical compatibility paths.
- CLI text/JSON inventory and contract fixtures.
- MCP stdio catalog, handlers, consent and descriptions.
- Generated agent capabilities, skills and templates.
- Documentation, examples, bundled resources and release metadata.
- Installed-wheel, offline and cross-version failure checks.
- WaveKit-facing contract fixture bundle for the exact release.

## Out Of Scope

- New structure-domain behavior not required by P1-P7.
- WaveKit implementation changes.
- Conversion of existing workspace schema 3 project state.
- Rewriting immutable historical release notes.
- Registry ranking or publication policy.

## Public Surface And MCP Impact

- CLI impact: audit and enforce all breaking/additive P1-P7 contracts.
- MCP impact: audit semantic parity and explicit deferrals; no undocumented
  missing or extra tools.
- Storage impact: prove runtime supports only the new current schemas.
- Agent-facing behavior: regenerate and test all installed adapter guidance.

## Functional Requirements

- R001: Maintained CLI help and docs SHALL use domain, structure source, project
  structure, memory scope, readiness and classification terminology correctly.
- R002: Machine-facing commands SHALL emit their declared versioned payloads
  under one valid JSON envelope and stable exit/error mapping.
- R003: No current CLI path SHALL inject rubric templates from domain.
- R004: No current project-structure path SHALL require an active vertical lock
  or create a vertical release for an ordinary edit.
- R005: No current read SHALL treat missing scope as implicit global content.
- R006: No readiness read SHALL count retired/origin criteria or classification
  debt in its score.
- R007: MCP tools SHALL use the same domain services as CLI or declare a reviewed
  transport-specific deferral.
- R008: Generated skills/templates SHALL explain empty projects, unassigned and
  global memory, decision scope gates, retirement preview/apply and readiness
  versus classification.
- R009: Bundled vertical resources SHALL validate under the current vertical
  schema and specialized presets SHALL be ordinary releases.
- R010: `p2p version --format json` and workspace status SHALL report the exact
  engine, CLI envelope, workspace, vertical-pack, portable-package,
  registry-protocol, project-domain, project-structure,
  memory-classification, project-readiness, authority-context and
  mutation-receipt contract versions needed by a collaborator or WaveKit
  worker.
- R011: An exported sanitized fixture bundle SHALL cover every P1-P7 CLI JSON
  command consumed by deterministic external workers.
- R012: Installed-wheel smoke SHALL prove fixtures, bundled resources, MCP
  catalog and offline workflows are present in the built artifact.
- R013: Searches for obsolete current-only schema, release and command wording
  SHALL have an explicit allowlist limited to historical documentation and
  intentional error messages.
- R014: Release notes SHALL state the clean break, recreation requirement and
  removed compatibility without claiming migration support.
- R015: The convergence matrix SHALL map every governed P1-P7 mutation to its
  exact capability, AuthorityContext behavior, CLI/MCP parity decision, receipt
  evidence and hosted-policy boundary, and SHALL record P8 merge/restore as an
  explicit post-0.5.0 deferral rather than an available operation.
- R016: No maintained service, CLI help, MCP description, generated skill,
  fixture or example SHALL encode WaveKit membership roles or use a mutable
  owner identity as the schema-4 technical project authority.
- R017: The current remote-registry client, docs, CLI/MCP catalog and fixtures
  SHALL converge on `p2p-vertical-registry/v2` domain discovery and SHALL NOT
  retain an executable protocol-v1 fallback.

## Non-Functional Requirements

- N001: Contract fixtures SHALL be deterministic, sanitized and safe to commit.
- N002: Generated files SHALL be produced through their owning generators and
  verified for drift.
- N003: The release gate SHALL test supported Python versions without sharing
  mutable build artifacts across matrix jobs.
- N004: Full validation SHALL run from source and from the built wheel.
- N005: Historical references SHALL remain historically accurate.

## Edge Cases And Errors

- Source tree passes while wheel omits schema or bundled release resources.
- CLI docs updated but MCP catalog or generated skills remain stale.
- Old domain values survive in examples as current commands.
- Contract fixture includes local root or operation secret.
- Parallel CI jobs race on shared dist output.
- Unsupported schema error is mistaken for conversion support.

## Acceptance Criteria

- AC001: All P1-P7 requirements map to source, tests, docs and public fixtures.
- AC002: CLI and MCP contract inventories contain no unexplained semantic gap.
- AC003: Generated guidance fully explains standalone use without WaveKit.
- AC004: Source-tree and wheel contract tests pass for the exact 0.5.0 artifact.
- AC005: Obsolete-reference audit contains only reviewed historical exceptions.
- AC006: CI build/test/release jobs are isolated and deterministic.
- AC007: A WaveKit worker can validate the exported fixture bundle without
  reading P2P internals.
- AC008: Version and schema references converge to the released current-only
  contract.
- AC009: The release inventory contains no missing capability mapping, no
  WaveKit-role dependency and no owner-shaped schema-4 technical authority.
- AC010: Installed-wheel registry tests prove v2 domain discovery,
  domain-filtered release search, read-only MCP parity and deterministic
  rejection of protocol v1.

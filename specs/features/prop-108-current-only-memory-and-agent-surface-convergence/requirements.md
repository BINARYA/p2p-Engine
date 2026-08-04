# Requirements - Current-Only Memory And Agent Surface Convergence

## Origin

- Accepted P2P proposal: `PROP-108`.
- Owner decision: accepted by `mrjungle` on 2026-08-04.
- Readiness at acceptance: `100`, `decision_ready`, high confidence, no failed
  gates and no owner override.
- Target release: P2P Engine `0.4.7`.
- This is an explicitly approved breaking cleanup for project-memory forms and
  public compatibility aliases that have no external compatibility obligation.

## Goal

Make the shipped product describe and enforce one current P2P Engine. The CLI,
MCP catalog, maintained documentation, generated agent instructions, packaged
templates, release metadata and every authoritative project-memory family must
converge on current behavior. Obsolete templates must be detected even when
their recorded file hash still matches, and discarded memory forms must be
rejected rather than interpreted, migrated or recreated.

## Definitions

- **Current contract**: the one authoritative representation and lifecycle
  accepted for a memory family by this release.
- **Memory family**: a cohesive persisted authority such as workspace schema,
  runtime contract, proposal decisions, proposal artifact state, project
  questions, permissions, registries, publications or derived-state metadata.
- **Template generation identity**: a product-controlled identifier for the
  shipped renderer and capability contract, independent from the hash of one
  rendered project file.
- **Content drift**: a managed file differs from the hash recorded when P2P
  last wrote it.
- **Template obsolescence**: a managed file may still match its recorded hash,
  but its template generation is not the current generation shipped by the
  installed P2P Engine.
- **Historical evidence**: an old command, format or decision mentioned in a
  clearly historical record that is not reachable as current runtime behavior.

Current-only does not require every memory family to share the same numeric
schema version. It requires exactly one accepted contract per family.

## In Scope

- A validated inventory of CLI leaves, MCP tools, adapter templates, operation
  capability classifications and release metadata.
- Complete standalone-agent guidance for current local and remote vertical
  workflows, including registry discovery, device login, search, pull, draft
  derivation, validation, publication and project adoption.
- Product-generation identity and stale-template diagnostics for all generated
  agent adapters and skills.
- Removal of obsolete readers, writers, fallbacks, aliases, migration/adoption
  paths, CLI commands, MCP tools, facade methods, diagnostics, fixtures and
  tests across all persisted P2P memory families.
- Current-only initialization, validation, packaging and installed-wheel
  verification.
- Archiving and semantic inventory of the canonical P2P Engine project followed
  by clean recreation on the release candidate.

## Out Of Scope

- General migration or compatibility support for third-party project state.
- Runtime conversion of the current canonical development project.
- WaveKit HTTP registry, OAuth or device-authorization implementation.
- Full one-to-one parity between CLI commands and MCP tools.
- Deletion of historical specifications, release notes or audit evidence solely
  because they mention an obsolete format.
- Changes to owner authority, consent or permission semantics except removal of
  obsolete fallback and alias surfaces.

## Public Surface And MCP Impact

- CLI impact: breaking removal of obsolete commands and aliases; corrected
  read-only agent diagnostics and current command references.
- MCP impact: breaking removal of obsolete tools and aliases; preserved
  governed subset with explicit capability classification.
- Storage impact: breaking rejection of every non-current project-memory form;
  no runtime migration.
- Agent-facing behavior: generated instructions and skills change, gain current
  vertical workflows, and report product-template obsolescence separately from
  user content drift.
- Documentation impact: maintained command, MCP, installation and release
  references become validated against registered runtime surfaces.
- MCP parity decision: intentional subset. Every relevant operation must be
  classified, but local administration and owner-governed operations are not
  exposed merely to match CLI command counts.

## Functional Requirements

### Canonical Public-Surface Inventory

- R001: THE SYSTEM SHALL derive the complete registered CLI leaf-command set
  from the Typer application used by the installed runtime.
- R002: THE SYSTEM SHALL derive the complete registered MCP tool set from the
  same MCP registry used by the server.
- R003: THE SYSTEM SHALL maintain one validated capability classification that
  maps agent workflows to current CLI paths, MCP tools, authority requirements
  and intentional omissions.
- R004: IF a capability references an unregistered CLI command or MCP tool,
  THEN validation SHALL fail with a machine-readable diagnostic.
- R005: IF a registered agent-relevant operation has no capability
  classification, THEN public-surface validation SHALL fail.
- R006: Maintained CLI and MCP reference regions SHALL be generated from, or
  checked against, the registered surfaces rather than independent command
  lists.
- R007: README, installation guidance, changelog release state and runtime
  recommendation SHALL identify the same released version and current contract
  values.
- R008: Historical documents MAY contain obsolete commands only when excluded
  explicitly from current-surface validation and clearly classified as
  historical.

### Standalone Agent Guidance

- R009: Generated generic, Codex and Claude guidance SHALL explain current
  project inspection, proposal governance, local vertical use and remote
  vertical use without requiring WaveKit.
- R010: Generated guidance SHALL identify the current commands for registry
  configuration, device authentication, remote search, immutable pull and
  local catalog inspection.
- R011: Generated guidance SHALL identify the current commands for creating,
  deriving, inspecting, validating, materializing and publishing a vertical
  draft.
- R012: Generated guidance SHALL identify which operations are available over
  MCP and SHALL label CLI-only operations explicitly.
- R013: Every command embedded in a current generated template SHALL resolve to
  a registered CLI path or be marked as external shell syntax.
- R014: Every MCP tool embedded in a current generated template SHALL resolve
  to a registered MCP tool.

### Template Generation And Obsolescence

- R015: Every managed generated agent file SHALL record a template ID and a
  product template-generation identity.
- R016: Managed adapter state SHALL record both the rendered content hash and
  the template-generation identity used to create each file.
- R017: Agent inspection SHALL classify files at least as `current`,
  `content_drift`, `template_obsolete`, `unknown_template` or `missing`.
- R018: IF a file matches its recorded content hash but its generation identity
  is older than the installed catalog, THEN it SHALL be classified as
  `template_obsolete` rather than `current`.
- R019: IF a file differs from its recorded content hash, THEN template age and
  content drift SHALL be reported independently.
- R020: `agent list`, `agent show`, `agent status`, `agent doctor`, `validate`
  and corresponding MCP agent inspection SHALL use the same classification
  service.
- R021: Read-only inspection and validation SHALL NOT rewrite generated files or
  managed adapter state.
- R022: `agent update` SHALL require an explicit force or conflict-resolution
  path before replacing user-modified managed content.
- R023: Fresh `init` and agent installation SHALL render only the current
  generation and SHALL never install superseded skill paths or template IDs.
- R024: Source-tree and installed-wheel execution SHALL expose identical
  template catalogs, capability maps and rendered generation identities.

### Current-Only Project Memory

- R025: The implementation SHALL inventory every persisted memory family with
  its current authority file, schema, readers, writers, validators, commands,
  MCP tools, facade entry points, fixtures and packaged examples.
- R026: Every inventoried memory family SHALL have exactly one current accepted
  representation and authority resolution path.
- R027: Current project initialization SHALL create every mandatory current
  authority declaration without relying on absent-file inference.
- R028: Unsupported forms MAY be inspected only far enough to identify and
  reject them; their semantic content SHALL NOT be adapted into current state.
- R029: Rejecting an unsupported form SHALL use a stable machine-readable error
  with family, observed form and expected current contract details.
- R030: Rejecting an unsupported form SHALL cause zero persistent writes.
- R031: Shipped runtime code SHALL NOT contain a reader, writer, fallback,
  automatic converter or normalizer whose only purpose is an obsolete memory
  form.
- R032: Shipped CLI and MCP registries SHALL NOT expose a command or tool whose
  only purpose is migration, adoption, repair or resolution of discarded
  memory forms.
- R033: Facade methods and compatibility wrappers that can reach discarded
  behavior SHALL be removed rather than retained as no-op aliases.
- R034: Current tests and fixtures SHALL assert rejection or absence of obsolete
  forms and SHALL NOT characterize successful legacy behavior.

### Required Family Convergence

- R035: Workspace schema 3 SHALL remain the sole workspace contract and the
  runtime SHALL expose no workspace migration command tree.
- R036: A current project SHALL require the current runtime contract; missing
  runtime state SHALL NOT become writable through a legacy-adoption workflow.
- R037: Proposal artifact state SHALL have one current state model and SHALL
  remove `legacy_absent`, `absent_legacy` and mark-legacy write surfaces.
- R038: Proposal authority SHALL come only from the current decision-event
  ledger and SHALL remove legacy projection adapters, `unknown_legacy` states
  and legacy-resolution CLI/MCP operations.
- R039: Project questions SHALL use the current structured question authority
  and SHALL NOT migrate or bind questions from obsolete definition fields.
- R040: Actor authority SHALL come from current permissions state and SHALL NOT
  fall back to obsolete governance-role records.
- R041: Decision-context relations SHALL persist only canonical relation terms;
  compatibility aliases SHALL be rejected rather than normalized.
- R042: Registries SHALL require the current verifiable manifest contract and
  SHALL remove `legacy_unverifiable` operation states.
- R043: Software-spec lifecycle and provenance SHALL use only the current
  generated contract and SHALL remove legacy-origin/current-legacy freshness
  states.
- R044: Publication state SHALL use only current edition paths and SHALL remove
  legacy path aliases from runtime models and readers.
- R045: Readiness, context packets, workspace status and derived freshness
  SHALL remove informational-legacy and current-legacy fallback states.
- R046: Current narrative evidence MAY remain when explicitly part of the
  current artifact contract, but it SHALL NOT act as a fallback authority for a
  missing structured artifact.

### Release And Canonical Project

- R047: Before canonical project recreation, repository tooling SHALL produce
  an external archive and semantic inventory without adding a converter to the
  shipped package.
- R048: The semantic inventory SHALL record at least proposal identities and
  statuses, decision heads, active vertical coordinate, current definition,
  choices, Change Sets, Work records and validation result.
- R049: The canonical P2P Engine project SHALL be recreated through public
  current-release commands in a fresh root.
- R050: Release verification SHALL NOT replace the canonical project unless its
  required semantic evidence has been deliberately re-established or recorded
  as intentionally historical.
- R051: Release artifacts SHALL contain no migration utility, compatibility
  fixture or packaged resource capable of recreating discarded state.

## Non-Functional Requirements

- N001: Public-surface checks SHALL be deterministic and independent of file
  modification time, process identity and network availability.
- N002: Template generation identity SHALL change only when rendered semantics
  or the capability contract changes, not because a timestamp changed.
- N003: Current-only preflight SHALL fail before acquiring a mutation path that
  can alter project state.
- N004: Capability inventory and compatibility inventory SHALL remain
  searchable and reviewable in source control.
- N005: Generated documentation checks SHALL distinguish current maintained
  references from historical evidence without broad directory exclusions.
- N006: Focused family tests, CLI/MCP public-contract tests, source/wheel parity
  tests and the full suite SHALL pass before release handoff.

## Edge Cases And Errors

- A managed file can be both `content_drift` and `template_obsolete`; both facts
  must be preserved in diagnostics.
- A generated file with a template ID unknown to the installed release must not
  be silently adopted as current.
- An MCP omission is valid only when the capability catalog records its reason
  and authority classification.
- Missing current authority files are invalid current state, not a signal to
  infer or migrate an old representation.
- A historical Markdown example must not fail current command validation when
  it is explicitly classified as historical, but the same command in a current
  generated template must fail.
- A symbol containing `legacy` may be retained only when the compatibility
  inventory proves it is historical evidence or current domain terminology and
  cannot activate discarded behavior.

## Acceptance Criteria

- AC001: Every registered CLI leaf and MCP tool is inventoried and every
  agent-relevant operation has an explicit exposure classification.
- AC002: Every current command/tool reference in maintained docs and generated
  templates resolves against the installed registries.
- AC003: Generic, Codex and Claude outputs cover local and remote vertical
  workflows and state intentional MCP omissions.
- AC004: A project generated by an older template generation is reported as
  `template_obsolete` even when all recorded content hashes match.
- AC005: User-modified managed content is reported independently and is not
  overwritten by read-only diagnostics or an unforced update.
- AC006: A clean source initialization and a clean installed-wheel
  initialization generate semantically identical current adapter files.
- AC007: The compatibility inventory contains no unclassified runtime reader,
  writer, fallback, alias, command, MCP tool, fixture or packaged example.
- AC008: Representative obsolete forms for every memory family fail before
  writes with stable current-only diagnostics.
- AC009: CLI and MCP registries contain none of the discarded migration,
  adoption, mark-legacy or legacy-resolution operations.
- AC010: Current proposal, decision, question, permission, registry, software
  spec, publication, readiness and derived-state workflows pass focused tests.
- AC011: Maintained release and installation documentation agrees on version
  and current contract values.
- AC012: A built wheel contains only current templates, resources and examples
  and passes clean-init and agent-diagnostics smoke tests.
- AC013: The canonical project is archived, semantically inventoried and
  recreated from current public commands without a shipped converter.
- AC014: `p2p validate` reports zero errors and warnings for the recreated
  canonical project.
- AC015: Focused validation, public CLI/MCP tests and the full suite pass.

# Requirements - Separate Domain From Structure Source

## Scope

Separate the project's subject classification from the source used to create
its initial structure. A project domain becomes a free portable descriptor;
starters and exact vertical releases become mutually exclusive structure
sources.

## Origin

- Source: owner-approved cross-product architecture review dated 2026-08-25.
- Target train: P2P Engine `0.5.0`.
- Related features: `introduce-project-owned-structure` and
  `converge-project-structure-surfaces`.
- Authority dependency: `support-typed-authority-context-in-governed-mutations`.
- Compatibility policy: current-only clean break; no runtime conversion of
  workspace schema 3 domain templates.

## In Scope

- A portable `ProjectDomainRef` with free key, display name, source and optional
  opaque external reference.
- An exclusive `StructureSource` union for project initialization.
- Built-in `generic` and `empty` starters.
- Reclassification of software, board-game, grant-document and other
  structural presets as bundled vertical releases rather than domains.
- Receipt-backed project-domain set and clear operations.
- Structured CLI and local MCP read/write surfaces.
- Optional domain metadata in portable vertical packs without introducing a
  domain catalog into P2P Engine.

## Out Of Scope

- Domain ownership, visibility, moderation, ranking or recommendations.
- A mandatory WaveKit connection or WaveKit-specific authentication.
- Project-structure editing, memory classification and readiness calculation.
- Automatic replacement of project structure when the domain changes.
- Compatibility parsing for the old structural meaning of `--domain`.

## Public Surface And MCP Impact

- CLI impact: breaking initialization semantics plus additive project-domain
  read and receipt-backed mutation commands.
- MCP impact: add read parity and consent-gated domain mutation parity through
  the same domain service; WaveKit continues to use CLI, not local MCP.
- Storage impact: workspace schema 4 introduces the free domain descriptor and
  normalized structure-source provenance.
- Agent-facing behavior: generated guidance must stop describing domains as
  rubric templates.
- MCP parity decision: required because standalone agents must be able to
  inspect and change the same project classification without WaveKit.

## Functional Requirements

### Domain Descriptor

- R001: THE SYSTEM SHALL represent the current project domain independently
  from sections, fields, criteria, questions, artifacts and readiness rules.
- R002: A domain descriptor SHALL contain a normalized non-empty key, bounded
  display name, source classification and optional opaque external reference.
- R003: WHEN a user supplies a previously unknown valid domain key, THE SYSTEM
  SHALL accept it without requiring a local or remote catalog entry.
- R004: Changing or clearing the domain SHALL NOT change the current project
  structure, structure origin, proposal scopes or readiness inputs.
- R005: Domain mutation SHALL record actor, previous descriptor, new descriptor
  and current project-memory revision in an append-only mutation receipt.

### Structure Source

- R006: Initialization SHALL resolve exactly one structure source.
- R007: A structure source SHALL be either one named built-in starter or one
  exact vertical release supplied as a bundled, installed or local pack.
- R008: Supplying two structure sources SHALL fail before workspace mutation.
- R009: `generic` SHALL be a built-in cross-domain starter and SHALL NOT be a
  domain or a user-visible vertical lineage ancestor.
- R010: `empty` SHALL create no project-specific sections or readiness criteria
  and SHALL NOT disable the invariant P2P project-memory services.
- R011: Software, board-game, grant-document and other specialized structures
  SHALL be represented as exact bundled vertical releases.
- R012: The normalized initialization result SHALL expose domain, selected
  source kind, source identity, structure origin and resulting structure
  revision through a versioned JSON payload.

### Initialization And Project Domain Commands

- R013: Machine-oriented initialization SHALL require an explicit normalized
  structure source and SHALL never infer a second source from the domain.
- R014: Human-oriented initialization MAY select `generic` as a documented
  default, but its structured result SHALL report that choice explicitly.
- R015: The CLI SHALL provide structured project-domain show, set and clear
  behavior without exposing internal storage paths.
- R016: Domain set and clear SHALL require typed authority context and operation
  key in JSON mutation mode and SHALL support exact replay and mutation-status
  lookup.
- R017: Reusing an operation key with divergent semantic inputs SHALL return a
  stable idempotency conflict and perform no write.
- R018: Initialization and domain mutation SHALL remain usable fully offline.

### Portable Vertical Metadata

- R019: A portable vertical release MAY declare one primary domain reference
  and bounded secondary tags as non-governing catalog metadata.
- R020: Missing vertical domain metadata SHALL NOT prevent local install or
  project use.
- R021: Vertical domain metadata SHALL NOT inject sections, criteria or
  readiness rules independently from the pack structure.

### Current-Only Transition

- R022: Runtime `0.5.0` SHALL reject workspace schemas whose domain still owns
  structural rubric-template semantics.
- R023: Runtime `0.5.0` SHALL not silently map old `none`, `custom`, `generic`,
  `software`, `grant_document` or `board_game` domain behavior into the new
  model.
- R024: Maintained documentation SHALL identify recreation or an explicit
  external one-time conversion as the only transition for old workspaces.

### Governed Capability Contract

- R025: Project initialization SHALL declare capability `project.initialize`;
  project-domain set and clear SHALL declare `project.domain.change`.
- R026: These governed mutations SHALL consume the typed authority contract
  from `support-typed-authority-context-in-governed-mutations` and bind it to
  preview, apply, receipt and replay identity.
- R027: P2P local policy SHALL preserve standalone owner authority, while an
  external provider decides delegability; this feature SHALL NOT embed WaveKit
  roles or grant models.

## Non-Functional Requirements

- N001: Domain parsing SHALL reject path-like, control-character, oversized and
  otherwise unsafe identifiers deterministically.
- N002: Public JSON SHALL remain bounded, deterministic and path-safe.
- N003: Domain services SHALL not depend on registry credentials, networking,
  Django or WaveKit concepts.
- N004: Mutations SHALL reuse existing atomic transaction and receipt
  infrastructure.
- N005: The global `p2p-cli/v1` envelope SHALL remain unchanged unless its six
  envelope fields themselves need to change.

## Edge Cases And Errors

- Empty, malformed or oversized domain key or name.
- Domain source with an invalid opaque external reference.
- No explicit source in machine initialization.
- Starter and vertical pack supplied together.
- Unknown starter.
- Missing, corrupt or checksum-mismatched vertical pack.
- Exact retry, divergent-key retry and lost response after commit.
- Domain mutation against an unsupported workspace schema.
- Domain change while another workspace transaction is active.

## Acceptance Criteria

- AC001: An offline project initializes with arbitrary domain `gardening` and
  starter `generic` without receiving any domain-owned rubric overlay.
- AC002: An offline project initializes with arbitrary domain
  `lunar-gardening` and starter `empty` with zero structural criteria.
- AC003: An exact physical-product pack is the only structure source even when
  the current domain is `automotive`.
- AC004: Conflicting sources fail with no project-state write.
- AC005: Domain set/clear replay safely and never change structure identity or
  readiness inputs.
- AC006: Bundled specialized structures are listed and inspected as vertical
  releases, not accepted as structural domain values.
- AC007: CLI, MCP, generated guidance and maintained documentation use the new
  terminology consistently.
- AC008: Installed-wheel contract tests prove offline behavior and rejection of
  the old workspace schema.
- AC009: Local and external-authority initialization/domain mutations use the
  declared capabilities and preserve exact subject/executor receipt evidence.

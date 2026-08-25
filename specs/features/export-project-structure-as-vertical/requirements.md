# Requirements - Export Project Structure As Vertical

## Scope

Turn the current active project structure into a reusable portable vertical only
after an explicit user action. Export may declare social derivation from the
original release or create an independent vertical, without changing the
project's current structure.

## Origin

- Source: owner-approved separation of project editing and vertical authoring.
- Depends on: project-owned structure, domain/source contracts and
  `support-typed-authority-context-in-governed-mutations`.
- Target train: P2P Engine `0.5.0`, implemented only after the P1-P5 structural
  core passes its focused stability checkpoint and before the final 0.5.0
  convergence/tag gate.

## In Scope

- Read-only export preview from one exact structure revision.
- Explicit derived or independent lineage choice.
- Domain metadata for the exported vertical.
- Materialization to a vertical draft and portable schema-3 pack.
- Active structure only by default.
- Deterministic checksum, validation and structured CLI results.
- Offline standalone workflow and WaveKit worker compatibility.

## Out Of Scope

- Automatic export after project edits.
- Remote publication, authentication or moderation.
- Export of project proposal/decision contents as vertical structure.
- Automatic inclusion of retired elements or structure history.
- Applying the exported release back to the source project.

## Public Surface And MCP Impact

- CLI impact: additive preview/export commands with JSON output.
- MCP impact: eligibility and preview are read-only; durable draft/package
  creation remains CLI-only because it writes user-local artifacts and accepts
  a server/local output destination.
- Storage impact: user-local vertical draft/catalog and generated pack only;
  project structure remains unchanged.
- Agent-facing behavior: guidance must require explicit lineage choice and
  distinguish export from project editing.

## Functional Requirements

- R001: Export SHALL read one exact active project-structure revision and
  checksum without mutating the project.
- R002: Export preview SHALL report active sections, criteria, questions,
  artifacts, domain metadata, validation blockers and excluded retired counts.
- R003: Export SHALL require exact target publisher, vertical ID, semantic
  version, name, license and domain metadata.
- R004: Export SHALL require lineage mode `derived` or `independent` explicitly.
- R005: Derived export SHALL reference an exact eligible source vertical release
  selected from project origin/history and preserve required attribution.
- R006: Independent export SHALL omit social parent lineage while retaining
  legally required source attribution.
- R007: Export SHALL include active structural elements only unless a future
  contract explicitly adds historical export.
- R008: Export SHALL fail when no active section exists or when the active
  structure is invalid.
- R009: Export SHALL normalize to the current portable vertical schema and
  produce deterministic semantic and artifact checksums.
- R010: Export SHALL create or update a user-local vertical draft through the
  supported draft service and SHALL not create an automatic remote release.
- R011: Repeating export with the same operation identity and semantic inputs
  SHALL return the same result without duplicate draft/package state.
- R012: Changed project structure after preview SHALL invalidate export apply.
- R013: The source project's domain, structure, revision, readiness and origin
  SHALL remain unchanged after successful export.
- R014: The workflow SHALL function fully offline.
- R015: Durable export apply SHALL declare capability
  `project.vertical.export` and bind typed authority context, source revision,
  lineage decision and operation identity into its receipt; read-only
  eligibility and preview SHALL not fabricate mutation authority.
- R016: Local policy SHALL preserve standalone owner control while hosted
  delegability remains external-provider policy; publisher/artifact ownership
  SHALL remain distinct from project mutation authority.
- R017: MCP SHALL expose read-only export eligibility and preview over the
  shared service and SHALL NOT expose export apply, destination paths or
  package-writing behavior.

## Non-Functional Requirements

- N001: Export payloads and generated packs SHALL be deterministic and bounded.
- N002: User-controlled metadata SHALL be strictly validated and path-safe.
- N003: The worker-facing JSON result SHALL omit unsafe local paths where a
  stable artifact identifier can be used.
- N004: Export SHALL reuse portable-pack validation and draft services rather
  than introduce another pack renderer.

## Edge Cases And Errors

- Empty or invalid structure.
- Retired-only structure.
- Stale revision/checksum after preview.
- Invalid publisher, ID, version, license or lineage parent.
- Parent license disallows derivation.
- Target draft/version collision.
- Output failure or lost response after package creation.
- Offline use with no registry configured.

## Acceptance Criteria

- AC001: An active customized structure exports as a valid portable pack without
  creating another project-structure revision.
- AC002: Derived export records exact parent lineage and attribution.
- AC003: Independent export has no social parent but preserves mandatory legal
  attribution.
- AC004: Retired elements and project memory contents are absent from the pack.
- AC005: Empty export and stale apply fail without a partial draft/release.
- AC006: Exact retry is idempotent and produces deterministic checksums.
- AC007: The complete workflow works offline from an installed wheel.
- AC008: Documentation clearly separates export, local draft and remote
  publication.
- AC009: Export receipt records `project.vertical.export`, and that evidence
  neither publishes the result nor grants publisher ownership.
- AC010: MCP eligibility/preview is side-effect free and no MCP tool can create
  a draft, package or destination file.

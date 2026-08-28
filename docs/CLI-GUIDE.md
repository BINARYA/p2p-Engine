# P2P CLI Guide

This guide covers the practical command-line workflows for P2P Engine. It is not
an exhaustive generated reference; use `p2p --help` and `p2p <group> --help` for
the complete command list in your installed version.

## Principles

- Use CLI commands for P2P mutations.
- Do not edit `.p2p/` internals by hand unless repairing with explicit owner intent.
- Use `p2p context --budget small` before broad inspection.
- Owner-controlled governance actions require explicit owner instruction.
- Run `p2p validate` and `p2p registry refresh` after meaningful P2P changes.

## 1. Start A New Project

Interactive setup:

```bash
p2p init
```

Scriptable setup:

```bash
p2p init "My Project" \
  --domain software \
  --vertical binarya/software_project@2.0.0 \
  --mcp-hint
```

When `--agent` is omitted, `p2p init` uses an adaptive bootstrap default. It
installs `generic` plus the detected current adapter when detection is reliable;
otherwise it falls back to all built-in adapters and prints a warning. The
detected adapter is only a bootstrap hint, not a persisted project identity.

To narrow the generated adapters explicitly, repeat `--agent`:

```bash
p2p init "My Project" --agent codex --agent claude
```

`generic` is always included.

After init, manage the footprint with `p2p agent list`,
`p2p agent install <adapter>`, `p2p agent update <adapter>`,
`p2p agent doctor <adapter>`, `p2p agent uninstall <adapter>`, and
`p2p agent instructions refresh --profile <adapter>`.

When `--mcp-hint` is used, init prints a root-aware MCP setup section. The
preferred server command uses the absolute running P2P interpreter reported by
`p2p doctor`, followed by `-m p2p_engine.mcp.server --root /path/to/project`.
An existing POSIX/Windows project virtualenv is only a supported fallback;
`p2p-mcp-server --root /path/to/project` is offered only when it resolves on
`PATH`. The hint also reports an exact-version uv command when uv is available.
`--root` means the governed P2P decision root.

Initialization is source-control neutral: it creates neither `.git` nor
`.gitignore` and does not inspect repository status.

`--domain` records an optional free subject classification. It never chooses
sections, criteria, questions or readiness requirements. Initialization resolves one
independent structure source: `--starter generic`, `--starter empty`, or one
exact `--vertical publisher/id@version`. Human text mode defaults to the
documented `generic` starter; JSON mode requires the source explicitly.

Examples:

```bash
p2p init "Garden plan" --domain gardening --starter generic
p2p init "Lunar garden" --domain lunar-gardening --starter empty
p2p init "Software" --domain software --vertical binarya/software_project@2.0.0
```

Inspect or reclassify the domain without changing structure:

```bash
p2p project domain show --format json
p2p project domain set gardening --name "Gardening" --actor owner --operation-key local:domain-001 --format json
p2p project domain clear --actor owner --operation-key local:domain-002 --format json
```

Initialization copies the effective source into a detached, project-owned
structure. Inspect and make simple governed edits against its own revision:

```bash
p2p project structure show --format json
p2p project structure history --limit 20 --format json
p2p project structure add-section "Distribution" --expected-revision 1 \
  --operation-key local:structure-001 --format json
p2p project structure update-metadata section distribution \
  --title "Distribution model" --expected-revision 2 \
  --operation-key local:structure-002 --format json
p2p project structure reorder --section-id distribution --section-id scope \
  --expected-revision 3 --operation-key local:structure-003 --format json
p2p project structure retire preview --target section:distribution \
  --expected-structure-revision 4 --expected-memory-revision SHA256 \
  --plan retirement-plan.yml --format json
p2p project structure retire apply --target section:distribution \
  --expected-structure-revision 4 --expected-memory-revision SHA256 \
  --preview-token TOKEN --operation-key local:structure-retire-001 \
  --plan retirement-plan.yml --confirm --format json
p2p project structure retire status \
  --operation-key local:structure-retire-001 --format json
p2p project structure replace preview example/my-vertical@1.0.0 \
  --expected-structure-revision 5 --expected-memory-revision SHA256 \
  --format json
p2p project structure replace preview example/my-vertical@1.0.0 \
  --expected-structure-revision 5 --expected-memory-revision SHA256 \
  --plan replacement-plan.yml --format json
p2p project structure replace apply example/my-vertical@1.0.0 \
  --expected-structure-revision 5 --expected-memory-revision SHA256 \
  --preview-token TOKEN --operation-key local:structure-replace-001 \
  --plan replacement-plan.yml --confirm --format json
p2p project structure replace status \
  --operation-key local:structure-replace-001 --format json
```

The source release and origin checksum remain provenance only. Source updates
do not change an initialized project. Retirement is impact-previewed and
disposition-driven. Release replacement is its own higher-risk
`project.structure.replace` mutation: it copies one exact schema-3 release into
the project-owned structure, resolves required active-memory dispositions, and
does not create an active release subscription.

Typical first checks:

```bash
p2p status
p2p status --format json
p2p runtime status
p2p context --budget small
p2p context --target PROP-001 --budget small
p2p context --target PROP-001 --budget medium --format json
p2p validate
p2p registry refresh
p2p next
```

### Fast Reads And Vertical Project Memory

`p2p status`, proposal list, ordinary project progress, small context and
`p2p next` are fast or bounded reads. Their structured output states which
checks ran. They do not imply that `p2p validate` or the complete derived-state
graph ran; use `p2p validate` and `p2p project freshness` explicitly for those
deep checks.

The engine can materialize a compact, vertical-aware read model from canonical
proposal decisions, declared vertical coverage, project definition, questions,
choices and conflicts. It is derived, never an authority source, and never
claims that accepted work was implemented.

```bash
p2p project memory status --format json
p2p project memory show --limit 20
p2p project memory show --section data_model --limit 20
p2p project memory show --section data_model --include-history --limit 20
p2p project refresh
```

`status` and `show` are read-only. Section IDs are exact and list results are
bounded with source-bound cursors. A missing, stale or invalid materialization
is rebuilt in memory from canonical sources for authority-sensitive reads when
possible, without writing files. `p2p project refresh` is the explicit atomic
write that refreshes vertical memory and the existing project projections.

Supported canonical mutations may attempt a proven incremental post-commit
update. Its additive `derived_updates.vertical_project_memory` result is one of
`updated`, `unchanged`, `stale`, `failed` or `not_applicable`. A derived failure
does not roll back or reinterpret the successful canonical operation.

### Project-Memory Classification

Memory organization against the detached project structure is a separate,
canonical axis. It is not the materialized vertical-memory view above and it
is reported beside readiness, never folded into the readiness formula:

```bash
p2p project memory classification --format json
p2p proposal scope show PROP-001 --format json
p2p proposal scope set PROP-001 --kind sections \
  --section-id system_objective --section-id mvp_scope \
  --expected-memory-revision <sha256> --expected-structure-revision 1 \
  --operation-key local:scope-001 --format json
p2p proposal scope set PROP-001 --kind project_global \
  --expected-memory-revision <sha256> --expected-structure-revision 1 \
  --operation-key local:scope-002 --format json
```

New proposals start as explicit `unassigned` memory, including projects with an
empty structure. Draft work may remain unassigned, but accepting or reinstating
a proposal requires active section scope or explicit `project_global` scope.
Scope mutation requires capability `project.memory.classify`; that capability
does not authorize proposal decisions or readiness overrides.

### Runtime Contract

Project runtime compatibility is declared in `.p2p/project/runtime.yml`.
`p2p runtime status` reads that contract and compares it with the installed P2P
Engine runtime:

```bash
p2p runtime status
p2p runtime status --format json
```

The command is read-only. It does not install, upgrade, downgrade, replace, or
reconcile environments.

Status meanings:

- `compatible`: the installed runtime satisfies the project contract.
- `incompatible`: install the recommended P2P Engine version using the official
  installation guidance, then rerun `p2p runtime status`.
- `invalid_contract` or `unsupported_contract`: fix or restore the contract
  before mutating governed P2P state.
- `missing_contract`: `.p2p/project.yml` requires a contract but
  `.p2p/project/runtime.yml` is missing; restore it from project history or
  recreate the project with the current runtime.

`p2p validate` reports deterministic runtime findings, including
`P2P268_RUNTIME_SETUP_GUIDE_DRIFT` when managed `P2P-SETUP.md` no longer
matches the contract-rendered setup guide.

Project owners can preview and apply a governed runtime contract change with:

```bash
p2p runtime contract preview \
  --requires ">=0.5.1,<0.6" \
  --recommended "0.5.1" \
  --reason "Allow compatible 0.5 patch releases."

p2p runtime contract apply \
  --requires ">=0.5.1,<0.6" \
  --recommended "0.5.1" \
  --reason "Allow compatible 0.5 patch releases." \
  --expected-state-token "<token-from-preview>" \
  --confirm
```

`preview` is read-only. It validates the proposed values, classifies impacts,
checks the managed setup guide state, reports owner-authority diagnostics, and
returns an expected-state token only when the current contract is trusted and
the update is structurally applicable.

Use the exact same `--reason` for preview and apply whenever preview reports
`reason_required: true`; narrowing or otherwise strongly changing compatibility
without that reason is blocked.

`apply` rechecks the current state, owner authority, confirmation, reason
requirements, and expected-state token before writing. It updates managed
`P2P-SETUP.md` and `.p2p/project/runtime.yml` in one rollback-safe local
transaction. A handled failure restores the original bytes of both targets. It
never installs, upgrades, downgrades, or reconciles the local P2P Engine runtime.

Strong impacts such as range tightening, runtime line changes, or updates that
exclude the active runtime require `--reason`. An unmanaged `P2P-SETUP.md`
blocks apply; P2P does not overwrite human-owned setup documentation as a side
effect of a contract update.

### Current Workspace Schema

Workspace layout versioning is independent from the runtime contract. P2P
Engine 0.5.1 accepts schema 4 only. Inspect schema alignment and interrupted
transaction state without writing:

```bash
p2p workspace schema status
p2p workspace schema status --format json
p2p workspace transaction status --format json
```

Missing, older, unknown, or future schemas fail with
`P2P_WORKSPACE_UNSUPPORTED_SCHEMA`. This runtime has no workspace conversion
commands; recreate or convert such a workspace outside the runtime.

An interrupted transaction blocks unrelated governed writes. Resume or roll it
back only through the supported recovery commands:

```bash
p2p workspace transaction resume mutation-... --actor owner --confirm
p2p workspace transaction rollback mutation-... --actor owner --confirm
```

Do not edit schema state, locks, journals or candidates by hand. See
[WORKSPACE-SCHEMA.md](WORKSPACE-SCHEMA.md) for the current-only contract and
recovery preconditions.

### Project Interaction Style

Project interaction style is the project-level default for how agents and
mediators communicate with the owner. It has three independent integer scales
from `0` to `5`:

- `technical_verbosity`: how much engine and technical workflow language to use.
- `formality`: how informal or formal the owner-facing tone should be.
- `assertiveness`: how strongly agents should follow up on gaps, evidence, and ordering.

Missing configuration is valid and uses defaults:

```text
technical_verbosity=2
formality=2
assertiveness=0
```

Inspect the effective style:

```bash
p2p project interaction-style show
```

Set one or more values:

```bash
p2p project interaction-style set --technical-verbosity 3
p2p project interaction-style set --formality 1 --assertiveness 2 --actor owner
```

Style changes presentation and follow-up pressure only. They do not change
governance authority, readiness scores, validation truth, permissions, consent,
or facts. Agents and owners should use this CLI surface, or the matching MCP
tools, instead of editing `.p2p/project/interaction-style.yml` directly.

`p2p next` combines curated project actions with generated actions derived from
project state. Manage curated actions through CLI commands instead of editing
`.p2p/project/next-actions.yml` by hand:

```bash
p2p next list
p2p next add verify_integration mcp-client --priority high --reason "Verify real MCP client setup." --command "p2p-mcp-server --root /path/to/project"
p2p next complete NEXT-003 --reason "Consolidated in commit abc1234."
p2p next retire NEXT-004 --reason "Superseded by a newer proposal."
p2p next refresh
```

Completed and retired curated actions are moved to
`.p2p/project/next-actions-log.yml`.

Generated choice actions use canonical project-choice nodes and normalized
relations. Proposal-local votes are evidence attached to a proposal and never
become project choices. Active `choice -> blocks -> proposal/change` relations
retain highest precedence; decided choices and missing relation targets do not
produce resolution actions. Change Set status still comes from its lifecycle
reader, while included-proposal context comes from normalized relations.

Every non-terminal Change Set produces one generated `continue_change` action.
Generated Change Set IDs use `NEXT-CHANGE-<CHANGE-ID>` and remain stable when
registry order or unrelated actions change. Actions are ordered by lifecycle
priority and then Change Set ID. `--top` is applied only after complete
composition and curated/generated deduplication; omit it to inspect the full
set. A curated action with the same `(kind, target)` remains authoritative in
the displayed list. `p2p next refresh` normalizes only curated records and
reports the complete generated count without persisting generated actions.

`.p2p/registries/relations.yml` remains a backward-compatible generated
projection. It is not a semantic source for decision context or next actions;
editing it cannot change normalized topology.

Inspect the two independent project progress axes and the complete derived-state
rebuild order with read-only commands:

```bash
p2p project progress --format json
p2p project freshness --format json
```

Definition completeness is not implementation completeness. Declared vertical
coverage contributes evidence authority; heuristic suggestions remain advisory.
Freshness actions identify deterministic commands separately from agent-curated,
owner-review and approval boundaries.

## 2. Define Project Verticals And Capisaldi

Project verticals are immutable pure-data releases used to seed or exchange a
structure. They describe sections, rubrics, questions and expected artifacts,
but after initialization the detached project-owned structure is authoritative.

List and inspect verticals:

```bash
p2p project vertical list
p2p project vertical list --format json
p2p project vertical show base_project
p2p project vertical show social_impact_program_design
p2p project context --format json
p2p project sections --format json
p2p project definition show --format json
```

Unqualified `p2p project sections` reads the project-owned structure. Supplying
a vertical coordinate explicitly inspects catalog content. Active-vertical and
lock commands are transitional release-lifecycle surfaces and do not define the
live project shape.

P2P Engine accepts schema-3 canonical multi-file packs only:

```text
<pack-root>/
  manifest.yml
  vertical.yml
  sections/<section-id>.yml
  rubrics.yml
  profiles/<profile-id>.yml
  modules/<module-id>.yml
  artifacts/<artifact-id>.yml
  examples/<example-id>.md
```

`vertical.yml` contains metadata only. Sections, rubrics and optional profile,
module, artifact and example content live in their canonical split paths.
`manifest.yml` may add advisory `primary_domain` and `domain_tags` metadata;
these values never select structure or change the project's domain.

The bundled releases use exact `binarya/<vertical-id>@2.0.0` coordinates.
Bare IDs work only when they resolve to one coordinate. Multiple releases make
a bare ID ambiguous, while semantically different packs claiming the same
coordinate fail with `P2P_VERTICAL_COORDINATE_CONFLICT`; no source precedence
silently chooses one. Schema-1, schema-2 and single-file packs are unsupported.

### Portable Versioned Packs

Schema-version-2 packs add a publisher, exact semantic version, license,
optional social lineage, and exact dependency checksums. Their identity is the
coordinate `publisher/vertical-id@version`. Structural `extends`, social
`lineage.forked_from` and release-history `lineage.previous_release` are
separate declarations.

P2P Engine 0.5 provides a local catalog and a provider-neutral v2 remote
registry client. These commands perform no remote request unless `--refresh`
is passed to `registry list` or a remote discovery source is explicitly
selected:

```bash
p2p version --format json
p2p vertical list --format json
p2p vertical inspect binarya/software_project@2.0.0 --format json
p2p vertical registry add wavekit https://registry.example.test --default
p2p vertical registry list --format json
p2p vertical registry remove wavekit
```

Registry configuration is stored under `P2P_HOME` when set, otherwise under
the platform user-data directory. HTTPS is required except for explicit
loopback development URLs. Configuration files never contain credentials.

Remote discovery and retrieval are explicit:

```bash
p2p vertical registry list --refresh
p2p vertical domain list --registry wavekit
p2p vertical domain search software --registry wavekit
p2p vertical domain inspect dom-software --registry wavekit
p2p vertical search software --registry wavekit
p2p vertical search software --registry wavekit --domain dom-software
p2p vertical list --source remote --registry wavekit
p2p vertical list --source remote --registry wavekit --domain dom-software
p2p vertical login wavekit
p2p vertical list --source remote --registry wavekit --include-private
p2p vertical pull example/software-blue@1.0.0 --registry wavekit
p2p vertical logout wavekit
```

Catalog domains and `primary_domain` release metadata are advisory discovery
metadata. They are not project domains, do not select structure, and do not
prove semantic compatibility. Recommendations never trigger pull or
initialization by themselves. Login uses the registry-advertised OAuth device
flow and stores credentials in the operating-system keyring. Pull verifies the
exact dependency closure, artifact SHA-256, size, schema and semantic checksums
before committing the immutable user cache. See
[VERTICAL-REGISTRY.md](VERTICAL-REGISTRY.md) for the protocol and cache
contract.

Normalized draft authoring is available without writing canonical YAML by
hand:

```bash
p2p vertical draft create --empty --format json
p2p vertical draft create --from binarya/software_project@2.0.0 \
  --version 2.0.1 --previous-release binarya/software_project@2.0.0 \
  --format json
p2p vertical draft inspect VDRAFT-... --format json
p2p vertical draft update VDRAFT-... --document ./vertical.json \
  --expected-revision 1 --format json
p2p vertical draft materialize VDRAFT-... ./build/vertical --format json
p2p vertical draft validate VDRAFT-... --format json
p2p vertical draft package VDRAFT-... ./build/vertical.p2pv --format json
p2p vertical draft add-local VDRAFT-... --format json
p2p vertical draft publish VDRAFT-... --registry wavekit \
  --idempotency-key <operation-id> --format json
```

Draft state lives outside `.p2p`; edits invalidate all materialization and
publication evidence. See [VERTICAL-DRAFTS.md](VERTICAL-DRAFTS.md).

Local authoring and the existing WaveKit local-artifact handoff remain
available:

```bash
p2p project vertical schema --format json
p2p project vertical scaffold ./my-vertical \
  --publisher example --id my-vertical --version 1.0.0 --license MIT
p2p project vertical inspect ./my-vertical --view declared --format json
p2p project vertical package ./my-vertical --output ./my-vertical.p2pv
p2p project vertical validate ./my-vertical.p2pv --format json

p2p project vertical install preview ./my-vertical.p2pv \
  --expected-checksum <sha256> --actor owner --format json
p2p project vertical install apply ./my-vertical.p2pv \
  --expected-checksum <sha256> --token <preview-token> \
  --idempotency-key <operation-uuid> \
  --confirm --actor owner --format json
```

To reuse the current project-owned structure as a new portable vertical, export
it through a token-bound preview/apply workflow:

```bash
p2p project vertical export eligibility --format json
p2p project vertical export preview \
  --publisher example --id my-vertical --version 1.0.0 \
  --name "My Vertical" --license MIT \
  --primary-domain-key software --primary-domain-name "Software" \
  --lineage-mode independent --format json
p2p project vertical export apply \
  --target ./build/my-vertical \
  --output ./build/my-vertical.p2pv \
  --publisher example --id my-vertical --version 1.0.0 \
  --name "My Vertical" --license MIT \
  --primary-domain-key software --primary-domain-name "Software" \
  --lineage-mode independent \
  --expected-structure-revision <revision-from-preview> \
  --expected-structure-checksum <checksum-from-preview> \
  --token <preview-token> \
  --idempotency-key <operation-uuid> \
  --confirm --actor owner --format json
```

Preview is read-only and binds the exact `ProjectStructure` revision, checksum
and active semantic hash. Apply rejects stale tokens, exports active sections,
fields, questions, criteria and artifacts only, and uses the existing vertical
draft materialize/validate/package pipeline to produce a schema-3 `.p2pv`
artifact offline. `--lineage-mode derived` additionally requires an exact
parent coordinate and semantic checksum; `independent` omits social parent
lineage while preserving required attribution.

To replace the active project-owned structure from a reusable release, use the
structure replacement workflow instead of `adopt` or `migrate`:

```bash
p2p project structure replace preview example/my-vertical@1.0.0 \
  --expected-structure-revision <current-revision> \
  --expected-memory-revision <current-memory-sha256> \
  --format json
p2p project structure replace preview example/my-vertical@1.0.0 \
  --expected-structure-revision <current-revision> \
  --expected-memory-revision <current-memory-sha256> \
  --plan replacement-plan.yml \
  --format json
p2p project structure replace apply example/my-vertical@1.0.0 \
  --expected-structure-revision <current-revision> \
  --expected-memory-revision <current-memory-sha256> \
  --preview-token <preview-token> \
  --operation-key <operation-uuid> \
  --plan replacement-plan.yml \
  --confirm --actor owner --format json
p2p project structure replace status \
  --operation-key <operation-uuid> --format json
```

The first preview reports preserved, added, retired and conflicting stable
IDs plus required dispositions. A complete
`p2p-structure-replacement-plan/v1` binds the exact target coordinate and
semantic checksum; the second preview returns the apply token. Apply rechecks
the target bytes, source structure revision, memory revision, authority context
and operation key, then writes structure, memory dispositions, replacement
event and receipt atomically. Future publication of the source release does not
modify the project.

Portable versions are installed side by side under:

```text
.p2p/project/verticals/_portable/<publisher>/<vertical-id>/<version>/
```

Dependencies must already be locally available at their exact coordinates and
must match their declared semantic checksums. P2P never resolves a floating
version or silently upgrades a project.

Use exact coordinates for portable automation. A bare ID is accepted only when
it identifies one unambiguous portable coordinate. If multiple versions share
the ID, resolution fails with `P2P_VERTICAL_AMBIGUOUS_REFERENCE`; callers must
use `publisher/id@version`. If one exact coordinate is discovered with
different semantic checksums, resolution fails with
`P2P_VERTICAL_COORDINATE_CONFLICT` instead of applying source precedence.
Schema-1 packs are rejected with `P2P_VERTICAL_UNSUPPORTED_SCHEMA`.

For a new project, installation and selection can be requested together. Pack,
checksum, dependencies, profile and modules are checked before project files
are created:

```bash
p2p init "My Project" \
  --vertical-pack ./my-vertical.p2pv \
  --expected-checksum <sha256> \
  --owner owner
```

An exact bundled or cached coordinate initializes without network access:

```bash
p2p init "My Project" --vertical example/my-vertical@1.0.0
```

Network retrieval during init requires explicit consent:

```bash
p2p init "My Project" --vertical example/my-vertical@1.0.0 \
  --pull --registry wavekit
```

The following `adopt` and `migrate` commands are transitional release-lifecycle
surfaces. They can update active-release metadata and legacy projections, but
they never replace the canonical `ProjectStructure`. A project initialized as
`empty` therefore remains structurally empty after `adopt`. Replacing a live
structure is a separate impact-aware mutation and must not be inferred from
these commands. `migrate` can still report definition, question and rubric
effects and remains fail-closed when explicit transition decisions are missing:

```bash
p2p project vertical adopt preview example/my-vertical@1.0.0 --actor owner
p2p project vertical adopt apply example/my-vertical@1.0.0 \
  --token <preview-token> --idempotency-key <operation-uuid> \
  --confirm --actor owner

p2p project vertical migrate preview example/my-vertical@2.0.0 \
  --actor owner --format json
p2p project vertical migrate preview example/my-vertical@2.0.0 \
  --mapping vertical-transition-plan.yml --actor owner --format json
p2p project vertical migrate apply example/my-vertical@2.0.0 \
  --mapping vertical-transition-plan.yml --token <replacement-preview-token> \
  --idempotency-key <operation-uuid> \
  --confirm --actor owner
```

Example exact transition plan:

```yaml
vertical_transition_plan:
  schema_version: 1
  contract_version: p2p-vertical-transition-plan/v1
  analysis_fingerprint_sha256: <analysis-fingerprint>
  decisions:
    - id: <decision-id-from-preview>
      action: map
      source:
        kind: definition_field
        ref: definition_field:old_section.old_field
      target:
        kind: definition_field
        ref: definition_field:new_section.new_field
```

The 0.5.1 JSON transport contract is `p2p-cli/v1`. Every command supporting
`--format json` returns exactly `contract_version`, `ok`, `operation`, `data`,
`warnings`, and `error`. Domain payloads remain operation-specific under
`data`. Parser errors use the same envelope. See
[CLI JSON Contract](CLI-CONTRACT.md) for operation IDs, exit classes and
consumer integration. `p2p version --format json` and
`p2p status --format json` expose the exact release contract tuple needed by
collaborators and WaveKit workers, including workspace schema, portable
vertical schema, registry-v2, draft, readiness, AuthorityContext and receipt
versions. Preview operations do not write state; apply requires the
current token, explicit confirmation, actor and a caller-supplied idempotency
key. Use the same key only to retry the exact same request. After an uncertain
response, inspect the durable result without writing:

```bash
p2p mutation status --operation-key <operation-uuid> --format json
```

`applied` confirms matching committed postconditions, `not_found` permits an
exact apply retry, `postcondition_drift` requires investigation and
`incomplete` routes to `p2p workspace transaction status` and explicit
recovery.

WaveKit-style server workers should use the allowlisted CLI JSON contract for
deterministic reads, writes and recovery:

```bash
p2p version --format json
p2p status --format json
p2p project snapshot --format json
p2p proposal list --format json
p2p proposal show PROP-001 --format json
p2p proposal create "Title" --format json --operation-key wavekit:<uuid>
p2p proposal update PROP-001 --proposal "..." --format json --operation-key wavekit:<uuid>
p2p proposal contribution add PROP-001 "Text" --type suggestion --format json --operation-key wavekit:<uuid>
p2p proposal contribution list PROP-001 --type suggestion --format json
p2p mutation status --operation-key wavekit:<uuid> --format json
```

Local MCP stdio remains an agent tool surface with protocol-native payloads. It
is not wrapped in `p2p-cli/v1` and does not replace the worker
`--operation-key` retry boundary.

Vertical impact uses `p2p-vertical-transition-impact/v1`. Public output omits
project evidence values, question answers, free-form assumption/blocker text,
filesystem paths, physical hashes and generic preview internals. Collections
are bounded to 128 items and a transition to 512 material items; a truncated
material impact blocks apply.

Selecting a vertical writes explicit project state:

```text
.p2p/project/vertical.yml
.p2p/project/vertical.lock.yml
.p2p/project/definition.yml
.p2p/project/rubrics.yml
```

Transitional source selection and lock artifacts are never repaired by
project-structure reads. An explicit lock repair only repairs source metadata;
it does not edit the canonical structure:

```bash
p2p project vertical lock repair --actor owner
```

Definition state is updated through structured patch files, not arbitrary YAML
editing:

```bash
p2p project definition update definition-patch.yml --format json
```

Vertical pack text is declarative domain data. It can define questions,
examples, fields, and rubrics, but it cannot override system, developer,
governance, repository, safety, or tool-permission rules.

Project readiness v2 reads the current project-owned structure and current
project memory without mutating either one. Definition completeness and declared
evidence coverage are separate weighted axes; retired and not-applicable
criteria are excluded, and a structure with no applicable active criteria
returns `not_configured` with no numeric score:

```bash
p2p project readiness review
p2p project readiness review --vertical social_impact_program_design
p2p project readiness gaps --limit 20 --format json
p2p project readiness questions status --format json
p2p project readiness questions next --format json
```

The review reports the `p2p-project-readiness/v2` contract, source identity,
prioritized typed gaps, bounded diagnostics and concrete next operations.
Memory classification debt is guidance only and does not change the readiness
score. On workspace schema v4, project questions live in
`.p2p/project/questions.yml`; definition `open_questions` remain empty.

Only the declared project owner can answer, replace, defer, mute, reopen or
apply owner evidence. Recording an answer does not change project definition:

```bash
p2p project readiness questions answer PRQ-... \
  --value "Owner answer" --actor owner --expected-revision 1
p2p project readiness preview --question PRQ-... --actor owner --format json
p2p project readiness apply --question PRQ-... \
  --preview-token '<token>' --actor owner --confirm
```

Convergence commits definition and question state in one transaction. If the
vertical changes while question evidence exists, use `questions
reconcile-preview` and `reconcile-apply`; reconciliation never copies an answer
to a semantically different target.

The pre-0.5 vertical-coverage commands remain a transitional derived-memory
surface. They are not memory classification and do not satisfy readiness
evidence:

```bash
p2p proposal vertical-coverage show PROP-001 --format json
p2p proposal vertical-coverage suggest PROP-001 --format json
p2p proposal vertical-coverage preview PROP-001 coverage.yml --actor owner
p2p proposal vertical-coverage import PROP-001 coverage.yml \
  --preview-token '<token>' --actor owner --confirm
```

They are not the current structural authority and cannot satisfy the proposal
decision scope gate. Use `proposal scope` for new classification writes.
Project definition and bounded project metadata use their existing
preview/resupplied-patch/apply contract:

```bash
p2p project definition preview definition-patch.yml --actor owner
p2p project definition apply definition-patch.yml \
  --preview-token '<token>' --actor owner --confirm
p2p project metadata preview metadata-patch.yml --actor owner
p2p project metadata apply metadata-patch.yml \
  --preview-token '<token>' --actor owner --confirm
```

```yaml
vertical_coverage:
  schema_version: 1
  proposal_id: PROP-001
  vertical_id: social_impact_program_design
  sections:
    - id: measurement_reporting
      relevance: direct
      rationale: The proposal defines outcome metrics and reporting cadence.
      source: declared
```

`p2p validate` checks the project-owned structure and event head, project-local
vertical packs, optional transitional vertical/lock state, definition state,
safety/trust issues, and declared proposal coverage when present. Remote
vertical registries are deferred.

### Correct Legacy Semantic Artifacts

Existing impact and conflict records can be corrected without append-as-repair
or direct artifact edits. Preview reparses the complete resupplied content and
returns a token tied to source preconditions and candidate semantics:

```bash
p2p impact preview PROP-001 impact-artifacts/ --actor owner --format json
p2p impact apply PROP-001 impact-artifacts/ \
  --preview-token '<token>' --actor owner --confirm

p2p conflict show CONFLICT-001 --format json
p2p conflict preview-update CONFLICT-001 conflict-patch.yml \
  --actor owner --format json
p2p conflict update CONFLICT-001 conflict-patch.yml \
  --preview-token '<token>' --actor owner --confirm
```

Impact apply validates the complete supplied artifact set before atomically
replacing any target. Conflict update validates proposal ids, winner/rejected
consistency, reason and provenance for the stable conflict id.

## 3. Manage Agent Integrations

Installed project-local agent integrations are tracked in:

```text
.p2p/agent-integrations.yml
```

Use lifecycle commands instead of editing generated files or the registry by
hand:

```bash
p2p agent list
p2p agent show codex
p2p agent install cursor
p2p agent update all
p2p agent doctor all
p2p agent uninstall cursor
```

`agent list` and `agent show` report adapter health and file status. `update`
refuses to overwrite drifted generated files unless `--force` is used. Force is
scoped to the named adapter target and does not rewrite drifted files belonging
only to another adapter. `uninstall` removes only clean, managed, non-shared
files. `generic` cannot be uninstalled.

`agent doctor [adapter|all]` reports structured health findings and exits with
code `1` when agent-specific errors are found. `p2p validate` also checks the
agent integration registry for safe paths, known adapters, required metadata,
missing managed files, and hash mismatches.

Expected shape:

```text
P2P compact context
  budget: small
Current state:
  validation:
    ok: True
Next actions:
  ...
```

For a valid `PROP-*` target, the packet also contains versioned
`nearby_context`. It ranks only relevant proposal/decision/choice context and
reports the source fingerprint, completeness, score reasons, evidence and
truncation counts. `small` is direct and compact; `medium` can include one
bounded topology hop, qualifiers, non-goals and historical alternatives.
Empty retrieval is explicit and never falls back to the first registry records.

Source and semantic fingerprints are content/policy identities, not timestamps.
They change when an expected source appears, disappears or changes bytes, or
when extractor/authority/relation policy versions change. Retrieval and budget
policy versions identify the selected packet semantics. Ordinary context,
intake and prompt requests rebuild in memory and write no decision-context
manifest or cache.

Text renders the strongest reason for each selected owner. `--format yaml` and
`--format json` expose the same service-selected structure without reranking.
No-target, `CHANGE-*`, `CHOICE-*` and `WORK-*` contexts keep nearby retrieval
disabled.

### Decision-Context Source Boundary

The decision-context index is a derived, read-only view. Canonical proposal and
decision Markdown, governed proposal artifacts, project choices/conflicts,
Change Set links, Work manifests, vertical coverage and bounded governance or
project-definition sources provide evidence. `.p2p/` remains authoritative.

Generated registries (including `relations.yml`), `decisions-map.yml`, project
briefs and narratives, generated prompts, `outputs/` publications and any future
cache are excluded from semantic extraction. They may consume the index but can
never feed their own projection back into it.

## 4. Capture A Rough Idea

Use intake when the input is messy, overlapping, or not ready to become a
proposal.

```bash
p2p intake prompt "We may need a local MCP server, but it must not bypass owner decisions."
p2p intake status
```

The prompt workflow creates an intake folder and a prompt for human or AI
analysis. Its semantic project section is selected from the raw idea with the
versioned `medium` decision-context budget. Registry status and project overview
remain separate metadata; proposal, decision and relation registries are not
sampled by ID or file order. A generic or unsupported idea produces an explicit
empty neighborhood instead of unrelated records.

`explore`, `impact` and `synthesize` prompts use the same bounded retrieval for
their proposal target. Exploration receives nearby constraints, alternatives
and evidence; impact receives normalized selected relations and distinguishes
heuristic retrieval signals from topology edges; synthesis receives
authoritative constraints, decided choices and historical alternatives. These
sections are read-only prompt evidence. Import and apply steps remain controlled:

```bash
p2p intake import INTAKE-001 intake-output/
p2p intake apply plan INTAKE-001
p2p intake apply show INTAKE-001
```

Only run an apply action after reviewing what it will do:

```bash
p2p intake apply run INTAKE-001 --action APPLY-001
```

## 5. Create And Refine A Proposal

Create a structured proposal:

```bash
p2p proposal create "Local MCP Server" \
  --problem "Agents need bounded access to P2P project state." \
  --context "The CLI is the source of truth, but MCP clients need tool calls." \
  --goal "Expose read-only project context through a local stdio server." \
  --non-goal "Let agents accept proposals or decide choices." \
  --proposal "Add a local MCP server with read-only status, context, registry, and proposal tools." \
  --acceptance "An MCP client can call p2p_context before reading project files." \
  --acceptance "No MCP tool makes owner governance decisions."
```

Inspect and update:

```bash
p2p proposal list
p2p proposal show PROP-001
p2p proposal show PROP-001 --full
p2p proposal update PROP-001 --goal "Keep tool boundaries explicit."
```

Add review material without rewriting the proposal:

```bash
p2p contribution add PROP-001 \
  "The MCP surface should label read-only and write-safe tools clearly." \
  --type constraint \
  --relevance high
```

Proposal authoring is command-driven. New proposals may omit narrative artifact
files such as `findings.md`, `alternatives.md`, `open-questions.md`, `risks.md`,
`assumptions.md`, `suggested-scope.md`, and `exploration.md` until meaningful
content is imported or generated. Treat those absent files as missing evidence,
not corrupted project state, and use P2P commands instead of editing `.p2p/`
files directly.

Canonical contribution concepts include `finding`, `open_question`,
`alternative`, `risk`, `assumption`, `constraint`, `objection`,
`implementation_suggestion`, and `scope_boundary`. Existing contribution types
such as `suggestion`, `objective`, and `alternative_proposal` remain supported
for compatibility.

When readiness is weak, use proposal questions to run a deterministic interview:

```bash
p2p proposal readiness init PROP-001
p2p proposal readiness review PROP-001
p2p proposal artifact status PROP-001
p2p proposal artifact set PROP-001 impact_map \
  --status not_applicable \
  --reason "This proposal does not affect other project areas."
p2p proposal questions init PROP-001
p2p proposal questions add PROP-001 \
  --gap alternatives_quality \
  --priority high \
  --question "Which alternative should be compared first?"
p2p proposal questions next PROP-001
p2p proposal questions answer PROP-001 Q001 "Use a first-class CLI object."
p2p proposal questions apply PROP-001
p2p proposal readiness assess PROP-001
```

`readiness refresh` remains conservative. Use `readiness assess` after proposal
or question updates when you want evidence-aware recalculation from current
artifacts. `questions apply` returns an artifact update plan; update the useful
affected artifacts before relying on the new readiness score.

Server workers request the same recalculation with a durable retry identity:

```bash
p2p proposal readiness assess PROP-001 \
  --actor wavekit-user \
  --operation-key wavekit:<uuid> \
  --format json
```

The command returns `proposal.readiness.assess` in the `p2p-cli/v1` envelope.
Use `p2p mutation status --operation-key wavekit:<uuid> --format json` after an
uncertain response. Use `p2p proposal show PROP-001 --format json` for ordinary
reads: `proposal_detail.readiness.freshness` reports `not_assessed`, `current`
or `stale` without recalculating or writing.

Proposal readiness requires `questions.yml` as the structured source of truth
for owner-question resolution. `open-questions.md` remains human-readable
narrative evidence and never substitutes for missing structured state. It does
not reopen applied, retired, superseded, muted, or deferred structured
questions. `readiness assess`, `readiness explain`, and
`readiness review` can show `owner_question_state` categories such as blocking
owner questions, answered-not-applied questions, residual follow-up, and closed
questions.

Artifact state is the structured coverage surface for proposal artifacts. New
proposals initialize its complete current catalog by default. Missing or
incomplete `artifact-state.yml` is rejected and is not synthesized during a
read. Agents should use `p2p proposal artifact ...` commands or explicit MCP
write tools to update artifact coverage; they should not edit `.p2p` files
directly or copy temporary files into managed proposal artifacts.

`p2p proposal show PROP-001 --format json` returns the bounded
`proposal_detail` read model used by machine consumers. It keeps readiness
separate from artifact status, includes structured contributions, grouped
question sources, narrative/imported artifact summaries and next actions.

`p2p proposal show PROP-001 --full` renders the owner-facing full review view.
It keeps readiness separate from artifact status, includes structured
contributions, groups structured owner questions separately from analytical
`open_question` contributions and legacy `open-questions.md` artifacts, and
summarizes narrative/imported artifacts. Paths in that output are source or
evidence hints only; follow the displayed P2P commands for changes.

## 6. Decide A Proposal

Proposal decisions require `proposal.decide`. In local-policy projects this
preserves the owner-controlled flow. External-attestation projects may use a
delegated subject when the trusted provider supplies an exact typed context.
Schema-4 decisions are append-only events in
`decision-events.yml`; `decision.md` and the proposal status are deterministic
projections.

```bash
p2p decision status PROP-001
p2p decision history PROP-001 --limit 20
```

Every decision write is two-phase. The preview is read-only and returns the
canonical `decided_on`, `operation_key`, source head and `preview_token`:

```bash
p2p decision preview PROP-001 \
  --event-type accepted \
  --reason "The read-only MCP boundary is clear." \
  --actor owner \
  --format json
```

Apply by resubmitting the exact normalized inputs from that response:

```bash
p2p decision apply PROP-001 \
  --event-type accepted \
  --reason "The read-only MCP boundary is clear." \
  --actor owner \
  --decided-on '<preview-decided-on>' \
  --operation-key '<preview-operation-key>' \
  --preview-token '<preview-token>' \
  --confirm
```

For hosted authority, add the same `--authority-context context.json`,
`--actor`, `--executor-actor` and `--executor-kind` to preview and apply. The
context digest and the distinct subject/executor identities are persisted in
the decision event and mutation receipt. `--override-readiness` additionally
requires a root-authority `proposal.readiness.override` claim. See
[`AUTHORITY-CONTEXT.md`](AUTHORITY-CONTEXT.md).

`proposal accept`, `proposal reject`, `proposal defer`, and `decision record`
are deliberate convenience entries into the same current decision service. Without a token they only return
`preview_required`; they write only when rerun with the returned date,
operation key, source head when present, token, and `--confirm`.

Rejection is an initial decision for a proposal that was never active.
Revocation closes the authority of a previously accepted proposal without
deleting its rationale or rewriting dependent Change Sets, Work, specs, or
publication state. Inspect complete dependency impact before revocation:

```bash
p2p decision impact PROP-001 --event-type revoked --format json
p2p decision preview PROP-001 \
  --event-type revoked \
  --reason "The accepted direction is no longer valid." \
  --source-head-event-id '<current-head>' \
  --impact-preview-token '<impact-token>' \
  --acknowledge-drift \
  --format json
```

Use `reinstated` only with the original accepted event and matching revocation
references. Use typed lineage for `superseded`, `split`, and
`merged_into_other`. P2P Engine has no branch accept/reject commands:
source-control operations are external and never append proposal decision
events.

Projection and ledger repair have separate preview/apply commands:

```bash
p2p decision projection-repair-preview PROP-001
p2p decision ledger-repair-preview PROP-001 --candidate reviewed-ledger.yml
```

After an applied decision:

```bash
p2p registry refresh
p2p validate
```

## 7. Compare Alternatives With Choices

Use choices when the project needs an explicit selection between alternatives.

```bash
p2p choice create \
  --title "MCP write boundary" \
  --option "Read-only tools only" \
  --option "Write-safe draft tools" \
  --option "Full governance tools"
```

Inspect and decide:

```bash
p2p choice list
p2p choice show CHOICE-001
p2p choice decide CHOICE-001 \
  --option "Write-safe draft tools" \
  --reason "Draft mutations are useful, while owner decisions remain outside MCP."
```

Advisory discovery does not modify project state:

```bash
p2p choice discover
```

## 8. Create A Change Set

Create Change Sets from accepted intent:

```bash
p2p change create --from PROP-001
p2p change status
p2p change show CHANGE-001
```

Move lifecycle state when work planning changes:

```bash
p2p change set-status CHANGE-001 planned
p2p change tasks CHANGE-001
```

Change Sets are metadata first. They describe operational work derived from
accepted project intent; they do not replace Git commits or code review.

## 9. Export The Visible Project Definition

The default human-facing project definition is domain-aware and visible from the
repository root:

```bash
p2p project export
p2p project export-status
```

The default export writes:

```text
outputs/
  latest/
    project.md
    exports/
  review-001/
```

`outputs/latest/project.md` is generated output for humans and agents. `.p2p/`
remains the managed source of truth. Re-running the export archives the previous
`outputs/latest/` under the next `outputs/review-###/` directory before writing
a new latest version.

## 10. Publish Human Project Editions

Publication turns governed evidence into an autonomous project document for a
reader who does not need to know P2P. English is the default; language editions
share the same project scope but have independent files, freshness, rendering,
and owner review.

```bash
p2p project publish prepare --language en --output-name project --contributions auto
p2p project publish import drafts/project-publication/project-en.md \
  --model drafts/project-publication/project-en.model.yml \
  --evidence-accounting drafts/project-publication/project-en.evidence.yml \
  --language en --output-name project
p2p project publish validate --language en --output-name project
p2p project publish render --language en --output-name project
p2p project publish review --language en --output-name project \
  --status approved --reviewer owner
p2p project publish status --language en --output-name project
p2p project publish list
```

`--language` accepts normalized BCP 47 tags. Aliases `eng` and `ita` normalize to
`en` and `it`. `--output-name` is a lowercase ASCII slug. Together they form the
edition key, for example `project-en` or `manual-it`.

`prepare` writes one shared complete evidence index at
`outputs/latest/publication-evidence.yml` and edition metadata under
`outputs/latest/publications/<edition-key>/`. The packet names the exact three
candidate paths under `drafts/project-publication/`; it does not embed the full
visible export. Contribution policy is `auto`, `include`, or `omit`.
When included, contribution percentages are a deterministic distribution of
selected attributed records, including an explicit unattributed denominator.
They do not measure effort, merit, ownership, or intellectual-property shares.
The curator must preserve the prepared figures and add the supplied limitation
in the edition language.

The curator builds a project model, accounts for every evidence ID, and writes
reader Markdown in the selected language. `import` validates and atomically
commits that triplet. The final Markdown is
`outputs/latest/<edition-key>.md`; model, accounting, validation, and review
remain edition sidecars.

Validation checks the complete hash chain and structural reader contract. It
does not require an English `Executive Summary` heading or `.p2p` boilerplate in
reader prose. Internal proposal, decision, Change Set, and Work IDs are rejected
from normal prose; traceability remains in sidecars.

`render` writes `outputs/latest/<edition-key>.pdf` only after validation passes.
PDF support is optional through `p2p-engine[pdf]` and WeasyPrint. The HTML
language and title come from the selected edition and model.

Review is owner-controlled and edition-specific. Approval of one language never
approves another. For compatibility, a successful default `project-en` import
and render also update `project.curated.md` and `project.pdf` aliases. Those
aliases are not v2 freshness inputs, and legacy v1 review approval is never
copied into a v2 edition.

## 11. Generate And Export Software Specs

For software projects, a Change Set can still produce a P2P-native spec and
optional agent-first export documents for generic, OpenSpec, or Spec Kit
handoff. This is a compatibility/software-oriented workflow, not the default
project definition export.

Inspect the lifecycle route before generating or exporting durable artifacts:

```bash
p2p spec lifecycle --intent implementation_spec --change CHANGE-001
p2p spec lifecycle --intent downstream_export --change CHANGE-001 --target speckit
```

```bash
p2p spec refresh --change CHANGE-001
p2p spec status
p2p spec show CHANGE-001
p2p spec prompt --change CHANGE-001
```

`refresh` and `export` run the same lifecycle preflight. Blockers such as a
missing governed Change Set source stop the write; advisories such as inactive
`software_project` vertical coverage are reported without blocking generation.

`refresh` renders a pure candidate from the Change Set `change.md`,
`tasks.yml`, and the `proposal.md` of each included proposal. Generated
`provenance.yml` records versioned relative-source SHA-256 digests, a source
fingerprint, renderer version, origin, and generated-output digests. Absolute
checkout paths and mtimes are not fingerprint inputs. The seven required files
are committed atomically, and refreshing an unchanged current spec does not
rewrite bytes or mtimes.

`p2p spec status` preserves the completeness value (`generated` or
`incomplete`) and adds semantic freshness. Freshness can be `current`,
`current_imported`, `stale`, `modified`, `invalid`, or `incomplete`.
Generated specs are verified against deterministic provenance and output
digests; imported specs use explicit imported provenance. Missing or
unsupported provenance is invalid and is never guessed from age. CLI and MCP
status reads never refresh or overwrite a spec.

After reviewing refined spec output:

```bash
p2p spec import CHANGE-001 spec-output/
p2p spec export --change CHANGE-001 --target speckit
p2p spec export-status
p2p spec export-validate CHANGE-001 --target speckit
```

Primary export shapes:

```text
generic/
  project.md
  propose.md

openspec/
  propose.md

speckit/
  speckit.constitution.md
  speckit.specify.md
  speckit.plan.md
```

## 12. Manage Work Metadata

Work commands manage logical planning and handoff metadata for P2P-managed work.

```bash
p2p work plan --change CHANGE-001 --target speckit
p2p work list
p2p work status
p2p work show WORK-001
p2p work retire WORK-001 --reason "The planned handoff is no longer needed."
```

Branches, commits, review, merge and publication are external delivery-system
concerns and are not inferred from Work status.

## 13. Assess And Validate

Structural validation:

```bash
p2p validate
```

Readiness assessment:

```bash
p2p assess refresh
p2p assess show
```

This operational project assessment artifact is distinct from both
`p2p proposal readiness assess PROP-ID` and project readiness v2. For current
project completeness, use read-only `p2p project
snapshot`, `p2p project progress`, or `p2p project readiness review`; do not run
`p2p assess refresh` merely to update a client view.

Project definition maturity:

```bash
p2p project rubrics show
p2p assess maturity refresh
p2p assess maturity show
```

Maturity assessment now projects definition coverage from readiness-v2 criteria
for current workspace reads. It is not a measure of implementation completeness
and it is not the authoritative project-readiness contract.

## 14. Governance Preflight

Governance preflight is read-only. It reports whether a project choice is ready
for an owner decision, but it does not decide the choice, record votes, record
precedents, or repair governance files.

```bash
p2p governance status
p2p governance validate
p2p choice governance-preflight CHOICE-001 --option C --actor owner
p2p vote status PROP-001
p2p precedent search --choice CHOICE-001
```

Machine-readable output is available for automation:

```bash
p2p choice governance-preflight CHOICE-001 --option C --actor owner --format json
p2p governance validate --format json
p2p vote status PROP-001 --format json
p2p precedent search --tag release-policy --format json
```

Preflight treats votes as advisory evidence. A vote conflict creates a warning,
not a block, and appears as `vote_summary.alignment: conflicts` in machine
output. Active explicit blockers block normal finalization and report
`result.status: requires_owner_override` for an authorized owner.

Precedent search is deterministic: it matches only explicit precedent IDs,
proposal IDs, choice IDs, or tags. It does not use fuzzy title matching or AI
inference.

## 15. Recover From Common Problems

`p2p: command not found`

For the recommended uv tool install, update the owner shell path and rerun
diagnostics:

```bash
uv tool update-shell
p2p doctor
```

For an existing pip/virtualenv fallback, use the platform-native binary or
activate that virtualenv:

```bash
.venv/bin/p2p --help
.venv\Scripts\p2p.exe --help
. .venv/bin/activate
```

Registries look stale:

```bash
p2p registry refresh
p2p validate
```

An agent wants to edit `.p2p/` manually:

```text
Use CLI or MCP primitives. If a primitive is missing, stop and report it.
Do not invent .p2p files or IDs.
```

You need the exact command surface:

```bash
p2p --help
p2p proposal --help
p2p choice --help
p2p change --help
p2p spec --help
p2p work --help
```

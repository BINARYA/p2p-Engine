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
  --repository local \
  --domain software \
  --mcp-hint
```

When `--agent` is omitted, `p2p init` uses an adaptive bootstrap default. It
installs `generic` plus the detected current adapter when detection is reliable;
otherwise it falls back to all built-in adapters and prints a warning. The
detected adapter is only a bootstrap hint, not a persisted project identity.

To narrow the generated adapters explicitly, repeat `--agent`:

```bash
p2p init "My Project" --agent codex --agent claude --repository local
```

`generic` is always included.

After init, manage the footprint with `p2p agent list`,
`p2p agent install <adapter>`, `p2p agent update <adapter>`,
`p2p agent doctor <adapter>`, `p2p agent uninstall <adapter>`, and
`p2p agent instructions refresh --profile <adapter>`.

When `--mcp-hint` is used, init prints a root-aware MCP setup section. The
preferred server command uses `/path/to/project/.venv/bin/python -m
p2p_engine.mcp.server --root /path/to/project`; the shorter
`p2p-mcp-server --root /path/to/project` form remains a PATH-based fallback.
`--root` means the governed P2P decision root.

Init also applies append-only `.gitignore` hygiene for common local artifacts
and reports whether the repository hygiene section was applied, already
covered, or warning-only.

`--domain` applies an optional domain template. If omitted, the project starts
with unresolved domain and rubric state, and `p2p next` will recommend defining
the domain and rubric before maturity assessment can become meaningful.

Typical first checks:

```bash
p2p status
p2p runtime status
p2p context --budget small
p2p context --target PROP-001 --budget small
p2p context --target PROP-001 --budget medium --format json
p2p validate
p2p registry refresh
p2p next
```

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
  `.p2p/project/runtime.yml` is missing; restore it from project history.
- `legacy_undeclared`: the project has no runtime contract and no marker
  requiring one; validation reports a non-blocking warning and compatibility is
  not inferred.

`p2p validate` reports deterministic runtime findings, including
`P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED` for legacy projects and
`P2P268_RUNTIME_SETUP_GUIDE_DRIFT` when managed `P2P-SETUP.md` no longer
matches the contract-rendered setup guide.

Project owners can preview and apply a governed runtime contract change with:

```bash
p2p runtime contract preview \
  --requires ">=0.2.0,<0.3" \
  --recommended "0.2.4"

p2p runtime contract apply \
  --requires ">=0.2.0,<0.3" \
  --recommended "0.2.4" \
  --expected-state-token "<token-from-preview>" \
  --confirm
```

`preview` is read-only. It validates the proposed values, classifies impacts,
checks the managed setup guide state, reports owner-authority diagnostics, and
returns an expected-state token only when the current contract is trusted and
the update is structurally applicable.

`apply` rechecks the current state, owner authority, confirmation, reason
requirements, and expected-state token before writing. It updates managed
`P2P-SETUP.md` and `.p2p/project/runtime.yml` in one rollback-safe local
transaction. A handled failure restores the original bytes of both targets. It
never installs, upgrades, downgrades, or reconciles the local P2P Engine runtime.

Strong impacts such as range tightening, runtime line changes, or updates that
exclude the active runtime require `--reason`. An unmanaged `P2P-SETUP.md`
blocks apply; P2P does not overwrite human-owned setup documentation as a side
effect of a contract update.

### Workspace Schema And Migration

Workspace layout versioning is independent from the runtime contract. Inspect
layout, semantic alignment and interrupted transaction state without writing:

```bash
p2p workspace schema status
p2p workspace schema status --format json
p2p workspace migrate recovery status --format json
```

Build a deterministic forward-only plan. Supply a reviewed owner-input patch
when the findings require vertical, owner or bounded metadata values:

```bash
p2p workspace migrate plan --to 3 --format json
p2p workspace migrate plan --to 3 --input migration-input.yml --format json
```

Apply only the exact reviewed plan. The target, input patch and semantic
fingerprint are resupplied; P2P recomputes and validates the plan before and
after acquiring its process-safe lock:

```bash
p2p workspace migrate apply \
  --to 3 \
  --input migration-input.yml \
  --plan-fingerprint '<reviewed-fingerprint>' \
  --actor owner \
  --confirm
```

An interrupted transaction blocks unrelated governed writes. Resume or roll it
back only through the supported recovery commands:

```bash
p2p workspace migrate recovery resume \
  --transaction-id migration-... --actor owner --confirm
p2p workspace migrate recovery rollback \
  --transaction-id migration-... --actor owner --confirm
```

Do not edit schema state, locks, journals or candidates by hand. See
[WORKSPACE-MIGRATION.md](WORKSPACE-MIGRATION.md) for owner-input shape,
recovery preconditions and post-migration freshness handling.

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

Project verticals are pure data packs that describe the capisaldi, rubrics,
questions, and expected artifacts for a kind of project. `base_project` is the
cross-domain fallback. More specific verticals can extend it.

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

If no active vertical has been selected, project reads use `base_project` as a
normal fallback. This is not an init failure; it is a signal that an agent or
owner should define the project skeleton before relying on readiness.

Generate a candidate for a custom or detected vertical:

```bash
p2p project vertical propose "progettare la scatola perfetta"
```

The command prints an importable candidate YAML. Save or review that candidate,
then add/select it explicitly:

```bash
p2p project vertical validate candidate.yml
p2p project vertical add candidate.yml --activate --actor owner
p2p project vertical select packaging_or_physical_product_design --actor owner
p2p project vertical lock show
```

Source precedence is deterministic:

```text
explicit path/reference
.p2p/project/verticals/<vertical-id>/
P2P_HOME/verticals/<vertical-id>/
~/.p2p/verticals/<vertical-id>/
internal package resources
future remote registry sources (deferred)
base_project fallback only when no active lock exists or repair explicitly asks for it
```

Project-local packs override installed and internal packs with the same ID.
`P2P_HOME/verticals` wins over `~/.p2p/verticals` when `P2P_HOME` is configured.

The compatibility single-file shape remains supported:

```yaml
vertical:
  schema_version: 1
  id: social_impact_program_design
  name: Social Impact Program Design
  version: 1.0.0
  description: Domain-specific project skeleton.
  extends: base_project
  sections:
    - id: measurement_reporting
      title: Measurement And Reporting
      purpose: Define outcome metrics and reporting cadence.
      required: true
      priority: 60
  rubrics:
    - id: measurement_quality
      title: Measurement Quality
      section_id: measurement_reporting
      required: true
      keywords: [metric, outcome, report, evidence]
  questions:
    - id: measurement_main
      section_id: measurement_reporting
      priority: high
      question: How will real impact be measured?
  artifacts:
    - id: outcome_metric_framework
      title: Outcome Metric Framework
      section_ids: [measurement_reporting]
      required: true
```

Production packs may use the canonical multi-file layout:

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

The four bundled seed packs use this canonical layout. Their section filenames
carry a stable priority prefix, such as
`sections/010-project-identity.yml`, so filesystem ordering preserves semantic
section order. `vertical.yml` contains metadata only; split sections and
rubrics must not also be embedded there. External single-file `vertical.yml`
packs remain supported for compatibility.

Selecting a vertical writes explicit project state:

```text
.p2p/project/vertical.yml
.p2p/project/vertical.lock.yml
.p2p/project/definition.yml
.p2p/project/rubrics.yml
```

Existing projects that already have `.p2p/project/vertical.yml` but no
`vertical.lock.yml` are not repaired by reads. Validate reports an actionable
warning; repair is explicit:

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

Review project readiness against the active vertical:

```bash
p2p project readiness review
p2p project readiness review --vertical social_impact_program_design
p2p project readiness gaps --limit 20 --format json
p2p project readiness questions status --format json
p2p project readiness questions next --format json
```

The review reports prioritized typed gaps, counts, bounded legacy evidence and
concrete next operations. On workspace schema v2, project questions live in
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

Proposal-to-vertical traceability can be declared with an optional proposal
artifact:

```bash
p2p proposal vertical-coverage show PROP-001 --format json
p2p proposal vertical-coverage suggest PROP-001 --format json
p2p proposal vertical-coverage preview PROP-001 coverage.yml --actor owner
p2p proposal vertical-coverage import PROP-001 coverage.yml \
  --preview-token '<token>' --actor owner --confirm
```

Suggestions are read-only and never authoritative. Preview/import validates the
complete replacement and commits coverage plus artifact-state provenance as one
operation. Project definition and bounded project metadata use the same
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

`p2p validate` checks project-local vertical packs, active vertical state,
vertical lock state, definition state, safety/trust issues, and declared
proposal coverage when present. Remote vertical registries are deferred.

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

When `questions.yml` exists, proposal readiness uses that structured question
lifecycle as the source of truth for owner-question resolution. Stale
`open-questions.md` bullets remain human-readable evidence and legacy fallback,
but they do not reopen applied, retired, superseded, muted, or deferred
structured questions. `readiness assess`, `readiness explain`, and
`readiness review` can show `owner_question_state` categories such as blocking
owner questions, answered-not-applied questions, residual follow-up, and closed
questions.

Artifact state is the structured coverage surface for proposal artifacts. New
proposals initialize it by default. Older proposals without artifact state are
reported as advisory `absent_legacy`, not as validation errors. Agents should
use `p2p proposal artifact ...` commands or explicit MCP write tools to update
artifact coverage; they should not edit `.p2p` files directly or copy temporary
files into managed proposal artifacts.

`p2p proposal show PROP-001 --full` renders the owner-facing full review view.
It keeps readiness separate from artifact status, includes structured
contributions, groups structured owner questions separately from analytical
`open_question` contributions and legacy `open-questions.md` artifacts, and
summarizes narrative/imported artifacts. Paths in that output are source or
evidence hints only; follow the displayed P2P commands for changes.

## 6. Decide A Proposal

Proposal decisions are owner-controlled. Use these only when the owner has made
the corresponding decision. Schema-v3 decisions are append-only events in
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

`proposal accept`, `proposal reject`, `proposal defer`, and `decision record`
remain compatibility commands. Without a token they only return
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
`merged_into_other`. Managed branch accept/reject commands remain branch
operations and never append proposal decision events.

Projection, ledger, and unknown-legacy repair have separate preview/apply
commands:

```bash
p2p decision projection-repair-preview PROP-001
p2p decision ledger-repair-preview PROP-001 --candidate reviewed-ledger.yml
p2p decision legacy-resolution-preview PROP-001 \
  --event-type rejected \
  --reason "Owner reviewed preserved legacy evidence."
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

## 10. Publish The Canonical Human Project Output

The publication pipeline keeps the complete export separate from the curated
human publication:

```bash
p2p project publish prepare
p2p project publish import curated-draft.md
p2p project publish validate
p2p project publish render
p2p project publish review --status approved --reviewer owner
p2p project publish status
```

`prepare` writes `outputs/latest/publication-profile.yml`,
`outputs/latest/curator-input.md`, and `outputs/latest/publication-manifest.yml`.
It reuses `outputs/latest/project.md` when its recorded P2P source fingerprint
and hash are current, so it does not create duplicate `outputs/review-###/`
snapshots when nothing changed.

The external curator edits a draft outside the canonical output path. `import`
atomically copies that draft to `outputs/latest/project.curated.md` and records
source, profile, packet, and curated hashes. The curated document and PDF are
derived publication artifacts; `.p2p/` remains authoritative.

`validate` writes `outputs/latest/publication-validation.yml` and fails on
deterministic contract errors such as missing curated Markdown, wrong H1 count,
missing executive summary, missing `.p2p/` source-of-truth statement, stale
hashes, or renderer-incompatible Markdown.

`render` writes `outputs/latest/project.pdf` only after validation passes. PDF
support is optional; install `p2p-engine[pdf]` plus WeasyPrint native
dependencies to enable it. There is no handcrafted PDF fallback.

`review` records owner review in `outputs/latest/publication-review.yml` for the
current Markdown/PDF package. Approval means the publication package is approved
for publication; it is not proposal acceptance, Work acceptance, or governance
approval.

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

`p2p spec status` preserves the existing completeness value (`generated` or
`incomplete`) and adds semantic freshness. Freshness can be `current`,
`current_legacy`, `stale`, `modified`, `unknown_origin`, or `incomplete`.
Legacy generated specs are compared with the deterministic non-provenance
candidate; imported or ambiguous specs are not guessed from age. CLI and MCP
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

Work commands manage handoff and branch lifecycle metadata for P2P-managed work.

```bash
p2p work plan --change CHANGE-001 --target speckit
p2p work status
p2p work show WORK-001
```

Branch and review commands can touch Git state. Use them only when the local
repository policy is clear:

```bash
p2p work branch WORK-001
p2p work submit WORK-001
p2p work review WORK-001
p2p work publish WORK-001
p2p work request-review WORK-001
p2p work accept WORK-001
p2p work finalize WORK-001
p2p work cleanup WORK-001
```

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

Project definition maturity:

```bash
p2p project rubrics show
p2p assess maturity refresh
p2p assess maturity show
```

Maturity assessment checks project definition coverage against rubrics. It is
not a measure of implementation completeness.

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

Use the virtualenv binary or activate the virtualenv:

```bash
.venv/bin/p2p --help
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

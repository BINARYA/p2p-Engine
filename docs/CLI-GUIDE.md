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

By default, `p2p init` creates the generic baseline plus all built-in
project-local agent integrations. To narrow the generated adapters, repeat
`--agent`:

```bash
p2p init "My Project" --agent codex --agent claude --repository local
```

`generic` is always included.

`--domain` applies an optional domain template. If omitted, the project starts
with unresolved domain and rubric state, and `p2p next` will recommend defining
the domain and rubric before maturity assessment can become meaningful.

Typical first checks:

```bash
p2p status
p2p context --budget small
p2p validate
p2p registry refresh
p2p next
```

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

## 2. Define Project Verticals And Capisaldi

Project verticals are pure data packs that describe the capisaldi, rubrics,
questions, and expected artifacts for a kind of project. `base_project` is the
cross-domain fallback. More specific verticals can extend it.

List and inspect verticals:

```bash
p2p project vertical list
p2p project vertical show base_project
p2p project vertical show social_impact_program_design
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
```

Source precedence is deterministic:

```text
.p2p/project/verticals/<vertical-id>/vertical.yml
internal package resources
future remote registry sources
base_project fallback
```

Project-local packs override internal packs with the same ID. A valid pack uses
this shape:

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

Review project readiness against the active vertical:

```bash
p2p project readiness review
p2p project readiness review --vertical social_impact_program_design
```

The review reports section coverage, missing capisaldi, generated questions,
unmapped proposals, and suggested next commands. It does not mutate governance
state.

Proposal-to-vertical traceability can be declared with an optional proposal
artifact:

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

`p2p validate` checks project-local vertical packs, active vertical state, and
declared proposal coverage when present. Remote vertical registries are
deferred; the current MVP uses internal resources plus project-local packs.

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

## 4. Capture A Rough Idea

Use intake when the input is messy, overlapping, or not ready to become a
proposal.

```bash
p2p intake prompt "We may need a local MCP server, but it must not bypass owner decisions."
p2p intake status
```

The prompt workflow creates an intake folder and a prompt for human or AI
analysis. Import and apply steps are controlled:

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
p2p proposal update PROP-001 --goal "Keep tool boundaries explicit."
```

Add review material without rewriting the proposal:

```bash
p2p contribution add PROP-001 \
  "The MCP surface should label read-only and write-safe tools clearly." \
  --type constraint \
  --relevance high
```

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

## 6. Decide A Proposal

Proposal decisions are owner-controlled. Use these only when the owner has made
the corresponding decision.

```bash
p2p proposal accept PROP-001 --reason "The read-only MCP boundary is clear."
p2p proposal reject PROP-001 --reason "The scope conflicts with current priorities."
p2p proposal defer PROP-001 --reason "Needs more design evidence."
```

After a decision:

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

## 10. Generate And Export Software Specs

For software projects, a Change Set can still produce a P2P-native spec and
optional agent-first export documents for generic, OpenSpec, or Spec Kit
handoff. This is a compatibility/software-oriented workflow, not the default
project definition export.

```bash
p2p spec refresh --change CHANGE-001
p2p spec status
p2p spec show CHANGE-001
p2p spec prompt --change CHANGE-001
```

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

## 11. Manage Work Metadata

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

## 12. Assess And Validate

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

## 13. Recover From Common Problems

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

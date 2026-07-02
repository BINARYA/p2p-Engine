# P2P Engine Project Definition

## Generated Metadata

- generated_at: 2026-06-30
- generator: p2p project export
- source_of_truth: .p2p/
- output_role: generated human-facing project definition
- default_output: outputs/latest/project.md
- profile_exports: outputs/latest/exports/<profile-or-vertical>/

## Executive Summary

This project definition synthesizes 81 accepted proposals from P2P-managed state into a human-facing document. It is generated output; `.p2p/` remains the managed source of truth.

## Project Purpose

### PROP-001 - — CLI Foundation

Build the first P2P Engine CLI using Python and Typer.

The CLI should focus on local file generation and workflow guidance:

```text
p2p init
p2p proposal create
p2p contribution add
p2p digest prompt
p2p clarify prompt
p2p decision record
p2p plan prompt
p2p tasks prompt
p2p status
```

The first version should implement prompt generation instead of direct AI integration. A command such as:

```bash
p2p digest prompt PROP-001
```

should generate:

```text
.p2p/prompts/PROP-001/digest.prompt.md
```

The user can then provide that prompt to Codex, ChatGPT, Claude, Llama, or another model manually and paste the output into the correct artifact.

### PROP-002 - Proposal Exploration And Readiness Workflow

Introdurre un workflow di **Proposal Exploration And Readiness** composto da:

1. artifact di exploration human-authored;
2. readiness profile versionati;
3. assessment per-proposal con score, evidence, confidence e gate;
4. snapshot/registry per lookup operativo;
5. `p2p next` readiness-aware;
6. agent skill e MCP guidance piu prescrittive;
7. owner override come evento governance.

### Exploration Artifacts

Le proposal continuano a usare artifact Markdown leggibili da umani e agenti:

```text
exploration.md
findings.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

Questi artifact restano fonte di contenuto e discussione. I dati strutturati
necessari alla macchina vivono in readiness profile, readiness assessment,
snapshot, registries, export o audit record.

### Readiness Profile

La readiness deve essere profile-based e versioned. Il primo profilo e:

```yaml
readiness_profile:
  id: default-readiness-v0.1
  version: 0.1
  criteria:
    problem_clarity: 10
    goal_clarity: 10
    scope_boundaries: 10
    alternatives_quality: 15
    tradeoff_analysis: 10
    risk_coverage: 10
    assumptions_clarity: 10
    owner_questions_resolution: 10
    acceptance_criteria_quality: 10
    impact_overlap_analysis: 5
  thresholds:
    weak: 0
    partial: 70
    strong: 85
    decision_ready: 95
  gates: {}
  override_policy: {}
```

Ogni readiness assessment deve registrare almeno `profile_id`,
`profile_version` e `computed_at`, per rendere lo score interpretabile nel
tempo.

### Readiness Assessment

Una proposal riceve un assessment con:

```yaml
readiness:
  profile_id: default-readiness-v0.1
  profile_version: 0.1
  computed_at: 2026-06-04T10:30:00Z
  tier: governance-critical
  computed_score: 82
  computed_label: partial
  effective_status: normal
  confidence: medium
  confidence_reasons: []
  required_score_for_decision: 95
  failed_gates: []
  missing: []
  suggested_next: []
```

`computed_score` misura la qualita dell'esplorazione secondo il profilo.
`effective_status` rappresenta il risultato governance quando l'owner usa un
override.

### Tier And Gates

Le proposal hanno tier suggerito da agente/sistema e confermato dall'owner:

```text
small
medium
architectural
governance-critical
```

PROP-002 e `governance-critical` perche definisce come P2P Engine esplora,
valuta e muove le proposal future verso decisione.

Il total score non basta per le proposal importanti. Il modello deve supportare:

- required score by tier;
- minimum gates;
- required confidence;
- artifact quality caps;
- owner override esplicito.

### Artifact Quality

`explore status` deve evolvere oltre il controllo di esistenza file. Gli stati
artifact iniziali sono:

```text
missing
placeholder
thin
meaningful
needs_owner_input
ready
```

I cap iniziali sono:

```yaml
artifact_quality_caps:
  missing:
    max_score_percent: 0
  placeholder:
    max_score_percent: 0
  thin:
    max_score_percent: 50
  meaningful:
    max_score_percent: 75
  needs_owner_input:
    max_score_percent: 75
    blocks_ready_for_decision: true
  ready:
    max_score_percent: 100
```

`needs_owner_input` e diverso da `thin`: l'artifact puo essere specifico e utile
ma non completabile senza una scelta owner.

### Evidence

Ogni criterio valutato deve avere evidence strutturata e note leggibili:

```yaml
criteria:
  alternatives_quality:
    max_points: 15
    awarded_points: 11
    artifact_quality: meaningful
    evidence:
      - artifact: alternatives.md
        section: Alternative F - Hybrid Exploration And Readiness Model
    notes: "Alternative reali presenti, ma manca matrice comparativa completa."
```

Questo evita score opachi e riduce il rischio di artifact lunghi ma generici.

### Governance And Override

Owner override non modifica il computed score. Crea un evento governance
auditabile.

Comando primario:

```bash
p2p proposal accept PROP-XXX --override-readiness --reason "..."
```

L'override sotto target richiede:

- authority owner;
- `override_reason` obbligatoria;
- acknowledgement dei failed gates;
- preservazione del computed score;
- audit event.

### Commands

Il namespace readiness appartiene a `proposal`:

```bash
p2p proposal readiness PROP-XXX
p2p proposal readiness refresh PROP-XXX
p2p proposal readiness explain PROP-XXX
```

Separazione prevista:

```text
p2p explore status      -> artifact quality
p2p proposal readiness  -> proposal maturity
p2p next                -> next action recommendation
p2p proposal accept     -> governance decision
```

### MCP And Agent Behavior

MCP read tools possono essere accessibili agli agenti. MCP write/governance
tools devono essere permission-gated e non agent-autonomous.

Le skill agentiche devono istruire l'agente a:

- ispezionare readiness prima di raccomandare acceptance;
- non trattare artifact `thin` come completi;
- distinguere score, confidence, gates e override;
- chiedere input owner quando un artifact e `needs_owner_input`;
- proporre alternative e tradeoff reali;
- dire esplicitamente quando una proposal non e metodologicamente pronta.

### `p2p next`

`p2p next` deve usare readiness per suggerire azioni concrete:

```yaml
readiness_gap:
  current_score: 82
  target_score: 95
  missing_points: 13
  failed_gates:
    - owner_questions_resolution
    - acceptance_criteria_quality
  highest_impact_actions:
    - resolve_owner_questions
    - define_acceptance_criteria
    - improve_alternative_comparison
```

Le azioni devono essere ordinate gate-first e poi per punti recuperabili.

### Migration

Readiness si applica a nuove proposal e draft aperte. Le draft esistenti
possono essere marcate `not_assessed` e `p2p next` puo suggerire una readiness
refresh.

Le proposal gia accettate non vengono riscritte o invalidate. Possono essere
marcate come legacy o ricevere assessment retrospettivo chiaramente indicato.

### PROP-004 - Prompt-only Import Workflow

Implementare comandi import uniformi per le fasi successive a explore e aggiungere synthesize prompt/import.

### PROP-005 - Codex Skill Integration

Aggiungere una skill locale .codex/skills/p2p-engine/SKILL.md che istruisca Codex a usare P2P Engine come sorgente di verita operativa.

### PROP-006 - Multi-Agent Integration Model

Introduce an Agent Integration Registry MVP. By default, p2p init creates the generic baseline and all supported project-local adapter files for generic, codex, claude, cursor, copilot, gemini, and opencode. The owner may request a narrower init set with repeated --agent options, but generic is always included and cannot be removed. P2P records installed integrations in .p2p/agent-integrations.yml using schema_version 1, baseline_profile: generic, adapter status, maturity, capabilities, template_version, generated file records, shared ownership, managed flag, template_id, SHA-256 hash over exact file bytes, and drift state. The registry must not contain active_agent, default_agent, preferred_agent, current_agent, use, or switch state. Built-in adapter templates live in package data under src/p2p_engine/templates/agents/<adapter>/ for the MVP; project-local template overrides are deferred. Generated Markdown files should include a short managed header as a human hint, while the registry remains authoritative. The CLI exposes p2p agent list, show, install, update, doctor, and uninstall; excluded commands are use, switch, current, and install --no-use. doctor validates registry shape, file existence, hashes, shared references, generic baseline, ownership conflicts, uninstall safety, and presence of the generic method behavior block. install all may install every supported project-local integration only when non-shared file targets do not conflict. Migration is conservative: known generated files become managed, unknown or changed files become unmanaged or drifted, and P2P never overwrites them silently. Generated files derive from minimal generic P2P governance content and may be adapted for host tools without weakening the rules. That generic content must include readiness-driven refinement behavior: when a proposal is weak, low-confidence, below target, or blocked by failed gates, the agent must explain each gap, propose concrete alternatives, recommend one when justified, identify owner decisions, draft candidate updates, and re-check readiness after refinement. Initial files are AGENTS.md and .p2p/agent-policy.yml for generic; AGENTS.md plus a shared agent-neutral .agents/skills/p2p-project/SKILL.md for Codex when safe, with .codex/skills preserved as compatibility/migration; CLAUDE.md for Claude; .cursor/rules/p2p.mdc for Cursor; .github/copilot-instructions.md for Copilot; GEMINI.md for Gemini; and AGENTS.md only for OpenCode in the MVP. opencode.json is not generated by default. CLI and MCP tools are implemented over the same core behavior, with MCP exposing structured equivalents for compatible agents. Future readiness refinement commands should live under p2p proposal readiness, but they are not required for accepting this proposal.

### PROP-009 - Governance CLI Commands

Aggiungere comandi governance file-based per rendere operativo il modello di PROP-008, mantenendo Git come audit layer e rimandando enforcement permessi a fasi future.

### PROP-010 - P2P Project State Model

Add a P2P project state model that turns accepted proposals into versioned project artifacts under `.p2p/project/`. The MVP uses explicit refresh via `p2p project refresh`; automatic refresh after acceptance can be added later.

### PROP-011 - Project Refresh MVP

Add deterministic project-state generation from accepted proposals, starting with overview, problem, scope, project SWOT placeholder, features, decisions-map, and conflicts.

### PROP-012 - Impact Map and Conflict Memory

Add impact and conflict artifacts that allow P2P Engine to understand which project areas a proposal touches and preserve memory of competing or mutually exclusive alternatives.

### PROP-013 - Managed Git Adapter and Change Set Model

Adopt a managed Git model: proposals and change sets are the public P2P concepts, while Git branches, commits, merges, and tags are internal operations selected by a configurable policy. Git details are visible only in verbose/debug modes.

### PROP-014 - Change Set Metadata MVP

Add deterministic Change Set metadata generation from accepted proposals and decisions, preserving managed Git as metadata-only.

### PROP-015 - Change Set Lifecycle and Task Tracking

Add lifecycle commands and task/action inspection for Change Sets so P2P can track operational progress.

### PROP-016 - Project Registries MVP

Add .p2p/registries as a generated index layer for proposals, decisions, changes, choices and relations.

### PROP-017 - Proposal Intake and Context Analysis MVP

Introduce a proposal intake and context analysis workflow backed by generated registries and prompt-only AI output.

### PROP-018 - Choice Management CLI MVP

Add first-class CLI commands for project choices under .p2p/choices/.

### PROP-019 - Proposal Decision Shortcut Commands

Implement dedicated proposal decision shortcut commands that call the existing decision recording mechanism.

### PROP-020 - Proposal Inspection CLI MVP

Expose proposal inspection through dedicated CLI commands and make choice registry output stable for humans and agents.

### PROP-021 - Agent Skill Real Commands Update

Refresh .codex/skills/p2p-engine/SKILL.md so agents use the current CLI as the source of truth.

### PROP-022 - Operational Brief Prompt Workflow

Add a prompt-only operational brief workflow under project commands: the CLI gathers project state, registries, conflicts, choices, intake and changes into a context file, generates instructions for an AI/human synthesis, and imports the resulting operational brief and optional next-actions YAML.

### PROP-023 - Next Action Recommender MVP

Implement an advisory next-action recommender. The command should prefer imported next-actions.yml, fall back to deterministic project state checks, support --top N, and project status should summarize whether an operational brief exists plus the first suggested action.

### PROP-024 - Choice Blocking and Discovery MVP

Implement choice blocking and discovery in two steps. First add deterministic advisory inspection commands that surface project choices, proposal-local choice candidates, and unresolved discovery findings. Then add formal block/unblock commands that write links.yml for project choices, distinguishing related metadata from active blockers.

### PROP-025 - Controlled Intake Apply Workflow

Implement a two-phase controlled intake apply workflow. The plan command converts suggested-actions.yml into a versioned apply-plan.yml with support classifications. The show command displays the plan. The run command applies one explicit supported action and writes applied-actions.yml, while governance-only actions remain preview-only.

### PROP-026 - P2P Software Spec Generator MVP

Add p2p spec refresh/status/show/prompt/import. The refresh command deterministically generates a minimal software spec from a Change Set. The prompt command generates an AI/human refinement prompt from the deterministic spec and source context. The import command validates and imports refined spec artifacts.

### PROP-027 - Software Spec Exporter MVP

Add p2p spec export/status/show support for software spec export bundles. The MVP should export from .p2p/outputs/software-spec/CHANGE-XXX/ into .p2p/outputs/spec-export/CHANGE-XXX/TARGET/, starting with generic and openspec targets. Spec Kit remains a downstream target but is not implemented in this MVP unless the mapping becomes explicit.

### PROP-028 - Spec Kit Export Mapping MVP

Add speckit as a supported p2p spec export target. Export to .p2p/outputs/spec-export/CHANGE-XXX/speckit/specs/CHANGE-XXX-slug/ with spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md, contracts/README.md, and manifest.yml. The mapping should preserve P2P provenance and mark unresolved implementation details as NEEDS CLARIFICATION instead of inventing them.

### PROP-029 - Spec Export Validation MVP

Add p2p spec export-validate CHANGE-XXX --target TARGET. The command validates that the export directory exists, manifest.yml is valid and coherent, index.md exists, and target-specific required files are present for generic, openspec, and speckit bundles.

### PROP-030 - Managed Work and Multi-Branch Visibility Policy

Introduce P2P Work as the user-facing abstraction over future Git branches. Define levels from advisory to handoff plan, managed branch, managed commit, managed review, and owner-controlled merge. Implement p2p work plan/list/show to create and inspect .p2p/work/WORK-XXX/manifest.yml for validated spec exports. This first MVP must not create branches, commits, PRs, or merges.

### PROP-031 - Multi-Branch Work Scan MVP

Add p2p work scan to read local branches matching p2p/work/* through Git plumbing, discover .p2p/work/WORK-XXX/manifest.yml files on those branches, and write an aggregated .p2p/registries/work.yml. The command must be read-only with respect to Git: no checkout, fetch, branch creation, commit, PR, or merge.

### PROP-032 - Managed Work Branch Creation MVP

Add p2p work branch WORK-XXX. The command validates a clean Git repository, reads the Work manifest branch name, creates and checks out the managed branch, updates the manifest to branched, and keeps commit/merge actions disabled.

### PROP-033 - Managed Work Submit MVP

Add p2p work submit WORK-XXX. The command verifies the current branch is the Work branch, validates that the Work item is branched, requires changed files, records the changed file list, updates the Work manifest to submitted, stages the Work branch changes, and creates a local commit with a P2P-standard message.

### PROP-034 - Managed Work Review MVP

Add p2p work review WORK-XXX. The command verifies the current branch matches the Work branch, requires Work status submitted, requires a clean worktree, records the commit to review, updates the Work manifest to review_requested, creates a local metadata commit, and leaves push/PR/merge disabled.

### PROP-035 - Managed Work Publish MVP

Add p2p work publish WORK-XXX. The command verifies the current branch matches the Work branch, requires Work status review_requested, requires a clean worktree, requires an origin remote, updates the Work manifest to published with remote branch metadata, creates a local publish metadata commit, pushes the managed branch to origin, and leaves PR and merge disabled.

### PROP-036 - Managed Work Accept MVP

Add p2p work accept WORK-XXX. The command requires Work status published, a clean Git worktree, the Work branch to exist locally, and the current branch to be the manifest base branch. It performs a local no-ff merge from the managed branch, records accepted/merged metadata in the Work manifest, commits that metadata on the base branch, and leaves push and cleanup disabled.

### PROP-037 - Managed Work Status Summary MVP

Add p2p work status. The command reads local Work manifests and scanned branch registry entries, summarizes each Work item, and derives a conservative next command from status without modifying project or Git state.

### PROP-038 - Managed Work Merge Conflict Guidance MVP

Enhance p2p work accept with conflict guidance. On merge conflict, mark the Work manifest as merge_conflict, record source/base branches and conflicted files, and show recovery commands. Add p2p work accept --continue WORK-XXX to finalize after manual conflict resolution, and p2p work accept --abort WORK-XXX to abort the merge and restore the Work item to published.

### PROP-039 - Managed Work Finalize MVP

Add p2p work finalize WORK-XXX. The command requires Work status accepted, the current branch to match the Work base branch, a clean worktree, and a configured remote. It updates the Work manifest to finalized, records remote/base metadata, creates a local finalize metadata commit, pushes the base branch to the remote, and leaves branch cleanup disabled.

### PROP-040 - Managed Work Cleanup MVP

Add p2p work cleanup WORK-XXX. The command requires Work status finalized, a clean worktree, and the current branch to be the Work base branch. It deletes the local managed Work branch by default, can delete the remote Work branch with an explicit --remote flag, records cleanup metadata in the Work manifest, creates a local cleanup metadata commit, and optionally pushes the base branch so cleanup state is persisted remotely.

### PROP-041 - Remote Project Profile and Review Request Policy

Add a Remote Project Profile and a provider-agnostic review-request command. The profile records mode, provider, remote name, and remote URL. p2p work request-review WORK-XXX records that a published Work item is ready for external review, emits provider-specific guidance, and leaves merge/accept owner-controlled.

### PROP-042 - P2P Core CLI MCP Mediator Web Boundary

Adopt a five-layer architecture: Level 1 P2P Core, Level 2 P2P CLI, Level 3 Skill/MCP/Agent Interfaces, Level 4 P2P Mediator, Level 5 P2P Web. Core remains deterministic and provider-neutral. Intelligence lives in optional mediator or agent-facing layers. MCP exposes core capabilities to agents and mediators. Governance decisions remain owner-controlled unless an explicit future policy permits bounded automation.

### PROP-043 - Managed Work Retire MVP

Add p2p work retire WORK-XXX --reason TEXT. The command requires Work status planned, updates the manifest status to retired, records retirement metadata, and makes p2p work status report no next action for retired Work.

### PROP-044 - P2P MCP Server MVP

Add src/p2p_engine/mcp with a small JSON-RPC stdio MCP server and a p2p-mcp-server entrypoint. The server exposes read-only tools for project status, next actions, proposal list/show, choice list/show, change status, work status, and registry show. Each tool returns structured JSON derived from P2PWorkspace.

### PROP-045 - Agent-Safe Project Bootstrap MVP

Extend p2p init with an optional agent profile and repository mode. Generate generic AGENTS.md plus .p2p/agent-policy.yml. Add p2p agent instructions refresh so Codex, Claude, generic, or all profiles can be added later without replacing previous profiles. Instructions must state that .p2p is managed by P2P commands, missing primitives require stop-and-report, MCP is read-only unless tools explicitly say otherwise, and owner-controlled decisions cannot be made by agents.

### PROP-046 - MCP Write-Safe Bootstrap Tools MVP

Add p2p_init_project, p2p_agent_instructions_refresh, and p2p_registry_refresh MCP tools. Keep owner-controlled actions such as proposal accept/reject/defer, choice decide, work accept/finalize/cleanup, and direct Git merge out of MCP. Tool descriptions must make the governance boundary explicit.

### PROP-047 - Guided Init Wizard MVP

When p2p init is called without a project name, run a small interactive wizard that asks project name, initial agent profile, repository mode, and whether to show an MCP setup hint. Keep p2p init NAME --agent ... --repository ... as the scriptable path. Print concrete next steps after initialization.

### PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

Add MCP tools p2p_proposal_create, p2p_intake_prompt, and p2p_intake_status. These tools may create draft proposals and intake prompts using existing core methods, and may list intake records. They must not accept, reject, defer, decide choices, apply intake recommendations, or manage work merges.

### PROP-049 - MCP Level 4A Proposal Refinement Tools

Add MCP tools p2p_proposal_update, p2p_project_brief_prompt, and p2p_project_brief_show. Proposal update may replace structured proposal sections. Project brief prompt may create prompt/context artifacts, and brief show may read an imported brief. No brief import, proposal decision, choice decision, or work lifecycle mutation is added in this level.

### PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

Add MCP tools p2p_choice_discover, p2p_conflict_status, and p2p_impact_prompt. choice_discover returns advisory findings only. conflict_status reads recorded conflicts only. impact_prompt generates an impact analysis prompt for an existing proposal. Do not add conflict record, choice decide, choice block/unblock, impact import, intake apply, or change/work state transitions.

### PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

Update fallback next actions to recommend reviewing the first draft proposal when no stronger action exists. Update generated AGENTS.md, Codex project skill, Claude instructions, .p2p/agent-policy.yml, and the repository P2P skill so agents must use proposal/choice/change/work show or MCP equivalents before explaining existing artifacts.

### PROP-052 - MCP Proposal Contribution Tool

Add MCP tool p2p_proposal_contribution_add. It appends a typed contribution to a proposal using the existing core contribution model. It may record suggestion, objective, constraint, risk, objection, alternative proposal, and similar contribution types. It must not accept/reject/defer proposals, merge proposals, decide choices, or alter decision files.

### PROP-053 - Core Validation Layer MVP

Implement p2p validate with stable findings. The MVP validates required project structure, YAML readability for known structured files, proposal directory naming, required proposal sections, decision status presence, proposal/decision status consistency, and registry freshness. Findings have severity error/warning/info, stable codes, paths, messages, and optional suggested commands. Add --format text/json and exit code 1 when errors exist. Add p2p_validate MCP as read-only/advisory. Keep p2p check as minimal bootstrap validation.

### PROP-054 - Project Readiness and Maturity Assessment

Adopt a hybrid assessment model. Level 1 computes a deterministic completion/readiness score from P2P state: validation results, stale registries, draft proposals, accepted proposals, open choices, blockers, change/work lifecycle status and operational brief availability. Level 2 adds domain maturity rubrics through explicit criteria files and prompt/import workflows. Software rubrics may cover architecture, security, usability, testability, maintainability, packaging and documentation. Generic or non-software rubrics can be added per supported project type. Assessment output must include score, confidence, factors, gaps and suggested next actions.

### PROP-055 - Agent Token Budget and Context Discipline

Introduce an Agent Token Budget and Context Discipline with a narrow MVP based on compact deterministic context packets. The first implementation combines skill policy, CLI context view, and MCP context tool. Agents must read compact summaries first, then details only by explicit ID, and stop once the next bounded action is clear. Add p2p context, p2p context --budget small, p2p context --target ID, and an equivalent p2p_context MCP tool. The context output should include current state, next actions, relevant artifacts, allowed commands, explicit do-not-read guidance, and the smallest sufficient next step. Full repository scans, broad .p2p traversal, full registry reads, source-code exploration, and Git history reads are disallowed unless the user task explicitly requires them or the compact context is insufficient. Advanced token estimation, numeric budgets, read tracking, and model-specific optimization are deferred until after the MVP works in practice.

### PROP-056 - Project Definition Maturity Rubrics

Add Project Definition Maturity Rubrics. A project may define a domain and an enabled list of criteria under .p2p/project/rubrics.yml. The first MVP ships deterministic built-in rubrics for at least generic and software domains, with an architecture that can add grant_document, board_game, hardware, service, and other domains later. The init flow should be able to create an initial rubric profile, and a dedicated command should refresh/show maturity assessment. The assessment should scan P2P project artifacts conservatively and report each criterion as covered, partial, or missing, with evidence IDs when available. Scores represent definition maturity: whether the planned project has treated relevant topics enough for export, not whether implementation has been completed.

### PROP-057 - Guided Rubric Selection During Init

Add Guided Rubric Selection During Init. When p2p init runs interactively, after project domain selection it should ask whether to customize rubric criteria. If the owner says no, P2P keeps all domain criteria enabled. If the owner says yes, P2P asks an enable/disable confirmation for each suggested criterion and saves the selected enabled flags into .p2p/project/rubrics.yml. Scripted init with a project name remains non-interactive and uses the full default rubric for the selected domain.

### PROP-058 - Project README and Installation Guide

Create a concise README and docs/INSTALL.md. README should explain what P2P Engine is, core principles, five-layer architecture, current implementation status, quick start commands, token-aware context, project definition maturity, MCP overview, and roadmap. docs/INSTALL.md should provide source install steps with Python venv, editable install, verification commands, project initialization, MCP local setup for Codex/compatible clients, troubleshooting, and current limitations.

### PROP-059 - P2PWorkspace Modular Refactoring Plan

Adopt a conservative modular refactoring program. P2PWorkspace remains the stable compatibility facade, but new behavior should move into dedicated services and adapters. cli.py, storage/filesystem.py, and mcp/tools.py become thinner orchestration/facade layers rather than the default home for new domain logic. The first deliverable is documentation and development contract only: update AGENTS.md with short non-negotiable agent rules, create docs/DEVELOPMENT-GUIDELINES.md as the full architecture guide, and define a prioritized refactoring roadmap. Alternatives considered are: keep the monolith and document conventions; split large files mechanically; introduce internal managers behind the stable P2PWorkspace facade; or redesign public APIs. The preferred option is internal managers behind the facade because it improves maintainability while preserving CLI, MCP, storage, governance, and agent compatibility. After acceptance and local specs binding, the recommended first code extraction is consent/permissions because it has a clear boundary, high safety value, lower presentation exposure than CLI, and can establish the extraction pattern before more central proposal/readiness workflows are touched. Services/use cases should be extracted before CLI modularization. Any breaking change requires a separate proposal.

### PROP-061 - Focused README and Documentation Map

Refine documentation with four steps: rewrite README.md around what P2P Engine is, what it does, repository components, installation, quick start, and agent usage; keep docs/INSTALL.md; add docs/CLI-GUIDE.md, docs/MCP.md, docs/AGENT-INTEGRATION.md, and docs/API.md as structured stubs; and create a documentation index in README.md describing each docs file.

### PROP-062 - README Product Landing Page Refinement

Rewrite README.md with sections: pitch, why, what it does, who it is for, status, 5-minute demo, install, core concepts, docs, roadmap, development. Use HTTPS clone first and keep future hosted product scope out of the engine README.

### PROP-064 - Spec Kit Three-Prompt Export Model

Implement an agent-first project definition export pipeline. Step 1 synthesizes accepted P2P memory into project.md using a required core checklist, domain extensions, evidence labels, and explicit missing-information markers. Step 2 derives target-specific outputs from project.md: generic exports project.md and propose.md; OpenSpec exports propose.md aligned with OpenSpec proposal principles; Spec Kit exports speckit.constitution.md, speckit.specify.md, and speckit.plan.md aligned with the three starting Spec Kit prompts. Legacy bundle-style exports may remain temporarily under a legacy/ or bundle/ path, but they must be labeled secondary and not documented as the primary flow.

### PROP-065 - MCP Agent-First Coverage Expansion

Expand the P2P MCP tool surface with all priority 1, 2, and 3 agent-safe tools. Keep descriptions explicit about read-only, write-safe, advisory, and governance boundaries. Update tests and agent-facing documentation/skill instructions accordingly.

### PROP-066 - Permission-Gated MCP Governance And Git Operations

Adopt a hybrid Role + Consent Receipt model for permission-gated MCP governance and Git operations.

P2P distinguishes three concepts:

- actor_id: the declared person, agent, or client performing work; useful for audit and collaboration but not strong authentication in local/Git-only mode.
- authorizer: the project role or owner identity that approves a privileged operation.
- enforcer: the mechanism that actually prevents unauthorized state changes. In local projects this is mostly P2P policy and audit. In cloud-backed projects this must be Git provider permissions, branch protection, required approvals, and token scopes.

Project-declared roles are stored in versioned P2P project policy, such as `.p2p/project/permissions.yml` or an equivalent generated policy file. On project init, P2P should ask for or accept an owner display name. If no owner is provided, it creates a generic `owner` identity. Contributor identities may be added later; if no contributor name is known, P2P may use generic `contributor` or agent IDs for branch metadata.

Example policy:

```yaml
permissions:
  version: 1
  identities:
    owner:
      role: owner
      kind: person
      display_name: owner
    contributor:
      role: contributor
      kind: person
      display_name: contributor
  roles:
    owner:
      can_grant_consent: true
      can_manage_permissions: true
    maintainer:
      can_request_privileged_operations: true
    contributor:
      can_create_local_branches: true
      can_request_review: true
    agent:
      can_use_safe_tools: true
    readonly:
      can_read: true
```

Tool classes:

- safe_read: read/status/context/scan tools; no consent required.
- write_safe_preparatory: deterministic or local preparatory operations such as fetch and proposal branch creation; no owner consent required by default, but must be audited when they touch Git state.
- privileged_publish: publish, push, request-review, provider PR/MR handoff; requires a valid consent receipt unless project policy explicitly allows the actor role.
- owner_controlled_governance: accept, reject, defer, choice decide, select candidate, merge, finalize, cleanup; requires owner consent receipt.
- destructive_or_external: cleanup, branch deletion, provider side effects, irreversible remote changes; requires owner consent receipt, single-use, and explicit audit.

Consent receipts are versioned audit records granting one bounded privileged operation. They include consent_id, operation, target, actor_id, requested_by, approved_by, role, scope, expiry, single_use flag, created_at, and optional provider metadata. Sensitive MCP tools must refuse execution without a valid unexpired receipt. After single-use execution, the receipt is marked consumed with result metadata.

The MVP does not require external IAM. Project init should support an owner name but must fall back to generic `owner`. The model is declarative and auditable locally. In cloud-backed projects, robust enforcement depends on Git provider controls protecting main and privileged remote actions. A future P2P API server may replace or augment declarative identities with authenticated users, OAuth, organization membership, signed consent, or IAM-backed policy checks.

Safe MCP surface may remain available before privileged consent implementation: sync status/fetch and proposal branch/status/scan. MCP pull, push, publish, request-review, retire, accept, reject, merge, finalize, cleanup, provider PR/MR handoff, and protected-branch updates remain deferred until role policy, consent receipts, and audit records are implemented.

### PROP-067 - Agent-First Setup Documentation Split

Revise README and INSTALL around an agent-first new-project setup model. Add or update agent setup guidance so the P2P Engine checkout, target project, and agent client are clearly separated. Move repository-contributor instructions for installing P2P and enabling an agent against the P2P Engine repository into CONTRIBUTING.md, and keep README limited to a concise contribution pointer.

### PROP-068 - Document Agent MCP Client Setup Commands

Update docs/INSTALL.md with an agent MCP setup section covering the common stdio command, Codex CLI, Claude Code, Claude Desktop JSON, and generic MCP clients. Keep README as a pointer to the install/MCP docs.

### PROP-069 - Clarify MCP Stdio Integration Model

Update docs/INSTALL.md and docs/MCP.md with a clear MCP stdio model, verified client setup sections, and explicit notes about future Streamable HTTP for shared long-running multi-client services. Keep all examples based on the current Python MCP server command and --root target-project argument.

### PROP-070 - Clarify README Agent Access Modes

Update README's 5-minute agent setup to describe two valid agent connection modes: CLI access and MCP access. Add a short warning that MCP is currently an agent-safe tool surface and not the full P2P command surface.

### PROP-071 - Custom Domain Definition Workflow

Refactor domain initialization around optional templates. Every project has explicit domain state and rubric state. At init, the user may choose no template, a predefined template such as generic/software/grant_document/board_game, or a custom unresolved path. Applying a template pre-populates domain metadata and rubric criteria. Choosing custom or none leaves domain/rubric setup unresolved and creates or recommends first activities for defining the domain and defining the rubric with the user and agent. Maturity assessment becomes assessable only when an enabled rubric exists; unresolved or empty rubrics report a missing/unresolved rubric state instead of well_defined.

### PROP-072 - Concurrent Managed Work and Merge Decision Model

Introduce a Concurrent Managed Collaboration model with P2P-owned CLI operations for proposal branches, Work branches, remote synchronization, candidate decisions, and owner-controlled merges.

Core rule: `main` contains accepted project state only. Draft proposals, proposal refinements, alternative proposal candidates, and implementation Work candidates must live on P2P-managed branches until explicitly accepted and merged by an authorized owner or governance process.

Branch classes:

- `p2p/proposal/<proposal-id>-<slug>-<actor-slug>-<hash16>`: a managed branch for creating or refining proposal state.
- `p2p/work/<work-id>-<change-id>-<target>`: the existing managed branch class for implementation work.

Resolved design choices:

- Draft proposal work stays off `main` by default.
- Proposal branches use real `PROP-XXX` identifiers, not temporary candidate IDs.
- Proposal branch names include a stable 16-hex-character hash suffix for branch-name disambiguation.
- P2P must mitigate concurrent proposal ID collisions by fetching/scanning accepted and remote proposal state before allocating IDs, then validating again before publish/merge.
- P2P must expose user-facing remote operations through CLI commands, because users and routine agents should not need to understand fetch, pull, push, or PR/MR mechanics.
- Work selection is required only when multiple Work candidates exist for one Change Set.
- Combining candidates creates a new auditable Work item or proposal branch derived from the selected source candidates.

Proposal ID allocation and collision rule:

For cloud-backed projects, `p2p proposal create` and `p2p proposal branch` must perform a remote-aware allocation pass when a remote profile is configured:

```text
1. fetch configured remote metadata;
2. scan local main, local P2P proposal branches, remote main, and remote P2P proposal branches;
3. allocate the next available PROP-XXX ID;
4. create a branch name with capped slug, actor slug, and hash-16 suffix;
5. record actor, allocation, hash, and remote scan metadata in the proposal branch;
6. re-check for ID collision before publish and before merge.
```

Concurrent ID allocation is treated as a recoverable publish-time conflict, not as silent corruption. If publish detects that the remote already contains a conflicting `PROP-XXX` proposal branch or accepted proposal, P2P must stop, fetch, allocate the next available proposal ID, and either ask for confirmation or proceed only when an explicit `--auto-renumber` option or policy allows it. Safe auto-renumber must rewrite the local proposal directory, proposal metadata, title references where applicable, branch metadata, and branch name from the losing ID to the new ID before retrying publication. The old local branch must be retired or deleted only after the new proposal branch is safely created and validated.

This fetch/scan/recheck/renumber strategy is sufficient for the MVP but is not a perfect distributed lock. A later enhancement may add a remote lock ref or allocation manifest if strict sequential IDs are required under simultaneous branch creation. Hashing the user or agent into the branch name reduces branch-name collisions, but it does not replace the human-readable `PROP-XXX` ID.

Proposal branch lifecycle:

```text
planned -> branched -> revised -> review_requested -> published -> accepted -> merged -> finalized
                                   -> rejected -> retired
                                   -> merge_conflict -> accepted|aborted
```

Work candidate lifecycle extends the existing Work lifecycle with candidate decision states:

```text
planned -> branched -> submitted -> review_requested -> published -> review_handoff
                                                        -> selected -> accepted -> finalized -> cleaned_up
                                                        -> rejected|retired
                                                        -> merge_conflict -> accepted|aborted
```

Minimum proposal CLI operations:

```bash
p2p proposal branch PROP-XXX
p2p proposal status PROP-XXX
p2p proposal publish PROP-XXX
p2p proposal publish PROP-XXX --auto-renumber
p2p proposal request-review PROP-XXX
p2p proposal accept-branch PROP-XXX --reason "..."
p2p proposal reject-branch PROP-XXX --reason "..."
p2p proposal merge PROP-XXX
p2p proposal merge --continue PROP-XXX
p2p proposal merge --abort PROP-XXX
p2p proposal retire-branch PROP-XXX --reason "..."
p2p proposal scan
```

Minimum P2P-managed remote/sync operations:

```bash
p2p sync fetch
p2p sync status
p2p sync pull
p2p sync push
p2p proposal publish PROP-XXX
p2p work publish WORK-XXX
p2p work request-review WORK-XXX
p2p work finalize WORK-XXX
```

These commands wrap Git transport operations and enforce P2P validation, branch policy, remote profile checks, actor attribution, and audit recording. They should never require Matteo, Lorenzo, or routine agents to run raw Git commands.

Minimum candidate CLI operations for concurrent Work:

```bash
p2p work plan CHANGE-XXX --author "matteo" --agent "codex"
p2p work list --change CHANGE-XXX
p2p work compare WORK-001 WORK-002
p2p work select WORK-001 --reason "..."
p2p work reject WORK-002 --reason "..."
p2p work combine WORK-001 WORK-003 --reason "..."
```

Existing implementation commands remain the execution path after candidate selection:

```bash
p2p work branch WORK-XXX
p2p work submit WORK-XXX
p2p work review WORK-XXX
p2p work publish WORK-XXX
p2p work request-review WORK-XXX
p2p work accept WORK-XXX
p2p work accept --continue WORK-XXX
p2p work accept --abort WORK-XXX
p2p work finalize WORK-XXX
p2p work cleanup WORK-XXX
p2p work retire WORK-XXX
```

Local/cloud semantics:

```text
local: branch local, review local, merge local, audit local.
cloud: fetch remote state, branch local, publish branch to remote, optional PR/MR handoff, merge/finalize against remote-backed base branch, audit local plus remote metadata.
```

Remote-backed projects must not change the core lifecycle. They add remote profile validation, safe fetch/pull/push wrappers, branch publication, provider-specific review automation or guidance, and final base-branch push.

Candidate decision model:

- Independent proposal branches may be accepted and merged separately if validation passes and no project-state conflict is detected.
- Competing proposal branches for the same problem should create or reference a P2P Choice before one is accepted.
- Multiple Work candidates may exist for one Change Set.
- A Work candidate must be selected before owner-controlled accept/merge when more than one candidate exists for the same Change Set.
- Rejected and retired candidates remain auditable and must not disappear from project history.
- Combining candidates should create a new Work item or proposal branch that records its source candidates rather than silently mutating one branch.

Required engine hardening:

- Validation must report duplicate proposal IDs as an explicit P2P error.
- Registry generation must fail clearly or mark an error when duplicate proposal IDs exist; it must not silently produce ambiguous project state.
- Proposal lookup must preserve the current ambiguity guard and user-facing commands must surface actionable recovery guidance.
- Publish and merge operations must re-run duplicate-ID checks against local and fetched remote state.
- Auto-renumber must be safe, auditable, and non-destructive until the replacement branch is created and validated.

Audit metadata required for proposal and Work branch decisions:

```text
actor_id
actor_type: person|agent
agent_profile, when applicable
source_branch
base_branch
proposal_id, when applicable
change_id, when applicable
work_id, when applicable
branch_hash16
decision_kind: accept|reject|select|combine|retire|merge|abort|finalize
id_allocation_source
id_collision_check
remote_scan_commit
review_status
local_commit
merge_commit
remote_name
remote_url
remote_branch
review_url, when available
conflict_files
created_at
decided_at
```

Agent instruction requirements:

- Generated `AGENTS.md`, Codex skill instructions, and Claude/generic agent instructions must state that agents use P2P CLI commands for managed proposal, Work, and sync operations.
- Agents must not run raw `git branch`, `git merge`, `git fetch`, `git pull`, `git push`, or provider-specific PR commands for managed project state unless a user explicitly authorizes an escape hatch.
- Agents must inspect P2P status and sync status before creating proposal or Work branches.
- Agents must keep draft proposal work off `main` unless the project policy explicitly allows direct-owner drafts on main.
- Agents must stop and ask for owner approval before accept, merge, finalize, cleanup, or remote publication if policy marks those actions as owner-controlled.

This proposal intentionally defines the CLI-facing collaboration model. Permission-gated MCP exposure of these operations remains part of PROP-066.

### PROP-073 - Ergonomic Remote Project Initialization

Extend p2p init and remote profile setup with an ergonomic remote initialization flow. Add init options such as --repository cloud, --provider, --remote, and --remote-url. During init, P2P should write the project remote profile, detect whether the named Git remote exists, compare its URL when present, and print actionable follow-up commands when Git state is missing or mismatched. The command should not create provider resources in the MVP. Existing p2p project remote configure remains available for later edits, and p2p sync status remains the validation command after setup.

### PROP-074 - Agent Runtime Bootstrap Robustness

Introduce an Agent Runtime Bootstrap Robustness model. Generated AGENTS.md, agent policy, and docs should include a runtime discovery sequence: try p2p, try repository-local virtualenv paths when present, try python -m p2p_engine if the package is importable, then check MCP availability. Add a diagnostic command or script such as p2p doctor, p2p agent doctor, or a lightweight repo-local bootstrap hint that reports whether p2p CLI, MCP server, Git, and project root are usable. For cloud environments, provide a documented install/bootstrap path that agents can request from the owner rather than stopping with only p2p command not found. The Missing Primitive Rule remains valid, but the error should include actionable recovery steps.

### PROP-075 - MCP End-To-End Proposal Collaboration Workflow

Define an MCP end-to-end proposal collaboration workflow: create or update draft proposal, persist/commit draft state through an explicit P2P primitive or documented auto-commit policy, create a managed proposal branch from an explicit base branch such as main, request or reference owner consent, publish the branch, and request review. Add MCP tools or behavior such as p2p_project_remote_configure, p2p_consent_request, p2p_proposal_draft_commit, and p2p_proposal_branch with base_branch. Keep p2p_consent_grant owner-controlled; MCP may request consent, but granting consent should remain CLI/UI/server owner action until strong authentication exists.

### PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

Adopt a strict boundary: P2P Engine exposes stable local automation primitives through CLI, local project files, Git, and local MCP. P2P Cloud is a separate web/API product that uses P2P Engine by launching isolated runner jobs. The cloud stack may use Caddy, a web/API framework such as Django/DRF or NestJS, PostgreSQL for users/projects/jobs/permissions, Redis or equivalent queues, Prefect or equivalent workflow orchestration, and ephemeral p2p-runner containers. Each runner gets a temporary workspace, checks out or initializes the target Git repository, executes p2p CLI commands, records .p2p state, commits/pushes through Git, emits logs/artifacts, and exits. P2P Engine must not become a public multi-tenant API server, IAM system, web UI, workflow scheduler, provider PR automation service, or hosted database-backed application.

### PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

Add p2p_proposal_accept, p2p_proposal_reject, and p2p_proposal_defer MCP tools. Each tool must require proposal_id, actor_id, consent_id, and reason, validate a granted consent receipt for operation proposal_accept/proposal_reject/proposal_defer targeting the proposal ID and actor, call the same workspace decision path used by the CLI, consume the consent with audit metadata, and document that MCP can request but not grant consent.

### PROP-078 - Project-Local Wheel Installation and Upgrade Model

Introduce a packaging and installation model based on versioned wheel artifacts attached to GitHub Releases as the first distribution channel. Project setup documentation should install P2P Engine into the project-local .venv from a release wheel URL, and project upgrade documentation should use python -m pip install --upgrade <wheel-url>, followed by p2p doctor, p2p agent doctor, p2p registry refresh, p2p agent instructions refresh, and p2p validate. This is a transitional distribution model: the long-term target remains a public package such as PyPI, where installation becomes python -m pip install p2p-engine and upgrade becomes python -m pip install --upgrade p2p-engine. The proposal should avoid requiring users to reference external source checkout paths during normal project use.

### PROP-079 - Managed Next Action Lifecycle

Implement a hybrid next-action lifecycle. Curated active actions remain in .p2p/project/next-actions.yml. Completed and retired curated actions are moved to .p2p/project/next-actions-log.yml with status, reason, and date. Generated actions are computed at runtime from project state using the existing fallback/blocker logic and shown alongside curated actions with clear source labels. Add CLI commands p2p next list, p2p next add, p2p next complete, p2p next retire, and p2p next refresh. The default p2p next view should list curated plus generated actions with deduplication by kind/target. p2p next complete NEXT-003 --reason ... should remove the obsolete curated item from active next actions and record an audit log entry.

### PROP-080 - Automated GitHub Release Wheel Publishing

Add a GitHub Actions release workflow triggered by version tags matching v*. The workflow should check out the repository, set up Python, install development dependencies, run the test suite, run p2p validate, build the source distribution and wheel with python -m build, verify expected dist artifacts exist, and upload the .whl and .tar.gz as assets to the matching GitHub Release. Document the new release flow: update pyproject.toml version, commit and push main, create and push an annotated tag such as v0.1.1, then GitHub Actions publishes the release assets. Keep manual release notes as a fallback, but make the tag-triggered workflow the normal path.

### PROP-081 - MCP and Skill Support for Managed Next Actions

Add MCP tools p2p_next_add, p2p_next_complete, p2p_next_retire, and p2p_next_refresh. Treat these as write-safe project planning tools without consent receipts because they update the operational next-action board and audit completed/retired entries, but do not decide proposals, merge branches, publish remotes, or change governance policy. Update the p2p-engine skill and MCP documentation to explain that p2p_next remains read/list, while the new tools manage curated next actions. Keep owner-controlled governance boundaries intact.

### PROP-082 - Readiness Assessment Refresh And Review Workflow

Extend the readiness review and proposal-question workflow so generated questions are artifact-aware, not only score-gap-aware. When readiness is weak, low-confidence, blocked by gates, or missing evidence, the agent must inspect the full proposal artifact set and generate or update questions that seek coverage across proposal.md, exploration.md, findings.md, alternatives.md, risks.md, assumptions.md, open-questions.md, suggested-scope.md, impact-map.yml, related/conflict artifacts, readiness.yml, questions.yml, and duplicate or aggregation evidence. The question list should represent the missing information needed to make the proposal robust and approvable, not just the labels currently listed in readiness.missing. When answers are recorded, the workflow must help the agent apply them to every useful affected artifact through available CLI or MCP write primitives. A question answer may update the proposal text, acceptance criteria, alternatives, tradeoffs, risks, assumptions, open questions, impact analysis, duplicate/aggregation notes, or readiness evidence. Applied question state should mean the answer has been propagated into proposal artifacts or an explicit reason exists for why no artifact update was needed. Agent assertiveness should be driven by a stepped readiness policy rather than a separate pedantry score. Very low or weak readiness requires proactive challenge, next-question selection, and refusal to recommend acceptance without owner override. Partial readiness requires focused follow-up on missing artifacts and high-risk ambiguity. Near-target readiness requires only residual high-value questions or confirmation. Deferred and muted question/group states reduce re-asking unless the owner explicitly asks to increase readiness or revisit unanswered material. After applying answers or importing refined artifacts, readiness must be recalculated through the evidence-aware assessment path; low readiness should cause the skill to direct the agent to continue interviewing the owner instead of passively reporting gaps.

### PROP-083 - Domain-Aware Visible Project Definition Export

Introduce a domain-aware visible project definition export. The default export for every P2P project should be a human-facing, comprehensive Markdown document written to outputs/latest/project.md. The document should be organized in chapters and synthesize accepted P2P memory: project purpose, domain, problem framing, accepted proposals, decisions, requirements, scope boundaries, alternatives, tradeoffs, risks, assumptions, open questions, readiness notes, and relevant implementation or delivery context. The output should be generic across verticals and should not assume that the project is software. The visible root-level outputs/ directory is intentional and not configurable in the MVP because human accessibility is more important than keeping the repository root minimal; outputs/ is preferred over project/ because it clearly describes generated visible outputs and avoids confusion with .p2p/project. Each export run should preserve review history by writing or archiving prior versions under outputs/review-001, outputs/review-002, and later review directories. Domain-specific exports are additional nested profiles, not the default. For software-compatible projects, software-spec, OpenSpec, Spec Kit, or similar outputs may be generated under outputs/latest/exports/software-spec/, outputs/latest/exports/openspec/, outputs/latest/exports/speckit/, or equivalent profile folders. Other verticals may define their own export profiles under outputs/latest/exports/<profile-or-vertical>/. Existing .p2p/outputs behavior must be treated as a compatibility surface: the implementation should verify whether current generated artifacts are still needed, preserve public CLI/API expectations, and only remove, deprecate, or relocate legacy outputs through an explicit compatibility path.

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

Introduce pluggable project verticals. A vertical package defines its id, name, version, base extension, sections, section detail packs, maturity levels, rubric criteria, blocking/refinement questions, artifact templates, examples, profiles, and optional compatible modules. P2P Engine provides a generic loader/validator and a project orchestrator skill that reads these definitions, evaluates project readiness, proposes capisaldi, creates initial refinement questions, and guides a one-question-at-a-time interview. Vertical packages are pure data packages made of text files, primarily .md and/or .yaml, not executable code in the MVP. They contain the project skeleton for the vertical: chapters, sections, topics to address, vertical-specific peculiarities, rubrics, questions, and useful artifacts. The minimum MVP vertical pack requires vertical.yml with id, name, version, description, and base/extends; project sections/chapters; minimal completeness/readiness rubrics; initial blocking questions; and expected or suggested artifacts. Examples, profiles, compatible modules, and rich output templates are optional in the MVP. Default vertical packs are distributed internally with the project/package as versioned, testable data resources for the MVP. The design should stay registry-ready, but an external registry is not part of the first slice; a later registry can expose REST endpoints to list available packs and fetch pack details/versions. The CLI remains deterministic: p2p init may ask deterministic setup questions and persist project/init state, but it does not launch or embody the agent. The proactive behavior belongs to the agent instructions. When the agent detects an uninitialized project, an initialization state, or missing project capisaldi and initial questions, it must treat that as priority context work because it determines project readiness. The agent should know how to initialize the project with the CLI, use owner answers to populate init/project objects, propose the vertical-derived capisaldi, save initial questions when possible, interview one question at a time, and return to deferred core-definition work unless the owner explicitly silences it. When a requested vertical is missing, resolution order is project-local vertical packs, core/default packs, configured data registry/plugin packs, then base_project fallback. The fallback is not passive: the agent proposes a default/base vertical, enters customization mode, extracts the missing vertical information from the owner, creates or updates a project-local custom vertical with sections/capisaldi, minimal rubrics, blocking questions, and expected artifacts, and uses it only after owner confirmation. This proposal extends and reuses the existing project rubrics and project maturity/readiness artifacts rather than replacing them. Vertical packs provide structured inputs that specialize the current system; they must not create a parallel maturity engine. The explicit command for later review is p2p project readiness review: the command goal is project readiness/context strengthening, while verticals are the data source used by the review. It should reuse existing project rubrics/maturity, read packaged and project-local verticals, identify missing capisaldi, produce initial or follow-up project questions, and guide the agent on readiness priorities. Core should start with base_project and a small MVP set of high-quality verticals, while additional verticals live in an external registry or project-local custom directory. Initial implementation scope is base_project plus the vertical pack loader/validator, the project orchestrator skill, one complete demonstration vertical, and project readiness review integration. The five-vertical MVP set remains a follow-up target, not part of the first implementation slice.

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

Introduce artifact-aware proposal readiness backed by a dedicated artifact-specific primitive. Each proposal artifact type receives an expectation class: required for decision, required when applicable, optional memory, or not applicable with reason. The source of truth for artifact applicability is a public CLI/MCP surface such as proposal artifact state commands/tools, not free-form contribution text, not hidden readiness-only metadata, and not direct filesystem writes. Readiness and compact context consume artifact state: they surface empty or weak applicable artifacts as concrete gaps, report not-applicable and legacy reasons, and suggest owner-facing questions. The artifact state lifecycle should include unknown, missing, weak, satisfied, deferred, not_applicable, and absent_legacy. unknown means a new proposal artifact has not yet been assessed. missing means it is applicable but absent or empty. weak means present but insufficient. satisfied means adequate for the current readiness profile. deferred means a known gap is intentionally postponed and must remain visible. not_applicable requires a concrete rationale. absent_legacy marks proposals created before artifact-aware state existed; it is advisory and non-blocking. Artifact state records at least artifact id/type, expectation, status, reason, actor/source, timestamp, risk flags, and whether the state is agent-proposed or owner-confirmed when relevant. Agents may propose artifact status and rationale, but the owner has final authority over governance decisions and acceptance. For always-required or auto-required artifacts, agent-proposed not_applicable or deferred states remain owner-visible and should not be treated as silently equivalent to satisfied. The MVP CLI/MCP surface should be narrow: initialize artifact state for a proposal, show/list artifact coverage, set an artifact expectation/status/reason, mark legacy absence, and expose the same operations through explicit write-safe MCP tools that internally use the P2P engine write path. Example command shape: p2p proposal artifact status PROP-XXX; p2p proposal artifact init PROP-XXX; p2p proposal artifact set PROP-XXX impact-map --expectation required_when_applicable --status not_applicable --reason '...'; p2p proposal artifact mark-legacy PROP-XXX. Exact names may change, but the public primitive must exist before agents are expected to persist artifact state. The default artifact policy is graduated by risk. proposal.md, readiness.yml, and open-questions.md are always required for proposal maturity. clarifications.md, findings.md, exploration.md, and impact-map.yml are required when applicable. findings.md and impact-map.yml become auto-required when robust risk triggers are present: governance or policy changes; public CLI, MCP, API, or command behavior changes; storage schema, registry, proposal layout, or persistent state changes; compatibility or migration impact; cross-module/shared service/core workflow impact; permission, consent, security, remote sync, provider, or destructive-operation concerns; source-of-truth, agent instruction, memory, or artifact-writing behavior changes; user-visible workflow, docs/install/release impact; new dependency/runtime/infrastructure assumptions; high uncertainty, multiple credible alternatives, or claims that depend on technical evidence. exploration.md becomes required when multiple credible alternatives exist, uncertainty is high, or the proposal chooses between materially different designs. clarifications.md becomes required when owner answers correct, narrow, or change an assumption. Existing proposals are handled compatibly: when artifact-aware state is absent, artifact-aware commands, readiness refresh, context generation, or a dedicated migration/status command should detect it and mark/report absent_legacy through the P2P write interface. Legacy absence must not raise validation errors, block decisions, or force manual retroactive completion. Coverage improves naturally for new proposals without requiring review of historical work. Integration boundaries are strict. Agents interact with P2P memory only through the p2p CLI or explicit MCP write tools whose schema describes the mutation. A local agent must follow the same boundary as a future remote MCP client: no direct edits under .p2p, no copying prepared temporary files into artifacts, no reverse-engineering internal layouts, and no filesystem workaround when a primitive is missing. If an artifact update requires large text, the solution is a CLI/MCP import/update primitive, not a temp-file copy into managed state. If no supported primitive exists, the agent stops and reports the missing primitive. Readiness, context, validation, registries, and MCP tools must reuse artifact state rather than duplicating a parallel lifecycle. Validation checks structural consistency; readiness scores maturity; context summarizes next action; artifact state remains the source of truth for artifact coverage. Test coverage should include a new simple proposal, a new cross-cutting proposal that auto-requires findings and impact map, a legacy proposal without artifact state, not_applicable with rationale, deferred with owner visibility, MCP write-safe behavior, missing-primitive refusal, and a guard that direct/temp-file artifact writes are not part of the workflow.

### PROP-087 - Agent Personality Model For Decision Mediation

Introduce a project-level interaction_style configuration model with three independent integer fields: technical_verbosity 0..5, formality 0..5, and assertiveness 0..5. technical_verbosity controls how much engine/technical language the agent uses with the decision owner. formality controls how informal or formal the tone is. assertiveness, informally described by the owner as pedanteria, controls how strongly the agent pushes on unresolved gaps, evidence, order, and follow-up before moving on. Defaults: technical_verbosity=2, formality=2, assertiveness=0. The first implementation stores one project-level default interaction_style because the project should define a shared interaction style for all agents and mediators that address the decision owner. The public CLI namespace should be project interaction-style, with matching MCP tools. Values must be readable and modifiable through public P2P CLI commands and exposed through explicit MCP tools with read-only and write-safe behavior. Generated agent instructions and local/project skills must describe how agents inspect and update the style through those CLI/MCP surfaces. Per-agent and per-session overrides are future extension points. Named presets should not be persisted as source of truth; scales remain explicit and independent.

## Domain And Context

### PROP-001 - — CLI Foundation

The current repository is being bootstrapped manually. The manual `.p2p/` structure defines the file format that the first CLI must later generate.

The first useful milestone is not a web app, AI billing, MCP server, or complete exporter set. The first useful milestone is a local Git-native CLI that can create the same structure currently being created by hand.

### PROP-002 - Proposal Exploration And Readiness Workflow

Il dogfooding del progetto ha mostrato che il modello iniziale di
`Exploration Phase` era utile ma troppo stretto. `p2p explore prompt`,
`p2p explore import` e `p2p explore status` permettono di creare e popolare
artifact, ma non bastano a garantire che una proposta sia ben strutturata.

L'esplorazione di PROP-002 ha chiarito che il modello deve distinguere:

- lifecycle state: dove si trova proceduralmente la proposal;
- computed readiness: quanto e matura secondo criteri espliciti;
- effective governance status: cosa decide l'owner, anche tramite override;
- artifact quality: quanto gli artifact sono specifici, utili e completi;
- confidence: quanto l'analisi e fondata su evidenze solide.

Il modello deve restare compatibile con il principio P2P: CLI/engine come fonte
operativa, artifact versionati come memoria, agenti come guida conversazionale,
owner come autorita governance.

### PROP-004 - Prompt-only Import Workflow

Il workflow MVP deve restare prompt-only: la CLI prepara prompt, l'utente o Codex produce output, la CLI importa gli artefatti versionati.

### PROP-005 - Codex Skill Integration

P2P Engine ora supporta un workflow prompt-only completo con prompt/import per exploration, clarify, synthesize, plan e tasks.

### PROP-006 - Multi-Agent Integration Model

The original PROP-006 proposed an agent integration layer inspired by Spec Kit and OpenSpec. Subsequent work implemented the first layer through p2p init --agent, p2p agent instructions refresh, AGENTS.md, CLAUDE.md, .codex skills, .p2p/agent-policy.yml, and MCP bootstrap tools. The remaining gap is lifecycle governance for installed agent integrations and their generated files. Generated instructions, CLI, and MCP are separate layers: instructions define method and guardrails, CLI exposes textual commands, and MCP exposes the same P2P capabilities as structured tools for compatible agents. P2P should not choose or record a project-level preferred agent: collaborators may use different tools at the same time. Agent incisiveness is not a Codex-specific profile concern; it is a common P2P method behavior that must be carried by the generic baseline and inherited by every generated adapter file.

### PROP-009 - Governance CLI Commands

PROP-008 ha definito owner_decides, open_consensus, exclusive_vote, votes.yml, swot-analysis.md e decision-precedents.yml. Ora serve rendere questi artefatti operativi nella CLI senza introdurre ancora permessi reali.

### PROP-010 - P2P Project State Model

OpenSpec and Spec Kit are useful downstream targets, but P2P Engine needs its own intermediate project model before exporting to those tools.

### PROP-011 - Project Refresh MVP

PROP-010 accepted .p2p/project as the versioned project state derived from accepted proposals.

### PROP-012 - Impact Map and Conflict Memory

PROP-010 and PROP-011 introduced .p2p/project as project state. The next step is preserving impact and conflict memory so accepted decisions are not reconsidered accidentally.

### PROP-013 - Managed Git Adapter and Change Set Model

The current foundation still risks coupling proposals and branches too tightly. PROP-012 introduced impact/conflict memory; the next step is a managed Git adapter model with explicit change sets and a user-facing workflow based on P2P concepts rather than Git concepts.

### PROP-014 - Change Set Metadata MVP

PROP-013 defines Change Set as the visible operational unit and keeps Git operations metadata-only for the MVP.

### PROP-015 - Change Set Lifecycle and Task Tracking

PROP-014 introduced .p2p/changes metadata. The next step is making Change Sets usable for following execution progress.

### PROP-016 - Project Registries MVP

PROP-010 introduced .p2p/project, PROP-012 introduced conflict memory, and PROP-014/015 introduced Change Sets. The next step is making global navigation and provenance explicit.

### PROP-017 - Proposal Intake and Context Analysis MVP

PROP-016 introduced generated registries. The next step is using those registries to analyze incoming ideas against existing project memory.

### PROP-018 - Choice Management CLI MVP

INTAKE-001 suggested opening CHOICE-001. The choice was created manually, proving the artifact model but exposing the need for CLI commands.

### PROP-019 - Proposal Decision Shortcut Commands

Choice and intake workflows now produce recommended actions that require clear proposal lifecycle commands.

### PROP-020 - Proposal Inspection CLI MVP

Agent skills need simple, stable commands for checking proposal state before creating intake, choices or decisions.

### PROP-021 - Agent Skill Real Commands Update

P2P Engine now has stable commands for proposal list/show, intake prompt/import/status, choice create/list/decide and proposal accept/reject/defer.

### PROP-022 - Operational Brief Prompt Workflow

The project uses prompt-only workflows for exploration, impact, and intake. The same pattern should introduce intelligence without making the CLI decide on behalf of the owner.

### PROP-023 - Next Action Recommender MVP

The owner decided that p2p next should be top-level, advisory only, list ordered actions with --top support, read .p2p/project/next-actions.yml when present, and compute conservative fallback actions when it is missing or empty.

### PROP-024 - Choice Blocking and Discovery MVP

The project now has p2p next and operational brief artifacts. The next intelligence step is to distinguish related choices, discovered candidate blockers, and formal blocks without letting the CLI decide on behalf of the owner.

### PROP-025 - Controlled Intake Apply Workflow

The project now supports operational briefs, p2p next, and choice discovery/blocking. Intake apply should follow the same source-of-truth discipline: plan first, show reviewable actions, run only explicit supported actions, and log what was applied.

### PROP-026 - P2P Software Spec Generator MVP

CHANGE-001 established Change Set as the operational unit and separated execution_domains, implementation_targets, spec_targets and export_targets. PROP-010 already selected a P2P-native software spec before downstream export.

### PROP-027 - Software Spec Exporter MVP

CHANGE-012 introduced the P2P-native software spec layer. The next step is to export from that normalized layer instead of reading raw proposal folders.

### PROP-028 - Spec Kit Export Mapping MVP

CHANGE-013 added generic and OpenSpec-oriented software spec exports. Spec Kit expects a specification-driven feature directory with spec, plan, supporting design artifacts and tasks.

### PROP-029 - Spec Export Validation MVP

CHANGE-013 and CHANGE-014 added software spec export targets. Downstream handoff should not rely only on generation success; agents need a read-only validation command.

### PROP-030 - Managed Work and Multi-Branch Visibility Policy

CHANGE-001 established managed Git as an internal adapter. CHANGE-012 through CHANGE-015 created a spec/export/validate pipeline. The next step is to define work manifests and the incremental path toward invisible managed Git.

### PROP-031 - Multi-Branch Work Scan MVP

CHANGE-016 introduced P2P Work manifests and the incremental path toward invisible managed Git. The next step is read-only branch visibility.

### PROP-032 - Managed Work Branch Creation MVP

The project policy keeps Git invisible to the user while using managed work branches under the hood to avoid divergence on main.

### PROP-033 - Managed Work Submit MVP

The managed Git path should keep Git under the hood while giving the owner a clear Work lifecycle before later review and merge steps.

### PROP-034 - Managed Work Review MVP

Level 4 should prepare the review handoff while keeping remote push, PR creation, and merge out of scope until later levels.

### PROP-035 - Managed Work Publish MVP

Level 4.5 should be the remote handoff step between local review and owner-controlled merge. It must keep PR creation and merge separate.

### PROP-036 - Managed Work Accept MVP

Level 5 should integrate published Work only through an explicit owner action, while keeping push to the base branch and branch cleanup separate.

### PROP-037 - Managed Work Status Summary MVP

After Level 5, the base workflow exists but needs a safer operational summary before adding GitHub PR or finalize behavior.

### PROP-038 - Managed Work Merge Conflict Guidance MVP

Managed Work Level 5 exists. Before adding finalize, cleanup, or GitHub PR flow, accept must leave the repository and Work manifest in a clear state when a merge conflict occurs.

### PROP-039 - Managed Work Finalize MVP

Managed Work now supports plan, branch, submit, review, publish, accept, status, and merge conflict guidance. Finalize should be the explicit post-accept publication step, separate from cleanup and PR creation.

### PROP-040 - Managed Work Cleanup MVP

The managed Work lifecycle now reaches finalization. Cleanup should be separate from finalize so branch deletion remains explicit and reversible by policy.

### PROP-041 - Remote Project Profile and Review Request Policy

The owner wants GitHub/GitLab support to remain optional and adapter-based while keeping Git invisible under P2P Work commands.

### PROP-042 - P2P Core CLI MCP Mediator Web Boundary

The accepted direction is to keep P2P usable as an open local product while enabling optional intermediaries: agent skills, MCP tools, mediators, and later web collaboration. The owner wants users to choose their intermediary without making the core depend on AI infrastructure.

### PROP-043 - Managed Work Retire MVP

WORK-001 is a planned speckit handoff for CHANGE-012, but CHANGE-012 and the speckit exporter are already completed. P2P needs a first-class way to retire obsolete planned Work items instead of editing manifests by hand.

### PROP-044 - P2P MCP Server MVP

PROP-042 established that MCP is an agent-facing interface over the deterministic P2P Core, not the mediator itself. The first MCP implementation should be local, read-only, and provider-neutral.

### PROP-045 - Agent-Safe Project Bootstrap MVP

The first local MCP test succeeded for read-only status, but an agent then created proposal files and an accepted decision directly under .p2p because the test project lacked P2P agent instructions and MCP write tools.

### PROP-046 - MCP Write-Safe Bootstrap Tools MVP

CHANGE-030 added agent-safe init and instruction refresh in the CLI/Core. The next increment is to expose only those safe bootstrap mutations through MCP, without adding governance decisions or managed-work mutations.

### PROP-047 - Guided Init Wizard MVP

After the MCP local test, the product direction is to make project bootstrap safe and understandable before expanding MCP mutations. The CLI should guide first-time users while keeping scriptable flags available.

### PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

The tested Codex/Codium workflow now correctly stops instead of editing .p2p by hand. The next safe MCP increment should expose draft creation primitives while keeping proposal acceptance and governance decisions owner-controlled.

### PROP-049 - MCP Level 4A Proposal Refinement Tools

Level 3 intentionally stopped before governance decisions. The next advisory workflow increment should support draft refinement and operational synthesis prompts without accepting proposals or applying decisions.

### PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

Level 4A completed proposal refinement while keeping governance decisions out of MCP. The next advisory level should expose analysis-only tools that help agents understand divergence and impact without recording decisions or conflicts.

### PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

The La scatola perfetta MCP test created a correct draft proposal, but next action remained weak. The agent explanation was good, but it should be anchored to current P2P state rather than conversation memory.

### PROP-052 - MCP Proposal Contribution Tool

The La scatola perfetta test produced multiple related draft proposals. P2P already has a controlled CLI contribution command and core method. Exposing that primitive through MCP is safer than letting agents create separate proposals for every related idea.

### PROP-053 - Core Validation Layer MVP

The current p2p check command only verifies minimal bootstrap files. Before packaging and before owner-gated MCP mutations, the core should expose a semantic validation pass with stable finding codes, severities, JSON output, and MCP access.

### PROP-054 - Project Readiness and Maturity Assessment

Recent MCP tests show that agents can now create and refine draft proposals safely. The next product layer should help owners and agents reason about project readiness without pretending that subjective quality is fully objective. Different project domains need different maturity criteria, such as software security/usability/maintainability or non-software domain-specific criteria.

### PROP-055 - Agent Token Budget and Context Discipline

The product direction is: AI is expensive, CLI is cheap, Git is memory, .p2p is governance, owner decides, and agents work in bounded sessions. Current skills already require using CLI/MCP primitives and avoiding manual .p2p edits, but they do not yet define an explicit token budget discipline or compact context contract for agents.

### PROP-056 - Project Definition Maturity Rubrics

P2P Engine aims to export a project definition toward downstream generators, agents, OpenSpec/Spec Kit, or implementation workflows. Different project domains require different definition criteria: software, grant/bid documents, board games, documents, hardware, services, and other domains need different rubrics. The init wizard can ask for a project domain and create a rubric checklist that becomes the deterministic driver for future maturity assessment.

### PROP-057 - Guided Rubric Selection During Init

Project definition maturity is now based on .p2p/project/rubrics.yml. The rubric file already supports enabled/disabled criteria, and the assessment ignores disabled criteria. Therefore the init wizard can offer a lightweight owner confirmation step without adding custom criteria, keyword editing, or advanced UI.

### PROP-058 - Project README and Installation Guide

The current installation path is source-based Python with a virtual environment. Future packaging may move toward a compiled/installable CLI, but the immediate user need is clear documentation for cloning, installing, initializing a project, using compact context, running assessment, and configuring MCP locally.

### PROP-059 - P2PWorkspace Modular Refactoring Plan

The current repository has broad and growing surfaces: CLI, P2PWorkspace facade, filesystem storage, Git collaboration, registries, project refresh, readiness/maturity assessment, software/spec export, MCP tools, permission/consent handling, generated agent policy, and local development specs. The proposal has been refined through owner discussion: the first deliverable must be an architecture contract and development guidance, not source refactoring. P2PWorkspace should remain the compatibility facade while internal managers/services become the target home for cohesive behavior. This proposal remains in P2P governance scope; implementation tasks will be derived later through the local specs binding workflow after acceptance.

### PROP-061 - Focused README and Documentation Map

P2P Engine documentation now has an installation guide, but the repository still needs a focused README and stubs for the detailed documentation areas identified as important for humans, agents, and contributors.

### PROP-062 - README Product Landing Page Refinement

The repository is being made public. README should explain P2P Engine as the engine, not future hosted products, and route detailed material to docs.

### PROP-064 - Spec Kit Three-Prompt Export Model

Accepted PROP-027 and PROP-028 implemented conservative file bundle exports from P2P-native software specs. User review showed this does not match the desired integration contract. Spec Kit starts from three agent prompts: constitution, specify, and plan. OpenSpec starts from a proposal-oriented input. Generic export should be a readable full project definition and a project/proposal initialization input. Therefore project.md should become the canonical generic synthesis artifact, and downstream exports should be deterministic views derived from it and its P2P evidence.

### PROP-065 - MCP Agent-First Coverage Expansion

The owner requested adding MCP coverage for priority 1 read-only tools, priority 2 write-safe deterministic tools, and priority 3 prompt/advisory tools while preserving governance boundaries.

### PROP-066 - Permission-Gated MCP Governance And Git Operations

Current MCP tools are limited to read-only, write-safe deterministic, and advisory prompt operations. Deferred operations include proposal accept/reject/defer, choice decide/block, conflict/vote/precedent record, spec import, Work publish/accept/finalize/cleanup, proposal branch publish/request-review/retire/accept/reject/merge, push/pull, merge, provider PR/MR workflows, and other repository-sensitive operations.

Recent concurrent collaboration work clarified that P2P should expose a safe MCP surface now, but privileged MCP operations must not rely on local actor names as strong identity. In a local or Git-only setup, actor IDs are declarative audit metadata. In cloud-backed repositories, the strongest enforcement comes from the Git provider: repository permissions, protected branches, required approvals, and token scopes. A future API server or IAM integration may add stronger identity verification, but it is not required for the first permission-gated MCP model.

### PROP-067 - Agent-First Setup Documentation Split

README currently has a 5-minute demo with manual CLI commands. INSTALL documents source installation, project init, MCP setup, and manual first commands. CONTRIBUTING has basic developer setup but does not clearly explain how contributors should enable their agent to add proposals to the P2P Engine project state.

### PROP-068 - Document Agent MCP Client Setup Commands

README should stay concise and avoid contributor-specific examples. INSTALL is the right place for new-project MCP client setup. CONTRIBUTING remains the only place for configuring an agent against the P2P Engine repository itself.

### PROP-069 - Clarify MCP Stdio Integration Model

P2P Engine currently exposes a local stdio MCP server through the Python module p2p_engine.mcp.server. In stdio mode, each MCP client starts its own local process and shared project state lives in the target repository, .p2p, Git, and P2P core storage. The docs should distinguish this from future shared Streamable HTTP operation.

### PROP-070 - Clarify README Agent Access Modes

P2P Engine supports agent-mediated use through CLI access or MCP access. CLI access can reach the full local command surface when the owner explicitly authorizes actions. MCP access is structured and safer, but intentionally limited until a repository permission and ownership model is accepted.

### PROP-071 - Custom Domain Definition Workflow

Domain and rubric setup should be modeled consistently for every project. Predefined domains should be optional templates that pre-populate domain/rubric metadata, not proof that the project is already semantically well-defined. Custom or no-template projects should start with explicit unresolved domain/rubric state and recommended setup activities.

### PROP-072 - Concurrent Managed Work and Merge Decision Model

P2P Engine already has an accepted managed Work lifecycle for implementation work: plan, branch, submit, review, publish, request-review, accept, finalize, cleanup, retire, and scan. It also has remote project profile concepts that distinguish local and cloud projects without binding the core model to a single provider. Recent design discussion clarified that Git should remain the interchange and storage layer, while normal users and agents should operate through P2P CLI commands and generated agent instructions, not raw Git.

The unresolved collaboration model is proposal-level and candidate-level concurrency. In a cloud-backed project, one person may own main as accepted project state while another person or agent creates new proposal drafts or alternative implementations. In a local-only project the same behavior exists, except branches do not need to be pushed to an external remote. Therefore local and cloud should share one semantic lifecycle, with cloud adding publication and external review handoff.

### PROP-073 - Ergonomic Remote Project Initialization

Not recorded.

### PROP-074 - Agent Runtime Bootstrap Robustness

Not recorded.

### PROP-075 - MCP End-To-End Proposal Collaboration Workflow

Not recorded.

### PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

Not recorded.

### PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

Not recorded.

### PROP-078 - Project-Local Wheel Installation and Upgrade Model

Not recorded.

### PROP-079 - Managed Next Action Lifecycle

Not recorded.

### PROP-080 - Automated GitHub Release Wheel Publishing

Not recorded.

### PROP-081 - MCP and Skill Support for Managed Next Actions

Not recorded.

### PROP-082 - Readiness Assessment Refresh And Review Workflow

This proposal refines the accepted exploration and readiness direction by separating information completeness from agent behavioral guidance. It keeps agent proactivity and deterministic clarification interview inside PROP-082 for now rather than splitting a separate proposal. It should remain compatible with conservative deterministic refresh, owner-controlled governance, readiness profiles, evidence records, p2p next recommendations, MCP context, clarification workflows, and agent skills. It should also connect proposal-level readiness with project-level assessment and maturity rubrics without collapsing them into one score. Current CLI primitives can add contributions, update structured proposal sections, and generate/import clarification prompts, but a production-ready workflow requires a first-class deterministic proposal-question object and CLI surface. Backward compatibility is mandatory: older proposals without question state must continue to work, with CLI commands reporting absent question state rather than failing.

### PROP-083 - Domain-Aware Visible Project Definition Export

The accepted project memory already contains proposals, decisions, readiness, questions, risks, assumptions, alternatives, and refinement history. PROP-083 should turn that memory into a visible human-facing project definition. Existing software-specific exports may remain useful, but they should become specialized export profiles nested under the generic visible output model rather than the universal default. The root folder should be named outputs/ instead of project/ to avoid confusion with .p2p/project. Existing .p2p outputs should not be removed or moved without a compatibility check.

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

This proposal extends the direction opened by PROP-057, Guided Rubric Selection During Init. PROP-057 lets the owner confirm suggested rubric criteria during init. The next step is to treat a vertical as a data-driven package loaded by a generic project orchestrator skill: base_project plus optional verticals/modules/profiles that can live in core defaults, registries, or project-local custom packs. The attached discussion distinguishes a stable orchestrator skill from vertical definitions and section detail packs, recommends a small high-quality default set, and keeps broader growth in plugins/registries rather than hardcoding all possible verticals in P2P Engine.

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

This refines the accepted direction of PROP-085. PROP-085 defines pluggable project verticals and readiness orchestration for project definition. This proposal applies the same principle to proposal collaboration itself: artifacts should be typed readiness inputs with explicit applicability, not passive optional files. The current weakness is not that every artifact must always be full; it is that the system does not force a visible distinction between not needed, not yet investigated, and missing but important.

### PROP-087 - Agent Personality Model For Decision Mediation

The owner defines personality as project interaction style: how an agent or mediator addresses the decision owner. The first implementation uses three independent 0-5 scales. technical_verbosity=0 avoids engine terms in owner-facing language while 5 reports technical operations in detail. formality=0 is very informal while 5 is detached and highly formal. assertiveness=0 preserves the current standard while 5 is highly persistent about unresolved gaps, evidence, order, and follow-up. The owner chose project-level defaults shared by all agents, no persisted presets, and CLI/MCP access under project interaction-style.

## Scope

### PROP-001 - — CLI Foundation

#### Goals

- Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.

#### Non-Goals

- No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.

#### Suggested Scope

Not recorded.

### PROP-002 - Proposal Exploration And Readiness Workflow

#### Goals

- Reframing di PROP-002 da semplice fase `explore` a workflow di proposal
  exploration and readiness.
- Mantenere gli artifact di exploration come memoria durable della proposta:
  `exploration.md`, `findings.md`, `alternatives.md`, `open-questions.md`,
  `risks.md`, `assumptions.md`, `suggested-scope.md`.
- Introdurre un modello di readiness profile-based e versioned.
- Definire un profilo iniziale `default-readiness-v0.1` con score 0-100,
  criteri, pesi, soglie, gate e override policy.
- Separare lifecycle state, computed readiness, confidence ed effective
  governance status.
- Introdurre criteri con pesi espliciti, inclusa enfasi su `alternatives
  quality`.
- Introdurre minimum gates per impedire che un punteggio alto compensi lacune
  essenziali nelle proposal importanti.
- Introdurre artifact quality states:
  `missing`, `placeholder`, `thin`, `meaningful`, `needs_owner_input`, `ready`.
- Usare artifact quality gates per limitare il punteggio massimo dei criteri
  collegati ad artifact deboli o generici.
- Richiedere evidence strutturata e note leggibili per i punteggi criterio.
- Introdurre confidence qualitativa basata su qualita delle evidenze, non su
  qualita retorica del testo.
- Rendere `p2p next` readiness-aware, con gap concreti, failed gates e azioni ad
  alto impatto.
- Aggiornare skill agentiche e MCP workflow per rendere gli agenti
  metodologicamente piu esigenti.
- Definire owner override come evento governance auditabile, non come modifica
  del computed score.
- Applicare readiness a nuove proposal e draft aperte, preservando le proposal
  gia accettate come legacy storiche.

#### Non-Goals

- Non sostituire le decisioni governance dell'owner con uno score automatico.
- Non trattare `computed_score: 100` come acceptance automatica.
- Non modificare `computed_score` quando l'owner usa un override.
- Non rendere il registry readiness fonte primaria al posto di artifact,
  profile, assessment e audit record.
- Non richiedere a ogni proposal piccola lo stesso livello di cerimonia delle
  proposal architectural o governance-critical.
- Non riscrivere, invalidare o bloccare retroattivamente proposal gia accettate.
- Non introdurre una web app.
- Non introdurre adapter AI diretti come requisito per la readiness.
- Non cambiare il modello di distribuzione/package del progetto.

#### Suggested Scope

# Suggested Scope - PROP-002

## Included

- Reframe PROP-002 from a narrow `explore` command proposal into a proposal
  exploration and readiness workflow.
- Keep the existing exploration artifacts as durable proposal memory:
  - `exploration.md`
  - `findings.md`
  - `alternatives.md`
  - `open-questions.md`
  - `risks.md`
  - `assumptions.md`
  - `suggested-scope.md`
- Keep authored proposal artifacts human-readable, while adding
  machine-readable readiness metadata, snapshots, registries, or exports.
- Define readiness as profile-based and versioned.
- Include a default readiness profile:

```yaml
readiness_profile:
  id: default-readiness-v0.1
  version: 0.1
  criteria:
    problem_clarity: 10
    goal_clarity: 10
    scope_boundaries: 10
    alternatives_quality: 15
    tradeoff_analysis: 10
    risk_coverage: 10
    assumptions_clarity: 10
    owner_questions_resolution: 10
    acceptance_criteria_quality: 10
    impact_overlap_analysis: 5
  thresholds:
    weak: 0
    partial: 70
    strong: 85
    decision_ready: 95
  gates: {}
  override_policy: {}
```

- Record `profile_id`, `profile_version`, and `computed_at` with every
  readiness assessment.
- Keep readiness separate from lifecycle state:
  - lifecycle state says where the proposal is procedurally;
  - readiness says how mature the proposal analysis is.
- Represent readiness with computed analytical fields and effective governance
  fields.
- Define tier classification and classify PROP-002 as governance-critical.
- Define minimum gates by tier so essential criteria cannot be compensated away
  by secondary strengths.
- Define artifact quality states and scoring caps:
  - missing: max 0%.
  - placeholder: max 0%.
  - thin: max 50%.
  - meaningful: max 75%.
  - needs_owner_input: max 75% and blocks automatic `ready_for_decision`.
  - ready: max 100%.
- Require criterion-level evidence for readiness scoring.
- Define threshold-driven agent behavior at 70, 85, and 95.
- Define confidence as evidence quality, not writing quality.
- Define governance gates as configurable:
  - warn
  - block_ready_for_decision
  - block_acceptance
  - allow_override
  - require_reason
- Define owner override as an audited governance event, not a score edit.
- Make `override_reason` mandatory when accepting below target readiness.
- Use acceptance-time override as the primary UX:

```bash
p2p proposal accept PROP-XXX --override-readiness --reason "..."
```

- Preserve accepted legacy proposals without rewriting history.
- Apply readiness to new proposals and open drafts.
- Include readiness in registries as a snapshot/cache, not as source of truth.
- Make `p2p next` report concrete proposal refinement gaps, failed gates, and
  highest-impact actions.
- Teach agent skills and MCP-facing workflows to interrogate proposals
  persistently and to say when a proposal is not methodologically ready.
- Expose MCP readiness reads to agents while making override/acceptance writes
  governance-gated and non-autonomous.
- Use a hybrid assessment model:
  - agent assesses criteria, evidence, confidence, and qualitative gaps;
  - CLI validates, caps, aggregates, gates, snapshots, and stores.

## Excluded

- Replacing owner governance decisions with an automatic score.
- Treating maturity 100 as automatic acceptance without owner action.
- Mutating `computed_score` to 100 when the owner uses an override.
- Allowing a high total score to hide failed minimum gates for important
  proposals.
- Allowing generic artifact text to earn full criterion points.
- Treating `needs_owner_input` as a weak/thin artifact rather than owner-gated
  progress.
- Forcing every small/routine proposal through the same heavy exploration depth
  as architectural or governance-critical proposals.
- Rewriting, invalidating, or retroactively blocking already accepted proposals.
- Requiring public package distribution changes.
- Building a web UI for proposal maturity.

## Possible MVP

1. Add versioned readiness profile support with `default-readiness-v0.1`.
2. Add proposal readiness assessment and reporting.
3. Compute or import criterion-level scores with evidence and notes.
4. Apply deterministic caps, gates, labels, thresholds, and aggregation.
5. Add confidence and confidence reasons.
6. Add tier suggestion/confirmation flow.
7. Add artifact quality states and caps, including `needs_owner_input`.
8. Add registry snapshots for readiness.
9. Update `p2p next` to use readiness gaps and highest-impact actions.
10. Update agent skill/MCP guidance for readiness-aware exploration.
11. Support owner acceptance below target only with explicit override reason and
    audit record.
12. Apply readiness to new proposals and open drafts; mark accepted legacy
    proposals without rewriting decisions.

## Deferred

- Strict blocking of all proposal acceptance below maturity threshold.
- Full historical backfill of all accepted proposals.
- Advanced numeric weighting UI.
- Cross-project maturity analytics.
- Optional future artifact states such as `blocked_by_dependency`, `stale`, and
  `superseded`.

### PROP-004 - Prompt-only Import Workflow

#### Goals

- Aggiungere import per clarify, synthesize, plan e tasks.
- Rendere il workflow prompt-only end-to-end testabile.

#### Non-Goals

- Non invocare provider AI direttamente.
- Non introdurre MCP.
- Non aggiungere web app o database.

#### Suggested Scope

# Suggested Scope - PROP-004

Not suggested yet.

### PROP-005 - Codex Skill Integration

#### Goals

- Creare una skill Codex che guidi l'uso della CLI P2P e degli artefatti .p2p.
- Stabilire regole per trasformare conversazioni in proposal, exploration, decisioni, piani e task versionati.

#### Non-Goals

- Non introdurre MCP in questa fase.
- Non invocare direttamente provider AI dalla CLI.
- Non sostituire la CLI come sorgente di verita.

#### Suggested Scope

# Suggested Scope - PROP-005

Not suggested yet.

### PROP-006 - Multi-Agent Integration Model

#### Goals

- Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.

#### Non-Goals

- Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.

#### Suggested Scope

# Suggested Scope - PROP-006

## Product Direction

Promote generated agent instructions into a governed **Agent Integration
Registry MVP**.

Project initialization should create the file structures for all supported
project-local agent integrations by default, unless the owner explicitly asks to
include only a subset.

`generic` is always present and cannot be removed. Specific agent integrations
can be added, updated, or removed later.

## Architectural Model

P2P has three separate layers:

```text
Generated agent instructions
  -> explain the P2P method, workflow, guardrails, and operating channel

CLI
  -> exposes textual P2P commands for humans, scripts, CI, and agents with shell

MCP
  -> exposes structured P2P tools for MCP-compatible agents
```

MCP does not teach agents the CLI. MCP gives compatible agents a structured way
to use P2P Engine capabilities without relying on textual command syntax.

CLI and MCP must both sit above the same P2P core behavior:

```text
P2P Core
   ^        ^
 CLI      MCP
```

## Baseline And Default Install Behavior

`generic` is the common baseline profile and is always generated.

Default project initialization installs all supported project-local adapters:

```bash
p2p init "Project Name"
```

Expected effect:

```yaml
baseline_profile: generic
integrations:
  generic:
    status: installed
  codex:
    status: installed
  claude:
    status: installed
  cursor:
    status: installed
  copilot:
    status: installed
  gemini:
    status: installed
  opencode:
    status: installed
```

The owner can choose a narrower install set:

```bash
p2p init "Project Name" --agent codex
p2p init "Project Name" --agent codex --agent claude
```

Even in a narrowed install, `generic` is still created.

Later lifecycle:

```bash
p2p agent install cursor
p2p agent install all
p2p agent update all
p2p agent uninstall cursor
```

There is no project-level preferred/default/active agent. P2P should not care
which collaborator uses which agent.

## Minimal Generic Content

The generic baseline is the source content from which all agent-specific files
are derived.

Minimum generic content:

```text
1. P2P Engine is the project governance source of truth.
2. Use P2P CLI or MCP tools for P2P writes.
3. Do not edit `.p2p/` internals directly.
4. If no CLI command or MCP write tool exists, stop and report the missing
   primitive.
5. The owner controls proposal decisions, choice decisions, managed merges,
   finalize, cleanup, and governance policy.
6. Before recommending proposal acceptance, inspect readiness and report gaps.
7. Prefer compact context before broad reads.
8. For managed P2P sync/branch/publish/merge flows, use P2P commands or
   explicit permission-gated MCP tools, not raw Git escape hatches.
9. If MCP is configured, use structured MCP tools for P2P operations.
10. If MCP is unavailable but shell access exists, use the `p2p` CLI.
11. If neither MCP nor CLI is available, ask the user to run the required P2P
    command.
```

Generated agent files may rephrase this content for their host tool, but they
must not weaken these rules.

## Method Behavior: Readiness-Driven Refinement

PROP-006 must not only decide which files are generated for each agent. It must
also define the common method behavior those files carry.

The distinction is:

```text
agent adapter/profile
  -> where instructions are written, which file format is used, whether CLI or
     MCP is available, and what host-tool conventions apply

agent policy / method behavior
  -> how every agent should behave when working with weak proposals, readiness
     gaps, owner questions, alternatives, and governance boundaries

readiness workflow
  -> concrete CLI/MCP-visible actions that transform a diagnostic score into
     refinement work
```

The "incalzante" behavior is a P2P method requirement, not a Codex-specific
personality trait. Every generated integration must preserve it.

When a proposal is weak, low-confidence, below target, or has failed readiness
gates, generated instructions must tell the agent not to stop at summarizing
gaps. For each failed gate or material gap, the agent should:

1. explain why the gate failed in proposal-specific terms;
2. propose one to three concrete alternatives;
3. recommend one option when evidence supports a recommendation;
4. identify the owner decision required;
5. draft the exact proposal, scope, risk, acceptance, or question update that
   would close the gap;
6. ask for confirmation only where owner authority is required;
7. re-check or request readiness re-check after the refinement is applied.

This should turn a diagnostic such as:

```yaml
failed_gates:
  - owner_questions_resolution
missing:
  - acceptance_criteria_quality
  - impact_overlap_analysis
```

into operational refinement actions such as:

```text
1. Resolve owner question
   - clarify the decision to make
   - offer alternatives
   - recommend one
   - ask for owner confirmation

2. Improve acceptance criteria
   - propose exact criteria
   - connect each criterion to expected behavior

3. Add impact and overlap analysis
   - compare with related policies, MCP tools, CLI flows, and existing files
   - identify what changes and what stays separate
```

The generated instruction files should therefore include a "readiness gap
handling" block in the generic baseline and adapt it to each tool. The same
behavior should also become visible through P2P Engine commands and MCP tools
over time, so the core makes this workflow hard to ignore.

## Included In MVP

### Registry

Add:

```text
.p2p/agent-integrations.yml
```

The registry records:

- schema version;
- baseline profile;
- available adapter definitions;
- installed integrations;
- generated files;
- template version;
- file hash;
- ownership status;
- shared-file flag;
- drift status;
- last installed or updated timestamp.

It must not record `active_agent`, `default_agent`, or `preferred_agent`.

MVP schema:

```yaml
schema_version: 1
baseline_profile: generic
generated_at: "2026-06-05T00:00:00Z"
adapters:
  generic:
    status: installed
    maturity: stable
    template_version: agent-template-v1
    files:
      - path: AGENTS.md
        shared: true
        owner: generic
        managed: true
        template_id: generic-agents-md-v1
        sha256: "..."
        drift: clean
  codex:
    status: installed
    maturity: stable
    template_version: agent-template-v1
    capabilities:
      mcp: supported
      shell: supported
      project_instructions: true
    files:
      - path: .agents/skills/p2p-project/SKILL.md
        shared: false
        owner: codex
        managed: true
        template_id: codex-p2p-skill-v1
        sha256: "..."
        drift: clean
```

Hashing is SHA-256 over exact file bytes. Do not normalize line endings,
whitespace, or Markdown formatting before hashing.

Templates live in package data for the MVP:

```text
src/p2p_engine/templates/agents/<adapter>/<file-template>
```

Project-local template overrides are deferred.

Generated Markdown files should include a short managed header where practical:

```markdown
<!--
Managed by P2P Engine.
Adapter: codex
Template: codex-p2p-skill-v1
Do not edit generated sections unless you accept drift.
-->
```

The registry is still the source of truth. The header is a human hint.

### CLI Commands

Add:

```bash
p2p agent list
p2p agent show <agent>
p2p agent install <agent|all>
p2p agent update <agent|all>
p2p agent doctor <agent|all>
p2p agent uninstall <agent>
```

Command semantics:

- `list`: show supported adapters and installed state.
- `show`: explain adapter capabilities, files, hashes, and drift.
- `install`: generate files, record registry manifest, and ensure `generic`
  baseline.
- `install all`: install all supported project-local adapters whose file targets
  do not conflict.
- `update`: refresh generated files only when safe.
- `doctor`: check registry health, missing files, hashes, drift, and baseline
  consistency.
- `uninstall`: remove only the target adapter's safe, managed, unchanged,
  non-shared files.

Excluded commands:

```text
p2p agent use
p2p agent switch
p2p agent current
p2p agent install --no-use
```

These are unnecessary because there is no active/default agent.

### Adapter File Matrix

#### generic

Files:

```text
AGENTS.md
.p2p/agent-policy.yml
```

Purpose:

- portable baseline for humans and generic agents;
- source content for generated agent-specific files;
- structured P2P agent policy.

Removal:

- cannot be uninstalled;
- not removed by uninstalling other adapters.

#### codex

Files:

```text
AGENTS.md                         shared baseline
.agents/skills/p2p-project/SKILL.md
```

Optional compatibility/migration:

```text
.codex/skills/p2p-project/SKILL.md
```

Notes:

- Codex officially reads `AGENTS.md`.
- Codex repo-scoped skills are discovered from `.agents/skills`.
- `.agents/skills` may also be visible to other tools such as OpenCode, so the
  skill content must be agent-neutral or the adapter must avoid installing it
  when it would be interpreted incorrectly.
- The existing P2P implementation currently generates `.codex/skills/...`;
  migration should preserve existing projects while moving new generation toward
  the official/common skill location if verified safe.

#### claude

Files:

```text
AGENTS.md     shared baseline
CLAUDE.md
```

Optional future:

```text
.claude/CLAUDE.md
.claude/skills/p2p-project/SKILL.md
```

Notes:

- Claude Code project memory supports `./CLAUDE.md` or `./.claude/CLAUDE.md`.
- MVP should generate root `CLAUDE.md` as the simplest shared project memory.
- Claude-specific skills/slash-command files are deferred unless the exact
  current format is needed.

#### cursor

Files:

```text
AGENTS.md
.cursor/rules/p2p.mdc
```

Notes:

- Cursor supports project rules in `.cursor/rules`.
- Cursor also supports `AGENTS.md` as a simpler Markdown alternative.
- `.cursorrules` is legacy and must not be generated.

#### copilot

Files:

```text
AGENTS.md
.github/copilot-instructions.md
```

Notes:

- GitHub Copilot uses `.github/copilot-instructions.md` for repository custom
  instructions.
- The Copilot file should contain the minimal generic P2P rules, not just a
  pointer, because Copilot may not follow arbitrary import/link semantics.

#### gemini

Files:

```text
AGENTS.md
GEMINI.md
```

Notes:

- Gemini CLI uses `GEMINI.md` context files.
- `GEMINI.md` should contain the minimal generic P2P rules adapted for Gemini.

#### opencode

Files:

```text
AGENTS.md
```

Optional future:

```text
opencode.json
.opencode/agents/p2p.md
.opencode/skills/p2p-project/SKILL.md
```

Notes:

- OpenCode supports `AGENTS.md`.
- `opencode.json` should not be generated in the MVP unless P2P needs to
  configure instruction paths or permissions.
- OpenCode may also load `.agents/skills`; therefore `.agents/skills` must not
  contain Codex-only behavior.

### Known File Sharing And Conflicts

Shared files:

```text
AGENTS.md
.p2p/agent-policy.yml
```

These are shared baseline files and are not conflicts.

No blocking adapter file conflicts are currently expected for the MVP matrix.

Potential conflict areas:

- `.agents/skills`: likely shared by more than one agent ecosystem. Do not put
  Codex-only content there.
- `opencode.json`: may already exist in a project for unrelated OpenCode
  settings. Do not generate by default in MVP.
- `.github/copilot-instructions.md`: may already exist in public repositories.
  Treat pre-existing unmanaged files as drift/unmanaged and avoid overwriting
  without explicit force.
- `.cursor/rules`: directory is shared with user-created Cursor rules. Generate
  only a dedicated `p2p.mdc` file.

### Safety Rules

- `AGENTS.md` is the shared baseline file.
- Uninstalling a specific agent must not remove `AGENTS.md` or
  `.p2p/agent-policy.yml`.
- `update` must detect manual drift by comparing stored hash and current hash.
- `update` may overwrite unchanged generated files.
- `update` must require `--force` or explicit user confirmation for drifted
  managed files.
- `uninstall` must remove only the target adapter's managed files whose current
  hash matches the registry and that are not shared baseline files.
- manually modified files should be marked `drifted`, not silently replaced.
- `install all` must fail or warn when two adapters would manage the same
  non-shared path.

### Doctor And Migration

`p2p agent doctor <agent|all>` checks:

- registry exists and validates;
- installed files exist;
- hashes match;
- shared files are still referenced;
- `generic` baseline exists;
- adapter documentation hints are available;
- no adapter claims ownership of a non-shared file owned by another adapter;
- no uninstall would remove a shared baseline file;
- generated instruction files include the generic method behavior block.

Existing projects migrate conservatively:

- if an existing file matches a known generated template hash, mark it
  `managed`;
- if an existing file exists but does not match, mark it `unmanaged` or
  `drifted`;
- do not overwrite unmanaged or drifted files during migration;
- preserve `.codex/skills/...` as compatibility if present;
- always ensure the `generic` baseline exists or report the missing baseline
  through `doctor`.

### MCP

Add MCP tools in the same implementation scope as the CLI lifecycle, backed by
the same core behavior.

Read-only tools:

```text
p2p_agent_list
p2p_agent_show
```

Write-safe tools:

```text
p2p_agent_install
p2p_agent_update
p2p_agent_uninstall
```

These tools are not governance decisions and do not require owner-decision
permissions, but they must preserve the same drift, shared-file, conflict, and
safe uninstall checks as the CLI.

### Readiness Refinement Surface

PROP-006 should integrate with the readiness model by ensuring generated agent
instructions point agents toward concrete refinement actions.

The implementation can start with instruction text only, but the product model
should leave room for CLI and MCP surfaces such as:

```bash
p2p proposal readiness next PROP-XXX
p2p proposal readiness refine PROP-XXX
p2p proposal readiness questions PROP-XXX
```

Equivalent MCP concepts could be exposed later as:

```text
p2p_proposal_readiness_next
p2p_proposal_readiness_refine
p2p_proposal_readiness_questions
```

These commands/tools are not required to solve the file-generation registry
MVP, but the generated policy must be written so agents naturally perform this
workflow even before dedicated commands exist.

## Excluded From MVP

- Project-level preferred/default/active agent state.
- `p2p agent use`, `switch`, `current`, and `install --no-use`.
- `.cursorrules` generation.
- Default `opencode.json` generation unless a concrete permission/instruction
  need is introduced.
- Destructive overwrite of pre-existing unmanaged agent files.
- External adapter packages from arbitrary URLs or Git repositories.
- Destructive uninstall of modified files.
- Automatic editing of user/global agent configuration outside the project
  without explicit consent.
- Direct AI provider invocation.
- Hosted web UI integration.
- Full support for every existing AI coding assistant.
- MCP client auto-registration in user home directories, unless handled by a
  separate consent-gated setup proposal.
- Full implementation of dedicated readiness refinement commands, unless it is
  split into or covered by a separate readiness-focused proposal.

## Future Work

- External adapter package format.
- Team-shared adapter catalog.
- Adapter compatibility checks against installed agent CLI versions.
- Per-agent MCP setup validation.
- Adapter-specific prompt libraries.
- Registry migration commands.
- OpenCode permission templates in `opencode.json`.
- Claude skill/slash-command adapter once the exact target format is stabilized.
- Dedicated readiness refinement commands and MCP tools that convert failed
  gates into ranked owner questions, alternatives, candidate edits, and next
  actions.

### PROP-009 - Governance CLI Commands

#### Goals

- Implementare p2p governance init/status.
- Implementare p2p swot prompt per alternative contrapposte.
- Implementare p2p vote record/status.
- Implementare p2p precedent record.

#### Non-Goals

- Implementare enforcement reale dei permessi applicativi.
- Integrare branch protection, CODEOWNERS o required approvals.
- Chiudere automaticamente votazioni o decisioni complesse.

#### Suggested Scope

# Suggested Scope - PROP-009

Not suggested yet.

### PROP-010 - P2P Project State Model

#### Goals

- Define a P2P-native project state generated from accepted proposals.
- Create a dedicated `.p2p/project/` area for rationalized project artifacts.
- Specify how accepted proposals update project state.
- Keep OpenSpec and Spec Kit as downstream exporters, not the source of truth.

#### Non-Goals

- Implement a full OpenSpec or Spec Kit exporter in this proposal.
- Replace proposal, decision, plan, or task artifacts.

#### Suggested Scope

# Suggested Scope - PROP-010

## Include

- Define `.p2p/project/` as the home for rationalized generated project state.
- Define minimal project files:
  - `overview.md`
  - `problem.md`
  - `scope.md`
  - `project-swot.md`
  - `features/<feature-id>/feature.md`
  - `features/<feature-id>/tasks.yml`
  - `features/<feature-id>/actions.yml`
  - `decisions-map.yml`
  - `conflicts.yml`
- Define explicit refresh command:
  - `p2p project refresh`
- Define later automatic refresh behavior after accepted decisions.
- Define provenance from output sections back to accepted proposal IDs.

## Exclude

- Full OpenSpec exporter.
- Full Spec Kit exporter.
- AI-based automatic rewriting.
- Web UI for spec review.
- Complex schema validation.

## Suggested MVP Commands

```bash
p2p project refresh
p2p project status
p2p project show cli
```

## Suggested Later Commands

```bash
p2p project prompt PROP-010
p2p project import PROP-010 project-output.md
p2p export PROP-010 --target openspec
p2p export PROP-010 --target speckit
```

### PROP-011 - Project Refresh MVP

#### Goals

- Implement p2p project refresh to generate the first .p2p/project artifacts.
- Implement p2p project status to inspect generated project state.
- Implement p2p project show to read generated project sections.

#### Non-Goals

- Implement OpenSpec or Spec Kit export.
- Implement automatic refresh after decision record.

#### Suggested Scope

# Suggested Scope - PROP-011

Not suggested yet.

### PROP-012 - Impact Map and Conflict Memory

#### Goals

- Define proposal-level impact-map artifacts.
- Define conflict memory in .p2p/project/conflicts.yml.
- Add prompt-only analysis for impact, overlap, dependencies, and conflicts.
- Add CLI commands to record and inspect conflicts.

#### Non-Goals

- Automatically reject proposals without human decision.
- Implement full AI agent invocation.

#### Suggested Scope

# Suggested Scope - PROP-012

## Include

- Add `p2p impact prompt PROP-XXX`.
- Add `p2p impact import PROP-XXX <file-or-dir>`.
- Add proposal artifacts:
  - `impact-map.yml`
  - `related-proposals.yml`
  - `conflict-analysis.yml`
- Add `p2p conflict record`.
- Add `p2p conflict status`.
- Store persistent conflicts in `.p2p/project/conflicts.yml`.

## Exclude

- Automatic AI invocation.
- Automatic proposal rejection.
- Complex graph visualization.
- Merge conflict resolution.

## Suggested Artifact Shape

```yaml
impact:
  proposal: PROP-012
  features:
    - project-refresh-mvp
  commands:
    - p2p project refresh
  files:
    - .p2p/project/conflicts.yml
  dependencies:
    - PROP-010
    - PROP-011
  risks:
    - conflict detection may be advisory only
```

### PROP-013 - Managed Git Adapter and Change Set Model

#### Goals

- Define Change Set as the operational unit after proposal decision.
- Define Git as an internal adapter for persistence, audit, collaboration, and synchronization.
- Hide branch, commit, merge, and tag details from the default user experience.
- Reduce discretion in branch decisions through configurable Git policy.
- Preserve proposal and decision history in .p2p artifacts even when Git branches are removed.

#### Non-Goals

- Implement full Git branch automation in this proposal.
- Require users to understand or manually manage Git branches.
- Let AI agents bypass P2P CLI by manipulating Git directly.

#### Suggested Scope

# Suggested Scope - PROP-013

## Include

- Define `.p2p/changes/`.
- Define change-set metadata.
- Define change-set creation policy.
- Define Git as an internal adapter.
- Define public P2P UX without branch/commit/merge concepts.
- Define managed `git_policy.yml`.
- Define verbose/debug visibility for internal Git operations.
- Define branch/commit/tag policy criteria.
- Define first CLI commands for a later implementation:
  - `p2p change create --from PROP-XXX`
  - `p2p change status CHANGE-XXX`
  - `p2p change policy CHANGE-XXX`
  - `p2p status --verbose`
  - `p2p doctor`

## Exclude

- Actual Git branch/commit/merge automation in the first proposal.
- Pull request integration.
- GitHub/GitLab-specific automation.
- Automatic merge.

## Change Set Policy

```yaml
change_set_policy:
  creation:
    allowed_from:
      - accepted_proposal
      - accepted_decision
    disallowed_from:
      - draft_proposal
      - exploring_proposal
      - rejected_proposal

  references:
    allow_draft_references: true
    draft_references_are_binding: false

  domains:
    allow_non_software: true
    allowed_domains:
      - software
      - documentation
      - marketing
      - commercial
      - operations
      - governance
      - research
      - mixed

  git:
    mvp_operation_level: metadata_only
    branch_creation_in_mvp: false
    future_branch_creation_requires:
      - operation_level_managed_branches
      - clean_doctor_status
      - implementation_ready_change
      - accepted_decision
      - execution_plan
      - tasks
      - recovery_strategy
      - explicit_user_command

  project_mapping:
    primary_sources:
      - proposals
      - choices
      - decisions
      - changes
    derived_views:
      - project_map
      - project_features
      - roadmap

  change_md_minimum_fields:
    - change_id
    - title
    - status
    - created_at
    - created_by
    - summary
    - source
    - rationale
    - scope
    - execution_domains
    - deliverables
    - acceptance_criteria
    - dependencies
    - risks
    - implementation_targets
    - related_choices
    - plan_ref
    - tasks_ref

  lifecycle:
    statuses:
      - proposed
      - planned
      - implementation_ready
      - in_progress
      - blocked
      - in_review
      - completed
      - cancelled
      - superseded
```

## Managed Git Policy

```yaml
git_policy:
  mode: managed
  operation_level: metadata_only
  expose_git_details: false
  proposal_branching:
    default: auto
    create_branch_when:
      - complex_proposal
      - divergent_alternative
      - formal_review_required
      - multi_actor_edit
  change_branching:
    default: auto
    create_branch_when:
      - source_code_changes
      - governance_changes
      - schema_or_template_changes
      - public_cli_behavior_changes
      - high_impact
      - mutually_exclusive_alternative
  commits:
    auto_commit: false
    message_style: conventional
    include_actor: true
  tags:
    create_for_decisions: false
    create_for_changes: false
  debug:
    show_internal_operations_with_verbose: true
```

## Rollout Stages

```text
Stage 1 - metadata only
  Define git_policy.yml and planned operations. No Git mutation.

Stage 2 - read-only diagnostics
  Add p2p doctor and verbose Git state inspection.

Stage 3 - explicit safe writes
  Add opt-in commits/tags.

Stage 4 - managed branches and merges
  Add branch/merge automation after recovery tooling exists.
```

## Initial Change Set Structure

```text
.p2p/changes/
  CHANGE-001-cli-foundation/
    change.md
    included-proposals.yml
    referenced-proposals.yml
    excluded-alternatives.yml
    included-decisions.yml
    impact-map.yml
    git-policy.yml
    execution-plan.md
    tasks.yml
```

## Change Set Lifecycle

```yaml
change_lifecycle:
  statuses:
    - proposed
    - planned
    - implementation_ready
    - in_progress
    - blocked
    - in_review
    - completed
    - cancelled
    - superseded

  transitions:
    proposed:
      allowed_next:
        - planned
        - cancelled
        - superseded
    planned:
      allowed_next:
        - implementation_ready
        - blocked
        - cancelled
        - superseded
    implementation_ready:
      allowed_next:
        - in_progress
        - blocked
        - cancelled
        - superseded
    in_progress:
      allowed_next:
        - in_review
        - blocked
        - cancelled
        - superseded
    blocked:
      allowed_next:
        - planned
        - implementation_ready
        - in_progress
        - cancelled
        - superseded
    in_review:
      allowed_next:
        - completed
        - in_progress
        - blocked
    completed:
      allowed_next: []
    cancelled:
      allowed_next: []
    superseded:
      allowed_next: []
```

### PROP-014 - Change Set Metadata MVP

#### Goals

- Implement p2p change create --from PROP-XXX for accepted proposals.
- Generate .p2p/changes/CHANGE-XXX directories with change.md and metadata files.
- Implement p2p change status and p2p change policy.
- Reject Change Set creation from non-accepted proposals.

#### Non-Goals

- Create Git commits, branches, merges, or tags.
- Implement OpenSpec or Spec Kit export.

#### Suggested Scope

# Suggested Scope - PROP-014

Not suggested yet.

### PROP-015 - Change Set Lifecycle and Task Tracking

#### Goals

- Implement Change Set lifecycle transitions from proposed to completed.
- Validate allowed status transitions.
- Show tasks and actions for a Change Set.
- Keep the MVP metadata-only without Git writes.

#### Non-Goals

- Implement automatic task execution.
- Create Git branches or commits.

#### Suggested Scope

# Suggested Scope - PROP-015

Not suggested yet.

### PROP-016 - Project Registries MVP

#### Goals

- Define registry files for proposals, decisions, changes, choices and relations.
- Keep registries as derived/index artifacts generated from source .p2p artifacts.
- Prepare CLI commands to refresh and inspect registries.
- Support future proposal intake, overlap analysis and exporter workflows.

#### Non-Goals

- Replace proposal, decision or change source artifacts.
- Implement a database or web backend.

#### Suggested Scope

# Suggested Scope - PROP-016

## Include

- Define `.p2p/registries/` as the generated registry layer for P2P Engine.
- Define typed registry files:
  - `proposals.yml`
  - `decisions.yml`
  - `changes.yml`
  - `choices.yml`
  - `relations.yml`
  - `artifacts.yml`
- Define the registry source-of-truth rule:
  - primary sources remain `.p2p/proposals/`, `.p2p/decisions/`, `.p2p/choices/`, `.p2p/changes/` and governance/project artifacts.
  - registries are derived, deterministic and regenerable.
- Add CLI commands:
  - `p2p registry refresh`
  - `p2p registry status`
  - `p2p registry show proposals`
  - `p2p registry show changes`
- Use registries as compact context for:
  - proposal intake
  - overlap analysis
  - conflict checks
  - project refresh
  - future exporters
  - AI-guided navigation

## Exclude

- Database or server-side registry storage.
- Full graph database semantics.
- Manual registry editing workflow.
- Automatic Git commits or branch operations.
- Replacing `.p2p/project/` with registries.
- Complete OpenSpec or Spec Kit export implementation.

## Proposed Structure

```text
.p2p/
  registries/
    proposals.yml
    decisions.yml
    changes.yml
    choices.yml
    relations.yml
    artifacts.yml
```

## Minimum Registry Shape

### `proposals.yml`

```yaml
generated: true
proposals:
  - id: PROP-016
    title: Project Registries MVP
    status: draft
    path: .p2p/proposals/PROP-016-project-registries-mvp
    related_changes: []
    related_decisions: []
```

### `changes.yml`

```yaml
generated: true
changes:
  - id: CHANGE-001
    title: Managed Git Adapter and Change Set Model
    status: planned
    path: .p2p/changes/CHANGE-001-managed-git-adapter-and-change-set-model
    included_proposals:
      - PROP-013
      - PROP-014
      - PROP-015
```

### `relations.yml`

```yaml
generated: true
relations:
  - source: PROP-016
    target: PROP-010
    type: extends
    rationale: Registries extend the project state model with global indexes.
```

## Completion Boundary

The MVP is complete when P2P can regenerate registries from existing `.p2p/` artifacts and show a readable status without treating registry files as primary sources.

### PROP-017 - Proposal Intake and Context Analysis MVP

#### Goals

- Analyze new ideas against proposal, change and relation registries.
- Suggest whether to create a new proposal, add a contribution, open a choice, or record a conflict.
- Provide prompt-only intake analysis before direct AI adapters or MCP.

#### Non-Goals

- Automatically decide whether a proposal is accepted.
- Replace owner governance.
- Implement semantic embeddings or a database in the MVP.

#### Suggested Scope

# Suggested Scope - PROP-017

## Include

- Define the intake workflow for raw ideas and observations.
- Create an intake prompt generator backed by:
  - `proposals.yml`
  - `changes.yml`
  - `relations.yml`
  - `decisions.yml`
  - `project/overview.md`
- Define imported intake artifacts:
  - `input.md`
  - `context.md`
  - `related-proposals.yml`
  - `recommendation.md`
  - `suggested-actions.yml`
- Add initial commands:
  - `p2p intake prompt "raw idea"`
  - `p2p intake import INTAKE-001 output/`
  - `p2p intake status`
- Define possible recommendations:
  - create new proposal
  - add contribution to existing proposal
  - open choice
  - record conflict
  - defer idea
  - reject as duplicate suggestion

## Exclude

- Direct AI provider calls.
- MCP tools.
- Embeddings or vector search.
- Automatic acceptance/rejection of proposals.
- Automatic Git operations.
- Web UI.

## MVP Completion Boundary

The MVP is complete when a user or agent can submit a raw idea, generate a context-rich intake prompt, import analysis output and inspect suggested next actions.

### PROP-018 - Choice Management CLI MVP

#### Goals

- Implement p2p choice create.
- Implement p2p choice list.
- Implement p2p choice decide.

#### Non-Goals

- Implement full voting or permission enforcement.
- Automatically apply intake suggested-actions.

#### Suggested Scope

# Suggested Scope - PROP-018

Not suggested yet.

### PROP-019 - Proposal Decision Shortcut Commands

#### Goals

- Add p2p proposal accept.
- Add p2p proposal reject.
- Add p2p proposal defer.

#### Non-Goals

- Replace the lower-level p2p decision record command.

#### Suggested Scope

# Suggested Scope - PROP-019

Not suggested yet.

### PROP-020 - Proposal Inspection CLI MVP

#### Goals

- Add p2p proposal list with optional status filtering.
- Add p2p proposal show PROP-ID for compact proposal inspection.
- Improve p2p registry show choices output readability.

#### Non-Goals

- Add semantic search or advanced proposal queries.

#### Suggested Scope

# Suggested Scope - PROP-020

Not suggested yet.

### PROP-021 - Agent Skill Real Commands Update

#### Goals

- Update the local Codex skill to use current P2P CLI commands.
- Document the recommended agent workflow before creating or changing proposals.
- Make governance and decision boundaries explicit for agents.

#### Non-Goals

- Create MCP tools or direct AI adapters.

#### Suggested Scope

# Suggested Scope - PROP-021

Not suggested yet.

### PROP-022 - Operational Brief Prompt Workflow

#### Goals

- Generate a project brief prompt from registries and project state.
- Import AI or human operational brief output into .p2p/project artifacts.
- Keep the skill as method guidance while the CLI remains the source of repeatable context and stored output.

#### Non-Goals

- Direct AI invocation from the CLI.
- Automatic owner decisions or automatic application of recommendations.

#### Suggested Scope

# Suggested Scope - PROP-022

Not suggested yet.

### PROP-023 - Next Action Recommender MVP

#### Goals

- Add top-level p2p next.
- Read imported next-actions.yml as advisory source.
- Compute conservative fallback actions from stale registries, incomplete Change Sets, pending intake, and open or draft choices.
- Add a concise operational section to p2p project status.

#### Non-Goals

- Do not modify project state from p2p next.
- Do not make owner decisions automatically.

#### Suggested Scope

# Suggested Scope - PROP-023

Not suggested yet.

### PROP-024 - Choice Blocking and Discovery MVP

#### Goals

- Phase 1: add advisory choice show/status/discover commands.
- Phase 2: add explicit choice block/unblock commands backed by links.yml.
- Expose project choices and proposal-local vote choices consistently.
- Allow p2p next to prioritize unresolved formal choice blockers.

#### Non-Goals

- Do not automatically decide choices.
- Do not automatically convert proposal-local votes into project choices.
- Do not invoke AI directly.

#### Suggested Scope

# Suggested Scope - PROP-024

Not suggested yet.

### PROP-025 - Controlled Intake Apply Workflow

#### Goals

- Add p2p intake apply plan INTAKE-XXX to create apply-plan.yml.
- Add p2p intake apply show INTAKE-XXX to inspect the plan.
- Add p2p intake apply run INTAKE-XXX --action APPLY-XXX for explicit application.
- Record applied actions in applied-actions.yml.
- Support add_contribution and open_choice with explicit options in the MVP.

#### Non-Goals

- Do not automatically apply all intake recommendations by default.
- Do not apply governance decisions such as accept, reject, or defer.
- Do not invoke AI directly.

#### Suggested Scope

# Suggested Scope - PROP-025

Not suggested yet.

### PROP-026 - P2P Software Spec Generator MVP

#### Goals

- Generate deterministic P2P-native software specs from Change Sets.
- Store specs under .p2p/outputs/software-spec/CHANGE-XXX/.
- Provide optional prompt/import workflow for AI-refined specs.
- Validate imported spec artifact shape before replacing generated artifacts.
- Preserve provenance from spec to Change Set, proposals, decisions and source files.

#### Non-Goals

- Do not implement OpenSpec or Spec Kit export in this MVP.
- Do not invoke AI directly.
- Do not invent missing requirements beyond source artifacts.

#### Suggested Scope

# Suggested Scope - PROP-026

Not suggested yet.

### PROP-027 - Software Spec Exporter MVP

#### Goals

- Provide a conservative exporter MVP that writes generic and OpenSpec-oriented export bundles from an existing P2P software spec.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-027

Not suggested yet.

### PROP-028 - Spec Kit Export Mapping MVP

#### Goals

- Define and implement a conservative Spec Kit export mapping from P2P-native software specs without invoking Spec Kit or creating branches.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-028

Not suggested yet.

### PROP-029 - Spec Export Validation MVP

#### Goals

- Provide a read-only CLI validator for generated software spec export bundles.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-029

Not suggested yet.

### PROP-030 - Managed Work and Multi-Branch Visibility Policy

#### Goals

- Define a level-based managed Git policy and implement the first safe step: read-only handoff planning through P2P Work manifests.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-030

Not suggested yet.

### PROP-031 - Multi-Branch Work Scan MVP

#### Goals

- Let P2P scan local P2P-managed Git branches for Work manifests without checkout or mutation.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-031

Not suggested yet.

### PROP-032 - Managed Work Branch Creation MVP

#### Goals

- Allow an owner or agent to explicitly create a P2P-managed branch for a planned Work item without committing, submitting, or merging.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-032

Not suggested yet.

### PROP-033 - Managed Work Submit MVP

#### Goals

- Allow a branched Work item to be submitted as a local managed commit without pushing or merging.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-033

Not suggested yet.

### PROP-034 - Managed Work Review MVP

#### Goals

- Allow a submitted Work item to enter a local review_requested state with a clear review commit and no remote side effects.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-034

Not suggested yet.

### PROP-035 - Managed Work Publish MVP

#### Goals

- Allow a review_requested Work item to push its managed branch to origin without opening a PR or merging.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-035

Not suggested yet.

### PROP-036 - Managed Work Accept MVP

#### Goals

- Allow an owner to accept a published Work item by merging its managed branch locally into the base branch.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-036

Not suggested yet.

### PROP-037 - Managed Work Status Summary MVP

#### Goals

- Provide a readable p2p work status summary that reports Work state, branch, target, remote/acceptance metadata, and the next suggested command.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-037

Not suggested yet.

### PROP-038 - Managed Work Merge Conflict Guidance MVP

#### Goals

- Make merge conflicts during p2p work accept explicit, inspectable, and recoverable.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-038

Not suggested yet.

### PROP-039 - Managed Work Finalize MVP

#### Goals

- Allow an owner to finalize an accepted Work item by pushing the base branch to the configured remote.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-039

Not suggested yet.

### PROP-040 - Managed Work Cleanup MVP

#### Goals

- Allow an owner to clean up finalized Work branches without changing accepted project content.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-040

Not suggested yet.

### PROP-041 - Remote Project Profile and Review Request Policy

#### Goals

- Record whether a P2P project is local-only or remote-backed.
- Keep p2p work publish separate from external review/PR creation.
- Introduce an advisory request-review step that can later be implemented by provider adapters.

#### Non-Goals

- Create GitHub Pull Requests automatically in this MVP.
- Require PRs for P2P accept/finalize/cleanup.

#### Suggested Scope

# Suggested Scope - PROP-041

Not suggested yet.

### PROP-042 - P2P Core CLI MCP Mediator Web Boundary

#### Goals

- Define P2P Core as the deterministic library for models, rules, validation, .p2p memory, proposal, choice, change, work, and registry operations.
- Define P2P CLI as the terminal interface for users, agents, scripts, and local automations.
- Define Skill, MCP, and Agent Interfaces as optional ways for agents to use P2P without owning project decisions.
- Define P2P Mediator as an optional intelligent assistant layer that helps contributors but uses Core/CLI/MCP as source of truth.
- Define P2P Web as a later product UI over the same source-of-truth operations.

#### Non-Goals

- Implement the MCP server in this proposal.
- Implement the mediator or web application in this proposal.
- Allow AI or mediator layers to decide governance outcomes by default.

#### Suggested Scope

# Suggested Scope - PROP-042

Not suggested yet.

### PROP-043 - Managed Work Retire MVP

#### Goals

- Add an explicit p2p work retire command for obsolete planned Work manifests.
- Record retired status, reason, and date in the Work manifest.
- Keep retirement metadata-only and avoid Git branch, commit, push, merge, or cleanup side effects.

#### Non-Goals

- Retire branched, submitted, published, accepted, finalized, or cleaned Work items in this MVP.
- Delete Work manifests or generated exports.

#### Suggested Scope

# Suggested Scope - PROP-043

Not suggested yet.

### PROP-044 - P2P MCP Server MVP

#### Goals

- Add a local stdio MCP server inside this repository.
- Expose a minimal read-only tool surface over P2PWorkspace.
- Keep governance and Work mutation commands out of the MCP MVP.
- Avoid web server, cloud deployment, auth, container, direct AI invocation, and mediator logic.

#### Non-Goals

- Implement MCP over HTTP.
- Expose proposal accept, choice decide, work accept, Git branch, commit, merge, cleanup, or provider actions.
- Implement P2P Mediator or Web.

#### Suggested Scope

# Suggested Scope - PROP-044

Not suggested yet.

### PROP-045 - Agent-Safe Project Bootstrap MVP

#### Goals

- Generate agent-safe project instructions during init and provide a repeatable command to add or refresh instructions for additional agent profiles later.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-045

Not suggested yet.

### PROP-046 - MCP Write-Safe Bootstrap Tools MVP

#### Goals

- Allow MCP clients to initialize P2P projects, refresh agent instructions, and refresh registries through explicit controlled tools.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-046

Not suggested yet.

### PROP-047 - Guided Init Wizard MVP

#### Goals

- Make p2p init usable without memorizing flags, while preserving non-interactive CLI usage.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-047

Not suggested yet.

### PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

#### Goals

- Allow MCP clients to create draft proposals and intake prompts through explicit write-safe tools.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-048

Not suggested yet.

### PROP-049 - MCP Level 4A Proposal Refinement Tools

#### Goals

- Allow MCP clients to update draft proposal content and generate/show project brief artifacts while keeping governance owner-controlled.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-049

Not suggested yet.

### PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

#### Goals

- Expose choice, conflict, and impact advisory workflows through MCP without adding decision-making mutations.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-050

Not suggested yet.

### PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

#### Goals

- Make draft proposals visible as actionable next steps and require agents to read existing artifacts before explaining them.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-051

Not suggested yet.

### PROP-052 - MCP Proposal Contribution Tool

#### Goals

- Allow MCP clients to add typed contributions to existing proposals without making governance decisions.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-052

Not suggested yet.

### PROP-053 - Core Validation Layer MVP

#### Goals

- Add a read-only core validation layer and CLI/MCP entry points that report project-state issues without mutating files.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-053

Not suggested yet.

### PROP-054 - Project Readiness and Maturity Assessment

#### Goals

- Define a readiness and maturity assessment model that separates deterministic completion from domain-specific quality assessment.
- Provide scores and gaps that are explainable, versioned and grounded in explicit criteria.
- Keep P2P Core deterministic while allowing optional AI-assisted maturity review through prompt/import workflows.

#### Non-Goals

- Do not let P2P automatically decide that a project is ready or block work solely from a maturity score.
- Do not produce a single opaque score without criteria, confidence and known gaps.

#### Suggested Scope

# Suggested Scope - PROP-054

## MVP Scope

- Add a deterministic assessment model for project readiness.
- Add CLI commands:
  - `p2p assess refresh`
  - `p2p assess show`
- Include factor-level output for:
  - validation status
  - registry freshness
  - draft/deferred/accepted proposal counts
  - open project choices
  - formal blockers
  - Change Set lifecycle status
  - Work item lifecycle status
  - operational brief availability and freshness
  - next-action availability
- Write a stable assessment artifact with score or status band, confidence, factors, gaps and suggested next actions.
- Add tests for deterministic scoring and command output.

## Stretch Scope

- Add project-type rubric file discovery.
- Generate rubric prompt artifacts.
- Add rubric import validation.
- Expose read-only assessment through MCP.

## Out Of Scope For First Change Set

- AI/provider invocation.
- Automatic governance decisions.
- Automatic blocking of proposals, choices, Change Sets or Work items.
- PR/MR creation or managed Git behavior.
- Hosted web assessment dashboard.
- Complex configurable weighting.

## Likely Execution Domains

- software
- governance metadata
- documentation

## Suggested Next Governance Step

Synthesize PROP-054 with Alternative B: deterministic readiness MVP first, rubric shape documented and deferred to a later Change Set unless the owner explicitly expands scope.

### PROP-055 - Agent Token Budget and Context Discipline

#### Goals

- Define a token-aware operating policy for agents.
- Prefer compact deterministic context views before detailed file reads.
- Make CLI and MCP expose bounded context packets for common agent tasks.
- Prevent agents from scanning unrelated .p2p, source, test, or Git history context when a smaller command output is enough.

#### Non-Goals

- Do not remove detailed proposal/change/registry commands.
- Do not introduce autonomous AI decision-making inside the core.
- Do not optimize runtime performance or rewrite the CLI in Rust as part of this proposal.

#### Suggested Scope

# Suggested Scope - PROP-055

Not suggested yet.

### PROP-056 - Project Definition Maturity Rubrics

#### Goals

- Separate structural readiness from project definition maturity.
- Introduce extensible domain rubrics stored as project state.
- Evaluate whether important project topics have been covered by proposals and decisions.
- Allow future domains to add their own criteria without changing the assessment model.
- Prepare init/wizard flow to select a project domain and generate an editable rubric checklist.

#### Non-Goals

- Do not evaluate implemented code quality in this proposal.
- Do not require AI semantic scoring for the MVP.
- Do not make maturity assessment decide project governance outcomes.

#### Suggested Scope

# Suggested Scope - PROP-056

Not suggested yet.

### PROP-057 - Guided Rubric Selection During Init

#### Goals

- Let the owner confirm rubric criteria during interactive initialization.
- Keep all domain criteria enabled by default.
- Allow disabling suggested criteria with simple yes/no prompts.
- Store the selected criteria deterministically in .p2p/project/rubrics.yml.

#### Non-Goals

- Do not support custom criteria in the wizard yet.
- Do not support editing criterion keywords or descriptions yet.
- Do not change non-interactive p2p init defaults.

#### Suggested Scope

# Suggested Scope - PROP-057

Not suggested yet.

### PROP-058 - Project README and Installation Guide

#### Goals

- Update README.md as the product entry point.
- Add a practical installation guide.
- Document current architecture, quick start, init wizard, context discipline, rubrics, assessment, and MCP local setup.
- Be explicit about current limits and future packaging direction.

#### Non-Goals

- Do not implement packaging changes in this proposal.
- Do not add a full website or generated docs site.
- Do not document unstable internals exhaustively.

#### Suggested Scope

# Suggested Scope - PROP-058

Not suggested yet.

### PROP-059 - P2PWorkspace Modular Refactoring Plan

#### Goals

- Approve a modular architecture direction for P2P Engine without changing runtime behavior.
- Preserve the public CLI, MCP, storage, consent, governance, and P2PWorkspace compatibility surface while extracting cohesive internal modules in later work.
- Define a layered architecture that separates domain rules, application workflows, persistence adapters, Git effects, MCP transport/schema handling, and CLI presentation.
- Create development guidance for humans and agents before non-trivial refactoring starts.
- Select consent/permissions as the preferred first future code extraction after the architecture contract is accepted and bound into local specs.

#### Non-Goals

- Do not rewrite the whole engine in one pass.
- Do not implement source refactoring as part of this proposal decision.
- Do not break existing CLI commands, MCP tool names, .p2p storage layouts, validation behavior, registry refresh behavior, consent semantics, or owner-controlled governance actions.
- Do not split cli.py mechanically before service/use-case boundaries are defined.
- Do not translate this proposal into source-level implementation tasks inside specs/ until the proposal is accepted and intentionally bound.

#### Suggested Scope

# Suggested Scope - PROP-059

Not suggested yet.

### PROP-061 - Focused README and Documentation Map

#### Goals

- Rewrite README.md as a concise repository entry point for P2P Engine.
- Keep mediator and web out of the main README scope except as out-of-repo future directions.
- Add documentation stubs for CLI guide, MCP reference, agent integration, and core API reference.
- Make README link to each detailed documentation file with a short explanation.

#### Non-Goals

- Do not fully document every CLI command in this change.
- Do not add Python docstrings in this change.
- Do not implement packaging changes.

#### Suggested Scope

# Suggested Scope - PROP-061

Not suggested yet.

### PROP-062 - README Product Landing Page Refinement

#### Goals

- Make README.md a concise product-style landing page for the engine.
- Explain why P2P Engine exists and who it serves.
- Add a 5-minute demo with commands and expected output.
- Keep install instructions short and link to docs/INSTALL.md.
- Clearly mark stable and work-in-progress docs.

#### Non-Goals

- Do not expand detailed CLI/API/MCP documentation in this change.
- Do not describe mediator or web as part of this repository.

#### Suggested Scope

# Suggested Scope - PROP-062

Not suggested yet.

### PROP-064 - Spec Kit Three-Prompt Export Model

#### Goals

- Define project.md as the canonical synthesized project definition derived from accepted P2P memory.
- Define a core project coverage checklist that every project.md must cover.
- Allow domain-specific section extensions for software, grant documents, board games, environmental impact assessment, one-day projects, and future verticals.
- Derive generic, OpenSpec, and Spec Kit outputs from project.md instead of mirroring downstream folder layouts.
- Preserve P2P source traceability so agents and humans can see which accepted artifacts support each major section.

#### Non-Goals

- Invoke downstream tools directly.
- Treat draft proposals as accepted truth.
- Generate downstream folder structures as the primary export UX.
- Replace P2P governance decisions with export-time synthesis.

#### Suggested Scope

# Suggested Scope - PROP-064

Not suggested yet.

### PROP-065 - MCP Agent-First Coverage Expansion

#### Goals

- Expose read-only MCP tools for Change Sets, Work, registries, project state, remote profile, and spec/export inspection.
- Expose write-safe deterministic MCP tools for Change Set creation, project refresh, spec refresh/export/validation, and Work planning.
- Expose prompt/advisory MCP tools for explore, digest, clarify, synthesize, plan, tasks, swot, and spec refinement prompts.

#### Non-Goals

- Expose owner-governance decisions such as proposal accept/reject/defer, choice decide/block/unblock, conflict record, vote record, or work branch/merge/finalize operations.
- Expose import/apply workflows that ingest external AI output without a separate trust and preview model.

#### Suggested Scope

# Suggested Scope - PROP-065

Not suggested yet.

### PROP-066 - Permission-Gated MCP Governance And Git Operations

#### Goals

- Preserve the future requirement so missing MCP operations are not forgotten.
- Define a concrete permission model for privileged MCP operations.
- Use project-declared roles as the MVP authorization model while acknowledging they are not strong authentication.
- Require consent receipts for owner-controlled MCP operations.
- Keep Git provider enforcement as the cloud-backed security boundary for protected branches and main updates.
- Support generic fallback identities when project init does not know real person names.
- Keep future API server/IAM integration possible without blocking the MVP.

#### Non-Goals

- Implement privileged MCP methods before this proposal is accepted.
- Treat local actor_id values as strong authentication.
- Require an external IAM server for the MVP.
- Allow agents to bypass owner governance decisions.
- Expose Git commit, push, merge, provider PR/MR creation, or finalization without accepted permission and consent rules.

#### Suggested Scope

# Suggested Scope - PROP-066

Not suggested yet.

### PROP-067 - Agent-First Setup Documentation Split

#### Goals

- Make public setup documentation primarily about using P2P for a new target project.
- Keep P2P Engine repository contribution setup exclusively in CONTRIBUTING.md, with README linking there but not showing potentially confusing examples.
- Make manual CLI usage clearly secondary: useful for inspection, debugging, recovery, and learning the model.

#### Non-Goals

- Change runtime behavior or installation code.
- Document unverified agent-specific desktop integrations as definitive commands.

#### Suggested Scope

# Suggested Scope - PROP-067

Not suggested yet.

### PROP-068 - Document Agent MCP Client Setup Commands

#### Goals

- Add concrete MCP client setup examples for verified terminal clients.
- Show Claude Desktop/local MCP JSON using the same target-project server command.
- Keep unverified desktop or IDE-specific integrations framed as generic MCP client configuration rather than definitive commands.

#### Non-Goals

- Document P2P Engine repository contributor MCP setup outside CONTRIBUTING.md.
- Claim support for unverified Codex desktop, Codex VSCode, or other IDE-specific MCP flows.

#### Suggested Scope

# Suggested Scope - PROP-068

Not suggested yet.

### PROP-069 - Clarify MCP Stdio Integration Model

#### Goals

- Document the MCP stdio integration model clearly.
- Clarify that each client may start its own P2P MCP process and that shared state is repository-backed.
- Refine verified setup examples for Claude Code, Claude Desktop, Codex CLI/config, Codex IDE extension, and VS Code Copilot MCP.

#### Non-Goals

- Implement Streamable HTTP MCP support now.
- Change MCP server runtime behavior.

#### Suggested Scope

# Suggested Scope - PROP-069

Not suggested yet.

### PROP-070 - Clarify README Agent Access Modes

#### Goals

- Make the README quick start explicit about CLI access versus MCP access.
- State that current MCP access is intentionally limited and does not expose privileged operations.
- Point readers to INSTALL and MCP docs for detailed client setup and tool boundaries.

#### Non-Goals

- Change MCP behavior or add privileged MCP tools now.

#### Suggested Scope

# Suggested Scope - PROP-070

Not suggested yet.

### PROP-071 - Custom Domain Definition Workflow

#### Goals

- Represent domain and rubric state explicitly for all projects.
- Treat predefined domains as optional initialization templates.
- Make custom/none initialization a first-class unresolved setup path rather than a special-case error path.
- Base maturity assessability on rubric availability and status, not hardcoded domain identity.

#### Non-Goals

- Implement a mediator or AI semantic review inside core.
- Hardcode every possible vertical in P2P Engine.

#### Suggested Scope

# Suggested Scope - PROP-071

Not suggested yet.

### PROP-072 - Concurrent Managed Work and Merge Decision Model

#### Goals

- Keep Git invisible for non-technical users and routine agent workflows.
- Define main as accepted project state rather than shared draft space.
- Support concurrent proposal branches from multiple people or agents.
- Support multiple candidate Work items for the same Change Set.
- Add explicit candidate selection before merge when competing Work items exist.
- Make local and cloud projects follow the same P2P lifecycle, with cloud adding remote publication and optional external review handoff only.
- Require explicit P2P decisions before merging proposal or Work branches into main.
- Record auditable metadata for proposal branch decisions, Work candidate decisions, merge conflicts, and finalization.
- Generate clear agent instructions for branch, publish, review, accept, merge, conflict, finalize, and cleanup behavior.

#### Non-Goals

- Replace Git as the underlying storage or transport mechanism.
- Bind the core model to GitHub-specific PR semantics.
- Allow agents to perform owner-sensitive merge, cleanup, or publishing operations without permission.
- Implement real-time collaboration, distributed locking, or server-side coordination outside Git.
- Decide the full MCP permission model covered by PROP-066.
- Require normal users to understand or run raw Git commands.
- Guarantee automatic semantic conflict resolution between competing proposals.

#### Suggested Scope

# Suggested Scope - PROP-072

Not suggested yet.

### PROP-073 - Ergonomic Remote Project Initialization

#### Goals

- Let users declare remote project intent during init with provider, remote name, and remote URL options.
- Guide users when the Git remote is missing, mismatched, or not reachable, without requiring raw Git knowledge.
- Keep local and cloud project semantics unified: cloud mode only adds remote profile validation and managed sync guidance.
- Preserve provider-neutral behavior and avoid creating external repositories in the MVP.
- Generate agent instructions and next-step hints that match the selected repository mode.

#### Non-Goals

- Automatically create GitHub/GitLab repositories or provider PR/MR resources.
- Replace Git provider authentication, SSH setup, branch protection, or IAM.
- Make local actor identities into strong authentication.

#### Suggested Scope

# Suggested Scope - PROP-073

Not suggested yet.

### PROP-074 - Agent Runtime Bootstrap Robustness

#### Goals

- Make P2P-managed repositories self-diagnosing for agents when the p2p runtime is missing.
- Provide clear fallback guidance for PATH, virtualenv, module execution, MCP tools, or installation.
- Prevent agents from bypassing governance while still making the next recovery step obvious.
- Support cloud agent environments where the repository is mounted but the Python package is not installed.

#### Non-Goals

- Allow agents to create or edit .p2p files manually when the CLI is missing.
- Bundle a hosted P2P service or require a global package manager.
- Grant cloud agents repository write permissions or provider credentials automatically.

#### Suggested Scope

# Suggested Scope - PROP-074

Not suggested yet.

### PROP-075 - MCP End-To-End Proposal Collaboration Workflow

#### Goals

- Make the normal proposal collaboration path coherent and closable through P2P primitives without raw Git.
- Clarify draft persistence and commit behavior after MCP proposal creation or update.
- Prevent accidental branch chaining by requiring or defaulting a safe base branch.
- Define a safe consent-request path for MCP that preserves owner approval.
- Allow MCP clients to correct remote profile metadata when policy allows it.

#### Non-Goals

- Let MCP grant owner consent without an owner-controlled approval path.
- Open provider PRs/MRs automatically.
- Bypass clean-worktree requirements by silently committing arbitrary unrelated files.

#### Suggested Scope

# Suggested Scope - PROP-075

Not suggested yet.

### PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

#### Goals

- Keep P2P Engine focused on local deterministic automation: CLI, filesystem .p2p state, Git audit, and local MCP.
- Define P2P Cloud as a separate product layer that owns web/API, auth, UI, database, workflow orchestration, and multi-tenant state.
- Define a containerized P2P runner model for cloud workflows that invokes the p2p CLI in isolated Git checkouts.
- Make cloud execution auditable through .p2p artifacts and Git history without turning the engine into a hosted API service.
- Clarify which future proposals should be rejected, accepted, or reformulated based on this boundary.

#### Non-Goals

- Implement P2P Cloud inside this repository as part of P2P Engine core.
- Add a public FastAPI/Django/NestJS API server to P2P Engine.
- Make P2P Engine responsible for users, organizations, billing, sessions, OAuth, cloud IAM, or multi-tenant authorization.
- Keep one long-running P2P server container per project as the default execution model.
- Create provider PR/MR automation in the engine core.

#### Suggested Scope

# Suggested Scope - PROP-076

Not suggested yet.

### PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

#### Goals

- Provide explicit MCP tools for owner-approved draft proposal accept, reject, and defer decisions while preserving the governance boundary through granted consent receipts.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-077

Not suggested yet.

### PROP-078 - Project-Local Wheel Installation and Upgrade Model

#### Goals

- Make P2P Engine installable and upgradeable inside each project's own virtual environment, starting with GitHub Release wheel artifacts and explicitly preserving a future migration path to a public package registry.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-078

Not suggested yet.

### PROP-079 - Managed Next Action Lifecycle

#### Goals

- Provide a managed hybrid next-action model that combines curated owner/agent actions with generated actions derived from project state, and expose lifecycle CLI commands so stale next actions can be closed without manual .p2p edits.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-079

Not suggested yet.

### PROP-080 - Automated GitHub Release Wheel Publishing

#### Goals

- Automate wheel and sdist publishing for GitHub Releases so maintainers can publish installable project-local packages by pushing a version tag.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-080

Not suggested yet.

### PROP-081 - MCP and Skill Support for Managed Next Actions

#### Goals

- Expose the managed next-action lifecycle consistently through CLI guidance, agent skill instructions, and MCP write-safe tools.

#### Non-Goals

Not recorded.

#### Suggested Scope

# Suggested Scope - PROP-081

Not suggested yet.

### PROP-082 - Readiness Assessment Refresh And Review Workflow

#### Goals

- Separate information completeness from agent behavioral guidance in the readiness model.
- Provide a governed assess/review path that can update evidence, criterion scores, confidence, missing items, gates, suggested next actions, unresolved owner questions, and overlap candidates after proposal artifacts change.
- Introduce a first-class deterministic clarification interview memory for low-readiness proposals: generated questions start with empty answers, answers are recorded as the interview progresses, and every question remains tied to the readiness gap it is meant to resolve.
- Make agent guidance operational and proactive by default: agents must challenge thin or incomplete artifacts, ask focused owner questions one at a time, reassess the question list after each answer, propose alternatives and tradeoffs, detect mergeable proposals, and avoid recommending acceptance when readiness is methodologically weak.
- Define production-ready CLI commands and data structures for question lifecycle, answer recording, deferral, muting, grouping, applying answers, and handling merge candidates.
- Allow the agent to use completed question-and-answer memory to refine the proposal through supported CLI tools.
- Preserve owner control: agent proactivity may recommend, question, assess, and prepare aggregation, but must not decide acceptance, rejection, deferral, aggregation closure, or override.
- Preserve backward compatibility for proposals that have no question/interview state yet.

#### Non-Goals

- Do not make agents autonomous governance decision makers.
- Do not overwrite computed readiness scores with owner override outcomes.
- Do not require every small proposal to receive heavyweight qualitative review or a full interview.
- Do not replace deterministic refresh. Refresh remains a conservative synchronization step, while assess/review is the evidence-aware path.
- Do not store interview state only in free-form chat memory or only as unstructured contributions.
- Do not break existing proposals, registries, readiness snapshots, or CLI inspection commands when question state is absent.

#### Suggested Scope

# Suggested Scope - PROP-082

## Product Direction

Readiness must evolve from a conservative diagnostic snapshot into a governed
review workflow.

The workflow should support these distinct operations:

```text
init
  -> bootstrap a conservative first assessment

refresh
  -> synchronize/read current readiness snapshot without pretending to perform
     qualitative reassessment

assess
  -> re-evaluate proposal artifacts and update computed readiness evidence

review
  -> record human or owner-reviewed assessment confirmation

resolve-gate
  -> explicitly record that a failed gate is resolved with evidence/reason

import
  -> validate and persist a structured assessment produced by an agent or
     external review process

override
  -> decision-time owner governance event that does not falsify computed_score
```

## Included In MVP

- CLI command design for readiness assessment and review.
- Criterion-level evidence persistence through public P2P commands.
- Confidence update through public P2P commands.
- Failed gate resolution with reason and actor.
- Assessment source tracking:
  - deterministic;
  - agent_assisted;
  - owner_reviewed.
- Validation for malformed readiness records.
- MCP tool parity over the same core behavior.

## Candidate Commands

```bash
p2p proposal readiness assess PROP-XXX
p2p proposal readiness review PROP-XXX --by owner --reason "..."
p2p proposal readiness resolve-gate PROP-XXX owner_questions_resolution --reason "..."
p2p proposal readiness import PROP-XXX assessment.yml
```

Exact names may change during implementation planning, but the behavior must be
available through public commands rather than manual `readiness.yml` edits.

## Excluded From MVP

- Automatic proposal acceptance.
- Replacing owner decision authority.
- Falsifying `computed_score` when owner override is used.
- Building a perfect AI scoring model.
- Treating readiness metadata as more authoritative than proposal artifacts.

### PROP-083 - Domain-Aware Visible Project Definition Export

#### Goals

- Generate a default human-readable project definition for every P2P project.
- Write the default visible output to outputs/latest/project.md as a single chaptered Markdown document.
- Preserve prior generated project definitions by moving or writing snapshots under outputs/review-001, outputs/review-002, and later review directories.
- Support different vertical domains through a generic project definition model instead of assuming software.
- Allow domain-specific or tool-specific exports, such as software-spec, OpenSpec, or Spec Kit, as nested profiles under outputs/latest/exports/<profile-or-vertical>/ when compatible.
- Preserve compatibility with existing .p2p/outputs and CLI/API behavior until migration or deprecation is explicitly verified.

#### Non-Goals

- Do not make software-spec, OpenSpec, or Spec Kit the default export for non-software domains.
- Do not delete existing .p2p outputs without implementation-time compatibility review.
- Do not make the root outputs/ location configurable in the MVP.
- Do not split the default human-facing project definition into many default files.

#### Suggested Scope

# Suggested Scope

## In scope

- Add a visible generated output tree at repository root: `outputs/`.
- Generate the default project definition at `outputs/latest/project.md`.
- Make the default export a single chaptered Markdown document for humans.
- Keep the default export domain-generic, without assuming software as the
  project vertical.
- Include stable chapters for purpose, domain context, problem framing, accepted
  proposals, decisions, requirements, scope, alternatives, tradeoffs, risks,
  assumptions, open questions, readiness notes, and delivery context.
- Preserve review history through `outputs/review-001`, `outputs/review-002`,
  and subsequent review snapshot directories.
- Support specialized export profiles under
  `outputs/latest/exports/<profile-or-vertical>/`.
- Place software-oriented exports such as software-spec, OpenSpec, or Spec Kit
  under profile folders rather than making them the default.
- Treat current `.p2p/outputs` behavior as a compatibility surface and verify
  existing producers and consumers before changing it.
- Define deterministic generation behavior so repeated exports have predictable
  paths and review numbering.

## Out of scope for the MVP

- Making the root output destination configurable.
- Replacing all existing `.p2p/outputs` behavior without compatibility analysis.
- Deleting legacy generated outputs before proving they are unused.
- Making software-specific output the default project export.
- Requiring every vertical to define a custom export profile before the default
  project document can be generated.
- Building a full template marketplace or plugin system for vertical exports.
- Treating generated `outputs/` files as the source of truth instead of P2P
  managed state.

## Scope boundaries

The proposal defines the product behavior and compatibility direction for
visible project-definition exports. It does not yet prescribe the exact command
name, renderer class layout, or internal service boundaries; those belong in the
implementation design after the proposal is accepted.

The proposal should require implementation to preserve existing CLI/MCP
contracts or introduce explicit deprecation behavior where compatibility cannot
be preserved.

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

#### Goals

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

#### Non-Goals

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

#### Suggested Scope

# Suggested Scope - PROP-085

## MVP Scope

- Define the vertical pack schema for pure data packs.
- Ship `base_project` as the required common foundation, including its default
  cross-domain structure.
- Implement a loader and validator for internal and project-local vertical packs.
- Add one complete demonstration vertical.
- Extend project readiness review through `p2p project readiness review`.
- Add CLI/MCP read/write surfaces for listing, showing, validating, proposing,
  and adding project-local vertical packs.
- Add project-level traceability between vertical sections/capisaldi and
  proposals.
- Update agent/project skills so the agent treats missing initialization,
  capisaldi, and initial project questions as priority context work.
- Reuse existing project rubrics and maturity/readiness artifacts.
- Preserve backward compatibility for projects without vertical packs.

## Required MVP Pack Fields

- `vertical.yml` with id, name, version, description, and base/extends.
- Project sections/capitoli/capisaldi.
- Minimal completeness/readiness rubrics.
- Initial blocking questions.
- Expected or suggested artifacts.

## `base_project` Default Structure

`base_project` is not a domain vertical. It is the required cross-domain
foundation that every project starts from and every vertical extends.

Required default sections:

- vision: why the project exists and what change it should create.
- objective/outcome: concrete results the project must achieve.
- owner and stakeholders: decision maker, contributors, affected parties.
- target/users/beneficiaries: who receives value or impact.
- scope and non-goals: boundaries and explicit exclusions.
- constraints: budget, time, compliance, resources, technology, context.
- assumptions: beliefs that must be true for the project to work.
- risks: failure modes and mitigations.
- decisions and open questions: unresolved owner choices.
- milestones and next actions: staged path from definition to execution.
- definition of done/readiness criteria: how the project becomes actionable.
- expected artifacts: documents, specs, prototypes, reports, plans, or outputs.
- maturity/readiness status: current completeness and next strengthening step.

## Custom Vertical Candidate Procedure

When no suitable vertical exists, the agent should:

1. start from `base_project`;
2. infer a candidate vertical id and name;
3. propose vertical-specific sections/capisaldi;
4. propose minimal readiness rubrics;
5. propose initial blocking questions;
6. propose expected artifacts;
7. explain what came from `base_project` and what is vertical-specific;
8. ask the owner to confirm or modify the candidate;
9. save it as a project-local custom vertical only after confirmation;
10. use it for `p2p project readiness review`.

## Proposed CLI Surface

The current system has project domains and rubrics, not pluggable vertical packs.
This proposal should add a dedicated project vertical surface.

Expected MVP commands:

- `p2p project vertical list`
- `p2p project vertical show <vertical-id>`
- `p2p project vertical validate <path-or-id>`
- `p2p project vertical propose "<project idea>"`
- `p2p project vertical add <path>`
- `p2p project readiness review`

The commands should prefer project-local custom verticals, then internal defaults,
then future registry sources once implemented.

## Proposal-To-Vertical Traceability

The project should not only know which vertical is active. It should also know
which parts of the vertical are currently covered by proposals.

Expected behavior:

- A proposal can declare or be assessed against one or more vertical
  sections/capisaldi.
- `p2p project readiness review` should summarize the active vertical skeleton.
- For each vertical section, the review should list relevant proposals,
  accepted decisions, draft proposals, missing coverage, risks, and unresolved
  questions.
- The review should identify vertical sections with no proposal coverage.
- The review should identify proposals that affect the project but are not
  mapped to any vertical section.
- The visible project output should be able to include a vertical coverage
  summary.

Suggested traceability fields:

```yaml
vertical_coverage:
  vertical_id: social_impact_program_design
  sections:
    - id: theory_of_change
      relevance: direct
      rationale: Defines how initiatives create measurable impact.
    - id: measurement_and_reporting
      relevance: direct
      rationale: Adds outcome metrics and reporting requirements.
```

Suggested project-level summary:

```yaml
vertical_summary:
  vertical_id: social_impact_program_design
  sections:
    - id: social_impact_vision
      status: covered
      proposals: [PROP-101]
    - id: theory_of_change
      status: partial
      proposals: [PROP-102]
      gaps: [missing_assumptions]
    - id: measurement_and_reporting
      status: missing
      proposals: []
```

## Example Custom Vertical Candidate: `packaging_or_physical_product_design`

Example project: "progettare la scatola perfetta".

Purpose:

- Guide the design of a box or packaging solution from concept to testable and
  manufacturable specification.

Candidate sections:

- contained product and use case;
- meaning of "perfect" for the project;
- user and unboxing experience;
- physical structure and dimensions;
- materials and sustainability;
- protection, transport, and storage;
- brand/visual communication;
- production process and suppliers;
- cost targets;
- prototype plan;
- resistance/usability tests;
- final packaging specification.

Candidate blocking questions:

- What must the box contain?
- Does "perfect" mean beautiful, resistant, cheap, sustainable, memorable, or a
  weighted combination?
- Is the main context shipping, retail shelf, gift, luxury, e-commerce, or reuse?
- Which cost, material, size, logistics, and production constraints are fixed?

Candidate artifacts:

- packaging brief;
- requirement matrix;
- material shortlist;
- dieline/structural sketch;
- prototype plan;
- test checklist;
- supplier/manufacturing brief.

## Example Custom Vertical Candidate: `social_impact_program_design`

Example project: "progettare attività volte a migliorare l'impatto sociale di
una banca".

Purpose:

- Guide a bank or financial institution in designing social impact initiatives
  that are measurable, governed, credible, and connected to stakeholder needs.

Candidate sections:

- social impact vision;
- theory of change;
- beneficiary communities;
- impact areas;
- financial inclusion;
- financial education;
- partnerships and territory;
- ESG/social impact alignment;
- governance and accountability;
- budget and sustainability;
- measurement and reporting;
- responsible communication;
- program roadmap.

Candidate blocking questions:

- Which community or population should benefit?
- Is the desired impact about financial inclusion, education, credit access,
  territory, environment, work, or another area?
- Should the bank fund external initiatives, change internal products/processes,
  or both?
- How will real impact be measured and how will social-washing be avoided?

Candidate artifacts:

- social impact strategy brief;
- stakeholder map;
- theory of change;
- initiative portfolio;
- outcome metric framework;
- partner brief;
- governance model;
- impact reporting plan.

## Optional MVP Pack Fields

- Examples.
- Profiles.
- Compatible modules.
- Rich output templates.

## Out Of Scope For First Slice

- Remote registry implementation.
- Executable plugin code for verticals.
- A large catalog of verticals.
- The full five-vertical MVP set.
- Publishing project-local custom verticals to a shared registry.
- Replacing project rubrics or project maturity with a parallel system.

## Follow-Up Scope

- Design the REST registry API for listing packs and fetching pack details.
- Add the five-vertical MVP set once the pack model is proven.
- Add richer profiles/modules/templates after the minimal pack schema is stable.

## Vertical Catalog Roadmap

The first implementation slice remains intentionally smaller than the later
catalog MVP. It proves the model with `base_project`, one complete demonstration
vertical, loader/validator behavior, project-local overrides, agent guidance, and
`p2p project readiness review`.

After that first slice, the recommended catalog MVP is:

- `base_project`
- `software_product`
- `ai_agent_or_automation`
- `startup_or_business`
- `research_report`
- `board_game_design`

The recommended V1 default catalog is:

- `base_project`
- `software_product`
- `ai_agent_or_automation`
- `startup_or_business`
- `research_report`
- `course_or_training_program`
- `marketing_or_launch_campaign`
- `physical_product`
- `event_or_community`
- `board_game_design`

Domains such as podcast, newsletter, book, video game, documentary, e-commerce,
grant proposal, nonprofit, hiring process, and open source community should move
to registry/project-local packs rather than the initial core catalog.

## Vertical Admission Criteria

A vertical should enter the default catalog only if it:

1. has a clear project structure;
2. produces concrete artifacts;
3. benefits from interview mode;
4. has verifiable maturity/readiness criteria;
5. is common enough to justify maintenance;
6. does not require risky regulated expertise as its core value;
7. reuses cross-domain sections or modules;
8. is maintainable by the project team;
9. demonstrates a distinct capability of the engine;
10. can include high-quality examples.

## Vertical Profiles And Modules

Profiles specialize a vertical without creating another vertical. Examples:

- `board_game_design`: `early_concept`, `playable_prototype`,
  `publisher_pitch`, `crowdfunding_ready`, `educational_game`,
  `print_and_play`.
- `software_product`: `idea_to_mvp`, `internal_tool`, `saas_product`,
  `open_source_tool`, `enterprise_integration`.
- `research_report`: `quick_brief`, `deep_research`,
  `competitive_benchmark`, `decision_memo`, `literature_review`.
- `course_or_training_program`: `short_workshop`, `online_course`,
  `corporate_training`, `bootcamp`, `self_paced_program`.

Modules add cross-cutting concerns and can attach to multiple verticals.
Recommended module candidates:

- `go_to_market`
- `risk_management`
- `roadmap`
- `stakeholder_alignment`
- `accessibility`
- `security_privacy`
- `production_feasibility`
- `crowdfunding`
- `education`
- `community_building`
- `monetization`

## Suggested Package Layout

Internal default resources should be shaped so they can later be backed by a
registry without changing project-local semantics:

```text
p2p/verticals/
  base_project/
    vertical.yml
    sections/
    rubrics.yml
    artifacts/
  software_product/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/
  ai_agent_or_automation/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/
  startup_or_business/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/
  research_report/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/
  board_game_design/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/

p2p/modules/
  go_to_market/
  crowdfunding/
  production_feasibility/
  accessibility/
  security_privacy/
  compliance/
  education/
  community_building/
  monetization/
```

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

#### Goals

- Make proposal artifact expectations explicit and visible to agents.
- Prevent important proposal artifacts from staying empty by default when they are applicable.
- Keep lightweight proposals lightweight by allowing non-applicable artifacts to be skipped with an explicit reason.
- Guide agents to ask one focused owner question at a time when artifact gaps block maturity.
- Preserve owner control: agents may ask, draft, identify gaps, and recommend next steps, but do not decide acceptance.

#### Non-Goals

- Do not require every proposal artifact to be fully populated for every proposal.
- Do not replace the existing readiness engine or create a parallel proposal lifecycle.
- Do not retroactively rewrite accepted proposals.
- Do not make agents perform broad unmanaged scans of .p2p or source code to satisfy artifact checks.

#### Suggested Scope

# Suggested Scope - PROP-086

Not suggested yet.

### PROP-087 - Agent Personality Model For Decision Mediation

#### Goals

- Define a durable project-level interaction-style model for agent mediation with the decision owner.
- Persist three explicit independent scales: technical_verbosity, formality, and assertiveness.
- Provide stable defaults: technical_verbosity=2, formality=2, assertiveness=0.
- Expose read/update behavior through public project interaction-style CLI commands and matching MCP tools.
- Update generated agent instructions and project/local skills so agents know how to inspect and update style through CLI/MCP only.

#### Non-Goals

- Do not let personality change governance authority, readiness scores, validation, permissions, facts, or audit evidence.
- Do not introduce open-ended persona prose or persisted named presets as the primary configuration model.
- Do not implement per-agent or runtime/session style overrides in the first slice.
- Do not require migration or manual completion for existing projects.

#### Suggested Scope

# Suggested Scope - PROP-087

## In Scope

- Project-level `interaction_style` configuration.
- Three validated integer fields:
  - `technical_verbosity` from 0 to 5.
  - `formality` from 0 to 5.
  - `assertiveness` from 0 to 5.
- Defaults:
  - `technical_verbosity: 2`
  - `formality: 2`
  - `assertiveness: 0`
- CLI namespace: `p2p project interaction-style`.
- MCP tools for status/read and write-safe update.
- Generated agent instruction updates.
- Project/local skill updates explaining how to inspect and update style.
- Backward-compatible fallback when no style is configured.

## Out Of Scope

- Persisted named presets.
- Per-agent style overrides.
- Runtime/session style overrides.
- Any change to governance authority, validation truth, readiness scoring,
  permission gates, or audit behavior.

## Suggested CLI Shape

```text
p2p project interaction-style show
p2p project interaction-style set --technical-verbosity 2 --formality 2 --assertiveness 0
```

The exact command spelling can still be refined during implementation specs,
but the namespace should remain project-scoped.

## Accepted Proposals And Decisions

- PROP-001 - — CLI Foundation
  - source: .p2p/proposals/PROP-001-cli-foundation
  - decision_reason: The project needs a minimal executable workflow before adding AI adapters, exporters, MCP, or a web interface. Automating the manually bootstrapped `.p2p/` structure is the shortest path to dogfooding.
- PROP-002 - Proposal Exploration And Readiness Workflow
  - source: .p2p/proposals/PROP-002-exploration-phase
  - decision_reason: Owner accepts the proposal exploration and readiness workflow after review.
- PROP-004 - Prompt-only Import Workflow
  - source: .p2p/proposals/PROP-004-prompt-only-import-workflow
  - decision_reason: Il workflow prompt-only deve essere completo: ogni fase che genera prompt deve poter importare l'output prodotto da AI, agenti esterni o dall'utente.
- PROP-005 - Codex Skill Integration
  - source: .p2p/proposals/PROP-005-codex-skill-integration
  - decision_reason: P2P Engine now has enough CLI workflow surface for Codex to use it as a structured method. A local skill makes the expected behavior explicit and reduces the risk of leaving decisions only in chat.
- PROP-006 - Multi-Agent Integration Model
  - source: .p2p/proposals/PROP-006-multi-agent-integration-model
  - decision_reason: Owner accepts PROP-006 after refinement. The proposal is considered ready as-is because remaining low readiness score reflects the current conservative readiness CLI, not unresolved product direction. A separate follow-up proposal will address readiness assessment refresh and review workflow.
- PROP-009 - Governance CLI Commands
  - source: .p2p/proposals/PROP-009-governance-cli-commands
  - decision_reason: PROP-008 ha definito il modello di governance, ma senza comandi CLI il workflow resta solo documentale. I comandi governance, swot, vote e precedent rendono il modello provabile nel repository senza introdurre ancora un sistema di privilegi applicativi.
- PROP-010 - P2P Project State Model
  - source: .p2p/proposals/PROP-010-p2p-software-specification-model
  - decision_reason: P2P Engine needs an internal rationalized project state before exporting to OpenSpec, Spec Kit, or task systems. Raw proposal folders contain discussion, governance, alternatives, and decision history; they should not be treated directly as implementation specifications.
- PROP-011 - Project Refresh MVP
  - source: .p2p/proposals/PROP-011-project-refresh-mvp
  - decision_reason: Project refresh MVP is implemented with deterministic .p2p/project generation and CLI inspection commands.
- PROP-012 - Impact Map and Conflict Memory
  - source: .p2p/proposals/PROP-012-impact-map-and-conflict-memory
  - decision_reason: Impact analysis and conflict memory are implemented as prompt-only impact artifacts plus persistent .p2p/project/conflicts.yml commands.
- PROP-013 - Managed Git Adapter and Change Set Model
  - source: .p2p/proposals/PROP-013-change-set-and-git-branch-model
  - decision_reason: P2P Engine should expose proposal, choice, decision, change, and task concepts to users. Git remains the internal layer for persistence, audit, synchronization, and collaboration, but users should not need to reason about branches, commits, merges, or tags during normal workflows.
- PROP-014 - Change Set Metadata MVP
  - source: .p2p/proposals/PROP-014-change-set-metadata-mvp
  - decision_reason: Change Set metadata MVP is implemented with create/status/policy commands and metadata-only managed Git policy.
- PROP-015 - Change Set Lifecycle and Task Tracking
  - source: .p2p/proposals/PROP-015-change-set-lifecycle-and-task-tracking
  - decision_reason: Change Set lifecycle transitions and task/action inspection are implemented with validated status changes and metadata-only behavior.
- PROP-016 - Project Registries MVP
  - source: .p2p/proposals/PROP-016-project-registries-mvp
  - decision_reason: Accepted as the next MVP step to introduce generated project registries for proposals, decisions, changes, choices, relations and artifacts.
- PROP-017 - Proposal Intake and Context Analysis MVP
  - source: .p2p/proposals/PROP-017-proposal-intake-and-context-analysis-mvp
  - decision_reason: Accepted to add registry-backed proposal intake and context analysis as the next usability layer for multi-user and multi-agent P2P workflows.
- PROP-018 - Choice Management CLI MVP
  - source: .p2p/proposals/PROP-018-choice-management-cli-mvp
  - decision_reason: Accepted to make choices first-class CLI-managed artifacts after INTAKE-001 required opening CHOICE-001.
- PROP-019 - Proposal Decision Shortcut Commands
  - source: .p2p/proposals/PROP-019-proposal-decision-shortcut-commands
  - decision_reason: Accepted to make proposal lifecycle decisions easier for users and AI agents.
- PROP-020 - Proposal Inspection CLI MVP
  - source: .p2p/proposals/PROP-020-proposal-inspection-cli-mvp
  - decision_reason: Accepted to provide stable proposal inspection commands needed before updating agent skills.
- PROP-021 - Agent Skill Real Commands Update
  - source: .p2p/proposals/PROP-021-agent-skill-real-commands-update
  - decision_reason: Accepted to align the Codex skill with the current P2P CLI before using agents more heavily.
- PROP-022 - Operational Brief Prompt Workflow
  - source: .p2p/proposals/PROP-022-operational-brief-prompt-workflow
  - decision_reason: Accepted to introduce intelligence through a prompt-only operational brief workflow while preserving CLI-owned context and owner-controlled decisions.
- PROP-023 - Next Action Recommender MVP
  - source: .p2p/proposals/PROP-023-next-action-recommender-mvp
  - decision_reason: Accepted to connect operational brief next-actions to a top-level advisory p2p next command and concise project status summary.
- PROP-024 - Choice Blocking and Discovery MVP
  - source: .p2p/proposals/PROP-024-choice-blocking-and-discovery-mvp
  - decision_reason: Accepted to make choices operational through advisory discovery first and explicit owner-controlled blockers second.
- PROP-025 - Controlled Intake Apply Workflow
  - source: .p2p/proposals/PROP-025-controlled-intake-apply-workflow
  - decision_reason: Accepted to implement intake apply as an auditable plan/show/run workflow rather than direct automatic application.
- PROP-026 - P2P Software Spec Generator MVP
  - source: .p2p/proposals/PROP-026-p2p-software-spec-generator-mvp
  - decision_reason: Accepted to introduce the P2P-native software spec layer before downstream OpenSpec or Spec Kit export.
- PROP-027 - Software Spec Exporter MVP
  - source: .p2p/proposals/PROP-027-software-spec-exporter-mvp
  - decision_reason: Accepted to add the first downstream export layer after the refined P2P-native software spec MVP.
- PROP-028 - Spec Kit Export Mapping MVP
  - source: .p2p/proposals/PROP-028-spec-kit-export-mapping-mvp
  - decision_reason: Accepted to complete the declared Spec Kit export target with a conservative P2P-spec-derived mapping.
- PROP-029 - Spec Export Validation MVP
  - source: .p2p/proposals/PROP-029-spec-export-validation-mvp
  - decision_reason: Accepted to add read-only validation before downstream use of generated export bundles.
- PROP-030 - Managed Work and Multi-Branch Visibility Policy
  - source: .p2p/proposals/PROP-030-managed-work-and-multi-branch-visibility-policy
  - decision_reason: Accepted to introduce P2P Work as the user-facing abstraction for the incremental path toward invisible managed Git.
- PROP-031 - Multi-Branch Work Scan MVP
  - source: .p2p/proposals/PROP-031-multi-branch-work-scan-mvp
  - decision_reason: Accepted to add read-only visibility into P2P-managed work manifests on parallel local branches.
- PROP-032 - Managed Work Branch Creation MVP
  - source: .p2p/proposals/PROP-032-managed-work-branch-creation-mvp
  - decision_reason: This is the next incremental step toward invisible managed Git: isolate operational work in P2P-managed branches without automatic commit or merge.
- PROP-033 - Managed Work Submit MVP
  - source: .p2p/proposals/PROP-033-managed-work-submit-mvp
  - decision_reason: This is the next incremental managed Git level: local auditable submit without push or merge.
- PROP-034 - Managed Work Review MVP
  - source: .p2p/proposals/PROP-034-managed-work-review-mvp
  - decision_reason: This completes the local review-request level before remote handoff and owner merge.
- PROP-035 - Managed Work Publish MVP
  - source: .p2p/proposals/PROP-035-managed-work-publish-mvp
  - decision_reason: This adds the remote handoff step after local review while keeping PR creation and merge separate.
- PROP-036 - Managed Work Accept MVP
  - source: .p2p/proposals/PROP-036-managed-work-accept-mvp
  - decision_reason: This completes the local owner-controlled managed Work lifecycle before optional base-branch push and cleanup.
- PROP-037 - Managed Work Status Summary MVP
  - source: .p2p/proposals/PROP-037-managed-work-status-summary-mvp
  - decision_reason: This is the safest next refinement: a read-only operational view before conflict handling, finalize, or GitHub PR work.
- PROP-038 - Managed Work Merge Conflict Guidance MVP
  - source: .p2p/proposals/PROP-038-managed-work-merge-conflict-guidance-mvp
  - decision_reason: Accept/merge is the riskiest step in the managed Work lifecycle; conflicts need explicit P2P guidance before finalize or GitHub handoff.
- PROP-039 - Managed Work Finalize MVP
  - source: .p2p/proposals/PROP-039-managed-work-finalize-mvp
  - decision_reason: Finalize is the explicit post-accept publication step and keeps base-branch push separate from cleanup and PR creation.
- PROP-040 - Managed Work Cleanup MVP
  - source: .p2p/proposals/PROP-040-managed-work-cleanup-mvp
  - decision_reason: Cleanup is the explicit post-finalize branch housekeeping step and keeps branch deletion separate from accept/finalize.
- PROP-041 - Remote Project Profile and Review Request Policy
  - source: .p2p/proposals/PROP-041-remote-project-profile-and-review-request-policy
  - decision_reason: Remote review must remain optional and provider-agnostic; publish should stay separate from PR/MR handoff.
- PROP-042 - P2P Core CLI MCP Mediator Web Boundary
  - source: .p2p/proposals/PROP-042-p2p-core-cli-mcp-mediator-web-boundary
  - decision_reason: The five-layer boundary keeps the core deterministic and open-source usable while allowing optional MCP, mediator, and web layers to evolve independently.
- PROP-043 - Managed Work Retire MVP
  - source: .p2p/proposals/PROP-043-managed-work-retire-mvp
  - decision_reason: Obsolete planned Work manifests should be retired through an explicit metadata-only command instead of manual manifest edits.
- PROP-044 - P2P MCP Server MVP
  - source: .p2p/proposals/PROP-044-p2p-mcp-server-mvp
  - decision_reason: A local read-only MCP server is the safest first agent-facing interface over the deterministic P2P Core.
- PROP-045 - Agent-Safe Project Bootstrap MVP
  - source: .p2p/proposals/PROP-045-agent-safe-project-bootstrap-mvp
  - decision_reason: Accepted as the immediate hardening step after the MCP local test showed that agents need explicit project-level boundaries before write-capable MCP tools are added.
- PROP-046 - MCP Write-Safe Bootstrap Tools MVP
  - source: .p2p/proposals/PROP-046-mcp-write-safe-bootstrap-tools-mvp
  - decision_reason: Accepted as the next controlled MCP increment after agent-safe init: expose only bootstrap and registry refresh primitives, not governance decisions.
- PROP-047 - Guided Init Wizard MVP
  - source: .p2p/proposals/PROP-047-guided-init-wizard-mvp
  - decision_reason: Accepted to make the newly hardened init path usable for first-time users before broadening MCP mutations.
- PROP-048 - MCP Level 3 Proposal and Intake Draft Tools
  - source: .p2p/proposals/PROP-048-mcp-level-3-proposal-and-intake-draft-tools
  - decision_reason: Accepted as MCP Level 3: safe contribution draft tools are needed after bootstrap hardening, while governance decisions remain out of MCP.
- PROP-049 - MCP Level 4A Proposal Refinement Tools
  - source: .p2p/proposals/PROP-049-mcp-level-4a-proposal-refinement-tools
  - decision_reason: Accepted as MCP Level 4A: support advisory draft refinement and brief prompt/show without opening governance mutations.
- PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools
  - source: .p2p/proposals/PROP-050-mcp-level-4b-choice-conflict-impact-advisory-tools
  - decision_reason: Accepted as MCP Level 4B: expose advisory analysis for choices, conflicts, and impact without governance mutations.
- PROP-051 - Draft Proposal Next Action and Agent Explanation Guard
  - source: .p2p/proposals/PROP-051-draft-proposal-next-action-and-agent-explanation-guard
  - decision_reason: Accepted to tighten the observed MCP test behavior: draft proposals should produce useful next actions, and explanations should be grounded in show/read tools.
- PROP-052 - MCP Proposal Contribution Tool
  - source: .p2p/proposals/PROP-052-mcp-proposal-contribution-tool
  - decision_reason: Accepted as MCP Level 5A: adding contributions is a safe way to reduce duplicate proposal proliferation without opening governance decisions.
- PROP-053 - Core Validation Layer MVP
  - source: .p2p/proposals/PROP-053-core-validation-layer-mvp
  - decision_reason: Accepted to harden the deterministic core before packaging, Rust migration planning, or owner-gated MCP mutations.
- PROP-054 - Project Readiness and Maturity Assessment
  - source: .p2p/proposals/PROP-054-project-readiness-and-maturity-assessment
  - decision_reason: Accepted to add an explainable deterministic project readiness assessment before subjective maturity rubrics, packaging, or owner-gated automation.
- PROP-055 - Agent Token Budget and Context Discipline
  - source: .p2p/proposals/PROP-055-agent-token-budget-and-context-discipline
  - decision_reason: Accepted as the C-light MVP: combine skill policy, CLI compact context, and MCP compact context to reduce agent token consumption without adding advanced token estimation yet.
- PROP-056 - Project Definition Maturity Rubrics
  - source: .p2p/proposals/PROP-056-project-definition-maturity-rubrics
  - decision_reason: Accepted to distinguish structural readiness from project definition maturity and introduce extensible domain rubrics as deterministic drivers for export readiness.
- PROP-057 - Guided Rubric Selection During Init
  - source: .p2p/proposals/PROP-057-guided-rubric-selection-during-init
  - decision_reason: Accepted to close the domain-to-rubric onboarding loop by letting the owner confirm which suggested criteria drive project definition maturity.
- PROP-058 - Project README and Installation Guide
  - source: .p2p/proposals/PROP-058-project-readme-and-installation-guide
  - decision_reason: Accepted to make the repository self-explanatory for new users now that Core, CLI, MCP, context, and maturity rubric MVPs are implemented.
- PROP-059 - P2PWorkspace Modular Refactoring Plan
  - source: .p2p/proposals/PROP-059-p2pworkspace-modular-refactoring-plan
  - decision_reason: Owner accepts the modular refactoring direction after consolidating scope, alternatives, compatibility constraints, first deliverable, first future extraction, and specs binding boundary. This is an explicit owner decision despite the automated readiness score remaining weak.
- PROP-061 - Focused README and Documentation Map
  - source: .p2p/proposals/PROP-061-focused-readme-and-documentation-map
  - decision_reason: Accepted to keep README focused on the p2p-engine repository and add a clear documentation map before expanding detailed guides.
- PROP-062 - README Product Landing Page Refinement
  - source: .p2p/proposals/PROP-062-readme-product-landing-page-refinement
  - decision_reason: Accepted to make the public README more effective as the p2p-engine landing page while keeping future hosted layers out of scope.
- PROP-064 - Spec Kit Three-Prompt Export Model
  - source: .p2p/proposals/PROP-064-spec-kit-three-prompt-export-model
  - decision_reason: Accepted fully. P2P should not imitate downstream tool domains or generate downstream-shaped folder bundles. Its vocation is to turn confused, distributed, discontinuous ideas and contributions into an organized project definition while supporting the decision flow. Exports should therefore be agent-first project definition and prompt/document outputs derived from accepted P2P memory.
- PROP-065 - MCP Agent-First Coverage Expansion
  - source: .p2p/proposals/PROP-065-mcp-agent-first-coverage-expansion
  - decision_reason: Accepted to expose priority 1 read-only, priority 2 write-safe deterministic, and priority 3 prompt/advisory MCP tools while preserving owner-only governance boundaries.
- PROP-066 - Permission-Gated MCP Governance And Git Operations
  - source: .p2p/proposals/PROP-066-permission-gated-mcp-governance-and-git-operations
  - decision_reason: Accepted as the permission-gated MCP model: project-declared roles, owner/contributor fallback identities, consent receipts for privileged operations, audit records, and Git provider enforcement for cloud-backed repositories.
- PROP-067 - Agent-First Setup Documentation Split
  - source: .p2p/proposals/PROP-067-agent-first-setup-documentation-split
  - decision_reason: Accepted to align public setup documentation with the agent-first new-project workflow and move P2P Engine contributor setup into CONTRIBUTING.md.
- PROP-068 - Document Agent MCP Client Setup Commands
  - source: .p2p/proposals/PROP-068-document-agent-mcp-client-setup-commands
  - decision_reason: Accepted to make new-project MCP client setup copy-pastable for verified agent environments while keeping contributor setup isolated in CONTRIBUTING.md.
- PROP-069 - Clarify MCP Stdio Integration Model
  - source: .p2p/proposals/PROP-069-clarify-mcp-stdio-integration-model
  - decision_reason: Accepted to make MCP stdio setup and client integration semantics precise before public users rely on the install docs.
- PROP-070 - Clarify README Agent Access Modes
  - source: .p2p/proposals/PROP-070-clarify-readme-agent-access-modes
  - decision_reason: Accepted to clarify README quick start semantics: agents can use CLI or MCP, and MCP is intentionally limited until permission/ownership governance is decided.
- PROP-071 - Custom Domain Definition Workflow
  - source: .p2p/proposals/PROP-071-custom-domain-definition-workflow
  - decision_reason: Accepted to make domain and rubric initialization explicit and template-based across all projects, with custom/none treated as unresolved setup work.
- PROP-072 - Concurrent Managed Work and Merge Decision Model
  - source: .p2p/proposals/PROP-072-concurrent-managed-work-and-merge-decision-model
  - decision_reason: Accepted as the core CLI-facing collaboration model for concurrent proposal branches, managed remote sync, candidate Work selection, safe proposal ID collision handling, and agent-safe Git abstraction.
- PROP-073 - Ergonomic Remote Project Initialization
  - source: .p2p/proposals/PROP-073-ergonomic-remote-project-initialization
  - decision_reason: Accepted to fix dogfooding gaps in remote/cloud project initialization: init must validate repository mode, configure P2P remote profile ergonomically, detect Git origin/profile divergence, and provide actionable recovery without requiring raw Git knowledge.
- PROP-074 - Agent Runtime Bootstrap Robustness
  - source: .p2p/proposals/PROP-074-agent-runtime-bootstrap-robustness
  - decision_reason: Accepted to make P2P-managed repositories usable in local and cloud agent runtimes when the p2p executable is missing or not on PATH, by adding runtime diagnostics, documented discovery fallbacks, and actionable recovery while preserving the Missing Primitive Rule.
- PROP-075 - MCP End-To-End Proposal Collaboration Workflow
  - source: .p2p/proposals/PROP-075-mcp-end-to-end-proposal-collaboration-workflow
  - decision_reason: Accepted to close the MCP proposal collaboration workflow discovered during dogfooding: MCP can now configure remote profile metadata, commit proposal drafts, branch from an explicit safe base, request owner consent without granting it, and then use existing permission-gated publish/review tools once owner consent is granted.
- PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model
  - source: .p2p/proposals/PROP-076-p2p-cloud-runner-boundary-and-containerized-execution-model
  - decision_reason: Accepted as the architectural boundary for future cloud work: P2P Engine remains local CLI/filesystem/Git/local-MCP, while P2P Cloud owns web/API/auth/UI/workflows/database and invokes P2P through isolated runner containers.
- PROP-077 - Permission-Gated Draft Proposal Decisions via MCP
  - source: .p2p/proposals/PROP-077-permission-gated-draft-proposal-decisions-via-mcp
  - decision_reason: Owner requested this refinement after real MCP usage exposed that draft proposal rejection was not available as a permission-gated MCP operation.
- PROP-078 - Project-Local Wheel Installation and Upgrade Model
  - source: .p2p/proposals/PROP-078-project-local-wheel-installation-and-upgrade-model
  - decision_reason: Owner approved project-local wheel installation as the transitional packaging model before public package distribution.
- PROP-079 - Managed Next Action Lifecycle
  - source: .p2p/proposals/PROP-079-managed-next-action-lifecycle
  - decision_reason: Owner selected the hybrid generated plus curated next-action model and requested implementation.
- PROP-080 - Automated GitHub Release Wheel Publishing
  - source: .p2p/proposals/PROP-080-automated-github-release-wheel-publishing
  - decision_reason: Owner approved automated tag-triggered GitHub release publishing to replace the manual wheel upload path.
- PROP-081 - MCP and Skill Support for Managed Next Actions
  - source: .p2p/proposals/PROP-081-mcp-and-skill-support-for-managed-next-actions
  - decision_reason: Owner requested MCP and skill alignment for the newly implemented managed next-action lifecycle.
- PROP-082 - Readiness Assessment Refresh And Review Workflow
  - source: .p2p/proposals/PROP-082-readiness-assessment-refresh-and-review-workflow
  - decision_reason: Owner confirms the refined second-slice direction for artifact-aware proposal questions, stepped readiness-driven agent assertiveness, evidence-aware readiness recalculation, and proactive low-readiness interview behavior.
- PROP-083 - Domain-Aware Visible Project Definition Export
  - source: .p2p/proposals/PROP-083-domain-aware-visible-project-definition-export
  - decision_reason: Owner accepts the domain-aware visible project definition export. Readiness has no missing gaps after refinement, but computed score remains partial because the current readiness profile is conservative and keeps confidence low for artifact-derived assessments.
- PROP-085 - Pluggable Project Verticals And Readiness Orchestration
  - source: .p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration
  - decision_reason: Accepted by owner after readiness reached decision_ready. The proposal defines pluggable pure-data project verticals, base_project, custom vertical candidate flow, project readiness review, and proposal-to-vertical traceability while preserving backward compatibility.
- PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration
  - source: .p2p/proposals/PROP-086-artifact-aware-proposal-readiness-and-agent-interview-orchestration
  - decision_reason: Accepted by owner as an explicit readiness override. The current default-readiness-v0.1 score remains weak because it is not artifact-aware, but the owner accepts the refined direction: introduce a dedicated artifact-specific CLI/MCP primitive, graduated-by-risk artifact requirements, default coverage for new proposals, advisory absent_legacy handling for old proposals, strict CLI/MCP-only memory mutation, and tests for readiness/context/MCP/missing-primitive behavior.
- PROP-087 - Agent Personality Model For Decision Mediation
  - source: .p2p/proposals/PROP-087-agent-personality-model-for-decision-mediation
  - decision_reason: Accepted by owner. The proposal is decision-ready and defines a project-level interaction_style model with three explicit scales, defaults, CLI/MCP surfaces, generated instruction updates, and no persisted presets.

## Requirements And Acceptance

### PROP-001 - — CLI Foundation

- A user can install or run the CLI locally.
- `p2p init` creates the baseline `.p2p/` structure.
- `p2p proposal create "CLI Foundation"` creates a proposal folder and baseline artifacts.
- `p2p contribution add PROP-001` appends a valid YAML contribution.
- `p2p decision record PROP-001 --outcome accepted` records a decision artifact.
- Prompt commands generate prompt files under `.p2p/prompts/<proposal-id>/`.
- `p2p status` shows project and proposal state.
- No direct AI provider is required.

### PROP-002 - Proposal Exploration And Readiness Workflow

- Esiste un modello documentato di proposal readiness profile-based e versioned.
- Esiste un profilo iniziale `default-readiness-v0.1` con criteri, pesi e
  soglie.
- La readiness separa lifecycle state, computed score, computed label,
  confidence, failed gates, missing dimensions, suggested next actions ed
  effective governance status.
- `computed_score` resta separato da owner override.
- Owner override sotto target richiede reason obbligatoria ed e registrato come
  evento governance/audit.
- Le proposal supportano tier `small`, `medium`, `architectural` e
  `governance-critical`.
- Il modello supporta required score, minimum gates e confidence requirement per
  tier.
- Gli artifact exploration supportano stati di qualita almeno:
  `missing`, `placeholder`, `thin`, `meaningful`, `needs_owner_input`, `ready`.
- Artifact quality caps impediscono a contenuti mancanti, placeholder, thin o
  generici di ottenere pieno punteggio.
- Ogni criterio del readiness assessment puo registrare evidence strutturata e
  note leggibili.
- `p2p proposal readiness`, `refresh` ed `explain` sono definiti come comandi
  target del workflow.
- `p2p explore status` resta responsabile della qualita artifact, distinto da
  proposal readiness.
- `p2p next` puo usare readiness snapshot per suggerire readiness gaps, failed
  gates e highest-impact actions.
- MCP espone readiness read tools agli agenti e mantiene override/acceptance come
  operazioni governance-gated.
- Le skill agentiche vengono aggiornate per rendere l'agente piu pedante nella
  valutazione di readiness e alternative.
- Le draft aperte possono essere marcate `not_assessed`; le proposal accettate
  legacy non vengono riscritte.
- `p2p validate` resta pulito dopo l'import della proposal sintetizzata.

### PROP-004 - Prompt-only Import Workflow

- Ogni fase prompt-only ha un comando prompt e un comando import.
- I test coprono un workflow completo da proposal a tasks.

### PROP-005 - Codex Skill Integration

- Codex sa quando creare o aggiornare una proposal P2P.
- Codex usa la CLI per generare/importare artefatti invece di lasciare output solo in chat.

### PROP-006 - Multi-Agent Integration Model

- Default project init installs generic plus all supported project-local adapters: codex, claude, cursor, copilot, gemini, and opencode.
- A narrowed init can install only requested specific adapters, but generic is still created and remains unremovable.
- .p2p/agent-integrations.yml uses schema_version 1 with baseline_profile, adapters, capabilities, template_version, generated file records, shared ownership, managed flag, template_id, SHA-256 hash, and drift state.
- The registry records installed integrations and generated files without active_agent, default_agent, preferred_agent, current, use, or switch state.
- Built-in adapter templates live in package data for the MVP; project-local template overrides are deferred.
- The generic baseline defines the minimum P2P governance rules and all generated agent-specific files preserve those rules.
- Generated instructions include a readiness gap handling block that requires agents to explain failed gates, propose alternatives, recommend one option when justified, identify owner decisions, draft candidate updates, and re-check readiness.
- The adapter matrix documents exact generated files for each built-in adapter and excludes deprecated .cursorrules and default opencode.json generation.
- install all detects non-shared file target conflicts and refuses conflicting adapters instead of overwriting.
- Generated files are recorded with template version, ownership metadata, shared-file flag, and SHA-256 hash over exact file bytes.
- Updating an adapter refreshes unchanged generated files and refuses to silently overwrite drifted files.
- Uninstall removes only the target adapter's managed, unchanged, non-shared files and preserves generic, shared, modified, and unmanaged files.
- p2p agent doctor validates registry shape, file existence, hashes, shared references, generic baseline, ownership conflicts, uninstall safety, and method behavior presence.
- Existing projects migrate conservatively by marking known generated files as managed and unknown or changed files as unmanaged or drifted without overwriting them.
- The .agents/skills path is used only for agent-neutral P2P skill content or otherwise deferred to avoid Codex/OpenCode interpretation conflicts.
- CLI and MCP expose equivalent agent integration lifecycle operations through the same core behavior.
- Existing p2p agent instructions refresh behavior remains backward compatible.

### PROP-009 - Governance CLI Commands

- La CLI genera e valida governance.yml, roles.yml e decision-precedents.yml.
- La CLI puo registrare voti in votes.yml e mostrare lo stato di voto.
- La CLI puo generare un prompt SWOT e registrare un precedente decisionale.

### PROP-010 - P2P Project State Model

- The proposal defines the `.p2p/project/` directory structure.
- The proposal defines when and how accepted proposals update project state.
- The proposal distinguishes P2P-native project state from OpenSpec and Spec Kit exports.

### PROP-011 - Project Refresh MVP

- p2p project refresh creates .p2p/project with deterministic files.
- p2p project status reports accepted proposal count and feature count.
- p2p project show can print overview or a feature.

### PROP-012 - Impact Map and Conflict Memory

- A proposal can generate an impact prompt.
- Impact artifacts can be imported into a proposal folder.
- Conflicts can be recorded in .p2p/project/conflicts.yml and inspected from the CLI.

### PROP-013 - Managed Git Adapter and Change Set Model

- The proposal defines Proposal, Choice, Decision, Change Set, Git Adapter, Branch, Commit, Merge, and Tag.
- The proposal defines a managed Git policy for branch/commit/tag behavior.
- The proposal defines an initial .p2p/changes structure.
- The proposal addresses the risk of arbitrary branch decisions by moving the choice into explicit policy.

### PROP-014 - Change Set Metadata MVP

- p2p change create creates a valid CHANGE-XXX folder from an accepted proposal.
- p2p change create rejects draft proposals.
- p2p change status lists Change Sets and lifecycle state.
- p2p change policy shows metadata-only Git policy and reasoning.

### PROP-015 - Change Set Lifecycle and Task Tracking

- A Change Set can transition through planned, implementation_ready, in_progress, in_review and completed.
- Invalid transitions are rejected with a clear error.
- p2p change show displays a Change Set summary.
- p2p change tasks displays tasks and actions from the Change Set artifacts.

### PROP-016 - Project Registries MVP

- The proposal defines .p2p/registries structure.
- The proposal distinguishes primary sources from generated registries.
- The proposal defines initial registry refresh/status commands.
- The proposal explains how registries support intake, impact, conflicts and exports.

### PROP-017 - Proposal Intake and Context Analysis MVP

- The proposal defines intake analysis inputs and outputs.
- The proposal defines initial CLI commands for intake prompt/status/import or analysis.
- The proposal explains how intake supports multi-user and multi-agent collaboration.

### PROP-018 - Choice Management CLI MVP

- Users can create a choice with multiple options.
- Users can list existing choices.
- Users can decide a choice and preserve the selected option and rationale.

### PROP-019 - Proposal Decision Shortcut Commands

- A user can accept a proposal with a reason.
- A user can reject a proposal with a reason.
- A user can defer a proposal with a reason.

### PROP-020 - Proposal Inspection CLI MVP

- Users can list proposals with statuses and titles.
- Users can filter proposals by status.
- Users can show a proposal summary.
- Choice registry output is not printed as raw Python dictionaries.

### PROP-021 - Agent Skill Real Commands Update

- The skill references registry refresh/status.
- The skill references proposal list/show and decision shortcuts.
- The skill references intake and choice workflows.

### PROP-022 - Operational Brief Prompt Workflow

- p2p project brief prompt creates a prompt and context file.
- p2p project brief import stores operational-brief.md and optional next-actions.yml.
- p2p project brief show prints the stored operational brief.

### PROP-023 - Next Action Recommender MVP

- p2p next lists ordered advisory actions.
- p2p next --top 1 shows only the first action.
- p2p next falls back when next-actions.yml is missing or empty.
- p2p project status shows operational brief availability, next action count, and first next action summary.

### PROP-024 - Choice Blocking and Discovery MVP

- p2p choice show CHOICE-XXX shows project choice details and links.
- p2p choice status lists project choices and proposal-local choice candidates.
- p2p choice discover reports advisory findings without modifying state.
- p2p choice block/unblock records and deactivates explicit blockers in links.yml.
- p2p next prioritizes active unresolved choice blockers before generic continue_change actions.

### PROP-025 - Controlled Intake Apply Workflow

- p2p intake apply plan INTAKE-XXX writes apply-plan.yml.
- p2p intake apply show INTAKE-XXX displays planned actions.
- p2p intake apply run supports add_contribution.
- p2p intake apply run supports open_choice only when at least two --option values are provided.
- defer, accept, reject, duplicate and unsupported actions are not applied automatically.
- applied-actions.yml records every successful application.

### PROP-026 - P2P Software Spec Generator MVP

- p2p spec refresh --change CHANGE-XXX generates index.md, requirements.md, design.md, commands.yml, data-model.yml, acceptance.md and provenance.yml.
- p2p spec status lists generated specs.
- p2p spec show CHANGE-XXX prints index.md.
- p2p spec prompt --change CHANGE-XXX writes a refinement prompt.
- p2p spec import CHANGE-XXX spec-output/ validates required files and YAML keys.

### PROP-027 - Software Spec Exporter MVP

- p2p spec export --change CHANGE-XXX --target generic writes an export bundle from the refined P2P spec. p2p spec export --change CHANGE-XXX --target openspec writes an OpenSpec-oriented bundle. p2p spec export-status lists export bundles. p2p spec export-show CHANGE-XXX --target TARGET prints the export index. Tests cover successful export and unsupported targets.

### PROP-028 - Spec Kit Export Mapping MVP

- p2p spec export --change CHANGE-XXX --target speckit writes a Spec Kit-oriented feature directory. Export status and show include the speckit target. The export is generated only from the P2P-native software spec and provenance. Tests cover successful speckit export and required artifacts.

### PROP-029 - Spec Export Validation MVP

- p2p spec export-validate CHANGE-XXX --target generic validates generic bundles. The same command validates openspec and speckit bundles. Missing files or manifest mismatches fail explicitly. Tests cover valid bundles and invalid/missing export artifacts.

### PROP-030 - Managed Work and Multi-Branch Visibility Policy

- p2p work plan --change CHANGE-XXX --target TARGET creates a WORK manifest with source Change Set, export target, validation status, logical branch name, allowed files, and disabled auto_branch/auto_commit/auto_merge policy. p2p work list and p2p work show inspect manifests. Skill guidance explains that Git remains invisible and future levels will add branch scan/create/submit/accept incrementally.

### PROP-031 - Multi-Branch Work Scan MVP

- p2p work scan lists local Work manifests and writes .p2p/registries/work.yml. p2p work list can include local manifests and scanned branch manifests. The scan handles non-Git or no-branch repositories gracefully. Tests cover scanning a P2P-managed branch without checkout.

### PROP-032 - Managed Work Branch Creation MVP

- A planned Work item can be branched with p2p work branch WORK-XXX; the command refuses dirty worktrees and existing branches; tests cover branch creation and safety failures; the P2P skill documents the workflow.

### PROP-033 - Managed Work Submit MVP

- A branched Work item can be submitted into one local commit; the command refuses wrong branches, unbranched Work items, and empty submissions; it does not push or merge; tests cover submit and safety behavior; the P2P skill documents Level 3.

### PROP-034 - Managed Work Review MVP

- A submitted Work item can request local review; the command refuses wrong branches, unsubmitted Work items, and dirty worktrees; it does not push, open PRs, or merge; tests cover review and safety behavior; the P2P skill documents the full Level 1-4 flow and the future 4.5/5 steps.

### PROP-035 - Managed Work Publish MVP

- A review_requested Work item can be published to origin; the command refuses wrong branches, unreviewed Work items, dirty worktrees, and missing remotes; it does not open PRs or merge; tests cover publish using a local bare remote and safety behavior; the P2P skill documents Level 4.5 separately from Level 5.

### PROP-036 - Managed Work Accept MVP

- A published Work item can be accepted into main/base locally; the command refuses unpublished Work, wrong branches, dirty worktrees, and missing Work branches; it does not push main or delete branches; tests cover accept and safety behavior; the P2P skill documents Level 5.

### PROP-037 - Managed Work Status Summary MVP

- p2p work status lists Work items with status, change, target, branch and next action; it handles planned, branched, submitted, review_requested, published, accepted, and scanned Work items; tests cover summary output; the P2P skill documents using status before lifecycle commands.

### PROP-038 - Managed Work Merge Conflict Guidance MVP

- Conflicting accepts do not produce ambiguous errors; Work status becomes merge_conflict with conflicted files; --continue completes the accept after conflicts are resolved; --abort aborts the merge and restores published state; tests cover conflict, continue, and abort; the skill documents the recovery flow.

### PROP-039 - Managed Work Finalize MVP

- An accepted Work item can be finalized to origin/main or another configured base branch; the command refuses unaccepted Work, wrong branches, dirty worktrees, and missing remotes; it does not delete local or remote Work branches; tests cover finalize and safety behavior; the skill documents finalize after accept.

### PROP-040 - Managed Work Cleanup MVP

- A finalized Work item can be cleaned locally; remote branch deletion only happens with --remote; the command refuses unfinalized Work, wrong branches, dirty worktrees, and missing branches; tests cover local cleanup, remote cleanup, and safety behavior; the skill documents cleanup after finalize.

### PROP-041 - Remote Project Profile and Review Request Policy

- p2p project remote configure/show can manage a local or remote-backed profile.
- p2p work request-review WORK-XXX works only after publish and records review-request metadata without opening a PR.
- The agent skill documents that publish does not create PRs and external provider adapters are future extensions.

### PROP-042 - P2P Core CLI MCP Mediator Web Boundary

- The architecture boundary is recorded as accepted project direction.
- Future MCP work must be scoped as an interface over the deterministic core, not as the mediator itself.
- Future mediator/web work must consume Core/CLI/MCP operations instead of becoming the source of truth.
- AI-assisted behavior remains advisory by default; owner-controlled governance remains the default policy.

### PROP-043 - Managed Work Retire MVP

- p2p work retire WORK-001 --reason TEXT marks a planned Work manifest retired.
- p2p work status shows retired Work with next none.
- The command refuses non-planned Work statuses.
- Tests cover successful retire and invalid status refusal.

### PROP-044 - P2P MCP Server MVP

- p2p-mcp-server can initialize over stdio and list tools.
- tools/call works for p2p_project_status, p2p_next, p2p_proposal_list, p2p_proposal_show, p2p_choice_list, p2p_choice_show, p2p_change_status, p2p_work_status, and p2p_registry_show.
- MCP tools are read-only in the MVP.
- Tests cover tool listing and representative tool calls without requiring a web server or network.

### PROP-045 - Agent-Safe Project Bootstrap MVP

- p2p init creates AGENTS.md and .p2p/agent-policy.yml by default; an initial agent profile can be selected without becoming permanent; p2p agent instructions refresh can add Codex, Claude, generic, or all instruction files; tests verify missing primitive behavior and owner-controlled boundaries are present.

### PROP-046 - MCP Write-Safe Bootstrap Tools MVP

- MCP tool definitions include the three write-safe bootstrap tools; p2p_init_project generates AGENTS.md and .p2p/agent-policy.yml; p2p_agent_instructions_refresh can add Codex/Claude/generic/all profiles; p2p_registry_refresh returns written registry paths; tests cover tool calls and confirm governance tools remain absent.

### PROP-047 - Guided Init Wizard MVP

- p2p init without a name prompts for project name, agent profile, repository mode, and MCP hint; p2p init NAME remains non-interactive; output includes next commands and optional MCP setup guidance; tests cover interactive and scriptable paths.

### PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

- MCP exposes proposal/intake draft tools; p2p_proposal_create returns a draft proposal with path and does not create an accepted decision; p2p_intake_prompt creates intake prompt artifacts; p2p_intake_status lists intake state; tests cover tool behavior and confirm governance tools remain absent.

### PROP-049 - MCP Level 4A Proposal Refinement Tools

- MCP exposes proposal update and project brief prompt/show tools; proposal update modifies proposal sections without changing decision status; project brief prompt returns context and prompt paths; project brief show returns stored brief or a clear error if missing; tests cover the flow and governance tools remain absent.

### PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

- MCP exposes choice discovery, conflict status, and impact prompt tools; tests verify choice discovery is read/advisory, conflict status does not record conflicts, impact prompt writes only prompt artifacts, and governance tools remain absent.

### PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

- p2p next suggests review_draft_proposal for draft proposals after registries are fresh and no stronger fallback exists; generated agent policy contains an explain_existing_artifacts rule; generated agent instructions mention reading via show/MCP before explaining; tests cover the new fallback and generated policy text.

### PROP-052 - MCP Proposal Contribution Tool

- MCP exposes p2p_proposal_contribution_add; the tool appends to contributions.yml and returns the new contribution; tests cover adding a contribution and verify decision status remains pending and governance tools remain absent.

### PROP-053 - Core Validation Layer MVP

- p2p validate reports no errors on a fresh valid project; invalid YAML or missing required files produce errors; stale registries produce warnings with p2p registry refresh suggestion; --format json emits machine-readable findings; exit code is 1 only for errors; MCP p2p_validate returns the same structured validation result; tests cover CLI and MCP behavior.

### PROP-054 - Project Readiness and Maturity Assessment

- A future MVP can implement p2p assess refresh and p2p assess show for deterministic completion; later rubric prompt/import can estimate domain maturity; scores are explainable and never treated as owner decisions; MCP exposure remains advisory or write-safe only.

### PROP-055 - Agent Token Budget and Context Discipline

- p2p context returns a compact deterministic context packet.
- p2p context --target ID limits output to one proposal, change, choice, or work target when possible.
- p2p context --budget small omits full document bodies and favors IDs, statuses, commands, and short reasons.
- MCP exposes equivalent compact context through p2p_context.
- Agent skill instructs agents to call compact context before broad file reads.
- The policy explicitly forbids broad scans when a CLI/MCP context command is sufficient.
- Advanced token estimation and numeric token budgets are deferred.

### PROP-056 - Project Definition Maturity Rubrics

- Project rubrics are stored in .p2p/project/rubrics.yml as editable project state.
- The rubric model supports multiple domains and enabled/disabled criteria.
- A software-domain rubric includes criteria such as problem definition, scope, user workflows, functional requirements, non-functional requirements, security/privacy, data model, integration boundaries, deployment/operations, testing strategy, UX/accessibility, risks/tradeoffs, and acceptance criteria.
- A maturity assessment reports per-criterion status, score, evidence, and suggested next action.
- The maturity score is explicitly project definition maturity, not implementation completeness.
- CLI and MCP expose the maturity assessment without requiring broad file scans by agents.

### PROP-057 - Guided Rubric Selection During Init

- Interactive p2p init asks whether to customize rubric criteria.
- If customization is skipped, all criteria remain enabled.
- If customization is accepted, each criterion can be enabled or disabled.
- .p2p/project/rubrics.yml stores enabled false for disabled criteria.
- p2p assess maturity refresh evaluates only enabled criteria.
- Non-interactive p2p init behavior remains scriptable and unchanged except for domain defaults.

### PROP-058 - Project README and Installation Guide

- README.md describes P2P Engine, principles, architecture, current status, quick start, and roadmap.
- docs/INSTALL.md documents installation from source with Python virtualenv.
- docs/INSTALL.md documents local MCP setup with PATH and explicit python -m alternatives.
- Documentation is honest that packaged/compiled CLI is future work.
- Docs reference p2p context, p2p assess, p2p assess maturity, and init wizard rubric selection.

### PROP-059 - P2PWorkspace Modular Refactoring Plan

- The proposal explicitly defines P2PWorkspace as a compatibility facade, not the long-term home for all behavior.
- The proposal identifies cli.py, storage/filesystem.py, and mcp/tools.py as compatibility/orchestration layers that should not receive unrelated new domain logic by default.
- The proposal chooses internal managers behind the stable facade over monolith-only documentation, mechanical split, or public API redesign.
- The first accepted deliverable is an architecture contract: AGENTS.md agent rules, docs/DEVELOPMENT-GUIDELINES.md, and a prioritized roadmap, with no runtime behavior change.
- The proposal records compatibility constraints for CLI commands, MCP tool names and payloads, .p2p storage artifacts, validation, registry refresh, consent receipts, Git/sync behavior, and owner-controlled governance.
- The proposal records consent/permissions as the preferred first future code extraction after accepted-proposal binding into local specs.
- The proposal requires service/use-case extraction before CLI modularization.
- The proposal identifies impact and overlap with permission-gated MCP governance, draft proposal decisions via MCP, next actions MCP/skill support, domain-aware project export, runtime bootstrap, and the local specs binding workflow.
- No source refactor is required merely to accept the proposal; implementation tasks are produced later through the local specs binding workflow.

### PROP-061 - Focused README and Documentation Map

- README.md is focused on the p2p-engine repository scope.
- README.md explains what P2P Engine is, what it enables, repository components, install, CLI usage, and agent usage.
- README.md includes a documentation map with short descriptions for each docs file.
- docs/CLI-GUIDE.md exists as a structured stub.
- docs/MCP.md exists as a structured stub.
- docs/AGENT-INTEGRATION.md exists as a structured stub.
- docs/API.md exists as a structured stub.

### PROP-062 - README Product Landing Page Refinement

- README starts with a one-line pitch.
- README contains Why, What it does, Who it is for, Status, 5-minute demo, Install, Core concepts, Docs, and Roadmap sections.
- README install example uses HTTPS clone first.
- README marks detailed docs as stable or WIP.

### PROP-064 - Spec Kit Three-Prompt Export Model

- Generic export writes project.md and propose.md as the primary output.
- project.md includes the required core sections: executive summary, vision, domain, problem, goals, non-goals, stakeholders, workflows, accepted decisions, requirements, constraints, assumptions, dependencies, operating model or architecture, data or knowledge model, priorities, success criteria, validation method, risks and tradeoffs, open questions, pending proposals, and source traceability.
- project.md includes domain-specific sections based on project rubrics or detected/declared domain.
- Every major project.md section distinguishes accepted evidence, pending/draft material, and missing information.
- Spec Kit export writes exactly speckit.constitution.md, speckit.specify.md, and speckit.plan.md as primary output.
- OpenSpec export writes propose.md as primary output.
- Exports avoid creating synthetic downstream folder layouts as the primary UX.
- Export validation checks required files, required project.md sections, target-specific files, and source traceability metadata.
- Docs explain that P2P exports are agent cognition and downstream initialization artifacts, not downstream tool execution.

### PROP-065 - MCP Agent-First Coverage Expansion

- MCP exposes the requested priority 1 read-only tools.
- MCP exposes the requested priority 2 write-safe deterministic tools.
- MCP exposes the requested priority 3 prompt/advisory tools.
- MCP still does not expose owner-controlled governance decisions, direct Git lifecycle operations, or import/apply commands.
- Tests cover tool definitions and representative calls for read-only, write-safe, and prompt/advisory additions.

### PROP-066 - Permission-Gated MCP Governance And Git Operations

- The proposal defines project-declared roles for owner, maintainer, contributor, agent, and readonly.
- The proposal specifies owner-name capture during project init and generic fallback identities such as owner and contributor.
- The proposal distinguishes actor_id, authorizer, and enforcer.
- The proposal states that local actor IDs are audit metadata, not strong authentication.
- The proposal states that cloud enforcement relies on Git provider permissions, branch protection, required approvals, and token scopes.
- The proposal defines tool classes: safe_read, write_safe_preparatory, privileged_publish, owner_controlled_governance, and destructive_or_external.
- The proposal requires consent receipts for privileged MCP operations and defines required receipt fields.
- The proposal requires single-use consent for merge, finalize, cleanup, destructive, or protected-branch operations.
- The proposal allows the safe MCP surface to remain available before privileged MCP implementation.
- The proposal defers external IAM/API-server authentication to a future enhancement while preserving compatibility.

### PROP-067 - Agent-First Setup Documentation Split

- README no longer presents manual CLI proposal creation as the primary 5-minute path.
- README frames setup as installing P2P Engine, initializing a separate target project, connecting an agent, and letting the agent use P2P.
- INSTALL focuses on using P2P for a new project and marks manual CLI commands as optional.
- CONTRIBUTING contains the instructions for contributors who want to use P2P to add proposals to the P2P Engine repository itself.
- README links to CONTRIBUTING for P2P Engine contributor setup without showing explicit contributor-agent examples.

### PROP-068 - Document Agent MCP Client Setup Commands

- INSTALL contains a copy-pastable Codex CLI MCP add command for a new target project.
- INSTALL contains a Claude Code MCP add command for a new target project.
- INSTALL contains a Claude Desktop local MCP JSON example for a new target project.
- INSTALL clearly says unverified desktop/IDE clients should use the same command/args through their MCP configuration UI.

### PROP-069 - Clarify MCP Stdio Integration Model

- MCP docs explain that stdio clients launch the server as a subprocess and that stdout must contain only MCP messages.
- Docs explain that multiple clients may create multiple MCP server processes and shared state must live in the repository/.p2p/Git/core storage.
- Docs state that a future shared multi-client service would use Streamable HTTP, not the current stdio process model.
- INSTALL client examples use the current Python module command and --root, not Node or P2P_ROOT placeholders.

### PROP-070 - Clarify README Agent Access Modes

- README lists CLI access and MCP access as distinct agent connection modes.
- README says MCP does not currently expose proposal accept/reject/defer, choice decide/block, spec import, Git branch/commit/push/PR/merge, or privileged Work lifecycle operations.
- README points to INSTALL and MCP docs for detailed setup and boundaries.

### PROP-071 - Custom Domain Definition Workflow

- p2p init can represent no-template/custom initialization without forcing the project into a predefined domain.
- All projects store explicit domain state and rubric state.
- Predefined domains are treated as templates that populate initial domain/rubric metadata.
- Custom or no-template initialization records unresolved domain/rubric setup.
- Custom or no-template initialization creates or recommends first activities: define the domain, then define the rubric.
- Maturity assessment does not report well_defined when rubric state is unresolved or criteria are missing.
- The workflow keeps mediator/agent domain synthesis outside core while preserving deterministic state in .p2p/.

### PROP-072 - Concurrent Managed Work and Merge Decision Model

- The proposal defines separate semantics for proposal branches and Work branches.
- The proposal specifies that main contains accepted project state only.
- The proposal defines lifecycle states for proposal branch collaboration.
- The proposal extends the Work lifecycle with candidate selection states for concurrent Work.
- The proposal defines CLI-level operations for proposal branch creation, status, publication, publication with safe auto-renumber, review request, acceptance, rejection, merge, conflict continuation/abort, retirement, and scan.
- The proposal defines CLI-level sync operations that wrap fetch, pull, push, and status without requiring users or routine agents to run raw Git.
- The proposal defines CLI-level operations for listing, comparing, selecting, rejecting, retiring, or combining competing Work candidates.
- The proposal requires proposal branch names to include a capped slug, actor slug, and hash-16 suffix.
- The proposal requires duplicate proposal ID validation and clear failure modes for ambiguous project state.
- The proposal requires publish-time collision recheck and safe auto-renumber behavior for concurrent proposal ID allocation.
- The proposal explains how local and cloud projects share lifecycle semantics while differing only in remote publication, review handoff, and final base-branch push.
- The proposal defines when a P2P Choice is required for competing proposal candidates.
- The proposal requires selected Work before accept when multiple candidates exist for the same Change Set.
- The proposal includes agent instruction requirements that hide raw Git from normal agent workflows.
- The proposal defines audit metadata required for proposal/work candidate decisions and merge outcomes.
- The proposal explicitly keeps permission-gated MCP exposure out of scope and delegates it to PROP-066.

### PROP-073 - Ergonomic Remote Project Initialization

- p2p init accepts remote profile options for cloud-backed projects without requiring a separate p2p project remote configure command.
- p2p init validates whether the configured Git remote exists and reports clear recovery guidance when it is missing or mismatched.
- p2p project remote configure remains available to modify mode, provider, remote name, and URL after init.
- p2p sync status reflects the initialized remote profile and explains readiness or blockers.
- Generated AGENTS.md and agent policy explain the selected repository mode and the no-raw-Git boundary.
- The MVP does not create external provider repositories; it only records profile metadata and validates local Git remote configuration.

### PROP-074 - Agent Runtime Bootstrap Robustness

- Generated AGENTS.md explains what to do when p2p is not found in PATH.
- Docs include cloud-agent setup and recovery steps for installing or invoking p2p.
- A diagnostic command or documented script can report p2p CLI, MCP server, Git repository, project root, and remote profile readiness.
- When p2p is unavailable, the recommended behavior remains stop-and-report, but the report includes exact recovery commands.
- Tests cover repository mode validation and runtime hint generation where practical.

### PROP-075 - MCP End-To-End Proposal Collaboration Workflow

- A documented MCP workflow exists for create proposal -> persist draft -> branch from base -> request consent -> publish -> request review.
- p2p_proposal_branch supports explicit base_branch or refuses unsafe branch chaining from another proposal branch.
- MCP can request or record pending consent without consuming it, while grant remains owner-controlled.
- MCP can configure or request correction of P2P remote profile metadata without manual .p2p edits.
- Dirty worktree errors after proposal create/update include a precise P2P recovery command.
- Tests cover branch base guardrails, consent-request lifecycle, and remote profile correction.

### PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

- Architecture documentation states that P2P Engine remains CLI/filesystem/Git/local-MCP, while P2P Cloud owns web/API/auth/UI/workflows/database.
- Cloud workflows are modeled as isolated runner jobs that invoke p2p CLI against a temporary Git checkout.
- Future proposals that add public web APIs or multi-tenant IAM directly to P2P Engine are rejected or reformulated as P2P Cloud proposals.
- The runner image requirements are clear: p2p engine installed, git installed, credentials injected per job, workspace mounted or cloned, no long-lived project daemon required.
- The boundary preserves Git and .p2p as the project audit/source-of-truth layer while allowing cloud DB indexing and job orchestration outside the engine.

### PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

- The CLI remains unchanged for direct owner decisions; MCP lists the new tools; requested consent cannot authorize draft decisions; granted matching consent authorizes and consumes the decision; docs and agent skill explain the distinction between draft proposal decisions and branch decisions.

### PROP-078 - Project-Local Wheel Installation and Upgrade Model

- A user can initialize or update a project-local .venv using a GitHub Release .whl without cloning or referencing a separate p2p-Engine source directory; docs clearly distinguish engine runtime upgrade from project repository sync; docs state GitHub wheel distribution is transitional and future public package publication is planned; post-upgrade refresh and validation commands are documented; no guidance suggests rerunning p2p init for existing projects.

### PROP-079 - Managed Next Action Lifecycle

- Users can add curated next actions through CLI; users can complete or retire curated actions through CLI without editing .p2p files; completed/retired actions are audited in next-actions-log.yml; p2p next shows curated and generated actions together; generated actions still appear even when curated actions exist; stale curated actions such as NEXT-003 can be completed; p2p validate remains clean and tests cover add, complete, retire, generated visibility, and deduplication.

### PROP-080 - Automated GitHub Release Wheel Publishing

- A .github/workflows/release.yml workflow exists and is triggered by v* tags; the workflow runs tests, p2p validate, and python -m build; the workflow uploads dist/*.whl and dist/*.tar.gz to the GitHub Release for the tag; documentation explains that maintainers should bump pyproject.toml, commit, push, tag, and push the tag; documentation warns not to reuse an existing version/tag; local release-how-to.md can remain a personal ignored fallback; p2p validate and the test suite pass.

### PROP-081 - MCP and Skill Support for Managed Next Actions

- MCP tool definitions include p2p_next_add, p2p_next_complete, p2p_next_retire, and p2p_next_refresh; tool handlers call the same workspace methods as the CLI; tests cover add, complete, retire, refresh, and log creation through MCP; docs/MCP and the p2p-engine skill describe the lifecycle; p2p validate and the test suite pass.

### PROP-082 - Readiness Assessment Refresh And Review Workflow

- Readiness review generates or updates questions that seek coverage across the full proposal artifact set, not only missing readiness criterion names.
- Question answers can be mapped to multiple affected artifacts, and apply behavior reports which artifacts should be updated or why no update is needed.
- Agent guidance defines stepped assertiveness from readiness score, label, failed gates, confidence, missing evidence, and question state rather than a standalone pedantry index.
- When readiness is weak, low-confidence, or gate-blocked, agent guidance requires the agent to initialize/update questions, ask the next focused question, record the answer, apply it, and recalculate readiness.
- Muted and deferred question or group states reduce re-asking by default while still allowing the owner to explicitly revisit them to increase readiness.
- Readiness recalculation after artifact refinement updates missing criteria, failed gates, confidence, suggested next actions, and acceptance cautions using current artifact evidence.
- Existing owner authority remains intact: agents may challenge, recommend, and prepare artifact updates, but cannot accept, reject, defer, merge, or aggregate proposals without owner-controlled governance actions.

### PROP-083 - Domain-Aware Visible Project Definition Export

- A default visible project-definition export generates a single chaptered Markdown file at outputs/latest/project.md.
- The default project document is domain-generic and does not require the project to be software-oriented.
- Each export refresh preserves prior generated output under deterministic review folders such as outputs/review-001 and outputs/review-002 before updating outputs/latest.
- Specialized vertical exports are written under outputs/latest/exports/<profile-or-vertical>/ and do not replace the default project.md output.
- Software-specific exports such as software-spec, OpenSpec, or Spec Kit are represented as nested export profiles, not as the default output shape.
- Existing .p2p/outputs behavior is inventoried and either preserved, mirrored, deprecated, or migrated through an explicit compatibility path before any removal.
- Generated outputs clearly indicate that .p2p remains the managed source of truth and outputs/ contains generated human-facing artifacts.

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

- A pure-data vertical pack schema is defined and validated, with required fields for vertical metadata, sections/capisaldi, minimal readiness rubrics, blocking questions, and expected artifacts.
- base_project is available as the universal fallback and existing projects without vertical packs continue to work with current project rubrics and maturity/readiness behavior.
- Default MVP vertical packs are loaded from internal package/project resources, while project-local custom packs can override or extend them.
- A project readiness review command, p2p project readiness review, reads vertical packs, project-local custom packs, existing rubrics/maturity state, and project context to identify missing capisaldi and generate prioritized project questions.
- Project readiness review produces a vertical skeleton summary that maps vertical sections/capisaldi to relevant proposals, accepted decisions, gaps, risks, and unmapped proposals.
- Generated agent/project instructions explain that missing initialization, capisaldi, or initial project questions are priority context work and guide the agent to propose, confirm, and refine project-local custom verticals.
- The first implementation slice includes one complete demonstration vertical and does not require the later five-vertical set, remote registry, or executable plugin verticals.
- The design remains registry-ready by keeping pack identity/version metadata and a loader boundary that can later support REST list/detail endpoints without changing project-local pack semantics.

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

- Proposal artifact state has a dedicated public CLI and/or MCP primitive for initializing, showing, and setting artifact expectation, status, rationale, actor/source, risk flags, and legacy absence.
- Artifact lifecycle supports at least unknown, missing, weak, satisfied, deferred, not_applicable, and absent_legacy, with clear scoring and context semantics for each state.
- Proposal readiness consumes artifact state and exposes coverage by artifact type, including whether each artifact is satisfied, weak, missing, optional, deferred, not applicable, unknown, or legacy-absent.
- The default artifact policy is graduated by risk: proposal.md, readiness.yml, and open-questions.md are always required; clarifications.md, findings.md, exploration.md, and impact-map.yml are required when applicable; findings.md and impact-map.yml become auto-required for governance, policy, architecture, compatibility, CLI, MCP, storage, persistent-state, permission, remote-sync, source-of-truth, agent-memory, or core workflow changes.
- Risk trigger detection is deterministic enough for agents and readiness: high uncertainty, multiple credible alternatives, cross-module impact, public interface changes, persistent state changes, compatibility/migration impact, permission/security/sync concerns, or evidence-dependent claims raise artifact expectations rather than relying on ad hoc agent judgment.
- Artifact-aware readiness is the default for newly created proposals.
- Existing proposals without artifact-aware state are marked or reported as absent_legacy through P2P CLI/MCP state, with advisory gaps or migration recommendations only; validation does not error, proposal decisions are not blocked, and manual retroactive completion is not required.
- Agents may propose artifact status, but owner authority remains explicit: not_applicable or deferred states for always-required or auto-required artifacts are visible to the owner and cannot be silently treated as equivalent to satisfied.
- Compact proposal context surfaces applicable empty artifacts as next-step gaps instead of hiding them behind the main proposal summary, and shows not-applicable, deferred, unknown, and absent_legacy reasons when present.
- Agent instructions include a pre-acceptance artifact review workflow that shows artifact coverage, asks focused owner questions one at a time, avoids fake artifact filling, and refuses direct managed-file edits when no public primitive exists.
- All P2P memory mutations for artifacts go through p2p CLI commands or explicit write-safe MCP tools backed by the P2P engine write path; direct .p2p edits, copying temporary files into artifacts, and reverse-engineered filesystem writes are out of scope and forbidden.
- Tests or documented scenarios cover simple new proposals, risk-triggered proposals, legacy absent state, not_applicable rationale, deferred owner visibility, readiness/context integration, MCP write-safe behavior, and missing-primitive refusal.

### PROP-087 - Agent Personality Model For Decision Mediation

- Project-level interaction_style is stored as the first implementation scope with no per-agent or session override in the first slice.
- The model validates technical_verbosity, formality, and assertiveness as integers from 0 to 5.
- Missing interaction_style configuration falls back to technical_verbosity=2, formality=2, and assertiveness=0 without breaking existing projects.
- Users and agents can read the project interaction style through a public CLI command under project interaction-style.
- Users and agents can update the project interaction style through a public CLI command under project interaction-style with validation and actionable errors.
- MCP exposes explicit read-only and write-safe tools for project interaction style status and update operations.
- Generated agent instructions and project/local skills explain how to inspect and update interaction style through CLI/MCP and prohibit direct .p2p edits for this state.
- Rendered agent guidance translates numeric values into concrete communication behavior for technical verbosity, formality, and assertiveness.
- Persisted named presets are not introduced; scales remain the source of truth and any labels are non-authoritative help text only.
- Tests cover defaults, validation bounds, CLI show/set, MCP status/update, generated instruction text, missing-config fallback, and no-direct-write guidance.

## Alternatives And Tradeoffs

### PROP-002 - Proposal Exploration And Readiness Workflow

#### alternatives.md

# Alternatives - PROP-002

## Context

PROP-002 is not only about adding an `explore` command. The deeper product
problem is that P2P Engine must prevent proposals from moving too quickly from a
generic idea to an accepted direction without enough questioning, comparison,
risk analysis, owner input, and scope definition.

The alternatives below compare different ways to make proposal exploration a
real decision-support workflow instead of a passive artifact scaffold.

## Alternative A - Strict Completeness Gate

Require every proposal to have all exploration artifacts meaningfully populated
before it can be considered mature:

- `exploration.md`
- `findings.md`
- `alternatives.md`
- `open-questions.md`
- `risks.md`
- `assumptions.md`
- `suggested-scope.md`

The agent must inspect these artifacts and challenge missing, empty, or generic
content before recommending acceptance or implementation.

Pros:

- Simple rule to explain and enforce.
- Makes the existing proposal artifact structure operationally meaningful.
- Reduces the chance that important concerns stay only in chat.
- Encourages consistent proposal records across the project.

Cons:

- Can become bureaucratic for small or obvious proposals.
- May produce decorative text if the agent optimizes for "all files filled"
  instead of useful exploration.
- Does not by itself define whether the content is good enough.

Best fit:

- Governance-critical, architectural, or high-impact proposals where the cost of
  weak exploration is high.

## Alternative B - Proposal Readiness Gate

Introduce an explicit readiness workflow, for example:

```text
draft -> explored -> ready_for_decision -> accepted/rejected/deferred
```

A proposal cannot become `ready_for_decision` while key exploration gaps remain,
such as missing alternatives, unresolved owner questions, unclear assumptions,
unassessed risks, or absent acceptance criteria.

`p2p next` should report specific readiness gaps instead of only saying that a
draft proposal should be reviewed.

Pros:

- Directly addresses the current weakness in `next` recommendations.
- Separates "draft exists" from "proposal is ready to decide".
- Gives agents a concrete workflow to follow.
- Can make proposal review more repeatable and auditable.

Cons:

- Requires new state, checks, or derived readiness logic.
- Needs careful governance boundaries so agents do not decide readiness in place
  of the owner.
- May require migration or interpretation for existing proposals.

Best fit:

- Core P2P Engine workflow because readiness is central to turning discussion
  into trustworthy decisions.

## Alternative C - Agent Interrogation Protocol

Define explicit agent behavior for proposal exploration. The agent should be
instructed to be deliberately demanding before allowing an idea to harden into a
proposal:

- Do not accept the first generic formulation as sufficient.
- Ask targeted questions about ambiguity, constraints, edge cases, and user
  intent.
- Separate desired outcome from implementation approach.
- Identify assumptions that are being silently made.
- Generate and compare alternatives, including smaller and more structural
  options.
- Look for overlap, conflict, or duplication with existing proposals.
- Ask the owner for real governance decisions instead of inventing them.
- Capture unresolved questions instead of smoothing them over.

Pros:

- Improves the quality of AI-assisted proposal development immediately.
- Fits the current Codex skill and MCP-agent direction.
- Makes the agent more useful as a critical collaborator, not just a summarizer.
- Can be implemented first as instructions and later enforced by CLI/MCP checks.

Cons:

- If implemented only as prose instructions, compliance may be inconsistent.
- Different agents may apply the protocol with different levels of rigor.
- Without readiness checks, the protocol may not reliably affect `p2p next`.

Best fit:

- Agent-facing workflows, MCP clients, Codex skill behavior, and prompt
  generation.

## Alternative D - Alternatives-First Proposal Model

Require non-trivial proposals to identify at least two or three plausible
directions before recommending one. Example pattern:

```text
A - minimal implementation
B - structured workflow
C - agent-first / MCP-first workflow
```

Each option should be compared on cost, risk, product impact, implementation
complexity, governance effect, agent ergonomics, and future extensibility.

Pros:

- Forces real choice rather than documenting the first solution.
- Helps the owner understand tradeoffs before deciding.
- Makes sub-optimal choices acceptable when chosen consciously for pragmatic
  reasons.
- Creates a stronger basis for future precedent and conflict analysis.

Cons:

- Can feel heavy for routine maintenance work.
- Requires the agent to invent alternatives responsibly without overcomplicating
  simple problems.
- Needs a way to distinguish meaningful alternatives from artificial ones.

Best fit:

- Product, governance, architecture, MCP surface, agent behavior, and lifecycle
  proposals.

## Alternative E - Tiered Exploration Model

Classify proposals by required exploration depth, for example:

```text
small / routine
medium / product
large / architectural
governance-critical
```

The higher the tier, the more exploration artifacts become required or strongly
recommended. A small documentation fix may need only a concise proposal and risk
note; a governance or agent-workflow proposal should require alternatives,
risks, assumptions, open questions, and explicit suggested scope.

Pros:

- Avoids unnecessary bureaucracy for small changes.
- Allows strictness where it matters most.
- Gives `p2p next` a basis for targeted refinement prompts.
- Makes the exploration workflow scalable across project sizes.

Cons:

- The tiering rules must be clear or agents may classify too many proposals as
  small.
- Adds one more decision point before exploration.
- Needs owner override when the apparent size of a proposal hides strategic
  importance.

Best fit:

- Projects that need both lightweight iteration and serious governance for
  important decisions.

## Alternative F - Hybrid Exploration And Readiness Model

Combine the strongest parts of the previous alternatives:

- Keep exploration artifacts as the durable proposal memory.
- Add readiness checks for missing or weak exploration dimensions.
- Instruct agents to interrogate proposals actively and persistently.
- Require alternatives for non-trivial proposals.
- Use tiers to avoid forcing full ceremony on every tiny change.
- Make `p2p next` surface concrete refinement gaps.

The intended workflow becomes:

```text
rough idea -> explored draft -> readiness gaps -> owner questions -> alternatives
comparison -> suggested scope -> ready for decision
```

Pros:

- Addresses the actual observed failure mode from multiple angles.
- Gives both humans and agents a clearer path from idea to decision.
- Preserves lightweight operation for simple proposals while strengthening core
  product and governance work.
- Makes the existing proposal files useful instead of optional decoration.

Cons:

- More complex than a single command or single artifact rule.
- Requires careful implementation sequencing.
- Needs good documentation and skill/MCP alignment to avoid confusing agents.

Best fit:

- Recommended direction for PROP-002 because proposal exploration is central to
  P2P Engine's value.

## Cross-Cutting Comment - Multi-Criteria Decision Support

The alternatives should not only list pros and cons. P2P Engine should consider
a lightweight value or scoring system that derives an impact measure from the
pros and cons across the analyzed dimensions.

This could work like a multi-criteria analysis model where each alternative is
evaluated against explicit criteria such as:

- product impact
- implementation cost
- governance clarity
- agent ergonomics
- risk reduction
- documentation burden
- future extensibility
- migration complexity

The goal is not to force the mathematically "best" option. The goal is to help
the owner choose consciously. A user may intentionally select a sub-optimal
alternative because it is cheaper, faster, easier to explain, or better aligned
with current project constraints. The important point is that the tradeoff is
visible, recorded, and auditable.

This scoring model should remain advisory. It must support owner judgment, not
replace governance decisions.

#### findings.md

# Findings - PROP-002

## Existing Findings

```yaml
findings:
  - id: F001
    type: hidden_decision
    title: Exploration as repeatable phase
    impact: high
    related_to:
      - workflow
      - proposal_lifecycle

  - id: F002
    type: architectural_principle
    title: CLI engine remains source of truth
    impact: high
    related_to:
      - cli
      - agent_skills
      - filesystem_storage
```

## New Findings From Review

### F003 - Proposal maturity should be measurable

Proposal readiness should not be only a binary or informal state. A proposal can
have a formal maturity value from 0 to 100, computed from defined exploration
criteria.

### F004 - Pedantry should relax by maturity threshold

Agent strictness should be tied to maturity thresholds. The owner suggested
step thresholds at 70, 85, and 95.

### F005 - Computed readiness and owner override must be separate

Owner override should not falsify the computed score. The analytical score and
the governance decision must remain separate.

### F006 - Readiness should complement proposal lifecycle state

The design should not replace proposal lifecycle state with readiness. It should
combine both procedural state and analytical quality.

### F007 - Maturity is advisory unless owner-controlled policy says otherwise

The maturity score should guide the agent and improve `p2p next`, but it should
not silently replace owner decisions.

### F008 - Multi-criteria analysis can support maturity and decision quality

The maturity score and the alternatives comparison can share a multi-criteria
model that makes tradeoffs visible without replacing owner judgment.

### F009 - Score alone is not enough

A total score can hide essential weaknesses if strong secondary areas compensate
for missing critical dimensions. The readiness model should combine total score,
minimum gates, confidence, evidence, artifact quality gates, and override
metadata.

### F010 - Minimum gates are required for important proposals

For medium, architectural, and governance-critical proposals, certain criteria
must meet minimum quality thresholds.

### F011 - Confidence should be separate from score

A proposal can be well documented but based on fragile assumptions. Readiness
should include confidence and confidence reasons.

### F012 - Criterion scores need evidence

Each criterion score should point to the artifacts or sections that justify it.

### F013 - Artifact quality must cap criterion scoring

If an artifact is placeholder or thin, related criteria should be capped.

### F014 - `p2p next` should show delta to target

`p2p next` should estimate the gap to the target score and suggest the
highest-impact refinement actions.

### F015 - PROP-002 is governance-critical

PROP-002 defines how future proposals are explored, evaluated, and moved toward
decision. It is therefore governance-critical.

### F016 - Readiness must be profile-based and versioned

The 10-criterion model is the first default profile, not a hardcoded permanent
model. Every readiness assessment must record the profile id and version used to
compute it.

### F017 - Markdown remains authored, structured data remains machine-facing

Human-readable artifacts should remain authored in Markdown. Machine-readable
readiness data should live in metadata, readiness snapshots, registries,
exports, or audit records.

### F018 - Owner override is a governance event

Override is not a score edit. It creates an audited governance event such as
`accept_with_override`, preserving the computed score and recording reason,
authority, and failed gates.

### F019 - Governance gates must be configurable

The final product model must support warnings, hard gates, override policies,
reason requirements, and different behavior by governance profile, proposal
tier, and failure type.

### F020 - Open drafts should adopt readiness immediately

New proposals and current open drafts should use readiness. Already accepted
proposals should preserve historical decisions and use legacy markers or
optional retrospective assessment.

### F021 - Hybrid assessment is the right product model

The engine should validate, cap, aggregate, gate, and store readiness. Agents
should provide qualitative assessment, evidence, notes, confidence reasons, and
recommendations. The agent should not produce an opaque final score.

### F022 - MCP write operations are governance-gated, not merely deferred

Read tools can be agent-accessible. Write/governance operations such as
readiness override or accept-with-override are part of the product model, but
must require explicit governance permission and must not be agent-autonomous.

### F023 - Readiness override belongs primarily to acceptance

The primary UX should be `p2p proposal accept --override-readiness --reason`.
This communicates that the owner is accepting despite readiness gaps. A
standalone readiness override risks implying that computed readiness is being
modified.

### F024 - `needs_owner_input` is a first-class artifact state

`needs_owner_input` is different from `thin`. An artifact can be specific and
useful but blocked because only the owner can choose a policy, strictness level,
or strategic direction.

### F025 - Current unresolved-question counting is semantically weak

`p2p explore status` can report a different unresolved count than the number of
implementation decision points visible in `open-questions.md`. Future status and
readiness logic should distinguish explicit questions, decision items, grouped
subtopics, and artifact quality states.

### PROP-004 - Prompt-only Import Workflow

#### alternatives.md

# Alternatives - PROP-004

None identified yet.

#### findings.md

findings: []

### PROP-005 - Codex Skill Integration

#### alternatives.md

# Alternatives - PROP-005

None identified yet.

#### findings.md

findings: []

### PROP-006 - Multi-Agent Integration Model

#### alternatives.md

# Alternatives - PROP-006

PROP-006 is no longer about inventing basic agent profiles from scratch. P2P
Engine already supports generated instructions for `generic`, `codex`, and
`claude`. The remaining product question is how far to evolve those profiles
into governed, inspectable, updateable integrations.

## Alternative A - Keep Lightweight Instruction Profiles

Keep the current model and add only small inspection commands.

Candidate commands:

```bash
p2p agent list
p2p agent show codex
p2p agent instructions refresh --profile cursor
```

Pros:

- Lowest implementation risk.
- Fits the current code.
- Avoids lifecycle machinery.

Cons:

- Does not record which files were generated.
- Cannot safely update or uninstall generated files.
- Does not distinguish a supported profile from an installed integration.
- Leaves manual drift invisible.

Assessment:
Useful as an incremental baseline, but too weak for a durable multi-agent
model.

## Alternative B - Agent Integration Registry

Introduce a first-class registry of installed agent integrations:

```text
.p2p/agent-integrations.yml
```

The registry records installed adapters, generated files, template versions,
hashes, shared files, drift status, and installation status. It does not choose
an active/default/preferred agent.

Candidate commands:

```bash
p2p agent list
p2p agent show <agent>
p2p agent install <agent|all>
p2p agent update <agent|all>
p2p agent doctor <agent|all>
p2p agent uninstall <agent>
```

Pros:

- Makes installed integrations visible.
- Enables drift detection.
- Enables safe update and safe uninstall.
- Supports multiple collaborators using different agents.
- Keeps P2P Engine as the source of truth for generated agent artifacts.

Cons:

- Adds schema and lifecycle complexity.
- Requires clear rules for shared files such as `AGENTS.md`.
- Requires hash and ownership semantics.

Assessment:
This is the strongest MVP foundation.

## Alternative C - Registry Plus Active Agent

Add an active/default/preferred agent to Alternative B.

Candidate commands:

```bash
p2p agent use codex
p2p agent current
p2p agent switch claude
```

Pros:

- Useful when a project wants one primary agent surface.
- Can improve setup hints for single-agent usage.

Cons:

- Adds state the owner does not need.
- Can imply that one agent is preferred project-wide.
- Does not match teams where different contributors use different agents.
- Requires extra commands such as `use`, `current`, and possibly `--no-use`.

Assessment:
Rejected for the MVP. P2P should support installed integrations, not select a
project-level favorite agent.

## Alternative D - Adapter-Specific Integration Model

Model each supported agent as an adapter with file targets and capabilities.

Initial adapters:

```text
generic
codex
claude
cursor
copilot
gemini
opencode
```

Indicative target files:

```text
generic   -> AGENTS.md
codex     -> AGENTS.md, .codex/skills/p2p-project/SKILL.md
claude    -> AGENTS.md, CLAUDE.md
cursor    -> AGENTS.md, .cursor/rules/p2p.mdc
copilot   -> AGENTS.md, .github/copilot-instructions.md
gemini    -> AGENTS.md, GEMINI.md
opencode  -> AGENTS.md, optionally opencode.json
```

Pros:

- Represents real differences between tools.
- Avoids assuming that every agent reads the same files.
- Allows capability-specific guidance such as MCP support, local command
  support, skill support, and permission model.

Cons:

- Tool conventions change over time.
- Requires documentation checks and adapter versioning.
- Some integrations may be advisory because the external tool does not provide
  strong enforcement.

Assessment:
This should be combined with Alternative B for a serious MVP.

## Alternative E - External Integration Packages

Allow external adapter packages from local paths, Git repositories, or URLs.

Candidate commands:

```bash
p2p agent install custom --from ./my-agent-adapter.yml
p2p agent update all
```

Pros:

- Highly extensible.
- Allows community-maintained adapters.

Cons:

- Larger security surface.
- Requires adapter validation and trust model.
- Premature for the current project.

Assessment:
Defer. Keep adapter definitions internal until the core lifecycle is stable.

## Recommended Direction

Adopt a hybrid of Alternatives B and D:

```text
Agent Integration Registry MVP
```

The MVP should promote existing agent profiles into governed integrations with:

- `.p2p/agent-integrations.yml`;
- no project-level active/default/preferred agent;
- baseline `generic` always present;
- install/list/show/update/doctor/uninstall commands;
- `p2p agent install all` when adapter file targets do not conflict;
- adapter-specific file targets;
- generated file hashes;
- safe update and safe uninstall rules;
- coexistence of multiple installed agents.

External adapter packages remain out of scope for the first implementation.

#### findings.md

# Findings - PROP-006

## F001 - Basic Agent Profiles Already Exist

P2P Engine already implements `generic`, `codex`, `claude`, and `all` profiles.
The current implementation can generate `AGENTS.md`, `CLAUDE.md`,
`.codex/skills/p2p-project/SKILL.md`, and `.p2p/agent-policy.yml`.

Impact:
PROP-006 should not be framed as introducing profiles from zero. It should
focus on lifecycle management for installed integrations.

## F002 - Project Init Should Install All Supported Project-Local Adapters

The owner does not want P2P to choose one default agent. A project can safely
support several agent tools at once as long as their generated files do not
overwrite each other.

Impact:
Default init should install all supported project-local adapters. Narrower
installation remains available when the owner wants fewer generated files.

## F003 - The Missing Layer Is Installation State

The current model can generate instructions but does not record which files were
generated, which template version produced them, whether they changed, or
whether they can be updated or removed safely.

Impact:
The main missing artifact is `.p2p/agent-integrations.yml`.

## F004 - Agent Files Are Not Interchangeable

Different tools consume different project-local instruction files:

- Codex reads `AGENTS.md` and supports repo-scoped skills.
- Claude Code project memory supports `CLAUDE.md`.
- Cursor uses project rules in `.cursor/rules` and also supports `AGENTS.md`.
- GitHub Copilot uses `.github/copilot-instructions.md`.
- Gemini CLI uses `GEMINI.md`.
- OpenCode supports `AGENTS.md` and can use `opencode.json` for additional
  instruction paths or permissions.

Impact:
P2P needs adapter definitions rather than a single generic output file.

## F005 - AGENTS.md Is The Shared Baseline

`AGENTS.md` should remain the cross-agent baseline because it is readable by
humans, generic agents, and several modern agent tools. Tool-specific files
should supplement it only where they provide better integration.

Impact:
`AGENTS.md` is a shared managed file and needs special uninstall/update rules.

## F006 - Safe Update Requires Hashes

Without stored hashes P2P cannot distinguish:

- generated file unchanged;
- generated file manually edited;
- generated file stale because template changed;
- unmanaged file with the same path.

Impact:
Every managed generated file needs a stored hash and ownership metadata.

## F007 - No Active Agent Is Needed

The project owner does not need P2P to choose whether a contributor uses Codex,
Claude, Cursor, Copilot, Gemini, or OpenCode. Integrations should be installed
because somebody needs them, and multiple integrations should coexist.

Impact:
Do not introduce `active_agent`, `default_agent`, `preferred_agent`,
`p2p agent use`, `p2p agent current`, or `install --no-use` in the MVP.

## F008 - Existing Implementation Should Be Migrated, Not Replaced

The current `p2p agent instructions refresh` behavior should remain compatible.
New install/update commands can call the same rendering logic while recording
registry metadata.

Impact:
PROP-006 can be implemented incrementally without breaking existing projects.

## F009 - MCP And CLI Are Peer Interfaces Over P2P Core

MCP does not teach agents how to use the CLI. MCP exposes P2P Engine
capabilities as structured tools for MCP-compatible agents. Generated
instructions still explain when to use CLI, when to use MCP, what order to
follow, and which governance boundaries apply.

Impact:
PROP-006 should instruct agent profiles to describe operating-channel
preference:

- if MCP is configured, prefer MCP tools for structured P2P operations;
- otherwise use CLI when shell access exists;
- otherwise ask the user to run the required P2P command.

CLI and MCP behavior must share the same underlying core semantics.

## F010 - `.agents/skills` Is Potentially Shared

Codex supports repo-scoped skills from `.agents/skills`. OpenCode documentation
also describes loading skills from `.agents/skills`.

Impact:
Any file generated under `.agents/skills` must be agent-neutral. Do not put
Codex-only behavior in a shared skill path. If Codex-specific behavior is still
needed, preserve existing `.codex/skills` behavior as a compatibility/migration
matter rather than using it as the general shared adapter path.
## F011 - Agent Incisiveness Is A Method Behavior Problem

The observed weakness is not mainly that one agent lacks a better technical
profile. It is that P2P's method instructions do not yet force agents to turn
readiness gaps into concrete refinement work.

An agent profile answers "where do instructions go and which tools can this
agent use?" The method policy answers "what should the agent do when the
proposal is weak?" The second question belongs in the generic baseline and must
be inherited by all generated agent files.

## F012 - Readiness Must Become Operational For Agents

Readiness currently gives a score, label, failed gates, missing items, and
suggested next actions. Agents can still stop at diagnosis unless instructions
and future commands guide them through a refinement loop.

The desired loop is:

```text
readiness gap
  -> required refinement action
  -> candidate alternatives
  -> recommendation
  -> owner decision
  -> proposal update
  -> readiness re-check
```

## F013 - Generated Instructions Must Include Gap Handling

Every generated agent file should preserve a common rule:

```text
Do not stop at identifying gaps. For each failed readiness gate, explain the
failure, propose alternatives, recommend one when justified, identify the owner
decision, draft the concrete update, and re-check readiness after refinement.
```

This is a generic P2P behavior and should not live only in the Codex adapter.

## F014 - Remaining Questions Can Be Closed With Conservative MVP Defaults

The remaining questions do not require more product discovery. They can be
settled with conservative implementation defaults:

- versioned `.p2p/agent-integrations.yml`;
- built-in package templates;
- SHA-256 over exact bytes;
- managed Markdown header as a human hint;
- conservative migration that never overwrites unknown or drifted files;
- future readiness refinement commands under `p2p proposal readiness`.

Impact:
PROP-006 can move toward decision once these defaults are recorded, even if
small internal names change during implementation.

### PROP-009 - Governance CLI Commands

#### alternatives.md

# Alternatives - PROP-009

None identified yet.

#### findings.md

findings: []

### PROP-010 - P2P Project State Model

#### alternatives.md

# Alternatives - PROP-010

## Alternative A - Export raw proposals directly

Export each accepted proposal directly to OpenSpec or Spec Kit.

Pros:

- Fast to implement.
- Simple mental model.
- Useful for small software-only proposals.

Cons:

- Leaks governance/discussion artifacts into implementation specs.
- Forces each exporter to understand P2P proposal complexity.
- Poor fit for proposals that are methodological, strategic, or mixed-domain.

## Alternative B - Generate P2P-native software specs first

Generate a normalized software specification under `.p2p/outputs/software-spec/`, then export that normalized model to external targets.

Pros:

- Keeps P2P as source of truth.
- Makes exporters simpler and more reliable.
- Separates decision history from implementation-facing specs.
- Supports future internal task tracking.

Cons:

- Requires defining a new P2P spec model.
- Adds one more transformation step.

## Alternative C - Adopt OpenSpec or Spec Kit as the internal model

Use OpenSpec or Spec Kit as the primary specification format and treat P2P as a proposal intake layer.

Pros:

- Reuses existing conventions.
- Faster path to software implementation.

Cons:

- Makes P2P dependent on a downstream tool.
- Weakens P2P's multi-domain and governance-first identity.
- Makes non-software proposals awkward.

## Preferred Direction

Alternative B. P2P Engine should generate a neutral internal software specification first, then export downstream selectively.

#### findings.md

findings:
  - id: F001
    type: architectural_boundary
    title: "P2P proposal is not a software spec"
    impact: high
    summary: >
      A P2P proposal contains discussion, governance, alternatives, and decision
      context. It must be rationalized before it becomes an implementation-facing
      software specification.
  - id: F002
    type: output_model
    title: "Rationalized project state needs a dedicated directory"
    impact: high
    summary: >
      Derived artifacts should live under .p2p/project so they are clearly
      separated from source proposal artifacts while representing the official
      rationalized project state.
  - id: F003
    type: downstream_export
    title: "OpenSpec and Spec Kit consume normalized specs"
    impact: high
    summary: >
      Exporters should consume P2P-native software specs, not raw proposal folders.
  - id: F004
    type: workflow_trigger
    title: "Accepted proposals should refresh outputs"
    impact: medium
    summary: >
      The system should refresh output artifacts when decisions are accepted,
      starting with an explicit p2p project refresh command and later optional
      automatic refresh.
  - id: F005
    type: conflict_memory
    title: "Mutually exclusive proposals need persistent conflict memory"
    impact: high
    summary: >
      When proposals are alternatives, accepting one should mark the others as
      rejected, superseded, or not selected. The project layer should preserve
      the conflict group and final choice.

### PROP-011 - Project Refresh MVP

#### alternatives.md

# Alternatives - PROP-011

None identified yet.

#### findings.md

findings: []

### PROP-012 - Impact Map and Conflict Memory

#### alternatives.md

# Alternatives - PROP-012

None identified yet.

#### findings.md

findings:
  - id: F001
    type: impact_analysis
    title: "Proposal impact needs structured artifacts"
    impact: high
    summary: >
      P2P needs proposal-level impact-map.yml artifacts to describe affected
      features, commands, files, governance rules, outputs, dependencies, and risks.
  - id: F002
    type: conflict_memory
    title: "Conflicts must survive the decision"
    impact: high
    summary: >
      Mutually exclusive or competing proposals should be preserved in
      .p2p/project/conflicts.yml so future proposals can be checked against
      already decided alternatives.
  - id: F003
    type: human_governance
    title: "Detection is advisory, decision remains human"
    impact: medium
    summary: >
      The CLI and AI can detect overlaps and suggest conflicts, but should not
      automatically reject proposals in the MVP.

### PROP-013 - Managed Git Adapter and Change Set Model

#### alternatives.md

# Alternatives - PROP-013

## Alternative A - Proposal Always Creates Branch

Every proposal gets a dedicated Git branch.

Pros:

- Strong isolation.
- Easy review of file diffs per proposal.
- Simple policy.

Cons:

- Too many branches for small ideas.
- Operational overhead.
- Proposal and branch become overly coupled.
- Historical memory can be dispersed if branches are deleted.

## Alternative B - Proposal Never Creates Branch

All proposals live only as `.p2p/` artifacts on the current branch.

Pros:

- Simpler CLI.
- Less Git overhead.
- Proposal registry remains centralized.

Cons:

- Weak isolation for controversial or complex proposals.
- Harder collaboration for concurrent proposal work.
- Harder review of project-state preview changes.

## Alternative C - Hybrid Proposal/Change Set Model

Proposals live in `.p2p/`. Branches are optional for proposals and recommended or required for operational change sets.

Pros:

- Keeps proposal as decision unit.
- Keeps Git as audit/collaboration layer.
- Reduces branch clutter.
- Allows formal branch workflow when implementation starts.

Cons:

- Requires branch policy criteria.
- Requires a new change-set abstraction.

## Alternative D - Managed Git Under The Hood

Users work only with P2P concepts. P2P Engine applies Git operations internally according to `git_policy.yml`.

Pros:

- Best user experience for non-Git users.
- Keeps Git-native auditability and portability.
- Removes arbitrary user-facing branch decisions.
- Lets AI agents use the P2P public interface instead of direct Git commands.
- Preserves advanced/debug visibility through verbose and doctor commands.

Cons:

- Requires a Git adapter.
- Requires careful safety rules for automatic commits/branches/tags.
- Debugging internal Git state needs explicit tooling.

## Preferred Direction

Alternative D.

Alternative C is still conceptually useful, but the user-facing model should be managed Git under the hood rather than exposing branch decisions as a normal workflow concern.

#### findings.md

findings:
  - id: F001
    type: conceptual_boundary
    title: "Proposal is not branch"
    impact: high
    summary: >
      A proposal is a decision unit stored in P2P artifacts. A Git branch is an
      optional workspace for isolation, review, or implementation.
  - id: F002
    type: missing_abstraction
    title: "Change Set is the operational unit"
    impact: high
    summary: >
      Accepted proposals should flow into change sets before implementation.
      Change sets can group multiple proposals and decisions into one operational
      package.
  - id: F003
    type: workflow_risk
    title: "Visible branch decisions create process variance"
    impact: high
    summary: >
      If users decide branch usage ad hoc, the workflow becomes inconsistent and
      too technical. Branch/commit/merge decisions should be managed internally
      by policy.
  - id: F004
    type: git_boundary
    title: "P2P memory must survive branch deletion"
    impact: high
    summary: >
      Proposal, decision, impact, conflict, and change-set history must live in
      .p2p artifacts, not only in Git branch history.
  - id: F005
    type: user_experience
    title: "Git should be internal by default"
    impact: high
    summary: >
      Users should operate with P2P concepts: proposal, choice, decision, change,
      and task. Git details should appear only in verbose/debug/doctor flows.
  - id: F006
    type: ai_instruction
    title: "AI agents should use P2P CLI instead of direct Git"
    impact: high
    summary: >
      Codex/Claude-style agents should call P2P commands and avoid manual Git
      branch/commit manipulation unless explicitly operating in debug or repair mode.

### PROP-014 - Change Set Metadata MVP

#### alternatives.md

# Alternatives - PROP-014

None identified yet.

#### findings.md

findings:
  - id: F001
    type: implementation_slice
    title: "Change Set MVP should be metadata-only"
    impact: high
    summary: >
      The first Change Set implementation should generate .p2p/changes metadata
      without mutating Git.
  - id: F002
    type: guardrail
    title: "Change Sets require accepted sources"
    impact: high
    summary: >
      Draft proposals must not create operational Change Sets. Accepted proposals
      or accepted decisions are required.
  - id: F003
    type: git_policy
    title: "Git policy is recorded, not executed"
    impact: high
    summary: >
      git-policy.yml records managed metadata-only behavior: no automatic
      commits, branches, tags, or merges.

### PROP-015 - Change Set Lifecycle and Task Tracking

#### alternatives.md

# Alternatives - PROP-015

None identified yet.

#### findings.md

findings:
  - id: F001
    type: lifecycle
    title: "Change Set lifecycle is separate from proposal status"
    impact: high
    summary: >
      Proposals decide project intent. Change Sets track operational execution.
  - id: F002
    type: validation
    title: "Lifecycle transitions must be constrained"
    impact: high
    summary: >
      Invalid jumps such as proposed to completed should be rejected to preserve
      reliable execution tracking.
  - id: F003
    type: execution_tracking
    title: "Tasks and actions need inspection commands"
    impact: medium
    summary: >
      Users need to see Change Set tasks and checklist actions without opening
      YAML files manually.

### PROP-016 - Project Registries MVP

#### alternatives.md

# Alternatives - PROP-016

## Alternative A - Continue Scanning Folders

Commands discover proposals, decisions and changes by scanning `.p2p/` directories every time.

Pros:

- No extra generated files.
- Simple in the short term.

Cons:

- Scales poorly.
- Makes prompt generation and exporters more ad hoc.
- Harder to inspect relationships globally.

## Alternative B - Single Global Registry

Create one large `.p2p/registry.yml`.

Pros:

- One file to inspect.
- Simple first implementation.

Cons:

- Can become large and conflict-prone.
- Mixes unrelated concerns.
- Harder to update incrementally.

## Alternative C - Typed Registries

Create `.p2p/registries/` with separate files for proposals, decisions, changes, choices, relations and artifacts.

Pros:

- Clear ownership by concern.
- Easier to inspect and regenerate.
- Better input for AI prompts and exporters.
- Lower conflict surface than one giant file.

Cons:

- More files to manage.
- Requires refresh/status commands.

## Preferred Direction

Alternative C.

#### findings.md

findings:
  - id: F001
    type: derived_index
    title: "Registries should be derived, not primary"
    impact: high
    summary: >
      Registries should index source artifacts but never replace proposal,
      decision, change, or governance files as source of truth.
  - id: F002
    type: navigation
    title: "Project navigation needs compact indexes"
    impact: high
    summary: >
      As .p2p grows, commands and AI agents need compact registry files instead
      of scanning every artifact for every workflow.
  - id: F003
    type: ai_context
    title: "Registries improve AI context loading"
    impact: medium
    summary: >
      Prompt generation and future AI adapters can load registries first, then
      selectively open relevant artifacts.
  - id: F004
    type: exporter_support
    title: "Exporters need stable lookup inputs"
    impact: medium
    summary: >
      Markdown, OpenSpec, Spec Kit and task-board exporters should consume
      registry indexes plus selected source artifacts.

### PROP-017 - Proposal Intake and Context Analysis MVP

#### alternatives.md

# Alternatives - PROP-017

## Alternative A - Manual Intake Only

Users and agents manually inspect `p2p status`, registries and proposal files before creating new proposals.

Pros:

- no new CLI surface;
- simple to understand;
- useful while project is small.

Cons:

- does not scale;
- easy to miss overlaps or accepted decisions;
- weak support for multi-agent collaboration.

## Alternative B - Prompt-Only Intake

The CLI gathers registry/project context and generates an intake prompt. AI output is imported back into `.p2p/intake/`.

Pros:

- fits current MVP architecture;
- no direct AI adapter required;
- keeps auditability;
- lets agents reason over shared context.

Cons:

- still requires manual prompt/output flow;
- quality depends on user importing structured output;
- not fully interactive.

## Alternative C - Direct AI Intake

The CLI directly invokes an AI adapter for intake analysis.

Pros:

- smoother UX;
- can provide immediate recommendations.

Cons:

- requires AI credentials/provider handling;
- harder to test deterministically;
- premature before prompt-only intake proves the model.

## Alternative D - MCP Tooling

Expose intake as MCP tools for Codex, Claude or other agents.

Pros:

- best fit for multi-agent workflows;
- agents call P2P functions directly;
- avoids shell command parsing.

Cons:

- later-stage architecture;
- requires stable P2P tool contracts;
- not necessary for local MVP.

## Preferred Direction

Start with Alternative B: prompt-only intake backed by registries.

This aligns with the current architecture and creates a stable workflow that can later be automated by AI adapters or MCP.

#### findings.md

findings:
  - id: F001
    type: missing_capability
    title: "Raw ideas lack context-aware intake"
    impact: high
    summary: "P2P can store proposals, but it does not yet help classify a new idea against project memory."

  - id: F002
    type: architecture
    title: "Registries make intake feasible"
    impact: high
    summary: "PROP-016 provides compact generated indexes that intake can use as context without scanning every artifact manually."

  - id: F003
    type: governance
    title: "Intake must recommend, not decide"
    impact: high
    summary: "Agents may suggest next actions, but accepted/rejected/deferred outcomes remain governed decisions."

  - id: F004
    type: collaboration
    title: "Multi-agent collaboration needs shared classification"
    impact: medium
    summary: "Different agents can participate coherently if all classify ideas through P2P artifacts."

### PROP-018 - Choice Management CLI MVP

#### alternatives.md

# Alternatives - PROP-018

None identified yet.

#### findings.md

findings: []

### PROP-019 - Proposal Decision Shortcut Commands

#### alternatives.md

# Alternatives - PROP-019

None identified yet.

#### findings.md

findings: []

### PROP-020 - Proposal Inspection CLI MVP

#### alternatives.md

# Alternatives - PROP-020

None identified yet.

#### findings.md

findings: []

### PROP-021 - Agent Skill Real Commands Update

#### alternatives.md

# Alternatives - PROP-021

None identified yet.

#### findings.md

findings: []

### PROP-022 - Operational Brief Prompt Workflow

#### alternatives.md

# Alternatives - PROP-022

None identified yet.

#### findings.md

findings: []

### PROP-023 - Next Action Recommender MVP

#### alternatives.md

# Alternatives - PROP-023

None identified yet.

#### findings.md

findings: []

### PROP-024 - Choice Blocking and Discovery MVP

#### alternatives.md

# Alternatives - PROP-024

None identified yet.

#### findings.md

findings: []

### PROP-025 - Controlled Intake Apply Workflow

#### alternatives.md

# Alternatives - PROP-025

None identified yet.

#### findings.md

findings: []

### PROP-026 - P2P Software Spec Generator MVP

#### alternatives.md

# Alternatives - PROP-026

None identified yet.

#### findings.md

findings: []

### PROP-027 - Software Spec Exporter MVP

#### alternatives.md

# Alternatives - PROP-027

None identified yet.

#### findings.md

findings: []

### PROP-028 - Spec Kit Export Mapping MVP

#### alternatives.md

# Alternatives - PROP-028

None identified yet.

#### findings.md

findings: []

### PROP-029 - Spec Export Validation MVP

#### alternatives.md

# Alternatives - PROP-029

None identified yet.

#### findings.md

findings: []

### PROP-030 - Managed Work and Multi-Branch Visibility Policy

#### alternatives.md

# Alternatives - PROP-030

None identified yet.

#### findings.md

findings: []

### PROP-031 - Multi-Branch Work Scan MVP

#### alternatives.md

# Alternatives - PROP-031

None identified yet.

#### findings.md

findings: []

### PROP-032 - Managed Work Branch Creation MVP

#### alternatives.md

# Alternatives - PROP-032

None identified yet.

#### findings.md

findings: []

### PROP-033 - Managed Work Submit MVP

#### alternatives.md

# Alternatives - PROP-033

None identified yet.

#### findings.md

findings: []

### PROP-034 - Managed Work Review MVP

#### alternatives.md

# Alternatives - PROP-034

None identified yet.

#### findings.md

findings: []

### PROP-035 - Managed Work Publish MVP

#### alternatives.md

# Alternatives - PROP-035

None identified yet.

#### findings.md

findings: []

### PROP-036 - Managed Work Accept MVP

#### alternatives.md

# Alternatives - PROP-036

None identified yet.

#### findings.md

findings: []

### PROP-037 - Managed Work Status Summary MVP

#### alternatives.md

# Alternatives - PROP-037

None identified yet.

#### findings.md

findings: []

### PROP-038 - Managed Work Merge Conflict Guidance MVP

#### alternatives.md

# Alternatives - PROP-038

None identified yet.

#### findings.md

findings: []

### PROP-039 - Managed Work Finalize MVP

#### alternatives.md

# Alternatives - PROP-039

None identified yet.

#### findings.md

findings: []

### PROP-040 - Managed Work Cleanup MVP

#### alternatives.md

# Alternatives - PROP-040

None identified yet.

#### findings.md

findings: []

### PROP-041 - Remote Project Profile and Review Request Policy

#### alternatives.md

# Alternatives - PROP-041

None identified yet.

#### findings.md

findings: []

### PROP-042 - P2P Core CLI MCP Mediator Web Boundary

#### alternatives.md

# Alternatives - PROP-042

## Alternative A - Core Directly Invokes AI

P2P Core or CLI directly calls Codex, Claude or other providers for analysis.

Pros:

- convenient CLI UX;
- fewer manual prompt/import steps;
- faster perceived intelligence.

Cons:

- couples the deterministic core to providers, credentials, costs and rate limits;
- makes tests and reproducibility harder;
- increases security surface;
- blurs whether P2P is recommending or deciding.

Assessment:

Rejected as the primary architecture. It may be revisited later as a thin optional adapter, but not as the core boundary.

## Alternative B - Core Deterministic, AI Mediator Outside

P2P Core remains deterministic. Optional mediator layers use CLI/MCP/API to interact with it.

Pros:

- keeps open-source local usage complete;
- supports multiple intermediaries chosen by the user;
- keeps credentials and provider behavior outside the core;
- scales to Codex, Claude, custom models, web assistants and IDEs;
- preserves auditability and governance clarity.

Cons:

- requires a clean interface contract;
- may feel less automatic without a mediator;
- needs additional packaging for MCP/mediator layers.

Assessment:

Accepted as the preferred direction.

## Alternative C - Web Product First

Build the web app and put intelligence/collaboration there first.

Pros:

- clearer product UX for non-technical users;
- easier onboarding and collaboration;
- central place for mediator features.

Cons:

- risks delaying the open local engine;
- introduces auth, hosting, persistence and security concerns too early;
- can accidentally make the web app the source of truth instead of `.p2p/`.

Assessment:

Deferred. Web remains a higher layer after Core/CLI/MCP boundaries are stable.

## Alternative D - MCP Server Includes Mediator Logic

Make the MCP server both the tool interface and the intelligent mediator.

Pros:

- fewer deployable components;
- agents get smarter behavior through one endpoint.

Cons:

- mixes deterministic tools with non-deterministic reasoning;
- makes it harder to test and secure;
- reduces portability across different mediator implementations.

Assessment:

Rejected. MCP should expose P2P Core tools. Mediator logic should be separate and optional.

#### findings.md

findings: []

### PROP-043 - Managed Work Retire MVP

#### alternatives.md

# Alternatives - PROP-043

None identified yet.

#### findings.md

findings: []

### PROP-044 - P2P MCP Server MVP

#### alternatives.md

# Alternatives - PROP-044

None identified yet.

#### findings.md

findings: []

### PROP-045 - Agent-Safe Project Bootstrap MVP

#### alternatives.md

# Alternatives - PROP-045

None identified yet.

#### findings.md

findings: []

### PROP-046 - MCP Write-Safe Bootstrap Tools MVP

#### alternatives.md

# Alternatives - PROP-046

None identified yet.

#### findings.md

findings: []

### PROP-047 - Guided Init Wizard MVP

#### alternatives.md

# Alternatives - PROP-047

None identified yet.

#### findings.md

findings: []

### PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

#### alternatives.md

# Alternatives - PROP-048

None identified yet.

#### findings.md

findings: []

### PROP-049 - MCP Level 4A Proposal Refinement Tools

#### alternatives.md

# Alternatives - PROP-049

None identified yet.

#### findings.md

findings: []

### PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

#### alternatives.md

# Alternatives - PROP-050

None identified yet.

#### findings.md

findings: []

### PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

#### alternatives.md

# Alternatives - PROP-051

None identified yet.

#### findings.md

findings: []

### PROP-052 - MCP Proposal Contribution Tool

#### alternatives.md

# Alternatives - PROP-052

None identified yet.

#### findings.md

findings: []

### PROP-053 - Core Validation Layer MVP

#### alternatives.md

# Alternatives - PROP-053

None identified yet.

#### findings.md

findings: []

### PROP-054 - Project Readiness and Maturity Assessment

#### alternatives.md

# Alternatives - PROP-054

## A - Deterministic Readiness Only

Implement only a Core/CLI readiness assessment from existing P2P state.

Benefits:
- Smallest reliable MVP.
- Fully deterministic and testable.
- Fits current Core/CLI/MCP boundary.

Costs:
- Does not answer broader quality or maturity questions.
- May feel too mechanical for non-software projects.

## B - Hybrid Model With Deferred Rubrics

Implement deterministic readiness now and define rubric artifact shape without scoring rubrics in the first Change Set.

Benefits:
- Preserves the full product direction.
- Avoids premature subjective scoring.
- Gives future AI-assisted review a stable import target.

Costs:
- Requires more design upfront than deterministic-only.
- Some rubric decisions remain open.

## C - Full Readiness And Rubric Assessment MVP

Implement deterministic scoring and domain maturity rubrics together.

Benefits:
- More complete user-facing assessment.
- Exercises prompt/import workflows early.

Costs:
- Higher risk of mixing objective state with subjective quality.
- More difficult acceptance criteria and test strategy.
- More likely to expand scope into AI review policy.

## D - Operational Brief Extension Only

Add readiness and maturity sections to the existing operational brief instead of creating assessment commands.

Benefits:
- Minimal new command surface.
- Reuses an existing project-level synthesis workflow.

Costs:
- Briefs can become stale and narrative-heavy.
- Harder to consume programmatically through CLI/MCP.
- Does not provide a stable assessment model.

## Preferred Direction For Synthesis

Alternative B is the strongest next direction: deterministic readiness in the MVP, rubric shape defined but rubric scoring deferred unless explicitly accepted later.

#### findings.md

findings:
  - id: F001
    type: hidden_decision
    title: Score semantics must be explicit
    impact: high
    detail: The proposal needs to decide whether readiness is represented as a percentage, status band, maturity level, factor list, or a combination. A single opaque number would conflict with the non-goal.
    related_to:
      - PROP-054
  - id: F002
    type: architectural_implication
    title: Assessment should reuse validation, registry and next-action signals
    impact: high
    detail: The feature overlaps with p2p validate, registries, operational briefs and p2p next. It should compose existing state readers instead of creating a second validation system.
    related_to:
      - PROP-016
      - PROP-022
      - PROP-023
      - PROP-053
  - id: F003
    type: scope_boundary
    title: Deterministic readiness and domain maturity are different products
    impact: high
    detail: Deterministic readiness can ship first in Core/CLI. Domain maturity requires rubrics, evidence and optional review workflows, and should not block the deterministic MVP.
    related_to:
      - PROP-054
  - id: F004
    type: governance_constraint
    title: Assessment must not become an automatic decision gate
    impact: high
    detail: The assessment can recommend next actions and expose gaps, but owner-controlled governance must remain responsible for accept, reject, defer, merge and work lifecycle decisions.
    related_to:
      - PROP-008
      - PROP-054
  - id: F005
    type: data_model
    title: Assessment artifacts need a stable project-level location
    impact: medium
    detail: The feature needs a deterministic output path such as .p2p/project/assessment.yml or .p2p/assessments/current.yml, plus optional rubric artifacts for project-type criteria.
    related_to:
      - PROP-010
      - PROP-011
  - id: F006
    type: mcp_boundary
    title: MCP exposure should remain advisory and low-risk
    impact: medium
    detail: Initial MCP support should expose assessment status or create prompt artifacts only. It should not mutate governance outcomes or block Work items.
    related_to:
      - PROP-044
      - PROP-046
      - PROP-052
  - id: F007
    type: missing_requirement
    title: The MVP needs factor weights or rule precedence
    impact: medium
    detail: The proposal lists possible signals but does not yet define how severe findings, stale registries, open choices, draft proposals and active work affect readiness.
    related_to:
      - PROP-054
  - id: F008
    type: execution_domain
    title: Implementation spans software and governance metadata
    impact: medium
    detail: The first Change Set would likely touch CLI commands, Core assessment logic, storage paths, tests, registries or project metadata, and MCP read-only exposure later.
    related_to:
      - PROP-054

### PROP-055 - Agent Token Budget and Context Discipline

#### alternatives.md

# Alternatives - PROP-055

None identified yet.

#### findings.md

findings: []

### PROP-056 - Project Definition Maturity Rubrics

#### alternatives.md

# Alternatives - PROP-056

None identified yet.

#### findings.md

findings: []

### PROP-057 - Guided Rubric Selection During Init

#### alternatives.md

# Alternatives - PROP-057

None identified yet.

#### findings.md

findings: []

### PROP-058 - Project README and Installation Guide

#### alternatives.md

# Alternatives - PROP-058

None identified yet.

#### findings.md

findings: []

### PROP-059 - P2PWorkspace Modular Refactoring Plan

#### alternatives.md

# Alternatives - PROP-059

None identified yet.

#### findings.md

findings: []

### PROP-061 - Focused README and Documentation Map

#### alternatives.md

# Alternatives - PROP-061

None identified yet.

#### findings.md

findings: []

### PROP-062 - README Product Landing Page Refinement

#### alternatives.md

# Alternatives - PROP-062

None identified yet.

#### findings.md

findings: []

### PROP-064 - Spec Kit Three-Prompt Export Model

#### alternatives.md

# Alternatives - PROP-064

None identified yet.

#### findings.md

findings: []

### PROP-065 - MCP Agent-First Coverage Expansion

#### alternatives.md

# Alternatives - PROP-065

None identified yet.

#### findings.md

findings: []

### PROP-066 - Permission-Gated MCP Governance And Git Operations

#### alternatives.md

# Alternatives - PROP-066

None identified yet.

#### findings.md

findings: []

### PROP-067 - Agent-First Setup Documentation Split

#### alternatives.md

# Alternatives - PROP-067

None identified yet.

#### findings.md

findings: []

### PROP-068 - Document Agent MCP Client Setup Commands

#### alternatives.md

# Alternatives - PROP-068

None identified yet.

#### findings.md

findings: []

### PROP-069 - Clarify MCP Stdio Integration Model

#### alternatives.md

# Alternatives - PROP-069

None identified yet.

#### findings.md

findings: []

### PROP-070 - Clarify README Agent Access Modes

#### alternatives.md

# Alternatives - PROP-070

None identified yet.

#### findings.md

findings: []

### PROP-071 - Custom Domain Definition Workflow

#### alternatives.md

# Alternatives - PROP-071

None identified yet.

#### findings.md

findings: []

### PROP-072 - Concurrent Managed Work and Merge Decision Model

#### alternatives.md

# Alternatives - PROP-072

None identified yet.

#### findings.md

findings: []

### PROP-073 - Ergonomic Remote Project Initialization

#### alternatives.md

# Alternatives - PROP-073

None identified yet.

#### findings.md

findings: []

### PROP-074 - Agent Runtime Bootstrap Robustness

#### alternatives.md

# Alternatives - PROP-074

None identified yet.

#### findings.md

findings: []

### PROP-075 - MCP End-To-End Proposal Collaboration Workflow

#### alternatives.md

# Alternatives - PROP-075

None identified yet.

#### findings.md

findings: []

### PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

#### alternatives.md

# Alternatives - PROP-076

None identified yet.

#### findings.md

findings: []

### PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

#### alternatives.md

# Alternatives - PROP-077

None identified yet.

#### findings.md

findings: []

### PROP-078 - Project-Local Wheel Installation and Upgrade Model

#### alternatives.md

# Alternatives - PROP-078

None identified yet.

#### findings.md

findings: []

### PROP-079 - Managed Next Action Lifecycle

#### alternatives.md

# Alternatives - PROP-079

None identified yet.

#### findings.md

findings: []

### PROP-080 - Automated GitHub Release Wheel Publishing

#### alternatives.md

# Alternatives - PROP-080

None identified yet.

#### findings.md

findings: []

### PROP-081 - MCP and Skill Support for Managed Next Actions

#### alternatives.md

# Alternatives - PROP-081

None identified yet.

#### findings.md

findings: []

### PROP-082 - Readiness Assessment Refresh And Review Workflow

#### alternatives.md

# Alternatives - PROP-082

## Preferred: artifact-covering interview plus stepped assertiveness

The readiness workflow should generate questions across the whole proposal
artifact set, not only against the missing numeric readiness criteria. Questions
should cover the proposal text and all supporting artifacts that make the
proposal approvable: problem, goals, non-goals, proposal direction, acceptance
criteria, exploration findings, alternatives, tradeoffs, risks, assumptions,
open questions, impact/overlap, readiness evidence, and duplicate/aggregation
candidates.

Answers should be applied back into every useful affected artifact through
available CLI primitives. A single answer may update proposal text, risks,
assumptions, alternatives, open questions, readiness evidence, or impact
artifacts when those artifacts are involved.

Agent assertiveness should be derived from readiness level through a stepped
policy. The lower the readiness, the more the agent must challenge, ask, and
refuse to recommend acceptance. As readiness approaches the target, the agent
should become less intrusive and focus on residual risks or confirmation.

## Alternative: readiness criteria only

The system could generate questions only for missing readiness criteria such as
`risk_coverage` or `alternatives_quality`.

This is insufficient because readiness criteria are a scoring projection, not
the full proposal memory. A proposal can have a missing or stale supporting
artifact even when a criterion label appears covered.

## Alternative: fixed pedantry index

The system could add a dedicated numeric pedantry or assertiveness index.

This is not preferred for the MVP. It introduces another score to calibrate and
explain, while readiness score, failed gates, confidence, missing artifacts, and
question state already provide enough signals to choose agent behavior.

## Alternative: owner-only stop signal

The system could always keep asking until readiness reaches 100 unless the owner
explicitly stops the flow.

This is too aggressive for near-complete proposals. The better behavior is a
stepped policy plus question/group states. The owner can still stop, defer, mute,
or accept with override, but the agent behavior should be proportionate to the
remaining readiness gap.

## Alternative: chat-only application of answers

The agent could ask questions and summarize answers in chat without updating
proposal artifacts.

This is rejected. Readiness and future agents need durable project memory.
Answers must be written back into affected artifacts through public CLI/MCP
write primitives.

#### findings.md

# Findings - PROP-082

## F001 - PROP-006 Exposed A Real Workflow Gap

PROP-006 was refined enough for owner acceptance, but readiness remained at the
conservative bootstrap score after `p2p proposal readiness refresh`.

Impact:
Readiness needs a public reassessment primitive, otherwise mature proposals may
look artificially weak.

## F002 - Refresh And Assess Are Different Operations

`refresh` should not imply qualitative judgment unless it actually re-evaluates
criteria and evidence.

Impact:
The CLI should use explicit language so users understand whether a command is
synchronizing a snapshot or changing analytical readiness.

## F003 - Owner Override Is Not A Substitute For Assessment

Owner override is appropriate when the owner intentionally accepts below target
readiness. It is not the right mechanism for saying that the computed assessment
is stale.

Impact:
The model needs assessment review in addition to override.

## F004 - Questions Must Cover Proposal Artifacts, Not Only Scores

Readiness criteria are useful, but the proposal is made of multiple artifacts.
Questions should inspect and cover all artifacts that make the proposal robust:
proposal text, exploration, findings, alternatives, risks, assumptions, open
questions, impact, readiness, and duplicate/aggregation evidence.

Impact:
Question generation should be artifact-aware and able to create questions for
stale, missing, placeholder, contradictory, or thin artifacts even if the
readiness criterion name is not itself missing.

## F005 - Applying Answers Must Update All Affected Artifacts

Recording an answer in question memory is not enough. The system must help the
agent propagate answers into the proposal artifacts involved by the answer.

Impact:
`questions apply` or the surrounding agent workflow should produce an
artifact-update plan and use available CLI import/update primitives to update
proposal text, exploration artifacts, impact artifacts, readiness evidence, and
open questions when affected.

## F006 - Pedantry Can Be A Stepped Behavior, Not A New Score

A dedicated pedantry index would add calibration complexity. Readiness bands,
failed gates, confidence, missing criteria, and question state already provide
strong behavior signals.

Impact:
Agent guidance should define stepped assertiveness: high when readiness is low,
focused when readiness is partial, residual when near target, and quiet for
muted/deferred areas unless the owner explicitly reopens them.

### PROP-083 - Domain-Aware Visible Project Definition Export

#### alternatives.md

# Alternatives

## Preferred: visible default Markdown export plus nested profile exports

Generate a human-facing default project definition at `outputs/latest/project.md`.
The file is a single chaptered Markdown document that synthesizes accepted P2P
memory in a form that normal users can inspect without knowing P2P internal
state. Specialized exports are optional additional profiles under
`outputs/latest/exports/<profile-or-vertical>/`.

This is the preferred direction because it keeps the default generic across
verticals while still allowing software-specific outputs, OpenSpec exports,
Spec Kit exports, or future vertical profiles to exist without taking over the
main project definition.

## Alternative: keep generated outputs under `.p2p/outputs`

The system could continue writing generated project outputs only under
`.p2p/outputs`. This preserves a clean repository root and avoids introducing a
new visible directory.

This is not preferred because the output remains hidden inside managed P2P
state. It is difficult for humans to discover, inspect, and share, especially
when the project definition is intended to be a primary deliverable rather than
an internal implementation artifact.

## Alternative: use `project/` at repository root

The system could write the human-facing output under `project/latest/` with
review snapshots under `project/review-001`, `project/review-002`, and later
review folders.

This is not preferred because `project/` is easy to confuse with `.p2p/project`
and with the conceptual project state managed by P2P Engine. The name
`outputs/` communicates that the directory contains generated visible outputs.

## Alternative: generate multiple default files

The default export could be a folder of several Markdown files, such as
overview, requirements, risks, assumptions, decisions, and scope.

This is not preferred for the default because it creates more navigation work
and makes the canonical human-readable project definition less obvious. Multiple
files remain appropriate for specialized profiles under `outputs/latest/exports/`
when a vertical needs structured output.

## Alternative: make the software export the default

The project export could keep treating software-spec, OpenSpec, or Spec Kit as
the primary default output.

This is not preferred because P2P Engine is intended to handle projects across
many vertical domains. Software exports should be profile-specific outputs, not
the default representation of every project.

## Alternative: make the visible output path configurable in the MVP

The system could allow users to choose between `outputs/`, `project/`, `.p2p`,
or another location from the first implementation.

This is not preferred for the MVP because configurability would add migration,
documentation, validation, and compatibility complexity before the default
behavior is proven. A stable root-level `outputs/` convention is simpler and
more predictable.

#### findings.md

# Findings

## Tradeoff Analysis

### Visible `outputs/` root versus hidden `.p2p/outputs`

The visible root-level `outputs/` directory improves human discoverability and
makes the project definition usable as a primary artifact. The cost is a small
increase in root-level generated content and the need to document that `outputs/`
is generated, while `.p2p/` remains the managed source of truth. This tradeoff
is acceptable because the proposal's core value is human-readable project
definition, and hiding that artifact under `.p2p/` works against that goal.

### Single default `project.md` versus multiple default files

A single chaptered `outputs/latest/project.md` gives owners, stakeholders, and
agents one canonical document to inspect. Multiple default files could scale
better for very large projects, but would make the default harder to discover
and easier to partially read out of context. The chosen approach keeps the
default simple and allows complex vertical-specific structures under
`outputs/latest/exports/<profile-or-vertical>/`.

### Generic default export versus software-first export

A generic project definition keeps P2P Engine aligned with multiple verticals.
Software-specific exports remain available as profiles, but do not define the
shape of every project. The tradeoff is that software workflows need one more
nested export path, while non-software projects gain a default representation
that does not force them into implementation-spec language.

### Fixed output path versus configurable destination

Using a fixed `outputs/` path in the MVP reduces design, documentation, and
compatibility complexity. Configurability would be useful later for advanced
repository layouts, but it would add avoidable surface area before the behavior
is proven. The MVP should prefer deterministic generation and a stable convention.

### Review snapshots versus overwriting latest only

Keeping `outputs/latest/` plus `outputs/review-###/` provides auditability and
lets humans compare previous generated project definitions. The cost is more
generated files over time. This is acceptable if review folders are deterministic
and confined under `outputs/`.

### Compatibility preservation versus immediate cleanup

Treating `.p2p/outputs` as a compatibility surface slows down cleanup, but
prevents breaking existing CLI, MCP, tests, or scripts that may rely on current
paths. The implementation should inventory current usage first, then choose
mirroring, deprecation, migration, or removal deliberately.

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

#### alternatives.md

# Alternatives - PROP-085

## Preferred: Pure Data Vertical Packs

Use `.yaml` and/or `.md` files to define vertical metadata, sections, rubrics,
blocking questions, and expected artifacts. The engine loads and validates these
packs, and the agent uses them to guide project initialization and readiness
review.

Benefits:
- inspectable by humans;
- easy to version and test;
- compatible with project-local customization;
- safer than executable plugins;
- extensible toward a future registry.

Costs:
- limited to declarative behavior in the MVP;
- requires a well-defined schema and validation errors;
- agent instructions must be strong enough to interpret the data proactively.

## Alternative: Executable Plugin Verticals

Model each vertical as installable plugin code.

Benefits:
- maximum flexibility;
- vertical-specific logic can be arbitrarily rich.

Costs:
- larger security and compatibility surface;
- harder governance and review;
- more difficult packaging and upgrade story;
- too heavy for the MVP.

## Alternative: Hardcoded Core Verticals

Ship many verticals directly in P2P Engine procedural code.

Benefits:
- deterministic behavior;
- simple runtime dependency model.

Costs:
- does not scale to many domains;
- expensive to maintain;
- encourages superficial verticals;
- makes project-local extension awkward.

## Alternative: Generic `base_project` Only

Use only generic project readiness rubrics and avoid vertical-specific packs.

Benefits:
- simplest implementation;
- no vertical quality problem.

Costs:
- too generic for real project guidance;
- weak support for domain-specific capisaldi;
- agent has little structured context for proactive interviewing.

## Decision

The MVP should use pure data vertical packs, with `base_project` as fallback,
one complete demonstration vertical, and project-local custom packs. Executable
plugins and remote registries remain future extensions.

#### findings.md

# Findings - PROP-085

- Vertical specificity is necessary for useful project readiness. Without
  domain-specific sections, questions, and artifacts, P2P can only provide
  generic project hygiene and risks feeling banal.
- Full domain coverage inside the core engine is not viable. Creating and
  maintaining every possible vertical would be costly and would lower quality.
- Pure data packs are the right MVP boundary. They are inspectable, testable,
  versionable, and safer than executable plugin code.
- `base_project` should be the universal fallback and extension point. It
  provides common project sections while leaving room for vertical-specific
  specialization.
- The agent must be the proactive orchestrator. The CLI can persist state and
  run deterministic commands, but the agent must recognize weak initialization,
  propose capisaldi, ask owner questions, and return to deferred foundational
  project work when readiness is weak.
- Existing project rubrics and maturity/readiness should be reused. Vertical
  packs should feed structured evidence into the current system, not create a
  parallel maturity engine.
- Registry support should be deferred. The MVP should keep default packs internal
  and project-local overrides possible, while keeping the data model compatible
  with a future REST registry.
- The proposal must define `base_project`, not only the vertical mechanism.
  Without a concrete default structure, fallback behavior remains too abstract.
- Current P2P Engine code has project domains and project rubrics, but does not
  yet have pluggable vertical pack commands. The feature should add a dedicated
  `p2p project vertical ...` CLI surface for list/show/validate/propose/add.
- Example custom vertical candidates are useful as reference fixtures because
  they prove the model can adapt to unrelated domains without hardcoding every
  possible vertical.
- The long-term default catalog should be explicit, but not all of it belongs in
  the first implementation slice. The first slice proves the mechanism with
  `base_project` and one demonstration vertical; the next catalog milestone is
  `base_project` plus five verticals; the V1 default catalog is `base_project`
  plus roughly nine high-quality verticals.
- Profiles and modules reduce vertical proliferation. A profile specializes a
  vertical, while a module adds a cross-cutting concern such as security,
  accessibility, go-to-market, crowdfunding, education, or community building.
- Vertical packs become more useful when proposals are traceable to vertical
  sections/capisaldi. The project should be able to summarize the active
  vertical skeleton and show which proposals cover each point, which points are
  missing, and which proposals are unmapped.

## Tradeoffs

- Internal default packs improve reliability and testing, but reduce immediate
  ecosystem extensibility.
- Project-local custom packs make the system flexible, but require validation
  and agent guidance to avoid low-quality or inconsistent packs.
- A single demonstration vertical keeps scope controllable, but it must be
  complete enough to prove that the pack model works end to end.
- Deferring executable plugins limits advanced behavior, but avoids security,
  compatibility, and governance complexity in the MVP.
- Adding a vertical CLI surface increases implementation scope, but makes the
  model understandable and operational for agents and users.
- Naming the catalog roadmap makes future scope clearer, but the proposal must
  keep the first slice narrow enough to implement and validate.
- Proposal-to-vertical traceability adds modeling work, but it prevents the
  vertical from becoming a static template detached from governance decisions.

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

#### alternatives.md

# Alternatives - PROP-086

None identified yet.

#### findings.md

findings: []

### PROP-087 - Agent Personality Model For Decision Mediation

#### alternatives.md

# Alternatives - PROP-087

## A. Project-Level Interaction Style

Store one `interaction_style` for the project.

Pros:

- Consistent experience for the decision owner.
- Simple schema and validation.
- Good default for generated project instructions.
- Easy to expose via `p2p project interaction-style`.

Cons:

- Less flexible for different agent surfaces.
- Requires a future extension if an owner wants agent-specific style.

Status: selected for the first implementation.

## B. Per-Agent Interaction Style

Store one style per agent profile.

Pros:

- Different clients can have different interaction contracts.
- Useful if one agent is used as a technical operator and another as a mediator.

Cons:

- More configuration paths.
- Higher risk of inconsistent owner experience.
- More generated instruction variants.

Status: deferred.

## C. Runtime Or Session Override

Allow temporary style changes for one session or command.

Pros:

- Flexible for debugging, demos, or exceptional conversations.
- Could let the owner temporarily raise or lower assertiveness.

Cons:

- Harder to persist and audit.
- Weak fit for remote MCP unless exposed through explicit stateful primitives.
- Can make behavior unpredictable across sessions.

Status: deferred.

## D. Named Presets

Persist named combinations of scale values.

Pros:

- Easy to choose at first.
- Friendly for non-technical setup.

Cons:

- Does not scale with three or more dimensions.
- Creates another abstraction layer to explain and maintain.
- Can hide the actual values that drive behavior.

Status: rejected for persisted configuration.

#### findings.md

# Findings - PROP-087

## Key Findings

- Interaction style should be a project property in the first implementation,
  not an agent-specific property.
- The model should persist numeric scale values, not prose personas.
- The first-slice defaults are:
  - `technical_verbosity: 2`
  - `formality: 2`
  - `assertiveness: 0`
- `assertiveness` is a separate behavioral dimension. It should not be encoded
  through formality or technical verbosity.
- The public command surface should use `project interaction-style`.
- MCP tools must mirror the CLI boundary with explicit read-only and write-safe
  operations.
- Generated agent instructions and project/local skills must teach agents how
  to inspect and update interaction style through CLI/MCP only.
- Existing projects must work without configured interaction style by falling
  back to the defaults.

## Implementation Findings

- A compact, versioned configuration record is preferable to prompt-only
  instructions because it is inspectable, validated, and reusable by CLI, MCP,
  generated instructions, and future UIs.
- The behavior should be rendered into instructions through deterministic text
  mapping. The persisted values remain the source of truth.
- Direct `.p2p` edits must stay out of the workflow. If a future surface needs
  to change interaction style remotely, it must use explicit MCP tools.

## Risk Findings

- If `assertiveness` is too high by default, the agent may block normal owner
  flow. Keeping the default at `0` preserves current behavior.
- If `technical_verbosity` is too low, the owner may lose operational
  transparency. Diagnostics and audit evidence must remain available.
- If labels/presets become the source of truth, the model becomes hard to scale
  when additional dimensions are added.

## Risks

### PROP-002 - Proposal Exploration And Readiness Workflow

#### risks.md

# Risks - PROP-002

## R1 - Confusione tra explore e digest

Rischio:
`explore` potrebbe essere usato come sinonimo di digest.

Mitigazione:
Documentare chiaramente che explore scopre implicazioni e digest riassume
contributi gia raccolti.

## R2 - Conversazioni non persistite

Rischio:
Le esplorazioni fatte dentro agenti AI restano nella chat e non entrano nel
repository.

Mitigazione:
Richiedere import o salvataggio negli artefatti P2P.

## R3 - Falsificazione della maturity tramite override

Rischio:
Se l'override owner forza direttamente il valore calcolato a 100, il sistema
perde onesta analitica.

Mitigazione:
Separare `computed_score` dalla governance decision. L'override crea un audit
event come `accept_with_override`, preservando score, failed gates e reason.

## R4 - Score percepito come decisione automatica

Rischio:
Utenti o agenti potrebbero interpretare readiness alta come accettazione
automatica, o readiness bassa come rifiuto automatico.

Mitigazione:
Documentare che readiness e lifecycle state sono separati. La readiness supporta
la decisione, ma l'owner mantiene il controllo.

## R5 - Pedanteria eccessiva sulle proposte piccole

Rischio:
Un modello di maturity troppo uniforme potrebbe rallentare correzioni semplici
o trasformare ogni proposta in un esercizio burocratico.

Mitigazione:
Usare tier, soglie e gate diversi. Small proposal ha percorso leggero, ma non
zero-governance.

## R6 - Compensazione impropria del punteggio

Rischio:
Una proposta potrebbe raggiungere uno score totale alto grazie a criteri
secondari, pur avendo lacune essenziali.

Mitigazione:
Introdurre minimum gate per tier. Il total score misura maturita complessiva,
ma i gate impediscono readiness automatica quando mancano criteri essenziali.

## R7 - Testo generico usato per raggiungere lo score

Rischio:
Un agente potrebbe compilare artifact lunghi ma vaghi, ottenendo punteggi alti
senza migliorare davvero la proposta.

Mitigazione:
Collegare ogni criterio a evidenze specifiche e usare artifact quality gate.
Un artifact non puo essere `meaningful` o `ready` senza claim, vincoli,
decisioni, tradeoff o evidenze specifiche della proposal.

## R8 - Score alto ma bassa affidabilita

Rischio:
La proposta potrebbe essere ben scritta ma basata su informazioni non validate,
ipotesi fragili o impatti non verificati.

Mitigazione:
Aggiungere `confidence` e `confidence_reasons`. Per proposal governance-critical,
low confidence impedisce automatic `ready_for_decision`.

## R9 - Classificazione tier incoerente

Rischio:
Agenti diversi potrebbero classificare la stessa proposta in tier diversi,
alterando soglie e gate richiesti.

Mitigazione:
Agent/system suggeriscono il tier, owner conferma. Il sistema segnala downgrade
incoerenti rispetto alle evidenze.

## R10 - Readiness profile non versionato

Rischio:
Uno score senza profilo e versione non e interpretabile nel tempo.

Mitigazione:
Ogni assessment registra `profile_id`, `profile_version` e `computed_at`.

## R11 - Registry scambiato per fonte di verita

Rischio:
Snapshot o registry readiness potrebbero diventare divergenti dagli artifact e
venire trattati come sorgente primaria.

Mitigazione:
Definire registries come cache/snapshot. Source of truth: artifact, profile,
assessment e governance audit record.

## R12 - MCP write trattato come autonomia agente

Rischio:
Se i tool MCP di override o accept-with-override sono esposti senza gate,
l'agente potrebbe superare la readiness o registrare decisioni governance senza
autorita owner.

Mitigazione:
MCP write/governance tools sono parte del modello, ma permission-gated. Gli
agenti possono leggere e spiegare readiness; override e accept richiedono
autorita esplicita.

## R13 - `needs_owner_input` confuso con artifact debole

Rischio:
Un artifact che richiede una scelta owner potrebbe essere classificato come
thin, spingendo l'agente a scrivere altro testo invece di chiedere una decisione.

Mitigazione:
Trattare `needs_owner_input` come stato distinto. `p2p next` deve proporre
azioni come `ask_owner`, `resolve_owner_question` o `confirm_policy`.

### PROP-004 - Prompt-only Import Workflow

#### risks.md

# Risks - PROP-004

None identified yet.

### PROP-005 - Codex Skill Integration

#### risks.md

# Risks - PROP-005

None identified yet.

### PROP-006 - Multi-Agent Integration Model

#### risks.md

# Risks - PROP-006

## R1 - Overengineering

Risk:
Replicating too much of Spec Kit, OpenSpec, or external agent configuration
systems before P2P Engine needs it.

Mitigation:
Keep the MVP focused on a local registry, generated files, hashes, install all,
safe update, and safe uninstall. Defer external adapter packages and deep
provider-specific automation.

## R2 - Shared File Ownership

Risk:
Several adapters may depend on `AGENTS.md`. A naive uninstall could remove a
baseline file still needed by other integrations.

Mitigation:
Track `shared: true` files in `.p2p/agent-integrations.yml`. Uninstalling a
specific agent must not remove `AGENTS.md` or `.p2p/agent-policy.yml`.

## R3 - Manual Drift And Data Loss

Risk:
Users may edit generated files manually. Update or uninstall could overwrite or
delete those changes.

Mitigation:
Store generated file hashes. If the current hash differs from the stored hash,
mark the file as drifted and require explicit `--force` or manual resolution.

## R4 - Tool Convention Drift

Risk:
Cursor, Copilot, Gemini, OpenCode, Claude, or Codex may change their instruction
file conventions.

Mitigation:
Version adapter templates. Keep adapter definitions internal in the MVP. Update
documentation and tests when external conventions change.

## R5 - False Sense Of Enforcement

Risk:
Some agents treat instruction files as advisory and may not follow them
deterministically.

Mitigation:
Generated instructions must describe P2P boundaries clearly, but P2P Engine
must still rely on CLI validation, readiness checks, permission gates, and owner
decisions. Do not treat agent instructions as hard security.

## R6 - Global Configuration Side Effects

Risk:
Installing an adapter might be interpreted as permission to edit user-level
agent configuration, home directories, IDE settings, or MCP client config.

Mitigation:
PROP-006 MVP should only manage project-local files. Any user/global
configuration requires a separate explicit consent-gated flow.

## R7 - Registry Corruption Or Staleness

Risk:
The registry may get out of sync with actual files.

Mitigation:
`p2p agent show`, `p2p agent list`, and `p2p agent doctor` should recompute
current file hashes and report stale, missing, modified, or orphaned files.

## R8 - Adapter Surface Too Broad

Risk:
Supporting many agents at once can dilute quality and leave poorly tested
templates.

Mitigation:
Implement adapter behavior with a shared test harness and snapshot tests. Keep
the initial templates small, explicit, and based on documented file conventions.

## R9 - File Target Collisions During Install All

Risk:
`p2p agent install all` could cause two adapters to manage the same non-shared
file path.

Mitigation:
Declare shared vs non-shared file targets in adapter definitions. `install all`
must fail or warn before writing when two adapters would own the same non-shared
path.

### PROP-009 - Governance CLI Commands

#### risks.md

# Risks - PROP-009

None identified yet.

### PROP-010 - P2P Project State Model

#### risks.md

# Risks - PROP-010

## R1 - Duplicated source of truth

Risk:

Generated project artifacts may be edited manually and diverge from proposal artifacts.

Mitigation:

Mark `.p2p/project/` as derived and include provenance metadata. Decide explicitly whether manual edits are allowed.

## R2 - Premature internal spec complexity

Risk:

Designing a complete specification model too early could slow CLI progress.

Mitigation:

Start with a minimal `software-spec/index.md` and module files. Add schemas only when exporter or task tracking needs prove them necessary.

## R3 - Automatic refresh surprises users

Risk:

If accepting a proposal silently rewrites derived files, users may be surprised by broad diffs.

Mitigation:

Start with explicit `p2p project refresh`. Add automatic refresh later behind an option or config flag.

## R4 - Exporter coupling

Risk:

The internal spec model could accidentally mirror OpenSpec or Spec Kit too closely.

Mitigation:

Keep P2P spec concepts neutral and map to downstream tools through adapters.

### PROP-011 - Project Refresh MVP

#### risks.md

# Risks - PROP-011

None identified yet.

### PROP-012 - Impact Map and Conflict Memory

#### risks.md

# Risks - PROP-012

None identified yet.

### PROP-013 - Managed Git Adapter and Change Set Model

#### risks.md

# Risks - PROP-013

## R1 - Hidden Git operations surprise users

Risk:

If P2P creates commits, branches, merges, or tags silently, users may be surprised by repository state changes.

Mitigation:

Start with metadata-only policy. Add managed Git operations gradually. Expose internal operations through:

```text
p2p status --verbose
p2p doctor
p2p internals git-policy
```

Additional controls:

- Default MVP mode is `metadata_only`.
- No automatic commit, branch, merge, or tag without explicit opt-in.
- Normal output mentions that Git is managed, but does not expose low-level details.
- Verbose output shows planned/internal Git operations.
- Doctor/debug output explains repository state and policy decisions.

## R2 - Git policy becomes arbitrary

Risk:

The system may inconsistently decide when to create branches/commits/tags.

Mitigation:

Use explicit `git_policy.yml` criteria derived from impact/conflict data.

The policy decision should be explainable:

```text
Policy result:
  internal_branch: recommended

Reasons:
  - proposal touches public CLI behavior
  - proposal modifies governance/project artifacts
  - proposal has conflict relation CONFLICT-002
```

## R3 - Too many change sets

Risk:

Every accepted proposal may become a separate change set, causing fragmentation.

Mitigation:

Allow one change set to include multiple accepted proposals and decisions.

## R4 - Git history becomes the only memory

Risk:

Important decision context may live only in branch/PR history.

Mitigation:

Persist proposal, decision, impact, conflict, and change-set metadata in `.p2p/`.

## R5 - AI bypasses P2P Engine

Risk:

An AI agent may manipulate Git directly, bypassing proposal/change/decision artifacts.

Mitigation:

P2P skills and agent instructions must require agents to use P2P CLI commands by default. Direct Git should be limited to debug/repair flows.

## R6 - Git adapter becomes too complex too early

Risk:

Building a full Git adapter may distract from the core proposal/change/project workflow.

Mitigation:

Introduce the adapter in layers:

```text
Layer 1 - metadata only
  record intended Git policy and planned operations

Layer 2 - read-only diagnostics
  inspect branch/status/log without changing Git state

Layer 3 - safe write operations
  explicit commits/tags behind opt-in

Layer 4 - managed branches and merges
  only after policy and recovery tooling are mature
```

## R7 - Managed Git creates recovery burden

Risk:

If P2P performs Git operations, users need a way to understand and recover from failed operations.

Mitigation:

Before enabling write operations, implement:

```text
p2p doctor
p2p status --verbose
p2p internals git-log
p2p internals git-policy
```

The first adapter implementation should be transactional where possible and should never hide failures.

## R8 - Non-technical UX hides too much from technical users

Risk:

Hiding Git details by default may frustrate advanced users who need auditability and control.

Mitigation:

Expose details through progressive disclosure:

```text
normal
  P2P concepts only

verbose
  planned/internal Git operations

doctor/debug
  repository state, policy reasoning, repair hints
```

### PROP-014 - Change Set Metadata MVP

#### risks.md

# Risks - PROP-014

None identified yet.

### PROP-015 - Change Set Lifecycle and Task Tracking

#### risks.md

# Risks - PROP-015

None identified yet.

### PROP-016 - Project Registries MVP

#### risks.md

# Risks - PROP-016

## R1 - Registry Drift

Risk:

Generated registries can diverge from source artifacts.

Mitigation:

Treat registries as derived and refreshable. Add `p2p registry refresh` and make drift detectable with `p2p registry status`.

## R2 - Source Of Truth Confusion

Risk:

Users or agents may edit registries directly and treat them as primary data.

Mitigation:

Mark registries as generated. Source artifacts remain proposals, decisions, changes, governance and project files.

## R3 - Large Diffs

Risk:

Refreshing registries may create broad diffs.

Mitigation:

Use typed registries and stable sorting.

## R4 - Premature Schema Complexity

Risk:

Overdesigning registry schemas may slow MVP progress.

Mitigation:

Start with minimal fields required by current CLI workflows.

### PROP-017 - Proposal Intake and Context Analysis MVP

#### risks.md

# Risks - PROP-017

## R001 - False Duplicate Detection

Risk:
The intake process may classify a genuinely new idea as already covered.

Mitigation:
Output should include confidence, rationale and suggested human review. Intake recommendations are advisory.

## R002 - Agent Overreach

Risk:
An agent may treat an intake recommendation as a decision.

Mitigation:
Make governance explicit: intake can suggest `create proposal`, `add contribution`, `open choice`, or `record conflict`, but cannot accept/reject proposals.

## R003 - Registry Drift

Risk:
Intake quality depends on registries being current.

Mitigation:
Require `p2p registry status` in intake context and recommend `p2p registry refresh` when stale.

## R004 - Overcomplex MVP

Risk:
Semantic search, embeddings, AI adapters or MCP could make the first implementation too large.

Mitigation:
Keep the MVP prompt-only, file-based and registry-backed.

### PROP-018 - Choice Management CLI MVP

#### risks.md

# Risks - PROP-018

None identified yet.

### PROP-019 - Proposal Decision Shortcut Commands

#### risks.md

# Risks - PROP-019

None identified yet.

### PROP-020 - Proposal Inspection CLI MVP

#### risks.md

# Risks - PROP-020

None identified yet.

### PROP-021 - Agent Skill Real Commands Update

#### risks.md

# Risks - PROP-021

None identified yet.

### PROP-022 - Operational Brief Prompt Workflow

#### risks.md

# Risks - PROP-022

None identified yet.

### PROP-023 - Next Action Recommender MVP

#### risks.md

# Risks - PROP-023

None identified yet.

### PROP-024 - Choice Blocking and Discovery MVP

#### risks.md

# Risks - PROP-024

None identified yet.

### PROP-025 - Controlled Intake Apply Workflow

#### risks.md

# Risks - PROP-025

None identified yet.

### PROP-026 - P2P Software Spec Generator MVP

#### risks.md

# Risks - PROP-026

None identified yet.

### PROP-027 - Software Spec Exporter MVP

#### risks.md

# Risks - PROP-027

None identified yet.

### PROP-028 - Spec Kit Export Mapping MVP

#### risks.md

# Risks - PROP-028

None identified yet.

### PROP-029 - Spec Export Validation MVP

#### risks.md

# Risks - PROP-029

None identified yet.

### PROP-030 - Managed Work and Multi-Branch Visibility Policy

#### risks.md

# Risks - PROP-030

None identified yet.

### PROP-031 - Multi-Branch Work Scan MVP

#### risks.md

# Risks - PROP-031

None identified yet.

### PROP-032 - Managed Work Branch Creation MVP

#### risks.md

# Risks - PROP-032

None identified yet.

### PROP-033 - Managed Work Submit MVP

#### risks.md

# Risks - PROP-033

None identified yet.

### PROP-034 - Managed Work Review MVP

#### risks.md

# Risks - PROP-034

None identified yet.

### PROP-035 - Managed Work Publish MVP

#### risks.md

# Risks - PROP-035

None identified yet.

### PROP-036 - Managed Work Accept MVP

#### risks.md

# Risks - PROP-036

None identified yet.

### PROP-037 - Managed Work Status Summary MVP

#### risks.md

# Risks - PROP-037

None identified yet.

### PROP-038 - Managed Work Merge Conflict Guidance MVP

#### risks.md

# Risks - PROP-038

None identified yet.

### PROP-039 - Managed Work Finalize MVP

#### risks.md

# Risks - PROP-039

None identified yet.

### PROP-040 - Managed Work Cleanup MVP

#### risks.md

# Risks - PROP-040

None identified yet.

### PROP-041 - Remote Project Profile and Review Request Policy

#### risks.md

# Risks - PROP-041

None identified yet.

### PROP-042 - P2P Core CLI MCP Mediator Web Boundary

#### risks.md

# Risks - PROP-042

None identified yet.

### PROP-043 - Managed Work Retire MVP

#### risks.md

# Risks - PROP-043

None identified yet.

### PROP-044 - P2P MCP Server MVP

#### risks.md

# Risks - PROP-044

None identified yet.

### PROP-045 - Agent-Safe Project Bootstrap MVP

#### risks.md

# Risks - PROP-045

None identified yet.

### PROP-046 - MCP Write-Safe Bootstrap Tools MVP

#### risks.md

# Risks - PROP-046

None identified yet.

### PROP-047 - Guided Init Wizard MVP

#### risks.md

# Risks - PROP-047

None identified yet.

### PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

#### risks.md

# Risks - PROP-048

None identified yet.

### PROP-049 - MCP Level 4A Proposal Refinement Tools

#### risks.md

# Risks - PROP-049

None identified yet.

### PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

#### risks.md

# Risks - PROP-050

None identified yet.

### PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

#### risks.md

# Risks - PROP-051

None identified yet.

### PROP-052 - MCP Proposal Contribution Tool

#### risks.md

# Risks - PROP-052

None identified yet.

### PROP-053 - Core Validation Layer MVP

#### risks.md

# Risks - PROP-053

None identified yet.

### PROP-054 - Project Readiness and Maturity Assessment

#### risks.md

# Risks - PROP-054

- Risk: Users may treat a readiness score as an automatic approval or rejection.
  Mitigation: Label assessment as advisory, include explicit gaps, and keep governance decisions separate.

- Risk: A single number may hide important blockers.
  Mitigation: Always show factor-level results, blocking gaps and confidence alongside any score.

- Risk: The feature duplicates `p2p validate` or `p2p next`.
  Mitigation: Compose existing validation and next-action logic; do not create independent rule systems for the same signals.

- Risk: Rubric maturity becomes subjective and inconsistent.
  Mitigation: Require explicit criteria files, evidence fields and confidence values; treat AI output as importable advisory material only.

- Risk: The MVP scope expands into AI/provider integration.
  Mitigation: Keep Core deterministic; use prompt/import workflows for subjective review; defer mediator/provider behavior.

- Risk: Assessment artifacts become stale.
  Mitigation: Include generation metadata, source timestamps or registry freshness checks, and expose refresh/show behavior clearly.

- Risk: Poor weighting makes the readiness score misleading.
  Mitigation: Start with transparent rule bands and factor severity rather than complex weighted scoring.

### PROP-055 - Agent Token Budget and Context Discipline

#### risks.md

# Risks - PROP-055

None identified yet.

### PROP-056 - Project Definition Maturity Rubrics

#### risks.md

# Risks - PROP-056

None identified yet.

### PROP-057 - Guided Rubric Selection During Init

#### risks.md

# Risks - PROP-057

None identified yet.

### PROP-058 - Project README and Installation Guide

#### risks.md

# Risks - PROP-058

None identified yet.

### PROP-059 - P2PWorkspace Modular Refactoring Plan

#### risks.md

# Risks - PROP-059

None identified yet.

### PROP-061 - Focused README and Documentation Map

#### risks.md

# Risks - PROP-061

None identified yet.

### PROP-062 - README Product Landing Page Refinement

#### risks.md

# Risks - PROP-062

None identified yet.

### PROP-064 - Spec Kit Three-Prompt Export Model

#### risks.md

# Risks - PROP-064

None identified yet.

### PROP-065 - MCP Agent-First Coverage Expansion

#### risks.md

# Risks - PROP-065

None identified yet.

### PROP-066 - Permission-Gated MCP Governance And Git Operations

#### risks.md

# Risks - PROP-066

None identified yet.

### PROP-067 - Agent-First Setup Documentation Split

#### risks.md

# Risks - PROP-067

None identified yet.

### PROP-068 - Document Agent MCP Client Setup Commands

#### risks.md

# Risks - PROP-068

None identified yet.

### PROP-069 - Clarify MCP Stdio Integration Model

#### risks.md

# Risks - PROP-069

None identified yet.

### PROP-070 - Clarify README Agent Access Modes

#### risks.md

# Risks - PROP-070

None identified yet.

### PROP-071 - Custom Domain Definition Workflow

#### risks.md

# Risks - PROP-071

None identified yet.

### PROP-072 - Concurrent Managed Work and Merge Decision Model

#### risks.md

# Risks - PROP-072

None identified yet.

### PROP-073 - Ergonomic Remote Project Initialization

#### risks.md

# Risks - PROP-073

None identified yet.

### PROP-074 - Agent Runtime Bootstrap Robustness

#### risks.md

# Risks - PROP-074

None identified yet.

### PROP-075 - MCP End-To-End Proposal Collaboration Workflow

#### risks.md

# Risks - PROP-075

None identified yet.

### PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

#### risks.md

# Risks - PROP-076

None identified yet.

### PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

#### risks.md

# Risks - PROP-077

None identified yet.

### PROP-078 - Project-Local Wheel Installation and Upgrade Model

#### risks.md

# Risks - PROP-078

None identified yet.

### PROP-079 - Managed Next Action Lifecycle

#### risks.md

# Risks - PROP-079

None identified yet.

### PROP-080 - Automated GitHub Release Wheel Publishing

#### risks.md

# Risks - PROP-080

None identified yet.

### PROP-081 - MCP and Skill Support for Managed Next Actions

#### risks.md

# Risks - PROP-081

None identified yet.

### PROP-082 - Readiness Assessment Refresh And Review Workflow

#### risks.md

# Risks - PROP-082

## Agent becomes annoying instead of useful

If assertiveness is too high after the proposal is already nearly complete, the
owner may experience the agent as obstructive.

Mitigation: use a stepped behavior tied to readiness bands, failed gates,
confidence, and question state. Near target readiness, the agent should ask only
high-value residual questions.

## Agent stays passive when readiness is low

If the skill only reports gaps and does not require next-question behavior, the
agent may summarize problems without driving the interview.

Mitigation: when readiness is low or blocked, agent guidance must require the
agent to initialize/update question memory, select the highest-impact next
question, ask one question at a time, and record answers.

## Questions cover only score gaps, not real artifacts

Generated questions may overfit the readiness criterion names and miss stale
supporting artifacts.

Mitigation: the question generator must inspect and cover the whole proposal
artifact set: proposal.md, exploration artifacts, impact artifacts, readiness,
questions, and duplicate/aggregation evidence.

## Answers remain disconnected from proposal state

Owner answers can be recorded in `questions.yml` but never applied to the
proposal artifacts that should change.

Mitigation: answer application must identify affected artifacts and update all
useful artifacts through available CLI import/update commands. Applied state
should mean that the answer has been propagated, not merely recorded.

## Readiness stays stale after refinement

The system may update artifacts but leave readiness score, missing criteria, or
confidence unchanged.

Mitigation: after applying answers or importing refined artifacts, the workflow
must recompute readiness through the evidence-aware reassessment path and report
remaining gaps. `refresh` should not masquerade as reassessment if it is only
snapshot synchronization.

## Owner control is bypassed

An aggressive agent may treat readiness improvement as authorization to accept,
merge, close, or aggregate proposals.

Mitigation: agent behavior may recommend and prepare, but owner-controlled
governance actions remain explicit decisions.

### PROP-083 - Domain-Aware Visible Project Definition Export

#### risks.md

# Risks

## Backward compatibility with `.p2p/outputs`

Existing users, tests, MCP tools, or scripts may depend on current generated
outputs under `.p2p/outputs`. Moving or removing those artifacts without a
compatibility path could break existing workflows.

Mitigation: treat `.p2p/outputs` as a compatibility surface. Before deleting or
relocating anything, inventory current producers and consumers, preserve public
CLI and MCP behavior, and introduce deprecation or mirroring only through an
explicit migration path.

## Confusion between visible outputs and managed P2P state

Users may misunderstand whether `outputs/` is source-of-truth governance state
or generated material.

Mitigation: document `outputs/` as generated visible output, keep `.p2p/` as the
managed source of truth, and include generated metadata in the output such as
source project, export profile, generation time, and source proposal/decision
references.

## Root directory noise

Adding `outputs/` at repository root makes generated files more visible but also
adds another top-level directory.

Mitigation: keep only `latest/`, review snapshots, and profile exports under the
directory. Do not spread generated files directly across the root.

## Oversized `project.md`

A single default Markdown file could become long and difficult to read for
large projects.

Mitigation: organize the file into stable chapters, include a concise executive
summary, and keep detailed machine- or vertical-specific exports under nested
profile folders when appropriate.

## Stale or misleading exports

If `outputs/latest/project.md` is not refreshed after proposal decisions or
project changes, users may treat stale information as current.

Mitigation: make export refresh explicit, archive previous versions into
`outputs/review-###`, and include generation metadata so readers can see when
the output was produced.

## Profile contract sprawl

Supporting software and non-software vertical profiles may create many slightly
different export contracts.

Mitigation: define a generic export profile contract first, then let vertical
profiles extend it through named folders under `outputs/latest/exports/`.

## Premature deletion of legacy generated outputs

The current `.p2p/outputs` content may appear unused but still provide
compatibility for existing commands or tests.

Mitigation: do not delete legacy outputs as part of the proposal itself. The
implementation should verify dependencies and decide whether to mirror, migrate,
deprecate, or remove them in a controlled code change.

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

#### risks.md

# Risks - PROP-085

## Genericity Risk

If P2P Engine lacks vertical-specific structure, project readiness becomes too
generic. The system may check basic project hygiene but fail to guide the owner
toward domain-specific capisaldi, artifacts, and decisions.

Mitigation:
- require `base_project` plus at least one complete demonstration vertical;
- make project readiness review identify missing vertical coverage;
- instruct the agent to propose custom verticals when no suitable pack exists.

## Catalog Explosion Risk

Trying to create every possible vertical inside the core engine is not realistic.
It would be expensive, hard to maintain, and likely produce many shallow packs.

Mitigation:
- keep the default set small and high quality;
- support project-local custom packs;
- defer broad domain coverage to future registry/plugin data packs.

## Low-Quality Custom Pack Risk

Project-local custom verticals may be incomplete, inconsistent, or too tailored
to one conversation.

Mitigation:
- validate required fields;
- require sections/capisaldi, minimal rubrics, blocking questions, and expected
  artifacts;
- have the agent present the generated pack to the owner for confirmation before
  using it.

## Parallel Maturity System Risk

Vertical packs could accidentally create a second maturity/readiness model.

Mitigation:
- vertical packs must feed existing project rubrics and maturity/readiness;
- `p2p project readiness review` should reuse current assessment artifacts.

## Registry Prematurity Risk

Implementing a remote registry too early would add API, versioning, trust, and
distribution concerns before the local model is proven.

Mitigation:
- keep the MVP internal/project-local;
- design the schema to be registry-ready without implementing registry behavior.

## Agent Passivity Risk

If agent instructions are weak, the CLI may have valid pack data but agents may
still fail to push for capisaldi and initial questions.

Mitigation:
- add explicit project orchestrator skill guidance;
- make missing initialization/capisaldi a high-priority readiness concern;
- instruct the agent to return to deferred foundational questions unless muted
  by the owner.

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

#### risks.md

# Risks - PROP-086

None identified yet.

### PROP-087 - Agent Personality Model For Decision Mediation

#### risks.md

# Risks - PROP-087

## Behavioral Risks

- High assertiveness can make the agent feel obstructive.
  Mitigation: default `assertiveness` is `0`; higher values are explicit owner
  choices.
- Low technical verbosity can hide useful operational detail from the owner.
  Mitigation: owner-facing tone changes, but diagnostics, audit evidence, and
  command outputs remain available where appropriate.
- High informality may be inappropriate for some project contexts.
  Mitigation: `formality` is explicit and project-level.

## Product Risks

- Named presets could become a parallel source of truth.
  Mitigation: do not persist presets in the first implementation.
- Per-agent overrides could fragment the owner experience.
  Mitigation: defer per-agent style until project-level defaults are stable.
- Session overrides could be hard to audit.
  Mitigation: defer runtime/session overrides until explicit CLI/MCP primitives
  exist.

## Implementation Risks

- Prompt-only implementation would be fragile and hard to inspect.
  Mitigation: use validated project configuration and deterministic instruction
  rendering.
- Direct `.p2p` edits would break local/remote parity.
  Mitigation: expose CLI and MCP primitives and document them in generated
  skills/instructions.

## Assumptions

### PROP-002 - Proposal Exploration And Readiness Workflow

#### assumptions.md

# Assumptions - PROP-002

- Gli artefatti P2P restano la fonte di verita per la proposta.
- Git versiona il risultato dell'interlocuzione.
- L'agente puo valutare e segnalare la qualita dell'esplorazione, ma non puo
  decidere al posto dell'owner.
- Gli artifact Markdown restano il formato authored per umani e agenti.
- I dati strutturati necessari alla macchina devono vivere in readiness profile,
  readiness assessment, snapshot, registry, export o audit record.
- La readiness della proposta affianca lo stato procedurale della proposal; non
  lo sostituisce.
- La readiness e profile-based e versioned.
- Ogni score deve registrare profile id, profile version e computed_at.
- La maturity della proposta puo essere rappresentata con un valore da 0 a 100.
- La maturity misura la qualita e completezza dell'esplorazione, non il merito
  politico o strategico della decisione.
- `computed_score` deve restare il risultato onesto dei criteri automatici o
  ibridi.
- Owner override e un evento governance, non una modifica del computed score.
- L'override readiness avviene primariamente durante l'accept owner, tramite un
  comando esplicito come `p2p proposal accept --override-readiness --reason`.
- L'owner override deve preservare computed score, failed gates e reason.
- `override_reason` e obbligatorio quando l'owner accetta sotto la readiness
  target.
- Le soglie 70, 85 e 95 possono controllare quanto l'agente deve essere pedante.
- Un punteggio totale alto non basta se mancano criteri essenziali per il tier
  della proposta.
- Le proposal governance-critical richiedono minimum gate piu severi e almeno
  confidence media per automatic `ready_for_decision`.
- PROP-002 e governance-critical.
- La confidence deve essere distinta dallo score e basata sulla qualita delle
  evidenze, non sulla qualita retorica del testo.
- Ogni criterio valutato deve avere evidenze collegate ad artifact o sezioni.
- Gli artifact `placeholder` o `thin` devono limitare il punteggio massimo dei
  criteri collegati.
- `needs_owner_input` e uno stato utile e distinto da `thin`: l'artifact puo
  essere buono ma non decision-ready senza input owner.
- Il modello deve essere ibrido: agenti per valutazione qualitativa e CLI per
  validazione, caps, aggregazione, gate e storage.
- MCP read tools possono essere agent-accessible; MCP write/governance tools
  devono essere permission-gated e non agent-autonomous.
- Readiness deve applicarsi alle nuove proposal e alle draft aperte.
- Le proposal gia accettate non devono essere riscritte o invalidate; possono
  essere marcate legacy o valutate retrospettivamente.
- Readiness registry e snapshot sono cache/viste, non fonte primaria.
- Il modello di maturity deve essere utile anche a `p2p next`, che dovrebbe
  suggerire refinement action specifiche e delta verso il target.
- Il conteggio automatico di questioni unresolved deve essere considerato
  indicativo finche non distingue semanticamente domande, decisioni e subtopic.
- Il modello deve evitare burocrazia inutile sulle proposte piccole, ma restare
  esigente sulle proposte product, architetturali e governance-critical.

### PROP-004 - Prompt-only Import Workflow

#### assumptions.md

# Assumptions - PROP-004

None identified yet.

### PROP-005 - Codex Skill Integration

#### assumptions.md

# Assumptions - PROP-005

None identified yet.

### PROP-006 - Multi-Agent Integration Model

#### assumptions.md

# Assumptions - PROP-006

- P2P Engine remains local-first and file-based for this proposal.
- P2P Engine does not invoke AI providers directly.
- Agent integrations produce project-local instructions and metadata.
- Generated instructions are advisory guardrails, not hard security.
- P2P CLI, `.p2p` state, validation, readiness, and owner decisions remain the
  source of truth.
- Multiple agent integrations may coexist in the same project.
- `AGENTS.md` is the shared baseline instruction file.
- Tool-specific files are generated only when they add value for that adapter.
- Safe update and uninstall require file hashes.
- Existing generated instruction behavior must remain backward compatible.
- External adapter packages are deferred until the internal adapter lifecycle is
  stable.

### PROP-009 - Governance CLI Commands

#### assumptions.md

# Assumptions - PROP-009

None identified yet.

### PROP-010 - P2P Project State Model

#### assumptions.md

# Assumptions - PROP-010

- P2P proposal artifacts remain the source of truth for discussion, governance, and decisions.
- `.p2p/project/` contains rationalized derived project state.
- The first software spec model can be Markdown-first, with YAML indexes only where needed.
- Exporters should consume normalized P2P project state rather than raw proposal directories.
- Automatic refresh should be deterministic and should not require AI by default.
- AI-assisted rationalization can be added later through prompt/import commands.

### PROP-011 - Project Refresh MVP

#### assumptions.md

# Assumptions - PROP-011

None identified yet.

### PROP-012 - Impact Map and Conflict Memory

#### assumptions.md

# Assumptions - PROP-012

None identified yet.

### PROP-013 - Managed Git Adapter and Change Set Model

#### assumptions.md

# Assumptions - PROP-013

- Proposal artifacts remain the source of decision history.
- Git is useful but should not define the P2P user-facing domain model.
- Change sets are needed to bridge accepted decisions and implementation.
- Git policy can use impact-map and conflict-memory artifacts.
- The MVP should avoid unsafe automatic Git operations.
- P2P should preserve branch and merge references as metadata even if branches are later deleted.
- Users should not need to understand branch, commit, merge, or tag semantics for normal P2P workflows.
- AI agents should use P2P CLI as the public interface.

### PROP-014 - Change Set Metadata MVP

#### assumptions.md

# Assumptions - PROP-014

None identified yet.

### PROP-015 - Change Set Lifecycle and Task Tracking

#### assumptions.md

# Assumptions - PROP-015

None identified yet.

### PROP-016 - Project Registries MVP

#### assumptions.md

# Assumptions - PROP-016

- Registries are generated and versioned.
- Registries are not primary source artifacts.
- Registry refresh should be deterministic.
- AI prompts can use registries as compact context.
- Exporters should prefer registries for discovery, then load source artifacts for detail.
- The first implementation can remain YAML-only.

### PROP-017 - Proposal Intake and Context Analysis MVP

#### assumptions.md

# Assumptions - PROP-017

- Registries generated by `p2p registry refresh` are available or can be generated before intake.
- Intake results are advisory and must not bypass governance.
- The first MVP can use keyword/context packaging instead of embeddings.
- The user or agent can pass the generated prompt to Codex, Claude, ChatGPT or another model.
- Imported intake output should remain versioned under `.p2p/`.
- Multi-agent use can initially be coordinated through shared files and Git, without MCP.

### PROP-018 - Choice Management CLI MVP

#### assumptions.md

# Assumptions - PROP-018

None identified yet.

### PROP-019 - Proposal Decision Shortcut Commands

#### assumptions.md

# Assumptions - PROP-019

None identified yet.

### PROP-020 - Proposal Inspection CLI MVP

#### assumptions.md

# Assumptions - PROP-020

None identified yet.

### PROP-021 - Agent Skill Real Commands Update

#### assumptions.md

# Assumptions - PROP-021

None identified yet.

### PROP-022 - Operational Brief Prompt Workflow

#### assumptions.md

# Assumptions - PROP-022

None identified yet.

### PROP-023 - Next Action Recommender MVP

#### assumptions.md

# Assumptions - PROP-023

None identified yet.

### PROP-024 - Choice Blocking and Discovery MVP

#### assumptions.md

# Assumptions - PROP-024

None identified yet.

### PROP-025 - Controlled Intake Apply Workflow

#### assumptions.md

# Assumptions - PROP-025

None identified yet.

### PROP-026 - P2P Software Spec Generator MVP

#### assumptions.md

# Assumptions - PROP-026

None identified yet.

### PROP-027 - Software Spec Exporter MVP

#### assumptions.md

# Assumptions - PROP-027

None identified yet.

### PROP-028 - Spec Kit Export Mapping MVP

#### assumptions.md

# Assumptions - PROP-028

None identified yet.

### PROP-029 - Spec Export Validation MVP

#### assumptions.md

# Assumptions - PROP-029

None identified yet.

### PROP-030 - Managed Work and Multi-Branch Visibility Policy

#### assumptions.md

# Assumptions - PROP-030

None identified yet.

### PROP-031 - Multi-Branch Work Scan MVP

#### assumptions.md

# Assumptions - PROP-031

None identified yet.

### PROP-032 - Managed Work Branch Creation MVP

#### assumptions.md

# Assumptions - PROP-032

None identified yet.

### PROP-033 - Managed Work Submit MVP

#### assumptions.md

# Assumptions - PROP-033

None identified yet.

### PROP-034 - Managed Work Review MVP

#### assumptions.md

# Assumptions - PROP-034

None identified yet.

### PROP-035 - Managed Work Publish MVP

#### assumptions.md

# Assumptions - PROP-035

None identified yet.

### PROP-036 - Managed Work Accept MVP

#### assumptions.md

# Assumptions - PROP-036

None identified yet.

### PROP-037 - Managed Work Status Summary MVP

#### assumptions.md

# Assumptions - PROP-037

None identified yet.

### PROP-038 - Managed Work Merge Conflict Guidance MVP

#### assumptions.md

# Assumptions - PROP-038

None identified yet.

### PROP-039 - Managed Work Finalize MVP

#### assumptions.md

# Assumptions - PROP-039

None identified yet.

### PROP-040 - Managed Work Cleanup MVP

#### assumptions.md

# Assumptions - PROP-040

None identified yet.

### PROP-041 - Remote Project Profile and Review Request Policy

#### assumptions.md

# Assumptions - PROP-041

None identified yet.

### PROP-042 - P2P Core CLI MCP Mediator Web Boundary

#### assumptions.md

# Assumptions - PROP-042

None identified yet.

### PROP-043 - Managed Work Retire MVP

#### assumptions.md

# Assumptions - PROP-043

None identified yet.

### PROP-044 - P2P MCP Server MVP

#### assumptions.md

# Assumptions - PROP-044

None identified yet.

### PROP-045 - Agent-Safe Project Bootstrap MVP

#### assumptions.md

# Assumptions - PROP-045

None identified yet.

### PROP-046 - MCP Write-Safe Bootstrap Tools MVP

#### assumptions.md

# Assumptions - PROP-046

None identified yet.

### PROP-047 - Guided Init Wizard MVP

#### assumptions.md

# Assumptions - PROP-047

None identified yet.

### PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

#### assumptions.md

# Assumptions - PROP-048

None identified yet.

### PROP-049 - MCP Level 4A Proposal Refinement Tools

#### assumptions.md

# Assumptions - PROP-049

None identified yet.

### PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

#### assumptions.md

# Assumptions - PROP-050

None identified yet.

### PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

#### assumptions.md

# Assumptions - PROP-051

None identified yet.

### PROP-052 - MCP Proposal Contribution Tool

#### assumptions.md

# Assumptions - PROP-052

None identified yet.

### PROP-053 - Core Validation Layer MVP

#### assumptions.md

# Assumptions - PROP-053

None identified yet.

### PROP-054 - Project Readiness and Maturity Assessment

#### assumptions.md

# Assumptions - PROP-054

- P2P Core must remain deterministic and provider-neutral.
- Assessment output is advisory and cannot make or block governance decisions by itself.
- Existing validation, registries, choices, Change Sets, Work items and operational brief state are sufficient inputs for a Level 1 readiness MVP.
- Domain maturity cannot be fully deterministic across all project types.
- Rubric-based maturity should require explicit project-type criteria and recorded evidence.
- MCP exposure, if added, should initially be read-only or use existing write-safe prompt/artifact patterns.
- The first implementation should prefer explainable factor status over complex weighted scoring.

### PROP-055 - Agent Token Budget and Context Discipline

#### assumptions.md

# Assumptions - PROP-055

None identified yet.

### PROP-056 - Project Definition Maturity Rubrics

#### assumptions.md

# Assumptions - PROP-056

None identified yet.

### PROP-057 - Guided Rubric Selection During Init

#### assumptions.md

# Assumptions - PROP-057

None identified yet.

### PROP-058 - Project README and Installation Guide

#### assumptions.md

# Assumptions - PROP-058

None identified yet.

### PROP-059 - P2PWorkspace Modular Refactoring Plan

#### assumptions.md

# Assumptions - PROP-059

None identified yet.

### PROP-061 - Focused README and Documentation Map

#### assumptions.md

# Assumptions - PROP-061

None identified yet.

### PROP-062 - README Product Landing Page Refinement

#### assumptions.md

# Assumptions - PROP-062

None identified yet.

### PROP-064 - Spec Kit Three-Prompt Export Model

#### assumptions.md

# Assumptions - PROP-064

None identified yet.

### PROP-065 - MCP Agent-First Coverage Expansion

#### assumptions.md

# Assumptions - PROP-065

None identified yet.

### PROP-066 - Permission-Gated MCP Governance And Git Operations

#### assumptions.md

# Assumptions - PROP-066

None identified yet.

### PROP-067 - Agent-First Setup Documentation Split

#### assumptions.md

# Assumptions - PROP-067

None identified yet.

### PROP-068 - Document Agent MCP Client Setup Commands

#### assumptions.md

# Assumptions - PROP-068

None identified yet.

### PROP-069 - Clarify MCP Stdio Integration Model

#### assumptions.md

# Assumptions - PROP-069

None identified yet.

### PROP-070 - Clarify README Agent Access Modes

#### assumptions.md

# Assumptions - PROP-070

None identified yet.

### PROP-071 - Custom Domain Definition Workflow

#### assumptions.md

# Assumptions - PROP-071

None identified yet.

### PROP-072 - Concurrent Managed Work and Merge Decision Model

#### assumptions.md

# Assumptions - PROP-072

None identified yet.

### PROP-073 - Ergonomic Remote Project Initialization

#### assumptions.md

# Assumptions - PROP-073

None identified yet.

### PROP-074 - Agent Runtime Bootstrap Robustness

#### assumptions.md

# Assumptions - PROP-074

None identified yet.

### PROP-075 - MCP End-To-End Proposal Collaboration Workflow

#### assumptions.md

# Assumptions - PROP-075

None identified yet.

### PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

#### assumptions.md

# Assumptions - PROP-076

None identified yet.

### PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

#### assumptions.md

# Assumptions - PROP-077

None identified yet.

### PROP-078 - Project-Local Wheel Installation and Upgrade Model

#### assumptions.md

# Assumptions - PROP-078

None identified yet.

### PROP-079 - Managed Next Action Lifecycle

#### assumptions.md

# Assumptions - PROP-079

None identified yet.

### PROP-080 - Automated GitHub Release Wheel Publishing

#### assumptions.md

# Assumptions - PROP-080

None identified yet.

### PROP-081 - MCP and Skill Support for Managed Next Actions

#### assumptions.md

# Assumptions - PROP-081

None identified yet.

### PROP-082 - Readiness Assessment Refresh And Review Workflow

#### assumptions.md

# Assumptions - PROP-082

## Readiness is the main behavior signal

The system does not need a separate pedantry score in the MVP. Agent
assertiveness can be derived from readiness score, label, failed gates,
confidence, missing criteria, unanswered questions, and question/group state.

## Stepped assertiveness is sufficient

The agent can follow readiness bands:

- very low readiness: strongly proactive, challenge assumptions, ask the next
  blocking question, and avoid acceptance recommendations;
- partial readiness: continue the interview, focus on missing artifacts and
  high-risk ambiguity;
- near target readiness: ask only residual high-value questions or request
  confirmation;
- owner-muted or explicitly deferred areas: do not re-ask by default unless the
  owner asks to increase readiness or revisit muted/deferred questions.

## Question state replaces a dedicated "stop working on this" index

The existing question and group states can represent owner intent:

- `to_answer`: keep asking when relevant;
- `defer`: skip for now, keep available;
- `muted`: skip by default unless explicitly revisited;
- `answered` and `applied`: use the answer to refine artifacts;
- `retired` and `superseded`: preserve history without re-asking obsolete
  questions.

## Answers may affect multiple artifacts

A single owner answer can legitimately update proposal text, acceptance
criteria, alternatives, risks, assumptions, open questions, impact analysis, or
readiness evidence. Application should be artifact-aware rather than
one-question-to-one-file.

## Low readiness requires agent initiative

When readiness is low, failed, or low-confidence, the skill should instruct the
agent to take initiative: inspect gaps, update questions, ask the next focused
question, and record the answer. The agent should not wait for the owner to ask
what to do next.

### PROP-083 - Domain-Aware Visible Project Definition Export

#### assumptions.md

# Assumptions

## Human-readable project definition is a primary output

The default export should serve humans first. It should be useful to an owner,
stakeholder, or implementing agent without requiring direct inspection of
managed `.p2p/` internals.

## P2P Engine must remain domain-generic

The default export cannot assume that the project is software. It must be able
to describe different verticals using the same generic project-definition
structure, while allowing vertical-specific profiles to add extra output forms.

## `outputs/` is an acceptable root-level convention

The MVP can use a fixed root-level `outputs/` directory. It does not need a
configurable destination yet because a single convention is clearer and reduces
implementation surface.

## `outputs/latest/project.md` is the canonical default export

The default project definition should be a single chaptered Markdown document.
Specialized profile exports can use additional folders and formats under
`outputs/latest/exports/`.

## Review history should be preserved

Each refresh should make it possible to inspect previous generated versions
through review directories such as `outputs/review-001`, `outputs/review-002`,
and later snapshots.

## Existing `.p2p/outputs` behavior may still be depended on

Even if current generated outputs appear disposable, compatibility must be
checked before removal or relocation. The proposal assumes implementation will
preserve or migrate existing public behavior deliberately.

## P2P memory contains enough structured input to synthesize the document

The first implementation can synthesize from accepted proposals, decisions,
requirements, risks, assumptions, choices, scope notes, readiness notes, and
related P2P artifacts. Gaps should be surfaced in the generated document rather
than silently invented.

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

#### assumptions.md

# Assumptions - PROP-085

- Vertical packs are pure data in the MVP, primarily `.yaml` and/or `.md`.
- `base_project` is a concrete pack with a default cross-domain structure, not
  only a conceptual fallback.
- Default packs are distributed internally with the project/package as versioned
  and testable resources.
- Project-local custom packs are allowed and take precedence over core defaults.
- The MVP introduces a project vertical CLI surface because the current CLI only
  exposes project domains/rubrics and does not yet list, show, add, or validate
  vertical packs.
- A future registry may expose REST endpoints for listing available packs and
  fetching pack details, but registry behavior is outside the first slice.
- The CLI remains deterministic and does not launch the agent.
- Agent proactivity is delivered through generated/local skills and project
  instructions.
- Vertical packs extend and reuse existing project rubrics and maturity/readiness
  artifacts.
- Backward compatibility is required for projects without vertical packs.
- The first slice can prove the architecture with one complete demonstration
  vertical rather than the later five-vertical MVP set.

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

#### assumptions.md

# Assumptions - PROP-086

None identified yet.

### PROP-087 - Agent Personality Model For Decision Mediation

#### assumptions.md

# Assumptions - PROP-087

- The decision owner wants a shared project interaction contract across agents.
- The current behavior corresponds to `assertiveness=0`.
- `technical_verbosity=2` and `formality=2` are acceptable defaults for normal
  mediation.
- The first implementation does not need per-agent or per-session overrides.
- Numeric scales are easier to validate and evolve than named persona presets.
- Generated agent instructions are the first consumer of the model.
- CLI and MCP should be the public mutation surfaces for interaction style.

## Open Questions

### PROP-002 - Proposal Exploration And Readiness Workflow

#### open-questions.md

# Open Questions - PROP-002

## Resolved Product Decisions

These questions are no longer treated as open for the current direction of
PROP-002. They are recorded here as design decisions or MVP leanings.

1. `explore import` should support both a single file and a directory with named
   exploration artifacts.

   Current state: directory import is already supported by the CLI.

2. `findings.md` should remain human-readable Markdown.

   Exploration is primarily authored, reviewed, and discussed by humans and
   agents. Structured data should still exist, but as derived metadata,
   readiness snapshots, registries, or exports. Do not replace `findings.md`
   with mandatory `findings.yml`.

3. `explore status` should distinguish more than file existence.

   It should evolve toward artifact quality states:

   ```text
   missing
   placeholder
   thin
   meaningful
   needs_owner_input
   ready
   ```

   Optional future states such as `blocked_by_dependency`, `stale`, and
   `superseded` are deferred.

4. Agent skills and MCP-facing workflows must become methodologically strict.

   The agent is not sovereign, but it must behave as a method guardian: inspect
   readiness, identify missing alternatives, detect thin artifacts, surface owner
   questions, and avoid turning weak exploration into confident recommendations.

5. Readiness must be profile-based and versioned.

   The 10-criterion model is the first default profile, not a hardcoded forever
   model.

   ```yaml
   readiness_profile:
     id: default-readiness-v0.1
     version: 0.1
     criteria: []
     thresholds: {}
     gates: {}
     override_policy: {}
   ```

   Every computed score must record `profile_id`, `profile_version`, and
   `computed_at`.

6. The MVP readiness score uses a 0-100 default profile with explicit criteria
   and weights.

   | Criterion | Points |
   | --- | ---: |
   | Problem clarity | 10 |
   | Goal clarity | 10 |
   | Scope boundaries | 10 |
   | Alternatives quality | 15 |
   | Tradeoff analysis | 10 |
   | Risk coverage | 10 |
   | Assumptions clarity | 10 |
   | Owner questions resolution | 10 |
   | Acceptance criteria quality | 10 |
   | Impact and overlap analysis | 5 |
   | Total | 100 |

7. `Alternatives quality` should carry extra weight.

   It receives 15 points because the core observed failure is
   solution-first proposal writing.

8. PROP-002 is `governance-critical`.

   It defines how P2P Engine explores, evaluates, challenges, and moves future
   proposals toward decision.

9. Tier and maturity interact through `required_score_for_decision`, minimum
   gates, confidence, and artifact quality gates.

   A high total score is not enough for important proposals if essential
   criteria fail.

10. Artificial completeness should be countered with artifact quality gates and
    criterion-level evidence.

    A criterion cannot receive a high score unless supporting artifacts are at
    least `meaningful` and contain proposal-specific evidence.

11. `p2p next` must report readiness gaps and actionable next steps as part of
    the readiness-driven workflow.

    Useful output should include current score, target score, missing points,
    failed gates, and highest-impact actions.

12. Owner override must not falsify `computed_score`.

    Override creates a governance event and may set `effective_status:
    forced_ready` or `effective_score: 100`, but it must preserve the analytical
    computed score.

13. `override_reason` is mandatory when accepting below target readiness.

    Without a reason, override becomes indistinguishable from accidental bypass.

14. Governance gates must be configurable.

    The product model must support warning, blocking automatic
    `ready_for_decision`, blocking acceptance for critical governance violations,
    allowing override, and requiring reasons.

15. Low maturity should not simply be "warn" or "block".

    Default policy:

    ```text
    low maturity -> warning
    below required score -> strong warning
    failed minimum gates -> block automatic ready_for_decision
    owner override -> allowed with reason
    critical governance violation -> block acceptance
    ```

16. Acceptable owner override requires owner authority, explicit reason,
    acknowledgement of failed gates, computed score preservation, and audit
    event.

17. Legacy accepted proposals must not be rewritten or invalidated.

    New proposals and current open drafts should use readiness. Accepted legacy
    proposals should preserve historical decisions and may be marked or assessed
    retrospectively.

18. Small proposals should have a lightweight path, not a zero-governance path.

    Small proposals still need problem, goal, scope, acceptance criteria, and a
    lightweight risk check. They do not always need a full alternative matrix or
    deep risk register.

19. Analytical labels should be derived; owner decisions should create effective
    governance statuses.

    Example:

    ```yaml
    computed_label: partial
    effective_status: forced_ready
    owner_override: true
    ```

20. High score with low confidence should not automatically be
    `ready_for_decision`.

    Decision readiness requires score target, minimum gates, and required
    confidence. Governance-critical proposals should require at least medium
    confidence before automatic readiness promotion.

21. Proposal tier should be suggested by the agent/system and confirmed by the
    owner.

    The system should warn when the confirmed tier appears inconsistent with
    evidence.

22. Readiness should be required before implementation planning, but at a lower
    threshold than acceptance.

    Planning and decision are different gates.

23. Multi-criteria alternative comparison informs but does not automate the
    owner decision.

    The system may recommend an alternative with rationale and dissenting risks,
    but the owner selects the final option explicitly.

24. Readiness should apply immediately to all open drafts and all new proposals.

    Already accepted proposals should use legacy markers or optional
    retrospective assessment, not retroactive blocking.

25. Readiness should be included in registries as a snapshot/cache, not as the
    source of truth.

## Resolved Implementation Decisions

These are product-level implementation decisions for PROP-002, with progressive
implementation allowed. They should not be treated as temporary MVP shortcuts.

1. Storage should use a layered model.

   ```text
   readiness profile -> scoring rules
   proposal artifacts -> source material
   criterion assessment -> evidence and criterion-level score
   readiness snapshot -> latest computed result
   registry entry -> fast project-level lookup
   decision/audit log -> overrides and governance events
   ```

   `readiness.yml` stores the latest assessment and criterion evidence. It must
   not silently override proposal artifacts or decision records.

2. Readiness commands belong under proposal.

   Recommended command family:

   ```bash
   p2p proposal readiness PROP-002
   p2p proposal readiness refresh PROP-002
   p2p proposal readiness explain PROP-002
   ```

   `p2p explore status` remains focused on artifact quality.

3. Readiness override happens during owner acceptance.

   Primary command:

   ```bash
   p2p proposal accept PROP-002 --override-readiness --reason "..."
   ```

   A standalone readiness override command is not the primary model because it
   can imply that the computed readiness is being edited. Override is a
   governance decision, not score correction.

4. MCP is read-first and write/governance operations are permission-gated.

   MCP read tools are available to agents. MCP write/governance tools are part
   of the product model, but require explicit governance permission and must not
   be agent-autonomous.

5. Confidence is qualitative and hybrid.

   It is derived from evidence quality, unresolved owner questions, assumptions,
   realness of alternatives, risk clarity, and whether the assessment has owner
   review. It should not pretend to be a precise numeric formula in the first
   product model.

6. `p2p next` should rank readiness actions gate-first, then by recoverable
   points.

   Failed gates outrank raw point gain. Recoverable points still help estimate
   which action produces the most improvement.

7. Existing open drafts should be migrated as `not_assessed`.

   `p2p next` should surface readiness assessment as a recommended action
   instead of auto-generating noisy assessments for every draft.

8. Validation should be progressive.

   ```text
   schema/profile invalid -> error
   registry stale -> warning initially
   below threshold -> warning or policy gate
   failed gates -> block automatic ready_for_decision
   accept below threshold -> requires override reason
   ```

9. Artifact quality assessment should be hybrid and include `needs_owner_input`.

   Deterministic checks catch missing, placeholder, and obvious thin artifacts.
   Agent assessment classifies `meaningful`, `ready`, and `needs_owner_input`
   with evidence.

   `needs_owner_input` is not the same as `thin`: an artifact may be well formed
   but blocked because the owner must choose a policy, strictness level, or
   strategic direction.

10. Criterion evidence should use structured data plus Markdown notes.

    The assessment should be machine-readable enough for audit and `p2p next`,
    while remaining understandable to humans.

## Remaining Naming And Schema Details

These are no longer product direction questions. They are concrete naming,
schema, and sequencing details to settle during implementation planning.

1. Exact file paths for readiness profiles, proposal assessment files, registry
   snapshots, and audit events.

   Current leaning:

   ```text
   .p2p/config/readiness-profiles/default-readiness-v0.1.yml
   .p2p/proposals/PROP-XXX/readiness.yml
   .p2p/registries/readiness.yml
   decision/audit event for override
   ```

2. Exact MCP tool names.

   Current leaning:

   ```text
   p2p_proposal_readiness_get
   p2p_proposal_readiness_explain
   p2p_proposal_readiness_refresh
   p2p_proposal_readiness_list_gaps
   p2p_proposal_accept_with_override
   ```

3. Exact confidence labels and rule text.

   Current leaning:

   ```text
   low    -> mostly inferred, weak evidence, unresolved key questions
   medium -> sufficient evidence, some unresolved assumptions, usable for review
   high   -> strong evidence, owner questions resolved, alternatives compared, risks explicit
   ```

4. Exact estimated-gain ranking formula for `p2p next`.

   Current leaning:

   ```text
   priority =
     failed_gate_weight
     + recoverable_points
     + tier_importance
     + dependency_unblocking_value
   ```

5. Exact migration mechanics for existing open drafts.

   Current leaning: mark as `not_assessed`, and let `p2p next` recommend a
   readiness refresh when useful.

6. Exact validation severity per command and governance policy.

   Current leaning: strict schema/profile validation immediately, warnings for
   staleness and low readiness initially, hard gates only for automatic
   readiness promotion and missing override reason.

7. Exact deterministic heuristics for artifact quality.

   Current leaning: deterministic detection for missing, placeholder, and
   obvious thin artifacts; imported agent assessment for richer quality states.

8. Exact criterion-level evidence schema.

   Current leaning:

   ```yaml
   criteria:
     alternatives_quality:
       max_points: 15
       awarded_points: 11
       artifact_quality: meaningful
       evidence:
         - artifact: alternatives.md
           section: Alternative F - Hybrid Exploration And Readiness Model
       notes: "Alternative reali presenti, ma manca matrice comparativa completa."
   ```

9. Exact handling of the current unresolved-question counter.

   Current finding: `p2p explore status` may not reflect all implementation
   decision points. Future status/readiness logic should distinguish explicit
   questions, decision items, grouped subtopics, and artifact quality states.

### PROP-004 - Prompt-only Import Workflow

#### open-questions.md

# Open Questions - PROP-004

None identified yet.

### PROP-005 - Codex Skill Integration

#### open-questions.md

# Open Questions - PROP-005

None identified yet.

### PROP-006 - Multi-Agent Integration Model

#### open-questions.md

# Open Questions - PROP-006

## Resolved Direction

These points are no longer open for the current direction of PROP-006.

1. Basic agent profiles already exist.

   Current implementation supports `generic`, `codex`, `claude`, and `all`
   through `p2p init --agent ...` and `p2p agent instructions refresh
   --profile ...`.

2. The initial model should remain file-based.

   P2P Engine should generate project-local instruction files and structured
   registry metadata. It should not invoke AI providers directly.

3. Agents are adapters, not source of truth.

   P2P CLI, `.p2p` state, validation, readiness, and owner decisions remain
   authoritative.

4. MCP is a capability and operating channel, not a replacement for generated
   instructions.

   Generated instructions explain the method, workflow, guardrails, and which
   channel to prefer. CLI exposes textual commands for humans, scripts, CI, and
   agents with shell access. MCP exposes the same P2P capabilities as structured
   tools for MCP-compatible agents.

5. CLI and MCP should sit above the same P2P core behavior.

   The architecture must avoid divergent behavior where CLI writes one shape of
   `.p2p` state and MCP writes another. MCP tools may call shared core methods
   directly, or use CLI as an implementation bridge initially, but the behavior
   must stay equivalent.

6. `AGENTS.md` remains the shared baseline.

   Tool-specific files may supplement it, but the common project boundary should
   remain readable by generic agents and tools that support `AGENTS.md`.

7. Default project init should install all supported project-local adapters.

   The default setup should create useful files for `generic`, `codex`,
   `claude`, `cursor`, `copilot`, `gemini`, and `opencode`, unless the owner
   explicitly asks for a narrower set.

8. `generic` is the common baseline and cannot be removed.

   `generic` represents the portable project baseline. Installing or removing a
   specific agent must not remove the generic baseline.

9. There should be no project-level preferred/default/active agent.

   P2P Engine should not care whether one collaborator uses Codex and another
   uses Claude. Agent integrations are installed because somebody needs them.
   Their coexistence is the design goal.

10. `p2p agent use`, `switch`, `current`, and `--no-use` are out of scope.

    Without an active/default agent concept, these commands are unnecessary.
    The useful inspection command is `p2p agent list`, `p2p agent status`, or
    `p2p agent show <agent>`.

11. Installing all supported agent integrations should be possible.

    `p2p agent install all` may create all supported project-local agent files,
    provided adapters do not overwrite each other and shared files are handled
    explicitly.

12. Uninstall removes only files specific to that agent.

    Shared files such as `AGENTS.md` and `.p2p/agent-policy.yml` are baseline
    files and should not be removed by uninstalling a specific agent. Agent
    uninstall removes only that adapter's non-shared managed files when safe.

13. Drift means manual modification of a generated file.

    If P2P generated a file and stored its hash, but the current file hash no
    longer matches, the file has drifted. Update must not silently overwrite
    drifted files.

14. MCP agent tools should be implemented with the CLI-facing lifecycle, not
    deferred for a separate product phase.

    Read and write-safe MCP tools can ship in the same Change Set as the CLI as
    long as they call the same underlying core behavior and preserve the same
    safety checks.

15. `.cursorrules` should not be generated.

    Cursor project rules live in `.cursor/rules`; `.cursorrules` is legacy.

16. `opencode.json` should not be generated by default.

    OpenCode can use `AGENTS.md`. Generate `opencode.json` only when P2P needs a
    concrete configuration for additional instruction paths or permissions.

17. The initial named adapter set is not experimental.

    `generic`, `codex`, `claude`, `cursor`, `copilot`, `gemini`, and `opencode`
    are treated as supported built-in adapters. If an adapter has weaker
    generated content in the first implementation, expose a maturity label
    rather than hiding it behind `--experimental`.

18. Shared `.agents/skills` content is allowed only when agent-neutral.

    `.agents/skills/p2p-project/SKILL.md` may be generated for Codex-compatible
    project skills only if its content is written as a general P2P project skill
    and does not depend on Codex-only behavior. If this cannot be guaranteed,
    the shared skill file must be deferred and the adapter should rely on
    `AGENTS.md` plus tool-specific instruction files.

19. Existing `.codex/skills/p2p-project/SKILL.md` is a compatibility path, not
    the general cross-agent model.

    Existing projects using `.codex/skills/...` should not be broken. New
    generation should prefer the verified shared/project-local path when safe,
    while migration preserves or marks the old path according to registry
    ownership and hash state.

20. Agent incisiveness belongs to the common P2P method policy.

    The problem of an agent being insufficiently proactive is not solved only
    by adding more adapter files. The generic baseline must instruct every
    agent to transform readiness gaps into concrete refinement actions,
    alternatives, recommendations, owner questions, candidate edits, and
    readiness re-checks.

21. Dedicated readiness refinement commands are valuable but not required for
    the file-registry MVP.

    PROP-006 should include the behavioral contract in generated instructions
    now. Full commands such as `p2p proposal readiness next`, `p2p proposal
    refine`, or equivalent MCP tools can be implemented in this proposal only
    if scope allows, otherwise they remain future work or belong to a
    readiness-focused follow-up.

## Resolved Implementation Decisions

These decisions are concrete enough for implementation planning. Small internal
names may still change during coding if behavior and validation remain
equivalent.

1. `.p2p/agent-integrations.yml` uses a versioned manifest schema.

   MVP shape:

   ```yaml
   schema_version: 1
   baseline_profile: generic
   generated_at: "2026-06-05T00:00:00Z"
   adapters:
     codex:
       status: installed
       maturity: stable
       template_version: agent-template-v1
       capabilities:
         mcp: supported
         shell: supported
         project_instructions: true
       files:
         - path: AGENTS.md
           shared: true
           owner: generic
           managed: true
           template_id: generic-agents-md-v1
           sha256: "..."
           drift: clean
         - path: .agents/skills/p2p-project/SKILL.md
           shared: false
           owner: codex
           managed: true
           template_id: codex-p2p-skill-v1
           sha256: "..."
           drift: clean
   ```

   The registry must not contain `active_agent`, `default_agent`,
   `preferred_agent`, `current_agent`, `use`, or `switch` state.

2. Adapter templates live in package data for the MVP.

   Decision:

   ```text
   src/p2p_engine/templates/agents/<adapter>/<file-template>
   ```

   Internal Python rendering may fill variables such as project name,
   repository mode, and MCP hints. Project-local template overrides are
   deferred.

3. Hashing uses SHA-256 over exact file bytes.

   Do not normalize line endings, whitespace, or Markdown formatting before
   hashing. A file is `drifted` when the current byte hash differs from the
   stored hash.

4. Generated files use a short managed header where the target format supports
   comments or plain Markdown.

   Recommended Markdown header:

   ```markdown
   <!--
   Managed by P2P Engine.
   Adapter: codex
   Template: codex-p2p-skill-v1
   Do not edit generated sections unless you accept drift.
   -->
   ```

   The registry remains authoritative for hashes. The header is a human hint,
   not the source of truth.

5. `p2p agent doctor <agent|all>` checks registry, files, drift, conflicts, and
   method behavior.

   Checks:

   - registry exists and validates;
   - installed files exist;
   - hashes match;
   - shared files are still referenced;
   - `generic` baseline exists;
   - adapter documentation hints are available;
   - no adapter claims ownership of a non-shared file owned by another adapter;
   - no uninstall would remove a shared baseline file;
   - generated instruction files include the generic method behavior block.

6. Existing projects migrate conservatively.

   Migration behavior:

   - if an existing file matches a known generated template hash, mark it
     `managed`;
   - if an existing file exists but does not match, mark it `unmanaged` or
     `drifted`;
   - do not overwrite unmanaged or drifted files during migration;
   - preserve `.codex/skills/...` as compatibility if present;
   - always ensure the `generic` baseline exists or report the missing baseline
     through `doctor`.

7. The generic readiness gap handling block uses fixed MVP wording.

   Baseline text:

   ```text
   When a proposal is weak, low-confidence, below target, or has failed
   readiness gates, do not stop at diagnosis.

   For each failed gate or material gap:
   1. explain why the gate failed in proposal-specific terms;
   2. propose one to three concrete alternatives;
   3. recommend one option when evidence supports a recommendation;
   4. identify the owner decision required;
   5. draft the exact artifact update that would close the gap;
   6. ask for confirmation only where owner authority is required;
   7. re-check or request readiness re-check after refinement.
   ```

   Adapter-specific files may rephrase this text only if they preserve all
   behavioral requirements.

8. Future readiness refinement commands should live under proposal readiness.

   Current leaning:

   ```bash
   p2p proposal readiness next PROP-XXX
   p2p proposal readiness refine PROP-XXX
   p2p proposal readiness questions PROP-XXX
   ```

   MCP equivalents can mirror the concept:

   ```text
   p2p_proposal_readiness_next
   p2p_proposal_readiness_refine
   p2p_proposal_readiness_questions
   ```

   PROP-006 does not need to implement these commands to be accepted, but the
   generated instructions must be compatible with this future surface.

## Remaining Open Questions

None for product acceptance.

### PROP-009 - Governance CLI Commands

#### open-questions.md

# Open Questions - PROP-009

None identified yet.

### PROP-010 - P2P Project State Model

#### open-questions.md

# Open Questions - PROP-010

1. Should `.p2p/outputs/` be committed to Git by default, or treated as regenerable build output?
2. Should `p2p decision record --outcome accepted` refresh outputs automatically in the MVP, or should refresh begin as an explicit command?
3. What is the minimum shape of a P2P software spec: requirements, modules, interfaces, commands, data model, acceptance tests?
4. Should one accepted proposal update one spec module, or can one proposal update multiple modules?
5. How should conflicts be handled when two accepted proposals modify the same output section?
6. Should generated output include provenance links back to proposal IDs and decision IDs?
7. Should OpenSpec/Spec Kit exports be generated from `.p2p/outputs/software-spec/` only, or may they also include proposal history as appendix material?

### PROP-011 - Project Refresh MVP

#### open-questions.md

# Open Questions - PROP-011

None identified yet.

### PROP-012 - Impact Map and Conflict Memory

#### open-questions.md

# Open Questions - PROP-012

None identified yet.

### PROP-013 - Managed Git Adapter and Change Set Model

#### open-questions.md

# Open Questions - PROP-013

None. Structural Change Set policy questions are resolved for the MVP.

### PROP-014 - Change Set Metadata MVP

#### open-questions.md

# Open Questions - PROP-014

None identified yet.

### PROP-015 - Change Set Lifecycle and Task Tracking

#### open-questions.md

# Open Questions - PROP-015

None identified yet.

### PROP-016 - Project Registries MVP

#### open-questions.md

# Open Questions - PROP-016

All initial questions have been answered in `clarifications.md`.

## Resolved Questions

1. Registries should live under `.p2p/registries/`.
2. Registries should be committed to Git by default because they support audit, review, AI context loading and export reproducibility.
3. Registry refresh should have a dedicated command: `p2p registry refresh`.
4. MVP registry records should contain compact metadata: id, title, status, path, source references and relations.
5. Manual registry edits are unsupported and may be overwritten on refresh.

## Remaining Questions

None for the MVP proposal.

### PROP-017 - Proposal Intake and Context Analysis MVP

#### open-questions.md

# Open Questions - PROP-017

## Resolved For MVP

1. Direct AI calls are excluded from the MVP.
   - No. MVP remains prompt-only.

2. Proposal acceptance and rejection remain outside intake.
   - No. Intake only recommends next actions.

3. Intake uses generated registries as compact project memory.
   - Yes. Registries are the compact project memory layer for intake.

4. Multi-user and multi-agent workflows are supported through shared artifacts first.
   - Yes, but initially through shared `.p2p/` artifacts, not MCP.

## Still Open

1. Should intake artifacts use `.p2p/intake/` or live inside each proposal directory?
2. Should `p2p proposal create` optionally run intake first?
3. What minimum structured schema should `suggested-actions.yml` use?

### PROP-018 - Choice Management CLI MVP

#### open-questions.md

# Open Questions - PROP-018

None identified yet.

### PROP-019 - Proposal Decision Shortcut Commands

#### open-questions.md

# Open Questions - PROP-019

None identified yet.

### PROP-020 - Proposal Inspection CLI MVP

#### open-questions.md

# Open Questions - PROP-020

None identified yet.

### PROP-021 - Agent Skill Real Commands Update

#### open-questions.md

# Open Questions - PROP-021

None identified yet.

### PROP-022 - Operational Brief Prompt Workflow

#### open-questions.md

# Open Questions - PROP-022

None identified yet.

### PROP-023 - Next Action Recommender MVP

#### open-questions.md

# Open Questions - PROP-023

None identified yet.

### PROP-024 - Choice Blocking and Discovery MVP

#### open-questions.md

# Open Questions - PROP-024

None identified yet.

### PROP-025 - Controlled Intake Apply Workflow

#### open-questions.md

# Open Questions - PROP-025

None identified yet.

### PROP-026 - P2P Software Spec Generator MVP

#### open-questions.md

# Open Questions - PROP-026

None identified yet.

### PROP-027 - Software Spec Exporter MVP

#### open-questions.md

# Open Questions - PROP-027

None identified yet.

### PROP-028 - Spec Kit Export Mapping MVP

#### open-questions.md

# Open Questions - PROP-028

None identified yet.

### PROP-029 - Spec Export Validation MVP

#### open-questions.md

# Open Questions - PROP-029

None identified yet.

### PROP-030 - Managed Work and Multi-Branch Visibility Policy

#### open-questions.md

# Open Questions - PROP-030

None identified yet.

### PROP-031 - Multi-Branch Work Scan MVP

#### open-questions.md

# Open Questions - PROP-031

None identified yet.

### PROP-032 - Managed Work Branch Creation MVP

#### open-questions.md

# Open Questions - PROP-032

None identified yet.

### PROP-033 - Managed Work Submit MVP

#### open-questions.md

# Open Questions - PROP-033

None identified yet.

### PROP-034 - Managed Work Review MVP

#### open-questions.md

# Open Questions - PROP-034

None identified yet.

### PROP-035 - Managed Work Publish MVP

#### open-questions.md

# Open Questions - PROP-035

None identified yet.

### PROP-036 - Managed Work Accept MVP

#### open-questions.md

# Open Questions - PROP-036

None identified yet.

### PROP-037 - Managed Work Status Summary MVP

#### open-questions.md

# Open Questions - PROP-037

None identified yet.

### PROP-038 - Managed Work Merge Conflict Guidance MVP

#### open-questions.md

# Open Questions - PROP-038

None identified yet.

### PROP-039 - Managed Work Finalize MVP

#### open-questions.md

# Open Questions - PROP-039

None identified yet.

### PROP-040 - Managed Work Cleanup MVP

#### open-questions.md

# Open Questions - PROP-040

None identified yet.

### PROP-041 - Remote Project Profile and Review Request Policy

#### open-questions.md

# Open Questions - PROP-041

None identified yet.

### PROP-042 - P2P Core CLI MCP Mediator Web Boundary

#### open-questions.md

# Open Questions - PROP-042

None identified yet.

### PROP-043 - Managed Work Retire MVP

#### open-questions.md

# Open Questions - PROP-043

None identified yet.

### PROP-044 - P2P MCP Server MVP

#### open-questions.md

# Open Questions - PROP-044

None identified yet.

### PROP-045 - Agent-Safe Project Bootstrap MVP

#### open-questions.md

# Open Questions - PROP-045

None identified yet.

### PROP-046 - MCP Write-Safe Bootstrap Tools MVP

#### open-questions.md

# Open Questions - PROP-046

None identified yet.

### PROP-047 - Guided Init Wizard MVP

#### open-questions.md

# Open Questions - PROP-047

None identified yet.

### PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

#### open-questions.md

# Open Questions - PROP-048

None identified yet.

### PROP-049 - MCP Level 4A Proposal Refinement Tools

#### open-questions.md

# Open Questions - PROP-049

None identified yet.

### PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

#### open-questions.md

# Open Questions - PROP-050

None identified yet.

### PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

#### open-questions.md

# Open Questions - PROP-051

None identified yet.

### PROP-052 - MCP Proposal Contribution Tool

#### open-questions.md

# Open Questions - PROP-052

None identified yet.

### PROP-053 - Core Validation Layer MVP

#### open-questions.md

# Open Questions - PROP-053

None identified yet.

### PROP-054 - Project Readiness and Maturity Assessment

#### open-questions.md

# Open Questions - PROP-054

- What readiness scale should the MVP use: percentage, status band, checklist completion, risk level, or a combined model?
- Which deterministic signals are mandatory for Level 1?
- Should draft proposals reduce readiness, or only unresolved blockers and active work?
- How should stale operational briefs affect readiness if registries and validation are current?
- Should assessment output be computed on demand or written by `p2p assess refresh`?
- Where should assessment artifacts live: `.p2p/project/assessment.yml`, `.p2p/assessments/current.yml`, or another path?
- Should `p2p next` consume assessment gaps, or should assessment consume `p2p next` output?
- What is the minimum rubric format needed to support future maturity assessment?
- Should the first MVP include only CLI commands, or also MCP read-only tools?
- What project types should be recognized initially: generic, software, documentation, governance, mixed, or user-defined?

### PROP-055 - Agent Token Budget and Context Discipline

#### open-questions.md

# Open Questions - PROP-055

None identified yet.

### PROP-056 - Project Definition Maturity Rubrics

#### open-questions.md

# Open Questions - PROP-056

None identified yet.

### PROP-057 - Guided Rubric Selection During Init

#### open-questions.md

# Open Questions - PROP-057

None identified yet.

### PROP-058 - Project README and Installation Guide

#### open-questions.md

# Open Questions - PROP-058

None identified yet.

### PROP-059 - P2PWorkspace Modular Refactoring Plan

#### open-questions.md

# Open Questions - PROP-059

None identified yet.

### PROP-061 - Focused README and Documentation Map

#### open-questions.md

# Open Questions - PROP-061

None identified yet.

### PROP-062 - README Product Landing Page Refinement

#### open-questions.md

# Open Questions - PROP-062

None identified yet.

### PROP-064 - Spec Kit Three-Prompt Export Model

#### open-questions.md

# Open Questions - PROP-064

None identified yet.

### PROP-065 - MCP Agent-First Coverage Expansion

#### open-questions.md

# Open Questions - PROP-065

None identified yet.

### PROP-066 - Permission-Gated MCP Governance And Git Operations

#### open-questions.md

# Open Questions - PROP-066

None identified yet.

### PROP-067 - Agent-First Setup Documentation Split

#### open-questions.md

# Open Questions - PROP-067

None identified yet.

### PROP-068 - Document Agent MCP Client Setup Commands

#### open-questions.md

# Open Questions - PROP-068

None identified yet.

### PROP-069 - Clarify MCP Stdio Integration Model

#### open-questions.md

# Open Questions - PROP-069

None identified yet.

### PROP-070 - Clarify README Agent Access Modes

#### open-questions.md

# Open Questions - PROP-070

None identified yet.

### PROP-071 - Custom Domain Definition Workflow

#### open-questions.md

# Open Questions - PROP-071

None identified yet.

### PROP-072 - Concurrent Managed Work and Merge Decision Model

#### open-questions.md

# Open Questions - PROP-072

None identified yet.

### PROP-073 - Ergonomic Remote Project Initialization

#### open-questions.md

# Open Questions - PROP-073

None identified yet.

### PROP-074 - Agent Runtime Bootstrap Robustness

#### open-questions.md

# Open Questions - PROP-074

None identified yet.

### PROP-075 - MCP End-To-End Proposal Collaboration Workflow

#### open-questions.md

# Open Questions - PROP-075

None identified yet.

### PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

#### open-questions.md

# Open Questions - PROP-076

None identified yet.

### PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

#### open-questions.md

# Open Questions - PROP-077

None identified yet.

### PROP-078 - Project-Local Wheel Installation and Upgrade Model

#### open-questions.md

# Open Questions - PROP-078

None identified yet.

### PROP-079 - Managed Next Action Lifecycle

#### open-questions.md

# Open Questions - PROP-079

None identified yet.

### PROP-080 - Automated GitHub Release Wheel Publishing

#### open-questions.md

# Open Questions - PROP-080

None identified yet.

### PROP-081 - MCP and Skill Support for Managed Next Actions

#### open-questions.md

# Open Questions - PROP-081

None identified yet.

### PROP-082 - Readiness Assessment Refresh And Review Workflow

#### open-questions.md

# Open Questions - PROP-082

No unresolved owner questions remain for the current product direction.

## Resolved Direction

- Questions generated by readiness review must seek coverage across the full
  proposal artifact set, not only the missing readiness score criteria.
- Applying answers must update every useful affected artifact through supported
  CLI/MCP write primitives.
- No dedicated pedantry index is required for the MVP.
- Agent assertiveness should follow a stepped readiness policy: stronger when
  readiness is low, less intrusive as readiness approaches target.
- Existing question and group states are sufficient to represent owner intent to
  continue, defer, mute, apply, retire, or supersede questions.
- Low readiness must cause the skill to direct the agent to proactively
  interview the owner, record answers, apply them, and recompute readiness.

## Deferred Implementation Design Choices

- Exact command names for evidence-aware reassessment beyond the current
  `review` output.
- Exact schema for imported structured readiness assessments.
- Exact artifact update plan format returned by `questions apply`.
- Exact confidence promotion thresholds after evidence-aware reassessment.

### PROP-083 - Domain-Aware Visible Project Definition Export

#### open-questions.md

# Open Questions

No unresolved owner questions remain for the current proposal definition.

## Resolved Owner Inputs

- The visible generated output root is `outputs/`, not `project/`.
- The default export destination is fixed for the MVP and is not configurable.
- The canonical default document is `outputs/latest/project.md`.
- The default export is a single chaptered Markdown document.
- Specialized vertical exports are nested under `outputs/latest/exports/<profile-or-vertical>/`.
- Software-specific exports are profile outputs and are not the default representation.
- Existing `.p2p/outputs` artifacts must be treated as a compatibility surface and checked before removal.

## Implementation Decisions Deferred To Design

- Exact CLI command naming for generating the visible project definition.
- Exact renderer/service class layout.
- Whether legacy `.p2p/outputs` is mirrored, deprecated, migrated, or kept unchanged after compatibility analysis.
- Retention policy for old `outputs/review-###/` snapshots beyond deterministic creation.

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

#### open-questions.md

# Open Questions - PROP-085

No owner-blocking questions remain for the MVP proposal.

Deferred follow-up topics, explicitly outside the first slice:

- Exact REST API shape for a future vertical registry.
- Selection of the first complete demonstration vertical.
- Selection of the later five-vertical MVP set after the first slice proves the
  pack model.
- Possible publishing flow from project-local custom verticals to a shared
  registry.

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

#### open-questions.md

# Open Questions - PROP-086

None identified yet.

### PROP-087 - Agent Personality Model For Decision Mediation

#### open-questions.md

# Open Questions - PROP-087

All owner-facing questions needed for the current proposal direction have been
answered.

Resolved:

- Scope: project-level default.
- Defaults: `technical_verbosity=2`, `formality=2`, `assertiveness=0`.
- Presets: not persisted in the first implementation.
- Assertiveness: included in first implementation.
- CLI/MCP namespace: `project interaction-style`.

No remaining blocking owner question is currently known.

## Readiness

### Project Vertical Skeleton

- active_vertical: base_project
- source: fallback
- fallback_used: true

### Vertical Coverage

- vision: covered (proposals: PROP-001, PROP-002, PROP-003, PROP-006, PROP-010, PROP-011, PROP-013, PROP-014, PROP-015, PROP-016, PROP-017, PROP-018, PROP-021, PROP-022, PROP-023, PROP-024, PROP-025, PROP-026, PROP-027, PROP-028, PROP-029, PROP-030, PROP-031, PROP-032, PROP-033, PROP-034, PROP-035, PROP-037, PROP-038, PROP-039, PROP-040, PROP-041, PROP-042, PROP-043, PROP-044, PROP-045, PROP-046, PROP-048, PROP-049, PROP-050, PROP-051, PROP-052, PROP-054, PROP-055, PROP-056, PROP-057, PROP-058, PROP-059, PROP-060, PROP-061, PROP-062, PROP-063, PROP-064, PROP-065, PROP-066, PROP-067, PROP-069, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-076, PROP-077, PROP-080, PROP-081, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-087, PROP-089)
- objective: covered (proposals: PROP-001, PROP-002, PROP-003, PROP-004, PROP-005, PROP-006, PROP-007, PROP-008, PROP-009, PROP-010, PROP-011, PROP-012, PROP-013, PROP-014, PROP-015, PROP-016, PROP-017, PROP-018, PROP-019, PROP-020, PROP-021, PROP-022, PROP-023, PROP-024, PROP-025, PROP-026, PROP-027, PROP-028, PROP-029, PROP-030, PROP-031, PROP-032, PROP-033, PROP-034, PROP-035, PROP-036, PROP-037, PROP-038, PROP-039, PROP-040, PROP-041, PROP-042, PROP-043, PROP-044, PROP-045, PROP-046, PROP-047, PROP-048, PROP-049, PROP-050, PROP-051, PROP-052, PROP-053, PROP-054, PROP-055, PROP-056, PROP-057, PROP-058, PROP-059, PROP-060, PROP-061, PROP-062, PROP-063, PROP-064, PROP-065, PROP-066, PROP-067, PROP-068, PROP-069, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-076, PROP-077, PROP-078, PROP-079, PROP-080, PROP-081, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-087, PROP-088, PROP-089)
- stakeholders: covered (proposals: PROP-001, PROP-002, PROP-006, PROP-008, PROP-009, PROP-010, PROP-013, PROP-016, PROP-017, PROP-018, PROP-019, PROP-020, PROP-022, PROP-023, PROP-024, PROP-030, PROP-032, PROP-033, PROP-034, PROP-035, PROP-036, PROP-037, PROP-038, PROP-039, PROP-040, PROP-041, PROP-042, PROP-045, PROP-046, PROP-047, PROP-048, PROP-049, PROP-051, PROP-053, PROP-054, PROP-055, PROP-056, PROP-057, PROP-058, PROP-059, PROP-061, PROP-063, PROP-064, PROP-065, PROP-066, PROP-067, PROP-068, PROP-069, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-076, PROP-077, PROP-078, PROP-079, PROP-080, PROP-081, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-087, PROP-088, PROP-089)
- scope: covered (proposals: PROP-001, PROP-002, PROP-003, PROP-004, PROP-005, PROP-006, PROP-007, PROP-008, PROP-009, PROP-010, PROP-011, PROP-012, PROP-013, PROP-014, PROP-015, PROP-016, PROP-017, PROP-018, PROP-019, PROP-020, PROP-021, PROP-022, PROP-023, PROP-024, PROP-025, PROP-026, PROP-027, PROP-028, PROP-029, PROP-030, PROP-031, PROP-032, PROP-033, PROP-034, PROP-035, PROP-036, PROP-037, PROP-038, PROP-039, PROP-040, PROP-041, PROP-042, PROP-043, PROP-044, PROP-045, PROP-046, PROP-047, PROP-048, PROP-049, PROP-050, PROP-051, PROP-052, PROP-053, PROP-054, PROP-055, PROP-056, PROP-057, PROP-058, PROP-059, PROP-060, PROP-061, PROP-062, PROP-063, PROP-064, PROP-065, PROP-066, PROP-067, PROP-068, PROP-069, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-076, PROP-077, PROP-078, PROP-079, PROP-080, PROP-081, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-087, PROP-088, PROP-089)
- assumptions: covered (proposals: PROP-001, PROP-002, PROP-003, PROP-004, PROP-005, PROP-006, PROP-007, PROP-009, PROP-011, PROP-013, PROP-016, PROP-017, PROP-019, PROP-021, PROP-022, PROP-025, PROP-026, PROP-030, PROP-031, PROP-032, PROP-033, PROP-034, PROP-035, PROP-036, PROP-037, PROP-038, PROP-039, PROP-040, PROP-041, PROP-042, PROP-043, PROP-044, PROP-046, PROP-048, PROP-049, PROP-050, PROP-051, PROP-053, PROP-054, PROP-055, PROP-056, PROP-058, PROP-059, PROP-060, PROP-062, PROP-063, PROP-064, PROP-065, PROP-066, PROP-067, PROP-069, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-076, PROP-077, PROP-080, PROP-081, PROP-082, PROP-083, PROP-085, PROP-086, PROP-088)
- risks: covered (proposals: PROP-001, PROP-002, PROP-004, PROP-005, PROP-006, PROP-007, PROP-008, PROP-009, PROP-010, PROP-011, PROP-012, PROP-013, PROP-014, PROP-015, PROP-016, PROP-017, PROP-018, PROP-019, PROP-020, PROP-021, PROP-022, PROP-023, PROP-024, PROP-025, PROP-026, PROP-027, PROP-028, PROP-029, PROP-030, PROP-031, PROP-032, PROP-033, PROP-034, PROP-035, PROP-036, PROP-037, PROP-038, PROP-039, PROP-040, PROP-041, PROP-042, PROP-043, PROP-044, PROP-045, PROP-046, PROP-047, PROP-048, PROP-049, PROP-050, PROP-051, PROP-052, PROP-053, PROP-054, PROP-055, PROP-056, PROP-057, PROP-058, PROP-059, PROP-060, PROP-061, PROP-062, PROP-063, PROP-064, PROP-065, PROP-066, PROP-067, PROP-068, PROP-069, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-076, PROP-077, PROP-078, PROP-079, PROP-080, PROP-081, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-087, PROP-088, PROP-089)
- decisions: covered (proposals: PROP-001, PROP-002, PROP-003, PROP-005, PROP-006, PROP-008, PROP-009, PROP-010, PROP-011, PROP-012, PROP-013, PROP-014, PROP-016, PROP-017, PROP-018, PROP-019, PROP-020, PROP-021, PROP-022, PROP-023, PROP-024, PROP-025, PROP-026, PROP-027, PROP-028, PROP-029, PROP-030, PROP-032, PROP-033, PROP-034, PROP-035, PROP-036, PROP-039, PROP-040, PROP-041, PROP-042, PROP-045, PROP-046, PROP-048, PROP-049, PROP-050, PROP-051, PROP-052, PROP-053, PROP-054, PROP-055, PROP-056, PROP-057, PROP-059, PROP-060, PROP-064, PROP-065, PROP-066, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-077, PROP-078, PROP-079, PROP-080, PROP-081, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-087, PROP-088, PROP-089)
- milestones: covered (proposals: PROP-001, PROP-002, PROP-006, PROP-007, PROP-010, PROP-012, PROP-013, PROP-015, PROP-016, PROP-017, PROP-018, PROP-019, PROP-022, PROP-023, PROP-024, PROP-025, PROP-026, PROP-027, PROP-030, PROP-031, PROP-032, PROP-033, PROP-037, PROP-043, PROP-044, PROP-046, PROP-047, PROP-048, PROP-049, PROP-050, PROP-051, PROP-053, PROP-054, PROP-055, PROP-056, PROP-057, PROP-058, PROP-059, PROP-064, PROP-065, PROP-066, PROP-067, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-076, PROP-077, PROP-078, PROP-079, PROP-080, PROP-081, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-088)
- definition_of_done: covered (proposals: PROP-001, PROP-002, PROP-003, PROP-004, PROP-005, PROP-006, PROP-007, PROP-008, PROP-009, PROP-010, PROP-011, PROP-012, PROP-013, PROP-014, PROP-015, PROP-016, PROP-017, PROP-018, PROP-019, PROP-020, PROP-021, PROP-022, PROP-023, PROP-024, PROP-025, PROP-026, PROP-027, PROP-028, PROP-029, PROP-030, PROP-031, PROP-032, PROP-033, PROP-034, PROP-035, PROP-036, PROP-037, PROP-038, PROP-039, PROP-040, PROP-041, PROP-042, PROP-043, PROP-044, PROP-045, PROP-046, PROP-047, PROP-048, PROP-049, PROP-050, PROP-051, PROP-052, PROP-053, PROP-054, PROP-055, PROP-056, PROP-057, PROP-058, PROP-059, PROP-060, PROP-061, PROP-062, PROP-063, PROP-064, PROP-065, PROP-066, PROP-067, PROP-068, PROP-069, PROP-070, PROP-071, PROP-072, PROP-073, PROP-074, PROP-075, PROP-076, PROP-077, PROP-078, PROP-079, PROP-080, PROP-081, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-087, PROP-088, PROP-089)
- artifacts: covered (proposals: PROP-001, PROP-002, PROP-003, PROP-004, PROP-005, PROP-006, PROP-007, PROP-010, PROP-011, PROP-012, PROP-013, PROP-015, PROP-016, PROP-017, PROP-018, PROP-019, PROP-022, PROP-024, PROP-026, PROP-027, PROP-028, PROP-029, PROP-031, PROP-032, PROP-033, PROP-034, PROP-035, PROP-036, PROP-037, PROP-038, PROP-039, PROP-040, PROP-041, PROP-048, PROP-049, PROP-050, PROP-051, PROP-052, PROP-053, PROP-054, PROP-055, PROP-056, PROP-058, PROP-059, PROP-062, PROP-063, PROP-064, PROP-067, PROP-072, PROP-073, PROP-074, PROP-076, PROP-078, PROP-080, PROP-082, PROP-083, PROP-084, PROP-085, PROP-086, PROP-087, PROP-088, PROP-089)

### PROP-006 - Multi-Agent Integration Model

#### readiness.yml

readiness:
  status: assessed
  profile_id: default-readiness-v0.1
  profile_version: '0.1'
  tier: medium
  confidence: low
  confidence_reasons:
  - Initial readiness was bootstrapped from proposal artifacts.
  - Review criterion evidence before using it for acceptance.
  missing: []
  suggested_next:
  - resolve_owner_questions_resolution
  failed_gates:
  - owner_questions_resolution:needs_owner_input
  criteria:
    problem_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Problem
      effective_points: 7
    goal_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Goals
      effective_points: 7
    scope_boundaries:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Non-Goals
      effective_points: 7
    alternatives_quality:
      max_points: 15
      awarded_points: 11
      artifact_quality: meaningful
      evidence:
      - artifact: alternatives.md
      effective_points: 11
    tradeoff_analysis:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: alternatives.md
      effective_points: 7
    risk_coverage:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: risks.md
      effective_points: 7
    assumptions_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: assumptions.md
      effective_points: 7
    owner_questions_resolution:
      max_points: 10
      awarded_points: 7
      artifact_quality: needs_owner_input
      evidence:
      - artifact: open-questions.md
      effective_points: 7
    acceptance_criteria_quality:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Acceptance Criteria
      effective_points: 7
    impact_overlap_analysis:
      max_points: 5
      awarded_points: 3
      artifact_quality: meaningful
      evidence:
      - artifact: impact-map.yml
      effective_points: 3
  computed_score: 70
  computed_label: partial
  computed_at: '2026-06-05'
  owner_override: true
  effective_status: forced_ready
  effective_score: 100
  override_reason: Owner accepts PROP-006 after refinement. The proposal is considered
    ready as-is because remaining low readiness score reflects the current conservative
    readiness CLI, not unresolved product direction. A separate follow-up proposal
    will address readiness assessment refresh and review workflow.
  override_approver: owner
  override_recorded_at: '2026-06-05'

### PROP-059 - P2PWorkspace Modular Refactoring Plan

#### readiness.yml

readiness:
  status: assessed
  profile_id: default-readiness-v0.1
  profile_version: '0.1'
  tier: medium
  confidence: low
  confidence_reasons:
  - Initial readiness was bootstrapped from proposal artifacts.
  - Review criterion evidence before using it for acceptance.
  missing:
  - scope_boundaries
  - alternatives_quality
  - tradeoff_analysis
  - risk_coverage
  - assumptions_clarity
  - owner_questions_resolution
  - acceptance_criteria_quality
  - impact_overlap_analysis
  suggested_next:
  - add_scope_boundaries
  - add_alternatives_quality
  - add_tradeoff_analysis
  - add_risk_coverage
  - add_assumptions_clarity
  - add_owner_questions_resolution
  - add_acceptance_criteria_quality
  - add_impact_overlap_analysis
  failed_gates: []
  criteria:
    problem_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Problem
      effective_points: 7
    goal_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Goals
      effective_points: 7
    scope_boundaries:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: proposal.md
        section: Non-Goals
      effective_points: 0
    alternatives_quality:
      max_points: 15
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: alternatives.md
      effective_points: 0
    tradeoff_analysis:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: alternatives.md
      effective_points: 0
    risk_coverage:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: risks.md
      effective_points: 0
    assumptions_clarity:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: assumptions.md
      effective_points: 0
    owner_questions_resolution:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: open-questions.md
      effective_points: 0
    acceptance_criteria_quality:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: proposal.md
        section: Acceptance Criteria
      effective_points: 0
    impact_overlap_analysis:
      max_points: 5
      awarded_points: 0
      artifact_quality: missing
      evidence:
      - artifact: impact-map.yml
      effective_points: 0
  computed_score: 14
  computed_label: weak
  computed_at: '2026-06-05'

### PROP-082 - Readiness Assessment Refresh And Review Workflow

#### readiness.yml

readiness:
  status: assessed
  profile_id: default-readiness-v0.1
  profile_version: '0.1'
  tier: medium
  confidence: high
  confidence_reasons:
  - Evidence-aware assessment found no missing criteria, failed gates, unresolved
    owner questions, or pending high-priority questions.
  - Criterion evidence was recalculated from current proposal artifacts.
  missing: []
  suggested_next: []
  failed_gates: []
  criteria:
    problem_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Problem
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    goal_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Goals
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    scope_boundaries:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Non-Goals
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    alternatives_quality:
      max_points: 15
      awarded_points: 15
      artifact_quality: ready
      evidence:
      - artifact: alternatives.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 15
    tradeoff_analysis:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: alternatives.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    risk_coverage:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: risks.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    assumptions_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: assumptions.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    owner_questions_resolution:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: open-questions.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    acceptance_criteria_quality:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Acceptance Criteria
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    impact_overlap_analysis:
      max_points: 5
      awarded_points: 5
      artifact_quality: ready
      evidence:
      - artifact: impact-map.yml
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 5
  computed_score: 100
  computed_label: decision_ready
  computed_at: '2026-06-08'
  assessment_source: evidence_aware
  assessed_at: '2026-06-08'
  owner_override: true
  effective_status: forced_ready
  effective_score: 100
  override_reason: Owner confirms the refined second-slice direction for artifact-aware
    proposal questions, stepped readiness-driven agent assertiveness, evidence-aware
    readiness recalculation, and proactive low-readiness interview behavior.
  override_approver: owner
  override_recorded_at: '2026-06-08'

### PROP-083 - Domain-Aware Visible Project Definition Export

#### readiness.yml

readiness:
  status: assessed
  profile_id: default-readiness-v0.1
  profile_version: '0.1'
  tier: medium
  confidence: low
  confidence_reasons:
  - Initial readiness was bootstrapped from proposal artifacts.
  - Review criterion evidence before using it for acceptance.
  missing: []
  suggested_next: []
  failed_gates: []
  criteria:
    problem_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Problem
      effective_points: 7
    goal_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Goals
      effective_points: 7
    scope_boundaries:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Non-Goals
      effective_points: 7
    alternatives_quality:
      max_points: 15
      awarded_points: 11
      artifact_quality: meaningful
      evidence:
      - artifact: alternatives.md
      effective_points: 11
    tradeoff_analysis:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: alternatives.md
      effective_points: 7
    risk_coverage:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: risks.md
      effective_points: 7
    assumptions_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: assumptions.md
      effective_points: 7
    owner_questions_resolution:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: open-questions.md
      effective_points: 7
    acceptance_criteria_quality:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Acceptance Criteria
      effective_points: 7
    impact_overlap_analysis:
      max_points: 5
      awarded_points: 3
      artifact_quality: meaningful
      evidence:
      - artifact: impact-map.yml
      effective_points: 3
  computed_score: 70
  computed_label: partial
  computed_at: '2026-06-08'
  owner_override: true
  effective_status: forced_ready
  effective_score: 100
  override_reason: Owner accepts the domain-aware visible project definition export.
    Readiness has no missing gaps after refinement, but computed score remains partial
    because the current readiness profile is conservative and keeps confidence low
    for artifact-derived assessments.
  override_approver: owner
  override_recorded_at: '2026-06-08'

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

#### readiness.yml

readiness:
  status: assessed
  profile_id: default-readiness-v0.1
  profile_version: '0.1'
  tier: medium
  confidence: high
  confidence_reasons:
  - Evidence-aware assessment found no missing criteria, failed gates, unresolved
    owner questions, or pending high-priority questions.
  - Criterion evidence was recalculated from current proposal artifacts.
  missing: []
  suggested_next: []
  failed_gates: []
  criteria:
    problem_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Problem
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    goal_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Goals
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    scope_boundaries:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Non-Goals
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    alternatives_quality:
      max_points: 15
      awarded_points: 15
      artifact_quality: ready
      evidence:
      - artifact: alternatives.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 15
    tradeoff_analysis:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: alternatives.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    risk_coverage:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: risks.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    assumptions_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: assumptions.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    owner_questions_resolution:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: open-questions.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    acceptance_criteria_quality:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Acceptance Criteria
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    impact_overlap_analysis:
      max_points: 5
      awarded_points: 5
      artifact_quality: ready
      evidence:
      - artifact: impact-map.yml
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 5
  computed_score: 100
  computed_label: decision_ready
  computed_at: '2026-06-09'
  assessment_source: evidence_aware
  assessed_at: '2026-06-09'

### PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

#### readiness.yml

readiness:
  status: assessed
  profile_id: default-readiness-v0.1
  profile_version: '0.1'
  tier: medium
  confidence: low
  confidence_reasons:
  - Initial readiness was bootstrapped from proposal artifacts.
  - Review criterion evidence before using it for acceptance.
  missing:
  - scope_boundaries
  - alternatives_quality
  - tradeoff_analysis
  - risk_coverage
  - assumptions_clarity
  - owner_questions_resolution
  - acceptance_criteria_quality
  - impact_overlap_analysis
  suggested_next:
  - add_scope_boundaries
  - add_alternatives_quality
  - add_tradeoff_analysis
  - add_risk_coverage
  - add_assumptions_clarity
  - add_owner_questions_resolution
  - add_acceptance_criteria_quality
  - add_impact_overlap_analysis
  failed_gates: []
  criteria:
    problem_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Problem
      effective_points: 7
    goal_clarity:
      max_points: 10
      awarded_points: 7
      artifact_quality: meaningful
      evidence:
      - artifact: proposal.md
        section: Goals
      effective_points: 7
    scope_boundaries:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: proposal.md
        section: Non-Goals
      effective_points: 0
    alternatives_quality:
      max_points: 15
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: alternatives.md
      effective_points: 0
    tradeoff_analysis:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: alternatives.md
      effective_points: 0
    risk_coverage:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: risks.md
      effective_points: 0
    assumptions_clarity:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: assumptions.md
      effective_points: 0
    owner_questions_resolution:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: open-questions.md
      effective_points: 0
    acceptance_criteria_quality:
      max_points: 10
      awarded_points: 0
      artifact_quality: placeholder
      evidence:
      - artifact: proposal.md
        section: Acceptance Criteria
      effective_points: 0
    impact_overlap_analysis:
      max_points: 5
      awarded_points: 0
      artifact_quality: missing
      evidence:
      - artifact: impact-map.yml
      effective_points: 0
  computed_score: 14
  computed_label: weak
  computed_at: '2026-06-09'
  owner_override: true
  effective_status: forced_ready
  effective_score: 100
  override_reason: 'Accepted by owner as an explicit readiness override. The current
    default-readiness-v0.1 score remains weak because it is not artifact-aware, but
    the owner accepts the refined direction: introduce a dedicated artifact-specific
    CLI/MCP primitive, graduated-by-risk artifact requirements, default coverage for
    new proposals, advisory absent_legacy handling for old proposals, strict CLI/MCP-only
    memory mutation, and tests for readiness/context/MCP/missing-primitive behavior.'
  override_approver: owner
  override_recorded_at: '2026-06-09'

### PROP-087 - Agent Personality Model For Decision Mediation

#### readiness.yml

readiness:
  status: assessed
  profile_id: default-readiness-v0.1
  profile_version: '0.1'
  tier: medium
  confidence: high
  confidence_reasons:
  - Evidence-aware assessment found no missing criteria, failed gates, unresolved
    owner questions, or pending high-priority questions.
  - Criterion evidence was recalculated from current proposal artifacts.
  missing: []
  suggested_next: []
  failed_gates: []
  criteria:
    problem_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Problem
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    goal_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Goals
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    scope_boundaries:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Non-Goals
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    alternatives_quality:
      max_points: 15
      awarded_points: 15
      artifact_quality: ready
      evidence:
      - artifact: alternatives.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 15
    tradeoff_analysis:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: alternatives.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    risk_coverage:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: risks.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    assumptions_clarity:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: assumptions.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    owner_questions_resolution:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: open-questions.md
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    acceptance_criteria_quality:
      max_points: 10
      awarded_points: 10
      artifact_quality: ready
      evidence:
      - artifact: proposal.md
        section: Acceptance Criteria
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 10
    impact_overlap_analysis:
      max_points: 5
      awarded_points: 5
      artifact_quality: ready
      evidence:
      - artifact: impact-map.yml
      - artifact: questions.yml
        reason: artifact evidence assessed with no unresolved blocking questions
      effective_points: 5
  computed_score: 100
  computed_label: decision_ready
  computed_at: '2026-06-09'
  assessment_source: evidence_aware
  assessed_at: '2026-06-09'
  artifact_coverage_warnings: []

## Delivery And Export Context

The default visible export is this chaptered Markdown document. Specialized vertical or tool-specific exports belong under `outputs/latest/exports/<profile-or-vertical>/`. Existing `.p2p/outputs` spec exports remain compatibility artifacts unless a separate migration changes them.

## Source Traceability

- .p2p/project.yml
- .p2p/proposals/
- .p2p/proposals/PROP-001-cli-foundation
- .p2p/proposals/PROP-002-exploration-phase
- .p2p/proposals/PROP-004-prompt-only-import-workflow
- .p2p/proposals/PROP-005-codex-skill-integration
- .p2p/proposals/PROP-006-multi-agent-integration-model
- .p2p/proposals/PROP-009-governance-cli-commands
- .p2p/proposals/PROP-010-p2p-software-specification-model
- .p2p/proposals/PROP-011-project-refresh-mvp
- .p2p/proposals/PROP-012-impact-map-and-conflict-memory
- .p2p/proposals/PROP-013-change-set-and-git-branch-model
- .p2p/proposals/PROP-014-change-set-metadata-mvp
- .p2p/proposals/PROP-015-change-set-lifecycle-and-task-tracking
- .p2p/proposals/PROP-016-project-registries-mvp
- .p2p/proposals/PROP-017-proposal-intake-and-context-analysis-mvp
- .p2p/proposals/PROP-018-choice-management-cli-mvp
- .p2p/proposals/PROP-019-proposal-decision-shortcut-commands
- .p2p/proposals/PROP-020-proposal-inspection-cli-mvp
- .p2p/proposals/PROP-021-agent-skill-real-commands-update
- .p2p/proposals/PROP-022-operational-brief-prompt-workflow
- .p2p/proposals/PROP-023-next-action-recommender-mvp
- .p2p/proposals/PROP-024-choice-blocking-and-discovery-mvp
- .p2p/proposals/PROP-025-controlled-intake-apply-workflow
- .p2p/proposals/PROP-026-p2p-software-spec-generator-mvp
- .p2p/proposals/PROP-027-software-spec-exporter-mvp
- .p2p/proposals/PROP-028-spec-kit-export-mapping-mvp
- .p2p/proposals/PROP-029-spec-export-validation-mvp
- .p2p/proposals/PROP-030-managed-work-and-multi-branch-visibility-policy
- .p2p/proposals/PROP-031-multi-branch-work-scan-mvp
- .p2p/proposals/PROP-032-managed-work-branch-creation-mvp
- .p2p/proposals/PROP-033-managed-work-submit-mvp
- .p2p/proposals/PROP-034-managed-work-review-mvp
- .p2p/proposals/PROP-035-managed-work-publish-mvp
- .p2p/proposals/PROP-036-managed-work-accept-mvp
- .p2p/proposals/PROP-037-managed-work-status-summary-mvp
- .p2p/proposals/PROP-038-managed-work-merge-conflict-guidance-mvp
- .p2p/proposals/PROP-039-managed-work-finalize-mvp
- .p2p/proposals/PROP-040-managed-work-cleanup-mvp
- .p2p/proposals/PROP-041-remote-project-profile-and-review-request-policy
- .p2p/proposals/PROP-042-p2p-core-cli-mcp-mediator-web-boundary
- .p2p/proposals/PROP-043-managed-work-retire-mvp
- .p2p/proposals/PROP-044-p2p-mcp-server-mvp
- .p2p/proposals/PROP-045-agent-safe-project-bootstrap-mvp
- .p2p/proposals/PROP-046-mcp-write-safe-bootstrap-tools-mvp
- .p2p/proposals/PROP-047-guided-init-wizard-mvp
- .p2p/proposals/PROP-048-mcp-level-3-proposal-and-intake-draft-tools
- .p2p/proposals/PROP-049-mcp-level-4a-proposal-refinement-tools
- .p2p/proposals/PROP-050-mcp-level-4b-choice-conflict-impact-advisory-tools
- .p2p/proposals/PROP-051-draft-proposal-next-action-and-agent-explanation-guard
- .p2p/proposals/PROP-052-mcp-proposal-contribution-tool
- .p2p/proposals/PROP-053-core-validation-layer-mvp
- .p2p/proposals/PROP-054-project-readiness-and-maturity-assessment
- .p2p/proposals/PROP-055-agent-token-budget-and-context-discipline
- .p2p/proposals/PROP-056-project-definition-maturity-rubrics
- .p2p/proposals/PROP-057-guided-rubric-selection-during-init
- .p2p/proposals/PROP-058-project-readme-and-installation-guide
- .p2p/proposals/PROP-059-p2pworkspace-modular-refactoring-plan
- .p2p/proposals/PROP-061-focused-readme-and-documentation-map
- .p2p/proposals/PROP-062-readme-product-landing-page-refinement
- .p2p/proposals/PROP-064-spec-kit-three-prompt-export-model
- .p2p/proposals/PROP-065-mcp-agent-first-coverage-expansion
- .p2p/proposals/PROP-066-permission-gated-mcp-governance-and-git-operations
- .p2p/proposals/PROP-067-agent-first-setup-documentation-split
- .p2p/proposals/PROP-068-document-agent-mcp-client-setup-commands
- .p2p/proposals/PROP-069-clarify-mcp-stdio-integration-model
- .p2p/proposals/PROP-070-clarify-readme-agent-access-modes
- .p2p/proposals/PROP-071-custom-domain-definition-workflow
- .p2p/proposals/PROP-072-concurrent-managed-work-and-merge-decision-model
- .p2p/proposals/PROP-073-ergonomic-remote-project-initialization
- .p2p/proposals/PROP-074-agent-runtime-bootstrap-robustness
- .p2p/proposals/PROP-075-mcp-end-to-end-proposal-collaboration-workflow
- .p2p/proposals/PROP-076-p2p-cloud-runner-boundary-and-containerized-execution-model
- .p2p/proposals/PROP-077-permission-gated-draft-proposal-decisions-via-mcp
- .p2p/proposals/PROP-078-project-local-wheel-installation-and-upgrade-model
- .p2p/proposals/PROP-079-managed-next-action-lifecycle
- .p2p/proposals/PROP-080-automated-github-release-wheel-publishing
- .p2p/proposals/PROP-081-mcp-and-skill-support-for-managed-next-actions
- .p2p/proposals/PROP-082-readiness-assessment-refresh-and-review-workflow
- .p2p/proposals/PROP-083-domain-aware-visible-project-definition-export
- .p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration
- .p2p/proposals/PROP-086-artifact-aware-proposal-readiness-and-agent-interview-orchestration
- .p2p/proposals/PROP-087-agent-personality-model-for-decision-mediation

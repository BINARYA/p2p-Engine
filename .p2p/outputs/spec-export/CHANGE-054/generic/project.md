# P2P Engine Project Definition

This document is synthesized from accepted P2P memory. It is the canonical generic project export. Draft or undecided material is listed only as pending or missing information.

## Executive Summary

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

## Vision

Organize confused, distributed, and discontinuous project intent into a governed project definition that agents can use without rediscovering context from scratch.

## Domain

software

## Problem

- **PROP-001 CLI Foundation**: P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.
- **PROP-004 Prompt-only Import Workflow**: P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.
- **PROP-005 Codex Skill Integration**: Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.
- **PROP-009 Governance CLI Commands**: P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.
- **PROP-010 P2P Project State Model**: Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.
- **PROP-011 Project Refresh MVP**: P2P Engine has accepted the .p2p/project state model, but the CLI cannot yet generate or inspect that rationalized project layer.
- **PROP-012 Impact Map and Conflict Memory**: P2P Engine can generate a rationalized project state, but it does not yet capture what a proposal touches or whether it overlaps, depends on, supersedes, or conflicts with other proposals.
- **PROP-013 Managed Git Adapter and Change Set Model**: P2P Engine distinguishes proposals from project state, but it does not yet define how accepted decisions become operational change sets or how Git operations should be managed under the hood without exposing branch/commit/merge complexity to users.

## Goals

- **PROP-001 CLI Foundation**: - Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.
- **PROP-004 Prompt-only Import Workflow**: - Aggiungere import per clarify, synthesize, plan e tasks.
- Rendere il workflow prompt-only end-to-end testabile.
- **PROP-005 Codex Skill Integration**: - Creare una skill Codex che guidi l'uso della CLI P2P e degli artefatti .p2p.
- Stabilire regole per trasformare conversazioni in proposal, exploration, decisioni, piani e task versionati.
- **PROP-009 Governance CLI Commands**: - Implementare p2p governance init/status.
- Implementare p2p swot prompt per alternative contrapposte.
- Implementare p2p vote record/status.
- Implementare p2p precedent record.
- **PROP-010 P2P Project State Model**: - Define a P2P-native project state generated from accepted proposals.
- Create a dedicated `.p2p/project/` area for rationalized project artifacts.
- Specify how accepted proposals update project state.
- Keep OpenSpec and Spec Kit as downstream exporters, not the source of truth.
- **PROP-011 Project Refresh MVP**: - Implement p2p project refresh to generate the first .p2p/project artifacts.
- Implement p2p project status to inspect generated project state.
- Implement p2p project show to read generated project sections.
- **PROP-012 Impact Map and Conflict Memory**: - Define proposal-level impact-map artifacts.
- Define conflict memory in .p2p/project/conflicts.yml.
- Add prompt-only analysis for impact, overlap, dependencies, and conflicts.
- Add CLI commands to record and inspect conflicts.
- **PROP-013 Managed Git Adapter and Change Set Model**: - Define Change Set as the operational unit after proposal decision.
- Define Git as an internal adapter for persistence, audit, collaboration, and synchronization.
- Hide branch, commit, merge, and tag details from the default user experience.
- Reduce discretion in branch decisions through configurable Git policy.
- Preserve proposal and decision history in .p2p artifacts even when Git branches are removed.

## Non-Goals / Exclusions

- **PROP-001 CLI Foundation**: - No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.
- **PROP-004 Prompt-only Import Workflow**: - Non invocare provider AI direttamente.
- Non introdurre MCP.
- Non aggiungere web app o database.
- **PROP-005 Codex Skill Integration**: - Non introdurre MCP in questa fase.
- Non invocare direttamente provider AI dalla CLI.
- Non sostituire la CLI come sorgente di verita.
- **PROP-009 Governance CLI Commands**: - Implementare enforcement reale dei permessi applicativi.
- Integrare branch protection, CODEOWNERS o required approvals.
- Chiudere automaticamente votazioni o decisioni complesse.
- **PROP-010 P2P Project State Model**: - Implement a full OpenSpec or Spec Kit exporter in this proposal.
- Replace proposal, decision, plan, or task artifacts.
- **PROP-011 Project Refresh MVP**: - Implement OpenSpec or Spec Kit export.
- Implement automatic refresh after decision record.
- **PROP-012 Impact Map and Conflict Memory**: - Automatically reject proposals without human decision.
- Implement full AI agent invocation.
- **PROP-013 Managed Git Adapter and Change Set Model**: - Implement full Git branch automation in this proposal.
- Require users to understand or manually manage Git branches.
- Let AI agents bypass P2P CLI by manipulating Git directly.

## Stakeholders / Users

- Humans supervise outputs and make governance decisions.
- AI agents use P2P memory and exports as structured project cognition.
- Downstream tools receive initialization prompts or documents, not synthetic ownership of P2P state.

## Workflows

- Capture rough ideas as intake, proposals, or contributions.
- Decide accepted direction through owner-controlled P2P governance.
- Derive Change Sets and exports from accepted memory.
- Use target-specific outputs to initialize downstream agent workflows.

## Accepted Decisions

- **PROP-001 CLI Foundation**: # Decision — PROP-001 CLI Foundation

## Status

`accepted`

## Outcome

Build the first P2P Engine CLI as a local, Git-native, prompt-only Python application.

## Reason

The project needs a minimal executable workflow before adding AI adapters, exporters, MCP, or a web interface. Automating the manually bootstrapped `.p2p/` structure is the shortest path to dogfooding.

## Conditions

- Keep the MVP file-based.
- Do not add direct AI provider integration yet.
- Do not add a web app yet.
- Prefer explicit, inspectable artifacts over hidden state.
- Make generated files easy to edit manually.

## Date

2026-05-19

## Approver

bootstrap maintainer
- **PROP-004 Prompt-only Import Workflow**: # Decision - PROP-004

## Status

`accepted`

## Outcome

accepted

## Reason

Il workflow prompt-only deve essere completo: ogni fase che genera prompt deve poter importare l'output prodotto da AI, agenti esterni o dall'utente.

## Date

2026-05-19

## Approver

bootstrap maintainer
- **PROP-005 Codex Skill Integration**: # Decision - PROP-005

## Status

`accepted`

## Outcome

accepted

## Reason

P2P Engine now has enough CLI workflow surface for Codex to use it as a structured method. A local skill makes the expected behavior explicit and reduces the risk of leaving decisions only in chat.

## Date

2026-05-19

## Approver

bootstrap maintainer
- **PROP-009 Governance CLI Commands**: # Decision - PROP-009

## Status

`accepted`

## Outcome

accepted

## Reason

PROP-008 ha definito il modello di governance, ma senza comandi CLI il workflow resta solo documentale. I comandi governance, swot, vote e precedent rendono il modello provabile nel repository senza introdurre ancora un sistema di privilegi applicativi.

## Scope

- Inizializzare governance.yml, roles.yml e decision-precedents.yml.
- Generare prompt SWOT per alternative contrapposte.
- Registrare voti in votes.yml e mostrare conteggi.
- Registrare precedenti decisionali riutilizzabili.

## Constraints

- La governance MVP e audit-only.
- La decisione resta umana o governance-defined.
- Git resta il layer di audit e permessi reali fino a una fase successiva.
- **PROP-010 P2P Project State Model**: # Decision - PROP-010

## Status

`accepted`

## Outcome

accepted

## Reason

P2P Engine needs an internal rationalized project state before exporting to OpenSpec, Spec Kit, or task systems. Raw proposal folders contain discussion, governance, alternatives, and decision history; they should not be treated directly as implementation specifications.

## Decision

Create a versioned `.p2p/project/` layer.

The official `.p2p/project/` state lives on `main`. Proposal branches may contain preview changes. When a proposal is accepted and merged, the corresponding project-state changes become official.

## Initial Model

```text
.p2p/project/
  overview.md
  problem.md
  scope.md
  project-swot.md
  features/
    <feature-id>/
      feature.md
      tasks.yml
      actions.yml
  decisions-map.yml
  conflicts.yml
  exports/
    markdown/
    openspec/
    speckit/
```

## Refresh Policy

The MVP uses explicit refresh:

```bash
p2p project refresh
```

Automatic refresh after accepted decisions can be added later as an opt-in behavior.
- **PROP-011 Project Refresh MVP**: # Decision - PROP-011

## Status

`accepted`

## Outcome

accepted

## Reason

Project refresh MVP is implemented with deterministic .p2p/project generation and CLI inspection commands.

## Date

2026-05-19

## Approver

local
- **PROP-012 Impact Map and Conflict Memory**: # Decision - PROP-012

## Status

`accepted`

## Outcome

accepted

## Reason

Impact analysis and conflict memory are implemented as prompt-only impact artifacts plus persistent .p2p/project/conflicts.yml commands.

## Date

2026-05-20

## Approver

local
- **PROP-013 Managed Git Adapter and Change Set Model**: # Decision - PROP-013

## Status

`accepted`

## Outcome

accepted

## Decision

Adopt Alternative D - Managed Git Under The Hood.

## Reason

P2P Engine should expose proposal, choice, decision, change, and task concepts to users. Git remains the internal layer for persistence, audit, synchronization, and collaboration, but users should not need to reason about branches, commits, merges, or tags during normal workflows.

## MVP Policy

```yaml
git_policy:
  mode: managed
  operation_level: metadata_only
  expose_git_details: false
  commits:
    auto_commit: false
  branches:
    auto_create: false
  tags:
    auto_create: false
```

## Change Set Policy

- Change Sets can be created only from accepted proposals or accepted decisions.
- Draft proposals can be referenced as non-binding context.
- Change Sets are multi-domain.
- `.p2p/project/features/` is a derived project view.
- Future internal branches require `implementation_ready`, accepted source, plan, tasks, doctor OK, safe worktree or snapshot, recovery strategy, and explicit command or enabled policy.
- **PROP-014 Change Set Metadata MVP**: # Decision - PROP-014

## Status

`accepted`

## Outcome

accepted

## Reason

Change Set metadata MVP is implemented with create/status/policy commands and metadata-only managed Git policy.

## Date

2026-05-20

## Approver

local
- **PROP-015 Change Set Lifecycle and Task Tracking**: # Decision - PROP-015

## Status

`accepted`

## Outcome

accepted

## Reason

Change Set lifecycle transitions and task/action inspection are implemented with validated status changes and metadata-only behavior.

## Date

2026-05-20

## Approver

local
- **PROP-016 Project Registries MVP**: # Decision - PROP-016

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted as the next MVP step to introduce generated project registries for proposals, decisions, changes, choices, relations and artifacts.

## Date

2026-05-20

## Approver

local
- **PROP-017 Proposal Intake and Context Analysis MVP**: # Decision - PROP-017

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to add registry-backed proposal intake and context analysis as the next usability layer for multi-user and multi-agent P2P workflows.

## Date

2026-05-20

## Approver

local

## Requirements

## Functional Requirements

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

## Non-Goals / Exclusions

- Automatic Git commits, branches, tags, or merges.

## Constraints

Do not treat raw proposal discussion as implementation requirements without accepted scope.

## Open Questions

Not specified yet.

## Constraints

- Exports must not invent requirements unsupported by accepted P2P artifacts.
- Missing information must be marked as NEEDS CLARIFICATION.
- Draft proposals must not be treated as accepted project truth.

## Assumptions

- Accepted P2P proposals and decisions are authoritative project memory.
- Target-specific exports are initialization artifacts for agents or downstream tools.

## Dependencies

- Source Change Set: `CHANGE-054` Permission-Gated MCP Roles and Consent Receipts
- P2P software spec artifacts generated before export.
- Downstream tools, if used, run outside P2P export.

## Operating Model / Architecture

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- Change Set metadata.

## Data / Knowledge Model

```yaml
entities:
- name: ChangeSet
  description: Operational package derived from accepted project intent.
- name: SoftwareSpec
  description: P2P-native normalized implementation-facing specification.
- name: ExportTarget:openspec
  description: Downstream export target.
- name: ExportTarget:speckit
  description: Downstream export target.
- name: PROP-066
  description: Permission-Gated MCP Governance And Git Operations

```

## Priorities

- Preserve accepted project intent and governance first.
- Produce small agent-consumable outputs instead of downstream-shaped folders.
- Keep target-specific exports derived from this project definition.

## Success Criteria

## Criteria

- Change Set metadata is present and reviewable.

## Tests / Verification

- Not specified yet.

## Validation / Evaluation Method

- Validate required export files exist.
- Validate required project definition sections exist.
- Validate source traceability is present.

## Risks And Tradeoffs

- Removing folder-shaped exports may surprise users of the previous MVP export layout.
- Agent-first documents require clear traceability to avoid over-synthesis.

## Open Questions

- Which legacy bundle outputs, if any, should remain available behind an explicit compatibility flag?

## Pending Proposals

- `PROP-002` Exploration Phase
- `PROP-006` Multi-Agent Integration Model
- `PROP-007` Proposal Intake and Overlap Analysis
- `PROP-008` Governance Model
- `PROP-059` P2PWorkspace Modular Refactoring Plan
- `PROP-060` Real Test Coverage Reporting
- `PROP-063` Public Documentation Gap Closure
- `PROP-073` Ergonomic Remote Project Initialization

## Software Domain Extension

### Technical Architecture

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- Change Set metadata.

### CLI/API/UI Surface

```yaml
commands: []

```

### Testing Strategy

## Criteria

- Change Set metadata is present and reviewable.

## Tests / Verification

- Not specified yet.

### Deployment / Operations

NEEDS CLARIFICATION

### Integration Boundaries

- Implementation targets: local_cli
- Spec targets: p2p_spec
- Export targets: openspec, speckit


## Source Traceability

- Source Change Set: `CHANGE-054` Permission-Gated MCP Roles and Consent Receipts
- `PROP-001` CLI Foundation — `.p2p/proposals/PROP-001-cli-foundation`
- `PROP-004` Prompt-only Import Workflow — `.p2p/proposals/PROP-004-prompt-only-import-workflow`
- `PROP-005` Codex Skill Integration — `.p2p/proposals/PROP-005-codex-skill-integration`
- `PROP-009` Governance CLI Commands — `.p2p/proposals/PROP-009-governance-cli-commands`
- `PROP-010` P2P Project State Model — `.p2p/proposals/PROP-010-p2p-software-specification-model`
- `PROP-011` Project Refresh MVP — `.p2p/proposals/PROP-011-project-refresh-mvp`
- `PROP-012` Impact Map and Conflict Memory — `.p2p/proposals/PROP-012-impact-map-and-conflict-memory`
- `PROP-013` Managed Git Adapter and Change Set Model — `.p2p/proposals/PROP-013-change-set-and-git-branch-model`
- `PROP-014` Change Set Metadata MVP — `.p2p/proposals/PROP-014-change-set-metadata-mvp`
- `PROP-015` Change Set Lifecycle and Task Tracking — `.p2p/proposals/PROP-015-change-set-lifecycle-and-task-tracking`
- `PROP-016` Project Registries MVP — `.p2p/proposals/PROP-016-project-registries-mvp`
- `PROP-017` Proposal Intake and Context Analysis MVP — `.p2p/proposals/PROP-017-proposal-intake-and-context-analysis-mvp`
- `PROP-018` Choice Management CLI MVP — `.p2p/proposals/PROP-018-choice-management-cli-mvp`
- `PROP-019` Proposal Decision Shortcut Commands — `.p2p/proposals/PROP-019-proposal-decision-shortcut-commands`
- `PROP-020` Proposal Inspection CLI MVP — `.p2p/proposals/PROP-020-proposal-inspection-cli-mvp`
- `PROP-021` Agent Skill Real Commands Update — `.p2p/proposals/PROP-021-agent-skill-real-commands-update`
- `PROP-022` Operational Brief Prompt Workflow — `.p2p/proposals/PROP-022-operational-brief-prompt-workflow`
- `PROP-023` Next Action Recommender MVP — `.p2p/proposals/PROP-023-next-action-recommender-mvp`
- `PROP-024` Choice Blocking and Discovery MVP — `.p2p/proposals/PROP-024-choice-blocking-and-discovery-mvp`
- `PROP-025` Controlled Intake Apply Workflow — `.p2p/proposals/PROP-025-controlled-intake-apply-workflow`
- `PROP-026` P2P Software Spec Generator MVP — `.p2p/proposals/PROP-026-p2p-software-spec-generator-mvp`
- `PROP-027` Software Spec Exporter MVP — `.p2p/proposals/PROP-027-software-spec-exporter-mvp`
- `PROP-028` Spec Kit Export Mapping MVP — `.p2p/proposals/PROP-028-spec-kit-export-mapping-mvp`
- `PROP-029` Spec Export Validation MVP — `.p2p/proposals/PROP-029-spec-export-validation-mvp`
- `PROP-030` Managed Work and Multi-Branch Visibility Policy — `.p2p/proposals/PROP-030-managed-work-and-multi-branch-visibility-policy`
- `PROP-031` Multi-Branch Work Scan MVP — `.p2p/proposals/PROP-031-multi-branch-work-scan-mvp`
- `PROP-032` Managed Work Branch Creation MVP — `.p2p/proposals/PROP-032-managed-work-branch-creation-mvp`
- `PROP-033` Managed Work Submit MVP — `.p2p/proposals/PROP-033-managed-work-submit-mvp`
- `PROP-034` Managed Work Review MVP — `.p2p/proposals/PROP-034-managed-work-review-mvp`
- `PROP-035` Managed Work Publish MVP — `.p2p/proposals/PROP-035-managed-work-publish-mvp`
- `PROP-036` Managed Work Accept MVP — `.p2p/proposals/PROP-036-managed-work-accept-mvp`
- `PROP-037` Managed Work Status Summary MVP — `.p2p/proposals/PROP-037-managed-work-status-summary-mvp`
- `PROP-038` Managed Work Merge Conflict Guidance MVP — `.p2p/proposals/PROP-038-managed-work-merge-conflict-guidance-mvp`
- `PROP-039` Managed Work Finalize MVP — `.p2p/proposals/PROP-039-managed-work-finalize-mvp`
- `PROP-040` Managed Work Cleanup MVP — `.p2p/proposals/PROP-040-managed-work-cleanup-mvp`
- `PROP-041` Remote Project Profile and Review Request Policy — `.p2p/proposals/PROP-041-remote-project-profile-and-review-request-policy`
- `PROP-042` P2P Core CLI MCP Mediator Web Boundary — `.p2p/proposals/PROP-042-p2p-core-cli-mcp-mediator-web-boundary`
- `PROP-043` Managed Work Retire MVP — `.p2p/proposals/PROP-043-managed-work-retire-mvp`
- `PROP-044` P2P MCP Server MVP — `.p2p/proposals/PROP-044-p2p-mcp-server-mvp`
- `PROP-045` Agent-Safe Project Bootstrap MVP — `.p2p/proposals/PROP-045-agent-safe-project-bootstrap-mvp`
- `PROP-046` MCP Write-Safe Bootstrap Tools MVP — `.p2p/proposals/PROP-046-mcp-write-safe-bootstrap-tools-mvp`
- `PROP-047` Guided Init Wizard MVP — `.p2p/proposals/PROP-047-guided-init-wizard-mvp`
- `PROP-048` MCP Level 3 Proposal and Intake Draft Tools — `.p2p/proposals/PROP-048-mcp-level-3-proposal-and-intake-draft-tools`
- `PROP-049` MCP Level 4A Proposal Refinement Tools — `.p2p/proposals/PROP-049-mcp-level-4a-proposal-refinement-tools`
- `PROP-050` MCP Level 4B Choice Conflict Impact Advisory Tools — `.p2p/proposals/PROP-050-mcp-level-4b-choice-conflict-impact-advisory-tools`
- `PROP-051` Draft Proposal Next Action and Agent Explanation Guard — `.p2p/proposals/PROP-051-draft-proposal-next-action-and-agent-explanation-guard`
- `PROP-052` MCP Proposal Contribution Tool — `.p2p/proposals/PROP-052-mcp-proposal-contribution-tool`
- `PROP-053` Core Validation Layer MVP — `.p2p/proposals/PROP-053-core-validation-layer-mvp`
- `PROP-054` Project Readiness and Maturity Assessment — `.p2p/proposals/PROP-054-project-readiness-and-maturity-assessment`
- `PROP-055` Agent Token Budget and Context Discipline — `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline`
- `PROP-056` Project Definition Maturity Rubrics — `.p2p/proposals/PROP-056-project-definition-maturity-rubrics`
- `PROP-057` Guided Rubric Selection During Init — `.p2p/proposals/PROP-057-guided-rubric-selection-during-init`
- `PROP-058` Project README and Installation Guide — `.p2p/proposals/PROP-058-project-readme-and-installation-guide`
- `PROP-061` Focused README and Documentation Map — `.p2p/proposals/PROP-061-focused-readme-and-documentation-map`
- `PROP-062` README Product Landing Page Refinement — `.p2p/proposals/PROP-062-readme-product-landing-page-refinement`
- `PROP-064` Spec Kit Three-Prompt Export Model — `.p2p/proposals/PROP-064-spec-kit-three-prompt-export-model`
- `PROP-065` MCP Agent-First Coverage Expansion — `.p2p/proposals/PROP-065-mcp-agent-first-coverage-expansion`
- `PROP-066` Permission-Gated MCP Governance And Git Operations — `.p2p/proposals/PROP-066-permission-gated-mcp-governance-and-git-operations`
- `PROP-067` Agent-First Setup Documentation Split — `.p2p/proposals/PROP-067-agent-first-setup-documentation-split`
- `PROP-068` Document Agent MCP Client Setup Commands — `.p2p/proposals/PROP-068-document-agent-mcp-client-setup-commands`
- `PROP-069` Clarify MCP Stdio Integration Model — `.p2p/proposals/PROP-069-clarify-mcp-stdio-integration-model`
- `PROP-070` Clarify README Agent Access Modes — `.p2p/proposals/PROP-070-clarify-readme-agent-access-modes`
- `PROP-071` Custom Domain Definition Workflow — `.p2p/proposals/PROP-071-custom-domain-definition-workflow`
- `PROP-072` Concurrent Managed Work and Merge Decision Model — `.p2p/proposals/PROP-072-concurrent-managed-work-and-merge-decision-model`

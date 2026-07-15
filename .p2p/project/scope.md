# Project Scope

Generated from accepted proposal goals and non-goals.

## PROP-001 - — CLI Foundation

### Goals

- Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.

### Non-Goals

- No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.

## PROP-002 - Proposal Exploration And Readiness Workflow

### Goals

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

### Non-Goals

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

## PROP-004 - Prompt-only Import Workflow

### Goals

- Aggiungere import per clarify, synthesize, plan e tasks.
- Rendere il workflow prompt-only end-to-end testabile.

### Non-Goals

- Non invocare provider AI direttamente.
- Non introdurre MCP.
- Non aggiungere web app o database.

## PROP-005 - Codex Skill Integration

### Goals

- Creare una skill Codex che guidi l'uso della CLI P2P e degli artefatti .p2p.
- Stabilire regole per trasformare conversazioni in proposal, exploration, decisioni, piani e task versionati.

### Non-Goals

- Non introdurre MCP in questa fase.
- Non invocare direttamente provider AI dalla CLI.
- Non sostituire la CLI come sorgente di verita.

## PROP-006 - Multi-Agent Integration Model

### Goals

- Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.

### Non-Goals

- Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.

## PROP-009 - Governance CLI Commands

### Goals

- Implementare p2p governance init/status.
- Implementare p2p swot prompt per alternative contrapposte.
- Implementare p2p vote record/status.
- Implementare p2p precedent record.

### Non-Goals

- Implementare enforcement reale dei permessi applicativi.
- Integrare branch protection, CODEOWNERS o required approvals.
- Chiudere automaticamente votazioni o decisioni complesse.

## PROP-010 - P2P Project State Model

### Goals

- Define a P2P-native project state generated from accepted proposals.
- Create a dedicated `.p2p/project/` area for rationalized project artifacts.
- Specify how accepted proposals update project state.
- Keep OpenSpec and Spec Kit as downstream exporters, not the source of truth.

### Non-Goals

- Implement a full OpenSpec or Spec Kit exporter in this proposal.
- Replace proposal, decision, plan, or task artifacts.

## PROP-011 - Project Refresh MVP

### Goals

- Implement p2p project refresh to generate the first .p2p/project artifacts.
- Implement p2p project status to inspect generated project state.
- Implement p2p project show to read generated project sections.

### Non-Goals

- Implement OpenSpec or Spec Kit export.
- Implement automatic refresh after decision record.

## PROP-012 - Impact Map and Conflict Memory

### Goals

- Define proposal-level impact-map artifacts.
- Define conflict memory in .p2p/project/conflicts.yml.
- Add prompt-only analysis for impact, overlap, dependencies, and conflicts.
- Add CLI commands to record and inspect conflicts.

### Non-Goals

- Automatically reject proposals without human decision.
- Implement full AI agent invocation.

## PROP-013 - Managed Git Adapter and Change Set Model

### Goals

- Define Change Set as the operational unit after proposal decision.
- Define Git as an internal adapter for persistence, audit, collaboration, and synchronization.
- Hide branch, commit, merge, and tag details from the default user experience.
- Reduce discretion in branch decisions through configurable Git policy.
- Preserve proposal and decision history in .p2p artifacts even when Git branches are removed.

### Non-Goals

- Implement full Git branch automation in this proposal.
- Require users to understand or manually manage Git branches.
- Let AI agents bypass P2P CLI by manipulating Git directly.

## PROP-014 - Change Set Metadata MVP

### Goals

- Implement p2p change create --from PROP-XXX for accepted proposals.
- Generate .p2p/changes/CHANGE-XXX directories with change.md and metadata files.
- Implement p2p change status and p2p change policy.
- Reject Change Set creation from non-accepted proposals.

### Non-Goals

- Create Git commits, branches, merges, or tags.
- Implement OpenSpec or Spec Kit export.

## PROP-015 - Change Set Lifecycle and Task Tracking

### Goals

- Implement Change Set lifecycle transitions from proposed to completed.
- Validate allowed status transitions.
- Show tasks and actions for a Change Set.
- Keep the MVP metadata-only without Git writes.

### Non-Goals

- Implement automatic task execution.
- Create Git branches or commits.

## PROP-016 - Project Registries MVP

### Goals

- Define registry files for proposals, decisions, changes, choices and relations.
- Keep registries as derived/index artifacts generated from source .p2p artifacts.
- Prepare CLI commands to refresh and inspect registries.
- Support future proposal intake, overlap analysis and exporter workflows.

### Non-Goals

- Replace proposal, decision or change source artifacts.
- Implement a database or web backend.

## PROP-017 - Proposal Intake and Context Analysis MVP

### Goals

- Analyze new ideas against proposal, change and relation registries.
- Suggest whether to create a new proposal, add a contribution, open a choice, or record a conflict.
- Provide prompt-only intake analysis before direct AI adapters or MCP.

### Non-Goals

- Automatically decide whether a proposal is accepted.
- Replace owner governance.
- Implement semantic embeddings or a database in the MVP.

## PROP-018 - Choice Management CLI MVP

### Goals

- Implement p2p choice create.
- Implement p2p choice list.
- Implement p2p choice decide.

### Non-Goals

- Implement full voting or permission enforcement.
- Automatically apply intake suggested-actions.

## PROP-019 - Proposal Decision Shortcut Commands

### Goals

- Add p2p proposal accept.
- Add p2p proposal reject.
- Add p2p proposal defer.

### Non-Goals

- Replace the lower-level p2p decision record command.

## PROP-020 - Proposal Inspection CLI MVP

### Goals

- Add p2p proposal list with optional status filtering.
- Add p2p proposal show PROP-ID for compact proposal inspection.
- Improve p2p registry show choices output readability.

### Non-Goals

- Add semantic search or advanced proposal queries.

## PROP-021 - Agent Skill Real Commands Update

### Goals

- Update the local Codex skill to use current P2P CLI commands.
- Document the recommended agent workflow before creating or changing proposals.
- Make governance and decision boundaries explicit for agents.

### Non-Goals

- Create MCP tools or direct AI adapters.

## PROP-022 - Operational Brief Prompt Workflow

### Goals

- Generate a project brief prompt from registries and project state.
- Import AI or human operational brief output into .p2p/project artifacts.
- Keep the skill as method guidance while the CLI remains the source of repeatable context and stored output.

### Non-Goals

- Direct AI invocation from the CLI.
- Automatic owner decisions or automatic application of recommendations.

## PROP-023 - Next Action Recommender MVP

### Goals

- Add top-level p2p next.
- Read imported next-actions.yml as advisory source.
- Compute conservative fallback actions from stale registries, incomplete Change Sets, pending intake, and open or draft choices.
- Add a concise operational section to p2p project status.

### Non-Goals

- Do not modify project state from p2p next.
- Do not make owner decisions automatically.

## PROP-024 - Choice Blocking and Discovery MVP

### Goals

- Phase 1: add advisory choice show/status/discover commands.
- Phase 2: add explicit choice block/unblock commands backed by links.yml.
- Expose project choices and proposal-local vote choices consistently.
- Allow p2p next to prioritize unresolved formal choice blockers.

### Non-Goals

- Do not automatically decide choices.
- Do not automatically convert proposal-local votes into project choices.
- Do not invoke AI directly.

## PROP-025 - Controlled Intake Apply Workflow

### Goals

- Add p2p intake apply plan INTAKE-XXX to create apply-plan.yml.
- Add p2p intake apply show INTAKE-XXX to inspect the plan.
- Add p2p intake apply run INTAKE-XXX --action APPLY-XXX for explicit application.
- Record applied actions in applied-actions.yml.
- Support add_contribution and open_choice with explicit options in the MVP.

### Non-Goals

- Do not automatically apply all intake recommendations by default.
- Do not apply governance decisions such as accept, reject, or defer.
- Do not invoke AI directly.

## PROP-026 - P2P Software Spec Generator MVP

### Goals

- Generate deterministic P2P-native software specs from Change Sets.
- Store specs under .p2p/outputs/software-spec/CHANGE-XXX/.
- Provide optional prompt/import workflow for AI-refined specs.
- Validate imported spec artifact shape before replacing generated artifacts.
- Preserve provenance from spec to Change Set, proposals, decisions and source files.

### Non-Goals

- Do not implement OpenSpec or Spec Kit export in this MVP.
- Do not invoke AI directly.
- Do not invent missing requirements beyond source artifacts.

## PROP-027 - Software Spec Exporter MVP

### Goals

- Provide a conservative exporter MVP that writes generic and OpenSpec-oriented export bundles from an existing P2P software spec.

### Non-Goals

- Not provided.

## PROP-028 - Spec Kit Export Mapping MVP

### Goals

- Define and implement a conservative Spec Kit export mapping from P2P-native software specs without invoking Spec Kit or creating branches.

### Non-Goals

- Not provided.

## PROP-029 - Spec Export Validation MVP

### Goals

- Provide a read-only CLI validator for generated software spec export bundles.

### Non-Goals

- Not provided.

## PROP-030 - Managed Work and Multi-Branch Visibility Policy

### Goals

- Define a level-based managed Git policy and implement the first safe step: read-only handoff planning through P2P Work manifests.

### Non-Goals

- Not provided.

## PROP-031 - Multi-Branch Work Scan MVP

### Goals

- Let P2P scan local P2P-managed Git branches for Work manifests without checkout or mutation.

### Non-Goals

- Not provided.

## PROP-032 - Managed Work Branch Creation MVP

### Goals

- Allow an owner or agent to explicitly create a P2P-managed branch for a planned Work item without committing, submitting, or merging.

### Non-Goals

- Not provided.

## PROP-033 - Managed Work Submit MVP

### Goals

- Allow a branched Work item to be submitted as a local managed commit without pushing or merging.

### Non-Goals

- Not provided.

## PROP-034 - Managed Work Review MVP

### Goals

- Allow a submitted Work item to enter a local review_requested state with a clear review commit and no remote side effects.

### Non-Goals

- Not provided.

## PROP-035 - Managed Work Publish MVP

### Goals

- Allow a review_requested Work item to push its managed branch to origin without opening a PR or merging.

### Non-Goals

- Not provided.

## PROP-036 - Managed Work Accept MVP

### Goals

- Allow an owner to accept a published Work item by merging its managed branch locally into the base branch.

### Non-Goals

- Not provided.

## PROP-037 - Managed Work Status Summary MVP

### Goals

- Provide a readable p2p work status summary that reports Work state, branch, target, remote/acceptance metadata, and the next suggested command.

### Non-Goals

- Not provided.

## PROP-038 - Managed Work Merge Conflict Guidance MVP

### Goals

- Make merge conflicts during p2p work accept explicit, inspectable, and recoverable.

### Non-Goals

- Not provided.

## PROP-039 - Managed Work Finalize MVP

### Goals

- Allow an owner to finalize an accepted Work item by pushing the base branch to the configured remote.

### Non-Goals

- Not provided.

## PROP-040 - Managed Work Cleanup MVP

### Goals

- Allow an owner to clean up finalized Work branches without changing accepted project content.

### Non-Goals

- Not provided.

## PROP-041 - Remote Project Profile and Review Request Policy

### Goals

- Record whether a P2P project is local-only or remote-backed.
- Keep p2p work publish separate from external review/PR creation.
- Introduce an advisory request-review step that can later be implemented by provider adapters.

### Non-Goals

- Create GitHub Pull Requests automatically in this MVP.
- Require PRs for P2P accept/finalize/cleanup.

## PROP-042 - P2P Core CLI MCP Mediator Web Boundary

### Goals

- Define P2P Core as the deterministic library for models, rules, validation, .p2p memory, proposal, choice, change, work, and registry operations.
- Define P2P CLI as the terminal interface for users, agents, scripts, and local automations.
- Define Skill, MCP, and Agent Interfaces as optional ways for agents to use P2P without owning project decisions.
- Define P2P Mediator as an optional intelligent assistant layer that helps contributors but uses Core/CLI/MCP as source of truth.
- Define P2P Web as a later product UI over the same source-of-truth operations.

### Non-Goals

- Implement the MCP server in this proposal.
- Implement the mediator or web application in this proposal.
- Allow AI or mediator layers to decide governance outcomes by default.

## PROP-043 - Managed Work Retire MVP

### Goals

- Add an explicit p2p work retire command for obsolete planned Work manifests.
- Record retired status, reason, and date in the Work manifest.
- Keep retirement metadata-only and avoid Git branch, commit, push, merge, or cleanup side effects.

### Non-Goals

- Retire branched, submitted, published, accepted, finalized, or cleaned Work items in this MVP.
- Delete Work manifests or generated exports.

## PROP-044 - P2P MCP Server MVP

### Goals

- Add a local stdio MCP server inside this repository.
- Expose a minimal read-only tool surface over P2PWorkspace.
- Keep governance and Work mutation commands out of the MCP MVP.
- Avoid web server, cloud deployment, auth, container, direct AI invocation, and mediator logic.

### Non-Goals

- Implement MCP over HTTP.
- Expose proposal accept, choice decide, work accept, Git branch, commit, merge, cleanup, or provider actions.
- Implement P2P Mediator or Web.

## PROP-045 - Agent-Safe Project Bootstrap MVP

### Goals

- Generate agent-safe project instructions during init and provide a repeatable command to add or refresh instructions for additional agent profiles later.

### Non-Goals

- Not provided.

## PROP-046 - MCP Write-Safe Bootstrap Tools MVP

### Goals

- Allow MCP clients to initialize P2P projects, refresh agent instructions, and refresh registries through explicit controlled tools.

### Non-Goals

- Not provided.

## PROP-047 - Guided Init Wizard MVP

### Goals

- Make p2p init usable without memorizing flags, while preserving non-interactive CLI usage.

### Non-Goals

- Not provided.

## PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

### Goals

- Allow MCP clients to create draft proposals and intake prompts through explicit write-safe tools.

### Non-Goals

- Not provided.

## PROP-049 - MCP Level 4A Proposal Refinement Tools

### Goals

- Allow MCP clients to update draft proposal content and generate/show project brief artifacts while keeping governance owner-controlled.

### Non-Goals

- Not provided.

## PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

### Goals

- Expose choice, conflict, and impact advisory workflows through MCP without adding decision-making mutations.

### Non-Goals

- Not provided.

## PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

### Goals

- Make draft proposals visible as actionable next steps and require agents to read existing artifacts before explaining them.

### Non-Goals

- Not provided.

## PROP-052 - MCP Proposal Contribution Tool

### Goals

- Allow MCP clients to add typed contributions to existing proposals without making governance decisions.

### Non-Goals

- Not provided.

## PROP-053 - Core Validation Layer MVP

### Goals

- Add a read-only core validation layer and CLI/MCP entry points that report project-state issues without mutating files.

### Non-Goals

- Not provided.

## PROP-054 - Project Readiness and Maturity Assessment

### Goals

- Define a readiness and maturity assessment model that separates deterministic completion from domain-specific quality assessment.
- Provide scores and gaps that are explainable, versioned and grounded in explicit criteria.
- Keep P2P Core deterministic while allowing optional AI-assisted maturity review through prompt/import workflows.

### Non-Goals

- Do not let P2P automatically decide that a project is ready or block work solely from a maturity score.
- Do not produce a single opaque score without criteria, confidence and known gaps.

## PROP-055 - Agent Token Budget and Context Discipline

### Goals

- Define a token-aware operating policy for agents.
- Prefer compact deterministic context views before detailed file reads.
- Make CLI and MCP expose bounded context packets for common agent tasks.
- Prevent agents from scanning unrelated .p2p, source, test, or Git history context when a smaller command output is enough.

### Non-Goals

- Do not remove detailed proposal/change/registry commands.
- Do not introduce autonomous AI decision-making inside the core.
- Do not optimize runtime performance or rewrite the CLI in Rust as part of this proposal.

## PROP-056 - Project Definition Maturity Rubrics

### Goals

- Separate structural readiness from project definition maturity.
- Introduce extensible domain rubrics stored as project state.
- Evaluate whether important project topics have been covered by proposals and decisions.
- Allow future domains to add their own criteria without changing the assessment model.
- Prepare init/wizard flow to select a project domain and generate an editable rubric checklist.

### Non-Goals

- Do not evaluate implemented code quality in this proposal.
- Do not require AI semantic scoring for the MVP.
- Do not make maturity assessment decide project governance outcomes.

## PROP-057 - Guided Rubric Selection During Init

### Goals

- Let the owner confirm rubric criteria during interactive initialization.
- Keep all domain criteria enabled by default.
- Allow disabling suggested criteria with simple yes/no prompts.
- Store the selected criteria deterministically in .p2p/project/rubrics.yml.

### Non-Goals

- Do not support custom criteria in the wizard yet.
- Do not support editing criterion keywords or descriptions yet.
- Do not change non-interactive p2p init defaults.

## PROP-058 - Project README and Installation Guide

### Goals

- Update README.md as the product entry point.
- Add a practical installation guide.
- Document current architecture, quick start, init wizard, context discipline, rubrics, assessment, and MCP local setup.
- Be explicit about current limits and future packaging direction.

### Non-Goals

- Do not implement packaging changes in this proposal.
- Do not add a full website or generated docs site.
- Do not document unstable internals exhaustively.

## PROP-059 - P2PWorkspace Modular Refactoring Plan

### Goals

- Approve a modular architecture direction for P2P Engine without changing runtime behavior.
- Preserve the public CLI, MCP, storage, consent, governance, and P2PWorkspace compatibility surface while extracting cohesive internal modules in later work.
- Define a layered architecture that separates domain rules, application workflows, persistence adapters, Git effects, MCP transport/schema handling, and CLI presentation.
- Create development guidance for humans and agents before non-trivial refactoring starts.
- Select consent/permissions as the preferred first future code extraction after the architecture contract is accepted and bound into local specs.

### Non-Goals

- Do not rewrite the whole engine in one pass.
- Do not implement source refactoring as part of this proposal decision.
- Do not break existing CLI commands, MCP tool names, .p2p storage layouts, validation behavior, registry refresh behavior, consent semantics, or owner-controlled governance actions.
- Do not split cli.py mechanically before service/use-case boundaries are defined.
- Do not translate this proposal into source-level implementation tasks inside specs/ until the proposal is accepted and intentionally bound.

## PROP-060 - Real Test Coverage Reporting

### Goals

- Add optional, non-blocking code coverage observability for P2P Engine runtime code.
- Use terminal coverage output to identify internal modules or branches that need better focused tests.
- Keep coverage separate from deterministic test routing, project evidence coverage, and release gating.

### Non-Goals

- Do not implement test impact routing in this proposal; that belongs to PROP-098.
- Do not measure project-design completeness or evidence coverage for P2P Engine user projects.
- Do not introduce HTML coverage reports, generated coverage artifacts, or an initial CI fail-under gate.
- Do not run coverage after every small code change as the default agent behavior.

## PROP-061 - Focused README and Documentation Map

### Goals

- Rewrite README.md as a concise repository entry point for P2P Engine.
- Keep mediator and web out of the main README scope except as out-of-repo future directions.
- Add documentation stubs for CLI guide, MCP reference, agent integration, and core API reference.
- Make README link to each detailed documentation file with a short explanation.

### Non-Goals

- Do not fully document every CLI command in this change.
- Do not add Python docstrings in this change.
- Do not implement packaging changes.

## PROP-062 - README Product Landing Page Refinement

### Goals

- Make README.md a concise product-style landing page for the engine.
- Explain why P2P Engine exists and who it serves.
- Add a 5-minute demo with commands and expected output.
- Keep install instructions short and link to docs/INSTALL.md.
- Clearly mark stable and work-in-progress docs.

### Non-Goals

- Do not expand detailed CLI/API/MCP documentation in this change.
- Do not describe mediator or web as part of this repository.

## PROP-064 - Spec Kit Three-Prompt Export Model

### Goals

- Define project.md as the canonical synthesized project definition derived from accepted P2P memory.
- Define a core project coverage checklist that every project.md must cover.
- Allow domain-specific section extensions for software, grant documents, board games, environmental impact assessment, one-day projects, and future verticals.
- Derive generic, OpenSpec, and Spec Kit outputs from project.md instead of mirroring downstream folder layouts.
- Preserve P2P source traceability so agents and humans can see which accepted artifacts support each major section.

### Non-Goals

- Invoke downstream tools directly.
- Treat draft proposals as accepted truth.
- Generate downstream folder structures as the primary export UX.
- Replace P2P governance decisions with export-time synthesis.

## PROP-065 - MCP Agent-First Coverage Expansion

### Goals

- Expose read-only MCP tools for Change Sets, Work, registries, project state, remote profile, and spec/export inspection.
- Expose write-safe deterministic MCP tools for Change Set creation, project refresh, spec refresh/export/validation, and Work planning.
- Expose prompt/advisory MCP tools for explore, digest, clarify, synthesize, plan, tasks, swot, and spec refinement prompts.

### Non-Goals

- Expose owner-governance decisions such as proposal accept/reject/defer, choice decide/block/unblock, conflict record, vote record, or work branch/merge/finalize operations.
- Expose import/apply workflows that ingest external AI output without a separate trust and preview model.

## PROP-066 - Permission-Gated MCP Governance And Git Operations

### Goals

- Preserve the future requirement so missing MCP operations are not forgotten.
- Define a concrete permission model for privileged MCP operations.
- Use project-declared roles as the MVP authorization model while acknowledging they are not strong authentication.
- Require consent receipts for owner-controlled MCP operations.
- Keep Git provider enforcement as the cloud-backed security boundary for protected branches and main updates.
- Support generic fallback identities when project init does not know real person names.
- Keep future API server/IAM integration possible without blocking the MVP.

### Non-Goals

- Implement privileged MCP methods before this proposal is accepted.
- Treat local actor_id values as strong authentication.
- Require an external IAM server for the MVP.
- Allow agents to bypass owner governance decisions.
- Expose Git commit, push, merge, provider PR/MR creation, or finalization without accepted permission and consent rules.

## PROP-067 - Agent-First Setup Documentation Split

### Goals

- Make public setup documentation primarily about using P2P for a new target project.
- Keep P2P Engine repository contribution setup exclusively in CONTRIBUTING.md, with README linking there but not showing potentially confusing examples.
- Make manual CLI usage clearly secondary: useful for inspection, debugging, recovery, and learning the model.

### Non-Goals

- Change runtime behavior or installation code.
- Document unverified agent-specific desktop integrations as definitive commands.

## PROP-068 - Document Agent MCP Client Setup Commands

### Goals

- Add concrete MCP client setup examples for verified terminal clients.
- Show Claude Desktop/local MCP JSON using the same target-project server command.
- Keep unverified desktop or IDE-specific integrations framed as generic MCP client configuration rather than definitive commands.

### Non-Goals

- Document P2P Engine repository contributor MCP setup outside CONTRIBUTING.md.
- Claim support for unverified Codex desktop, Codex VSCode, or other IDE-specific MCP flows.

## PROP-069 - Clarify MCP Stdio Integration Model

### Goals

- Document the MCP stdio integration model clearly.
- Clarify that each client may start its own P2P MCP process and that shared state is repository-backed.
- Refine verified setup examples for Claude Code, Claude Desktop, Codex CLI/config, Codex IDE extension, and VS Code Copilot MCP.

### Non-Goals

- Implement Streamable HTTP MCP support now.
- Change MCP server runtime behavior.

## PROP-070 - Clarify README Agent Access Modes

### Goals

- Make the README quick start explicit about CLI access versus MCP access.
- State that current MCP access is intentionally limited and does not expose privileged operations.
- Point readers to INSTALL and MCP docs for detailed client setup and tool boundaries.

### Non-Goals

- Change MCP behavior or add privileged MCP tools now.

## PROP-071 - Custom Domain Definition Workflow

### Goals

- Represent domain and rubric state explicitly for all projects.
- Treat predefined domains as optional initialization templates.
- Make custom/none initialization a first-class unresolved setup path rather than a special-case error path.
- Base maturity assessability on rubric availability and status, not hardcoded domain identity.

### Non-Goals

- Implement a mediator or AI semantic review inside core.
- Hardcode every possible vertical in P2P Engine.

## PROP-072 - Concurrent Managed Work and Merge Decision Model

### Goals

- Keep Git invisible for non-technical users and routine agent workflows.
- Define main as accepted project state rather than shared draft space.
- Support concurrent proposal branches from multiple people or agents.
- Support multiple candidate Work items for the same Change Set.
- Add explicit candidate selection before merge when competing Work items exist.
- Make local and cloud projects follow the same P2P lifecycle, with cloud adding remote publication and optional external review handoff only.
- Require explicit P2P decisions before merging proposal or Work branches into main.
- Record auditable metadata for proposal branch decisions, Work candidate decisions, merge conflicts, and finalization.
- Generate clear agent instructions for branch, publish, review, accept, merge, conflict, finalize, and cleanup behavior.

### Non-Goals

- Replace Git as the underlying storage or transport mechanism.
- Bind the core model to GitHub-specific PR semantics.
- Allow agents to perform owner-sensitive merge, cleanup, or publishing operations without permission.
- Implement real-time collaboration, distributed locking, or server-side coordination outside Git.
- Decide the full MCP permission model covered by PROP-066.
- Require normal users to understand or run raw Git commands.
- Guarantee automatic semantic conflict resolution between competing proposals.

## PROP-073 - Ergonomic Remote Project Initialization

### Goals

- Let users declare remote project intent during init with provider, remote name, and remote URL options.
- Guide users when the Git remote is missing, mismatched, or not reachable, without requiring raw Git knowledge.
- Keep local and cloud project semantics unified: cloud mode only adds remote profile validation and managed sync guidance.
- Preserve provider-neutral behavior and avoid creating external repositories in the MVP.
- Generate agent instructions and next-step hints that match the selected repository mode.

### Non-Goals

- Automatically create GitHub/GitLab repositories or provider PR/MR resources.
- Replace Git provider authentication, SSH setup, branch protection, or IAM.
- Make local actor identities into strong authentication.

## PROP-074 - Agent Runtime Bootstrap Robustness

### Goals

- Make P2P-managed repositories self-diagnosing for agents when the p2p runtime is missing.
- Provide clear fallback guidance for PATH, virtualenv, module execution, MCP tools, or installation.
- Prevent agents from bypassing governance while still making the next recovery step obvious.
- Support cloud agent environments where the repository is mounted but the Python package is not installed.

### Non-Goals

- Allow agents to create or edit .p2p files manually when the CLI is missing.
- Bundle a hosted P2P service or require a global package manager.
- Grant cloud agents repository write permissions or provider credentials automatically.

## PROP-075 - MCP End-To-End Proposal Collaboration Workflow

### Goals

- Make the normal proposal collaboration path coherent and closable through P2P primitives without raw Git.
- Clarify draft persistence and commit behavior after MCP proposal creation or update.
- Prevent accidental branch chaining by requiring or defaulting a safe base branch.
- Define a safe consent-request path for MCP that preserves owner approval.
- Allow MCP clients to correct remote profile metadata when policy allows it.

### Non-Goals

- Let MCP grant owner consent without an owner-controlled approval path.
- Open provider PRs/MRs automatically.
- Bypass clean-worktree requirements by silently committing arbitrary unrelated files.

## PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

### Goals

- Keep P2P Engine focused on local deterministic automation: CLI, filesystem .p2p state, Git audit, and local MCP.
- Define P2P Cloud as a separate product layer that owns web/API, auth, UI, database, workflow orchestration, and multi-tenant state.
- Define a containerized P2P runner model for cloud workflows that invokes the p2p CLI in isolated Git checkouts.
- Make cloud execution auditable through .p2p artifacts and Git history without turning the engine into a hosted API service.
- Clarify which future proposals should be rejected, accepted, or reformulated based on this boundary.

### Non-Goals

- Implement P2P Cloud inside this repository as part of P2P Engine core.
- Add a public FastAPI/Django/NestJS API server to P2P Engine.
- Make P2P Engine responsible for users, organizations, billing, sessions, OAuth, cloud IAM, or multi-tenant authorization.
- Keep one long-running P2P server container per project as the default execution model.
- Create provider PR/MR automation in the engine core.

## PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

### Goals

- Provide explicit MCP tools for owner-approved draft proposal accept, reject, and defer decisions while preserving the governance boundary through granted consent receipts.

### Non-Goals

- Not provided.

## PROP-078 - Project-Local Wheel Installation and Upgrade Model

### Goals

- Make P2P Engine installable and upgradeable inside each project's own virtual environment, starting with GitHub Release wheel artifacts and explicitly preserving a future migration path to a public package registry.

### Non-Goals

- Not provided.

## PROP-079 - Managed Next Action Lifecycle

### Goals

- Provide a managed hybrid next-action model that combines curated owner/agent actions with generated actions derived from project state, and expose lifecycle CLI commands so stale next actions can be closed without manual .p2p edits.

### Non-Goals

- Not provided.

## PROP-080 - Automated GitHub Release Wheel Publishing

### Goals

- Automate wheel and sdist publishing for GitHub Releases so maintainers can publish installable project-local packages by pushing a version tag.

### Non-Goals

- Not provided.

## PROP-081 - MCP and Skill Support for Managed Next Actions

### Goals

- Expose the managed next-action lifecycle consistently through CLI guidance, agent skill instructions, and MCP write-safe tools.

### Non-Goals

- Not provided.

## PROP-082 - Readiness Assessment Refresh And Review Workflow

### Goals

- Separate information completeness from agent behavioral guidance in the readiness model.
- Provide a governed assess/review path that can update evidence, criterion scores, confidence, missing items, gates, suggested next actions, unresolved owner questions, and overlap candidates after proposal artifacts change.
- Introduce a first-class deterministic clarification interview memory for low-readiness proposals: generated questions start with empty answers, answers are recorded as the interview progresses, and every question remains tied to the readiness gap it is meant to resolve.
- Make agent guidance operational and proactive by default: agents must challenge thin or incomplete artifacts, ask focused owner questions one at a time, reassess the question list after each answer, propose alternatives and tradeoffs, detect mergeable proposals, and avoid recommending acceptance when readiness is methodologically weak.
- Define production-ready CLI commands and data structures for question lifecycle, answer recording, deferral, muting, grouping, applying answers, and handling merge candidates.
- Allow the agent to use completed question-and-answer memory to refine the proposal through supported CLI tools.
- Preserve owner control: agent proactivity may recommend, question, assess, and prepare aggregation, but must not decide acceptance, rejection, deferral, aggregation closure, or override.
- Preserve backward compatibility for proposals that have no question/interview state yet.

### Non-Goals

- Do not make agents autonomous governance decision makers.
- Do not overwrite computed readiness scores with owner override outcomes.
- Do not require every small proposal to receive heavyweight qualitative review or a full interview.
- Do not replace deterministic refresh. Refresh remains a conservative synchronization step, while assess/review is the evidence-aware path.
- Do not store interview state only in free-form chat memory or only as unstructured contributions.
- Do not break existing proposals, registries, readiness snapshots, or CLI inspection commands when question state is absent.

## PROP-083 - Domain-Aware Visible Project Definition Export

### Goals

- Generate a default human-readable project definition for every P2P project.
- Write the default visible output to outputs/latest/project.md as a single chaptered Markdown document.
- Preserve prior generated project definitions by moving or writing snapshots under outputs/review-001, outputs/review-002, and later review directories.
- Support different vertical domains through a generic project definition model instead of assuming software.
- Allow domain-specific or tool-specific exports, such as software-spec, OpenSpec, or Spec Kit, as nested profiles under outputs/latest/exports/<profile-or-vertical>/ when compatible.
- Preserve compatibility with existing .p2p/outputs and CLI/API behavior until migration or deprecation is explicitly verified.

### Non-Goals

- Do not make software-spec, OpenSpec, or Spec Kit the default export for non-software domains.
- Do not delete existing .p2p outputs without implementation-time compatibility review.
- Do not make the root outputs/ location configurable in the MVP.
- Do not split the default human-facing project definition into many default files.

## PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

### Goals

- Define .p2p/project/runtime.yml as the authoritative project-local declaration of P2P Engine runtime compatibility.
- Record a compatible runtime range and one recommended P2P Engine runtime version, without release source descriptors, wheel filenames, or digests.
- Generate project-local setup guidance, such as P2P-SETUP.md, so a collaborator who cloned or copied a project can find the required runtime information without knowing P2P internals.
- Provide read-only runtime status diagnostics and validation findings that tell humans and agents whether the installed runtime matches the project contract.
- Block governed writes only when a project declares or requires a runtime contract and the contract is incompatible, invalid, unsupported, or missing under that declared policy.
- Keep ownership boundaries clear: PROP-084 owns runtime contract, setup guidance, diagnostics, validation, and write-gate policy; PROP-078 owns installation mechanics; PROP-080 owns release artifact publication and integrity metadata.

### Non-Goals

- Do not make a mandatory bootstrap script central to the proposal.
- Do not add an install, reconcile, upgrade, downgrade, replacement, source-switch, virtualenv, package-resolution, or download manager in this scope.
- Do not put release tags, wheel filenames, SHA-256 digests, source descriptors, arbitrary URLs, arbitrary repositories, PyPI resolution, mirrors, source checkout installs, editable installs, or offline wheel behavior in the required runtime contract.
- Do not block legacy projects solely because they lack runtime.yml; report legacy_undeclared with guidance instead.
- Do not add broad command blocking across all commands; enforcement is limited to governed writes when a declared or required contract cannot be trusted.
- Do not make Git required for P2P Core or introduce separate runtime-contract formats for standalone, local Git, and remote Git contexts.

## PROP-085 - Pluggable Project Verticals And Readiness Orchestration

### Goals

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

### Non-Goals

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

## PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

### Goals

- Make proposal artifact expectations explicit and visible to agents.
- Prevent important proposal artifacts from staying empty by default when they are applicable.
- Keep lightweight proposals lightweight by allowing non-applicable artifacts to be skipped with an explicit reason.
- Guide agents to ask one focused owner question at a time when artifact gaps block maturity.
- Preserve owner control: agents may ask, draft, identify gaps, and recommend next steps, but do not decide acceptance.

### Non-Goals

- Do not require every proposal artifact to be fully populated for every proposal.
- Do not replace the existing readiness engine or create a parallel proposal lifecycle.
- Do not retroactively rewrite accepted proposals.
- Do not make agents perform broad unmanaged scans of .p2p or source code to satisfy artifact checks.

## PROP-087 - Agent Personality Model For Decision Mediation

### Goals

- Define a durable project-level interaction-style model for agent mediation with the decision owner.
- Persist three explicit independent scales: technical_verbosity, formality, and assertiveness.
- Provide stable defaults: technical_verbosity=2, formality=2, assertiveness=0.
- Expose read/update behavior through public project interaction-style CLI commands and matching MCP tools.
- Update generated agent instructions and project/local skills so agents know how to inspect and update style through CLI/MCP only.

### Non-Goals

- Do not let personality change governance authority, readiness scores, validation, permissions, facts, or audit evidence.
- Do not introduce open-ended persona prose or persisted named presets as the primary configuration model.
- Do not implement per-agent or runtime/session style overrides in the first slice.
- Do not require migration or manual completion for existing projects.

## PROP-088 - MCP Artifact Import Parity

### Goals

- Provide MCP parity for controlled proposal artifact content imports.
- Start with existing CLI-backed impact and exploration imports, because those services and validation rules already exist.
- Keep artifact state, readiness, context, and validation consistent after imports.
- Make unsupported artifact-content mutations fail with explicit missing-primitive guidance.
- Preserve owner governance boundaries and the rule that agents never write directly under .p2p/.

### Non-Goals

- Do not add proposal acceptance, rejection, deferral, or owner decision behavior.
- Do not solve Work lifecycle MCP parity; Work publish, review, accept, finalize, and cleanup remain a separate product decision.
- Do not add provider PR/MR automation.
- Do not introduce a broad arbitrary file-write MCP tool for .p2p artifacts.

## PROP-089 - Readiness Question-State Convergence

### Goals

- Make questions.yml authoritative for owner-question readiness whenever structured question state exists.
- Keep open-questions.md as human-readable evidence and legacy fallback, not as a competing source of blocking state.
- Preserve the one-question-at-a-time owner interaction flow.
- Keep owner override explicit and auditable when the owner decides despite unresolved questions or partial readiness.

### Non-Goals

- Do not change whole-project readiness semantics.
- Do not remove open-questions.md or require migration of all legacy proposals in this change.
- Do not force the owner to answer every question before making a governance decision.
- Do not turn agent questioning into a batch questionnaire.

## PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

### Goals

- Define a production-grade multi-file project vertical pack contract while preserving compatibility with existing single-file vertical.yml packs.
- Persist the exact resolved vertical package in .p2p/project/vertical.lock.yml with version, source, schema, checksum, and compatibility metadata.
- Introduce .p2p/project/definition.yml as the durable project definition state used by agents to record section data, assumptions, missing fields, open questions, decisions, and next suggested work.
- Keep p2p project vertical ... as the stable CLI namespace and extend it with JSON-ready project context operations instead of replacing it with a new top-level namespace in the first slice.
- Integrate selected vertical defaults with .p2p/project/rubrics.yml while preserving PROP-057 enabled/disabled rubric selection semantics.
- Define deterministic resolver behavior across explicit path/reference, project-local packs, installed local packs, packaged seed packs, future Wavekit packs, and base_project fallback.
- Define strict post-init lockfile behavior: after a vertical is locked, missing or mismatched packs must not silently fall back to another vertical without explicit repair, migration, or fallback command.
- Expose enough structured JSON context for a generic agent to guide project definition without hardcoded domain knowledge.
- Define the generic vertical-aware agent guidance runtime: progressive interview, one primary question per turn, examples, assisted answers, explicit assumptions, section completion checks, and structured state updates.
- Keep vertical pack content as declarative domain data, never executable code and never higher-priority agent instruction.
- Prepare local pack formats and lock metadata for future Wavekit remote installation without requiring remote registry support in the first implementation.
- Define validation, upgrade, migration, orphaned rubric, and orphaned project-definition-field behavior before broad catalog expansion.

### Non-Goals

- Do not replace PROP-085. This proposal hardens and completes the accepted direction.
- Do not replace p2p project vertical ... with a new required p2p vertical ... namespace in the first production slice.
- Do not move existing project-local packs out of .p2p/project/verticals/ as part of this proposal.
- Do not rename base_project as a breaking change. Any generic_project naming can be handled as aliasing or a future compatibility decision.
- Do not implement Wavekit remote search, install, update, or publish in the first implementation.
- Do not execute code from vertical packs or support executable plugin hooks.
- Do not allow vertical pack content to override system, developer, safety, governance, repository, or tool-permission instructions.
- Do not make p2p init ask all vertical interview questions. Init configures the project; agent guidance develops the project later.
- Do not replace .p2p/project/rubrics.yml or change the meaning of enabled: false from PROP-057.
- Do not silently upgrade vertical packs or project definition state during assessment, export, readiness review, or ordinary agent interaction.
- Do not require a domain-specific agent skill for every vertical.

## PROP-091 - Governance Policy Convergence

### Goals

- Keep `owner_decides` as the current operational default.
- Preserve owner authority as the final decision source for now.
- Make votes, blockers, and precedents transparent decision context rather than
  automatic decision makers.
- Introduce a deterministic governance preflight contract for proposed
  selections and decision attempts.
- Use `permissions.yml` as the primary actor and role source when available.
- Keep `governance/roles.yml` as a legacy, display, or fallback artifact during
  migration.
- Make vote disagreement, ties, related precedents, reopened decisions, weak
  consensus, and non-blocking concerns visible as warnings.
- Treat structural invalidity, unauthorized actors, unknown targets, unsupported
  governance modes, and corrupt governance artifacts as blocking errors.
- Treat explicit unresolved blockers as normal-flow blockers that can be
  overridden only by an authorized owner with recorded rationale.
- Expose first-phase MCP parity through read-only or low-risk governance status,
  validation, vote status, precedent lookup, and preflight tools.

### Non-Goals

- Do not implement a full democratic governance system.
- Do not introduce quorum, weighted voting, delegation, complex voting
  deadlines, or automatic vote enforcement.
- Do not make votes automatically accept, reject, or decide proposals or
  choices.
- Do not allow agents or MCP tools to bypass owner-controlled governance.
- Do not use fuzzy matching, semantic similarity, embeddings, title inference,
  keyword guessing, or AI search in the core precedent lookup.
- Do not expose MCP tools that mutate governance state or finalize decisions in
  phase 1.
- Do not remove compatibility for existing governance artifacts without a
  migration path.

## PROP-092 - Local MCP Work Lifecycle Parity And Remote Gateway Boundary

### Goals

- Expose the full managed Work lifecycle through the local P2P MCP adapter with functional parity to the CLI where the corresponding CLI transition already exists.
- Keep every mutating Work MCP operation domain-specific, permission-gated, state-gated, consent-gated, and auditable.
- Reuse the existing Work lifecycle services and P2P command layer instead of duplicating Work logic in CLI, MCP, or future Wavekit adapters.
- Define a stable architectural boundary: P2P core is MCP-ready and local-MCP capable; remote multi-user MCP belongs to a separate Wavekit gateway/control-plane layer.
- Prevent raw Git bypasses by exposing Work operations as P2P tools rather than generic Git tools.

### Non-Goals

- Do not implement a remote HTTP MCP server, OAuth flow, client registration, multi-tenancy, billing, global rate limiting, or hosted project access in P2P Engine core.
- Do not create provider PR/MR automation; provider-specific PR/MR creation remains a separate adapter decision.
- Do not grant agents autonomous authority over owner-controlled actions; owner-controlled transitions still require explicit consent and valid policy checks.
- Do not expose generic Git tools such as arbitrary push, merge, reset, clean, or delete-branch operations.

## PROP-093 - Agent Persistence Boundaries And Proposal Authoring Flow

### Goals

- Make every meaningful persistent agent write classified, owner-visible, and tied to a P2P primitive or policy.
- Make canonical P2P state, structured proposal inputs, generated narrative artifacts, generated exports, stable documentation, scratch files, and external side effects distinct.
- Expose a deterministic proposal artifact schema independent of physical file materialization.
- Provide a compact agent-operational playbook that maps common owner requests to the correct P2P route.
- Prevent agents from treating scaffolded narrative markdown under `.p2p/` as a manual editing surface.
- Make proposal authoring discoverable: structured inputs first, then synthesis/import, then owner review and decision.
- Align contribution primitives with narrative artifacts, or stop scaffolding narrative placeholders that cannot be populated through supported commands.
- Provide an owner-friendly full proposal view so humans do not need to inspect internal proposal files manually.
- Make `p2p init` deterministic, adaptive, and explicit about which agent integrations were created and why.
- Preserve compatibility when the current agent cannot be reliably detected by falling back to the existing broad adapter setup with a concise warning.
- Make add/remove/update/doctor lifecycle commands for agent integrations visible in init summaries, generated instructions, and docs.
- Make runtime and MCP setup robust when the P2P decision root differs from the current working directory.
- Avoid codifying local repository topology choices, including sibling repositories, as official P2P product direction.

### Non-Goals

- Do not discourage agents from creating P2P proposals, readiness artifacts, question state, choices, contributions, imports, or generated P2P artifacts when useful.
- Do not force project reasoning to stay in chat.
- Do not make P2P Engine less proactive.
- Do not require every proposal directory to contain every possible artifact file.
- Do not create empty placeholder files only to make proposal directories look uniform.
- Do not make a long prose manual the primary agent control surface.
- Do not duplicate the full CLI guide inside generated agent instructions.
- Do not make agent routing so rigid that owner intent and explicit owner instructions are ignored.
- Do not remove support for all built-in agent adapters.
- Do not automatically remove existing adapter files from upgraded projects just because the new init default is adaptive.
- Do not require users to manually edit `.p2p/agent-integrations.yml` or delete generated agent files by hand.
- Do not invalidate projects generated by the current release merely because they lack new PROP-093 metadata, generated instructions, artifact-catalog state, or write-class labels.
- Do not define or recommend a sibling repository model.
- Do not require users to separate specification repositories from implementation repositories.
- Do not solve the software specification lifecycle in this proposal; that belongs to PROP-094 and the software vertical.
- Do not define file names such as `tech-stack.md`, `substrate.md`, or `phase0.md` as core P2P concepts.
- Do not implement MCP HTTP, hosted service deployment, or remove local-first CLI/filesystem-backed operation in this proposal.
- Do not implement remote MCP permissions, WaveKit hosted permissions, cloud collaboration authorization, or provider PR automation.
- Do not change owner authority over governance decisions.
- Do not require a full external artifact registry in the first implementation slice.

## PROP-094 - P2P-Governed Software Specification Lifecycle

### Goals

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

### Non-Goals

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

## PROP-095 - Project Runtime Contract Update Lifecycle

### Goals

- Give the owner an explicit, preview-first operation for changing the project runtime contract.
- Expose separate read-only and mutating command surfaces.
- Update `.p2p/project/runtime.yml` and managed `P2P-SETUP.md` as one coordinated policy change.
- Classify upgrade, downgrade, range widening, range tightening, runtime-line change, recommended-only change, no-op, and active-runtime exclusion.
- Preserve PROP-084 write-gate safety while allowing a narrow runtime-contract update exception for valid incompatible old contracts.
- Allow agents and non-owner collaborators to produce read-only previews for owner review.
- Require owner authority, explicit confirmation, stale-preview protection, and structured reasons where the impact is material.
- Provide deterministic human-readable and JSON output for humans, agents, CI, and scripts.
- Keep runtime installation, upgrade, downgrade, package resolution, remote lookup, and release availability enforcement out of scope.

### Non-Goals

- Do not install, upgrade, downgrade, select, or reconcile a local P2P Engine runtime.
- Do not query GitHub, download release metadata, resolve wheels, or verify installability through the network.
- Do not make release metadata from PROP-080 a blocking dependency for runtime contract updates.
- Do not overwrite, adopt, merge, rename, back up, or replace unmanaged `P2P-SETUP.md` files.
- Do not implement contract repair, schema migration, contract recovery, or legacy adoption workflows.
- Do not add MCP mutation in the first implementation.
- Do not create Git commits, branches, pushes, pull requests, merges, or provider handoffs.
- Do not perform unrelated governed mutations after a new contract makes the active runtime incompatible.

## PROP-096 - Readiness Evidence Quality and Question State Normalization

### Goals

- Make readiness quality scoring evaluate each evidence artifact without letting a placeholder-only supplemental artifact invalidate meaningful primary evidence.
- Normalize proposal question state so answered questions already marked applied_to_proposal true are treated as applied or are repairable through a supported CLI flow.
- Add regression tests that reproduce the PROP-095 failure mode and prove readiness assess does not produce false missing evidence.

### Non-Goals

- Do not redesign the readiness scoring model or readiness profile thresholds.
- Do not change owner governance semantics or make readiness scores authoritative decisions.
- Do not introduce direct editing of .p2p proposal question state as a supported user workflow.

## PROP-097 - Runtime Contract Adoption For Legacy Projects

### Goals

- Provide an explicit owner-controlled adoption lifecycle for
  `legacy_undeclared` projects.
- Create the initial `.p2p/project/runtime.yml`, the
  `runtime_contract.required: true` marker, and a managed `P2P-SETUP.md`.
- Keep adoption separate from runtime installation, upgrade, package download,
  environment reconciliation, and contract update.
- Make the operation previewable, confirmable, testable, and repeatable for
  this repository and other legacy projects.

### Non-Goals

- Do not install, upgrade, downgrade, or select a P2P Engine runtime.
- Do not recover a missing required contract; recovery remains distinct from
  adoption.
- Do not repair invalid or unsupported contracts.
- Do not overwrite an unmanaged human-owned `P2P-SETUP.md` implicitly.
- Do not make `p2p init` a recovery or adoption shortcut.

## PROP-099 - Project Output Lifecycle and Retention Policy

### Goals

- Define a Human Project Publication Pipeline from governed P2P state to complete export, curated Markdown, publication validation, and neutral PDF.
- Keep deterministic export, semantic curation, owner review, publication validation, and PDF rendering as independent and inspectable stages.
- Make the curated document project-first, vertical-aware, traceable, and readable by humans who do not know P2P internals.
- Define an incremental implementation path with a minimal end-to-end slice first and richer CLI orchestration, publication packages, profiles, and themes later.

### Non-Goals

- Do not make generated outputs a new source of truth; .p2p remains governed project memory.
- Do not make the curator decide governance outcomes, readiness, implementation status, or owner choices.
- Do not replace the P2P-native software specification lifecycle, OpenSpec, Spec Kit, or downstream implementation exports.
- Do not require a fully deterministic curator in the first slice; semantic curation may be agentic but must be bounded by contracts and validation.
- Do not introduce multiple themes, branding, visual editors, template marketplaces, sophisticated appendices, automatic permanent replacement of project.md, or full MCP parity in the first slice.

## PROP-100 - Project Decision Context Index and Proposal Neighborhood

### Goals

- Approvare un decision context index derivato, non canonico, rebuildable, read-only e spiegabile.
- Introdurre un Source Catalog versionato che classifichi fonti semantiche, metadata di qualita, execution state, projection derivate e fonti escluse.
- Richiedere uno snapshot immutabile per richiesta che scopra le fonti una volta e legga, hashi e parsifichi ogni fonte al massimo una volta usando gli stessi byte.
- Mantenere `ProjectDecisionContextService` come facade stateless dietro `P2PWorkspace`, senza snapshot stale tra richieste.
- Definire record, node, relation, evidence, diagnostic, retrieval hit, index e manifest tipizzati e serializzabili con schema versionato.
- Separare canonicality, authority, activation, confidence e completeness.
- Coprire l'intero proposal decision lifecycle, inclusi acceptance qualificata, split, merge, supersession, pending e legacy divergence.
- Indicizzare decision precedents e un sottoinsieme esplicitamente catalogato di governance/project-definition constraints senza interpretazione libera di ogni testo.
- Normalizzare progressivamente relazioni da proposal artifacts, Change Set, choices, blockers, conflict memory, vertical coverage e Work lineage.
- Usare node namespace tipizzati, relation vocabulary versionata, evidence merge deterministico e traversal cycle-safe.
- Distinguere edge di topologia da retrieval reasons quali lexical overlap, same surface e heuristic vertical match.
- Fornire retrieval deterministico e spiegabile per proposal ID e idea text, con policy versionata, applicabilita esplicita, score ricostruibile e protezione dai falsi positivi.
- Rendere `small` e `medium` budget semantici misurabili applicati dopo ranking e grouping.
- Bloccare l'integrazione pubblica finche profiling, scan/read count e fixture di scala non dimostrano che il nuovo percorso non replica i timeout correnti.
- Introdurre freshness basata su presenza/hash reali delle fonti e versioni delle policy, separando `generated_at` dall'identita semantica.
- Migrare context packet, intake, prompt, next actions, projection e MCP per slice compatibili, mantenendo owner authority e controlled apply.

### Non-Goals

- Non sostituire proposal, decision, choice, Change Set, Work, YAML o Markdown canonici come source of truth.
- Non creare una memoria canonica parallela aggiornata da sintesi LLM libera.
- Non usare registri, decisions map, pubblicazioni, prompt o altri output derivati come input semantico dell'indice.
- Non implementare PROP-100 come un unico Change Set senza gate intermedi.
- Non scegliere o implementare una cache persistente nella prima realizzazione; una cache giustificata dalle misure richiede una feature separata.
- Non introdurre embeddings o ricerca non spiegabile nel primo retrieval.
- Non ridefinire proposal lifecycle, governance, owner authority, Git flow o controlled apply.
- Non interpretare genericamente ogni documento di governance o project definition.
- Non applicare automaticamente relazioni, tag, supersessioni, decisioni o vincoli.
- Non pubblicare una nuova registry topology stabile senza un consumer e uno schema separatamente approvati.
- Non estendere nella prima integrazione il retrieval pubblico a Change Set, Choice o Work target.
- Non incorporare nel dominio semantico la correzione funzionale del timeout preesistente; profiling e remediation delle scansioni necessarie all'integrazione restano tuttavia un gate obbligatorio di PROP-100.
- Non fissare nella proposta ombrello pesi numerici e layout dei moduli: tali dettagli appartengono alla feature versionata.

## PROP-101 - Project Readiness Convergence Workflow

### Goals

- Model project-readiness gaps as typed, prioritized and explainable records.
- Give each actionable required-section gap a declared question, a safe deterministic fallback or an explicit no-question diagnostic.
- Persist project-question lifecycle state, revisions, authority and provenance across sessions.
- Keep question answers distinct from applied project definition and owner decisions.
- Render owner-reviewable candidate definition patches and commit definition plus question state through one transaction.
- Integrate the highest-priority project gap into managed next actions.
- Preserve independent definition completeness and declared evidence coverage.
- Keep CLI and MCP contracts deterministic, bounded and semantically aligned.
- Preserve schema-v1 valid operations and provide a real transition-specific v1-to-v2 migration.
- Reconcile project questions safely across vertical revisions without re-opening or losing owner evidence.
- Preserve `PROP-100` authority by keeping unapplied question state non-semantic.
- Validate generic behavior against this repository without embedding repository-specific policy.

### Non-Goals

- Agents do not make owner decisions, fabricate owner answers, validate assumptions, complete sections, accept proposals or approve publication.
- This proposal does not replace proposal readiness or proposal questions.
- It does not create a second project definition, maturity, progress, next-action, decision-context or freshness engine.
- It does not automatically declare vertical coverage for legacy proposals.
- Heuristic matches never become owner-declared evidence automatically.
- It does not introduce database-backed persistence, a remote registry or hosted orchestration.
- It does not perform automatic agent curation, publication review or vertical upgrades.
- It does not remove schema-v1 compatibility, migrate implicitly or bypass the workspace migration lifecycle.
- It does not use clock-based preview expiry without an explicit durable preview-receipt contract.
- It does not treat migration absence of a legacy question as evidence that a question was answered or applied.

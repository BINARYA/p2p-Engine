# Project Scope

Generated from accepted proposal goals and non-goals.

## PROP-001 - CLI Foundation

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

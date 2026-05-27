# Project Problem

Generated from accepted proposal problem statements.

## PROP-001 - CLI Foundation

P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.

## PROP-004 - Prompt-only Import Workflow

P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.

## PROP-005 - Codex Skill Integration

Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.

## PROP-009 - Governance CLI Commands

P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.

## PROP-010 - P2P Project State Model

Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.

## PROP-011 - Project Refresh MVP

P2P Engine has accepted the .p2p/project state model, but the CLI cannot yet generate or inspect that rationalized project layer.

## PROP-012 - Impact Map and Conflict Memory

P2P Engine can generate a rationalized project state, but it does not yet capture what a proposal touches or whether it overlaps, depends on, supersedes, or conflicts with other proposals.

## PROP-013 - Managed Git Adapter and Change Set Model

P2P Engine distinguishes proposals from project state, but it does not yet define how accepted decisions become operational change sets or how Git operations should be managed under the hood without exposing branch/commit/merge complexity to users.

## PROP-014 - Change Set Metadata MVP

P2P Engine has accepted the Change Set and managed Git model, but the CLI cannot yet create or inspect .p2p/changes metadata.

## PROP-015 - Change Set Lifecycle and Task Tracking

P2P Engine can create metadata-only Change Sets, but it cannot yet move them through an operational lifecycle or inspect their tasks/actions.

## PROP-016 - Project Registries MVP

P2P Engine stores proposals, decisions, project state, conflicts and change sets, but it lacks explicit global registries for indexing and relating these artifacts.

## PROP-017 - Proposal Intake and Context Analysis MVP

P2P Engine can store proposals and registries, but it does not yet help agents or users decide whether a new idea should become a new proposal, enrich an existing one, open a choice, or be marked as overlapping/conflicting.

## PROP-018 - Choice Management CLI MVP

P2P Engine can represent a choice manually, but the CLI cannot yet create, list, or decide choices.

## PROP-019 - Proposal Decision Shortcut Commands

Users and agents must use p2p decision record with explicit outcomes to accept, reject, or defer proposals, which makes the workflow less natural.

## PROP-020 - Proposal Inspection CLI MVP

Users and agents can inspect proposals through p2p status or registries, but there are no dedicated p2p proposal list/show commands.

## PROP-021 - Agent Skill Real Commands Update

The local P2P Codex skill does not yet describe the current CLI capabilities: registries, intake, choices, proposal inspection and proposal decision shortcuts.

## PROP-022 - Operational Brief Prompt Workflow

Project status is currently technical and descriptive; agents can summarize it in chat, but the project lacks a versioned prompt/import workflow for operational synthesis.

## PROP-023 - Next Action Recommender MVP

The project now stores operational next-actions, but there is no top-level command that answers what to do next, and project status does not surface the operational brief state.

## PROP-024 - Choice Blocking and Discovery MVP

Choices can be created and decided, but they do not expose operational discovery, proposal-local choice candidates, or formal blockers for proposals and Change Sets.

## PROP-025 - Controlled Intake Apply Workflow

Intake analysis can recommend actions, but there is no controlled, auditable workflow to turn selected suggestions into P2P state changes.

## PROP-026 - P2P Software Spec Generator MVP

P2P can model proposals, decisions and Change Sets, but it cannot yet generate a normalized software specification suitable for downstream OpenSpec, Spec Kit, or code generation workflows.

## PROP-027 - Software Spec Exporter MVP

P2P can generate and refine P2P-native software specs, but it cannot yet export those specs into downstream code-generation or specification tool formats.

## PROP-028 - Spec Kit Export Mapping MVP

P2P can export generic and OpenSpec-oriented bundles from P2P-native software specs, but the declared Spec Kit export target still has no concrete mapping.

## PROP-029 - Spec Export Validation MVP

P2P can generate generic, OpenSpec-oriented, and Spec Kit-oriented export bundles, but it cannot yet validate whether an existing export bundle is complete and internally consistent before downstream use.

## PROP-030 - Managed Work and Multi-Branch Visibility Policy

P2P is moving toward managed Git under the hood, but users still lack a P2P-native work abstraction that can represent future branch, commit, review, and merge operations without exposing Git as the user interface.

## PROP-031 - Multi-Branch Work Scan MVP

P2P Work manifests can represent handoff plans locally, but P2P still cannot discover Work manifests that live on parallel P2P-managed branches without checking them out.

## PROP-032 - Managed Work Branch Creation MVP

P2P Work manifests can plan downstream work but cannot yet create an isolated managed branch for implementation.

## PROP-033 - Managed Work Submit MVP

P2P can create managed branches for Work items, but it cannot yet package completed branch work into an auditable managed commit.

## PROP-034 - Managed Work Review MVP

P2P can submit managed branch work as a local commit, but it cannot yet mark that submitted work as ready for owner review.

## PROP-035 - Managed Work Publish MVP

P2P can request local review for managed Work, but it cannot yet publish the reviewed branch to the configured remote for downstream owner inspection.

## PROP-036 - Managed Work Accept MVP

P2P can publish reviewed managed Work branches, but it cannot yet perform the owner-controlled local merge that accepts a Work item into the base branch.

## PROP-037 - Managed Work Status Summary MVP

The managed Work lifecycle now spans plan, branch, submit, review, publish, and accept, but users lack a single read-only view that explains each Work item state and next action.

## PROP-038 - Managed Work Merge Conflict Guidance MVP

p2p work accept can attempt a local merge, but merge conflicts are not represented clearly in P2P state and the user does not get guided recovery commands.

## PROP-039 - Managed Work Finalize MVP

After p2p work accept, the base branch merge remains local and P2P has no command to publish that accepted state to the remote.

## PROP-040 - Managed Work Cleanup MVP

After p2p work finalize, managed Work branches remain locally and remotely, and P2P has no explicit owner-controlled cleanup step.

## PROP-041 - Remote Project Profile and Review Request Policy

P2P can publish managed Work branches, but it does not yet distinguish local-only projects from remote-backed projects or express external review handoff without binding the core workflow to GitHub PRs.

## PROP-042 - P2P Core CLI MCP Mediator Web Boundary

P2P Engine needs a clear product and architecture boundary before adding MCP, mediator, web UI, or direct AI integrations. Without this boundary, the deterministic engine risks being coupled to optional AI or web infrastructure too early.

## PROP-043 - Managed Work Retire MVP

Obsolete planned Work manifests can remain in project status even after their source Change Set or export has already been completed, causing stale next actions.

## PROP-044 - P2P MCP Server MVP

Agents should access P2P project state through structured tools instead of parsing CLI text or reading .p2p files directly.

## PROP-045 - Agent-Safe Project Bootstrap MVP

New P2P projects do not give Codex, Claude, or other agents explicit boundaries. Agents can infer .p2p internals, edit files directly, invent IDs, or make owner-controlled decisions when an MCP or CLI primitive is missing.

## PROP-046 - MCP Write-Safe Bootstrap Tools MVP

The MCP server can read project state but cannot perform safe bootstrap operations. When an agent is asked to initialize or harden a project through MCP, it may fall back to manual filesystem edits if no explicit MCP primitive exists.

## PROP-047 - Guided Init Wizard MVP

P2P init can now generate safe project and agent boundaries, but non-technical users still need to know which flags to pass for project name, agent profile, repository mode, and MCP setup hints.

## PROP-048 - MCP Level 3 Proposal and Intake Draft Tools

Agents can now initialize projects and refresh registries through MCP, but cannot create draft proposals or intake prompts without a local p2p CLI in PATH. This keeps common contribution workflows dependent on shell setup and can push agents toward stopping even for safe draft creation.

## PROP-049 - MCP Level 4A Proposal Refinement Tools

MCP can create draft proposals and intake prompts, but agents still cannot refine an existing draft proposal or generate/show the operational project brief through MCP. This limits iterative proposal development after Level 3.

## PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

MCP can create and refine draft proposals, but agents still cannot use existing advisory analysis commands for choice discovery, conflict inspection, or impact prompt generation through MCP.

## PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

After MCP creates a draft proposal, p2p next can still fall back to generic project status instead of pointing the owner or agent at the draft proposal. Agent instructions also do not explicitly require show/read commands before explaining existing P2P artifacts.

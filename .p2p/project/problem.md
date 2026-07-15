# Project Problem

Generated from accepted proposal problem statements.

## PROP-001 - — CLI Foundation

P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.

## PROP-002 - Proposal Exploration And Readiness Workflow

P2P Engine deve impedire che una proposta passi troppo rapidamente da idea
generica a decisione accettata senza una esplorazione sufficiente. Il problema
non e solo creare file di exploration o generare prompt: il sistema deve aiutare
owner e agenti a capire se una proposta e davvero matura, quali lacune restano,
quanto l'agente deve essere pedante, e quando serve una decisione esplicita
dell'owner.

Senza questo livello, le proposal rischiano di documentare la prima soluzione
emersa invece di mostrare una scelta consapevole tra alternative reali. Gli
artifact possono esistere ma restare vuoti, generici o non collegati a criteri
decisionali. `p2p next` puo limitarsi a suggerire una review generica invece di
indicare azioni concrete per migliorare la proposta.

P2P Engine ha quindi bisogno di un workflow di exploration e readiness che renda
visibile la qualita metodologica della proposta senza sostituire la governance
dell'owner.

## PROP-004 - Prompt-only Import Workflow

P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.

## PROP-005 - Codex Skill Integration

Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.

## PROP-006 - Multi-Agent Integration Model

P2P Engine can already generate basic agent-facing instructions for generic, Codex, and Claude profiles, but it does not yet manage agent integrations as governed, inspectable, updateable project state. Project initialization should create the supported project-local agent file structures by default, but today there is no explicit registry of installed integrations, generated-file manifests, hashes, drift detection, safe update, safe uninstall, conflict detection, or precise adapter matrix for Cursor, Copilot, Gemini, OpenCode, Codex, Claude, and the generic baseline. A second gap is methodological: generated instructions do not yet force agents to turn weak proposal readiness, failed gates, and owner questions into concrete refinement actions, alternatives, recommendations, candidate edits, and readiness re-checks.

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

## PROP-052 - MCP Proposal Contribution Tool

Agents can create new draft proposals through MCP, but cannot safely attach new information to an existing proposal. This encourages proposal proliferation when a comment, criterion, objection, or suggestion should be recorded as a contribution instead.

## PROP-053 - Core Validation Layer MVP

P2P projects can now be manipulated through CLI and MCP, but there is no deeper read-only validation layer to detect malformed YAML, missing proposal sections, stale registries, or basic status inconsistencies before agents, CI, or future packaging workflows rely on the state.

## PROP-054 - Project Readiness and Maturity Assessment

P2P can track proposals, choices, changes, work, validation and MCP workflows, but it does not yet provide a structured assessment of how complete or mature a project is. Users need a way to understand whether a project is ready to proceed and which gaps matter most in the project context.

## PROP-055 - Agent Token Budget and Context Discipline

P2P Engine reduces conversational memory by storing governance state in .p2p and Git, but agents can still consume excessive tokens by scanning broad project context, reading full registries, loading many proposal/change files, or explaining artifacts from conversation memory instead of compact deterministic views. This is especially visible in the P2P Engine repository because the project is using P2P to build P2P, but the risk applies to any large P2P workspace used by CLI or MCP agents.

## PROP-056 - Project Definition Maturity Rubrics

P2P assess currently measures deterministic structural readiness: validation, registries, proposal status, choices, changes, work items, and operational brief availability. This is useful, but it does not evaluate whether the planned project definition covers the important topics for its domain. For P2P exports, the main question is not whether implementation is complete, but whether the project has been sufficiently defined through proposals, decisions, tradeoffs, risks, requirements, and acceptance criteria.

## PROP-057 - Guided Rubric Selection During Init

The init wizard now asks for a project domain and generates domain rubrics automatically, but the owner cannot confirm which suggested criteria should actually drive project definition maturity. This makes the rubric feel imposed by the system instead of selected as part of project governance.

## PROP-058 - Project README and Installation Guide

P2P Engine now has a mature Core/CLI/MCP MVP with init wizard, context packets, validation, readiness assessment, project definition rubrics, maturity assessment, spec/export flows, and managed work lifecycle. The repository README and installation guidance need to become an accurate entry point for new users instead of relying on chat history or internal project state.

## PROP-059 - P2PWorkspace Modular Refactoring Plan

P2PWorkspace has grown into a large monolithic class that contains initialization, proposals, governance, project state, assessment, context, specs, Change Sets, Work lifecycle, registry, and Git-related behavior. This is functional for the MVP but increases cognitive load, regression risk, and difficulty for contributors.

## PROP-060 - Real Test Coverage Reporting

P2P Engine has a mature marker-based pytest suite, but it still lacks an occasional code coverage diagnostic. Maintainers cannot easily see which runtime modules or branches are never exercised by a chosen validation tier. This is an internal software-maintenance observability gap for P2P Engine itself, not a project-design evidence gap for users designing non-software projects with P2P Engine.

## PROP-061 - Focused README and Documentation Map

The README should be the entry point for the p2p-engine repository, but it currently mixes engine scope with broader future product layers and does not yet provide a clean documentation map for CLI, MCP, agent integration, and core API references.

## PROP-062 - README Product Landing Page Refinement

The README should work as the public landing page for P2P Engine, but the current structure is still repository-oriented and does not lead with why the project exists, who it is for, a 5-minute demo, and a concise glossary.

## PROP-064 - Spec Kit Three-Prompt Export Model

The current P2P export model produces downstream-shaped file bundles for generic, OpenSpec, and Spec Kit targets. That makes P2P look like a folder generator and creates low-value handoff files. The intended value is different: P2P should synthesize accepted project memory into a robust project definition, then derive small agent-consumable prompt/document outputs for downstream systems.

## PROP-065 - MCP Agent-First Coverage Expansion

The CLI contains many read-only, write-safe, and prompt/advisory workflows that are useful for agents, but the MCP server exposes only a limited subset. This makes MCP less effective as the primary agent substrate, especially after agent-first project export became central.

## PROP-066 - Permission-Gated MCP Governance And Git Operations

The MCP surface intentionally excludes governance, ownership-sensitive, import, Git lifecycle, and repository publishing operations. These capabilities may become useful for advanced agent workflows, but exposing them before a repository permission and ownership model is defined would let agents perform actions that should remain owner-controlled.

## PROP-067 - Agent-First Setup Documentation Split

Public setup documentation still mixes two workflows: using P2P Engine for a new project and contributing to the P2P Engine repository itself. This can make users think they should operate the CLI manually or initialize work inside the engine repository when the normal workflow is to install P2P once and let an agent use it on a separate target project.

## PROP-068 - Document Agent MCP Client Setup Commands

The new-project setup explains the P2P MCP server command but does not clearly show how to add that server to specific agent environments. Users need concrete setup commands for common MCP-capable clients without confusing target-project setup with P2P Engine contributor setup.

## PROP-069 - Clarify MCP Stdio Integration Model

The installation and MCP documentation show client setup commands but do not explain that MCP stdio is not a shared server process. Users may misunderstand how multiple agents connect to P2P, where shared state lives, and when Streamable HTTP would be needed.

## PROP-070 - Clarify README Agent Access Modes

The README says to connect an agent through MCP but does not clearly distinguish CLI access from MCP access. This can make MCP appear complete even though the current MCP surface is intentionally agent-safe and excludes privileged governance, imports, Git operations, and Work lifecycle actions.

## PROP-071 - Custom Domain Definition Workflow

P2P currently treats project domains as a fixed set of hardcoded identities. This makes predefined domains look authoritative at init time and makes custom domains an exception, even though P2P's broader model is that projects often start from unclear intent and become defined through user-agent collaboration.

## PROP-072 - Concurrent Managed Work and Merge Decision Model

P2P Engine needs a first-class collaboration model for multiple people and agents working through Git without needing to understand Git. Main must represent accepted project state, but new proposal drafts, proposal refinements, and implementation candidates may be produced concurrently by different contributors. Today the managed Work lifecycle covers implementation branches, but proposal-level collaboration, candidate selection, and merge decisions across concurrent contributors are not specified as a single CLI-facing workflow.

Without this model, users may treat main as a shared scratchpad for draft proposals, agents may not know when to branch or publish, and P2P lacks a first-class way to compare, select, reject, combine, or merge competing proposal/work candidates before they alter accepted project state.

## PROP-073 - Ergonomic Remote Project Initialization

Initializing a cloud-backed P2P project currently requires separate mental steps: p2p init declares repository mode, raw Git config creates or attaches the Git remote, and p2p project remote configure records the P2P remote profile. This is workable for experienced users but too implicit for owners, contributors, and agents who should not need to understand raw Git setup details.

## PROP-074 - Agent Runtime Bootstrap Robustness

A P2P-managed repository can be shared with a cloud agent environment where project instructions require p2p CLI mutations, but the p2p executable is not installed or available in PATH. The agent correctly stops because direct .p2p edits are forbidden, but the workflow becomes unusable: it cannot create proposals, refresh registries, read context, or proceed through the documented P2P source-of-truth path.

## PROP-075 - MCP End-To-End Proposal Collaboration Workflow

MCP exposes useful proposal collaboration primitives, but a cloud or agent-only workflow is not yet end-to-end. An agent can create proposals and branches, but publish requires a consent receipt that MCP cannot request or create; remote P2P profile configuration is CLI-only; proposal drafts created through MCP leave a dirty worktree that blocks branch creation; and proposal branches can be accidentally chained from the current branch instead of a stable base branch.

## PROP-076 - P2P Cloud Runner Boundary and Containerized Execution Model

P2P Engine is intentionally a local CLI/core/MCP engine, but future cloud/web product work needs a clear execution boundary. Without an explicit boundary, proposals may drift toward embedding public web APIs, multi-tenant auth, workflow orchestration, or long-running SaaS responsibilities directly inside P2P Engine.

## PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

MCP exposes proposal branch accept/reject but does not expose direct draft proposal accept/reject/defer decisions, so agents using MCP cannot complete owner-approved governance on draft proposals without falling back to CLI or raw state edits.

## PROP-078 - Project-Local Wheel Installation and Upgrade Model

P2P Engine is currently practical to update only when the operator understands a separate source checkout or external path. Existing P2P projects need a coherent project-local installation and upgrade path that does not require referencing another folder, cloning the engine inside every project, or rerunning p2p init.

## PROP-079 - Managed Next Action Lifecycle

P2P next actions can become stale because .p2p/project/next-actions.yml is curated project state but the CLI only reads it. There is no managed command to add, complete, retire, or refresh next actions, so agents either leave obsolete items such as completed consolidation tasks visible or must edit .p2p state by hand, which violates the managed-state boundary.

## PROP-080 - Automated GitHub Release Wheel Publishing

Publishing P2P Engine as a project-local wheel currently requires a manual, error-prone release cycle: bump version, build artifacts locally, create a tag, create a GitHub Release, and upload .whl/.tar.gz assets through the UI. This makes frequent updates slow and increases the chance of mismatched version, tag, and wheel filenames.

## PROP-081 - MCP and Skill Support for Managed Next Actions

The CLI now supports managed next-action lifecycle commands, but the agent skill and MCP surface still describe p2p_next as read-only/advisory only. Agents using MCP cannot add, complete, retire, or refresh curated next actions, and agents following the skill may not know the CLI lifecycle exists.

## PROP-082 - Readiness Assessment Refresh And Review Workflow

The current proposal readiness CLI can bootstrap and refresh readiness snapshots, but it does not provide a governed way to qualitatively reassess an updated proposal, confirm that owner questions have been resolved, raise confidence, update criterion scores, clear failed gates, or import and review an evidence-based assessment. As seen with earlier accepted proposals, a proposal can become substantively ready for decision while p2p proposal readiness refresh still keeps a conservative bootstrap score, forcing acceptance to rely on owner override even when the artifacts are actually mature. The deeper issue is that readiness currently mixes two distinct capabilities. First, P2P must store enough exhaustive, inspectable information to judge proposal quality: artifacts, evidence, scores, missing items, gates, confidence, audit notes, unresolved owner questions, question state, and aggregation candidates. Second, P2P must guide the agent behavior that uses that information: the agent must be explicitly told to be proactive, pedantic, skeptical of thin artifacts, willing to ask owner questions, and unwilling to recommend acceptance when methodological gaps remain. Storing complete information is necessary but not sufficient. Without explicit agent behavioral guidance, an agent can read complete state and still behave passively, summarize gaps without challenging them, or treat a mechanically valid proposal as decision-ready. Without deterministic question-and-answer memory, the agent cannot reliably conduct an interview, track which gaps have been resolved, decide whether to re-ask, defer, or mute questions, detect proposal overlap during the interview, or use owner answers to refine the proposal.

## PROP-083 - Domain-Aware Visible Project Definition Export

P2P Engine currently routes accepted project intent through Change Set software-spec and spec-export outputs. This makes every project look like a software implementation workflow, even when the project domain is not software. P2P Engine is meant to define projects in detail across many vertical domains, not only to produce software delivery artifacts. The current generated outputs are also hidden under .p2p/outputs, which makes the human-facing project definition hard for normal users to find and inspect. Users need a visible, comprehensive, domain-aware project definition that captures what emerged during proposal preparation, exploration, decisions, and refinement.

## PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

A shared P2P-managed project must declare which P2P Engine runtime version is expected after clone, copy, or archive extraction. The problem is runtime version alignment: a human or agent must be able to determine the compatible runtime range and the recommended runtime version from project-local data, without relying on chat history, local machine state, Git history, or a separate P2P Engine source checkout.

## PROP-085 - Pluggable Project Verticals And Readiness Orchestration

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

## PROP-086 - Artifact-aware Proposal Readiness And Agent Interview Orchestration

Agents are willing to explore new proposals, but proposal-side artifacts such as open questions, clarifications, findings, exploration notes, and impact maps often remain nearly empty. Current readiness can mark a proposal decision-ready when the main proposal body is coherent, without making artifact coverage visible as a gap or requiring the agent to explain why an artifact is empty. This weakens auditability, owner prompting, impact analysis, and long-term proposal memory for complex or cross-cutting work.

## PROP-087 - Agent Personality Model For Decision Mediation

Agents currently adapt tone and technical detail only through prompt text or chat habit. The project needs an explicit, configurable interaction model for how an agent or mediator addresses the decision owner.

## PROP-088 - MCP Artifact Import Parity

Real MCP testing showed a gap in the proposal artifact workflow. MCP clients can generate prompts, update structured proposal sections, and set artifact coverage state, but they cannot import or update long-form proposal artifact content such as exploration.md, findings.md, clarifications.md, or impact-map.yml through MCP. The CLI already has controlled import primitives for impact and exploration outputs, so MCP users hit a missing primitive even when the core engine can perform the write safely.

## PROP-089 - Readiness Question-State Convergence

Proposal readiness currently has two competing sources for owner-question state: the structured questions.yml lifecycle and the legacy open-questions.md markdown text. When both exist, readiness can continue to treat stale markdown questions as open even after the corresponding structured questions have been answered and applied.

This creates a false blocker at the per-proposal readiness level. A proposal can show owner_questions_resolution:needs_owner_input even though questions.yml shows that the owner has already answered or resolved the relevant questions. The issue does not affect whole-project readiness directly; it affects the readiness assessment for individual proposals and then propagates misleading next actions to agents and owners.

The impact is practical: agents may keep asking for already-resolved input, owners may see a proposal as less mature than it is, and acceptance decisions may require unnecessary override. The root cause is that readiness still parses open-questions.md as blocking state instead of treating questions.yml as the authoritative lifecycle record whenever structured question state exists.

## PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

## PROP-091 - Governance Policy Convergence

P2P Engine already has governance-aware artifacts and helper utilities, but they
do not yet form a coherent operational governance policy. The project can store
`governance.yml`, `roles.yml`, `permissions.yml`, choices, votes, decision
precedents, explicit blockers, and owner-controlled decisions, but there is no
single structured evaluation that answers these questions before a decision:

- who is attempting to decide;
- whether that actor is allowed to decide;
- what target is being decided;
- which governance mode applies;
- whether the governance state is valid and readable;
- how the proposed decision relates to votes, blockers, and precedents;
- whether the decision can proceed normally, requires rationale, requires owner
  override, or must be blocked.

Without this layer, governance artifacts remain useful as audit records but weak
as decision support. Agents and external clients can see fragments of governance
state, yet they cannot consume a stable preflight contract that explains the
decision context in a deterministic way.

## PROP-092 - Local MCP Work Lifecycle Parity And Remote Gateway Boundary

P2P Engine can execute the managed Work lifecycle through the CLI, and it already exposes permission-gated MCP tools for several proposal-branch and sync operations. Work items, however, still have only partial MCP coverage: agents can inspect or create Work plans, but cannot use the local MCP adapter to publish, request review, accept, finalize, or clean up Work items through the same domain-specific controls available in the CLI. This leaves agent-first local workflows incomplete and tempts agents or external integrations to fall back to raw Git operations, which would bypass the P2P Work lifecycle, consent receipts, state checks, and audit semantics.

## PROP-093 - Agent Persistence Boundaries And Proposal Authoring Flow

Real new-project and external-agent tests showed that P2P Engine installs and works, and that agents can use it to capture project reasoning as structured state. That early use of P2P is desirable.

The problem is not that agents use P2P too soon. The problem is that P2P currently gives agents and owners some ambiguous signals about persistent writes and proposal authoring.

An agent can create or modify durable project knowledge without first showing the owner exactly what will become persistent state. A second, deeper ambiguity is inside the proposal workspace itself: P2P scaffolds narrative markdown files such as `alternatives.md`, `findings.md`, and `open-questions.md`, while generated instructions also say not to edit `.p2p/` by hand. If the canonical input is structured contribution or question state, those markdown placeholders look like editable files but are not the right write interface.

A related ambiguity is the physical shape of proposal directories. Different workflows can materialize different files for valid reasons: one proposal may have conflict analysis or related-proposal artifacts, while another may not. That can make the CLI feel non-deterministic if owners or agents infer proposal completeness from `ls`. The deterministic surface should be a CLI/MCP-visible logical artifact schema, not a requirement that every proposal directory contains every possible file.

The feedback also shows a documentation gap. P2P already has README, concepts, CLI, MCP, and agent-integration documentation, but agents still need a compact operational routing guide that answers: what is P2P for, when should an agent stay in chat, when should it create or update P2P state, when should it use project definition, when should it create proposals or choices, when should it defer to an explicit vertical primitive such as the PROP-094 software-spec lifecycle, and when is a requested file outside P2P governance.

The new-project bootstrap issue needs a more precise direction than simply changing the default from broad to narrow. A broad default creates noise when every adapter is generated without owner intent. A narrow default creates a different failure mode when the owner later opens the same project with Claude, Cursor, Copilot, Gemini, OpenCode, or another supported agent and cannot easily discover how to add that integration.

The result is predictable: a capable agent may duplicate content, write directly under `.p2p/`, create external project documents, jump to a spec file, judge proposal completeness from filesystem shape, or fail to onboard a second agent because the engine does not make the canonical authoring flow, artifact status model, agent request-routing model, and integration lifecycle obvious enough.

The core product issue is therefore:

- persistent agent writes are not classified and previewed clearly enough;
- canonical P2P inputs and generated narrative artifacts are not visually and operationally distinct enough;
- proposal artifact status is not exposed as a deterministic logical catalog independent of physical file materialization;
- agents lack a concise operational playbook that maps owner requests to the correct P2P route;
- the proposal authoring flow is not discoverable enough from help text, scaffold output, and owner-facing views;
- agent integration bootstrap is too broad today, but a narrow default would be unsafe unless add/remove lifecycle commands are visible from init summaries and generated instructions;
- P2P's decision root must be explicit and robust, but this must not be misread as an endorsement of any specific repository topology such as sibling specification repositories.

## PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

## PROP-095 - Project Runtime Contract Update Lifecycle

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

## PROP-096 - Readiness Evidence Quality and Question State Normalization

Readiness assessment can report false missing evidence when composed evidence includes a placeholder-only secondary artifact. We observed this when a meaningful Acceptance Criteria section was combined with an execution-plan.md file containing only the literal placeholder line `Pending`. The proposal question workflow can also leave answered questions in an inconsistent state where applied_to_proposal is true but state remains answered, causing readiness to keep reporting answered_not_applied even though the answer was already incorporated.

## PROP-097 - Runtime Contract Adoption For Legacy Projects

Projects created before the runtime contract feature can remain in
`legacy_undeclared` state. They have no `.p2p/project/runtime.yml` and no
`runtime_contract.required` marker, so `p2p validate` keeps warning that
compatibility cannot be inferred. Manually editing `.p2p` would solve one
repository once, but it would bypass the P2P write boundary and would not
provide a reusable safe path for other legacy projects.

## PROP-099 - Project Output Lifecycle and Retention Policy

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

## PROP-100 - Project Decision Context Index and Proposal Neighborhood

P2P conserva gia molte informazioni necessarie a ricostruire il ragionamento del progetto: decisioni e motivazioni nei Markdown, stati e readiness negli YAML, impact map, related proposals, conflict analysis, choice, Change Set, registri, artifact state, vertical coverage, decision precedents e artifact di pubblicazione. Il problema osservato non e prima di tutto il formato di persistenza. Il problema e che i servizi che generano registri, contesti e prompt ne usano solo una parte, perdendo motivazioni, vincoli, relazioni, autorita, provenienza e stato di attivazione.

La revisione della codebase e della feature implementativa ha chiarito ulteriori cause:

- `decisions-map.yml` e `relations.yml` sono projection lossy e non possono essere usati come memoria semantica autorevole;
- intake e context rendering usano ancora selezioni first-N o letture globali non ordinate per rilevanza;
- alcuni path ricostruiscono Change Set o summary ripetutamente e possono moltiplicare scansioni e tempi di risposta;
- il parser Markdown corrente e stretto e non preserva span, sezioni duplicate o diagnostica affidabile per frontmatter malformato;
- `P2PWorkspace` memoizza i service object, quindi un indice conservato nel service potrebbe diventare stale dopo una scrittura nella stessa sessione;
- proposal status e decision outcome possono divergere e il lifecycle include stati come `accepted_with_changes`, `split`, `merged_into_other` e `superseded` che non possono essere ridotti a accepted/rejected;
- decision precedents, project definition, governance constraints e Work execution state devono avere scope e authority espliciti;
- Change Set frontmatter e file di relazione companion possono duplicare o contraddirsi;
- similarity, topologia e authority sono dimensioni differenti e non devono essere fuse in uno score opaco;
- `generated_at` non puo far cambiare l'identita semantica di un output deterministico;
- CLI e MCP possono divergere se payload, serializer e target compatibility non vengono aggiornati nella stessa slice.

L'effetto pratico resta invariato: P2P possiede memoria, ma non recupera in modo affidabile cio che e gia stato deciso o analizzato quando deve supportare una nuova proposta, un intake, una sintesi o il prossimo passo.

## PROP-101 - Project Readiness Convergence Workflow

P2P Engine can diagnose project readiness but cannot yet drive a project from a diagnosed vertical gap to an auditable owner-reviewed update. The current review identifies incomplete capisaldi, declared evidence and unmapped proposals, but its convergence behavior is incomplete:

- it returns generic advice to complete the definition and rerun the review;
- some required incomplete sections have no applicable generated question;
- there is no persistent project-level question lifecycle equivalent to the proposal-question workflow;
- owner answers are not connected to a governed candidate project-definition patch;
- project-definition gaps are not coherently prioritized in managed next actions;
- large legacy proposal lists are emitted without bounded detail or prioritization;
- progress, readiness and freshness expose useful but separate states without an orchestration contract that closes the loop.

The result is a system that knows what is incomplete but still depends on an agent or owner to reconstruct the next workflow manually across multiple commands and sessions.

The implementation risk is broader than question generation. A naive implementation could create competing authority between project-question state, project definition, decision context, managed next actions and workspace migration state. It could also reuse the existing single-file definition apply in a way that leaves question and definition state partially committed, or register a v1-to-v2 migration while still executing the current legacy-to-v1 bootstrap planner.

# Project Problem

Derived problem evidence grouped by active vertical section. `.p2p/` remains authoritative.

## Assumptions (`assumptions`)

### PROP-100 - Project Decision Context Index and Proposal Neighborhood

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-6090667593464748c2106a3b`).

## Decisions And Open Questions (`decisions`)

### PROP-091 - Governance Policy Convergence

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-a595849db855e7d18119a70b`).

### PROP-101 - Project Readiness Convergence Workflow

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-8e1cd9c06d57e32d85fbe768`).

### PROP-102 - Proposal Decision Revision and Revocation Lifecycle

P2P currently represents a proposal decision primarily as one current outcome.
The decision write path replaces `decision.md` and then replaces the status in
`proposal.md`, without validating the previous lifecycle state or preserving a
queryable sequence of owner decisions.

As a result, an accepted proposal can be rewritten as rejected. The current
workspace then appears to say that the proposal was never adopted, even though
it may already have influenced project definition, Change Sets, Work,
specifications, implementation, publication and later decisions. Git can
recover earlier bytes, but normal validation, retrieval and derived-state
consumers do not use Git history as the proposal decision model.

The model also lacks a precise distinction between rejection before adoption,
withdrawal before decision, revocation after acceptance, replacement,
reinstatement and downstream deprecation. Without that distinction, future
decision-memory consolidation cannot reliably determine which decisions are
active, historical, previously active, replaced or merely deferred.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-43062e3e83542d81e50ad6bf`).

## Definition Of Done And Readiness (`definition_of_done`)

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-d88bb02fdcfb6db4dec516f2`).

### PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-432042b763efb79ca58bc262`).

### PROP-101 - Project Readiness Convergence Workflow

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-8e1cd9c06d57e32d85fbe768`).

## Expected Artifacts (`artifacts`)

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-d88bb02fdcfb6db4dec516f2`).

### PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-2cb54e5ebdc1161ce91a6a03`).

### PROP-099 - Project Output Lifecycle and Retention Policy

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-e59661e429785a0227a72c3a`).

### PROP-101 - Project Readiness Convergence Workflow

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-8e1cd9c06d57e32d85fbe768`).

### PROP-102 - Proposal Decision Revision and Revocation Lifecycle

P2P currently represents a proposal decision primarily as one current outcome.
The decision write path replaces `decision.md` and then replaces the status in
`proposal.md`, without validating the previous lifecycle state or preserving a
queryable sequence of owner decisions.

As a result, an accepted proposal can be rewritten as rejected. The current
workspace then appears to say that the proposal was never adopted, even though
it may already have influenced project definition, Change Sets, Work,
specifications, implementation, publication and later decisions. Git can
recover earlier bytes, but normal validation, retrieval and derived-state
consumers do not use Git history as the proposal decision model.

The model also lacks a precise distinction between rejection before adoption,
withdrawal before decision, revocation after acceptance, replacement,
reinstatement and downstream deprecation. Without that distinction, future
decision-memory consolidation cannot reliably determine which decisions are
active, historical, previously active, replaced or merely deferred.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-43062e3e83542d81e50ad6bf`).

## System Objective (`system_objective`)

### PROP-001 - — CLI Foundation

P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-2239c0460a206cca11c132a3`).

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-d88bb02fdcfb6db4dec516f2`).

### PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-2cb54e5ebdc1161ce91a6a03`).

## Users And Actors (`users_and_actors`)

### PROP-006 - Multi-Agent Integration Model

P2P Engine can already generate basic agent-facing instructions for generic, Codex, and Claude profiles, but it does not yet manage agent integrations as governed, inspectable, updateable project state. Project initialization should create the supported project-local agent file structures by default, but today there is no explicit registry of installed integrations, generated-file manifests, hashes, drift detection, safe update, safe uninstall, conflict detection, or precise adapter matrix for Cursor, Copilot, Gemini, OpenCode, Codex, Claude, and the generic baseline. A second gap is methodological: generated instructions do not yet force agents to turn weak proposal readiness, failed gates, and owner questions into concrete refinement actions, alternatives, recommendations, candidate edits, and readiness re-checks.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-c1954dabe48c3eac3790d9f3`).

### PROP-091 - Governance Policy Convergence

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-a595849db855e7d18119a70b`).

## Scope And MVP Boundaries (`mvp_scope`)

### PROP-001 - — CLI Foundation

P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-2239c0460a206cca11c132a3`).

### PROP-044 - P2P MCP Server MVP

Agents should access P2P project state through structured tools instead of parsing CLI text or reading .p2p files directly.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-9b2fbda413f210f58998d716`).

### PROP-055 - Agent Token Budget and Context Discipline

P2P Engine reduces conversational memory by storing governance state in .p2p and Git, but agents can still consume excessive tokens by scanning broad project context, reading full registries, loading many proposal/change files, or explaining artifacts from conversation memory instead of compact deterministic views. This is especially visible in the P2P Engine repository because the project is using P2P to build P2P, but the risk applies to any large P2P workspace used by CLI or MCP agents.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-7820f734b700eb50bb448d39`).

### PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

A shared P2P-managed project must declare which P2P Engine runtime version is expected after clone, copy, or archive extraction. The problem is runtime version alignment: a human or agent must be able to determine the compatible runtime range and the recommended runtime version from project-local data, without relying on chat history, local machine state, Git history, or a separate P2P Engine source checkout.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-db5bd2205413ebebfde29a7d`).

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-d88bb02fdcfb6db4dec516f2`).

### PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-2cb54e5ebdc1161ce91a6a03`).

### PROP-099 - Project Output Lifecycle and Retention Policy

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-e59661e429785a0227a72c3a`).

## Workflows And Use Cases (`workflows_use_cases`)

### PROP-001 - — CLI Foundation

P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-2239c0460a206cca11c132a3`).

### PROP-006 - Multi-Agent Integration Model

P2P Engine can already generate basic agent-facing instructions for generic, Codex, and Claude profiles, but it does not yet manage agent integrations as governed, inspectable, updateable project state. Project initialization should create the supported project-local agent file structures by default, but today there is no explicit registry of installed integrations, generated-file manifests, hashes, drift detection, safe update, safe uninstall, conflict detection, or precise adapter matrix for Cursor, Copilot, Gemini, OpenCode, Codex, Claude, and the generic baseline. A second gap is methodological: generated instructions do not yet force agents to turn weak proposal readiness, failed gates, and owner questions into concrete refinement actions, alternatives, recommendations, candidate edits, and readiness re-checks.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-c1954dabe48c3eac3790d9f3`).

### PROP-044 - P2P MCP Server MVP

Agents should access P2P project state through structured tools instead of parsing CLI text or reading .p2p files directly.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-9b2fbda413f210f58998d716`).

### PROP-055 - Agent Token Budget and Context Discipline

P2P Engine reduces conversational memory by storing governance state in .p2p and Git, but agents can still consume excessive tokens by scanning broad project context, reading full registries, loading many proposal/change files, or explaining artifacts from conversation memory instead of compact deterministic views. This is especially visible in the P2P Engine repository because the project is using P2P to build P2P, but the risk applies to any large P2P workspace used by CLI or MCP agents.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-7820f734b700eb50bb448d39`).

### PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

A shared P2P-managed project must declare which P2P Engine runtime version is expected after clone, copy, or archive extraction. The problem is runtime version alignment: a human or agent must be able to determine the compatible runtime range and the recommended runtime version from project-local data, without relying on chat history, local machine state, Git history, or a separate P2P Engine source checkout.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-db5bd2205413ebebfde29a7d`).

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-d88bb02fdcfb6db4dec516f2`).

### PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-432042b763efb79ca58bc262`).

### PROP-091 - Governance Policy Convergence

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-a595849db855e7d18119a70b`).

### PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-2cb54e5ebdc1161ce91a6a03`).

### PROP-095 - Project Runtime Contract Update Lifecycle

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-9f420787b6b3fe00db392821`).

### PROP-099 - Project Output Lifecycle and Retention Policy

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-e59661e429785a0227a72c3a`).

### PROP-100 - Project Decision Context Index and Proposal Neighborhood

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-6090667593464748c2106a3b`).

### PROP-101 - Project Readiness Convergence Workflow

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-8e1cd9c06d57e32d85fbe768`).

## Domain Concepts And Data Model (`data_model`)

### PROP-006 - Multi-Agent Integration Model

P2P Engine can already generate basic agent-facing instructions for generic, Codex, and Claude profiles, but it does not yet manage agent integrations as governed, inspectable, updateable project state. Project initialization should create the supported project-local agent file structures by default, but today there is no explicit registry of installed integrations, generated-file manifests, hashes, drift detection, safe update, safe uninstall, conflict detection, or precise adapter matrix for Cursor, Copilot, Gemini, OpenCode, Codex, Claude, and the generic baseline. A second gap is methodological: generated instructions do not yet force agents to turn weak proposal readiness, failed gates, and owner questions into concrete refinement actions, alternatives, recommendations, candidate edits, and readiness re-checks.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-c1954dabe48c3eac3790d9f3`).

### PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

A shared P2P-managed project must declare which P2P Engine runtime version is expected after clone, copy, or archive extraction. The problem is runtime version alignment: a human or agent must be able to determine the compatible runtime range and the recommended runtime version from project-local data, without relying on chat history, local machine state, Git history, or a separate P2P Engine source checkout.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-db5bd2205413ebebfde29a7d`).

### PROP-085 - Pluggable Project Verticals And Readiness Orchestration

Project initialization and project readiness currently rely on domain/rubric defaults that are useful but too static: P2P can suggest rubric criteria, but it does not yet model verticals as extensible project-specific packages with sections, maturity rules, questions, artifacts, examples, and agent guidance. This risks hardcoding a finite catalog of domains inside the engine, or leaving agents without enough structure to proactively define what a project should achieve in its chosen vertical.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-d88bb02fdcfb6db4dec516f2`).

### PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-432042b763efb79ca58bc262`).

### PROP-091 - Governance Policy Convergence

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-a595849db855e7d18119a70b`).

### PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-2cb54e5ebdc1161ce91a6a03`).

### PROP-095 - Project Runtime Contract Update Lifecycle

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-9f420787b6b3fe00db392821`).

### PROP-099 - Project Output Lifecycle and Retention Policy

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-e59661e429785a0227a72c3a`).

### PROP-100 - Project Decision Context Index and Proposal Neighborhood

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-6090667593464748c2106a3b`).

### PROP-101 - Project Readiness Convergence Workflow

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-8e1cd9c06d57e32d85fbe768`).

### PROP-102 - Proposal Decision Revision and Revocation Lifecycle

P2P currently represents a proposal decision primarily as one current outcome.
The decision write path replaces `decision.md` and then replaces the status in
`proposal.md`, without validating the previous lifecycle state or preserving a
queryable sequence of owner decisions.

As a result, an accepted proposal can be rewritten as rejected. The current
workspace then appears to say that the proposal was never adopted, even though
it may already have influenced project definition, Change Sets, Work,
specifications, implementation, publication and later decisions. Git can
recover earlier bytes, but normal validation, retrieval and derived-state
consumers do not use Git history as the proposal decision model.

The model also lacks a precise distinction between rejection before adoption,
withdrawal before decision, revocation after acceptance, replacement,
reinstatement and downstream deprecation. Without that distinction, future
decision-memory consolidation cannot reliably determine which decisions are
active, historical, previously active, replaced or merely deferred.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-43062e3e83542d81e50ad6bf`).

## Integrations And Dependencies (`integrations_dependencies`)

### PROP-006 - Multi-Agent Integration Model

P2P Engine can already generate basic agent-facing instructions for generic, Codex, and Claude profiles, but it does not yet manage agent integrations as governed, inspectable, updateable project state. Project initialization should create the supported project-local agent file structures by default, but today there is no explicit registry of installed integrations, generated-file manifests, hashes, drift detection, safe update, safe uninstall, conflict detection, or precise adapter matrix for Cursor, Copilot, Gemini, OpenCode, Codex, Claude, and the generic baseline. A second gap is methodological: generated instructions do not yet force agents to turn weak proposal readiness, failed gates, and owner questions into concrete refinement actions, alternatives, recommendations, candidate edits, and readiness re-checks.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-c1954dabe48c3eac3790d9f3`).

### PROP-044 - P2P MCP Server MVP

Agents should access P2P project state through structured tools instead of parsing CLI text or reading .p2p files directly.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-9b2fbda413f210f58998d716`).

### PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

A shared P2P-managed project must declare which P2P Engine runtime version is expected after clone, copy, or archive extraction. The problem is runtime version alignment: a human or agent must be able to determine the compatible runtime range and the recommended runtime version from project-local data, without relying on chat history, local machine state, Git history, or a separate P2P Engine source checkout.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-db5bd2205413ebebfde29a7d`).

### PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-432042b763efb79ca58bc262`).

### PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-2cb54e5ebdc1161ce91a6a03`).

### PROP-095 - Project Runtime Contract Update Lifecycle

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-9f420787b6b3fe00db392821`).

### PROP-100 - Project Decision Context Index and Proposal Neighborhood

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-6090667593464748c2106a3b`).

## Constraints And Non-Functional Requirements (`constraints_nfrs`)

### PROP-006 - Multi-Agent Integration Model

P2P Engine can already generate basic agent-facing instructions for generic, Codex, and Claude profiles, but it does not yet manage agent integrations as governed, inspectable, updateable project state. Project initialization should create the supported project-local agent file structures by default, but today there is no explicit registry of installed integrations, generated-file manifests, hashes, drift detection, safe update, safe uninstall, conflict detection, or precise adapter matrix for Cursor, Copilot, Gemini, OpenCode, Codex, Claude, and the generic baseline. A second gap is methodological: generated instructions do not yet force agents to turn weak proposal readiness, failed gates, and owner questions into concrete refinement actions, alternatives, recommendations, candidate edits, and readiness re-checks.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-c1954dabe48c3eac3790d9f3`).

### PROP-055 - Agent Token Budget and Context Discipline

P2P Engine reduces conversational memory by storing governance state in .p2p and Git, but agents can still consume excessive tokens by scanning broad project context, reading full registries, loading many proposal/change files, or explaining artifacts from conversation memory instead of compact deterministic views. This is especially visible in the P2P Engine repository because the project is using P2P to build P2P, but the risk applies to any large P2P workspace used by CLI or MCP agents.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-7820f734b700eb50bb448d39`).

### PROP-084 - Project-Local Runtime Bootstrap And Upgrade Flow

A shared P2P-managed project must declare which P2P Engine runtime version is expected after clone, copy, or archive extraction. The problem is runtime version alignment: a human or agent must be able to determine the compatible runtime range and the recommended runtime version from project-local data, without relying on chat history, local machine state, Git history, or a separate P2P Engine source checkout.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-db5bd2205413ebebfde29a7d`).

### PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-432042b763efb79ca58bc262`).

### PROP-091 - Governance Policy Convergence

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-a595849db855e7d18119a70b`).

### PROP-095 - Project Runtime Contract Update Lifecycle

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-9f420787b6b3fe00db392821`).

### PROP-100 - Project Decision Context Index and Proposal Neighborhood

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-6090667593464748c2106a3b`).

### PROP-101 - Project Readiness Convergence Workflow

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-8e1cd9c06d57e32d85fbe768`).

### PROP-102 - Proposal Decision Revision and Revocation Lifecycle

P2P currently represents a proposal decision primarily as one current outcome.
The decision write path replaces `decision.md` and then replaces the status in
`proposal.md`, without validating the previous lifecycle state or preserving a
queryable sequence of owner decisions.

As a result, an accepted proposal can be rewritten as rejected. The current
workspace then appears to say that the proposal was never adopted, even though
it may already have influenced project definition, Change Sets, Work,
specifications, implementation, publication and later decisions. Git can
recover earlier bytes, but normal validation, retrieval and derived-state
consumers do not use Git history as the proposal decision model.

The model also lacks a precise distinction between rejection before adoption,
withdrawal before decision, revocation after acceptance, replacement,
reinstatement and downstream deprecation. Without that distinction, future
decision-memory consolidation cannot reliably determine which decisions are
active, historical, previously active, replaced or merely deferred.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-43062e3e83542d81e50ad6bf`).

## Acceptance And Validation Strategy (`acceptance_validation`)

### PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-432042b763efb79ca58bc262`).

### PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-2cb54e5ebdc1161ce91a6a03`).

### PROP-095 - Project Runtime Contract Update Lifecycle

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-9f420787b6b3fe00db392821`).

### PROP-099 - Project Output Lifecycle and Retention Policy

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-e59661e429785a0227a72c3a`).

### PROP-100 - Project Decision Context Index and Proposal Neighborhood

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-6090667593464748c2106a3b`).

### PROP-101 - Project Readiness Convergence Workflow

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-8e1cd9c06d57e32d85fbe768`).

### PROP-102 - Proposal Decision Revision and Revocation Lifecycle

P2P currently represents a proposal decision primarily as one current outcome.
The decision write path replaces `decision.md` and then replaces the status in
`proposal.md`, without validating the previous lifecycle state or preserving a
queryable sequence of owner decisions.

As a result, an accepted proposal can be rewritten as rejected. The current
workspace then appears to say that the proposal was never adopted, even though
it may already have influenced project definition, Change Sets, Work,
specifications, implementation, publication and later decisions. Git can
recover earlier bytes, but normal validation, retrieval and derived-state
consumers do not use Git history as the proposal decision model.

The model also lacks a precise distinction between rejection before adoption,
withdrawal before decision, revocation after acceptance, replacement,
reinstatement and downstream deprecation. Without that distinction, future
decision-memory consolidation cannot reliably determine which decisions are
active, historical, previously active, replaced or merely deferred.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-43062e3e83542d81e50ad6bf`).

## Risks Alternatives And Owner Decisions (`risks_alternatives_decisions`)

### PROP-090 - Project Vertical Pack Runtime Hardening And Definition State

PROP-085 introduced pluggable project verticals and the first local implementation delivered an MVP: packaged vertical data, project-local override, active vertical state, CLI/MCP operations, readiness review, proposal-to-vertical coverage, and agent guidance. That MVP proves the direction, but it is not yet a production-grade vertical runtime.

The current implementation still relies on a compact single-file vertical model, does not persist an exact resolved vertical lockfile, does not persist durable project definition state, does not expose a complete JSON contract for agent-guided project construction, and does not yet formalize compatibility between selected verticals, generated rubrics, enabled rubric criteria, section completion, assumptions, and agent updates.

Without a stronger contract, verticals may remain useful templates rather than a reliable operating layer for project definition. Agents can inspect available vertical data, but they cannot durably record what the owner has answered, what remains missing, what is assumed, which section is blocked, or which question should be asked next. Pack updates or local overrides may also change behavior unexpectedly if the project does not pin the resolved pack version and checksum.

This proposal completes and hardens PROP-085 by defining the production-grade contracts for project vertical pack shape, source resolution, lockfiles, project definition state, CLI JSON access, agent-guided progressive interview behavior, validation, security, rubric regeneration, and future Wavekit-compatible installation.

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-432042b763efb79ca58bc262`).

### PROP-091 - Governance Policy Convergence

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-a595849db855e7d18119a70b`).

### PROP-094 - P2P-Governed Software Specification Lifecycle

In software projects, an owner may legitimately ask an agent to produce system specifications before the project is fully defined. If the agent responds by creating a standalone spec file immediately, that file can become the effective source of truth while the P2P project definition remains incomplete or bypassed.

This is a methodological failure, not a file-placement issue alone. The problem is not that specs are unnecessary or always premature. The problem is that the software vertical should guide the definition of the parts that make a useful specification, and those parts should be captured through P2P proposals, decisions, choices, readiness, and Change Sets before a durable spec file is treated as authoritative.

Without that lifecycle, the owner receives a useful-looking document, but future agents, readiness checks, Change Sets, exports, and project status may not be able to explain which governed decisions the spec reflects, which assumptions remain unresolved, or whether the file is only an exploratory draft.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-2cb54e5ebdc1161ce91a6a03`).

### PROP-095 - Project Runtime Contract Update Lifecycle

PROP-084 allows a P2P-managed project to declare the P2P Engine runtime range it trusts, recommend a runtime version to collaborators, expose compatibility diagnostics, and block governed writes when the declared runtime contract cannot be trusted.

The project still lacks an explicit lifecycle for changing that contract after initialization.

An owner may intentionally move a project to another P2P Engine version or runtime line. Editing `.p2p/project/runtime.yml` manually is unsafe because it bypasses validation, can leave generated setup guidance stale, provides no deterministic preview of collaborator impact, and does not define how the PROP-084 governed-write gate may be crossed when the active runtime is outside the old compatible range.

The project-level decision to change the required runtime must remain distinct from installing, upgrading, downgrading, or reconciling the runtime installed on a collaborator's machine.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-9f420787b6b3fe00db392821`).

### PROP-099 - Project Output Lifecycle and Retention Policy

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-e59661e429785a0227a72c3a`).

### PROP-100 - Project Decision Context Index and Proposal Neighborhood

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-6090667593464748c2106a3b`).

### PROP-101 - Project Readiness Convergence Workflow

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-8e1cd9c06d57e32d85fbe768`).

### PROP-102 - Proposal Decision Revision and Revocation Lifecycle

P2P currently represents a proposal decision primarily as one current outcome.
The decision write path replaces `decision.md` and then replaces the status in
`proposal.md`, without validating the previous lifecycle state or preserving a
queryable sequence of owner decisions.

As a result, an accepted proposal can be rewritten as rejected. The current
workspace then appears to say that the proposal was never adopted, even though
it may already have influenced project definition, Change Sets, Work,
specifications, implementation, publication and later decisions. Git can
recover earlier bytes, but normal validation, retrieval and derived-state
consumers do not use Git history as the proposal decision model.

The model also lacks a precise distinction between rejection before adoption,
withdrawal before decision, revocation after acceptance, replacement,
reinstatement and downstream deprecation. Without that distinction, future
decision-memory consolidation cannot reliably determine which decisions are
active, historical, previously active, replaced or merely deferred.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-43062e3e83542d81e50ad6bf`).

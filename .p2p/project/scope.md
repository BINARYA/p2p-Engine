# Project Scope

Derived goals and non-goals grouped by active vertical section. `.p2p/` remains authoritative.

## Assumptions (`assumptions`)

### Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-05e43da4ac2c2c1ef5814c79`).

### Non-Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-5eebb52013173bf13cade72b`).

## Decisions And Open Questions (`decisions`)

### Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-8d10157f85d22bc6b8681a6e`).

### Non-Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-56689f1b4972aec05787e5e9`).

### Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-4144a719c351590589d22d8d`).

### Non-Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-06bc3330b93fc264be61867c`).

### Goals - PROP-102

- Preserve an append-only, queryable history of proposal decision events,
  including rationale, owner authority, date, predecessor and lineage.
- Derive current proposal status and authority deterministically from the valid
  event sequence.
- Define an exhaustive transition matrix with exact retry, invalid transition
  and reconsideration behavior.
- Distinguish initial rejection from withdrawal, revocation, supersession,
  reinstatement and downstream deprecation.
- Make decision mutations owner-controlled, previewed, source-bound,
  stale-safe, atomic, idempotent where appropriate and recoverable.
- Keep current CLI and human-readable status views available as projections
  during a forward compatibility transition.
- Migrate current single-decision artifacts without inventing missing owner
  evidence or erasing legacy values.
- Propagate lifecycle authority consistently to validation, registries,
  project projections, decision context, relations, vertical evidence, Change
  Sets, Work, software specifications, next actions and publication.
- Produce explicit impact and remediation guidance without automatically
  changing dependent owner-controlled lifecycles.
- Establish the stable authority and lineage contract required by future
  thematic decision-memory consolidation.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-ea9c54a4d313f4621a7a4cfd`).

### Non-Goals - PROP-102

- Physically delete accepted, rejected, revoked or superseded proposals.
- Rewrite history so that a previously accepted decision appears never to have
  been active.
- Automatically roll back source code, deployments, completed Change Sets,
  Work or external effects.
- Automatically cancel, supersede, complete or reopen dependent lifecycle
  objects.
- Implement thematic proposal compaction, persistent decision-context caching
  or publication curator refinement.
- Treat `deprecated` as another proposal decision outcome.
- Allow an agent-supplied actor string to establish owner authority.
- Conflate proposal-decision rejection with managed proposal-branch rejection.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-689bd9fd5d8f1065457d75d1`).

## Definition Of Done And Readiness (`definition_of_done`)

### Goals - PROP-085

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-0890d33457c731f900fa1980`).

### Non-Goals - PROP-085

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-b2faeb973b6bc606387ebda1`).

### Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-61872580c197199b86b71508`).

### Non-Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-34bda5b6c0feb6d59e1a879f`).

### Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-4144a719c351590589d22d8d`).

### Non-Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-06bc3330b93fc264be61867c`).

## Expected Artifacts (`artifacts`)

### Goals - PROP-085

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-0890d33457c731f900fa1980`).

### Non-Goals - PROP-085

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-b2faeb973b6bc606387ebda1`).

### Goals - PROP-094

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-9393a021a0bcda9c593f1498`).

### Non-Goals - PROP-094

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-3184616defad3869d5509e39`).

### Goals - PROP-099

- Define a Human Project Publication Pipeline from governed P2P state to complete export, curated Markdown, publication validation, and neutral PDF.
- Keep deterministic export, semantic curation, owner review, publication validation, and PDF rendering as independent and inspectable stages.
- Make the curated document project-first, vertical-aware, traceable, and readable by humans who do not know P2P internals.
- Define an incremental implementation path with a minimal end-to-end slice first and richer CLI orchestration, publication packages, profiles, and themes later.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-7cd53531e3428369bf9c8bf5`).

### Non-Goals - PROP-099

- Do not make generated outputs a new source of truth; .p2p remains governed project memory.
- Do not make the curator decide governance outcomes, readiness, implementation status, or owner choices.
- Do not replace the P2P-native software specification lifecycle, OpenSpec, Spec Kit, or downstream implementation exports.
- Do not require a fully deterministic curator in the first slice; semantic curation may be agentic but must be bounded by contracts and validation.
- Do not introduce multiple themes, branding, visual editors, template marketplaces, sophisticated appendices, automatic permanent replacement of project.md, or full MCP parity in the first slice.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-555ec2cebc9475e511f15446`).

### Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-4144a719c351590589d22d8d`).

### Non-Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-06bc3330b93fc264be61867c`).

### Goals - PROP-102

- Preserve an append-only, queryable history of proposal decision events,
  including rationale, owner authority, date, predecessor and lineage.
- Derive current proposal status and authority deterministically from the valid
  event sequence.
- Define an exhaustive transition matrix with exact retry, invalid transition
  and reconsideration behavior.
- Distinguish initial rejection from withdrawal, revocation, supersession,
  reinstatement and downstream deprecation.
- Make decision mutations owner-controlled, previewed, source-bound,
  stale-safe, atomic, idempotent where appropriate and recoverable.
- Keep current CLI and human-readable status views available as projections
  during a forward compatibility transition.
- Migrate current single-decision artifacts without inventing missing owner
  evidence or erasing legacy values.
- Propagate lifecycle authority consistently to validation, registries,
  project projections, decision context, relations, vertical evidence, Change
  Sets, Work, software specifications, next actions and publication.
- Produce explicit impact and remediation guidance without automatically
  changing dependent owner-controlled lifecycles.
- Establish the stable authority and lineage contract required by future
  thematic decision-memory consolidation.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-ea9c54a4d313f4621a7a4cfd`).

### Non-Goals - PROP-102

- Physically delete accepted, rejected, revoked or superseded proposals.
- Rewrite history so that a previously accepted decision appears never to have
  been active.
- Automatically roll back source code, deployments, completed Change Sets,
  Work or external effects.
- Automatically cancel, supersede, complete or reopen dependent lifecycle
  objects.
- Implement thematic proposal compaction, persistent decision-context caching
  or publication curator refinement.
- Treat `deprecated` as another proposal decision outcome.
- Allow an agent-supplied actor string to establish owner authority.
- Conflate proposal-decision rejection with managed proposal-branch rejection.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-689bd9fd5d8f1065457d75d1`).

## System Objective (`system_objective`)

### Goals - PROP-001

- Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-c91b155ed7198944ce7ada0a`).

### Non-Goals - PROP-001

- No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-1709dd7c5dbc80efc1aead8e`).

### Goals - PROP-085

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-0890d33457c731f900fa1980`).

### Non-Goals - PROP-085

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-b2faeb973b6bc606387ebda1`).

### Goals - PROP-094

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-9393a021a0bcda9c593f1498`).

### Non-Goals - PROP-094

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-3184616defad3869d5509e39`).

## Users And Actors (`users_and_actors`)

### Goals - PROP-006

- Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-f979294a7ad323e9bc0ed276`).

### Non-Goals - PROP-006

- Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-79606489855bd9fd44eec508`).

### Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-8d10157f85d22bc6b8681a6e`).

### Non-Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-56689f1b4972aec05787e5e9`).

## Scope And MVP Boundaries (`mvp_scope`)

### Goals - PROP-001

- Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-c91b155ed7198944ce7ada0a`).

### Non-Goals - PROP-001

- No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-1709dd7c5dbc80efc1aead8e`).

### Goals - PROP-044

- Add a local stdio MCP server inside this repository.
- Expose a minimal read-only tool surface over P2PWorkspace.
- Keep governance and Work mutation commands out of the MCP MVP.
- Avoid web server, cloud deployment, auth, container, direct AI invocation, and mediator logic.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-9724e629de86a04e4c5d9e75`).

### Non-Goals - PROP-044

- Implement MCP over HTTP.
- Expose proposal accept, choice decide, work accept, Git branch, commit, merge, cleanup, or provider actions.
- Implement P2P Mediator or Web.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-cabf27fd1a8d149af423f1c8`).

### Goals - PROP-055

- Define a token-aware operating policy for agents.
- Prefer compact deterministic context views before detailed file reads.
- Make CLI and MCP expose bounded context packets for common agent tasks.
- Prevent agents from scanning unrelated .p2p, source, test, or Git history context when a smaller command output is enough.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-4289913675f0300df16f438b`).

### Non-Goals - PROP-055

- Do not remove detailed proposal/change/registry commands.
- Do not introduce autonomous AI decision-making inside the core.
- Do not optimize runtime performance or rewrite the CLI in Rust as part of this proposal.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-0f8c0e7c1efed124f57c48c6`).

### Goals - PROP-084

- Define .p2p/project/runtime.yml as the authoritative project-local declaration of P2P Engine runtime compatibility.
- Record a compatible runtime range and one recommended P2P Engine runtime version, without release source descriptors, wheel filenames, or digests.
- Generate project-local setup guidance, such as P2P-SETUP.md, so a collaborator who cloned or copied a project can find the required runtime information without knowing P2P internals.
- Provide read-only runtime status diagnostics and validation findings that tell humans and agents whether the installed runtime matches the project contract.
- Block governed writes only when a project declares or requires a runtime contract and the contract is incompatible, invalid, unsupported, or missing under that declared policy.
- Keep ownership boundaries clear: PROP-084 owns runtime contract, setup guidance, diagnostics, validation, and write-gate policy; PROP-078 owns installation mechanics; PROP-080 owns release artifact publication and integrity metadata.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-f0fb08058638fdeb3c110cad`).

### Non-Goals - PROP-084

- Do not make a mandatory bootstrap script central to the proposal.
- Do not add an install, reconcile, upgrade, downgrade, replacement, source-switch, virtualenv, package-resolution, or download manager in this scope.
- Do not put release tags, wheel filenames, SHA-256 digests, source descriptors, arbitrary URLs, arbitrary repositories, PyPI resolution, mirrors, source checkout installs, editable installs, or offline wheel behavior in the required runtime contract.
- Do not block legacy projects solely because they lack runtime.yml; report legacy_undeclared with guidance instead.
- Do not add broad command blocking across all commands; enforcement is limited to governed writes when a declared or required contract cannot be trusted.
- Do not make Git required for P2P Core or introduce separate runtime-contract formats for standalone, local Git, and remote Git contexts.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-e74f4802c8b5a646d0b3eea5`).

### Goals - PROP-085

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-0890d33457c731f900fa1980`).

### Non-Goals - PROP-085

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-b2faeb973b6bc606387ebda1`).

### Goals - PROP-094

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-9393a021a0bcda9c593f1498`).

### Non-Goals - PROP-094

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-3184616defad3869d5509e39`).

### Goals - PROP-099

- Define a Human Project Publication Pipeline from governed P2P state to complete export, curated Markdown, publication validation, and neutral PDF.
- Keep deterministic export, semantic curation, owner review, publication validation, and PDF rendering as independent and inspectable stages.
- Make the curated document project-first, vertical-aware, traceable, and readable by humans who do not know P2P internals.
- Define an incremental implementation path with a minimal end-to-end slice first and richer CLI orchestration, publication packages, profiles, and themes later.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-7cd53531e3428369bf9c8bf5`).

### Non-Goals - PROP-099

- Do not make generated outputs a new source of truth; .p2p remains governed project memory.
- Do not make the curator decide governance outcomes, readiness, implementation status, or owner choices.
- Do not replace the P2P-native software specification lifecycle, OpenSpec, Spec Kit, or downstream implementation exports.
- Do not require a fully deterministic curator in the first slice; semantic curation may be agentic but must be bounded by contracts and validation.
- Do not introduce multiple themes, branding, visual editors, template marketplaces, sophisticated appendices, automatic permanent replacement of project.md, or full MCP parity in the first slice.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-555ec2cebc9475e511f15446`).

## Workflows And Use Cases (`workflows_use_cases`)

### Goals - PROP-001

- Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-c91b155ed7198944ce7ada0a`).

### Non-Goals - PROP-001

- No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.

Source: `.p2p/proposals/PROP-001-cli-foundation/proposal.md` (`VME-1709dd7c5dbc80efc1aead8e`).

### Goals - PROP-006

- Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-f979294a7ad323e9bc0ed276`).

### Non-Goals - PROP-006

- Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-79606489855bd9fd44eec508`).

### Goals - PROP-044

- Add a local stdio MCP server inside this repository.
- Expose a minimal read-only tool surface over P2PWorkspace.
- Keep governance and Work mutation commands out of the MCP MVP.
- Avoid web server, cloud deployment, auth, container, direct AI invocation, and mediator logic.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-9724e629de86a04e4c5d9e75`).

### Non-Goals - PROP-044

- Implement MCP over HTTP.
- Expose proposal accept, choice decide, work accept, Git branch, commit, merge, cleanup, or provider actions.
- Implement P2P Mediator or Web.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-cabf27fd1a8d149af423f1c8`).

### Goals - PROP-055

- Define a token-aware operating policy for agents.
- Prefer compact deterministic context views before detailed file reads.
- Make CLI and MCP expose bounded context packets for common agent tasks.
- Prevent agents from scanning unrelated .p2p, source, test, or Git history context when a smaller command output is enough.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-4289913675f0300df16f438b`).

### Non-Goals - PROP-055

- Do not remove detailed proposal/change/registry commands.
- Do not introduce autonomous AI decision-making inside the core.
- Do not optimize runtime performance or rewrite the CLI in Rust as part of this proposal.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-0f8c0e7c1efed124f57c48c6`).

### Goals - PROP-084

- Define .p2p/project/runtime.yml as the authoritative project-local declaration of P2P Engine runtime compatibility.
- Record a compatible runtime range and one recommended P2P Engine runtime version, without release source descriptors, wheel filenames, or digests.
- Generate project-local setup guidance, such as P2P-SETUP.md, so a collaborator who cloned or copied a project can find the required runtime information without knowing P2P internals.
- Provide read-only runtime status diagnostics and validation findings that tell humans and agents whether the installed runtime matches the project contract.
- Block governed writes only when a project declares or requires a runtime contract and the contract is incompatible, invalid, unsupported, or missing under that declared policy.
- Keep ownership boundaries clear: PROP-084 owns runtime contract, setup guidance, diagnostics, validation, and write-gate policy; PROP-078 owns installation mechanics; PROP-080 owns release artifact publication and integrity metadata.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-f0fb08058638fdeb3c110cad`).

### Non-Goals - PROP-084

- Do not make a mandatory bootstrap script central to the proposal.
- Do not add an install, reconcile, upgrade, downgrade, replacement, source-switch, virtualenv, package-resolution, or download manager in this scope.
- Do not put release tags, wheel filenames, SHA-256 digests, source descriptors, arbitrary URLs, arbitrary repositories, PyPI resolution, mirrors, source checkout installs, editable installs, or offline wheel behavior in the required runtime contract.
- Do not block legacy projects solely because they lack runtime.yml; report legacy_undeclared with guidance instead.
- Do not add broad command blocking across all commands; enforcement is limited to governed writes when a declared or required contract cannot be trusted.
- Do not make Git required for P2P Core or introduce separate runtime-contract formats for standalone, local Git, and remote Git contexts.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-e74f4802c8b5a646d0b3eea5`).

### Goals - PROP-085

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-0890d33457c731f900fa1980`).

### Non-Goals - PROP-085

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-b2faeb973b6bc606387ebda1`).

### Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-61872580c197199b86b71508`).

### Non-Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-34bda5b6c0feb6d59e1a879f`).

### Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-8d10157f85d22bc6b8681a6e`).

### Non-Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-56689f1b4972aec05787e5e9`).

### Goals - PROP-094

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-9393a021a0bcda9c593f1498`).

### Non-Goals - PROP-094

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-3184616defad3869d5509e39`).

### Goals - PROP-095

- Give the owner an explicit, preview-first operation for changing the project runtime contract.
- Expose separate read-only and mutating command surfaces.
- Update `.p2p/project/runtime.yml` and managed `P2P-SETUP.md` as one coordinated policy change.
- Classify upgrade, downgrade, range widening, range tightening, runtime-line change, recommended-only change, no-op, and active-runtime exclusion.
- Preserve PROP-084 write-gate safety while allowing a narrow runtime-contract update exception for valid incompatible old contracts.
- Allow agents and non-owner collaborators to produce read-only previews for owner review.
- Require owner authority, explicit confirmation, stale-preview protection, and structured reasons where the impact is material.
- Provide deterministic human-readable and JSON output for humans, agents, CI, and scripts.
- Keep runtime installation, upgrade, downgrade, package resolution, remote lookup, and release availability enforcement out of scope.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-4fb25428255fdc76d8904c04`).

### Non-Goals - PROP-095

- Do not install, upgrade, downgrade, select, or reconcile a local P2P Engine runtime.
- Do not query GitHub, download release metadata, resolve wheels, or verify installability through the network.
- Do not make release metadata from PROP-080 a blocking dependency for runtime contract updates.
- Do not overwrite, adopt, merge, rename, back up, or replace unmanaged `P2P-SETUP.md` files.
- Do not implement contract repair, schema migration, contract recovery, or legacy adoption workflows.
- Do not add MCP mutation in the first implementation.
- Do not create Git commits, branches, pushes, pull requests, merges, or provider handoffs.
- Do not perform unrelated governed mutations after a new contract makes the active runtime incompatible.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-063c6c0a732774a2e120d847`).

### Goals - PROP-099

- Define a Human Project Publication Pipeline from governed P2P state to complete export, curated Markdown, publication validation, and neutral PDF.
- Keep deterministic export, semantic curation, owner review, publication validation, and PDF rendering as independent and inspectable stages.
- Make the curated document project-first, vertical-aware, traceable, and readable by humans who do not know P2P internals.
- Define an incremental implementation path with a minimal end-to-end slice first and richer CLI orchestration, publication packages, profiles, and themes later.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-7cd53531e3428369bf9c8bf5`).

### Non-Goals - PROP-099

- Do not make generated outputs a new source of truth; .p2p remains governed project memory.
- Do not make the curator decide governance outcomes, readiness, implementation status, or owner choices.
- Do not replace the P2P-native software specification lifecycle, OpenSpec, Spec Kit, or downstream implementation exports.
- Do not require a fully deterministic curator in the first slice; semantic curation may be agentic but must be bounded by contracts and validation.
- Do not introduce multiple themes, branding, visual editors, template marketplaces, sophisticated appendices, automatic permanent replacement of project.md, or full MCP parity in the first slice.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-555ec2cebc9475e511f15446`).

### Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-05e43da4ac2c2c1ef5814c79`).

### Non-Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-5eebb52013173bf13cade72b`).

### Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-4144a719c351590589d22d8d`).

### Non-Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-06bc3330b93fc264be61867c`).

## Domain Concepts And Data Model (`data_model`)

### Goals - PROP-006

- Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-f979294a7ad323e9bc0ed276`).

### Non-Goals - PROP-006

- Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-79606489855bd9fd44eec508`).

### Goals - PROP-084

- Define .p2p/project/runtime.yml as the authoritative project-local declaration of P2P Engine runtime compatibility.
- Record a compatible runtime range and one recommended P2P Engine runtime version, without release source descriptors, wheel filenames, or digests.
- Generate project-local setup guidance, such as P2P-SETUP.md, so a collaborator who cloned or copied a project can find the required runtime information without knowing P2P internals.
- Provide read-only runtime status diagnostics and validation findings that tell humans and agents whether the installed runtime matches the project contract.
- Block governed writes only when a project declares or requires a runtime contract and the contract is incompatible, invalid, unsupported, or missing under that declared policy.
- Keep ownership boundaries clear: PROP-084 owns runtime contract, setup guidance, diagnostics, validation, and write-gate policy; PROP-078 owns installation mechanics; PROP-080 owns release artifact publication and integrity metadata.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-f0fb08058638fdeb3c110cad`).

### Non-Goals - PROP-084

- Do not make a mandatory bootstrap script central to the proposal.
- Do not add an install, reconcile, upgrade, downgrade, replacement, source-switch, virtualenv, package-resolution, or download manager in this scope.
- Do not put release tags, wheel filenames, SHA-256 digests, source descriptors, arbitrary URLs, arbitrary repositories, PyPI resolution, mirrors, source checkout installs, editable installs, or offline wheel behavior in the required runtime contract.
- Do not block legacy projects solely because they lack runtime.yml; report legacy_undeclared with guidance instead.
- Do not add broad command blocking across all commands; enforcement is limited to governed writes when a declared or required contract cannot be trusted.
- Do not make Git required for P2P Core or introduce separate runtime-contract formats for standalone, local Git, and remote Git contexts.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-e74f4802c8b5a646d0b3eea5`).

### Goals - PROP-085

- Define a generic vertical package model for project init and project review, including sections, detail packs, rubric criteria, maturity levels, questions, artifacts, examples, profiles, and optional modules.
- Teach agents, through generated/local skills, to propose project capisaldi and focused refinement questions when the current project vertical or readiness information is weak, missing, or too generic.
- Support core defaults, external/plugin registries, and project-local custom verticals without requiring P2P Engine to hardcode every possible domain.
- Allow the same flow to run during interactive project init and later through an explicit project readiness review command.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-0890d33457c731f900fa1980`).

### Non-Goals - PROP-085

- Do not ship a large catalog of superficial verticals in the engine.
- Do not require all verticals to be known at build time.
- Do not replace owner governance: the agent proposes verticals, capisaldi, rubric extensions, and questions, but the owner decides.
- Do not make regulated verticals such as medical or legal authoritative without explicit caution, provenance, and owner responsibility.

Source: `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration/proposal.md` (`VME-b2faeb973b6bc606387ebda1`).

### Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-61872580c197199b86b71508`).

### Non-Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-34bda5b6c0feb6d59e1a879f`).

### Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-8d10157f85d22bc6b8681a6e`).

### Non-Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-56689f1b4972aec05787e5e9`).

### Goals - PROP-094

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-9393a021a0bcda9c593f1498`).

### Non-Goals - PROP-094

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-3184616defad3869d5509e39`).

### Goals - PROP-095

- Give the owner an explicit, preview-first operation for changing the project runtime contract.
- Expose separate read-only and mutating command surfaces.
- Update `.p2p/project/runtime.yml` and managed `P2P-SETUP.md` as one coordinated policy change.
- Classify upgrade, downgrade, range widening, range tightening, runtime-line change, recommended-only change, no-op, and active-runtime exclusion.
- Preserve PROP-084 write-gate safety while allowing a narrow runtime-contract update exception for valid incompatible old contracts.
- Allow agents and non-owner collaborators to produce read-only previews for owner review.
- Require owner authority, explicit confirmation, stale-preview protection, and structured reasons where the impact is material.
- Provide deterministic human-readable and JSON output for humans, agents, CI, and scripts.
- Keep runtime installation, upgrade, downgrade, package resolution, remote lookup, and release availability enforcement out of scope.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-4fb25428255fdc76d8904c04`).

### Non-Goals - PROP-095

- Do not install, upgrade, downgrade, select, or reconcile a local P2P Engine runtime.
- Do not query GitHub, download release metadata, resolve wheels, or verify installability through the network.
- Do not make release metadata from PROP-080 a blocking dependency for runtime contract updates.
- Do not overwrite, adopt, merge, rename, back up, or replace unmanaged `P2P-SETUP.md` files.
- Do not implement contract repair, schema migration, contract recovery, or legacy adoption workflows.
- Do not add MCP mutation in the first implementation.
- Do not create Git commits, branches, pushes, pull requests, merges, or provider handoffs.
- Do not perform unrelated governed mutations after a new contract makes the active runtime incompatible.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-063c6c0a732774a2e120d847`).

### Goals - PROP-099

- Define a Human Project Publication Pipeline from governed P2P state to complete export, curated Markdown, publication validation, and neutral PDF.
- Keep deterministic export, semantic curation, owner review, publication validation, and PDF rendering as independent and inspectable stages.
- Make the curated document project-first, vertical-aware, traceable, and readable by humans who do not know P2P internals.
- Define an incremental implementation path with a minimal end-to-end slice first and richer CLI orchestration, publication packages, profiles, and themes later.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-7cd53531e3428369bf9c8bf5`).

### Non-Goals - PROP-099

- Do not make generated outputs a new source of truth; .p2p remains governed project memory.
- Do not make the curator decide governance outcomes, readiness, implementation status, or owner choices.
- Do not replace the P2P-native software specification lifecycle, OpenSpec, Spec Kit, or downstream implementation exports.
- Do not require a fully deterministic curator in the first slice; semantic curation may be agentic but must be bounded by contracts and validation.
- Do not introduce multiple themes, branding, visual editors, template marketplaces, sophisticated appendices, automatic permanent replacement of project.md, or full MCP parity in the first slice.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-555ec2cebc9475e511f15446`).

### Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-05e43da4ac2c2c1ef5814c79`).

### Non-Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-5eebb52013173bf13cade72b`).

### Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-4144a719c351590589d22d8d`).

### Non-Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-06bc3330b93fc264be61867c`).

### Goals - PROP-102

- Preserve an append-only, queryable history of proposal decision events,
  including rationale, owner authority, date, predecessor and lineage.
- Derive current proposal status and authority deterministically from the valid
  event sequence.
- Define an exhaustive transition matrix with exact retry, invalid transition
  and reconsideration behavior.
- Distinguish initial rejection from withdrawal, revocation, supersession,
  reinstatement and downstream deprecation.
- Make decision mutations owner-controlled, previewed, source-bound,
  stale-safe, atomic, idempotent where appropriate and recoverable.
- Keep current CLI and human-readable status views available as projections
  during a forward compatibility transition.
- Migrate current single-decision artifacts without inventing missing owner
  evidence or erasing legacy values.
- Propagate lifecycle authority consistently to validation, registries,
  project projections, decision context, relations, vertical evidence, Change
  Sets, Work, software specifications, next actions and publication.
- Produce explicit impact and remediation guidance without automatically
  changing dependent owner-controlled lifecycles.
- Establish the stable authority and lineage contract required by future
  thematic decision-memory consolidation.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-ea9c54a4d313f4621a7a4cfd`).

### Non-Goals - PROP-102

- Physically delete accepted, rejected, revoked or superseded proposals.
- Rewrite history so that a previously accepted decision appears never to have
  been active.
- Automatically roll back source code, deployments, completed Change Sets,
  Work or external effects.
- Automatically cancel, supersede, complete or reopen dependent lifecycle
  objects.
- Implement thematic proposal compaction, persistent decision-context caching
  or publication curator refinement.
- Treat `deprecated` as another proposal decision outcome.
- Allow an agent-supplied actor string to establish owner authority.
- Conflate proposal-decision rejection with managed proposal-branch rejection.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-689bd9fd5d8f1065457d75d1`).

## Integrations And Dependencies (`integrations_dependencies`)

### Goals - PROP-006

- Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-f979294a7ad323e9bc0ed276`).

### Non-Goals - PROP-006

- Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-79606489855bd9fd44eec508`).

### Goals - PROP-044

- Add a local stdio MCP server inside this repository.
- Expose a minimal read-only tool surface over P2PWorkspace.
- Keep governance and Work mutation commands out of the MCP MVP.
- Avoid web server, cloud deployment, auth, container, direct AI invocation, and mediator logic.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-9724e629de86a04e4c5d9e75`).

### Non-Goals - PROP-044

- Implement MCP over HTTP.
- Expose proposal accept, choice decide, work accept, Git branch, commit, merge, cleanup, or provider actions.
- Implement P2P Mediator or Web.

Source: `.p2p/proposals/PROP-044-p2p-mcp-server-mvp/proposal.md` (`VME-cabf27fd1a8d149af423f1c8`).

### Goals - PROP-084

- Define .p2p/project/runtime.yml as the authoritative project-local declaration of P2P Engine runtime compatibility.
- Record a compatible runtime range and one recommended P2P Engine runtime version, without release source descriptors, wheel filenames, or digests.
- Generate project-local setup guidance, such as P2P-SETUP.md, so a collaborator who cloned or copied a project can find the required runtime information without knowing P2P internals.
- Provide read-only runtime status diagnostics and validation findings that tell humans and agents whether the installed runtime matches the project contract.
- Block governed writes only when a project declares or requires a runtime contract and the contract is incompatible, invalid, unsupported, or missing under that declared policy.
- Keep ownership boundaries clear: PROP-084 owns runtime contract, setup guidance, diagnostics, validation, and write-gate policy; PROP-078 owns installation mechanics; PROP-080 owns release artifact publication and integrity metadata.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-f0fb08058638fdeb3c110cad`).

### Non-Goals - PROP-084

- Do not make a mandatory bootstrap script central to the proposal.
- Do not add an install, reconcile, upgrade, downgrade, replacement, source-switch, virtualenv, package-resolution, or download manager in this scope.
- Do not put release tags, wheel filenames, SHA-256 digests, source descriptors, arbitrary URLs, arbitrary repositories, PyPI resolution, mirrors, source checkout installs, editable installs, or offline wheel behavior in the required runtime contract.
- Do not block legacy projects solely because they lack runtime.yml; report legacy_undeclared with guidance instead.
- Do not add broad command blocking across all commands; enforcement is limited to governed writes when a declared or required contract cannot be trusted.
- Do not make Git required for P2P Core or introduce separate runtime-contract formats for standalone, local Git, and remote Git contexts.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-e74f4802c8b5a646d0b3eea5`).

### Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-61872580c197199b86b71508`).

### Non-Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-34bda5b6c0feb6d59e1a879f`).

### Goals - PROP-094

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-9393a021a0bcda9c593f1498`).

### Non-Goals - PROP-094

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-3184616defad3869d5509e39`).

### Goals - PROP-095

- Give the owner an explicit, preview-first operation for changing the project runtime contract.
- Expose separate read-only and mutating command surfaces.
- Update `.p2p/project/runtime.yml` and managed `P2P-SETUP.md` as one coordinated policy change.
- Classify upgrade, downgrade, range widening, range tightening, runtime-line change, recommended-only change, no-op, and active-runtime exclusion.
- Preserve PROP-084 write-gate safety while allowing a narrow runtime-contract update exception for valid incompatible old contracts.
- Allow agents and non-owner collaborators to produce read-only previews for owner review.
- Require owner authority, explicit confirmation, stale-preview protection, and structured reasons where the impact is material.
- Provide deterministic human-readable and JSON output for humans, agents, CI, and scripts.
- Keep runtime installation, upgrade, downgrade, package resolution, remote lookup, and release availability enforcement out of scope.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-4fb25428255fdc76d8904c04`).

### Non-Goals - PROP-095

- Do not install, upgrade, downgrade, select, or reconcile a local P2P Engine runtime.
- Do not query GitHub, download release metadata, resolve wheels, or verify installability through the network.
- Do not make release metadata from PROP-080 a blocking dependency for runtime contract updates.
- Do not overwrite, adopt, merge, rename, back up, or replace unmanaged `P2P-SETUP.md` files.
- Do not implement contract repair, schema migration, contract recovery, or legacy adoption workflows.
- Do not add MCP mutation in the first implementation.
- Do not create Git commits, branches, pushes, pull requests, merges, or provider handoffs.
- Do not perform unrelated governed mutations after a new contract makes the active runtime incompatible.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-063c6c0a732774a2e120d847`).

### Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-05e43da4ac2c2c1ef5814c79`).

### Non-Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-5eebb52013173bf13cade72b`).

## Constraints And Non-Functional Requirements (`constraints_nfrs`)

### Goals - PROP-006

- Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-f979294a7ad323e9bc0ed276`).

### Non-Goals - PROP-006

- Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.

Source: `.p2p/proposals/PROP-006-multi-agent-integration-model/proposal.md` (`VME-79606489855bd9fd44eec508`).

### Goals - PROP-055

- Define a token-aware operating policy for agents.
- Prefer compact deterministic context views before detailed file reads.
- Make CLI and MCP expose bounded context packets for common agent tasks.
- Prevent agents from scanning unrelated .p2p, source, test, or Git history context when a smaller command output is enough.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-4289913675f0300df16f438b`).

### Non-Goals - PROP-055

- Do not remove detailed proposal/change/registry commands.
- Do not introduce autonomous AI decision-making inside the core.
- Do not optimize runtime performance or rewrite the CLI in Rust as part of this proposal.

Source: `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline/proposal.md` (`VME-0f8c0e7c1efed124f57c48c6`).

### Goals - PROP-084

- Define .p2p/project/runtime.yml as the authoritative project-local declaration of P2P Engine runtime compatibility.
- Record a compatible runtime range and one recommended P2P Engine runtime version, without release source descriptors, wheel filenames, or digests.
- Generate project-local setup guidance, such as P2P-SETUP.md, so a collaborator who cloned or copied a project can find the required runtime information without knowing P2P internals.
- Provide read-only runtime status diagnostics and validation findings that tell humans and agents whether the installed runtime matches the project contract.
- Block governed writes only when a project declares or requires a runtime contract and the contract is incompatible, invalid, unsupported, or missing under that declared policy.
- Keep ownership boundaries clear: PROP-084 owns runtime contract, setup guidance, diagnostics, validation, and write-gate policy; PROP-078 owns installation mechanics; PROP-080 owns release artifact publication and integrity metadata.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-f0fb08058638fdeb3c110cad`).

### Non-Goals - PROP-084

- Do not make a mandatory bootstrap script central to the proposal.
- Do not add an install, reconcile, upgrade, downgrade, replacement, source-switch, virtualenv, package-resolution, or download manager in this scope.
- Do not put release tags, wheel filenames, SHA-256 digests, source descriptors, arbitrary URLs, arbitrary repositories, PyPI resolution, mirrors, source checkout installs, editable installs, or offline wheel behavior in the required runtime contract.
- Do not block legacy projects solely because they lack runtime.yml; report legacy_undeclared with guidance instead.
- Do not add broad command blocking across all commands; enforcement is limited to governed writes when a declared or required contract cannot be trusted.
- Do not make Git required for P2P Core or introduce separate runtime-contract formats for standalone, local Git, and remote Git contexts.

Source: `.p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow/proposal.md` (`VME-e74f4802c8b5a646d0b3eea5`).

### Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-61872580c197199b86b71508`).

### Non-Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-34bda5b6c0feb6d59e1a879f`).

### Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-8d10157f85d22bc6b8681a6e`).

### Non-Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-56689f1b4972aec05787e5e9`).

### Goals - PROP-095

- Give the owner an explicit, preview-first operation for changing the project runtime contract.
- Expose separate read-only and mutating command surfaces.
- Update `.p2p/project/runtime.yml` and managed `P2P-SETUP.md` as one coordinated policy change.
- Classify upgrade, downgrade, range widening, range tightening, runtime-line change, recommended-only change, no-op, and active-runtime exclusion.
- Preserve PROP-084 write-gate safety while allowing a narrow runtime-contract update exception for valid incompatible old contracts.
- Allow agents and non-owner collaborators to produce read-only previews for owner review.
- Require owner authority, explicit confirmation, stale-preview protection, and structured reasons where the impact is material.
- Provide deterministic human-readable and JSON output for humans, agents, CI, and scripts.
- Keep runtime installation, upgrade, downgrade, package resolution, remote lookup, and release availability enforcement out of scope.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-4fb25428255fdc76d8904c04`).

### Non-Goals - PROP-095

- Do not install, upgrade, downgrade, select, or reconcile a local P2P Engine runtime.
- Do not query GitHub, download release metadata, resolve wheels, or verify installability through the network.
- Do not make release metadata from PROP-080 a blocking dependency for runtime contract updates.
- Do not overwrite, adopt, merge, rename, back up, or replace unmanaged `P2P-SETUP.md` files.
- Do not implement contract repair, schema migration, contract recovery, or legacy adoption workflows.
- Do not add MCP mutation in the first implementation.
- Do not create Git commits, branches, pushes, pull requests, merges, or provider handoffs.
- Do not perform unrelated governed mutations after a new contract makes the active runtime incompatible.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-063c6c0a732774a2e120d847`).

### Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-05e43da4ac2c2c1ef5814c79`).

### Non-Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-5eebb52013173bf13cade72b`).

### Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-4144a719c351590589d22d8d`).

### Non-Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-06bc3330b93fc264be61867c`).

### Goals - PROP-102

- Preserve an append-only, queryable history of proposal decision events,
  including rationale, owner authority, date, predecessor and lineage.
- Derive current proposal status and authority deterministically from the valid
  event sequence.
- Define an exhaustive transition matrix with exact retry, invalid transition
  and reconsideration behavior.
- Distinguish initial rejection from withdrawal, revocation, supersession,
  reinstatement and downstream deprecation.
- Make decision mutations owner-controlled, previewed, source-bound,
  stale-safe, atomic, idempotent where appropriate and recoverable.
- Keep current CLI and human-readable status views available as projections
  during a forward compatibility transition.
- Migrate current single-decision artifacts without inventing missing owner
  evidence or erasing legacy values.
- Propagate lifecycle authority consistently to validation, registries,
  project projections, decision context, relations, vertical evidence, Change
  Sets, Work, software specifications, next actions and publication.
- Produce explicit impact and remediation guidance without automatically
  changing dependent owner-controlled lifecycles.
- Establish the stable authority and lineage contract required by future
  thematic decision-memory consolidation.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-ea9c54a4d313f4621a7a4cfd`).

### Non-Goals - PROP-102

- Physically delete accepted, rejected, revoked or superseded proposals.
- Rewrite history so that a previously accepted decision appears never to have
  been active.
- Automatically roll back source code, deployments, completed Change Sets,
  Work or external effects.
- Automatically cancel, supersede, complete or reopen dependent lifecycle
  objects.
- Implement thematic proposal compaction, persistent decision-context caching
  or publication curator refinement.
- Treat `deprecated` as another proposal decision outcome.
- Allow an agent-supplied actor string to establish owner authority.
- Conflate proposal-decision rejection with managed proposal-branch rejection.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-689bd9fd5d8f1065457d75d1`).

## Acceptance And Validation Strategy (`acceptance_validation`)

### Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-61872580c197199b86b71508`).

### Non-Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-34bda5b6c0feb6d59e1a879f`).

### Goals - PROP-094

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-9393a021a0bcda9c593f1498`).

### Non-Goals - PROP-094

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-3184616defad3869d5509e39`).

### Goals - PROP-095

- Give the owner an explicit, preview-first operation for changing the project runtime contract.
- Expose separate read-only and mutating command surfaces.
- Update `.p2p/project/runtime.yml` and managed `P2P-SETUP.md` as one coordinated policy change.
- Classify upgrade, downgrade, range widening, range tightening, runtime-line change, recommended-only change, no-op, and active-runtime exclusion.
- Preserve PROP-084 write-gate safety while allowing a narrow runtime-contract update exception for valid incompatible old contracts.
- Allow agents and non-owner collaborators to produce read-only previews for owner review.
- Require owner authority, explicit confirmation, stale-preview protection, and structured reasons where the impact is material.
- Provide deterministic human-readable and JSON output for humans, agents, CI, and scripts.
- Keep runtime installation, upgrade, downgrade, package resolution, remote lookup, and release availability enforcement out of scope.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-4fb25428255fdc76d8904c04`).

### Non-Goals - PROP-095

- Do not install, upgrade, downgrade, select, or reconcile a local P2P Engine runtime.
- Do not query GitHub, download release metadata, resolve wheels, or verify installability through the network.
- Do not make release metadata from PROP-080 a blocking dependency for runtime contract updates.
- Do not overwrite, adopt, merge, rename, back up, or replace unmanaged `P2P-SETUP.md` files.
- Do not implement contract repair, schema migration, contract recovery, or legacy adoption workflows.
- Do not add MCP mutation in the first implementation.
- Do not create Git commits, branches, pushes, pull requests, merges, or provider handoffs.
- Do not perform unrelated governed mutations after a new contract makes the active runtime incompatible.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-063c6c0a732774a2e120d847`).

### Goals - PROP-099

- Define a Human Project Publication Pipeline from governed P2P state to complete export, curated Markdown, publication validation, and neutral PDF.
- Keep deterministic export, semantic curation, owner review, publication validation, and PDF rendering as independent and inspectable stages.
- Make the curated document project-first, vertical-aware, traceable, and readable by humans who do not know P2P internals.
- Define an incremental implementation path with a minimal end-to-end slice first and richer CLI orchestration, publication packages, profiles, and themes later.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-7cd53531e3428369bf9c8bf5`).

### Non-Goals - PROP-099

- Do not make generated outputs a new source of truth; .p2p remains governed project memory.
- Do not make the curator decide governance outcomes, readiness, implementation status, or owner choices.
- Do not replace the P2P-native software specification lifecycle, OpenSpec, Spec Kit, or downstream implementation exports.
- Do not require a fully deterministic curator in the first slice; semantic curation may be agentic but must be bounded by contracts and validation.
- Do not introduce multiple themes, branding, visual editors, template marketplaces, sophisticated appendices, automatic permanent replacement of project.md, or full MCP parity in the first slice.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-555ec2cebc9475e511f15446`).

### Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-05e43da4ac2c2c1ef5814c79`).

### Non-Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-5eebb52013173bf13cade72b`).

### Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-4144a719c351590589d22d8d`).

### Non-Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-06bc3330b93fc264be61867c`).

### Goals - PROP-102

- Preserve an append-only, queryable history of proposal decision events,
  including rationale, owner authority, date, predecessor and lineage.
- Derive current proposal status and authority deterministically from the valid
  event sequence.
- Define an exhaustive transition matrix with exact retry, invalid transition
  and reconsideration behavior.
- Distinguish initial rejection from withdrawal, revocation, supersession,
  reinstatement and downstream deprecation.
- Make decision mutations owner-controlled, previewed, source-bound,
  stale-safe, atomic, idempotent where appropriate and recoverable.
- Keep current CLI and human-readable status views available as projections
  during a forward compatibility transition.
- Migrate current single-decision artifacts without inventing missing owner
  evidence or erasing legacy values.
- Propagate lifecycle authority consistently to validation, registries,
  project projections, decision context, relations, vertical evidence, Change
  Sets, Work, software specifications, next actions and publication.
- Produce explicit impact and remediation guidance without automatically
  changing dependent owner-controlled lifecycles.
- Establish the stable authority and lineage contract required by future
  thematic decision-memory consolidation.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-ea9c54a4d313f4621a7a4cfd`).

### Non-Goals - PROP-102

- Physically delete accepted, rejected, revoked or superseded proposals.
- Rewrite history so that a previously accepted decision appears never to have
  been active.
- Automatically roll back source code, deployments, completed Change Sets,
  Work or external effects.
- Automatically cancel, supersede, complete or reopen dependent lifecycle
  objects.
- Implement thematic proposal compaction, persistent decision-context caching
  or publication curator refinement.
- Treat `deprecated` as another proposal decision outcome.
- Allow an agent-supplied actor string to establish owner authority.
- Conflate proposal-decision rejection with managed proposal-branch rejection.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-689bd9fd5d8f1065457d75d1`).

## Risks Alternatives And Owner Decisions (`risks_alternatives_decisions`)

### Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-61872580c197199b86b71508`).

### Non-Goals - PROP-090

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

Source: `.p2p/proposals/PROP-090-project-vertical-pack-runtime-hardening-and-definition-state/proposal.md` (`VME-34bda5b6c0feb6d59e1a879f`).

### Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-8d10157f85d22bc6b8681a6e`).

### Non-Goals - PROP-091

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

Source: `.p2p/proposals/PROP-091-governance-policy-convergence/proposal.md` (`VME-56689f1b4972aec05787e5e9`).

### Goals - PROP-094

- Treat the need for specs as a first-class part of the software vertical.
- Make specification content emerge from P2P-governed project definition, one or more proposals, decisions, and Change Sets.
- Teach generated agent instructions to route "make specs" requests through the software vertical and P2P state instead of creating an independent durable file by default.
- Clarify when a spec request should produce chat discussion, project-definition questions, proposal work, choices, a Change Set, a P2P-native spec, a generated export, or stable documentation.
- Allow early exploratory spec outlines, but prevent them from becoming primary project memory unless they are captured or exported through P2P.
- Keep user intent respected: if the owner explicitly requests a concrete file outside the P2P flow, the agent may create it after previewing the write and explaining its relationship to P2P state.
- Reuse existing P2P primitives instead of inventing a parallel specification workflow.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-9393a021a0bcda9c593f1498`).

### Non-Goals - PROP-094

- Do not prohibit users from explicitly requesting a concrete spec file.
- Do not replace existing P2P proposal, Change Set, spec refresh, or export primitives.
- Do not implement external artifact registration unless explicitly accepted in a separate proposal.
- Do not require all non-software projects to follow a software-spec lifecycle.
- Do not require agents to complete every possible project-definition question before drafting any useful provisional outline.
- Do not make generated specs authoritative when they contain unresolved questions, inferred details, or unaccepted alternatives.

Source: `.p2p/proposals/PROP-094-p2p-governed-software-specification-lifecycle/proposal.md` (`VME-3184616defad3869d5509e39`).

### Goals - PROP-095

- Give the owner an explicit, preview-first operation for changing the project runtime contract.
- Expose separate read-only and mutating command surfaces.
- Update `.p2p/project/runtime.yml` and managed `P2P-SETUP.md` as one coordinated policy change.
- Classify upgrade, downgrade, range widening, range tightening, runtime-line change, recommended-only change, no-op, and active-runtime exclusion.
- Preserve PROP-084 write-gate safety while allowing a narrow runtime-contract update exception for valid incompatible old contracts.
- Allow agents and non-owner collaborators to produce read-only previews for owner review.
- Require owner authority, explicit confirmation, stale-preview protection, and structured reasons where the impact is material.
- Provide deterministic human-readable and JSON output for humans, agents, CI, and scripts.
- Keep runtime installation, upgrade, downgrade, package resolution, remote lookup, and release availability enforcement out of scope.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-4fb25428255fdc76d8904c04`).

### Non-Goals - PROP-095

- Do not install, upgrade, downgrade, select, or reconcile a local P2P Engine runtime.
- Do not query GitHub, download release metadata, resolve wheels, or verify installability through the network.
- Do not make release metadata from PROP-080 a blocking dependency for runtime contract updates.
- Do not overwrite, adopt, merge, rename, back up, or replace unmanaged `P2P-SETUP.md` files.
- Do not implement contract repair, schema migration, contract recovery, or legacy adoption workflows.
- Do not add MCP mutation in the first implementation.
- Do not create Git commits, branches, pushes, pull requests, merges, or provider handoffs.
- Do not perform unrelated governed mutations after a new contract makes the active runtime incompatible.

Source: `.p2p/proposals/PROP-095-project-runtime-contract-upgrade-lifecycle/proposal.md` (`VME-063c6c0a732774a2e120d847`).

### Goals - PROP-099

- Define a Human Project Publication Pipeline from governed P2P state to complete export, curated Markdown, publication validation, and neutral PDF.
- Keep deterministic export, semantic curation, owner review, publication validation, and PDF rendering as independent and inspectable stages.
- Make the curated document project-first, vertical-aware, traceable, and readable by humans who do not know P2P internals.
- Define an incremental implementation path with a minimal end-to-end slice first and richer CLI orchestration, publication packages, profiles, and themes later.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-7cd53531e3428369bf9c8bf5`).

### Non-Goals - PROP-099

- Do not make generated outputs a new source of truth; .p2p remains governed project memory.
- Do not make the curator decide governance outcomes, readiness, implementation status, or owner choices.
- Do not replace the P2P-native software specification lifecycle, OpenSpec, Spec Kit, or downstream implementation exports.
- Do not require a fully deterministic curator in the first slice; semantic curation may be agentic but must be bounded by contracts and validation.
- Do not introduce multiple themes, branding, visual editors, template marketplaces, sophisticated appendices, automatic permanent replacement of project.md, or full MCP parity in the first slice.

Source: `.p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy/proposal.md` (`VME-555ec2cebc9475e511f15446`).

### Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-05e43da4ac2c2c1ef5814c79`).

### Non-Goals - PROP-100

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

Source: `.p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology/proposal.md` (`VME-5eebb52013173bf13cade72b`).

### Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-4144a719c351590589d22d8d`).

### Non-Goals - PROP-101

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

Source: `.p2p/proposals/PROP-101-project-readiness-convergence-workflow/proposal.md` (`VME-06bc3330b93fc264be61867c`).

### Goals - PROP-102

- Preserve an append-only, queryable history of proposal decision events,
  including rationale, owner authority, date, predecessor and lineage.
- Derive current proposal status and authority deterministically from the valid
  event sequence.
- Define an exhaustive transition matrix with exact retry, invalid transition
  and reconsideration behavior.
- Distinguish initial rejection from withdrawal, revocation, supersession,
  reinstatement and downstream deprecation.
- Make decision mutations owner-controlled, previewed, source-bound,
  stale-safe, atomic, idempotent where appropriate and recoverable.
- Keep current CLI and human-readable status views available as projections
  during a forward compatibility transition.
- Migrate current single-decision artifacts without inventing missing owner
  evidence or erasing legacy values.
- Propagate lifecycle authority consistently to validation, registries,
  project projections, decision context, relations, vertical evidence, Change
  Sets, Work, software specifications, next actions and publication.
- Produce explicit impact and remediation guidance without automatically
  changing dependent owner-controlled lifecycles.
- Establish the stable authority and lineage contract required by future
  thematic decision-memory consolidation.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-ea9c54a4d313f4621a7a4cfd`).

### Non-Goals - PROP-102

- Physically delete accepted, rejected, revoked or superseded proposals.
- Rewrite history so that a previously accepted decision appears never to have
  been active.
- Automatically roll back source code, deployments, completed Change Sets,
  Work or external effects.
- Automatically cancel, supersede, complete or reopen dependent lifecycle
  objects.
- Implement thematic proposal compaction, persistent decision-context caching
  or publication curator refinement.
- Treat `deprecated` as another proposal decision outcome.
- Allow an agent-supplied actor string to establish owner authority.
- Conflate proposal-decision rejection with managed proposal-branch rejection.

Source: `.p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle/proposal.md` (`VME-689bd9fd5d8f1065457d75d1`).

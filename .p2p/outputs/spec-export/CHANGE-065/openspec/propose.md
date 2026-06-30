# OpenSpec Proposal Input

Use this as the proposal-oriented initialization input for OpenSpec or an OpenSpec-aware agent.

## Problem

- **PROP-001 — CLI Foundation**: P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.
- **PROP-002 Proposal Exploration And Readiness Workflow**: P2P Engine deve impedire che una proposta passi troppo rapidamente da idea
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
- **PROP-004 Prompt-only Import Workflow**: P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.
- **PROP-005 Codex Skill Integration**: Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.
- **PROP-006 Multi-Agent Integration Model**: P2P Engine can already generate basic agent-facing instructions for generic, Codex, and Claude profiles, but it does not yet manage agent integrations as governed, inspectable, updateable project state. Project initialization should create the supported project-local agent file structures by default, but today there is no explicit registry of installed integrations, generated-file manifests, hashes, drift detection, safe update, safe uninstall, conflict detection, or precise adapter matrix for Cursor, Copilot, Gemini, OpenCode, Codex, Claude, and the generic baseline. A second gap is methodological: generated instructions do not yet force agents to turn weak proposal readiness, failed gates, and owner questions into concrete refinement actions, alternatives, recommendations, candidate edits, and readiness re-checks.
- **PROP-009 Governance CLI Commands**: P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.

## Proposed Change

- **PROP-001 — CLI Foundation**: Build the first P2P Engine CLI using Python and Typer.

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
- **PROP-002 Proposal Exploration And Readiness Workflow**: Introdurre un workflow di **Proposal Exploration And Readiness** composto da:

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
- **PROP-004 Prompt-only Import Workflow**: Implementare comandi import uniformi per le fasi successive a explore e aggiungere synthesize prompt/import.
- **PROP-005 Codex Skill Integration**: Aggiungere una skill locale .codex/skills/p2p-engine/SKILL.md che istruisca Codex a usare P2P Engine come sorgente di verita operativa.
- **PROP-006 Multi-Agent Integration Model**: Introduce an Agent Integration Registry MVP. By default, p2p init creates the generic baseline and all supported project-local adapter files for generic, codex, claude, cursor, copilot, gemini, and opencode. The owner may request a narrower init set with repeated --agent options, but generic is always included and cannot be removed. P2P records installed integrations in .p2p/agent-integrations.yml using schema_version 1, baseline_profile: generic, adapter status, maturity, capabilities, template_version, generated file records, shared ownership, managed flag, template_id, SHA-256 hash over exact file bytes, and drift state. The registry must not contain active_agent, default_agent, preferred_agent, current_agent, use, or switch state. Built-in adapter templates live in package data under src/p2p_engine/templates/agents/<adapter>/ for the MVP; project-local template overrides are deferred. Generated Markdown files should include a short managed header as a human hint, while the registry remains authoritative. The CLI exposes p2p agent list, show, install, update, doctor, and uninstall; excluded commands are use, switch, current, and install --no-use. doctor validates registry shape, file existence, hashes, shared references, generic baseline, ownership conflicts, uninstall safety, and presence of the generic method behavior block. install all may install every supported project-local integration only when non-shared file targets do not conflict. Migration is conservative: known generated files become managed, unknown or changed files become unmanaged or drifted, and P2P never overwrites them silently. Generated files derive from minimal generic P2P governance content and may be adapted for host tools without weakening the rules. That generic content must include readiness-driven refinement behavior: when a proposal is weak, low-confidence, below target, or blocked by failed gates, the agent must explain each gap, propose concrete alternatives, recommend one when justified, identify owner decisions, draft candidate updates, and re-check readiness after refinement. Initial files are AGENTS.md and .p2p/agent-policy.yml for generic; AGENTS.md plus a shared agent-neutral .agents/skills/p2p-project/SKILL.md for Codex when safe, with .codex/skills preserved as compatibility/migration; CLAUDE.md for Claude; .cursor/rules/p2p.mdc for Cursor; .github/copilot-instructions.md for Copilot; GEMINI.md for Gemini; and AGENTS.md only for OpenCode in the MVP. opencode.json is not generated by default. CLI and MCP tools are implemented over the same core behavior, with MCP exposing structured equivalents for compatible agents. Future readiness refinement commands should live under p2p proposal readiness, but they are not required for accepting this proposal.
- **PROP-009 Governance CLI Commands**: Aggiungere comandi governance file-based per rendere operativo il modello di PROP-008, mantenendo Git come audit layer e rimandando enforcement permessi a fasi future.

## Scope

- **PROP-001 — CLI Foundation**: - Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.
- **PROP-002 Proposal Exploration And Readiness Workflow**: - Reframing di PROP-002 da semplice fase `explore` a workflow di proposal
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
- **PROP-004 Prompt-only Import Workflow**: - Aggiungere import per clarify, synthesize, plan e tasks.
- Rendere il workflow prompt-only end-to-end testabile.
- **PROP-005 Codex Skill Integration**: - Creare una skill Codex che guidi l'uso della CLI P2P e degli artefatti .p2p.
- Stabilire regole per trasformare conversazioni in proposal, exploration, decisioni, piani e task versionati.
- **PROP-006 Multi-Agent Integration Model**: - Create all supported project-local agent integrations by default during project init, unless the owner explicitly narrows the install set.
- Keep generic as the mandatory, unremovable common baseline from which agent-specific files are derived.
- Introduce a versioned project-local .p2p/agent-integrations.yml registry with generated-file manifests, ownership metadata, shared-file flags, template versions, SHA-256 hashes, and drift state.
- Use built-in package templates for the MVP and defer project-local template overrides.
- Support safe install, install all, list, show, update, doctor, and uninstall flows without active/default/preferred agent state.
- Define the initial adapter matrix for generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode, including shared files and excluded legacy/conflicting targets.
- Define common method behavior for generated instructions so agents transform readiness gaps into alternatives, recommendations, owner questions, candidate edits, and readiness re-checks.
- Keep P2P CLI, MCP tools, .p2p state, validation, readiness, and owner decisions aligned over the same core behavior.
- **PROP-009 Governance CLI Commands**: - Implementare p2p governance init/status.
- Implementare p2p swot prompt per alternative contrapposte.
- Implementare p2p vote record/status.
- Implementare p2p precedent record.

## Out Of Scope

- **PROP-001 — CLI Foundation**: - No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.
- **PROP-002 Proposal Exploration And Readiness Workflow**: - Non sostituire le decisioni governance dell'owner con uno score automatico.
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
- **PROP-004 Prompt-only Import Workflow**: - Non invocare provider AI direttamente.
- Non introdurre MCP.
- Non aggiungere web app o database.
- **PROP-005 Codex Skill Integration**: - Non introdurre MCP in questa fase.
- Non invocare direttamente provider AI dalla CLI.
- Non sostituire la CLI come sorgente di verita.
- **PROP-006 Multi-Agent Integration Model**: - Project-level preferred, default, current, switched, or active agent selection.
- Direct invocation of AI providers or hosted agent runtimes.
- Destructive uninstall of files that have been manually modified or are shared with other installed integrations.
- Automatic edits to user/global agent configuration outside the project without explicit consent.
- Generation of deprecated .cursorrules files or default opencode.json configuration in the MVP.
- Full implementation of dedicated readiness refinement commands unless covered by this proposal's implementation scope or a follow-up readiness proposal.
- **PROP-009 Governance CLI Commands**: - Implementare enforcement reale dei permessi applicativi.
- Integrare branch protection, CODEOWNERS o required approvals.
- Chiudere automaticamente votazioni o decisioni complesse.

## Impact

- Source Change Set: `CHANGE-065` Implement Agent Integration Registry MVP

## Risks

- NEEDS CLARIFICATION: confirm target-specific risks before implementation.

## Acceptance Criteria

## Criteria

- Change Set metadata is present and reviewable.

## Tests / Verification

- Not specified yet.

## Source Traceability

- `PROP-001` — CLI Foundation — `.p2p/proposals/PROP-001-cli-foundation`
- `PROP-002` Proposal Exploration And Readiness Workflow — `.p2p/proposals/PROP-002-exploration-phase`
- `PROP-004` Prompt-only Import Workflow — `.p2p/proposals/PROP-004-prompt-only-import-workflow`
- `PROP-005` Codex Skill Integration — `.p2p/proposals/PROP-005-codex-skill-integration`
- `PROP-006` Multi-Agent Integration Model — `.p2p/proposals/PROP-006-multi-agent-integration-model`
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
- `PROP-059` P2PWorkspace Modular Refactoring Plan — `.p2p/proposals/PROP-059-p2pworkspace-modular-refactoring-plan`
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
- `PROP-073` Ergonomic Remote Project Initialization — `.p2p/proposals/PROP-073-ergonomic-remote-project-initialization`
- `PROP-074` Agent Runtime Bootstrap Robustness — `.p2p/proposals/PROP-074-agent-runtime-bootstrap-robustness`
- `PROP-075` MCP End-To-End Proposal Collaboration Workflow — `.p2p/proposals/PROP-075-mcp-end-to-end-proposal-collaboration-workflow`
- `PROP-076` P2P Cloud Runner Boundary and Containerized Execution Model — `.p2p/proposals/PROP-076-p2p-cloud-runner-boundary-and-containerized-execution-model`
- `PROP-077` Permission-Gated Draft Proposal Decisions via MCP — `.p2p/proposals/PROP-077-permission-gated-draft-proposal-decisions-via-mcp`
- `PROP-078` Project-Local Wheel Installation and Upgrade Model — `.p2p/proposals/PROP-078-project-local-wheel-installation-and-upgrade-model`
- `PROP-079` Managed Next Action Lifecycle — `.p2p/proposals/PROP-079-managed-next-action-lifecycle`
- `PROP-080` Automated GitHub Release Wheel Publishing — `.p2p/proposals/PROP-080-automated-github-release-wheel-publishing`
- `PROP-081` MCP and Skill Support for Managed Next Actions — `.p2p/proposals/PROP-081-mcp-and-skill-support-for-managed-next-actions`
- `PROP-082` Readiness Assessment Refresh And Review Workflow — `.p2p/proposals/PROP-082-readiness-assessment-refresh-and-review-workflow`
- `PROP-083` Domain-Aware Visible Project Definition Export — `.p2p/proposals/PROP-083-domain-aware-visible-project-definition-export`
- `PROP-085` Pluggable Project Verticals And Readiness Orchestration — `.p2p/proposals/PROP-085-pluggable-project-verticals-and-readiness-orchestration`
- `PROP-086` Artifact-aware Proposal Readiness And Agent Interview Orchestration — `.p2p/proposals/PROP-086-artifact-aware-proposal-readiness-and-agent-interview-orchestration`
- `PROP-087` Agent Personality Model For Decision Mediation — `.p2p/proposals/PROP-087-agent-personality-model-for-decision-mediation`

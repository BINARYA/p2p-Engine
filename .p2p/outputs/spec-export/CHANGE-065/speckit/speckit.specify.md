# Spec Kit Specify Prompt

Use this content with `/speckit.specify`. Focus on what and why; do not select a tech stack here.

## What To Build

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
- **PROP-010 P2P Project State Model**: Add a P2P project state model that turns accepted proposals into versioned project artifacts under `.p2p/project/`. The MVP uses explicit refresh via `p2p project refresh`; automatic refresh after acceptance can be added later.
- **PROP-011 Project Refresh MVP**: Add deterministic project-state generation from accepted proposals, starting with overview, problem, scope, project SWOT placeholder, features, decisions-map, and conflicts.

## Why

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
- **PROP-010 P2P Project State Model**: Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.
- **PROP-011 Project Refresh MVP**: P2P Engine has accepted the .p2p/project state model, but the CLI cannot yet generate or inspect that rationalized project layer.

## Users And Workflows

- Humans supervise and decide.
- Agents use P2P memory to preserve project context and propose bounded changes.

## Requirements

## Functional Requirements

### PROP-006 - Multi-Agent Integration Model

Introduce an Agent Integration Registry MVP. By default, p2p init creates the generic baseline and all supported project-local adapter files for generic, codex, claude, cursor, copilot, gemini, and opencode. The owner may request a narrower init set with repeated --agent options, but generic is always included and cannot be removed. P2P records installed integrations in .p2p/agent-integrations.yml using schema_version 1, baseline_profile: generic, adapter status, maturity, capabilities, template_version, generated file records, shared ownership, managed flag, template_id, SHA-256 hash over exact file bytes, and drift state. The registry must not contain active_agent, default_agent, preferred_agent, current_agent, use, or switch state. Built-in adapter templates live in package data under src/p2p_engine/templates/agents/<adapter>/ for the MVP; project-local template overrides are deferred. Generated Markdown files should include a short managed header as a human hint, while the registry remains authoritative. The CLI exposes p2p agent list, show, install, update, doctor, and uninstall; excluded commands are use, switch, current, and install --no-use. doctor validates registry shape, file existence, hashes, shared references, generic baseline, ownership conflicts, uninstall safety, and presence of the generic method behavior block. install all may install every supported project-local integration only when non-shared file targets do not conflict. Migration is conservative: known generated files become managed, unknown or changed files become unmanaged or drifted, and P2P never overwrites them silently. Generated files derive from minimal generic P2P governance content and may be adapted for host tools without weakening the rules. That generic content must include readiness-driven refinement behavior: when a proposal is weak, low-confidence, below target, or blocked by failed gates, the agent must explain each gap, propose concrete alternatives, recommend one when justified, identify owner decisions, draft candidate updates, and re-check readiness after refinement. Initial files are AGENTS.md and .p2p/agent-policy.yml for generic; AGENTS.md plus a shared agent-neutral .agents/skills/p2p-project/SKILL.md for Codex when safe, with .codex/skills preserved as compatibility/migration; CLAUDE.md for Claude; .cursor/rules/p2p.mdc for Cursor; .github/copilot-instructions.md for Copilot; GEMINI.md for Gemini; and AGENTS.md only for OpenCode in the MVP. opencode.json is not generated by default. CLI and MCP tools are implemented over the same core behavior, with MCP exposing structured equivalents for compatible agents. Future readiness refinement commands should live under p2p proposal readiness, but they are not required for accepting this proposal.

## Non-Goals / Exclusions

- Automatic Git commits, branches, tags, or merges.

## Constraints

Do not treat raw proposal discussion as implementation requirements without accepted scope.

## Open Questions

Not specified yet.

## Success Criteria

## Criteria

- Change Set metadata is present and reviewable.

## Tests / Verification

- Not specified yet.

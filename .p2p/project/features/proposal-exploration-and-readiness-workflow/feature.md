# Proposal Exploration And Readiness Workflow

## Provenance

- Proposal: PROP-002
- Source: .p2p/proposals/PROP-002-exploration-phase

## Problem

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

## Proposal

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

## Decision

# Decision - PROP-002

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner accepts the proposal exploration and readiness workflow after review.

## Date

2026-06-04

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-40bb9fc4ad4fb5072eba4077

## Decision Fingerprint

aa7ab4d393d704b8d42ebfadf6e1810104ea20cf6d909c629c485e98225aa225

## Lineage

None.

## Canonical Source

decision-events.yml

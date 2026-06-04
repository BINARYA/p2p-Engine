# Exploration - PROP-002

## Interpretazione

La proposal non introduce solo una fase `explore`. Introduce il metodo con cui
P2P Engine impedisce che una proposta passi da idea generica a decisione senza
una maturazione sufficiente.

Il punto centrale e distinguere tre cose:

- lifecycle state: dove si trova proceduralmente la proposta;
- computed readiness: quanto e matura secondo criteri espliciti;
- owner decision: cosa decide l'owner, anche quando accetta consapevolmente una
  proposta non pienamente matura.

## Concetti emersi

- Interlocuzione guidata.
- Exploration ripetibile.
- Readiness score da 0 a 100.
- Pedanteria agentica regolata da soglie.
- Minimum gate non compensabili per le proposte importanti.
- Confidence separata dallo score.
- Evidenze/artifact collegati ai criteri.
- Artifact quality gate contro compilazione generica.
- Skill agentiche come guida conversazionale.
- CLI/engine come sorgente di verita.
- Artefatti versionati.
- Owner override auditabile.

## Readiness Model

La readiness affianca lo stato della proposal e non lo sostituisce.

Esempio:

```yaml
state: draft
tier: governance-critical
readiness:
  computed_score: 82
  effective_score: 82
  label: partial
  confidence: medium
  required_score_for_decision: 95
  missing:
    - acceptance_criteria
    - owner_questions_resolution
  suggested_next:
    - resolve_owner_questions
    - define_acceptance_criteria
```

Con override owner:

```yaml
state: accepted
tier: small
readiness:
  computed_score: 61
  effective_score: 100
  label: forced_ready
  confidence: medium
  owner_override: true
  override_reason: "L'owner considera la proposta semplice e accetta consapevolmente i rischi residui."
```

`computed_score` deve restare onesto. `effective_score` rappresenta la
decisione operativa dopo eventuale override.

## Criteria And Weights

Prima griglia proposta per il `computed_score`:

| Criterion | Points |
| --- | ---: |
| Problem clarity | 10 |
| Goal clarity | 10 |
| Scope boundaries | 10 |
| Alternatives quality | 15 |
| Tradeoff analysis | 10 |
| Risk coverage | 10 |
| Assumptions clarity | 10 |
| Owner questions resolution | 10 |
| Acceptance criteria quality | 10 |
| Impact and overlap analysis | 5 |
| Total | 100 |

`Alternatives quality` pesa 15 perche il problema osservato e che molte proposte
descrivono una soluzione senza dimostrare una scelta consapevole tra opzioni
reali.

## Criterion Scoring Scale

Ogni criterio dovrebbe usare una scala interna:

```text
0%   assente
25%  presente ma generico
50%  parziale
75%  buono ma con lacune
100% solido e specifico
```

Il punteggio assegnato deve indicare le evidenze usate:

```yaml
criteria:
  alternatives_quality:
    max_points: 15
    awarded_points: 11
    evidence:
      - alternatives.md
      - suggested-scope.md
    notes: "Sono presenti alternative reali, ma manca una matrice comparativa completa."
```

## Labels And Thresholds

```text
0-69   weak
70-84  partial
85-94  strong
95-100 decision_ready
override forced_ready
```

Comportamento agente:

- 0-69: non suggerire acceptance; indicare lacune specifiche.
- 70-84: suggerire review solo con warning.
- 85-94: suggerire `ready_for_decision`.
- 95-100: suggerire acceptance se l'owner concorda.
- override: accettabile, ma tracciato come decisione consapevole.

## Tier Classification

```yaml
tier_classification:
  small:
    description: "Modifica locale, reversibile, basso impatto."
  medium:
    description: "Modifica di prodotto o workflow con impatto limitato."
  architectural:
    description: "Modifica struttura tecnica, dati, integrazioni, repository o API."
  governance-critical:
    description: "Modifica metodo P2P, lifecycle proposal, decisioni, agent behavior, ownership o policy."
```

`PROP-002` e `governance-critical`, perche definisce come il sistema valuta se
una proposta e abbastanza matura per essere portata a decisione.

## Minimum Gates

Il punteggio complessivo dice quanto e matura una proposta. I minimum gate
dicono se manca qualcosa di essenziale e non compensabile.

```yaml
tier_requirements:
  small:
    required_score: 70
    min_alternatives_quality: 0
    min_risk_coverage: 25

  medium:
    required_score: 85
    min_alternatives_quality: 50
    min_risk_coverage: 50
    min_acceptance_criteria_quality: 50

  architectural:
    required_score: 95
    min_alternatives_quality: 75
    min_tradeoff_analysis: 75
    min_risk_coverage: 75
    min_impact_overlap_analysis: 75

  governance-critical:
    required_score: 95
    min_alternatives_quality: 75
    min_owner_questions_resolution: 75
    min_acceptance_criteria_quality: 75
    min_impact_overlap_analysis: 75
```

## Confidence

Lo score misura maturita dell'esplorazione, ma serve anche una misura di
affidabilita dell'analisi.

```yaml
readiness:
  computed_score: 82
  confidence: medium
  confidence_reasons:
    - "Le alternative sono presenti ma non validate."
    - "Gli impatti sul modello MCP sono ipotetici."
```

Questo distingue:

- proposta incompleta;
- proposta completa ma incerta;
- proposta completa e ben fondata.

## Artifact Quality Gate

Per evitare compilazione generica, la qualita dell'artifact deve limitare il
punteggio massimo ottenibile dal criterio collegato.

```yaml
artifact_quality_gate:
  placeholder:
    max_criterion_score_percent: 0
  thin:
    max_criterion_score_percent: 50
  meaningful:
    max_criterion_score_percent: 75
  ready:
    max_criterion_score_percent: 100
```

Regola:

> Un criterio non puo ricevere piu del 50% del proprio punteggio se il relativo
> artifact e classificato come `thin` o contiene solo affermazioni generiche non
> collegate alla proposal.

## `p2p next` Delta

`p2p next` dovrebbe mostrare il delta verso il target, non solo la lacuna:

```yaml
readiness_gap:
  current_score: 82
  target_score: 95
  missing_points: 13
  highest_impact_actions:
    - action: add_alternatives_comparison
      estimated_gain: 6
    - action: resolve_owner_questions
      estimated_gain: 4
    - action: define_acceptance_criteria
      estimated_gain: 3
```

Questo aiuta owner e agenti a scegliere la prossima azione piu efficace.

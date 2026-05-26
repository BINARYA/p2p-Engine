# Exploration - PROP-008

## Interpretazione

La proposal definisce il primo modello di governance di P2P Engine: chi decide, con quali regole, come vengono confrontate alternative contrapposte e come le decisioni diventano tracciabili.

Il punto critico e separare:

```text
governance metodologica
  regole, ruoli, voti, decisioni, precedenti

governance tecnica
  Git, branch, commit, merge, PR, permessi esterni
```

Nel MVP P2P non deve implementare un sistema completo di privilegi applicativi. Deve pero produrre artefatti chiari, versionati e compatibili con futuri permessi reali.

## Modelli iniziali

### owner_decides

Chi avvia o mantiene il progetto decide.

Utile per:

- bootstrap;
- team piccoli;
- alta velocita;
- responsabilita chiara.

### open_consensus

Chiunque puo proporre, commentare e sostenere una proposta. Si procede se non ci sono obiezioni bloccanti o se il maintainer conferma.

Utile per:

- community;
- team aperti;
- decisioni non esclusive.

### exclusive_vote

Quando due o piu alternative sono contrapposte, solo una vince. Il risultato viene registrato come precedente decisionale.

Utile per:

- scelte mutualmente esclusive;
- standard;
- governance;
- direzioni architetturali.

## Integrazione Git

Git non sostituisce un permission system, ma fornisce audit:

```text
proposal branch
→ modifica proposal/governance artifacts
→ commit
→ decision.md + votes.yml + swot-analysis.md
→ merge su main = decisione applicata
```

In futuro, GitHub/GitLab/Gitea possono aggiungere:

- branch protection;
- CODEOWNERS;
- required approvals;
- signed commits;
- team permissions;
- PR review.

## Ruolo dell'AI

L'AI puo:

- sintetizzare alternative;
- generare SWOT;
- evidenziare trade-off;
- individuare conflitti;
- suggerire domande;
- evidenziare precedenti.

L'AI non decide.

## Output MVP

```text
.p2p/governance/governance.yml
.p2p/governance/roles.yml
.p2p/governance/decision-precedents.yml

.p2p/proposals/<proposal>/
  alternatives.md
  swot-analysis.md
  votes.yml
  decision.md
```

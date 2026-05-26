# Exploration - PROP-007

## Interpretazione

La proposal introduce una fase precedente alla creazione o arricchimento di una proposal: il triage della nuova idea rispetto al patrimonio di proposal esistenti.

L'obiettivo non e ancora esplorare a fondo la proposta, ma decidere dove collocarla:

- nuova proposal;
- contributo a proposal esistente;
- aggiornamento di proposal esistente;
- duplicato;
- merge;
- split;
- defer.

## Distinzione da Exploration

```text
triage
  valuta dove collocare una nuova idea rispetto alle proposal esistenti

explore
  interroga una proposal gia individuata per scoprirne implicazioni e rischi
```

## Scenario

Utente:

```text
preparare una CLI con dei comandi definiti
```

P2P Engine dovrebbe rispondere con un'analisi simile:

```text
PROP-001 CLI Foundation
  overlap: high
  reason: copre gia creazione CLI e comandi iniziali

PROP-004 Prompt-only Import Workflow
  overlap: medium
  reason: copre alcuni comandi specifici prompt/import

Suggested action:
  add contribution to PROP-001
```

## Output attesi

- overlap-analysis.md;
- related-proposals.yml;
- suggested action;
- next P2P command.

## MVP

Il primo MVP puo essere file-based e prompt-only:

```bash
p2p proposal triage prompt "idea grezza"
p2p proposal triage import triage-output.md
```

Oppure:

```bash
p2p triage prompt "idea grezza"
p2p triage import triage-output.md
```

La decisione sul naming resta aperta.

# PROP-002 - Exploration Phase

## Status

`draft`

## Problem

P2P Engine deve supportare la fase di interlocuzione in cui un'idea grezza viene interrogata prima di diventare una proposal strutturata. Senza questa fase, il sistema rischia di limitarsi a riassumere contributi gia esistenti invece di far maturare davvero la proposta.

## Context

Il primo dogfooding ha mostrato che `proposal create` e i prompt generator funzionano, ma una proposal iniziale puo restare troppo vuota. Serve una fase ripetibile che scopra implicazioni, alternative, assunzioni, rischi, decisioni nascoste e domande aperte.

## Goals

- Formalizzare `Exploration Phase` nel workflow P2P.
- Aggiungere artefatti dedicati per exploration, findings, alternative, domande, rischi, assunzioni e scope suggerito.
- Implementare `p2p explore prompt`.
- Implementare `p2p explore import`.
- Implementare `p2p explore status`.
- Mantenere il modello prompt-only, senza AI adapter diretti.
- Chiarire che CLI/engine e la sorgente di verita, mentre le skill agentiche guidano la conversazione.

## Non-Goals

- Non integrare Codex/Claude/Ollama direttamente in questa fase.
- Non introdurre MCP.
- Non costruire una web app.
- Non sostituire digest, clarify o synthesize.

## Proposal

Introdurre una fase autonoma e ripetibile chiamata `explore`.

`explore` non riassume e non decide. Serve a interrogare la proposta e generare materiale che alimenta clarify, synthesize, decision, plan e tasks.

Gli output validi devono essere salvati negli artefatti P2P versionati:

```text
exploration.md
findings.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

La CLI deve supportare:

```bash
p2p explore prompt PROP-002
p2p explore import PROP-002 exploration-output.md
p2p explore status PROP-002
```

## Acceptance Criteria

- Le proposal nuove includono gli artefatti di exploration.
- `p2p explore prompt PROP-XXX` genera un prompt dedicato.
- `p2p explore import PROP-XXX <file-or-directory>` importa output esterni negli artefatti P2P.
- `p2p explore status PROP-XXX` mostra quali artefatti sono completi o mancanti.
- La foundation documenta differenza tra explore, digest, clarify e synthesize.
- La regola CLI/engine come sorgente di verita e skill come guida conversazionale e documentata.

## Decision

Pending.


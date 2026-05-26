# Exploration - PROP-006

## Interpretazione

La proposta mira a generalizzare l'integrazione Codex appena introdotta, trasformandola da soluzione singola a modello multi-agent.

P2P Engine non dovrebbe integrare direttamente un singolo provider AI come centro del sistema. Dovrebbe invece installare e mantenere istruzioni, skill, slash command o command files specifici per diversi agenti, mantenendo la CLI e gli artefatti `.p2p/` come sorgente di verita.

## Pattern osservati

### Spec Kit

Spec Kit usa una CLI di integrazione con agent key e comandi per listare, installare, usare, switchare, aggiornare e disinstallare integrazioni. La documentazione ufficiale descrive anche un'integrazione generica per agent non elencati e il tracciamento dello stato in `.specify/integration.json`.

Fonte: https://github.github.com/spec-kit/reference/integrations.html

### OpenSpec

OpenSpec punta su slash command, skills, aggiornamento delle istruzioni agentiche e supporto a molti tool. Il README ufficiale evidenzia l'uso di `/opsx:propose`, l'update delle agent instructions tramite `openspec update` e un approccio tool-agnostic.

Fonte: https://github.com/Fission-AI/OpenSpec

## Direzione per P2P Engine

P2P Engine puo introdurre un Agent Integration Layer che gestisce:

- profili agent;
- directory di destinazione per skill/command files;
- template per ogni agent;
- stato delle integrazioni installate;
- default agent;
- install/update/remove/use;
- modalita generic per tool non supportati.

## Principio

Gli agenti sono interfacce conversazionali e operative. Il motore P2P resta la fonte di verita.

```text
P2P CLI/Core
→ genera profili agent
→ installa skill/commands specifici
→ gli agenti usano la CLI
→ gli artefatti .p2p restano versionati
```

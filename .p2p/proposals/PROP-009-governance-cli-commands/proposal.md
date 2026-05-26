# PROP-009 - Governance CLI Commands

## Status

`accepted`

## Problem

P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.

## Context

PROP-008 ha definito owner_decides, open_consensus, exclusive_vote, votes.yml, swot-analysis.md e decision-precedents.yml. Ora serve rendere questi artefatti operativi nella CLI senza introdurre ancora permessi reali.

## Goals

- Implementare p2p governance init/status.
- Implementare p2p swot prompt per alternative contrapposte.
- Implementare p2p vote record/status.
- Implementare p2p precedent record.

## Non-Goals

- Implementare enforcement reale dei permessi applicativi.
- Integrare branch protection, CODEOWNERS o required approvals.
- Chiudere automaticamente votazioni o decisioni complesse.

## Proposal

Aggiungere comandi governance file-based per rendere operativo il modello di PROP-008, mantenendo Git come audit layer e rimandando enforcement permessi a fasi future.

## Acceptance Criteria

- La CLI genera e valida governance.yml, roles.yml e decision-precedents.yml.
- La CLI puo registrare voti in votes.yml e mostrare lo stato di voto.
- La CLI puo generare un prompt SWOT e registrare un precedente decisionale.

## Decision

Accepted. La CLI deve rendere operativi gli artefatti governance definiti da PROP-008 in modalita audit-only.

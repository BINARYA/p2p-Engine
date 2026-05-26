# Governance CLI Commands

## Provenance

- Proposal: PROP-009
- Source: .p2p/proposals/PROP-009-governance-cli-commands

## Problem

P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.

## Proposal

Aggiungere comandi governance file-based per rendere operativo il modello di PROP-008, mantenendo Git come audit layer e rimandando enforcement permessi a fasi future.

## Decision

# Decision - PROP-009

## Status

`accepted`

## Outcome

accepted

## Reason

PROP-008 ha definito il modello di governance, ma senza comandi CLI il workflow resta solo documentale. I comandi governance, swot, vote e precedent rendono il modello provabile nel repository senza introdurre ancora un sistema di privilegi applicativi.

## Scope

- Inizializzare governance.yml, roles.yml e decision-precedents.yml.
- Generare prompt SWOT per alternative contrapposte.
- Registrare voti in votes.yml e mostrare conteggi.
- Registrare precedenti decisionali riutilizzabili.

## Constraints

- La governance MVP e audit-only.
- La decisione resta umana o governance-defined.
- Git resta il layer di audit e permessi reali fino a una fase successiva.

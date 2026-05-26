# PROP-003 - Prompt generator hardening

## Status

`deferred`

## Problem

I prompt generati ereditano troppe sezioni vuote o placeholder da proposal.md, producendo contesto poco utile per la sintesi AI.

## Context

PROP-003 e la prima proposal generata con la CLI stessa. Il suo scopo e migliorare subito la qualita degli artefatti prodotti dal workflow dogfooding.

## Goals

- Permettere a proposal create di ricevere sezioni strutturate gia al momento della creazione.
- Permettere a proposal update di arricchire una proposal esistente senza editing manuale.
- Aggiungere contesto di governance ai prompt generati.
- Istruire i prompt a trattare Pending e placeholder come informazioni mancanti.

## Non-Goals

- Non integrare provider AI diretti in questa fase.
- Non introdurre una web app o un database.

## Proposal

Estendere la CLI con opzioni strutturate per create/update e rendere i prompt piu robusti includendo governance e istruzioni esplicite sulle informazioni mancanti.

## Acceptance Criteria

- p2p proposal create accetta problem, context, goal, non-goal, proposal e acceptance.
- p2p proposal update aggiorna sezioni specifiche di proposal.md.
- I prompt includono governance context e istruzioni sui placeholder.
- Sono presenti test automatici per proposta arricchita, update e digest prompt.

## Decision

Pending.

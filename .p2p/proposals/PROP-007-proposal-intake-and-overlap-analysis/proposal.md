# PROP-007 - Proposal Intake and Overlap Analysis

## Status

`draft`

## Problem

Quando un utente propone una nuova idea, P2P Engine oggi non valuta automaticamente se sia gia coperta da proposal esistenti, se sia un duplicato, un'estensione, un conflitto o uno spunto da aggiungere a una proposal gia aperta.

## Context

Le proposal esistenti coprono exploration, skill Codex e workflow prompt-only, ma manca una fase di intake/triage che governi il patrimonio delle proposal prima di crearne una nuova.

## Goals

- Aggiungere una fase di intake per analizzare idee grezze rispetto alle proposal esistenti.
- Suggerire se creare una nuova proposal, aggiornarne una esistente, aggiungere un contributo, fondere, splittare o rimandare.
- Produrre artefatti versionati di overlap analysis e related proposals.

## Non-Goals

- Pending.

## Proposal

Introdurre un workflow prompt-only di proposal triage che legge le proposal esistenti, genera un prompt di analisi, importa il risultato e suggerisce l'azione P2P successiva.

## Acceptance Criteria

- Una nuova idea puo essere confrontata con le proposal esistenti prima di creare duplicati.
- Il triage produce overlap-analysis.md e related-proposals.yml.
- Il sistema suggerisce una prossima azione P2P concreta.

## Decision

Pending.

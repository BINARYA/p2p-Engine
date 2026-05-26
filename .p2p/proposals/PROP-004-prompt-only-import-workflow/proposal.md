# PROP-004 - Prompt-only Import Workflow

## Status

`accepted`

## Problem

P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.

## Context

Il workflow MVP deve restare prompt-only: la CLI prepara prompt, l'utente o Codex produce output, la CLI importa gli artefatti versionati.

## Goals

- Aggiungere import per clarify, synthesize, plan e tasks.
- Rendere il workflow prompt-only end-to-end testabile.

## Non-Goals

- Non invocare provider AI direttamente.
- Non introdurre MCP.
- Non aggiungere web app o database.

## Proposal

Implementare comandi import uniformi per le fasi successive a explore e aggiungere synthesize prompt/import.

## Acceptance Criteria

- Ogni fase prompt-only ha un comando prompt e un comando import.
- I test coprono un workflow completo da proposal a tasks.

## Decision

Accepted. The prompt-only workflow needs import commands before Codex skills or AI adapters can use P2P Engine reliably.

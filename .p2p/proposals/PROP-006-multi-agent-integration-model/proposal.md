# PROP-006 - Multi-Agent Integration Model

## Status

`draft`

## Problem

P2P Engine ha una prima skill Codex, ma non ha ancora un modello generale per integrare altri agenti AI come Claude, Gemini, Cursor, Copilot, OpenCode o strumenti generici.

## Context

Spec Kit espone un sistema di integrazioni per agent diversi, con install, switch, use e upgrade. OpenSpec usa slash command, skills e refresh degli agent instructions per supportare molti strumenti. P2P Engine puo prendere spunto da questi pattern restando proposal-first e Git-native.

## Goals

- Definire un modello di integrazione agent-agnostic per P2P Engine.
- Supportare agent profiles e installazione di istruzioni specifiche per tool diversi.
- Mantenere la CLI P2P come sorgente di verita e gli agenti come interfacce conversazionali.

## Non-Goals

- Pending.

## Proposal

Introdurre un P2P Agent Integration Layer con profili agent, comandi install/list/use/update e template di skill o command files per Codex, Claude, generic agent e futuri tool.

## Acceptance Criteria

- La proposal identifica pattern riusabili da Spec Kit e OpenSpec.
- La proposal distingue chiaramente engine P2P, agent profiles e artefatti installati per ciascun tool.
- La prima implementazione resta file-based e prompt-only.

## Decision

Pending.

# PROP-005 - Codex Skill Integration

## Status

`accepted`

## Problem

Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.

## Context

P2P Engine ora supporta un workflow prompt-only completo con prompt/import per exploration, clarify, synthesize, plan e tasks.

## Goals

- Creare una skill Codex che guidi l'uso della CLI P2P e degli artefatti .p2p.
- Stabilire regole per trasformare conversazioni in proposal, exploration, decisioni, piani e task versionati.

## Non-Goals

- Non introdurre MCP in questa fase.
- Non invocare direttamente provider AI dalla CLI.
- Non sostituire la CLI come sorgente di verita.

## Proposal

Aggiungere una skill locale .codex/skills/p2p-engine/SKILL.md che istruisca Codex a usare P2P Engine come sorgente di verita operativa.

## Acceptance Criteria

- Codex sa quando creare o aggiornare una proposal P2P.
- Codex usa la CLI per generare/importare artefatti invece di lasciare output solo in chat.

## Decision

Accepted. Codex should be able to guide conversation, but P2P CLI and `.p2p/` artifacts remain the operational source of truth.

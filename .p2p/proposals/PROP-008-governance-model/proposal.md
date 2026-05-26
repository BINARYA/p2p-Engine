# PROP-008 - Governance Model

## Status

`draft`

## Problem

P2P Engine deve definire chi puo decidere quali proposal entrano nel progetto, quali vengono rigettate, come scegliere tra alternative contrapposte e come evitare che decisioni gia prese vengano riproposte senza contesto nuovo.

## Context

La governance e una parte critica per trasformare discussioni in decisioni tracciate. In MVP non vogliamo ancora un sistema completo di permessi, utenti e ruoli applicativi, ma serve un modello file-based versionato e integrabile con Git.

## Goals

- Definire modelli decisionali iniziali: owner_decides, open_consensus, exclusive_vote.
- Definire artefatti per ruoli, regole, voti, precedenti decisionali e SWOT delle alternative.
- Chiarire come Git rende auditabile la governance senza sostituire un sistema di privilegi applicativi.

## Non-Goals

- Pending.

## Proposal

Introdurre una governance file-based con governance.yml, roles.yml, votes.yml, swot-analysis.md e decision-precedents.yml, usando owner_decides come default bootstrap e rimandando i permessi reali a fasi successive.

## Acceptance Criteria

- La proposal descrive almeno tre modelli decisionali iniziali.
- La proposal definisce come registrare voti, alternative, SWOT e decisioni.
- La proposal chiarisce integrazione Git e limiti del modello MVP.

## Decision

Pending.

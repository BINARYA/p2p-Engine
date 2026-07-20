# Custom Domain Definition Workflow

## Provenance

- Proposal: PROP-071
- Source: .p2p/proposals/PROP-071-custom-domain-definition-workflow

## Problem

P2P currently treats project domains as a fixed set of hardcoded identities. This makes predefined domains look authoritative at init time and makes custom domains an exception, even though P2P's broader model is that projects often start from unclear intent and become defined through user-agent collaboration.

## Proposal

Refactor domain initialization around optional templates. Every project has explicit domain state and rubric state. At init, the user may choose no template, a predefined template such as generic/software/grant_document/board_game, or a custom unresolved path. Applying a template pre-populates domain metadata and rubric criteria. Choosing custom or none leaves domain/rubric setup unresolved and creates or recommends first activities for defining the domain and defining the rubric with the user and agent. Maturity assessment becomes assessable only when an enabled rubric exists; unresolved or empty rubrics report a missing/unresolved rubric state instead of well_defined.

## Decision

# Decision - PROP-071

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to make domain and rubric initialization explicit and template-based across all projects, with custom/none treated as unresolved setup work.

## Date

2026-05-29

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-db12e1eb148c58478bc49735

## Decision Fingerprint

bbc7af42a43a1ef2262405b2f2a620e716dd951a4ace1c7ff33b419f85746300

## Lineage

None.

## Canonical Source

decision-events.yml

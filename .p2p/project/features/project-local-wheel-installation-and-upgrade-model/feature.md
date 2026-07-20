# Project-Local Wheel Installation and Upgrade Model

## Provenance

- Proposal: PROP-078
- Source: .p2p/proposals/PROP-078-project-local-wheel-installation-and-upgrade-model

## Problem

P2P Engine is currently practical to update only when the operator understands a separate source checkout or external path. Existing P2P projects need a coherent project-local installation and upgrade path that does not require referencing another folder, cloning the engine inside every project, or rerunning p2p init.

## Proposal

Introduce a packaging and installation model based on versioned wheel artifacts attached to GitHub Releases as the first distribution channel. Project setup documentation should install P2P Engine into the project-local .venv from a release wheel URL, and project upgrade documentation should use python -m pip install --upgrade <wheel-url>, followed by p2p doctor, p2p agent doctor, p2p registry refresh, p2p agent instructions refresh, and p2p validate. This is a transitional distribution model: the long-term target remains a public package such as PyPI, where installation becomes python -m pip install p2p-engine and upgrade becomes python -m pip install --upgrade p2p-engine. The proposal should avoid requiring users to reference external source checkout paths during normal project use.

## Decision

# Decision - PROP-078

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner approved project-local wheel installation as the transitional packaging model before public package distribution.

## Date

2026-06-03

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-17511e4112d3eb8d5006f03c

## Decision Fingerprint

9557c65f2432579bfdafa6992aaac67602090e7c84d2a502972e03e8b1f23bf8

## Lineage

None.

## Canonical Source

decision-events.yml

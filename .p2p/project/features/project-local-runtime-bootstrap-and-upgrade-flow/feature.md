# Project-Local Runtime Bootstrap And Upgrade Flow

## Provenance

- Proposal: PROP-084
- Source: .p2p/proposals/PROP-084-project-local-runtime-bootstrap-and-upgrade-flow

## Problem

A shared P2P-managed project must declare which P2P Engine runtime version is expected after clone, copy, or archive extraction. The problem is runtime version alignment: a human or agent must be able to determine the compatible runtime range and the recommended runtime version from project-local data, without relying on chat history, local machine state, Git history, or a separate P2P Engine source checkout.

## Proposal

Refocus PROP-084 on a minimal Project Runtime Contract and Runtime Version Alignment. Each P2P-managed project may declare .p2p/project/runtime.yml with a schema version, a compatible P2P Engine range, and a recommended P2P Engine runtime version. The contract tells a collaborator which runtime is expected and gives an installed runtime enough information to verify compatibility. New projects should receive both runtime.yml and a project-local P2P-SETUP.md that renders the same facts for humans and agents. When P2P Engine is available, runtime status reports compatible, incompatible, invalid_contract, unsupported_contract, missing_contract, or legacy_undeclared states with actionable guidance. Projects without any marker requiring runtime.yml are legacy_undeclared and warning-only. Projects that declare or require a runtime contract but are incompatible, invalid, unsupported, or missing the required contract must block governed writes before mutation. The proposal does not require a bootstrap script, does not add an install manager, does not perform runtime mutation, and does not depend on release wheel metadata.

## Decision

# Decision - PROP-084

## Status

`accepted_with_changes`

## Outcome

accepted_with_changes

## Reason

Accepted with changes after owner rescope: PROP-084 is limited to a minimal project runtime contract, project-local P2P-SETUP.md guidance, runtime status, validation, and a contract-aware governed-write gate. Mandatory setup scripts, install/reconcile managers, release resolvers, wheel/digest/source metadata, environment mutation, and automatic fallback are out of scope.

## Date

2026-07-12

## Approver

davide

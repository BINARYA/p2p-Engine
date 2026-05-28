# PROP-057 - Guided Rubric Selection During Init

## Status

`accepted`

## Problem

The init wizard now asks for a project domain and generates domain rubrics automatically, but the owner cannot confirm which suggested criteria should actually drive project definition maturity. This makes the rubric feel imposed by the system instead of selected as part of project governance.

## Context

Project definition maturity is now based on .p2p/project/rubrics.yml. The rubric file already supports enabled/disabled criteria, and the assessment ignores disabled criteria. Therefore the init wizard can offer a lightweight owner confirmation step without adding custom criteria, keyword editing, or advanced UI.

## Goals

- Let the owner confirm rubric criteria during interactive initialization.
- Keep all domain criteria enabled by default.
- Allow disabling suggested criteria with simple yes/no prompts.
- Store the selected criteria deterministically in .p2p/project/rubrics.yml.

## Non-Goals

- Do not support custom criteria in the wizard yet.
- Do not support editing criterion keywords or descriptions yet.
- Do not change non-interactive p2p init defaults.

## Proposal

Add Guided Rubric Selection During Init. When p2p init runs interactively, after project domain selection it should ask whether to customize rubric criteria. If the owner says no, P2P keeps all domain criteria enabled. If the owner says yes, P2P asks an enable/disable confirmation for each suggested criterion and saves the selected enabled flags into .p2p/project/rubrics.yml. Scripted init with a project name remains non-interactive and uses the full default rubric for the selected domain.

## Acceptance Criteria

- Interactive p2p init asks whether to customize rubric criteria.
- If customization is skipped, all criteria remain enabled.
- If customization is accepted, each criterion can be enabled or disabled.
- .p2p/project/rubrics.yml stores enabled false for disabled criteria.
- p2p assess maturity refresh evaluates only enabled criteria.
- Non-interactive p2p init behavior remains scriptable and unchanged except for domain defaults.

## Decision

Pending.

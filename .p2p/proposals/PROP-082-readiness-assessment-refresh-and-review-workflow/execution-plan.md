# Execution Plan - PROP-082

## Phase 1 - Command Semantics

Define exact semantics for:

```text
init
refresh
assess
review
resolve-gate
import
override
```

Document which commands modify computed readiness and which commands only
display or synchronize snapshots.

## Phase 2 - Schema

Define readiness assessment schema with:

- profile id/version;
- computed score/label;
- confidence and confidence reasons;
- criterion scores;
- criterion evidence;
- failed gates;
- missing items;
- suggested next actions;
- assessment source;
- actor/reviewer;
- timestamp;
- reason/notes.

## Phase 3 - CLI

Implement candidate commands:

```bash
p2p proposal readiness assess PROP-XXX
p2p proposal readiness review PROP-XXX --by owner --reason "..."
p2p proposal readiness resolve-gate PROP-XXX owner_questions_resolution --reason "..."
p2p proposal readiness import PROP-XXX assessment.yml
```

## Phase 4 - Validation

Extend `p2p validate` to detect malformed assessment records, invalid criterion
keys, invalid score ranges, inconsistent failed gates, and missing actor/reason
where required.

## Phase 5 - MCP Parity

Expose equivalent MCP tools over shared core behavior after CLI semantics are
stable:

```text
p2p_proposal_readiness_assess
p2p_proposal_readiness_review
p2p_proposal_readiness_resolve_gate
p2p_proposal_readiness_import
```

## Verification

- CLI tests for assessment updates.
- CLI tests for gate resolution.
- Import schema validation tests.
- Validation tests for malformed readiness.
- Regression tests preserving owner override semantics.
- MCP parity tests once tools are exposed.


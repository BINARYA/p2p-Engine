# Design - PROP-095 Project Runtime Contract Update Lifecycle

## Overview

PROP-095 extends the existing PROP-084 runtime contract subsystem with an
explicit two-phase update lifecycle:

```text
p2p runtime contract preview
p2p runtime contract apply
```

The design keeps runtime contract update logic in core/service modules. CLI code
registers commands, parses options, and renders human/JSON output. Storage facade
code delegates to services.

## Key Decisions

### D001 - Keep Preview And Apply Separate

`preview` is read-only and available to agents and non-owner collaborators.
`apply` is the only mutating command and repeats all checks on current state.

Rationale: a preview token can be passed from an agent to an owner, but the token
must never authorize the actor.

Satisfies: R001-R007, R032-R038, R045-R051.

### D002 - Add Update Models To Runtime Contract Core

Extend `src/p2p_engine/core/runtime_contract.py` with typed records for:

- proposed contract input;
- setup-guide update state;
- impact labels;
- release availability;
- preview result;
- apply result;
- expected-state token payload;
- blocked diagnostic result.

Use stable string constants for public states and labels.

Satisfies: R008-R031, R052-R073, N005.

### D003 - Implement Runtime Update Workflow In Service Layer

Add cohesive workflow methods to `RuntimeContractService` or a closely owned
runtime contract update service in `src/p2p_engine/services/runtime_contract.py`.

Responsibilities:

- parse and validate proposed values;
- classify current contract trust state;
- classify setup-guide state;
- compare ranges;
- calculate impact labels;
- build token input;
- render preview;
- apply coordinated writes.

Rationale: this logic is shared by CLI, tests, and future adapters. It does not
belong in Typer command handlers or `P2PWorkspace`.

Satisfies: N001-N002.

### D004 - Use Supported Range Grammar For Deterministic Comparison

The update lifecycle accepts only these forms for deterministic impact
classification:

```text
==VERSION
>=LOWER,<UPPER
```

The existing `packaging` version semantics remain the source for version
validation. Range comparison should be implemented as a small internal
normalized range model:

- exact version;
- bounded lower-inclusive, upper-exclusive interval.

Set relationships are derived from normalized intervals, not string equality.

Satisfies: R010-R012, R023-R031.

### D005 - Token Is Stateless Concurrency Evidence

The expected-state token is a deterministic digest over a versioned canonical
payload. The payload should include:

- operation identifier;
- token format version;
- current runtime contract bytes or digest;
- setup-guide state and bytes/digest;
- required-contract marker state;
- managed marker state;
- proposed normalized values;
- reason;
- optional decision reference;
- impact algorithm version;
- impact labels.

Use canonical JSON or another deterministic serialization. Do not persist token
state.

Satisfies: R045-R051.

### D006 - Setup Guide Is Derived And Protected

Use the existing `RUNTIME_SETUP_GUIDE_MARKER` to distinguish managed setup
guides from human-owned files.

States:

- `missing`;
- `managed_aligned`;
- `managed_drifted`;
- `unmanaged`.

Managed-guide drift can be replaced during a true contract update. Unmanaged
guide always blocks apply before mutation.

Satisfies: R052-R059.

### D007 - Contract-Last Coordinated Write

Apply prepares all content before writing. It writes or replaces the managed
setup guide first and the normative runtime contract last.

If the active runtime becomes incompatible after the new contract is in place,
the write gate is considered active immediately. No further governed mutation is
allowed inside the same command after the contract replacement.

Satisfies: R060-R069.

### D008 - MCP Mutation Deferred

No MCP mutation tool is introduced. Existing read-only MCP or context tools may
continue to observe proposal/runtime state. A future MCP mutation surface must
be consent-gated separately.

Satisfies: public surface requirements and out-of-scope constraints.

## Components

### Core Runtime Contract Module

File: `src/p2p_engine/core/runtime_contract.py`

Add stable constants and dataclasses for update lifecycle payloads.

### Runtime Contract Service

File: `src/p2p_engine/services/runtime_contract.py`

Add methods such as:

```python
preview_update(...)
apply_update(...)
```

or an internal helper class owned by the module. Keep compatibility with existing
`status`, `validation_findings`, `write_preflight`, and setup-guide rendering.

### CLI Runtime Commands

File: `src/p2p_engine/cli_commands/runtime.py`

Add a nested `contract` command group with `preview` and `apply` subcommands.
Presentation responsibilities:

- parse options;
- call facade/service;
- render text or JSON;
- fail with stable messages.

### P2PWorkspace Facade

File: `src/p2p_engine/storage/filesystem.py`

Add delegation methods only. Do not place domain logic here.

### Validation And Write Gate Integration

Existing `p2p runtime status` and `p2p validate` remain diagnostic surfaces.
Apply uses a narrow exception for valid old contracts whose active runtime is
outside range, but it must not weaken generic governed-write preflight.

## Error Handling

Use structured result statuses for handled blockers:

- `invalid_proposed_contract`;
- `untrusted_current_contract`;
- `unmanaged_setup_guide`;
- `stale_preview`;
- `authority_required`;
- `confirmation_required`;
- `reason_required`;
- `no_change`;
- `updated`;
- `partial_failure`.

Errors before mutation must report `files_changed: []`.

## JSON Output

Preview JSON should include at least:

- `status`;
- `current_state`;
- `current_contract`;
- `proposed_contract`;
- `proposal_valid`;
- `impact_labels`;
- `active_runtime`;
- `active_runtime_satisfies_proposed_range`;
- `setup_guide`;
- `release_availability`;
- `authority`;
- `reason_required`;
- `files_planned`;
- `expected_state_token`;
- `apply_allowed`;
- `blocked_reason`.

Apply JSON should include at least:

- `status`;
- `files_changed`;
- `final_contract`;
- `final_compatibility`;
- `active_runtime_compatible_after_update`;
- `subsequent_governed_writes_blocked`;
- `post_update_mutations_performed`;
- `full_validation_deferred`;
- `release_availability`;
- `audit_mode`;
- `reason_persisted`;
- `blocked_reason` or validation findings when applicable.

## Compatibility

- Existing runtime contracts remain valid.
- Existing `p2p runtime status` output remains compatible.
- Existing `p2p validate` findings remain compatible.
- Legacy undeclared projects remain warning-only until an adoption workflow is
  implemented separately.

## Alternatives

- Single `update` command: rejected because it weakens agent-safe preview.
- Automatic runtime installation: rejected because environment mutation is out
  of scope.
- Persisted single-use tokens: rejected because preview must remain read-only.
- Mandatory P2P decision link: rejected for first implementation because owner
  authority plus confirmation is sufficient for this technical operation.

## Test Strategy

- Unit tests for range normalization, set comparison, impact labels, token
  determinism, and token mismatch.
- Service tests for preview/apply success and all blockers.
- Filesystem tests for write order and partial failure behavior where feasible.
- CLI tests for command names, options, JSON fields, text output, exit behavior,
  and no-mutation blockers.
- Validation tests to ensure existing runtime status/validate behavior remains
  compatible.

Focused commands:

```bash
.venv/bin/pytest tests/test_runtime_contract_service.py
.venv/bin/pytest tests/test_cli.py -k "runtime"
```

Public/full validation before completion:

```bash
./scripts/test-public.sh
./scripts/test-full.sh
```

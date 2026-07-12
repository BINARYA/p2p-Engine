# Design - PROP-097 Runtime Contract Adoption For Legacy Projects

## Overview

PROP-097 adds a narrow adoption primitive:

```text
p2p runtime contract adopt
```

The command exists for pre-contract projects whose runtime status is
`legacy_undeclared`. It converts that legacy state into an explicit runtime
contract using owner-confirmed values. It is not an installer, updater,
recovery tool, or contract migration mechanism.

## Key Decisions

### D001 - Single Confirmed Adoption Command

Use one command, `p2p runtime contract adopt`, rather than a preview/apply pair.
Without `--confirm`, the command returns a blocked diagnostic and performs no
mutation.

Rationale: adoption is a one-time legacy transition with fewer moving parts than
the existing contract update lifecycle. Explicit confirmation keeps mutation
intent clear without introducing another token lifecycle.

Satisfies: R001-R006, R015-R018.

### D002 - Adopt Only From `legacy_undeclared`

The service checks current runtime status before validating writes. Only
`legacy_undeclared` is eligible. Existing valid contracts remain under PROP-095;
missing required contracts require recovery; invalid and unsupported contracts
require repair or migration.

Satisfies: R007-R009.

### D003 - Reuse Runtime Contract Validation

Adoption reuses the same proposed contract validation and supported range
grammar used by runtime contract update:

```text
==VERSION
>=LOWER,<UPPER
```

The adopted `recommended` version must satisfy the adopted `requires` range.

Satisfies: R010-R014, N004.

### D004 - Protect Human-Owned Setup Guides

Use the existing stable setup-guide marker to decide whether `P2P-SETUP.md` is
managed. Missing guides are generated. Managed guides are regenerated. Unmanaged
guides block adoption before any file is written.

Satisfies: R019-R022.

### D005 - Write Contract Before Required Marker

Successful adoption writes the runtime contract and setup guide before setting
`runtime_contract.required: true` in `.p2p/project.yml`.

Rationale: the required marker should not be activated before the contract it
requires exists. The project manifest is updated last among `.p2p` state.

Satisfies: R023-R028.

### D006 - MCP Mutation Deferred

No MCP mutation tool is added. The CLI command is the public write primitive for
this feature. Future MCP parity would need a consent-gated design.

Satisfies: public surface requirements.

## Components

### Core Runtime Contract Module

File: `src/p2p_engine/core/runtime_contract.py`

Add adoption status/blocker constants and a result dataclass with a `to_dict`
method. Reuse `RuntimeContractUpdateAuthority` for authority reporting.

### Runtime Contract Service

File: `src/p2p_engine/services/runtime_contract.py`

Add:

```python
adopt_contract(
    *,
    requires: str,
    recommended: str,
    confirm: bool = False,
    actor: str = "owner",
) -> RuntimeContractAdoptionResult
```

Responsibilities:

- read current runtime status;
- validate proposed values;
- resolve owner authority;
- classify setup-guide state;
- block unsupported states;
- write `runtime.yml`, managed `P2P-SETUP.md`, and project marker on success.

### P2PWorkspace Facade

File: `src/p2p_engine/storage/filesystem.py`

Add a delegating `runtime_contract_adopt(...)` method. Do not add domain logic.

### CLI Runtime Commands

File: `src/p2p_engine/cli_commands/runtime.py`

Add `p2p runtime contract adopt` under the existing `runtime contract` command
group. Reuse the existing runtime contract payload renderer where practical.

## Result Shape

Result statuses:

- `adopted`;
- `blocked`;
- `partial_failure`.

Stable blockers:

- `invalid_proposed_contract`;
- `unsupported_current_state`;
- `owner_authority_required`;
- `confirmation_required`;
- `unmanaged_setup_guide`.

JSON output includes:

```json
{
  "status": "adopted",
  "current_state": "legacy_undeclared",
  "proposed_contract": {
    "requires": "==0.1.9",
    "recommended": "0.1.9"
  },
  "files_changed": [
    ".p2p/project/runtime.yml",
    "P2P-SETUP.md",
    ".p2p/project.yml"
  ],
  "blocked_reason": "",
  "message": "Runtime contract adopted.",
  "setup_guide": {
    "path": "P2P-SETUP.md",
    "state": "missing",
    "planned_action": "generate"
  },
  "authority": {
    "apply_authorized": true,
    "status": "authorized"
  }
}
```

## Failure Semantics

- Blocked results return `files_changed: []`.
- If writing fails after one file has changed, return `partial_failure` with the
  changed files listed.
- Do not attempt rollback in this feature.
- Do not write the project marker until after the runtime contract and setup
  guide have been written.

## Compatibility

- Existing runtime status and validation behavior remains unchanged for all
  states before adoption.
- Existing runtime contract update preview/apply behavior is unchanged.
- Existing new-project initialization behavior is unchanged.

## Tests

Focused service tests:

- successful legacy adoption;
- blocked without confirmation;
- blocked for non-owner actor;
- blocked unmanaged setup guide;
- blocked non-legacy state;
- invalid proposed contract.

CLI tests:

- JSON success shape;
- text blocked output without confirmation or unmanaged setup guide.

Suggested validation:

```bash
.venv/bin/pytest tests/test_runtime_contract_service.py
.venv/bin/pytest tests/test_cli.py -k "runtime"
./scripts/test-full.sh
```

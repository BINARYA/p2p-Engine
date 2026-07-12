# Tasks - PROP-097 Runtime Contract Adoption For Legacy Projects

## Status

`implemented`

## Implementation Rules

- Keep adoption domain logic in `RuntimeContractService`.
- Keep `P2PWorkspace` as a facade only.
- Keep CLI code as presentation and option parsing only.
- Do not add runtime installation, package resolution, network lookup, or
  environment mutation.
- Do not add MCP mutation in this feature.
- Do not overwrite unmanaged `P2P-SETUP.md`.
- Run focused tests before broad validation.

## Tasks

- [x] T001. Re-read accepted `PROP-097`, this local feature spec, and quality
      policies before coding.
      - Covers: all requirements.

- [x] T002. Inspect current runtime contract service, CLI runtime command,
      `P2PWorkspace` facade, validation behavior, and runtime tests.
      - Covers: N001-N006.
      - Expected files:
        `src/p2p_engine/core/runtime_contract.py`,
        `src/p2p_engine/services/runtime_contract.py`,
        `src/p2p_engine/cli_commands/runtime.py`,
        `src/p2p_engine/storage/filesystem.py`,
        `tests/test_runtime_contract_service.py`,
        `tests/test_cli.py`.

- [x] T003. Add core adoption constants and result dataclass.
      - Covers: R029-R032.
      - Test layer: service/CLI JSON shape.

- [x] T004. Implement `RuntimeContractService.adopt_contract`.
      - Covers: R007-R028, N001.
      - Tests: success and handled blockers.

- [x] T005. Add `P2PWorkspace.runtime_contract_adopt` delegation.
      - Covers: N002.

- [x] T006. Add `p2p runtime contract adopt` CLI command.
      - Covers: R001-R006, N003.
      - Tests: command availability, JSON output, text output.

- [x] T007. Add service tests for adoption lifecycle.
      - Covers: AC001-AC007.
      - Suggested command:
        `.venv/bin/pytest tests/test_runtime_contract_service.py`.

- [x] T008. Add CLI tests for adoption.
      - Covers: CLI public contract and AC001-AC007.
      - Suggested command:
        `.venv/bin/pytest tests/test_cli.py -k "runtime"`.

- [x] T009. Run focused validation.
      - Required:
        `.venv/bin/pytest tests/test_runtime_contract_service.py`
        `.venv/bin/pytest tests/test_cli.py -k "runtime"`.

- [x] T010. Adopt this repository's runtime contract through the new command.
      - Covers: AC008.
      - Required:
        `.venv/bin/p2p runtime contract adopt --requires "==0.1.9" --recommended "0.1.9" --confirm --actor owner`.

- [x] T011. Run project validation after adoption.
      - Required:
        `.venv/bin/p2p runtime status`
        `.venv/bin/p2p validate`

- [x] T012. Run broad validation before declaring complete.
      - Required unless explicitly deferred:
        `./scripts/test-full.sh`.

- [x] T013. Final review: confirm no MCP mutation, no environment mutation, no
      unmanaged setup guide overwrite, and no manual `.p2p` edit was introduced.

## Validation Evidence

- `.venv/bin/pytest tests/test_runtime_contract_service.py` -> 29 passed
- `.venv/bin/pytest tests/test_cli.py -k runtime` -> 8 passed
- `.venv/bin/p2p runtime status` -> `compatible`
- `.venv/bin/p2p validate` -> 0 errors, 0 warnings, 0 infos
- `./scripts/test-full.sh` -> 621 passed

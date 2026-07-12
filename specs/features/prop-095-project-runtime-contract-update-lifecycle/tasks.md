# Tasks - PROP-095 Project Runtime Contract Update Lifecycle

## Status

`implemented`

## Implementation Rules

- Keep runtime update domain logic out of CLI presentation and `P2PWorkspace`.
- Do not add runtime installation, package resolution, network lookup, or
  environment mutation.
- Do not add MCP mutation in this feature.
- Do not replace unmanaged `P2P-SETUP.md`.
- Preserve existing `p2p runtime status` and `p2p validate` behavior.
- Write `.p2p/project/runtime.yml` last during apply.
- Run focused tests before broad validation.

## Tasks

- [x] T001. Re-read accepted `PROP-095`, this local feature spec, `PROP-084`
      runtime contract implementation, and quality policies before coding.
      - Covers: all requirements.
      - Output: implementation notes in final summary, not `.p2p`.

- [x] T002. Inspect current runtime contract service, CLI runtime command,
      `P2PWorkspace` facade, validation service, and runtime tests before
      editing.
      - Covers: N001-N006.
      - Expected files:
        `src/p2p_engine/core/runtime_contract.py`,
        `src/p2p_engine/services/runtime_contract.py`,
        `src/p2p_engine/cli_commands/runtime.py`,
        `src/p2p_engine/storage/filesystem.py`,
        `src/p2p_engine/services/validation.py`,
        `tests/test_runtime_contract_service.py`,
        `tests/test_cli.py`.

- [x] T003. Add core runtime update constants and dataclasses for proposed
      contract input, impact labels, setup-guide state, release availability,
      preview result, apply result, and token payload.
      - Covers: R008-R031, R052-R073, N005.
      - Test layer: unit/service.

- [x] T004. Implement proposed contract validation and supported update range
      normalization for `==VERSION` and `>=LOWER,<UPPER`.
      - Covers: R008-R015.
      - Tests: exact range, bounded range, invalid syntax, invalid version,
        recommended out of range.

- [x] T005. Implement set-based range comparison and impact classification.
      - Covers: R023-R031.
      - Tests: identical range, widening, tightening, partial overlap, disjoint
        range, runtime line change, active runtime excluded.

- [x] T006. Implement setup-guide state classification and planned actions.
      - Covers: R052-R059.
      - Tests: missing, managed aligned, managed drifted, unmanaged, drift-only
        no-op.

- [x] T007. Implement deterministic stateless expected-state token generation.
      - Covers: R045-R051.
      - Tests: deterministic token, token changes when protected state changes,
        token changes when proposed values/reason/decision changes, no token for
        blockers and no-op.

- [x] T008. Implement read-only preview workflow in the runtime contract service.
      - Covers: R001-R003, R016-R022, R032-R034, R070-R073.
      - Tests: applicable preview, non-owner preview, untrusted current states,
        release availability `unverified`, no filesystem mutations.

- [x] T009. Implement apply workflow in the runtime contract service.
      - Covers: R004-R005, R035-R044, R049-R069.
      - Tests: success, missing authority, missing confirm, missing reason,
        stale token, unmanaged setup guide, invalid proposal, untrusted current
        state.

- [x] T010. Implement coordinated write behavior with setup-guide replacement
      before runtime contract replacement.
      - Covers: R060-R069.
      - Tests: write order, setup guide failure leaves runtime unchanged,
        runtime replacement failure reports partial failure, no post-update
        governed mutation when active runtime becomes incompatible.

- [x] T011. Add `P2PWorkspace` facade delegations for runtime contract preview
      and apply.
      - Covers: N002.
      - Tests: facade delegates without domain logic where local pattern exists.

- [x] T012. Add `p2p runtime contract preview` and
      `p2p runtime contract apply` CLI commands.
      - Covers: R001-R007.
      - Tests: command availability, option parsing, text output, JSON output,
        stable failure fields.

- [x] T013. Preserve existing `p2p runtime status` and validation behavior.
      - Covers: compatibility requirements.
      - Tests: existing runtime status and validation tests still pass.

- [x] T014. Update docs and agent guidance for preview/apply, token semantics,
      unmanaged guide blockers, no-install boundary, and collaborator next
      action.
      - Covers: public surface and agent-facing behavior.
      - Expected files: `docs/CLI-GUIDE.md`, `docs/AGENT-INTEGRATION.md`, any
        generated agent-template source if needed.

- [x] T015. Add service regression tests for all accepted Q005-Q016 edge cases.
      - Covers: full proposal decision set.
      - Suggested command:
        `.venv/bin/pytest tests/test_runtime_contract_service.py`.

- [x] T016. Add CLI regression tests for preview/apply text and JSON output.
      - Covers: CLI public contract.
      - Suggested command:
        `.venv/bin/pytest tests/test_cli.py -k "runtime and contract"`.

- [x] T017. Run focused validation.
      - Required:
        `.venv/bin/pytest tests/test_runtime_contract_service.py`
        `.venv/bin/pytest tests/test_cli.py -k "runtime"`

- [x] T018. Run public and full validation before declaring complete.
      - Required unless explicitly deferred:
        `./scripts/test-public.sh`
        `./scripts/test-full.sh`

- [x] T019. Final review: confirm no MCP mutation was added, no environment
      mutation was introduced, unmanaged setup guide is protected, and runtime
      contract writes happen last.
      - Covers: out-of-scope and safety rules.

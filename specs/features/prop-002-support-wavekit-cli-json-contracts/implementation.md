# Implementation - Support WaveKit CLI JSON Contracts

## Status

Implemented for P2P Engine `0.4.10`.

The feature delivers the WaveKit worker boundary as an allowlisted CLI JSON
contract. MCP stdio remains protocol-native for local agents and is not wrapped
in the `p2p-cli/v1` envelope.

## Source Evidence

- `src/p2p_engine/cli_contract.py`: JSON envelope, parser normalization and
  stable error codes.
- `src/p2p_engine/cli.py`: `p2p init --format json --operation-key`,
  `p2p version --format json` and command registration.
- `src/p2p_engine/cli_commands/project_ops.py`: project snapshot and existing
  project/vertical JSON reads used by WaveKit.
- `src/p2p_engine/cli_commands/proposal_core.py`: proposal list/show/create
  and update JSON surfaces.
- `src/p2p_engine/cli_commands/proposal_contributions.py`: typed contribution
  add/list JSON surfaces.
- `src/p2p_engine/services/mutation_receipts.py`: WaveKit operation-key
  validation, replay/status handling and receipt validation for init,
  proposal and contribution mutations.
- `src/p2p_engine/services/project_snapshot.py`: bounded project overview read
  model for Angular/WaveKit.
- `src/p2p_engine/mcp/catalog/` and `src/p2p_engine/mcp/handlers/`: MCP
  descriptions and payload parity without using the CLI envelope.
- `src/p2p_engine/services/agent_capabilities.py` and
  `src/p2p_engine/services/agent_templates.py`: generated agent guidance for
  standalone use and the WaveKit worker boundary.
- `README.md`, `docs/CLI-CONTRACT.md`, `docs/CLI-GUIDE.md`,
  `docs/INSTALL.md`, `docs/MCP.md`, `docs/WORKSPACE-SCHEMA.md` and
  `CHANGELOG.md`: public contract and release documentation.

## Regression Found During Verification

Installed-wheel smoke initially found that:

```text
p2p mutation status --operation-key wavekit:<uuid> --format json
```

failed for an `init` receipt created with all generated agent adapter files.
The receipt validator allowed `.p2p/`, `.agents/`, `AGENTS.md`,
`P2P-SETUP.md` and `.gitignore`, but did not allow current generated adapter
files such as:

- `.cursor/rules/p2p.mdc`
- `.github/copilot-instructions.md`
- `CLAUDE.md`
- `GEMINI.md`

The fix is intentionally scoped to `project.init` receipt postconditions. Other
receipt-backed mutations still require canonical `.p2p/` project-state paths.

Regression coverage:

- `tests/test_project_initialization_receipts.py::test_init_json_all_agent_receipt_status_accepts_generated_adapter_files`

## Validation Evidence

Focused WaveKit contract suite:

```bash
.venv/bin/python -m pytest tests/test_cli_contract.py tests/test_mutation_receipts.py tests/test_project_initialization_receipts.py tests/test_project_initialization_service.py tests/test_project_snapshot_service.py tests/test_proposal_read_contract.py tests/test_proposal_write_contract.py tests/test_proposal_contribution_contract.py tests/test_cli_project_readiness.py tests/test_project_questions_service.py tests/test_proposal_questions_service.py tests/test_mcp_registry.py tests/test_mcp_project_handler.py tests/test_mcp_proposal_handler.py tests/test_mcp.py tests/test_version_consistency.py tests/test_current_only_surface.py tests/test_release_artifacts.py tests/test_public_surface_inventory.py -q
```

Result:

```text
211 passed in 51.69s
```

Public CLI/MCP contract suite:

```bash
./scripts/test-public.sh -q
```

Result:

```text
280 passed, 1196 deselected in 125.36s
```

Release artifacts:

```bash
.venv/bin/python -m build --no-isolation
.venv/bin/python scripts/verify-release-artifacts.py --dist dist --version 0.4.10
```

Result:

```text
Successfully built p2p_engine-0.4.10.tar.gz and p2p_engine-0.4.10-py3-none-any.whl
release artifacts verified: version=0.4.10 wheel_files=265 sdist_files=580
```

Installed-wheel smoke used `dist/p2p_engine-0.4.10-py3-none-any.whl`
installed under `/tmp/p2p_engine_0_4_10_smoke` and verified:

- import path resolves to `/tmp/p2p_engine_0_4_10_smoke/p2p_engine`;
- imported version is `0.4.10`;
- `p2p version --format json` reports engine version `0.4.10`;
- `p2p init "Wheel Smoke Project" --agent all --vertical software_project
  --format json --operation-key wavekit:<uuid>` succeeds;
- `p2p mutation status --operation-key wavekit:<uuid> --format json` reports
  `state: applied` and `postconditions_match: true`;
- `p2p project snapshot --format json` returns a compatible runtime,
  workspace schema `3`, active vertical `software_project`, readiness and
  section summaries;
- `p2p proposal list --format json` returns the typed empty proposal list.

Full suite:

```bash
./scripts/test-full.sh -q
```

Result:

```text
1477 passed in 306.81s (0:05:06)
```

## Residual Risks

- Contribution review/promote/reject is intentionally unsupported in `0.4.10`.
  The CLI exposes `review_capability.supported = false`; WaveKit must not store
  a PostgreSQL-only shadow review state for project-memory comments.
- Remote registry network behavior is not exercised by the installed-wheel
  smoke because no external registry is available in this repository. Local
  registry/vertical behavior remains covered by existing tests.
- MCP stdio remains an agent tool surface. WaveKit's deterministic worker must
  continue to use the CLI JSON commands plus operation-key receipts for retry
  and recovery.


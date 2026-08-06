# Binding Report - PROP-002 Support WaveKit CLI JSON Contracts

## Inputs

- Accepted P2P proposal: `PROP-002`, "Support WaveKit CLI JSON contracts".
- Owner decision: accepted by `mrjungle` on 2026-08-06.
- Decision event: `PDE-18fc8d4f7b74828934d28f6f`.
- Target release: P2P Engine `0.4.10`.
- Current implementation baseline: P2P Engine `0.4.9`, workspace schema `3`,
  vertical pack schema `2`, portable package format `1`, CLI envelope
  `p2p-cli/v1`.
- Downstream driver: WaveKit needs Django worker access to P2P project memory
  only through allowlisted CLI JSON commands. WaveKit must not parse `.p2p`,
  parse human text, call P2P Python internals, or use local MCP stdio as the
  deterministic server-worker transport.

## Owner Decisions Bound

- `C001`: preferred boundary is WaveKit worker invoking P2P CLI JSON.
- `C002`: local MCP stdio is rejected for the deterministic WaveKit worker.
- `C003`: parsing human CLI text is rejected.
- `C004`: adding JSON indiscriminately to the whole CLI is rejected.
- `C005`: read-only-first phasing is viable internally, but the accepted
  feature must specify the full P0 contract.
- `C011`: deliver the full P0 WaveKit CLI JSON contract in one P2P release.
- `C012`: WaveKit-facing writes standardize on
  `--operation-key wavekit:<uuid>`; `--idempotency-key` is only a compatibility
  alias where already present.
- `C013`: `p2p project snapshot --format json` is rich but summarized so the
  Angular overview can render from one CLI read.
- `C014`: `p2p init` becomes durable and idempotent with operation key,
  receipt, safe replay and conflict handling.
- `C015`: project chat and mediator conversations stay in WaveKit PostgreSQL,
  while structured proposal-bound contributions are P2P project memory.

## Existing Implementation Evidence

- `src/p2p_engine/cli_contract.py` already owns the `p2p-cli/v1` envelope,
  parser normalization and exit-code classes introduced by `PROP-107`.
- `src/p2p_engine/core/mutation_receipts.py` and
  `src/p2p_engine/services/mutation_receipts.py` already provide receipt
  models and status behavior for previous idempotent vertical mutations.
- `src/p2p_engine/cli.py` owns `p2p init`; it is currently text-oriented and
  has no WaveKit operation-key receipt boundary.
- `src/p2p_engine/services/project_initialization.py` owns initialization
  behavior and writes missing bootstrap files.
- `src/p2p_engine/cli_commands/project_ops.py` owns project read commands and
  some JSON outputs, but there is no single WaveKit project snapshot command.
- `src/p2p_engine/cli_commands/proposal_core.py` owns proposal
  create/update/list/show; these commands are currently text-oriented.
- `src/p2p_engine/cli_commands/proposal_contributions.py` owns contribution
  add/list; it currently supports typed contributions but no JSON, filters,
  operation key, receipt or review-state primitive.
- `tests/test_cli_contract.py`, `tests/test_mutation_receipts.py`,
  `tests/test_project_initialization_service.py`, `tests/test_cli.py`,
  `tests/test_proposal_review_view_service.py`, `tests/test_mcp_proposal_handler.py`
  and `tests/test_version_consistency.py` are expected validation anchors.

## Steering Alignment

- P2P Engine remains responsible for interpreting and mutating project memory.
- WaveKit remains a separate collaborative server and must not force P2P Engine
  to become a multi-user server.
- CLI JSON is the public machine contract for the WaveKit worker.
- MCP stdio remains protocol-native for agents and is not wrapped in
  `p2p-cli/v1`.
- Repository-local implementation specs stay under `specs/features/`; accepted
  P2P project memory does not prove implementation.

## Feature Spec Created

`specs/features/prop-002-support-wavekit-cli-json-contracts/`

- `requirements.md`
- `design.md`
- `tasks.md`
- `implementation.md`

## Readiness Notes

The proposal readiness score remained weak because the current readiness
profile does not infer artifact strength from contribution records. Before
acceptance, artifact states were marked satisfied for proposal, exploration,
open questions, clarifications, findings, impact map, vertical coverage and
readiness. There were no failed gates and no blocking owner questions.

Residual risk is implementation breadth: the feature touches CLI commands,
receipt persistence, project read models, proposal contribution semantics,
MCP/agent guidance, tests and release documentation.

## Requirement-To-Evidence Matrix

| Requirements | Expected behavior | Planned evidence | Status |
| --- | --- | --- | --- |
| R001-R007 | WaveKit command set is explicit and JSON remains `p2p-cli/v1` | CLI inventory and contract tests | implemented through T024 |
| R008-R014 | Project snapshot read model supports Angular overview | service and CLI golden tests | implemented |
| R015-R024 | `p2p init` is idempotent with operation-key receipts | service, CLI, replay and fault tests | implemented |
| R025-R034 | Proposal list/show/create/update expose JSON and safe writes | proposal service and CLI tests | implemented |
| R035-R044 | Contribution add/list/review expose typed JSON memory | contribution model, service and CLI tests | implemented; review intentionally unsupported |
| R045-R049 | Mutation status and error handling work for WaveKit keys | receipt/status and parser error tests | implemented |
| R050-R055 | Docs, generated guidance, MCP descriptions and version references converge | docs, template and version-consistency tests | implemented through T033 |

## Implementation Boundary

Proceed in dependency order:

1. inventory and freeze the WaveKit-facing CLI contract;
2. implement snapshot read model;
3. make init idempotent;
4. add proposal read JSON;
5. add proposal write receipts;
6. add contribution JSON and review semantics;
7. normalize status and errors for `wavekit:<uuid>`;
8. update MCP descriptions, generated skills and maintained docs;
9. bump the implementation release references to `0.4.10`;
10. validate focused tests, public CLI/MCP tests, wheel smoke and full suite.

No WaveKit implementation is included in this repository feature.

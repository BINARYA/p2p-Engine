# Implementation Inventory - Receipt-Backed Proposal Readiness

## Runtime And Domain

| Requirements | Source |
| --- | --- |
| R001-R013 | `src/p2p_engine/services/readiness.py` |
| R014-R019 | `src/p2p_engine/services/readiness.py`, `src/p2p_engine/services/proposal_read_contract.py` |
| R020-R030 | `src/p2p_engine/storage/filesystem.py`, `src/p2p_engine/services/mutation_receipts.py`, existing `src/p2p_engine/services/workspace_transactions.py` |
| R031-R039 | `src/p2p_engine/cli_commands/proposal_readiness.py`, existing `src/p2p_engine/cli_contract.py` |
| R040-R043 | `src/p2p_engine/mcp/handlers/proposals.py`, `src/p2p_engine/mcp/catalog/proposals.py` |
| R044-R047 | Existing project snapshot/progress/readiness services; regression-only coverage |
| R048-R050 | Agent templates/capabilities and maintained CLI/MCP documentation |
| R051-R052 | Package/version surfaces, install examples, changelog and consistency tests |

## Verification

| Concern | Tests |
| --- | --- |
| Pure plan, source inventory, fingerprint, freshness | `tests/test_proposal_readiness_write_contract.py`, `tests/test_readiness_service.py`, `tests/test_proposal_read_contract.py` |
| Receipt, replay, conflicts, drift, rollback, recovery, concurrency | `tests/test_proposal_readiness_write_contract.py`, `tests/test_mutation_receipts.py`, `tests/test_mutation_preview_and_writer.py` |
| CLI envelope and golden payload | `tests/test_proposal_readiness_write_contract.py`, `tests/fixtures/cli_contract/proposal-readiness-assess-v1.json` |
| MCP semantic parity and catalog | `tests/test_proposal_readiness_write_contract.py`, `tests/test_mcp.py`, `tests/test_mcp_registry.py` |
| Agent guidance | `tests/test_agent_instructions_service.py` |
| Project-readiness boundary | `tests/test_proposal_readiness_write_contract.py`, `tests/test_project_snapshot_service.py`, `tests/test_project_progress_service.py`, `tests/test_project_verticals.py` |
| Release convergence | `tests/test_version_consistency.py`, public and installed-wheel suites |

## Documentation

- `docs/CLI-CONTRACT.md`
- `docs/CLI-GUIDE.md`
- `docs/MCP.md`
- `docs/development/cli-primitive-inventory.md`
- `README.md`
- `CHANGELOG.md`


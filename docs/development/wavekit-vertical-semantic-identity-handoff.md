# WaveKit handoff: vertical semantic identity v1

This document is an implementation inventory, not evidence that WaveKit has
adopted the contract. WaveKit requires a separate OpenSpec change after the
P2P Engine 0.6.8 release containing `p2p-vertical-semantic-checksum/v1` and
`p2p-vertical-portable-provenance/v1` is published.

The downstream change must cover:

- Django release, recommendation and dependency models with contract,
  algorithm and digest constraints;
- additive migrations/backfill that interpret existing registry-v2 naked
  semantic checksums as v1/SHA-256 without altering immutable release meaning;
- uniqueness and immutability checks over the complete identity;
- OpenAPI provider responses that retain required `semantic_checksum` and add
  optional `semantic_identity` consistently;
- capability output with optional `semantic_checksum_contracts`, never added
  to registry-v2 `required_fields`;
- publication request and receipt validation that rejects contradictory dual
  forms and unknown contracts before persistence;
- worker SQL projections, serializers, caches and rebuild paths using all
  identity components while keeping artifact SHA-256 columns separate;
- official seed verticals and test fixtures with scalar-only legacy, valid
  dual-shape v1, malformed, non-SHA256 v1, unknown-contract and conflicting
  examples;
- worker installation/convergence pins to the published P2P Engine wheel and
  its `current_contract_versions()` entry;
- HTTP and MCP response parity, including stable fail-closed error mapping;
- migration, rollback and recovery tests proving existing published releases
  are not reinterpreted or rewritten under another checksum contract.

WaveKit must not copy P2P Engine's semantic projection or calculate the digest
independently. It consumes the typed P2P result and stores/transports its
identity. A future v2 is a separate capability and compatibility decision; it
does not change registry protocol v2 or an existing vertical's semantic
version by implication.

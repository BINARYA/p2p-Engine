# Design - Converge Project Structure Surfaces

## Requirements Covered

- R001-R017
- N001-N005
- AC001-AC010

## Decision Summary

Use a generated inventory and test matrix as the release gate for coordinated
P1-P7, typed authority and registry-domain discovery. Each implementation
feature owns its behavior; this feature finds drift across CLI, MCP, generated
agent files, docs, bundled resources, fixtures, packaging and CI. It removes
residual current-runtime compatibility rather than adding adapters.

## Key Decisions

### D001 - Traceability Matrix Is Generated From Maintained Surfaces

The audit maps each public operation to CLI command, payload contract, MCP
decision, capability guidance, fixture and tests. The matrix is evidence, not a
new source of domain behavior.

### D002 - Installed Wheel Is A Required Test Subject

Source-tree success cannot prove packaged starters, vertical releases, schemas,
skills or MCP resources exist. Build one immutable wheel, install it in an
isolated environment and run contract/offline smoke against it.

### D003 - Historical Allowlist, No Blanket Search Exclusions

Obsolete-reference detection classifies valid changelog/release-history
occurrences separately from maintained guidance. Every allowlisted path and
pattern has a reason.

### D004 - MCP Parity Is Semantic

Not every CLI filesystem operation belongs in MCP. The audit requires shared
domain semantics where a tool exists and an explicit security/transport reason
where it does not. Missing parity cannot be accidental.

### D005 - Release Matrix Isolation

Each CI matrix job builds and tests its own artifact or consumes one immutable
artifact from a dedicated build job. Jobs never upload concurrently to the same
release asset name.

### D006 - Authority And Capability Are Release-Gate Dimensions

The convergence inventory includes each operation's governed capability,
AuthorityContext mode, subject/executor attribution, receipt evidence and MCP
policy. Generated surfaces must explain standalone local authority without
encoding WaveKit roles, and hosted fixtures must use neutral schema-4 project
authority identities rather than owner-shaped technical principals.

### D007 - Registry V2 Is Part Of The Installed Contract

The convergence inventory includes provider-neutral domain catalog commands,
domain-filtered release reads, MCP read parity and protocol-v1 rejection from
`extend-remote-registry-client-with-domain-discovery`. This validates the
client against a deterministic mock provider without making WaveKit source a
P2P build dependency.

## Artifacts

- CLI/MCP/capability traceability inventory.
- Sanitized P1-P7 JSON fixture bundle.
- Obsolete-reference allowlist with reasons.
- Installed-wheel validation report.
- Release note and version/schema convergence evidence.

## Alternatives Considered

- Rely on full pytest only: rejected because docs, skills and package resources
  can drift without failing domain tests.
- Keep compatibility aliases indefinitely: rejected by the current-only owner
  policy and because aliases preserve the conceptual overlap.
- Run this only after every future feature: rejected; P1-P7 need a concrete
  0.5.0 gate, while deferred merge/restore owns later convergence.

## Compatibility

The audit validates P2P Engine 0.5.0, workspace schema 4 and vertical schema 3.
It records old releases only as history and unsupported-input diagnostics.

# Validation - Introduce Project-Owned Structure

Validated on 2026-08-26 with local Python 3.14.4.

## Completed Checks

- Focused structure, initialization, vertical, definition, schema, snapshot,
  authority and installed-contract tests: `129 passed`.
- Vertical and MCP regression gate after removing active-vertical structural
  assumptions: `65 passed`.
- Public CLI/MCP contract suite: `284 passed`, `1290 deselected`.
- Full suite: `1574 passed`.
- Source and wheel distributions built with
  `python -m build --no-isolation`.
- Release artifacts verified: wheel `320` members, sdist `657` members.
- The built `p2p_engine-0.4.11-py3-none-any.whl` was installed into an isolated
  target and imported from that target rather than the source checkout.
- Installed-wheel smoke suite: `19 passed`, `1555 deselected`.
- `git diff --check` completed without whitespace errors.

## Contract Evidence

- Generic, empty and exact-release initialization create detached revision-1
  structures with stable project-local identity and provenance.
- Definition fields and validation resolve against `ProjectStructure`; changing
  transitional active-release metadata does not replace project structure.
- Add-section, metadata-update and reorder use expected revision,
  `project.structure.edit`, typed authority, atomic events and compact receipts.
- Exact replay, divergent key reuse, stale revision, concurrent apply,
  pre-commit failure and explicit interrupted-transaction recovery are tested.
- CLI and MCP expose bounded path-free reads and share the same mutation
  services; MCP mutations additionally require consent.

## Release Matrix Gate

Python 3.11 is not installed in the local environment. The release workflow
retains its mandatory Python 3.11 and Python 3.14 matrix. The structure checksum
uses canonical semantic serialization and has no Python-version-specific input.
The package remains at 0.4.11 during this implementation sequence; the planned
0.5.0 version gate follows completion of the P2P Engine convergence features.

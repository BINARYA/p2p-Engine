# Alternatives

## Manual Repair

The owner could explicitly authorize a one-time direct edit of `.p2p/project.yml`,
`.p2p/project/runtime.yml`, and `P2P-SETUP.md`. This solves the immediate local
warning but bypasses the normal public write interface and does not give future
legacy projects a repeatable path.

## Reuse `p2p init`

Initialization already creates runtime contracts for new projects, but using it
for adoption would blur project creation with project migration. It would also
contradict the existing rule that ordinary init must not recreate a missing
required contract in an existing project.

## Extend Runtime Contract Update

PROP-095 updates a valid current contract. Extending it to legacy adoption would
mix two trust models: update compares old and new contracts, while adoption has
no current contract and must create the first declaration.

## Dedicated Adoption Command

A dedicated adoption command keeps the scope small and testable: only
`legacy_undeclared` can proceed, adoption values are explicit, and the generated
files are deterministic.

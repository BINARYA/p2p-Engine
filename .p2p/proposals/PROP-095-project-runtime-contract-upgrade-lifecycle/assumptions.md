# Assumptions

- PROP-084 provides the project runtime contract, manifest marker, status
  classification, setup-guide generation, managed marker, drift detection, and
  write-gate behavior consumed by PROP-095.
- A valid current contract is required for an applicable update preview. Invalid,
  unsupported, missing, and legacy-undeclared current states require separate
  repair, migration, recovery, or adoption workflows.
- The first supported range grammar is intentionally limited and uses the same
  PEP 440-compatible semantics already used to validate runtime contracts.
- The command can determine the active P2P Engine version locally without
  installing or upgrading anything.
- Owner authority can be checked at apply time through the existing project
  authority model, or through the narrow authority service added for this
  lifecycle.
- Preview can report whether apply appears authorized without exposing sensitive
  permission details.
- The stable P2P-managed marker in `P2P-SETUP.md` is sufficient to distinguish a
  managed generated guide from a human-owned setup document.
- `P2P-SETUP.md` is deterministic from the runtime contract, apart from newline
  normalization.
- Generic audit support may exist, but PROP-095 must remain correct when durable
  audit is supplied by Git history rather than by a P2P audit artifact.
- Agents may generate preview output and pass it to an owner; the expected-state
  token is transferable because it does not authorize the actor.
- Release availability can be checked only on a best-effort basis from local or
  official metadata and must not become a hidden network or installation
  dependency.
- If an update makes the active runtime incompatible, broad validation and
  subsequent governed writes are deferred until a compatible runtime is used.
- Adoption or replacement of unmanaged setup guides is a separate capability.
- Repair of invalid contracts, migration of unsupported schemas, and recovery of
  missing required contracts are outside PROP-095.

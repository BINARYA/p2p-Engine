# Suggested Scope

## In Scope

- `.p2p/project/runtime.yml`.
- Versioned runtime contract schema.
- Compatible P2P Engine range.
- Recommended P2P Engine runtime version.
- Project-root `P2P-SETUP.md`.
- Runtime status diagnostics with JSON output.
- Runtime contract validation.
- Distinction between `legacy_undeclared` and `missing_contract`.
- Governed-write gate for incompatible, invalid, unsupported, or required but
  missing contracts.
- Public documentation and generated agent guidance.

## Out Of Scope

- Mandatory script-based setup.
- Install manager.
- Reconcile manager.
- Environment mutation.
- Virtualenv lifecycle.
- Package resolver or package download.
- Release tags, wheel filenames, digests, source descriptors, URLs, or
  repository coordinates in the required runtime contract.
- Release workflow changes.
- Repository-local wheel behavior.
- Broad command blocking outside governed writes.
- Runtime MCP tools.

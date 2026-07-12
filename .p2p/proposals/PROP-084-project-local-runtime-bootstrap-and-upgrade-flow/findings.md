# Findings

- Runtime version alignment is a real problem for shared P2P-managed projects.
- A minimal runtime contract solves the problem without installation
  automation.
- Wheel filenames, release tags, digests, source descriptors, resolvers, and
  package sources are installer or release-integrity concerns and must stay out
  of the required runtime contract.
- `P2P-SETUP.md` is needed because a collaborator may not know where to look
  inside `.p2p/`.
- `legacy_undeclared` and `missing_contract` must be distinct. A missing file
  is only `missing_contract` when a project-level marker or policy requires it.
- The proposal should not introduce broad command blocking. It should gate only
  governed writes when a declared or required contract cannot be trusted.
- The write-gate guarantee applies to runtimes that implement PROP-084. Older
  runtimes may ignore the new contract unless a separate compatibility marker is
  introduced.

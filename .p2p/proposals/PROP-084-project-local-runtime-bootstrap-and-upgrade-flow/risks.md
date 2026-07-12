# Risks

- Risk: No existing project-level marker can distinguish a deleted required
  contract from a legacy project.
  Mitigation: report `missing_contract` only when an explicit marker or policy
  requires `runtime.yml`; otherwise report `legacy_undeclared`.

- Risk: Older runtimes ignore `runtime.yml`.
  Mitigation: document that enforcement is guaranteed only by runtimes that
  implement PROP-084. Consider a separate project-format compatibility proposal
  if stronger rejection by older runtimes is required.

- Risk: The governed-write gate is implemented in scattered command handlers.
  Mitigation: centralize the preflight behind a reusable service/facade boundary
  and test representative mutating paths.

- Risk: Future install automation is treated as already approved.
  Mitigation: keep script setup, installers, resolvers, source selectors,
  virtualenv lifecycle, and package downloads explicitly out of scope.

- Risk: `P2P-SETUP.md` drifts from `runtime.yml`.
  Mitigation: generate it from the runtime contract and preserve or refresh it
  only through explicit project initialization behavior.

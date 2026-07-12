# Assumptions

- P2P Engine can determine its own installed runtime version.
- A compatibility range can be generated from the active runtime version and an
  explicit compatibility policy selected during implementation.
- The project can write `.p2p/project/runtime.yml` and project-root
  `P2P-SETUP.md` during project initialization.
- A reusable runtime preflight can be placed on representative governed-write
  paths without changing read-only command behavior.
- PROP-078 remains the source for installation mechanics.
- PROP-080 remains the source for release artifact publication and integrity
  metadata, but PROP-084 does not need that metadata to create or validate the
  runtime contract.

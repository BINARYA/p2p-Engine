# Exploration

PROP-084 remains valid because runtime version alignment is a real
project-collaboration problem. A cloned, copied, or extracted P2P-managed
project must carry the runtime compatibility facts needed by a human or agent.

The corrected solution is not an installer. The required mechanism is a minimal
`.p2p/project/runtime.yml` contract plus project-local setup guidance.

The contract should record:

- schema version;
- compatible P2P Engine range;
- recommended P2P Engine runtime version.

It should not record release tags, wheel filenames, digests, source descriptors,
download locations, repository coordinates, or install commands.

The visible project-local guide should be `P2P-SETUP.md`, generated from the
contract. It helps collaborators who do not know P2P internals, while keeping
`runtime.yml` as the source of truth.

The contract should also have limited normative force. Read-only commands remain
available, and legacy projects without a contract remain warning-only. Governed
writes should fail before mutation when a declared or required contract is
incompatible, invalid, unsupported, or required but missing.

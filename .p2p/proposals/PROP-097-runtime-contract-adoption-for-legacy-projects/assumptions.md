# Assumptions

Legacy projects are identifiable by `p2p runtime status` returning
`legacy_undeclared`. The first adoption can use exact active-runtime
compatibility when the owner explicitly confirms that this installed runtime is
the intended baseline.

The runtime contract schema remains the same schema introduced by PROP-084:
`runtime_contract.schema_version: 1`, `runtime.p2p.requires`, and
`runtime.p2p.recommended`.

The managed setup guide marker from PROP-084 remains the stable way to identify
P2P-owned `P2P-SETUP.md` content.

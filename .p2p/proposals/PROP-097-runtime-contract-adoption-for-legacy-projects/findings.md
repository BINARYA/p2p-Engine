# Findings

The current P2P Engine repository is a representative legacy project: it has no
`.p2p/project/runtime.yml`, no `runtime_contract.required` marker, and no
managed setup guide. `p2p runtime status` reports `legacy_undeclared`, which is
non-blocking but leaves compatibility unverifiable. The existing PROP-095 update
lifecycle correctly refuses to operate in that state because there is no trusted
current contract to compare against.

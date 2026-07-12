# Execution Plan

1. Add local specs for the accepted adoption proposal once the owner accepts it.
2. Implement service-level adoption logic in the runtime contract service or a
   closely owned helper, keeping CLI presentation thin.
3. Expose the selected CLI surface under `p2p runtime contract`.
4. Add tests for successful legacy adoption, blocked non-legacy states,
   unmanaged setup-guide protection, and post-adoption validation.
5. Update CLI and agent documentation to explain adoption as distinct from
   installation and update.
6. Use the implemented command to adopt the runtime contract for this repository
   and confirm that `p2p validate` no longer reports the legacy warning.

# Assumptions - PROP-060

- A small development-only coverage dependency is acceptable for P2P Engine maintainers.
- Terminal `term-missing` output is sufficient for the first slice.
- Existing smoke and focused validation scripts should remain the normal fast feedback path.
- Coverage should be run occasionally, especially around refactors or new runtime areas.
- Coverage should not run automatically after every small change.
- Coverage should not become a release gate or CI fail-under threshold in the first slice.
- Deterministic validation selection is handled by `PROP-098`.
- User-facing project evidence coverage is a separate product concern and is not part of this proposal.

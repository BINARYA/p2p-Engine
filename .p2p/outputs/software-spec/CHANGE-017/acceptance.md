# Acceptance

## Criteria

- `p2p work scan` reads local branches matching `p2p/work/*`.
- `p2p work scan` discovers `.p2p/work/WORK-XXX/manifest.yml` files on matching branches.
- `p2p work scan` writes `.p2p/registries/work.yml`.
- `p2p work scan` does not checkout, fetch, create branches, commit, submit, or merge.
- `p2p work list` includes scanned branch Work items after scan.
- The command handles repositories with no matching branches gracefully.

## Tests / Verification

- T001: Add read-only Git branch scan helpers (completed)
- T002: Implement p2p work scan (completed)
- T003: Expose scanned Work items (completed)
- T004: Preserve read-only Git boundary (completed)
- T005: Update P2P skill and tests (completed)

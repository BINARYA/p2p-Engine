# Acceptance

## Criteria

- `p2p work plan --change CHANGE-XXX --target TARGET` requires a validated export bundle.
- `p2p work plan` creates `.p2p/work/WORK-XXX/manifest.yml`.
- Work manifests include source Change Set, source proposals, handoff target, export path, export validation status, logical internal branch name, allowed files, and managed Git levels.
- Work policy keeps `auto_branch`, `auto_commit`, and `auto_merge` disabled in this MVP.
- `p2p work list` lists planned Work manifests.
- `p2p work show WORK-XXX` prints manifest detail.
- The MVP does not create Git branches, commits, PRs, tags, or merges.

## Tests / Verification

- T001: Define managed Git levels (completed)
- T002: Create Work manifest from validated export (completed)
- T003: Inspect Work manifests (completed)
- T004: Preserve invisible Git boundary (completed)
- T005: Update P2P skill and tests (completed)

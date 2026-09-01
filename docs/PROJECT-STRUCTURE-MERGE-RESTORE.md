# Project Structure Merge And Restore

P2P Engine can selectively import typed structure elements from one exact
portable vertical release or canonical project bundle. It can also use a
retained prior structure revision as the source of a new forward revision.
Both workflows operate on canonical stable IDs and are independent of the
physical storage layout.

## Retention Contract

Every governed structure mutation retains the immediately previous canonical
structure in the selected project-state adapter. The current filesystem
adapter keeps the newest 100 distinct revisions. Older revisions are pruned
deterministically. Only revisions returned by `retained list` or `retained
inspect` are advertised as restorable; a missing, corrupt or pruned revision
fails closed and is never reconstructed from receipts, exports or Git history.

```bash
p2p project structure retained list --format json
p2p project structure retained inspect REVISION --include-structure --format json
```

Restore changes only the structure aggregate and the active memory references
covered by its explicit disposition plan. It does not rewind project identity,
proposals, decisions, evidence, receipts or audit history.

## Selective Merge

Start with a side-effect-free comparison. `SOURCE` is one exact release
coordinate or a verified `.p2pbundle`:

```bash
p2p project structure merge compare SOURCE \
  --select section:scope --format json
```

The comparison returns the exact source digest, current target revision,
selected IDs, deterministic dependency closure and stable-ID collisions. Build
a strict `p2p-structure-merge-plan/v1` from that result. The plan records:

- the exact source identity, digest and schema version;
- the current structure revision/checksum and memory revision;
- selected stable IDs and their exact dependency closure;
- one target parent/order placement for every imported element;
- one explicit `keep-current`, `replace-with-impact` or `import-as-new-id`
  decision for every collision;
- any required active-memory dispositions.

Titles, text similarity, physical paths, row IDs and ordering coincidence are
never used to infer identity. Preview and apply use the same plan:

```bash
p2p project structure merge preview SOURCE \
  --plan merge-plan.yml --actor owner --format json
p2p project structure merge apply SOURCE \
  --plan merge-plan.yml --preview-token TOKEN \
  --operation-key local:structure-merge-001 \
  --actor owner --confirm --format json
p2p project structure merge status \
  --operation-key local:structure-merge-001 --format json
```

Apply requires `project.structure.merge`. It revalidates the exact source,
target, memory revision, plan and authority bound to the unexpired preview
token. The candidate structure, retained previous revision, event, affected
memory and receipt commit atomically. The imported structure is detached: no
source subscription or second authority is created.

## Forward Restore

Create a strict `p2p-structure-restore-plan/v1` using a retained revision and
checksum plus the current target and memory revisions. Preview reports the same
typed comparison, impacts, dispositions, readiness and classification
projections used by replacement:

```bash
p2p project structure restore preview \
  --plan restore-plan.yml --actor owner --format json
p2p project structure restore apply \
  --plan restore-plan.yml --preview-token TOKEN \
  --operation-key local:structure-restore-001 \
  --actor owner --confirm --format json
p2p project structure restore status \
  --operation-key local:structure-restore-001 --format json
```

Apply requires the distinct `project.structure.restore` capability. If the
historical source was revision N and the current structure is revision M, a
successful restore creates revision M+1 with the retained logical content. It
never moves a current pointer backward.

If an atomic workspace transition reports recovery-required state, inspect the
shared transaction status and follow the exact recovery instruction. The
operation-specific aliases accept an explicit transaction ID, action, actor
and confirmation:

```bash
p2p project structure merge recover TRANSACTION-ID \
  --action resume --actor owner --confirm --format json
p2p project structure restore recover TRANSACTION-ID \
  --action rollback --actor owner --confirm --format json
```

## MCP Boundary

MCP offers only byte-invariant reads:

- `p2p_project_structure_merge_compare`;
- `p2p_project_structure_retained_inspect`.

There is intentionally no MCP merge/restore preview, apply, status or recovery
tool. Multi-decision apply remains an explicitly confirmed CLI workflow. All
public plans and results use logical IDs, revisions and checksums; they do not
expose filesystem paths, SQL, backend names or Git concepts.

# YAML Loader Audit

## Result

Generic P2P YAML readers use the project-owned helpers in
`p2p_engine.foundation.yaml_loaders`. The default `safe-v1` contract selects
`yaml.CSafeLoader` when available and has an explicit Python fallback. The
`unique-v1` contract adds duplicate-key rejection to matching C and Python
loader classes. Request-scoped readers key parsed values by path, captured
physical digest, and loader contract.

The source audit on 2026-07-20 found 26 direct `yaml.safe_load` or `yaml.load`
calls after migration. They are intentionally excluded from the generic-reader
replacement for the reasons below. New ordinary workspace readers should not
add to this list.

## Shared Contracts

| Surface | Contract | Reason |
| --- | --- | --- |
| `foundation/yaml_loaders.py` | `safe-v1`, `unique-v1` | Owns loader selection, duplicate-key handling, and Python fallback. Its single direct `yaml.load` call is the implementation boundary. |
| `foundation/files.py` and compatible domain readers | `safe-v1` | Generic trusted or validated workspace mappings and sequences. |
| decision-event ledgers and specialized decision readers | `unique-v1` | Duplicate keys are invalid and must retain the domain diagnostic. |
| `WorkspaceDocumentStore` parse cache | explicit caller contract | Prevents a weak safe parse from satisfying a unique-key request. |

## Justified Direct Uses

| Paths | Calls | Classification | Why excluded |
| --- | ---: | --- | --- |
| `foundation/markdown.py` | 1 | embedded front matter | Parses only the delimited YAML fragment of a Markdown document. It remains a separate content-format boundary; moving it requires front-matter parity tests rather than a mechanical reader change. |
| `services/workspace_compatibility.py` | 4 | migration compatibility and tagged owner input | Three calls inspect historical candidate bytes during migration planning/fingerprinting. The custom `_MigrationOwnerInputLoader` call owns `!p2p/delete` semantics and cannot use a generic safe contract. |
| `services/candidate_workspace.py`, `workspace_migrations.py`, `workspace_migration_handlers.py` | 7 | candidate/migration readers | These read an isolated migration candidate or original pre-migration bytes. Their behavior is covered by migration parity and rollback tests; changing the loader is intentionally deferred to a dedicated migration-loader contract. |
| `services/conflicts.py`, `project_metadata.py`, `proposal_artifacts.py`, `project_verticals.py` | 7 | YAML semantic clone/normalization round trip | Each call immediately reloads `safe_dump` output to make a detached normalized value. It is not an I/O parse hot path. Replacing half of the round trip would add no material read benefit and could alter normalization semantics. |
| `services/proposal_branches.py`, `work_branches.py` | 4 | Git object boundary | Parses YAML text supplied by an abstract Git file object, not a local captured workspace document. It remains isolated from request-cache and canonical source-read accounting. |
| `services/workspace_transactions.py` | 2 | transaction lock/recovery boundary | Reads lock and recovery metadata before or outside an ordinary read context. These paths must stay independent from project read caching so recovery never trusts a stale request snapshot. |

The table accounts for all 26 direct calls: one loader implementation call and
25 specialized uses. `rg -n "yaml\\.safe_load|yaml\\.load\\(" src/p2p_engine`
is the repeatable audit command.

## Parity And Failure Policy

- C and Python loaders must agree for mappings, sequences, scalars, null,
  Unicode, anchors, aliases, merge keys, malformed input, tags, multi-document
  input, duplicate keys, and large payloads.
- Duplicate-key behavior is part of the loader contract, not an optimization.
- Deep validation may share captured bytes and a parse only when the loader
  contract is identical.
- Migration, transaction, front-matter, Git-object, and normalization paths are
  excluded from the generic read optimization but remain covered by their
  existing domain suites.
- A future direct call must either move behind a shared contract or be added to
  this inventory with parity evidence.

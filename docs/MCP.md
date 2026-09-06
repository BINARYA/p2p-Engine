# P2P MCP Server

This document describes how agents can access P2P Engine through the local MCP
server. The MCP server is a local stdio bridge to P2P project state; it is not a
hosted product and it does not replace the CLI as the source of truth.

## Server

P2P Engine currently exposes MCP over local `stdio`.

In `stdio` mode, the MCP client starts the P2P MCP server as a local subprocess.
The client and server exchange JSON-RPC messages over `stdin` and `stdout`.
Diagnostic logs must go to `stderr`; `stdout` must contain only valid MCP
messages.

This is not a single shared daemon. If Codex, Claude, and VS Code all connect to
the same target project through `stdio`, each client may start its own P2P MCP
server process. Shared P2P state must therefore live outside the MCP process in
the governed target root's `.p2p/` workspace and other P2P core storage. A
caller may version that state externally, but Git history is neither required
storage nor a P2P runtime authority.

CLI and MCP enter the same project application service. The replica-local
storage manifest selects one writable adapter; MCP tools do not expose its
paths or provide raw storage operations. `p2p_init_project` accepts the
currently available `filesystem` selection, while reopening uses the stored
selection automatically.

For a `linked-local` project, local stdio MCP uses the same durable replica
service as the CLI. Reads catch up first and report their confirmed WaveKit
revision/freshness. Registered domain mutations are submitted to WaveKit as
typed commands and require a stable `linked_operation_id`, the observed
`linked_expected_project_revision` and any affected
`linked_entity_preconditions`. Caller-supplied actor fields are never trusted;
the authenticated WaveKit request establishes actor and capability. Confirmed
state enters the local replica only from a verified change batch.

Linked drift inspection is deliberately read-only. MCP exposes
`p2p_replica_drift_status` and `p2p_replica_drift_diff` as bounded,
backend-neutral diagnostics. It does not expose forensic backup,
discard/rebuild or reconciliation apply. When drift is blocked, the agent must
stop writes and request the explicit owner CLI workflow documented in
[Linked Replica Drift And Recovery](LINKED-REPLICA-DRIFT.md); it must never
repair `.p2p` manually or upload suspect local storage.

MCP exposes no raw command-envelope, feed, cursor, blob, compaction or
initialization primitive. `p2p_linked_replica_catch_up` remains a diagnostic
domain-level operation. Clone, attach, move and copy registration remain owner
CLI operations. WaveKit authority transfer exposes eligibility, preview and
status only; login, upload, apply and transfer recovery remain owner CLI
operations.

Linked-project lifecycle follows the same conservative boundary. MCP exposes
status, preview and immutable-publication inspection only. Suspend/resume,
detach, create-as-new, archive/restore, publication apply, remote deletion and
local-replica removal remain explicitly confirmed owner CLI operations. An
unreachable or tombstoned remote never turns a local MCP process into project
authority. See [LINKED-PROJECT-LIFECYCLE.md](LINKED-PROJECT-LIFECYCLE.md).

For a future multi-agent setup that requires one long-running shared service,
P2P Engine would need a Streamable HTTP MCP server. The current implementation
is local `stdio`.

Run `p2p doctor --root /path/to/project` and use the absolute
`running_python` it reports. That interpreter is the runtime that generated the
hint and can import the MCP server; it does not need to live in the project:

```bash
/absolute/path/reported/by/p2p-doctor/python \
  -m p2p_engine.mcp.server \
  --root /path/to/project
```

Typical uv locations are
`~/.local/share/uv/tools/p2p-engine/bin/python` on POSIX and
`%APPDATA%\uv\tools\p2p-engine\Scripts\python.exe` on Windows, but clients
must use the discovered absolute value rather than assuming a default path.

`--root` selects the governed P2P project root used for decisions and state. If
`p2p-mcp-server` is actually resolvable in the client process's `PATH`, this
shorter form remains valid:

```bash
p2p-mcp-server --root /path/to/project
```

For a project that requires P2P Engine 0.6.6 while the persistent tool is
incompatible, configure the owner-approved exact runtime. Keep command and
arguments separate in client configuration:

```text
command: /absolute/path/to/uv
args: tool, run, --isolated, --managed-python, --python, 3.12, --no-config,
      --from, https://github.com/BINARYA/p2p-Engine/releases/download/v0.6.6/p2p_engine-0.6.6-py3-none-any.whl,
      p2p-mcp-server, --root, /path/to/project
```

This launches a pinned process; MCP neither installs/reconciles persistent
runtimes nor bypasses runtime-contract write gates. A cold cache may require
network access. Environment changes always require explicit owner action.

## Verified Client Setup

The exact setup differs by client. Do not assume MCP configuration files are
portable across all clients without adaptation.

### Codex CLI

```bash
codex mcp add p2p-my-project -- \
  /absolute/path/reported/by/p2p-doctor/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Codex CLI and the Codex IDE extension share MCP configuration through
`config.toml`. Use `codex mcp --help` to inspect available management commands,
and use `/mcp` inside the Codex terminal UI to inspect active servers.

### Claude Code

```bash
claude mcp add --transport stdio p2p-my-project -- \
  /absolute/path/reported/by/p2p-doctor/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

Use `claude mcp list`, `claude mcp get p2p-my-project`, and `claude mcp remove
p2p-my-project` to manage the entry. Inside Claude Code, use `/mcp` to inspect
connected servers.

### Claude Desktop

Claude Desktop uses a local MCP JSON configuration file. Add the P2P server with
the same command and arguments:

```json
{
  "mcpServers": {
    "p2p-my-project": {
      "command": "/absolute/path/reported/by/p2p-doctor/python",
      "args": [
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        "/path/to/my-project"
      ]
    }
  }
}
```

Documented config paths:

```text
macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%\Claude\claude_desktop_config.json
```

### VS Code With GitHub Copilot Agent

VS Code's MCP configuration is separate from Codex configuration. Use workspace
`.vscode/mcp.json` or the user profile MCP configuration:

```json
{
  "servers": {
    "p2p-my-project": {
      "type": "stdio",
      "command": "/absolute/path/reported/by/p2p-doctor/python",
      "args": [
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        "${workspaceFolder}"
      ]
    }
  }
}
```

Then ask the agent to start with compact context:

```text
Use the P2P MCP server and show p2p_context for this project.
```

## Safety Model

MCP tools are grouped by behavior:

- read-only tools inspect state;
- write-safe tools create drafts or deterministic generated artifacts;
- advisory tools create prompts or analysis without deciding;
- permission-gated tools perform privileged sync/proposal operations only with a matching consent receipt;
- governance decisions remain owner-controlled;
- missing write primitives must be reported, not bypassed by manual `.p2p/` edits.

Agents should use `p2p_context` before broad file reads. The context packet tells
the agent what is relevant, what commands are allowed, and what not to scan.
When `target` is a valid `PROP-*` ID, `nearby_context` adds a read-only,
versioned decision neighborhood with policy versions, source and semantic
fingerprints, completeness, ranked hits, evidence, diagnostics and truncation
metadata. Other target types and no-target calls return `nearby_context: null`.
Fingerprint fields exclude observational generation time. No MCP context call
writes a freshness manifest or cache; future materialized projections can use
the in-memory manifest/stale contract without changing this read-only behavior.
The index reads canonical/governed P2P evidence, not generated registries,
decision maps, project narratives, prompts, publications or cache files.

`p2p_workspace_schema_status` is a read-only contract probe. It returns the
workspace schema status plus the same `contract_versions` tuple exposed by
`p2p version --format json` and `p2p status --format json`; MCP still returns a
protocol-native payload, not a `p2p-cli/v1` envelope.

Untargeted compact context uses the vertical-aware project-memory read model as
its primary project shape. `p2p_project_memory_status` and
`p2p_project_memory_show` provide read-only parity with the CLI. The show tool
uses exact section IDs, bounded results, explicit history and source-bound
cursors. Neither tool refreshes files. Materialized project memory is derived;
canonical `.p2p` intent remains authoritative and accepted proposals are not
evidence of implementation.

Structural organization is exposed separately from that derived vertical view.
`p2p_project_memory_classification` reads a bounded snapshot bound to the
current project-structure checksum and project-memory revision.
`p2p_proposal_scope_show` reads one proposal's explicit `sections`,
`project_global`, or `unassigned` scope. `p2p_proposal_scope_set` performs the
matching receipt-backed mutation and requires a consent for operation
`project_memory_scope_set`, target `proposal:<PROP-ID>`, plus current memory and
structure revisions. Classification never changes readiness scores, and its
consent does not authorize proposal decisions or readiness overrides.

Prompt tools keep their existing output contracts. `p2p_intake_prompt` selects a
bounded idea-text neighborhood internally, while `p2p_explore_prompt`,
`p2p_impact_prompt` and `p2p_synthesize_prompt` select a bounded proposal
neighborhood. The selected context is written only into the generated prompt;
it does not create contributions, choices, relations, decisions or imported
proposal artifacts. MCP responses still return the existing intake metadata or
prompt path only.

`p2p_next` also keeps its existing payload. Generated choice actions are
derived from normalized project-choice nodes and active relations, so
proposal-local vote records cannot appear as project choices requiring a
decision. Every non-terminal Change Set registry record produces a stable
`NEXT-CHANGE-<CHANGE-ID>` action even when the decision-context index is
partial. The optional `top` argument truncates only the final composed and
deduplicated list, so CLI and MCP return the same prefix. Topology diagnostics
remain visible only through existing read-only context/diagnostic payloads; no
diagnostic file is created.

`p2p_spec_status` preserves the existing `status` field and adds per-spec
`freshness`, `origin`, current/recorded fingerprints, changed paths, stable
reason codes, and a suggested command. Generated freshness is based on exact
source and candidate bytes, not mtimes. Legacy and imported origins are
classified conservatively. The tool is read-only and never rewrites
provenance.

Permission-gated MCP tools validate:

```text
consent_id
operation
target
actor_id
single-use status
expiry, when present
```

The tool consumes the receipt after successful execution and stores result
metadata. Consent receipts are auditable local project records, not strong
authentication. A hosted integration such as WaveKit must enforce its own user
authentication, project authorization, concurrency and worker access. Optional
source-control provider permissions protect only that provider's external
repository operations; they do not authorize P2P project-state mutations.

## Tool Matrix

| Tool | Type | Mutates state? | Governance? | When to use |
| --- | --- | ---: | ---: | --- |
| `p2p_context` | read-only | no | no | First tool before broad reads. |
| `p2p_validate` | read-only | no | no | Check structural and semantic consistency. |
| `p2p_project_status` | read-only | no | no | Inspect deterministic project status. |
| `p2p_project_identity_show` | read-only | no | no | Read the stable project UUID, local replica address, mode, binding and lineage without storage details. |
| `p2p_project_identity_status` | read-only | no | no | Read validity, mutation eligibility and actionable adoption/recovery guidance. |
| `p2p_project_identity_transitions` | read-only | no | no | Read the fixed identity behavior for rename, move, backup, restore, copy, derive and detach. |
| `p2p_project_identity_copy_check` | read-only | no | no | Classify an observed UUID/replica collision using explicit copy intent. |
| `p2p_project_identity_adopt_preview` | governed preview | no | yes | Preview backup-protected adoption for an identity-less development project. |
| `p2p_project_identity_adopt_apply` | consent-gated | yes | yes | Apply the exact adoption preview with root authority and consent bound to `project-identity@preview-token`. |
| `p2p_project_identity_derive_preview` | governed preview | no | yes | Preview a new independent UUID with optional typed lineage. |
| `p2p_project_identity_derive_apply` | consent-gated | yes | yes | Apply the exact derivation preview with root authority and token-bound consent. |
| `p2p_project_authority_transfer_eligibility` | read-only | no | no | Check local/server eligibility without creating a session, fencing writes or uploading content. |
| `p2p_project_authority_transfer_preview` | read-only | no | no | Read the sanitized revision/destination-bound handoff preview; apply remains absent from MCP. |
| `p2p_project_authority_transfer_status` | read-only | no | no | Inspect non-secret local transfer state and optionally query the authenticated remote session. |
| `p2p_project_lifecycle_status` | read-only | no | no | Inspect local lifecycle evidence plus authenticated remote state without changing authority or freshness. |
| `p2p_project_lifecycle_preview` | read-only | no | no | Preview a revision-bound lifecycle operation; confirmation and apply remain owner CLI-only. |
| `p2p_project_publication_list` | read-only | no | no | List locally verified immutable project-publication metadata without downloading or publishing content. |
| `p2p_linked_replica_status` | read-only | no | no | Inspect non-secret linked binding, access state, revision, cursor and freshness. |
| `p2p_linked_replica_catch_up` | write-safe | yes | no | Download and atomically activate a fully verified WaveKit snapshot; clone and replica identity changes remain owner CLI operations. |
| `p2p_workspace_schema_status` | read-only | no | no | Inspect workspace layout, semantic alignment, recovery state and release contract versions. |
| `p2p_project_progress` | read-only | no | no | Inspect the same weighted definition-completeness and declared-evidence axes used by project readiness. |
| `p2p_project_freshness` | read-only | no | no | Inspect the full derived-state graph and ordered rebuild actions. |
| `p2p_project_memory_status` | read-only | no | no | Inspect vertical-memory contract, source fingerprint and freshness without rebuilding it. |
| `p2p_project_memory_show` | read-only | no | no | Read a bounded aggregate or exact vertical section; history requires an explicit option. |
| `p2p_project_memory_classification` | read-only | no | no | Read bounded structural classification, revisions and debt separately from readiness. |
| `p2p_canonical_memory_inspect` | read-only | no | no | Classify every durable `.p2p` artifact and fail closed on unresolved state. |
| `p2p_canonical_memory_verify` | read-only | no | no | Verify the current storage-neutral logical aggregate, identity, relations, lineage and managed blobs. |
| `p2p_project_bundle_export_metadata` | read-only | no | no | Compute deterministic portable-bundle metadata and digest in memory without writing an archive. |
| `p2p_project_archive_verify` | read-only | no | no | Verify a bundle or physical backup independently without extraction or activation. |
| `p2p_proposal_scope_show` | read-only | no | no | Read explicit section, project-global or unassigned proposal scope. |
| `p2p_proposal_scope_set` | governed write | yes | consent | Assign scope atomically with current memory and structure revisions. |
| `p2p_proposal_vertical_coverage_show` | transitional read-only | no | no | Inspect the pre-0.5 derived vertical-coverage artifact; it is not current scope authority. |
| `p2p_proposal_vertical_coverage_suggest` | transitional advisory | no | no | Suggest legacy mappings without satisfying classification or decision gates. |
| `p2p_project_interaction_style_show` | read-only | no | no | Read effective project interaction style values and descriptions. |
| `p2p_project_interaction_style_set` | write-safe | yes | no | Set project-level interaction style values without governance side effects. |
| `p2p_next` | read-only | no | no | Show the complete composed advisory action set, optionally bounded by `top`. |
| `p2p_next_add` | write-safe | yes | no | Add a curated next action to the operational board. |
| `p2p_next_complete` | write-safe | yes | no | Complete a curated next action and audit it in the next-action log. |
| `p2p_next_retire` | write-safe | yes | no | Retire a curated next action and audit it in the next-action log. |
| `p2p_next_refresh` | write-safe | yes | no | Normalize curated next actions and report generated action count. |
| `p2p_proposal_list` | read-only | no | no | List proposals, optionally by status. |
| `p2p_proposal_show` | read-only | no | no | Inspect one proposal summary; pass `full: true` for the owner review view. |
| `p2p_proposal_decision_status` | read-only | no | no | Read effective lifecycle, head, authority intervals and diagnostics. |
| `p2p_proposal_decision_history` | read-only | no | no | Read bounded append-only decision history. |
| `p2p_proposal_decision_impact` | read-only | no | no | Inspect complete dependency impact with bounded rendering. |
| `p2p_proposal_decision_preview` | read-only | no | no | Create a source-bound decision preview without recording an event. |
| `p2p_proposal_decision_apply` | consent-gated | yes | yes | Apply the exact preview using `proposal_decision_apply` consent bound to `PROP-XXX@preview-token`. |
| `p2p_proposal_decision_projection_repair_preview` | read-only | no | yes | Preview restoring projections from a valid ledger. |
| `p2p_proposal_decision_projection_repair_apply` | consent-gated | yes | yes | Restore projections from a valid ledger and matching preview. |
| `p2p_proposal_decision_ledger_repair_preview` | read-only | no | yes | Preview a reviewed ledger candidate that preserves the valid prefix. |
| `p2p_proposal_decision_ledger_repair_apply` | consent-gated | yes | yes | Apply the reviewed ledger candidate and matching preview. |
| `p2p_choice_list` | read-only | no | no | List project choices. |
| `p2p_choice_show` | read-only | no | no | Inspect one choice. |
| `p2p_governance_status` | read-only | no | no | Read governance mode and audit artifact counts. |
| `p2p_governance_validate` | read-only | no | no | Validate governance artifacts without changing them. |
| `p2p_choice_governance_preflight` | read-only | no | no | Preview owner-decision readiness for a choice without deciding it. |
| `p2p_choice_transition_preview` | read-only | no | yes | Preview the one terminal `decide`, `withdraw`, or `supersede` transition. |
| `p2p_choice_transition_apply` | consent-gated | yes | yes | Apply the exact preview using `choice_transition_apply` consent bound to `CHOICE-XXX@preview-token`. |
| `p2p_vote_status` | read-only | no | no | Read proposal-local advisory vote counts. |
| `p2p_precedent_search` | read-only | no | no | Search deterministic explicit precedent matches without recording precedents. |
| `p2p_change_status` | read-only | no | no | List Change Set statuses. |
| `p2p_change_show` | read-only | no | no | Inspect one Change Set. |
| `p2p_change_tasks` | read-only | no | no | Inspect Change Set tasks and actions. |
| `p2p_work_list` | read-only | no | no | List Work manifests. |
| `p2p_work_status` | read-only | no | no | Show operational Work summaries. |
| `p2p_work_show` | read-only | no | no | Inspect one Work manifest. |
| `p2p_registry_status` | read-only | no | no | Check generated registry availability and freshness. |
| `p2p_registry_show` | read-only | no | no | Read a generated registry. |
| `p2p_project_show` | read-only | no | no | Read generated project sections or feature documents. |
| `p2p_permissions_show` | read-only | no | no | Read project-declared actors and role policy. |
| `p2p_consent_request` | write-safe | yes | no | Record a pending owner consent request; does not grant consent. |
| `p2p_consent_status` | read-only | no | no | List consent receipts without creating or consuming them. |
| `p2p_consent_show` | read-only | no | no | Inspect one consent receipt. |
| `p2p_spec_lifecycle` | advisory/read-only | no | no | Inspect software spec lifecycle routing and preflight diagnostics. |
| `p2p_spec_status` | read-only | no | no | List P2P-native software specs with additive semantic freshness details. |
| `p2p_spec_show` | read-only | no | no | Read a generated software spec index. |
| `p2p_spec_export_status` | read-only | no | no | List generated downstream spec exports. |
| `p2p_spec_export_show` | read-only | no | no | Read the primary file for a spec export target. |
| `p2p_assess_show` | read-only | no | no | Show the legacy stored operational readiness assessment. |
| `p2p_project_rubrics_show` | read-only | no | no | Read legacy/configured rubrics; current project readiness is based on `ProjectStructure` criteria. |
| `p2p_maturity_show` | read-only | no | no | Show stored maturity compatibility output. |
| `p2p_intake_status` | read-only | no | no | List intake records and analysis state. |
| `p2p_project_brief_show` | read-only | no | no | Show imported operational brief, if present. |
| `p2p_conflict_status` | read-only | no | no | Read recorded project conflicts. |
| `p2p_init_project` | write-safe | yes | no | Bootstrap a P2P workspace with a free domain classification and exactly one `generic`, `empty`, or exact vertical structure source. |
| `p2p_integration_status` | read-only | no | no | Report the access profile, independent contract versions, artifact ownership and drift without changing host files. |
| `p2p_agent_list` | read-only | no | no | List supported and installed agent integrations. |
| `p2p_agent_show` | read-only | no | no | Show one agent integration, files, and drift state. |
| `p2p_agent_doctor` | read-only | no | no | Return structured agent integration health findings. |
| `p2p_registry_refresh` | write-safe | yes | no | Regenerate deterministic registries. |
| `p2p_assess_refresh` | write-safe | yes | no | Generate the legacy deterministic operational readiness assessment. |
| `p2p_project_rubrics_init` | write-safe | yes | no | Create or refresh legacy rubric storage for compatibility. |
| `p2p_maturity_refresh` | write-safe | yes | no | Generate a compatibility projection from readiness-v2 definition completeness. |
| `p2p_proposal_create` | write-safe | yes | no | Create a draft proposal. |
| `p2p_proposal_update` | write-safe | yes | no | Update structured draft/proposal sections. |
| `p2p_proposal_contribution_add` | write-safe | yes | no | Add a typed contribution to a proposal. |
| `p2p_proposal_contribution_list` | read-only | no | no | List contributions recorded for a proposal. |
| `p2p_proposal_readiness_get` | read-only | no | no | Read stored proposal readiness and its current/stale/not-assessed freshness without writing. |
| `p2p_proposal_readiness_init` | write-safe | yes | no | Bootstrap a conservative readiness assessment from proposal artifacts. |
| `p2p_proposal_readiness_refresh` | write-safe | yes | no | Recompute readiness score from stored criterion evidence. |
| `p2p_proposal_readiness_assess` | write-safe | yes | no | Atomically recalculate evidence-aware readiness from current artifacts and structured question state. It remains advisory and does not decide or override. |
| `p2p_proposal_readiness_explain` | read-only | no | no | Explain readiness score, failed gates, gaps, next actions, and owner-question state evidence. |
| `p2p_proposal_readiness_list_gaps` | read-only | no | no | List readiness failed gates, missing criteria, next actions, and owner-question state evidence. |
| `p2p_proposal_readiness_review` | read-only | no | no | Review readiness gaps, owner questions, structured question categories, challenge points, and acceptance cautions. |
| `p2p_proposal_questions_status` | read-only | no | no | Read proposal question state or `not_initialized`. |
| `p2p_proposal_questions_init` | write-safe | yes | no | Initialize deterministic question state for a proposal. |
| `p2p_proposal_questions_add` | write-safe | yes | no | Add a readiness-linked owner question. |
| `p2p_proposal_questions_answer` | write-safe | yes | no | Record an answer for one proposal question. |
| `p2p_proposal_questions_next` | read-only | no | no | Return the next eligible proposal question. |
| `p2p_proposal_questions_apply` | write-safe | yes | no | Mark answered questions as applied and return an artifact-aware update plan. |
| `p2p_proposal_artifact_status` | read-only | no | no | Show proposal artifact coverage state plus the logical artifact catalog. |
| `p2p_proposal_artifact_init` | write-safe | yes | no | Initialize or refresh artifact-aware proposal state without deciding governance. |
| `p2p_proposal_artifact_set` | write-safe | yes | no | Set one artifact expectation/status/rationale without changing proposal decisions. |
| `p2p_proposal_artifact_confirm` | write-safe | yes | no | Record owner confirmation for one artifact state without accepting/rejecting the proposal. |
| `p2p_explore_import` | write-safe | yes | no | Import exploration artifact content from a source path, direct content, or allowlisted artifact payloads. |
| `p2p_impact_import` | write-safe | yes | no | Import impact artifacts from a source path, direct content, or allowlisted YAML artifact payloads with validation. |
| `p2p_clarify_import` | write-safe | yes | no | Import clarification content into `clarifications.md`. |
| `p2p_synthesize_import` | write-safe | yes | no | Import synthesized proposal content into `proposal.md`. |
| `p2p_plan_import` | write-safe | yes | no | Import execution-plan content into `execution-plan.md`. |
| `p2p_tasks_import` | write-safe | yes | no | Import task YAML into `tasks.yml` with tasks validation. |
| `p2p_change_create` | write-safe | yes | no | Create a metadata-only Change Set from an accepted proposal. |
| `p2p_project_refresh` | write-safe | yes | no | Refresh generated project definition files. |
| `p2p_project_export` | write-safe | yes | no | Export the visible human-facing project definition to `outputs/latest/project.md`. |
| `p2p_project_export_status` | read-only | no | no | Read visible project definition export status and review snapshots. |
| `p2p_project_publish_prepare` | write-safe | yes | no | Prepare shared evidence and one language edition using optional `language`, `output_name`, and `contributions`. |
| `p2p_project_publish_import` | write-safe | yes | no | Atomically import Markdown, model, and evidence-accounting candidates for one edition. |
| `p2p_project_publish_validate` | write-safe | yes | no | Validate one edition's complete evidence/model/Markdown hash chain. |
| `p2p_project_publish_render` | write-safe | yes | no | Render one validated edition to `<edition-key>.pdf` when `p2p-engine[pdf]` is installed. |
| `p2p_project_publish_status` | read-only | no | no | Read stage-level status and approval for one selected edition. |
| `p2p_project_publish_list` | read-only | no | no | List committed current editions without rebuilding publication state. |
| `p2p_project_vertical_list` | read-only | no | no | List internal and project-local vertical packs plus active/fallback state. |
| `p2p_project_domain_show` | read-only | no | no | Read the portable project-domain classification without exposing storage paths. |
| `p2p_project_domain_set` | permission-gated | yes | yes | Set domain classification through typed authority, consent and receipt-backed replay without changing structure. |
| `p2p_project_domain_clear` | permission-gated | yes | yes | Clear domain classification through typed authority, consent and receipt-backed replay without changing structure. |
| `p2p_project_structure_show` | read-only | no | no | Read the bounded canonical project-owned structure and provenance without storage paths. |
| `p2p_project_structure_history` | read-only | no | no | Read bounded append-only structure event evidence. |
| `p2p_project_structure_add_section` | permission-gated | yes | yes | Add one section with expected revision, `project.structure.edit`, consent and idempotent receipt. |
| `p2p_project_structure_update_metadata` | permission-gated | yes | yes | Update bounded metadata while preserving stable element identity. |
| `p2p_project_structure_reorder_sections` | permission-gated | yes | yes | Reorder the exact active section set without changing identity. |
| `p2p_project_structure_retirement_preview` | permission-gated preview | no | no | Preview structure retirement impacts and required dispositions against current structure and memory revisions. |
| `p2p_project_structure_retirement_apply` | permission-gated | yes | yes | Apply a token-bound structure retirement with resolved dispositions and idempotent receipt. |
| `p2p_project_structure_replacement_inspect` | read-only | no | no | Inspect one already resolvable exact replacement release and normalized candidate structure without pulling, writing cache, or mutating the project. |
| `p2p_project_structure_replacement_preview` | read-only preview | no | no | Compare one exact replacement release against current structure and memory revisions, returning impacts and required dispositions without an apply tool. |
| `p2p_project_structure_merge_compare` | read-only | no | no | Compare selected stable IDs from one exact release or canonical bundle, including dependency closure and collisions, without changing project state. |
| `p2p_project_structure_retained_inspect` | read-only | no | no | Inspect one still-retained canonical structure revision and its checksum without exposing or reconstructing physical storage. |
| `p2p_project_structure_export_eligibility` | read-only | no | no | Check whether the active project-owned structure can be exported as a portable vertical. |
| `p2p_project_structure_export_preview` | read-only | no | no | Build a source-token-bound export preview without creating drafts, packages, destination paths or remote releases. |
| `p2p_project_vertical_show` | read-only | no | no | Read one self-contained vertical release. |
| `p2p_project_vertical_validate` | read-only | no | no | Validate an installed vertical coordinate or schema-3 pack directory. |
| `p2p_project_vertical_select` | transitional | yes | no | Transitional release-selection surface; it is not the canonical project structure. |
| `p2p_project_vertical_lock_show` | transitional/read-only | no | no | Inspect a transitional source lock, not live structural authority. |
| `p2p_project_vertical_lock_repair` | transitional | yes | no | Repair transitional source metadata; it does not edit `ProjectStructure`. |
| `p2p_vertical_domain_list` | remote-network read-only | yes | no | List advisory remote catalog domains without project mutation, pull or cache writes. |
| `p2p_vertical_domain_search` | remote-network read-only | yes | no | Search advisory remote catalog domains; recommendations remain metadata only. |
| `p2p_vertical_domain_inspect` | remote-network read-only | yes | no | Inspect one exact catalog domain external ID without exposing inaccessible private domains. |
| `p2p_vertical_release_list` | remote-network read-only | yes | no | List remote vertical releases, optionally filtered by one exact advisory domain ID. |
| `p2p_vertical_release_search` | remote-network read-only | yes | no | Search remote vertical releases with optional exact domain filtering; matches are not compatibility proof. |
| `p2p_project_context` | read-only | no | no | Read structure/source context, definition summary, warnings, and next suggestion. |
| `p2p_project_sections` | read-only | no | no | List current project-structure sections, or inspect an explicitly requested vertical release. |
| `p2p_project_section_show` | read-only | no | no | Read one current project-structure section, or one section from an explicitly requested vertical release. |
| `p2p_project_definition_show` | read-only | no | no | Read durable project definition state. |
| `p2p_project_definition_update` | write-safe | yes | no | Apply a structured project definition patch file. |
| `p2p_project_readiness_review` | advisory/read-only | no | no | Review `p2p-project-readiness/v2` from current `ProjectStructure`, definition state and memory classification. |
| `p2p_project_readiness_gaps` | advisory/read-only | no | no | List bounded readiness-v2 gaps with stable structure or memory IDs and a snapshot-bound cursor. |
| `p2p_project_readiness_gap_show` | advisory/read-only | no | no | Read one stable readiness-v2 gap. |
| `p2p_project_questions_status` | advisory/read-only | no | no | List persistent project-question state with bounded pagination. |
| `p2p_project_questions_next` | advisory/read-only | no | no | Read the next applicable project question. |
| `p2p_spec_refresh` | write-safe | yes | no | Generate a P2P-native software spec after lifecycle preflight. |
| `p2p_spec_export` | write-safe | yes | no | Export spec outputs for `generic`, `openspec`, or `speckit` after lifecycle preflight. |
| `p2p_spec_export_validate` | read-only | no | no | Validate an existing spec export. |
| `p2p_work_plan` | write-safe | yes | no | Create a Work manifest from a validated export. |
| `p2p_proposal_accept` | compatibility preview | no | yes | Return an acceptance preview; old unbound consent cannot write. |
| `p2p_proposal_reject` | compatibility preview | no | yes | Return a rejection preview; old unbound consent cannot write. |
| `p2p_proposal_defer` | compatibility preview | no | yes | Return a deferral preview; old unbound consent cannot write. |
| `p2p_intake_prompt` | advisory/write-safe | yes | no | Create an intake prompt for a raw idea. |
| `p2p_project_brief_prompt` | advisory/write-safe | yes | no | Create project brief prompt artifacts. |
| `p2p_choice_discover` | advisory | no | no | Discover possible choices and blockers. |
| `p2p_explore_prompt` | advisory/write-safe | yes | no | Generate an exploration prompt for a proposal. |
| `p2p_digest_prompt` | advisory/write-safe | yes | no | Generate a digest prompt for a proposal. |
| `p2p_clarify_prompt` | advisory/write-safe | yes | no | Generate a clarification prompt for a proposal. |
| `p2p_synthesize_prompt` | advisory/write-safe | yes | no | Generate a synthesis prompt for a proposal. |
| `p2p_plan_prompt` | advisory/write-safe | yes | no | Generate a planning prompt for a proposal. |
| `p2p_tasks_prompt` | advisory/write-safe | yes | no | Generate a task prompt for a proposal. |
| `p2p_swot_prompt` | advisory/write-safe | yes | no | Generate a SWOT prompt for a proposal. |
| `p2p_impact_prompt` | advisory/write-safe | yes | no | Generate an impact-analysis prompt for a proposal. |
| `p2p_spec_prompt` | advisory/write-safe | yes | no | Generate a software-spec refinement prompt for a Change Set. |

## Project Vertical Transition Boundary

The MCP catalog intentionally has no install, adopt or migrate preview/apply
tool. Those owner-governed mutations remain CLI-only because they require the
typed `p2p-vertical-transition-impact/v1` review, an optional exact
`p2p-vertical-transition-plan/v1`, a replacement state-bound preview token,
explicit confirmation and a stable idempotency key.

The project-structure export MCP surface is also read-only. MCP exposes
`p2p_project_structure_export_eligibility` and
`p2p_project_structure_export_preview` so an agent can inspect eligibility,
metadata validation, lineage decisions and the exact source token. MCP does not
expose an apply/export-writing tool and cannot create a draft, choose a package
destination, write a `.p2pv`, publish remotely or claim publisher ownership.

Project-structure replacement has the same MCP read-only boundary. MCP exposes
`p2p_project_structure_replacement_inspect` and
`p2p_project_structure_replacement_preview` for already local, bundled or
cached exact releases. It does not pull missing releases, choose a destination,
create receipts, expose an MCP replacement apply tool, publish remotely, grant
publisher ownership or subscribe the project to future release
updates. Confirmed replacement apply remains a CLI JSON workflow using
`p2p project structure replace apply`, `project.structure.replace`, exact source
revisions, a complete `p2p-structure-replacement-plan/v1`, a preview token,
explicit confirmation and one operation key.

Selective merge and forward restore keep that boundary. MCP exposes only
`p2p_project_structure_merge_compare` and
`p2p_project_structure_retained_inspect`. It has no merge or restore preview,
apply, status or recovery mutation tool. Confirmed transitions remain CLI JSON
workflows with an exact typed plan, current source/target and memory revisions,
an unexpired preview token, the distinct `project.structure.merge` or
`project.structure.restore` capability, confirmation and one operation key.

MCP clients may inspect the canonical project structure and its history, plus
transitional vertical/lock metadata, context, definition, readiness, proposals
and structured contributions with registered read tools.
They must not translate those reads into direct `.p2p` writes or call an
unregistered lifecycle mutation. WaveKit may offer its own authenticated HTTP
MCP workflow, but its serialized P2P worker still uses the CLI JSON
`--operation-key` contract for retryable writes and status recovery.

## Proposal Artifact Content Imports

Proposal artifact import tools are write-safe content tools. They write only
fixed proposal artifact targets and never accept, reject, defer, publish,
merge, finalize, or otherwise decide a proposal.

Project publication MCP tools write only derived files under `outputs/`. They do
not mutate `.p2p/`, run an external curator/model, or expose owner review.
Prepare/import/validate/render accept optional `language` and `output_name`;
prepare also accepts `contributions`, while import accepts `model` and
`evidence_accounting`. Omitted edition fields preserve the `project-en` default.
Owner publication review remains a CLI/human action and is isolated per edition.

Use exactly one input mode per call:

```text
source     existing file or directory path; relative paths resolve from project root
content    direct string payload for the primary target
artifacts  object mapping allowlisted filenames to string payloads
```

Primary `content` targets:

| Tool | Target |
| --- | --- |
| `p2p_explore_import` | `exploration.md` |
| `p2p_impact_import` | `impact-map.yml` |
| `p2p_clarify_import` | `clarifications.md` |
| `p2p_synthesize_import` | `proposal.md` |
| `p2p_plan_import` | `execution-plan.md` |
| `p2p_tasks_import` | `tasks.yml` |

`artifacts` mode is supported only for exploration and impact imports.

Exploration artifact filenames:

```text
exploration.md
findings.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

These filenames are import targets, not guaranteed scaffold files. A newly
created proposal may omit narrative artifacts until an explicit import or
generation step materializes content. MCP clients should use contribution,
prompt, import, readiness, and artifact-state tools instead of writing arbitrary
files under `.p2p/`.

Impact artifact filenames and required top-level YAML keys:

```text
impact-map.yml          impact
related-proposals.yml   related_proposals
conflict-analysis.yml   conflicts
```

Example direct payload import:

```json
{
  "proposal_id": "PROP-001",
  "content": "tasks: []\n"
}
```

Example source-path import:

```json
{
  "proposal_id": "PROP-001",
  "source": "outputs/proposal-tasks.yml"
}
```

The import tools return `artifact_import` metadata with the proposal ID, import
kind, input mode, imported paths, filenames, validation flags, and
`artifact_state_updated: false`.

Artifact content import is separate from artifact coverage state. Use
`p2p_proposal_artifact_status`, `p2p_proposal_artifact_set`, and
`p2p_proposal_artifact_confirm` when the owner or agent needs to record whether
an artifact is required, satisfied, deferred, not applicable, or confirmed.
`p2p_proposal_artifact_status` also returns `artifact_status`, a read-only
logical catalog with expectation, status, materialization kind, source hint,
provenance confidence, evidence path when present, summary, and next action.

`p2p_proposal_show` accepts `full: true` for the owner-facing review payload.
The response keeps the compact `proposal` field, always adds protocol-native
`proposal_detail` aligned with `p2p proposal show --format json`, and adds
`proposal_view` when `full` is true. These include core sections, decision,
readiness, contributions, grouped question sources, narrative/imported artifact
summaries, artifact status, and next actions. Returned paths are backing
evidence or source hints, not direct edit targets.

`p2p_proposal_contribution_list` returns legacy `contributions` plus
`contribution_list`, a bounded protocol-native payload aligned with the CLI
contribution-list contract. MCP does not wrap these payloads in `p2p-cli/v1`.

Unsupported generic artifact writes remain unsupported. Agents should report the
missing primitive instead of writing arbitrary files under `.p2p/`.

MCP exposes token-bound proposal decision preview/apply tools. Their optional
`authority_context` object is the same closed `p2p-authority-context/v1`
contract accepted by the generic decision CLI. It records project authority,
authorized subject and actual executor separately; it never accepts arbitrary
provider payloads. Apply requires a
granted `proposal_decision_apply` receipt whose target is exactly
`PROP-XXX@preview-token`; owner authority and executor identity remain
separate. Legacy `p2p_proposal_accept`, `p2p_proposal_reject`, and
`p2p_proposal_defer` tools are preview-only compatibility surfaces. Their old
unbound consent receipts cannot write schema-4 events and are not consumed.
Choice terminal transitions use the same immutable application contract as the
CLI. MCP preview is read-only; apply requires owner-authorized evidence and a
single-use consent bound to the Choice and exact preview token. There is no
Choice edit, reopen or re-decide tool.

It exposes neutral Work planning and read tools, but source-control and delivery
pipeline operations are outside P2P Engine. It still does not expose spec
imports, conflict recording, voting, precedent recording, choice blocking,
provider review creation, remote registry login/pull/publish, or a hosted IAM
model. Remote vertical-registry MCP is limited to explicit read-only domain and
release discovery.

P2P performs no provider network verification. A hosted MCP gateway must
authenticate and authorize before constructing the context and must protect
worker invocation. Local MCP consent remains a separate transport safety gate.
Authority rotation apply is intentionally not exposed over MCP.

For proposal decisions, MCP can prepare the path but cannot grant owner consent:

```text
p2p_proposal_create or p2p_proposal_update
p2p_consent_request
owner grants consent through CLI, UI, or authenticated cloud workflow
p2p_proposal_decision_preview
p2p_proposal_decision_apply
```

`p2p_consent_request` creates a `requested` receipt. Permission-gated tools
still require a `granted` receipt, so a request cannot be reused as approval.

## Example Calls

The exact UI depends on the MCP client, but the payloads follow the same shape.

Read compact context:

```json
{
  "tool": "p2p_context",
  "arguments": {
    "root": "/path/to/project",
    "budget": "small"
  }
}
```

Read the bounded decision neighborhood for one proposal:

```json
{
  "tool": "p2p_context",
  "arguments": {
    "root": "/path/to/project",
    "target": "PROP-001",
    "budget": "medium"
  }
}
```

The MCP payload is JSON-ready and matches the workspace/CLI structured model.
An empty neighborhood has `hits: []`, `empty_reason` and a
`DC-RETRIEVAL-EMPTY` diagnostic. Retrieval does not write a cache or manifest.

Create a draft proposal:

```json
{
  "tool": "p2p_proposal_create",
  "arguments": {
    "root": "/path/to/project",
    "title": "Document MCP safety boundaries",
    "problem": "Agents need clear rules for which MCP tools can mutate state.",
    "goals": ["Make tool safety understandable."],
    "non_goals": ["Allow agents to decide owner governance outcomes."],
    "proposal": "Document each MCP tool as read-only, write-safe, or advisory.",
    "acceptance_criteria": ["A reader can tell which tools mutate state."]
  }
}
```

Refresh registries after accepted project state changes:

```json
{
  "tool": "p2p_registry_refresh",
  "arguments": {
    "root": "/path/to/project"
  }
}
```

Review project readiness:

```json
{
  "tool": "p2p_project_readiness_review",
  "arguments": {
    "root": "/path/to/project"
  }
}
```

Project-question and convergence mutations are intentionally absent from MCP in
this release. Use the owner-authorized CLI commands. Write parity requires a
separate consent-gated proposal after the CLI payloads have usage evidence and
stable semantics.

Use a permission-gated proposal decision operation after obtaining its preview
token:

```bash
p2p permissions actor add lorenzo --role contributor
p2p consent grant proposal_decision_apply PROP-001@PREVIEW-TOKEN \
  --actor lorenzo --approved-by owner
```

```json
{
  "tool": "p2p_proposal_decision_apply",
  "arguments": {
    "root": "/path/to/project",
    "proposal_id": "PROP-001",
    "decision": "accept",
    "preview_token": "PREVIEW-TOKEN",
    "actor_id": "lorenzo",
    "consent_id": "CONSENT-001"
  }
}
```

Current consent operation to decision tool mapping:

```text
proposal_decision_apply   -> p2p_proposal_decision_apply
```

The `proposal_decision_apply` target is
`PROP-XXX@<preview-token>`. Legacy `proposal_accept`,
`proposal_reject`, and `proposal_defer` receipts have no write mapping in
schema v3.

Logical Work flow:

```text
p2p_work_plan
p2p_work_list
p2p_work_status
p2p_work_show
```

P2P Work records describe logical project-state handoffs only. Source-control,
review, merge and delivery operations belong to external implementation tooling.

The local MCP server runs in the caller's local execution context. Remote HTTP
MCP, Wavekit user authentication, client grants, strong receipts, hosted audit
retention, tenancy, billing, and rate limits belong in a gateway layer outside
the P2P Engine core. A gateway can call the same core lifecycle methods, but it
must enforce its own remote identity and authorization policy before invoking
these local operations.

## Troubleshooting

Server cannot start:

```bash
p2p doctor --root /path/to/project
/absolute/path/reported/by/p2p-doctor/python -m p2p_engine.mcp.server --root /path/to/project
```

If this is an existing pip/virtualenv fallback, `doctor` also recognizes
`.venv/bin/python` and `.venv\Scripts\python.exe`. It never recommends a
nonexistent project-local interpreter.

Agent is reading too much:

```text
Use p2p_context first and follow the "Do not read" guidance in the context packet.
```

Agent wants to perform a governance decision:

```text
Stop unless the owner has explicitly instructed the action and the MCP tool has
a matching consent receipt. Use CLI or explicit permission-gated MCP tools only.
```

Tool appears missing:

```bash
python -m p2p_engine.mcp.server --help
p2p --help
```

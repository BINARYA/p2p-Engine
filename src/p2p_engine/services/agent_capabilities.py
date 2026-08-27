from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


AGENT_CAPABILITY_CATALOG_VERSION = "agent-capabilities-v9"


@dataclass(frozen=True)
class AgentCapability:
    capability_id: str
    cli_paths: tuple[str, ...]
    mcp_tools: tuple[str, ...]
    exposure: str
    authority: str
    reason: str
    adapters: tuple[str, ...] = ("generic", "codex", "claude")


AGENT_CAPABILITIES = (
    AgentCapability(
        capability_id="project.inspect",
        cli_paths=(
            "p2p status",
            "p2p context",
            "p2p project context",
            "p2p project definition show",
        ),
        mcp_tools=(
            "p2p_project_status",
            "p2p_context",
            "p2p_project_context",
            "p2p_project_definition_show",
        ),
        exposure="cli_and_mcp",
        authority="read_only",
        reason="Project inspection is safe on both local agent surfaces.",
    ),
    AgentCapability(
        capability_id="project.domain.classification",
        cli_paths=(
            "p2p project domain show",
            "p2p project domain set",
            "p2p project domain clear",
        ),
        mcp_tools=(
            "p2p_project_domain_show",
            "p2p_project_domain_set",
            "p2p_project_domain_clear",
        ),
        exposure="owner_governed",
        authority="project_domain_change",
        reason=(
            "Project domain is portable classification only; changing it is "
            "receipt-backed and never changes project structure."
        ),
    ),
    AgentCapability(
        capability_id="project.structure.manage",
        cli_paths=(
            "p2p project structure show",
            "p2p project structure history",
            "p2p project structure add-section",
            "p2p project structure update-metadata",
            "p2p project structure reorder",
        ),
        mcp_tools=(
            "p2p_project_structure_show",
            "p2p_project_structure_history",
            "p2p_project_structure_add_section",
            "p2p_project_structure_update_metadata",
            "p2p_project_structure_reorder_sections",
        ),
        exposure="owner_governed",
        authority="project.structure.edit",
        reason=(
            "Project structure is the detached live shape; simple writes are "
            "revision-checked, receipt-backed and consent-gated on MCP."
        ),
    ),
    AgentCapability(
        capability_id="project.memory.classification",
        cli_paths=(
            "p2p project memory classification",
            "p2p proposal scope show",
            "p2p proposal scope set",
        ),
        mcp_tools=(
            "p2p_project_memory_classification",
            "p2p_proposal_scope_show",
            "p2p_proposal_scope_set",
        ),
        exposure="owner_governed",
        authority="project.memory.classify",
        reason=(
            "Classification is a separate organizational axis; scope writes are "
            "revision-checked and receipt-backed and never authorize decisions or "
            "change readiness."
        ),
    ),
    AgentCapability(
        capability_id="project.structure.retirement",
        cli_paths=(
            "p2p project structure retire preview",
            "p2p project structure retire apply",
            "p2p project structure retire status",
        ),
        mcp_tools=(
            "p2p_project_structure_retirement_preview",
            "p2p_project_structure_retirement_apply",
        ),
        exposure="owner_governed",
        authority="project.structure.retire",
        reason=(
            "Retirement is impact-previewed, disposition-driven, and applied as "
            "one receipt-backed structure and memory mutation."
        ),
    ),
    AgentCapability(
        capability_id="project.structure.replacement",
        cli_paths=(
            "p2p project structure replace preview",
            "p2p project structure replace apply",
            "p2p project structure replace status",
        ),
        mcp_tools=(
            "p2p_project_structure_replacement_inspect",
            "p2p_project_structure_replacement_preview",
        ),
        exposure="cli_apply_mcp_read_only",
        authority="project.structure.replace",
        reason=(
            "Replacement copies one exact schema-3 release into the project-owned "
            "structure with explicit dispositions; MCP can inspect and preview "
            "only, and never applies or acquires a release."
        ),
    ),
    AgentCapability(
        capability_id="proposal.governance",
        cli_paths=(
            "p2p proposal list",
            "p2p proposal show",
            "p2p decision status",
            "p2p decision preview",
            "p2p decision apply",
        ),
        mcp_tools=(
            "p2p_proposal_list",
            "p2p_proposal_show",
            "p2p_proposal_decision_status",
            "p2p_proposal_decision_preview",
            "p2p_proposal_decision_apply",
        ),
        exposure="owner_governed",
        authority="owner_confirmation_for_apply",
        reason="Decision writes remain token-bound and owner controlled on both surfaces.",
    ),
    AgentCapability(
        capability_id="proposal.structured_contributions",
        cli_paths=(
            "p2p proposal contribution add",
            "p2p proposal contribution list",
            "p2p contribution add",
            "p2p contribution list",
        ),
        mcp_tools=(
            "p2p_proposal_contribution_add",
            "p2p_proposal_contribution_list",
        ),
        exposure="cli_and_mcp",
        authority="proposal_memory_write_without_decision",
        reason=(
            "Suggestions, objections, findings, open questions and alternatives "
            "are proposal-bound project memory, not generic chat."
        ),
    ),
    AgentCapability(
        capability_id="wavekit.cli.worker_contract",
        cli_paths=(
            "p2p status",
            "p2p version",
            "p2p runtime status",
            "p2p workspace schema status",
            "p2p workspace transaction status",
            "p2p init",
            "p2p project snapshot",
            "p2p project domain show",
            "p2p project domain set",
            "p2p project domain clear",
            "p2p project structure show",
            "p2p project structure history",
            "p2p project structure add-section",
            "p2p project structure update-metadata",
            "p2p project structure reorder",
            "p2p project structure retire preview",
            "p2p project structure retire apply",
            "p2p project structure retire status",
            "p2p project structure replace preview",
            "p2p project structure replace apply",
            "p2p project structure replace status",
            "p2p project vertical export eligibility",
            "p2p project vertical export preview",
            "p2p project vertical export apply",
            "p2p project memory classification",
            "p2p proposal scope show",
            "p2p proposal scope set",
            "p2p proposal list",
            "p2p proposal show",
            "p2p proposal create",
            "p2p proposal update",
            "p2p proposal contribution add",
            "p2p proposal contribution list",
            "p2p mutation status",
            "p2p vertical domain list",
            "p2p vertical domain search",
            "p2p vertical domain inspect",
            "p2p vertical list",
            "p2p vertical search",
        ),
        mcp_tools=(),
        exposure="cli_only_worker_contract",
        authority="serialized_server_worker",
        reason=(
            "WaveKit worker retries, receipts and recovery use allowlisted CLI "
            "JSON operations with --operation-key, not local MCP stdio."
        ),
    ),
    AgentCapability(
        capability_id="vertical.local.catalog",
        cli_paths=(
            "p2p vertical list",
            "p2p vertical inspect",
            "p2p project vertical list",
            "p2p project vertical show",
            "p2p project vertical validate",
        ),
        mcp_tools=(
            "p2p_project_vertical_list",
            "p2p_project_vertical_show",
            "p2p_project_vertical_validate",
        ),
        exposure="cli_and_mcp",
        authority="read_only",
        reason="MCP inspects project-visible verticals; the CLI also inspects the user catalog.",
    ),
    AgentCapability(
        capability_id="vertical.remote.registry",
        cli_paths=(
            "p2p vertical registry add",
            "p2p vertical registry list",
            "p2p vertical registry remove",
        ),
        mcp_tools=(),
        exposure="local_administration",
        authority="local_user",
        reason="Registry endpoint configuration is user-local administration and is CLI-only.",
    ),
    AgentCapability(
        capability_id="vertical.remote.authentication",
        cli_paths=(
            "p2p vertical login",
            "p2p vertical logout",
        ),
        mcp_tools=(),
        exposure="cli_only",
        authority="authenticated_user",
        reason="Device authorization and local credential removal are not exposed by local MCP.",
    ),
    AgentCapability(
        capability_id="vertical.remote.discovery",
        cli_paths=(
            "p2p vertical list",
            "p2p vertical search",
            "p2p vertical domain list",
            "p2p vertical domain search",
            "p2p vertical domain inspect",
        ),
        mcp_tools=(
            "p2p_vertical_domain_list",
            "p2p_vertical_domain_search",
            "p2p_vertical_domain_inspect",
            "p2p_vertical_release_list",
            "p2p_vertical_release_search",
        ),
        exposure="cli_and_mcp_remote_network_read",
        authority="read_only_authenticated_user_when_private",
        reason=(
            "Remote catalog discovery reads provider metadata only; domain matches and "
            "recommendations do not select structure or write the artifact cache."
        ),
    ),
    AgentCapability(
        capability_id="vertical.remote.obtain",
        cli_paths=(
            "p2p vertical pull",
        ),
        mcp_tools=(),
        exposure="cli_only",
        authority="authenticated_user_when_private",
        reason="Pull is an explicit immutable user-cache write and remains CLI-only.",
    ),
    AgentCapability(
        capability_id="vertical.draft.author",
        cli_paths=(
            "p2p vertical draft create",
            "p2p vertical draft add-local",
            "p2p vertical draft update",
            "p2p vertical draft inspect",
            "p2p vertical draft validate",
            "p2p vertical draft materialize",
            "p2p vertical draft package",
            "p2p vertical draft publish",
        ),
        mcp_tools=(),
        exposure="cli_only",
        authority="local_user_publish_authenticated",
        reason="Draft authoring is a user-local lifecycle; publication uses the configured registry client.",
    ),
    AgentCapability(
        capability_id="vertical.project.authoring",
        cli_paths=(
            "p2p project vertical schema",
            "p2p project vertical scaffold",
            "p2p project vertical inspect",
            "p2p project vertical validate",
            "p2p project vertical package",
        ),
        mcp_tools=(),
        exposure="cli_only",
        authority="local_user",
        reason="Portable pack authoring operates on explicit local paths and is CLI-only.",
    ),
    AgentCapability(
        capability_id="vertical.project.adoption",
        cli_paths=(
            "p2p project vertical install preview",
            "p2p project vertical install apply",
            "p2p project vertical adopt preview",
            "p2p project vertical adopt apply",
            "p2p project vertical migrate preview",
            "p2p project vertical migrate apply",
        ),
        mcp_tools=(),
        exposure="owner_governed",
        authority="owner_confirmation_for_apply",
        reason=(
            "Project pack mutation is a typed preview/decision-plan/apply CLI lifecycle; "
            "apply remains owner-confirmed and idempotency-key bound."
        ),
    ),
)


def capability_catalog_payload() -> dict[str, object]:
    return {
        "version": AGENT_CAPABILITY_CATALOG_VERSION,
        "capabilities": [asdict(capability) for capability in AGENT_CAPABILITIES],
    }


def capability_catalog_sha256() -> str:
    encoded = json.dumps(
        capability_catalog_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def standalone_vertical_guidance() -> str:
    return """P2P Engine can use bundled, local, cached, or remote vertical releases without WaveKit.

Inspect local availability:

```bash
p2p vertical list
p2p vertical inspect <publisher/id@version>
```

Configure and use a remote registry:

```bash
p2p vertical registry add <name> <base-url>
p2p vertical registry list
p2p vertical login <name>
p2p vertical domain list --registry <name>
p2p vertical domain search <query> --registry <name>
p2p vertical domain inspect <domain-external-id> --registry <name>
p2p vertical search <query> --registry <name>
p2p vertical search <query> --registry <name> --domain <domain-external-id>
p2p vertical list --source remote --registry <name> --domain <domain-external-id>
p2p vertical pull <publisher/id@version> --registry <name>
p2p vertical logout <name>
```

The login command performs the registry device-authorization flow. Public
domain and release discovery may work anonymously; private catalog results
require the authenticated user allowed by the registry. Catalog domains are
advisory metadata, not project domains, not project structure, and not evidence
of semantic compatibility. A recommended release is still only an exact
coordinate plus digest; it never triggers pull or initialization by itself.
Pulled releases are checksum-verified and cached as immutable exact
coordinates.

Author or derive a local draft:

```bash
p2p vertical draft create --empty --publisher <publisher> --vertical-id <id> --version <version> --name <name> --license <spdx-id>
p2p vertical draft create --from <publisher/id@version> --publisher <publisher> --vertical-id <id> --version <version> --name <name> --license <spdx-id>
p2p vertical draft update <draft-id> --document <draft.yml> --expected-revision <revision>
p2p vertical draft inspect <draft-id>
p2p vertical draft validate <draft-id>
p2p vertical draft materialize <draft-id> <pack-directory>
p2p vertical draft package <draft-id> <pack.p2pv>
p2p vertical draft add-local <draft-id>
p2p vertical draft publish <draft-id> --registry <name> --idempotency-key <operation-id>
```

Export the active project-owned structure into the same draft/package lifecycle:

```bash
p2p project vertical export eligibility --format json
p2p project vertical export preview --publisher <publisher> --id <id> --version <version> --name <name> --license <spdx-id> --primary-domain-key <key> --primary-domain-name <name> --lineage-mode derived|independent --format json
p2p project vertical export apply --target <pack-directory> --output <pack.p2pv> --publisher <publisher> --id <id> --version <version> --name <name> --license <spdx-id> --primary-domain-key <key> --primary-domain-name <name> --lineage-mode derived|independent --expected-structure-revision <n> --expected-structure-checksum <sha256> --token <preview-token> --idempotency-key <operation-id> --confirm --format json
```

Project structure export requires exact publisher, ID, semantic version, name,
license, domain metadata and an explicit lineage mode. Derived exports bind the
exact parent coordinate and checksum; independent exports omit social parent
lineage but keep required attribution. MCP exposes eligibility and preview only,
and never accepts package destinations or creates drafts/packages.

Replace the active project-owned structure from one exact schema-3 release:

```bash
p2p project structure replace preview <publisher/id@version> --expected-structure-revision <n> --expected-memory-revision <sha256> --format json
p2p project structure replace preview <publisher/id@version> --expected-structure-revision <n> --expected-memory-revision <sha256> --plan <replacement-plan.yml> --format json
p2p project structure replace apply <publisher/id@version> --expected-structure-revision <n> --expected-memory-revision <sha256> --preview-token <token> --operation-key <operation-id> --plan <replacement-plan.yml> --confirm --format json
p2p project structure replace status --operation-key <operation-id> --format json
```

Replacement is a detached copy, not vertical adoption or subscription. The plan
uses `p2p-structure-replacement-plan/v1`, binds the exact target coordinate and
semantic checksum, and resolves every required active-memory disposition.
Authority is `project.structure.replace`; target-release visibility, publisher
ownership, remote publication and moderation rights are separate concerns. MCP
exposes `p2p_project_structure_replacement_inspect` and
`p2p_project_structure_replacement_preview` only.

Remote registry configuration, authentication, pull, draft authoring,
publication, and project install/adopt/migrate are CLI-only. MCP exposes
read-only remote network discovery for domains and releases, plus
project-visible vertical inspection and validation. It does not silently
acquire credentials, write the user cache, publish drafts, pull artifacts, or
perform owner-governed project adoption.

For a project transition, request JSON and inspect
`impact.contract_version == p2p-vertical-transition-impact/v1`. Adoption is
allowed only when `source_state.classification` is `empty`. Migration starts
without `--mapping`; when `required_decisions.total` is non-zero, create an
exact `p2p-vertical-transition-plan/v1` document from those decision IDs and
domain references, re-run preview with `--mapping`, retain the replacement
preview token, then apply with owner confirmation and one stable idempotency
key. Never infer a destination from similar labels or edit `.p2p` directly."""


def wavekit_cli_worker_guidance() -> str:
    return """WaveKit-style server workers use the CLI JSON contract, not local MCP stdio.

Use the same boundary when a deterministic process needs stable machine output,
retry receipts, or recovery after a lost response:

```bash
p2p version --format json
p2p status --format json
p2p runtime status --format json
p2p workspace schema status --format json
p2p workspace transaction status --format json
p2p project snapshot --format json
p2p project memory classification --format json
p2p project domain show --format json
p2p project domain set software --name Software --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p project domain clear --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p project structure retire preview --target section:SECTION-ID --expected-structure-revision REV --expected-memory-revision SHA256 --plan retirement-plan.yml --actor ACTOR --format json
p2p project structure retire apply --target section:SECTION-ID --expected-structure-revision REV --expected-memory-revision SHA256 --preview-token TOKEN --operation-key wavekit:<uuid> --plan retirement-plan.yml --actor ACTOR --confirm --format json
p2p project structure retire status --operation-key wavekit:<uuid> --format json
p2p project structure replace preview <publisher/id@version> --expected-structure-revision REV --expected-memory-revision SHA256 --plan replacement-plan.yml --actor ACTOR --format json
p2p project structure replace apply <publisher/id@version> --expected-structure-revision REV --expected-memory-revision SHA256 --preview-token TOKEN --operation-key wavekit:<uuid> --plan replacement-plan.yml --actor ACTOR --confirm --format json
p2p project structure replace status --operation-key wavekit:<uuid> --format json
p2p project vertical export eligibility --format json
p2p project vertical export preview --publisher publisher --id vertical-id --version 1.0.0 --name "Vertical" --license MIT --primary-domain-key software --primary-domain-name Software --lineage-mode independent --format json
p2p project vertical export apply --target build/vertical --output dist/vertical.p2pv --publisher publisher --id vertical-id --version 1.0.0 --name "Vertical" --license MIT --primary-domain-key software --primary-domain-name Software --lineage-mode independent --expected-structure-revision REV --expected-structure-checksum SHA256 --token TOKEN --idempotency-key wavekit:<uuid> --confirm --actor ACTOR --format json
p2p proposal list --format json
p2p proposal show PROP-XXX --format json
p2p proposal scope show PROP-XXX --format json
p2p proposal scope set PROP-XXX --kind sections --section-id SECTION-ID --expected-memory-revision <sha256> --expected-structure-revision <n> --format json --operation-key wavekit:<uuid>
p2p proposal create "Title" --format json --operation-key wavekit:<uuid>
p2p proposal update PROP-XXX --proposal "..." --format json --operation-key wavekit:<uuid>
p2p proposal contribution add PROP-XXX "Text" --type suggestion --format json --operation-key wavekit:<uuid>
p2p proposal contribution list PROP-XXX --type suggestion --format json
p2p proposal readiness assess PROP-XXX --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p vertical domain list --registry REGISTRY --format json
p2p vertical domain search software --registry REGISTRY --format json
p2p vertical domain inspect DOMAIN-ID --registry REGISTRY --format json
p2p vertical search software --registry REGISTRY --domain DOMAIN-ID --format json
p2p vertical list --source remote --registry REGISTRY --domain DOMAIN-ID --format json
p2p mutation status --operation-key wavekit:<uuid> --format json
```

Every CLI JSON response uses the `p2p-cli/v1` envelope. Inspect `ok`,
`operation`, `data`, `warnings`, and `error`; do not parse human text. Exact
retries reuse the same `--operation-key` only for the same semantic request.
After an uncertain write, inspect `p2p mutation status --operation-key ...`
before retrying.

Proposal creation records explicit `unassigned` scope. Before an accepting or
reinstating decision, assign one or more active sections or explicit
`project_global` scope. Classification is not readiness: changing scope must
not change the definition-completeness score. Capability
`project.memory.classify` authorizes only scope organization and cannot
substitute for `proposal.decide` or `proposal.readiness.override`.

Read `proposal_detail.readiness.freshness` through `p2p proposal show` before
requesting a recalculation. `current` means the stored result matches current
assessment inputs, `stale` means evidence changed or the result predates the
current assessment policy, and `not_assessed` means no snapshot exists. A
WaveKit worker uses the keyed readiness command above only for an explicit
recalculation request; ordinary UI refresh remains read-only.

Registry-v2 domain discovery is a provider-neutral read contract. It may use
remote network access only for explicitly selected registry reads, must reject
protocol v1, and must not imply structure compatibility, artifact pull, project
initialization, publisher ownership, moderation rights, or WaveKit membership
authority.

Local MCP stdio remains an agent tool surface. MCP responses are protocol-native
and are not wrapped in `p2p-cli/v1`; MCP write tools also do not provide the
WaveKit worker receipt boundary. A standalone agent may use MCP when it has an
explicit tool, but a serialized server worker should use the allowlisted CLI
JSON commands above."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


AGENT_CAPABILITY_CATALOG_VERSION = "agent-capabilities-v2"


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
        capability_id="vertical.remote.obtain",
        cli_paths=(
            "p2p vertical search",
            "p2p vertical pull",
        ),
        mcp_tools=(),
        exposure="cli_only",
        authority="authenticated_user_when_private",
        reason="Remote search and immutable user-cache writes are CLI-only in this release.",
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
        reason="Project pack mutation remains preview/apply CLI-only and idempotency-key bound.",
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
p2p vertical search <query> --registry <name>
p2p vertical pull <publisher/id@version> --registry <name>
p2p vertical logout <name>
```

The login command performs the registry device-authorization flow. Public
search may work anonymously; private releases require the authenticated user
allowed by the registry. Pulled releases are checksum-verified and cached as
immutable exact coordinates.

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

Remote registry configuration, authentication, search/pull, draft authoring,
publication, and project install/adopt/migrate are CLI-only in this release.
MCP exposes project-visible vertical inspection and validation, but it does not
silently acquire credentials, write the user cache, publish drafts, or perform
owner-governed project adoption."""

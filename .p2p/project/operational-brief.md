# P2P Engine Operational Brief

## Where We Are

P2P Engine now has a complete local Core/CLI/MCP path for concurrent managed proposal collaboration.

Current state:

- validation is clean;
- registries are current;
- project definition maturity is well defined;
- all Change Sets are completed;
- all Work manifests are retired;
- draft proposals remain and still need normal product review before treating the roadmap as settled.

The MCP server is local and stdio-based. It now exposes both read/status tools and selected permission-gated write tools. It remains an interface to P2P Core, not a hosted IAM system, mediator, web app, or Git provider automation layer.

## Accepted Direction

- P2P Core remains deterministic, provider-neutral, and usable without AI or hosted infrastructure.
- P2P CLI remains the reference local interface.
- Agents must use P2P CLI or explicit MCP tools for managed project state instead of raw Git commands.
- Permission-gated MCP operations use project-declared actors and single-use consent receipts.
- Local/Git-only identity is declarative and auditable, not strong authentication.
- Cloud enforcement depends on Git provider controls such as branch protection, token scopes, and protected main.
- Provider PR/MR creation remains outside Core/MCP unless a dedicated adapter layer is accepted later.

## Implemented Collaboration Surface

CLI now supports:

```text
p2p sync status/fetch/pull/push
p2p proposal branch/status/publish/request-review
p2p proposal accept-branch/reject-branch
p2p proposal merge/finalize/cleanup
p2p proposal scan
```

MCP now includes permission-gated tools for:

```text
p2p_sync_pull
p2p_sync_push
p2p_proposal_publish
p2p_proposal_request_review
p2p_proposal_accept_branch
p2p_proposal_reject_branch
p2p_proposal_merge
p2p_proposal_finalize
p2p_proposal_cleanup
```

These tools require matching consent receipts and record audit metadata.

## Current Gaps

- MCP has been verified by tests and JSON-RPC paths, but still needs a real MCP client configuration smoke test.
- README, install, MCP, and agent setup documentation now describe permission-gated write tools and should be tested by following them from a real client setup.
- The current proposal/MCP collaboration tranche is large and should be reviewed and committed before starting another implementation tranche.
- Work lifecycle MCP parity is not yet decided. Proposal branch lifecycle is complete through permission-gated MCP, but Work publish/finalize/accept/cleanup MCP parity needs an explicit product decision.
- Provider PR/MR automation is intentionally not implemented.
- A future API/IAM server remains optional and should be introduced only through a new accepted proposal.
- Draft proposals remain open and should be reviewed or retired as normal roadmap hygiene.

## Recommended Next Actions

1. Verify the MCP server from a real MCP-capable client.
   Reason: tests cover the internal JSON-RPC path, but agent/client configuration must prove the tool schemas, stdio command, root handling, and permission-gated calls work outside the test harness.
   Command: `p2p-mcp-server --root /path/to/project`

2. Verify the documented MCP setup path.
   Reason: README, install, MCP, and agent docs now explain permission-gated write tools; the next check is whether a user can follow them successfully from a real MCP client.
   Command: follow `docs/INSTALL.md` and `docs/MCP.md` to configure a real MCP client.

3. Review remaining draft proposals.
   Reason: readiness is limited mainly by unsettled draft roadmap items, not by active implementation work.
   Command: `.venv/bin/p2p proposal list --status draft`

4. Consolidate the completed proposal/MCP collaboration tranche.
   Reason: the tranche is large, tests pass, and the project state is aligned; review and commit it before adding new scope.
   Command: review current diff and prepare commit for the completed proposal/MCP collaboration tranche.

5. Decide whether Work lifecycle MCP parity is in scope.
   Reason: proposal branch lifecycle is complete through permission-gated MCP, but Work publish/finalize/accept/cleanup MCP parity remains a product decision.
   Command: decide whether to create a proposal for permission-gated Work MCP lifecycle tools.

6. Decide whether provider PR/MR automation belongs in a future adapter.
   Reason: request-review currently records provider-agnostic handoff metadata only; opening GitHub PRs or GitLab MRs should remain outside Core/MCP unless accepted separately.
   Command: decide whether provider PR/MR automation belongs in a future adapter proposal.

## Not Yet

- Do not add provider PR/MR automation without a new accepted proposal and Change Set.
- Do not treat local actor names as strong authentication.
- Do not move direct AI/provider invocation into Core or MCP.
- Do not bypass P2P-managed Git commands for proposal collaboration unless the owner explicitly authorizes an escape hatch.

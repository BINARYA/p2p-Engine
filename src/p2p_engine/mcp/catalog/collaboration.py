from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            'p2p_sync_status',
            (
                'Read-only managed Git sync tool: show repository, branch, remote, '
                'clean-worktree, and sync readiness without running Git transport.'
            ),
            {'root': {'type': 'string'}, 'remote': {'type': 'string'}},
        ),
        _tool(
            'p2p_sync_fetch',
            (
                'Managed Git sync tool: fetch configured remote refs through P2P remote-profile '
                'validation. Does not merge, pull, push, or decide.'
            ),
            {'root': {'type': 'string'}, 'remote': {'type': 'string'}},
        ),
        _tool(
            'p2p_sync_pull',
            (
                'Permission-gated managed Git sync tool: fast-forward pull the current branch '
                'only with a valid sync_pull consent receipt. Does not merge divergent history.'
            ),
            {'root': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'remote': {'type': 'string'}},
            ['actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_sync_push',
            (
                'Permission-gated managed Git sync tool: push the current branch only with a '
                'valid sync_push consent receipt. Does not merge or open PRs.'
            ),
            {'root': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'remote': {'type': 'string'}},
            ['actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_proposal_branch',
            (
                'Managed proposal collaboration tool: create and check out a P2P proposal '
                'branch with actor metadata from an explicit safe base branch. Does not '
                'publish, accept, reject, or merge.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor': {'type': 'string'},
             'base_branch': {'type': 'string'},
             'allow_proposal_base': {'type': 'boolean'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_draft_commit',
            (
                'Managed proposal collaboration tool: commit current draft proposal changes '
                'before creating a proposal branch. Does not publish, push, or decide.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_branch_status',
            'Show one managed proposal branch status and metadata.',
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_publish',
            (
                'Permission-gated managed proposal collaboration tool: publish the current '
                'proposal branch only with a valid consent receipt matching operation '
                'proposal_publish, target proposal_id, and actor_id. Does not open provider PRs '
                'or merge.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'remote': {'type': 'string'},
             'auto_renumber': {'type': 'boolean'}},
            ['proposal_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_proposal_request_review',
            (
                'Permission-gated managed proposal collaboration tool: record review handoff '
                'metadata only with a valid proposal_request_review consent receipt. Does not '
                'open provider PRs or merge.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'provider': {'type': 'string', 'enum': ['generic', 'github', 'gitlab']}},
            ['proposal_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_proposal_accept',
            (
                'Deprecated compatibility tool: return a token-bound acceptance preview. '
                'Legacy proposal_accept consent cannot write a schema-v3 event; apply through '
                'p2p_proposal_decision_apply with preview-bound consent.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'owner_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['proposal_id', 'actor_id', 'consent_id', 'reason'],
        ),
        _tool(
            'p2p_proposal_reject',
            (
                'Deprecated compatibility tool: return a token-bound rejection preview. '
                'Legacy proposal_reject consent cannot write a schema-v3 event; apply through '
                'p2p_proposal_decision_apply with preview-bound consent.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'owner_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['proposal_id', 'actor_id', 'consent_id', 'reason'],
        ),
        _tool(
            'p2p_proposal_defer',
            (
                'Deprecated compatibility tool: return a token-bound deferral preview. '
                'Legacy proposal_defer consent cannot write a schema-v3 event; apply through '
                'p2p_proposal_decision_apply with preview-bound consent.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'owner_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['proposal_id', 'actor_id', 'consent_id', 'reason'],
        ),
        _tool(
            'p2p_proposal_accept_branch',
            (
                'Permission-gated managed proposal collaboration tool: record an '
                'owner-controlled governance acceptance for a proposal branch. Does not merge, '
                'finalize, or cleanup.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['proposal_id', 'actor_id', 'consent_id', 'reason'],
        ),
        _tool(
            'p2p_proposal_reject_branch',
            (
                'Permission-gated managed proposal collaboration tool: record an '
                'owner-controlled governance rejection for a proposal branch. Does not merge, '
                'finalize, or cleanup.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['proposal_id', 'actor_id', 'consent_id', 'reason'],
        ),
        _tool(
            'p2p_proposal_merge',
            (
                'Permission-gated managed proposal collaboration tool: merge a proposal branch '
                'into its base branch with a valid proposal_merge consent receipt. Does not '
                'finalize or cleanup.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'}},
            ['proposal_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_proposal_finalize',
            (
                'Permission-gated managed proposal collaboration tool: finalize a merged '
                'proposal branch by pushing its base branch with a valid proposal_finalize '
                'consent receipt. Does not cleanup or delete branches.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'remote': {'type': 'string'}},
            ['proposal_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_proposal_cleanup',
            (
                'Permission-gated managed proposal collaboration tool: delete a finalized, '
                'rejected, or retired managed proposal branch with a valid proposal_cleanup '
                'consent receipt. Deletes the remote branch only when delete_remote is true.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'delete_remote': {'type': 'boolean'},
             'remote': {'type': 'string'}},
            ['proposal_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_proposal_branch_scan',
            (
                'Read-oriented managed proposal collaboration tool: scan local p2p/proposal/* '
                'branches and refresh the proposal branch registry.'
            ),
            {'root': {'type': 'string'}},
        ),
    ]

from __future__ import annotations

from p2p_engine.core.software_spec_lifecycle import SPEC_LIFECYCLE_INTENTS
from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            'p2p_change_status',
            'List Change Set statuses.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_change_show',
            'Show one Change Set summary.',
            {'root': {'type': 'string'}, 'change_id': {'type': 'string'}},
            ['change_id'],
        ),
        _tool(
            'p2p_change_tasks',
            'Show one Change Set task and action view.',
            {'root': {'type': 'string'}, 'change_id': {'type': 'string'}},
            ['change_id'],
        ),
        _tool(
            'p2p_work_list',
            'List P2P Work manifests.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_work_status',
            'Show operational Work item summaries.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_work_show',
            'Show one P2P Work manifest.',
            {'root': {'type': 'string'}, 'work_id': {'type': 'string'}},
            ['work_id'],
        ),
        _tool(
            'p2p_work_branch',
            (
                'Local MCP Work lifecycle tool: create and checkout the managed Work branch. '
                'Does not publish, merge, finalize, cleanup, or create provider PR/MR records.'
            ),
            {'root': {'type': 'string'}, 'work_id': {'type': 'string'}},
            ['work_id'],
        ),
        _tool(
            'p2p_work_submit',
            (
                'Local MCP Work lifecycle tool: commit implementation changes on the managed '
                'Work branch. Does not publish, merge, finalize, cleanup, or create provider '
                'PR/MR records.'
            ),
            {'root': {'type': 'string'}, 'work_id': {'type': 'string'}},
            ['work_id'],
        ),
        _tool(
            'p2p_work_review',
            (
                'Local MCP Work lifecycle tool: record local Work review readiness. Does not '
                'publish, merge, finalize, cleanup, or create provider PR/MR records.'
            ),
            {'root': {'type': 'string'}, 'work_id': {'type': 'string'}},
            ['work_id'],
        ),
        _tool(
            'p2p_spec_lifecycle',
            (
                'Read-only advisory tool: show the governed software specification lifecycle '
                'route and preflight diagnostics for a requested intent.'
            ),
            {'root': {'type': 'string'},
             'intent': {'type': 'string', 'enum': list(SPEC_LIFECYCLE_INTENTS)},
             'change_id': {'type': 'string'},
             'target': {'type': 'string'}},
        ),
        _tool(
            'p2p_spec_status',
            'List generated P2P-native software specs.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_spec_show',
            'Show a generated P2P-native software spec index.',
            {'root': {'type': 'string'}, 'change_id': {'type': 'string'}},
            ['change_id'],
        ),
        _tool(
            'p2p_spec_export_status',
            'List generated software spec exports.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_spec_export_show',
            'Show the primary document for an existing software spec export.',
            {'root': {'type': 'string'},
             'change_id': {'type': 'string'},
             'target': {'type': 'string', 'enum': ['generic', 'openspec', 'speckit']}},
            ['change_id', 'target'],
        ),
        _tool(
            'p2p_change_create',
            (
                'Write-safe deterministic tool: create a metadata-only Change Set from an '
                'accepted proposal. Does not update status, branch, commit, or merge.'
            ),
            {'root': {'type': 'string'},
             'source': {'type': 'string'},
             'title': {'type': 'string'}},
            ['source'],
        ),
        _tool(
            'p2p_project_refresh',
            (
                'Write-safe deterministic tool: refresh generated project definition files from '
                'accepted P2P state. Does not make governance decisions.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_spec_refresh',
            (
                'Write-safe deterministic tool: generate a P2P-native software spec from a '
                'Change Set. Does not import external edits.'
            ),
            {'root': {'type': 'string'}, 'change_id': {'type': 'string'}},
            ['change_id'],
        ),
        _tool(
            'p2p_spec_export',
            (
                'Write-safe deterministic tool: export generated spec artifacts for generic, '
                'OpenSpec, or Spec Kit targets.'
            ),
            {'root': {'type': 'string'},
             'change_id': {'type': 'string'},
             'target': {'type': 'string', 'enum': ['generic', 'openspec', 'speckit']}},
            ['change_id', 'target'],
        ),
        _tool(
            'p2p_spec_export_validate',
            'Read-only validation tool: validate an existing software spec export.',
            {'root': {'type': 'string'},
             'change_id': {'type': 'string'},
             'target': {'type': 'string', 'enum': ['generic', 'openspec', 'speckit']}},
            ['change_id', 'target'],
        ),
        _tool(
            'p2p_work_plan',
            (
                'Write-safe deterministic tool: create a Work manifest from a validated spec '
                'export. Does not create branches, commits, PRs, or merges.'
            ),
            {'root': {'type': 'string'},
             'change_id': {'type': 'string'},
             'target': {'type': 'string', 'enum': ['generic', 'openspec', 'speckit']}},
            ['change_id', 'target'],
        ),
        _tool(
            'p2p_work_publish',
            (
                'Consent-gated local MCP Work lifecycle tool: publish a reviewed managed Work '
                'branch to a configured Git remote. Requires a granted work_publish consent '
                'receipt and does not create provider PR/MR records.'
            ),
            {'root': {'type': 'string'},
             'work_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'remote': {'type': 'string'}},
            ['work_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_work_request_review',
            (
                'Consent-gated local MCP Work lifecycle tool: record provider-advisory Work '
                'review metadata. Requires a granted work_request_review consent receipt and '
                'does not create provider PR/MR records.'
            ),
            {'root': {'type': 'string'},
             'work_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'provider': {'type': 'string', 'enum': ['generic', 'github', 'gitlab']}},
            ['work_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_work_accept',
            (
                'Consent-gated local MCP Work lifecycle tool: merge a published managed Work '
                'branch into its base branch. Requires a granted work_accept consent receipt. '
                'Does not finalize, push the base branch, or cleanup branches.'
            ),
            {'root': {'type': 'string'},
             'work_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'}},
            ['work_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_work_finalize',
            (
                'Consent-gated local MCP Work lifecycle tool: finalize an accepted Work item '
                'by pushing its base branch. Requires a granted work_finalize consent receipt. '
                'Does not cleanup branches.'
            ),
            {'root': {'type': 'string'},
             'work_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'remote': {'type': 'string'}},
            ['work_id', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_work_cleanup',
            (
                'Consent-gated local MCP Work lifecycle tool: cleanup a finalized managed Work '
                'branch. Requires a granted work_cleanup consent receipt. Remote branch '
                'deletion occurs only when delete_remote is true.'
            ),
            {'root': {'type': 'string'},
             'work_id': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'consent_id': {'type': 'string'},
             'delete_remote': {'type': 'boolean'},
             'remote': {'type': 'string'}},
            ['work_id', 'actor_id', 'consent_id'],
        ),
    ]

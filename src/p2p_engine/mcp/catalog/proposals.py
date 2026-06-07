from __future__ import annotations

from p2p_engine.core.contribution import ContributionType
from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            'p2p_proposal_create',
            (
                'Write-safe draft tool: create a draft P2P proposal using the core proposal '
                'scaffold. Does not accept, reject, defer, or decide.'
            ),
            {'root': {'type': 'string'},
             'title': {'type': 'string'},
             'problem': {'type': 'string'},
             'context': {'type': 'string'},
             'goals': {'type': 'array', 'items': {'type': 'string'}},
             'non_goals': {'type': 'array', 'items': {'type': 'string'}},
             'proposal': {'type': 'string'},
             'acceptance_criteria': {'type': 'array', 'items': {'type': 'string'}}},
            ['title'],
        ),
        _tool(
            'p2p_proposal_update',
            (
                'Write-safe refinement tool: update structured sections of an existing P2P '
                'proposal. Does not accept, reject, defer, or decide.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'problem': {'type': 'string'},
             'context': {'type': 'string'},
             'goals': {'type': 'array', 'items': {'type': 'string'}},
             'non_goals': {'type': 'array', 'items': {'type': 'string'}},
             'proposal': {'type': 'string'},
             'acceptance_criteria': {'type': 'array', 'items': {'type': 'string'}}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_contribution_add',
            (
                'Write-safe contribution tool: append a typed contribution to an existing '
                'proposal. Does not accept, reject, defer, merge, or decide.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'text': {'type': 'string'},
             'type': {'type': 'string',
                      'enum': [item.value for item in ContributionType]},
             'relevance': {'type': 'string'},
             'author': {'type': 'string'}},
            ['proposal_id', 'text'],
        ),
        _tool(
            'p2p_proposal_contribution_list',
            (
                'Read-only proposal contribution tool: list contributions recorded for an '
                'existing proposal.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_impact_prompt',
            (
                'Advisory analysis tool: generate an impact-analysis prompt for an existing '
                'proposal. Does not import impact output or change decisions.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_list',
            'List P2P proposals, optionally filtered by status.',
            {'root': {'type': 'string'}, 'status': {'type': 'string'}},
        ),
        _tool(
            'p2p_proposal_show',
            'Show one P2P proposal summary.',
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_readiness_get',
            (
                'Read-only proposal readiness tool: show the stored readiness assessment or '
                'not_assessed status. Does not refresh or decide.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_readiness_init',
            (
                'Write-safe analysis tool: bootstrap a conservative proposal readiness '
                'assessment from existing proposal artifacts. Does not accept, reject, defer, '
                'override, or decide.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_readiness_refresh',
            (
                'Write-safe analysis tool: refresh a proposal readiness snapshot from stored '
                'assessment evidence. Does not accept, reject, defer, override, or decide.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_readiness_explain',
            (
                'Read-only proposal readiness tool: explain score, failed gates, missing '
                'criteria, and suggested next actions.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_readiness_list_gaps',
            (
                'Read-only proposal readiness tool: list only failed gates, missing criteria, '
                'and suggested next actions for an existing proposal.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_choice_list',
            'List project choices.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_choice_show',
            'Show one project choice.',
            {'root': {'type': 'string'}, 'choice_id': {'type': 'string'}},
            ['choice_id'],
        ),
    ]

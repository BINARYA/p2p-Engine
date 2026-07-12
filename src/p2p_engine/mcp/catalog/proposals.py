from __future__ import annotations

from p2p_engine.core.contribution import ContributionType
from p2p_engine.mcp.catalog.common import tool as _tool


ARTIFACT_IMPORT_TOOLS = {
    'p2p_explore_import': 'exploration',
    'p2p_impact_import': 'impact',
    'p2p_clarify_import': 'clarification',
    'p2p_synthesize_import': 'synthesis/proposal',
    'p2p_plan_import': 'execution plan',
    'p2p_tasks_import': 'tasks',
}


def _artifact_import_tool(name: str, label: str) -> dict[str, object]:
    return _tool(
        name,
        (
            f'Write-safe proposal artifact import tool: import {label} artifact '
            'content into fixed proposal artifact targets. Supports exactly one '
            'of source, content, or artifacts. Does not update artifact coverage '
            'state and does not accept, reject, defer, or decide.'
        ),
        {'root': {'type': 'string'},
         'proposal_id': {'type': 'string'},
         'source': {'type': 'string'},
         'content': {'type': 'string'},
         'artifacts': {'type': 'object', 'additionalProperties': {'type': 'string'}},
         'actor': {'type': 'string'}},
        ['proposal_id'],
    )


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
        *[
            _artifact_import_tool(name, label)
            for name, label in ARTIFACT_IMPORT_TOOLS.items()
        ],
        _tool(
            'p2p_proposal_list',
            'List P2P proposals, optionally filtered by status.',
            {'root': {'type': 'string'}, 'status': {'type': 'string'}},
        ),
        _tool(
            'p2p_proposal_show',
            'Show one P2P proposal summary. Set full=true for the read-only owner review view.',
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}, 'full': {'type': 'boolean'}},
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
            'p2p_proposal_readiness_assess',
            (
                'Write-safe analysis tool: evidence-aware proposal readiness recalculation '
                'from current artifacts and question state. Does not accept, reject, defer, '
                'override, or decide.'
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
            'p2p_proposal_readiness_review',
            (
                'Read-only proposal readiness review tool: explain behavioral guidance, '
                'owner questions, challenge points, and next actions. Does not decide.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_questions_status',
            'Read-only proposal question tool: show question state or not_initialized status.',
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_questions_init',
            (
                'Write-safe proposal question tool: initialize deterministic question state. '
                'Does not decide governance.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}, 'actor': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_questions_add',
            (
                'Write-safe proposal question tool: add a readiness-linked owner question. '
                'Does not decide governance.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'gap': {'type': 'string'},
             'question': {'type': 'string'},
             'priority': {'type': 'string', 'enum': ['high', 'medium', 'low']},
             'rationale': {'type': 'string'},
             'actor': {'type': 'string'}},
            ['proposal_id', 'gap', 'question'],
        ),
        _tool(
            'p2p_proposal_questions_answer',
            (
                'Write-safe proposal question tool: record an answer for one question. '
                'Does not change proposal decision status.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'question_id': {'type': 'string'},
             'answer': {'type': 'string'},
             'source': {'type': 'string'},
             'actor': {'type': 'string'}},
            ['proposal_id', 'question_id', 'answer'],
        ),
        _tool(
            'p2p_proposal_questions_next',
            'Read-only proposal question tool: return the next eligible owner question.',
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_questions_apply',
            (
                'Write-safe proposal question tool: mark answered questions as applied and '
                'return an artifact-aware update plan. Does not decide governance.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}, 'actor': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_artifact_status',
            (
                'Read-only proposal artifact tool: show artifact-aware coverage state or '
                'legacy absence. Does not mutate proposal state.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_artifact_init',
            (
                'Write-safe proposal artifact tool: initialize or refresh artifact-aware '
                'coverage state. Does not accept, reject, defer, override, or decide.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}, 'actor': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_artifact_set',
            (
                'Write-safe proposal artifact tool: set one artifact expectation/status and '
                'rationale. Does not change proposal decision status.'
            ),
            {'root': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'artifact_id': {'type': 'string'},
             'expectation': {'type': 'string',
                             'enum': ['required', 'required_when_applicable', 'optional_memory', 'not_expected']},
             'status': {'type': 'string',
                        'enum': ['unknown', 'missing', 'weak', 'satisfied', 'deferred', 'not_applicable', 'absent_legacy']},
             'reason': {'type': 'string'},
             'actor': {'type': 'string'},
             'source': {'type': 'string'},
             'risk_flags': {'type': 'array', 'items': {'type': 'string'}}},
            ['proposal_id', 'artifact_id'],
        ),
        _tool(
            'p2p_proposal_artifact_confirm',
            (
                'Write-safe proposal artifact tool: record owner confirmation for one '
                'artifact state. Does not accept, reject, defer, override, or decide.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}, 'artifact_id': {'type': 'string'}, 'actor': {'type': 'string'}},
            ['proposal_id', 'artifact_id'],
        ),
        _tool(
            'p2p_proposal_artifact_mark_legacy',
            (
                'Write-safe proposal artifact tool: mark artifact-aware state as advisory '
                'absent_legacy for an older proposal. Does not block or decide.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}, 'reason': {'type': 'string'}, 'actor': {'type': 'string'}},
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

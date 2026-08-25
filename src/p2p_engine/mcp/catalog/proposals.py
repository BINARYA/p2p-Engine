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


def _authority_context_schema() -> dict[str, object]:
    identity = {
        'type': 'object',
        'properties': {
            'id': {'type': 'string', 'maxLength': 256},
            'kind': {
                'type': 'string',
                'enum': ['person', 'user', 'agent', 'mcp_client', 'client', 'service'],
            },
        },
        'required': ['id', 'kind'],
        'additionalProperties': False,
    }
    claim = {
        'type': 'object',
        'properties': {
            'capability': {'type': 'string', 'maxLength': 256},
            'basis': {
                'type': 'string',
                'enum': ['root_authority', 'local_policy', 'capability_grant'],
            },
            'authority_generation': {'type': ['integer', 'null'], 'minimum': 1},
            'grant_ref': {'type': ['string', 'null'], 'maxLength': 256},
            'grant_generation': {'type': ['integer', 'null'], 'minimum': 1},
        },
        'required': ['capability', 'basis'],
        'additionalProperties': False,
    }
    return {
        'type': ['object', 'null'],
        'properties': {
            'schema': {'type': 'string', 'const': 'p2p-authority-context/v1'},
            'mode': {
                'type': 'string',
                'enum': ['local_policy', 'external_attestation'],
            },
            'project_authority': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string', 'maxLength': 256},
                    'generation': {'type': 'integer', 'minimum': 1},
                    'local_policy_version': {'type': ['string', 'null'], 'maxLength': 256},
                    'provider_id': {'type': ['string', 'null'], 'maxLength': 256},
                    'provider_policy_version': {'type': ['string', 'null'], 'maxLength': 256},
                },
                'required': ['id', 'generation'],
                'additionalProperties': False,
            },
            'subject': identity,
            'executor': identity,
            'authorization_decision_id': {'type': 'string', 'maxLength': 256},
            'authorized_at': {'type': ['string', 'null'], 'maxLength': 64},
            'claims': {'type': 'array', 'items': claim, 'minItems': 1, 'maxItems': 16},
        },
        'required': [
            'schema',
            'mode',
            'project_authority',
            'subject',
            'executor',
            'authorization_decision_id',
            'claims',
        ],
        'additionalProperties': False,
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


def _decision_request_properties() -> dict[str, object]:
    return {
        'root': {'type': 'string'},
        'proposal_id': {'type': 'string'},
        'event_type': {
            'type': 'string',
            'enum': [
                'accepted',
                'accepted_with_changes',
                'deferred',
                'withdrawn',
                'rejected',
                'revoked',
                'superseded',
                'split',
                'merged_into_other',
                'reinstated',
            ],
        },
        'reason': {'type': 'string'},
        'owner_id': {'type': 'string'},
        'actor_id': {'type': 'string'},
        'executor_kind': {'type': 'string'},
        'decided_on': {'type': 'string'},
        'operation_key': {'type': 'string'},
        'source_head_event_id': {'type': ['string', 'null']},
        'conditions': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'text': {'type': 'string'},
                },
                'required': ['id', 'text'],
            },
        },
        'lineage': {
            'type': 'object',
            'properties': {
                'kind': {
                    'type': ['string', 'null'],
                    'enum': ['supersedes', 'split', 'merged_into', None],
                },
                'targets': {'type': 'array', 'items': {'type': 'string'}},
            },
        },
        'affected_event_id': {'type': ['string', 'null']},
        'revocation_event_id': {'type': ['string', 'null']},
        'impact_preview_token': {'type': ['string', 'null']},
        'drift_acknowledged': {'type': 'boolean'},
        'readiness_override': {'type': 'boolean'},
        'authority_context': _authority_context_schema(),
    }


def _decision_tool_definitions() -> list[dict[str, object]]:
    request = _decision_request_properties()
    return [
        _tool(
            'p2p_proposal_decision_status',
            'Read-only resolved proposal decision lifecycle, head, intervals, lineage, and diagnostics.',
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_decision_history',
            'Read-only bounded proposal decision event history.',
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                'cursor': {'type': 'string'},
            },
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_decision_impact',
            'Read-only bounded dependency impact for a proposed lifecycle event.',
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'event_type': request['event_type'],
                'source_head_event_id': {'type': ['string', 'null']},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                'cursor': {'type': 'string'},
            },
            ['proposal_id', 'event_type'],
        ),
        _tool(
            'p2p_proposal_decision_preview',
            'Read-only two-phase decision preview. It never records a governance event.',
            request,
            ['proposal_id', 'event_type', 'reason', 'owner_id', 'actor_id'],
        ),
        _tool(
            'p2p_proposal_decision_apply',
            (
                'Permission-gated decision apply using an exact preview and a '
                'proposal_decision_apply consent targeted to PROP-XXX@preview-token.'
            ),
            {
                **request,
                'preview_token': {'type': 'string'},
                'confirm': {'type': 'boolean'},
                'consent_id': {'type': 'string'},
            },
            [
                'proposal_id',
                'event_type',
                'reason',
                'owner_id',
                'actor_id',
                'decided_on',
                'operation_key',
                'preview_token',
                'confirm',
                'consent_id',
            ],
        ),
        _tool(
            'p2p_proposal_decision_projection_repair_preview',
            'Read-only preview for restoring ledger-derived proposal projections.',
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'owner_id': {'type': 'string'},
                'actor_id': {'type': 'string'},
            },
            ['proposal_id', 'owner_id', 'actor_id'],
        ),
        _tool(
            'p2p_proposal_decision_projection_repair_apply',
            'Permission-gated apply for an exact projection-repair preview.',
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'owner_id': {'type': 'string'},
                'actor_id': {'type': 'string'},
                'preview_token': {'type': 'string'},
                'confirm': {'type': 'boolean'},
                'consent_id': {'type': 'string'},
            },
            [
                'proposal_id',
                'owner_id',
                'actor_id',
                'preview_token',
                'confirm',
                'consent_id',
            ],
        ),
        _tool(
            'p2p_proposal_decision_ledger_repair_preview',
            'Read-only preview for a reviewed ledger repair candidate file.',
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'candidate_path': {'type': 'string'},
                'owner_id': {'type': 'string'},
                'actor_id': {'type': 'string'},
            },
            ['proposal_id', 'candidate_path', 'owner_id', 'actor_id'],
        ),
        _tool(
            'p2p_proposal_decision_ledger_repair_apply',
            'Permission-gated apply for an exact ledger-repair preview.',
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'candidate_path': {'type': 'string'},
                'owner_id': {'type': 'string'},
                'actor_id': {'type': 'string'},
                'preview_token': {'type': 'string'},
                'confirm': {'type': 'boolean'},
                'consent_id': {'type': 'string'},
            },
            [
                'proposal_id',
                'candidate_path',
                'owner_id',
                'actor_id',
                'preview_token',
                'confirm',
                'consent_id',
            ],
        ),
    ]


def tool_definitions() -> list[dict[str, object]]:
    return [
        *_decision_tool_definitions(),
        _tool(
            'p2p_proposal_create',
            (
                'Write-safe draft tool: create a draft P2P proposal using the core proposal '
                'scaffold. MCP returns protocol-native payloads, not the p2p-cli/v1 envelope; '
                'WaveKit worker retry/receipt semantics use the CLI --operation-key contract. '
                'Does not accept, reject, defer, or decide.'
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
                'proposal. MCP is protocol-native and does not provide WaveKit CLI receipts. '
                'Does not accept, reject, defer, or decide.'
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
                'proposal. MCP writes project memory directly as an agent tool, but WaveKit '
                'server-worker retries use CLI JSON with --operation-key. Does not accept, '
                'reject, defer, merge, or decide.'
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
                'Read-only proposal contribution tool: list typed contributions recorded for '
                'an existing proposal. Returns protocol-native data semantically aligned with '
                'the CLI contribution list payload, without p2p-cli/v1 wrapping.'
            ),
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'type': {'type': 'string', 'enum': [item.value for item in ContributionType]},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                'offset': {'type': 'integer', 'minimum': 0},
            },
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
            (
                'Read-only proposal list tool: list P2P proposals with protocol-native '
                'summary data semantically aligned with the CLI proposal list contract.'
            ),
            {
                'root': {'type': 'string'},
                'status': {'type': 'string'},
                'decision_state': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                'offset': {'type': 'integer', 'minimum': 0},
            },
        ),
        _tool(
            'p2p_proposal_show',
            (
                'Read-only proposal detail tool: show one P2P proposal and include a bounded '
                'proposal_detail read model aligned with CLI JSON. Set full=true for the '
                'legacy owner review view. MCP responses are not wrapped in p2p-cli/v1.'
            ),
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'full': {'type': 'boolean'},
                'contribution_limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
            },
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
                'from current artifacts and question state, committed atomically. Does not '
                'accept, reject, defer, override, or decide. Freshness is returned with the '
                'readiness result.'
            ),
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'actor': {'type': 'string'},
            },
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
                'Read-only proposal artifact tool: show current artifact-aware coverage '
                'state. Does not mutate proposal state.'
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
                        'enum': ['unknown', 'missing', 'weak', 'satisfied', 'deferred', 'not_applicable']},
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

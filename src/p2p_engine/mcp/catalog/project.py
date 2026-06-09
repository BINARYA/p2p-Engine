from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            'p2p_project_rubrics_init',
            (
                'Write-safe project setup tool: create deterministic project definition rubrics '
                'for a domain. Does not make governance decisions.'
            ),
            {'root': {'type': 'string'},
             'domain': {'type': 'string',
                        'enum': ['none',
                                 'custom',
                                 'generic',
                                 'software',
                                 'grant_document',
                                 'board_game']},
             'force': {'type': 'boolean'}},
        ),
        _tool(
            'p2p_project_rubrics_show',
            'Read configured project definition maturity rubrics.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_maturity_refresh',
            (
                'Write-safe analysis tool: generate deterministic project definition maturity '
                'from configured rubrics. Does not assess implementation completeness.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_maturity_show',
            'Read stored project definition maturity assessment.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_intake_prompt',
            (
                'Write-safe draft tool: create an intake prompt for a raw idea. Does not apply '
                'recommendations or make governance decisions.'
            ),
            {'root': {'type': 'string'}, 'idea': {'type': 'string'}},
            ['idea'],
        ),
        _tool(
            'p2p_intake_status',
            'List intake records and whether analysis artifacts are populated.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_brief_prompt',
            (
                'Advisory workflow tool: create project brief context and prompt artifacts from '
                'current project state. Does not import or decide.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_brief_show',
            'Show the stored operational project brief if one has been imported.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_choice_discover',
            (
                'Advisory analysis tool: discover choice candidates and blockers without '
                'creating, deciding, blocking, or unblocking choices.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_conflict_status',
            'Read recorded project conflicts without recording new conflicts.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_status',
            'Show deterministic P2P project state status.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_export',
            (
                'Write-safe deterministic tool: export the visible human-facing project '
                'definition to outputs/latest/project.md. Does not mutate P2P governance state.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_export_status',
            'Read visible project definition export status and review snapshots.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_vertical_list',
            'Read available project vertical packs and active/fallback status.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_vertical_show',
            'Read a project vertical pack, including inherited base-project sections.',
            {'root': {'type': 'string'}, 'vertical_id': {'type': 'string'}},
            ['vertical_id'],
        ),
        _tool(
            'p2p_project_vertical_validate',
            'Read-only validation tool: validate a project vertical ID, vertical.yml path, or pack directory.',
            {'root': {'type': 'string'}, 'target': {'type': 'string'}},
            ['target'],
        ),
        _tool(
            'p2p_project_vertical_propose',
            (
                'Advisory tool: generate an importable custom vertical candidate from a project idea. '
                'Does not persist or activate project state.'
            ),
            {'root': {'type': 'string'}, 'idea': {'type': 'string'}},
            ['idea'],
        ),
        _tool(
            'p2p_project_vertical_add',
            (
                'Write-safe project setup tool: add a project-local vertical pack. '
                'Does not make governance decisions.'
            ),
            {'root': {'type': 'string'}, 'source': {'type': 'string'}, 'activate': {'type': 'boolean'}, 'actor': {'type': 'string'}},
            ['source'],
        ),
        _tool(
            'p2p_project_vertical_select',
            (
                'Write-safe project setup tool: select the active project vertical. '
                'Does not accept, reject, or change proposals.'
            ),
            {'root': {'type': 'string'}, 'vertical_id': {'type': 'string'}, 'actor': {'type': 'string'}},
            ['vertical_id'],
        ),
        _tool(
            'p2p_project_readiness_review',
            (
                'Advisory review tool: evaluate project capisaldi coverage against the active '
                'or requested vertical without mutating governance state.'
            ),
            {'root': {'type': 'string'}, 'vertical_id': {'type': 'string'}},
        ),
        _tool(
            'p2p_next',
            'Show advisory next actions from P2P project state.',
            {'root': {'type': 'string'}, 'top': {'type': 'integer', 'minimum': 1}},
        ),
        _tool(
            'p2p_next_add',
            (
                'Write-safe project planning tool: add a curated next action. Does not decide '
                'governance, publish, merge, or run external provider operations.'
            ),
            {'root': {'type': 'string'},
             'kind': {'type': 'string'},
             'target': {'type': 'string'},
             'reason': {'type': 'string'},
             'command': {'type': 'string'},
             'priority': {'type': 'string'},
             'action_id': {'type': 'string'}},
            ['kind', 'reason'],
        ),
        _tool(
            'p2p_next_complete',
            (
                'Write-safe project planning tool: complete a curated next action and move it '
                'to the next-action audit log.'
            ),
            {'root': {'type': 'string'},
             'action_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['action_id', 'reason'],
        ),
        _tool(
            'p2p_next_retire',
            (
                'Write-safe project planning tool: retire a curated next action and move it to '
                'the next-action audit log.'
            ),
            {'root': {'type': 'string'},
             'action_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['action_id', 'reason'],
        ),
        _tool(
            'p2p_next_refresh',
            (
                'Write-safe project planning tool: normalize curated next actions and report '
                'generated action count.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_registry_status',
            'Show generated registry availability and freshness checks.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_registry_show',
            'Show a generated P2P registry.',
            {'root': {'type': 'string'}, 'name': {'type': 'string'}},
            ['name'],
        ),
        _tool(
            'p2p_project_show',
            'Show a generated project definition section or feature document.',
            {'root': {'type': 'string'}, 'section': {'type': 'string'}},
            ['section'],
        ),
        _tool(
            'p2p_project_remote_show',
            'Show local/cloud remote project profile metadata.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_remote_configure',
            (
                'Write-safe project setup tool: configure P2P remote profile metadata without '
                'creating provider repositories, opening PRs, or editing Git remotes.'
            ),
            {'root': {'type': 'string'},
             'mode': {'type': 'string', 'enum': ['local', 'remote']},
             'provider': {'type': 'string',
                          'enum': ['local', 'generic', 'github', 'gitlab']},
             'remote': {'type': 'string'},
             'url': {'type': 'string'}},
            ['mode'],
        ),
        _tool(
            'p2p_permissions_show',
            'Read project-declared permission identities and role policy.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_consent_request',
            (
                'Write-safe consent workflow tool: record a pending consent request for an '
                'owner-controlled operation. Does not grant consent and cannot authorize '
                'execution.'
            ),
            {'root': {'type': 'string'},
             'operation': {'type': 'string'},
             'target': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'requested_by': {'type': 'string'},
             'scope': {'type': 'string'},
             'expires_on': {'type': 'string'}},
            ['operation', 'target', 'actor_id'],
        ),
        _tool(
            'p2p_consent_status',
            'List permission-gated consent receipts without creating or consuming them.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_consent_show',
            'Show one permission-gated consent receipt without creating or consuming it.',
            {'root': {'type': 'string'}, 'consent_id': {'type': 'string'}},
            ['consent_id'],
        ),
    ]

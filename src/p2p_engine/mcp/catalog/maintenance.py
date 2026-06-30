from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            'p2p_init_project',
            (
                'Write-safe bootstrap tool: initialize a P2P project and generate agent '
                'boundary instructions. Defaults to all built-in adapters when agent is omitted. '
                'Does not make governance decisions.'
            ),
            {'root': {'type': 'string'},
             'name': {'type': 'string'},
             'agent': {'type': 'string',
                       'enum': ['generic',
                                'codex',
                                'claude',
                                'cursor',
                                'copilot',
                                'gemini',
                                'opencode',
                                'all']},
             'repository': {'type': 'string', 'enum': ['local', 'cloud']},
             'domain': {'type': 'string',
                        'enum': ['none',
                                 'custom',
                                 'generic',
                                 'software',
                                 'grant_document',
                                 'board_game']}},
            ['name'],
        ),
        _tool(
            'p2p_registry_refresh',
            (
                'Write-safe maintenance tool: regenerate deterministic P2P registries from '
                'existing project state. Does not decide or mutate proposals.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_validate',
            (
                'Read-only validation tool: report structural and semantic P2P findings. Does '
                'not repair, refresh, or mutate project state.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_context',
            (
                'Read-only token-aware context tool: return a compact deterministic context '
                'packet for agents before broad file reads.'
            ),
            {'root': {'type': 'string'},
             'budget': {'type': 'string', 'enum': ['small', 'medium']},
             'target': {'type': 'string'}},
        ),
        _tool(
            'p2p_assess_refresh',
            (
                'Write-safe analysis tool: generate a deterministic project readiness '
                'assessment from current P2P state. Does not make governance decisions.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_assess_show',
            (
                'Read-only analysis tool: show the stored project readiness assessment. Does '
                'not refresh or mutate project state.'
            ),
            {'root': {'type': 'string'}},
        ),
    ]

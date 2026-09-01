from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            'p2p_integration_status',
            (
                'Read-only project integration status: report access profile, independent '
                'contract versions, artifact ownership, and drift without changing host files.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_agent_list',
            (
                'Read-only agent integration tool: list supported and installed agent '
                'integrations, including drift status.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_agent_show',
            (
                "Read-only agent integration tool: show one adapter's managed files, "
                'capabilities, and drift status.'
            ),
            {'root': {'type': 'string'},
             'adapter': {'type': 'string',
                         'enum': ['generic',
                                  'codex',
                                  'claude',
                                  'cursor',
                                  'copilot',
                                  'gemini',
                                  'opencode']}},
            ['adapter'],
        ),
        _tool(
            'p2p_agent_doctor',
            (
                'Read-only agent integration doctor: return structured health findings for '
                'registry, managed files, hashes, shared ownership, and generic baseline.'
            ),
            {'root': {'type': 'string'},
             'adapter': {'type': 'string',
                         'enum': ['generic',
                                  'codex',
                                  'claude',
                                  'cursor',
                                  'copilot',
                                  'gemini',
                                  'opencode',
                                  'all']}},
        ),
    ]

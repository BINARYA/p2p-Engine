from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            'p2p_agent_instructions_refresh',
            (
                'Write-safe bootstrap tool: add or refresh agent instructions and agent policy.'
                'Does not remove other profiles or make decisions.'
            ),
            {'root': {'type': 'string'},
             'profile': {'type': 'string',
                         'enum': ['generic',
                                  'codex',
                                  'claude',
                                  'cursor',
                                  'copilot',
                                  'gemini',
                                  'opencode',
                                  'all']}},
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
        _tool(
            'p2p_agent_install',
            (
                'Write-safe agent integration tool: install generated project-local agent files '
                'and update the registry without making governance decisions.'
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
                                  'all']},
             'force': {'type': 'boolean'}},
            ['adapter'],
        ),
        _tool(
            'p2p_agent_update',
            (
                'Write-safe agent integration tool: update generated files when safe and report '
                'drifted files instead of overwriting them silently.'
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
                                  'all']},
             'force': {'type': 'boolean'}},
            ['adapter'],
        ),
        _tool(
            'p2p_agent_uninstall',
            (
                'Write-safe agent integration tool: remove only safe, managed, unchanged, '
                'non-shared files for one adapter.'
            ),
            {'root': {'type': 'string'},
             'adapter': {'type': 'string',
                         'enum': ['codex',
                                  'claude',
                                  'cursor',
                                  'copilot',
                                  'gemini',
                                  'opencode']}},
            ['adapter'],
        ),
    ]

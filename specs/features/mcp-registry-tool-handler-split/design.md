# MCP Registry Tool Handler Split Design

## Current Shape

`src/p2p_engine/mcp/tools.py` currently owns both:

- public MCP registry data: `TOOL_NAMES`, prompt tool kinds, JSON schemas, and `tool_definitions()`;
- runtime execution: `call_tool()`, dispatch branches, argument conversion, consent-gated wrappers, and JSON conversion.

That makes the module hard to review because declaration-only changes are mixed with operational behavior.

## Target Shape

Introduce `src/p2p_engine/mcp/registry.py` as the declaration module.

The registry module owns:

- `TOOL_NAMES`;
- `PROMPT_TOOL_KINDS`;
- `_schema()`;
- prompt tool definition construction;
- `tool_definitions()`.

`src/p2p_engine/mcp/tools.py` remains the compatibility module and imports:

- `TOOL_NAMES`;
- `PROMPT_TOOL_KINDS`;
- `tool_definitions()`.

`call_tool()` remains in `tools.py` during the first extraction phase to preserve behavior and reduce risk.

## Follow-Up Handler Split

After registry extraction is verified, dispatch branches can be grouped by domain:

- agent/bootstrap tools;
- project/context/assessment tools;
- proposal document/readiness/decision tools;
- branch/sync/consent tools;
- spec/export/work tools;
- prompt tools.

The follow-up must keep one public `call_tool()` facade until callers are migrated.

## Handler Inventory

The current `call_tool()` branches should be extracted in this order:

1. `mcp.handlers.project`: `p2p_init_project`, agent integration tools,
   registry refresh/show, validation, context, assessment, rubrics, maturity,
   project status/show/refresh, project brief, intake, choices, conflicts,
   impact, and next actions.
2. `mcp.handlers.proposals`: proposal create/update/list/show,
   contribution add/list, readiness get/init/refresh/explain/list gaps,
   non-branch proposal decisions, and proposal branch scan.
3. `mcp.handlers.collaboration`: remote profile, permissions, consent, sync,
   proposal draft commit, proposal branch/status/publish/request-review,
   accept/reject branch, merge, finalize, and cleanup.
4. `mcp.handlers.work_specs`: change status/show/tasks/create, work
   list/status/show/plan, spec status/show, spec export status/show/refresh,
   export, and export validation.
5. `mcp.handlers.prompts`: proposal prompt tools and software spec prompt.

Each handler should expose a small `handle_<domain>_tool(workspace, name,
arguments)` function that returns either a JSON-ready result or `None` when the
tool is outside its domain. The public `call_tool()` facade should remain the
only exported execution entry point while this split is in progress.

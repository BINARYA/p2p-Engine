# MCP Registry Domain Catalog Split Design

## Current Shape

`src/p2p_engine/mcp/registry.py` currently owns:

- `TOOL_NAMES`;
- prompt tool kind mapping;
- prompt tool definition generation;
- all static tool definition dictionaries;
- the `_schema()` helper.

The module is approximately 1,075 lines. Its size is caused by compatibility
catalog data rather than domain behavior, but the concentration makes MCP schema
changes harder to review safely.

## Target Shape

Keep `mcp.registry` as the public compatibility module:

```text
src/p2p_engine/mcp/
  registry.py                  # public exports and final assembly
  catalog/
    __init__.py
    common.py                  # schema helper and shared constants
    agents.py                  # agent integration tools
    maintenance.py             # init, validate, context, registry refresh
    project.py                 # project status/profile/rubrics/maturity tools
    proposals.py               # proposal/readiness/contribution/choice tools
    collaboration.py           # sync, branch, publish, merge, consent-aware tools
    work_specs.py              # Change Set, spec, spec export, Work tools
    prompts.py                 # advisory prompt tools
```

`registry.py` should import ordered definition groups and assemble:

- `TOOL_NAMES`;
- `tool_definitions()`;
- any backward-compatible constants that existing tests/imports expect.

## Ordering Contract

Tool ordering is compatibility-sensitive because agents can display tools in
registry order and tests may compare deterministic lists.

The split must preserve the current order by assembling groups in the same
sequence as the existing `TOOL_NAMES` tuple and `tool_definitions()` list.

## Schema Contract

Each moved tool definition must remain byte-for-byte equivalent as a Python data
structure when returned by `tool_definitions()`. The test should compare:

- ordered names;
- full definition dictionaries;
- required fields;
- enum lists;
- descriptions.

## Module Ownership

- `catalog.common` owns `_schema()` or a renamed public-local equivalent.
- Domain catalog modules own definition lists only.
- MCP handlers continue to own execution behavior.
- `mcp.tools.call_tool()` continues to route execution only; it must not import
  catalog internals.

## Migration Strategy

Use small slices:

1. Introduce `mcp/catalog/common.py` and one small catalog module.
2. Move prompt definitions first because they are generated and isolated.
3. Move read-mostly maintenance/project definitions.
4. Move proposal/readiness definitions.
5. Move collaboration and Work/spec definitions last because they are larger
   and compatibility-sensitive.
6. After each slice, run MCP registry tests.

## Risks

- Schema drift from manual movement.
- Tool order drift when groups are assembled.
- Missing import of `ContributionType` enum in moved proposal definitions.
- Accidental behavior change if execution handlers are touched.

The mitigation is to compare the public `tool_definitions()` output and avoid
handler edits.

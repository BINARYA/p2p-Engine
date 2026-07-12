# PROP-093E Root, MCP, And Hygiene Requirements

## Status

`draft`

## Traceability

- P2P proposal: `PROP-093 - Agent Persistence Boundaries And Proposal Authoring Flow`
- Accepted slice: `093-E - Root, MCP, And Hygiene Hardening`
- Related local specs:
  - `specs/features/prop-093d-bootstrap-agent-lifecycle/`
  - `specs/features/agent-integration-registry-production-hardening/`

## Problem

First-run setup can still leave two avoidable sources of confusion:

- MCP setup hints may prefer a short executable form even when the project-local
  Python module command is more robust for virtualenv installs;
- new repositories may accidentally track virtualenvs, caches, build outputs, or
  local runtime files unless the owner already has `.gitignore` protection.

There is also a terminology risk: `--root` must mean the governed P2P decision
root. It must not imply support for sibling repositories, external topology
management, or P2P ownership of unrelated repos.

## Goals

- Prefer robust project-local MCP commands in generated hints.
- Make `--root` an explicit decision-root selector.
- Help agents find and use the governed P2P root when current working directory
  differs.
- Add non-destructive repository hygiene protection for common local artifacts.
- Keep `.p2p/` trackable.
- Keep root/MCP hardening and `.gitignore` hygiene independently releasable.

## Non-Goals

- Do not implement remote MCP permissions.
- Do not implement HTTP MCP transport.
- Do not support sibling-repository project topology as a core P2P feature.
- Do not make P2P manage arbitrary external repositories.
- Do not mutate external MCP client configuration files automatically.
- Do not implement a full Python environment resolver for uv, conda, pipx,
  devcontainers, or arbitrary virtualenv layouts.
- Do not implement a complete `.gitignore` parser.
- Do not overwrite user `.gitignore` policy.
- Do not change adaptive agent defaults; that belongs to `PROP-093D`.
- Do not change agent persistence policy; that belongs to `PROP-093C`.

## Scope

In scope:

- CLI init MCP setup hint;
- MCP docs and install docs;
- generated agent instructions about finding the governed root;
- `.gitignore` guard for fresh or existing projects;
- init summary grouping for MCP and hygiene;
- tests for root semantics, MCP hint output, and non-destructive hygiene.

Out of scope:

- MCP client configuration mutation beyond printing/documenting commands;
- provider-specific authentication;
- cross-repository orchestration;
- destructive cleanup of already tracked files;
- broad Git management.

## Requirements

### R001: MCP hint prefers project-local Python module command

When init prints an MCP setup hint, the preferred command shall use the
project-local Python executable when available or predictable:

```bash
codex mcp add p2p-<project-slug> -- \
  /path/to/project/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/project
```

The shorter `p2p-mcp-server --root /path/to/project` form may remain documented
as an alternative for users who have it on `PATH`.

### R002: MCP server name derives from project identity

The suggested MCP server name shall derive from declared project identity when
available.

If project identity is unavailable, P2P may fall back to the project directory
name.

### R003: `--root` means governed decision root

CLI output, generated instructions, and docs shall describe `--root` as the
governed P2P project root used for decisions and state.

They shall not describe `--root` as a sibling-repository mechanism or imply that
P2P manages external repository topology.

### R004: Agents can locate the governed root

Generated agent instructions shall tell agents how to identify the governed
P2P root when the current working directory differs.

At minimum, instructions shall prefer an explicit `--root /path/to/project`
argument for P2P CLI and MCP operations when the root may be ambiguous.

### R005: Init summary groups MCP setup separately

Init output shall group MCP setup hints separately from:

- governed P2P state;
- project rubric and permissions;
- agent integrations;
- repository hygiene;
- next actions.

### R006: Repository hygiene is non-destructive

Init shall provide safe `.gitignore` protection or an explicit guided option
without overwriting existing user content.

The implementation shall append missing managed lines or report that existing
coverage is already present. It shall not replace the file.

### R007: Hygiene ignores common local artifacts

The `.gitignore` guard shall cover at least:

- `.venv/`;
- `__pycache__/`;
- `*.py[cod]`;
- `.pytest_cache/`;
- `.mypy_cache/`;
- `.ruff_cache/`;
- `build/`;
- `dist/`;
- `*.egg-info/`;
- local runtime logs or temp files that the project already treats as noise.

### R008: Hygiene never ignores `.p2p/`

The `.gitignore` guard shall not add `.p2p/` or patterns that would ignore the
governed P2P state.

If an existing `.gitignore` already ignores `.p2p/`, P2P shall warn rather than
silently rewriting user policy.

### R009: Hygiene is idempotent

Running init or the hygiene helper multiple times shall not duplicate patterns.

### R010: Hygiene preserves existing content and comments

Existing `.gitignore` lines, comments, ordering, and user-managed sections shall
be preserved.

Any P2P-added section shall be clearly marked and limited to the safe local
artifact patterns.

### R011: Hygiene can be tested independently from init

The `.gitignore` logic shall live in a cohesive helper or service that can be
tested without running full init.

### R012: CLI and MCP behavior is explicit

CLI init shall expose whether hygiene was applied, skipped, already covered, or
warning-only.

MCP init shall either expose the same hygiene behavior or explicitly defer it
with a documented reason.

### R013: MCP commands are structured before rendering

MCP hint construction shall keep commands as argument lists until the final CLI
or documentation renderer.

CLI rendering shall shell-quote paths and server names so project roots with
spaces or shell-special characters produce copyable commands.

### R014: Missing project-local Python is reported, not hidden

If the conventional project-local Python path such as `.venv/bin/python` does
not exist, init shall not fail solely for that reason.

The MCP hint shall mark that path as expected or conventional, or include a
clear note and the PATH-based fallback command. It shall not imply that a
missing executable was verified as present.

### R015: MCP server names are stable slugs

The MCP server name shall be derived through one normalization rule used by CLI,
MCP metadata, docs examples, and tests.

At minimum, the rule shall lowercase, convert spaces and unsupported
punctuation to hyphens, collapse duplicate hyphens, strip surrounding hyphens,
avoid duplicating a leading `p2p-` prefix, and fall back to a non-empty
directory-based slug when project identity is missing.

### R016: Generic server command and client registration command are distinct

The MCP hint model shall distinguish the generic stdio server command from
client-specific registration commands such as Codex CLI registration.

Generic docs and generated instructions shall not imply that Codex-specific MCP
registration is the only supported MCP setup path.

### R017: Hygiene matching is conservative and exact-first

The `.gitignore` helper shall recognize the P2P-managed section and practical
exact equivalents such as `.venv` and `.venv/`.

Broad user patterns shall not be interpreted aggressively. When coverage is
ambiguous, the helper may append the safe P2P-managed section or report a
warning, but it shall not remove or rewrite user policy.

### R018: Init and MCP compatibility are preserved

Existing `init_project()` callers that expect created-path lists shall remain
compatible. New init metadata for MCP hints or hygiene shall be exposed through
additive result fields, wrapper methods, or facade metadata.

MCP init response changes shall be additive: existing fields such as
`initialized`, `root`, and `created_or_updated` shall remain present.

## Public Surface Impact

### CLI

- Init MCP hint output changes to prefer project-local Python.
- Init summary gains grouped MCP and hygiene sections.
- Optional new flags may be added for hygiene behavior if needed, such as
  `--gitignore/--no-gitignore`.

### MCP

- MCP init may return additional hint/hygiene metadata.
- No new arbitrary filesystem write tool is introduced.

### Storage

- `.gitignore` may be created or appended non-destructively.
- `.p2p/` files remain trackable.
- Existing `.gitignore` content is preserved.

### Docs

- MCP and install docs shall prefer the project-local Python command and explain
  the shorter PATH-based alternative.
- Docs shall clarify decision-root semantics and avoid sibling-repository
  guidance.

### Tests

- CLI, service/helper, MCP, and docs tests shall cover root semantics, robust
  hint generation, and non-destructive `.gitignore` behavior.

## Compatibility

Existing projects remain valid. Existing MCP configurations using
`p2p-mcp-server` remain documented and supported when the executable is on
`PATH`.

Existing `.gitignore` files are not overwritten. Projects that already ignore
local artifacts should receive no duplicate lines.

## Risks

- Project-local `.venv/bin/python` is POSIX-oriented and may need future Windows
  handling.
- The robust MCP hint is longer than the short executable form.
- `.gitignore` pattern matching can be hard to infer when user patterns are
  broad.
- Warning about an existing `.p2p/` ignore may worry users but should not
  mutate their policy without consent.

## Acceptance Criteria

- Init MCP hint prefers `/path/to/project/.venv/bin/python -m
  p2p_engine.mcp.server --root /path/to/project`.
- The shorter `p2p-mcp-server` form remains documented as a PATH-based
  alternative.
- Suggested MCP server name derives from project identity when available.
- Suggested MCP commands are rendered safely for roots with spaces.
- Missing project-local Python is surfaced with a note or fallback, not hidden.
- Generic MCP server command data is separate from Codex-specific registration.
- Docs and generated instructions explain `--root` as governed decision-root
  selection, not sibling-repository support.
- Agents are instructed to use explicit root arguments when cwd is ambiguous.
- `.gitignore` guard is non-destructive, idempotent, and preserves existing
  content.
- `.gitignore` guard covers common local artifacts and never adds `.p2p/`.
- Existing `.gitignore` that ignores `.p2p/` produces a warning.
- Existing `init_project()` and MCP init public fields remain compatible.
- Root/MCP and hygiene changes can be validated independently.
- Focused service, CLI, MCP, and docs tests cover the behavior.

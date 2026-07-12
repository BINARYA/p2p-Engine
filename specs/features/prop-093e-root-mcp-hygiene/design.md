# PROP-093E Root, MCP, And Hygiene Design

## Design Summary

`PROP-093E` hardens first-run operational setup. It has two independently
releasable parts:

- root-aware MCP setup hints and generated instructions;
- non-destructive repository hygiene through `.gitignore`.

The implementation should avoid topology expansion. `--root` is a decision-root
selector for the governed P2P project, not a sibling repository feature.

## Key Decisions

### D001: Prefer robust MCP command, keep short command as alternative

Init and docs should lead with project-local Python:

```bash
/path/to/project/.venv/bin/python -m p2p_engine.mcp.server --root /path/to/project
```

The short `p2p-mcp-server --root /path/to/project` form remains an alternative
for environments where that executable is on `PATH`.

The command may point to the conventional `.venv/bin/python` path even when that
path is not present yet, but output must label it as conventional or include a
note. A missing project-local Python executable is not an init failure by
itself.

### D002: Root semantics are product semantics

Every generated root hint should describe `--root` as the governed P2P decision
root. This prevents accidental drift toward sibling repository management or
external topology support.

### D003: Hygiene helper is separate from init orchestration

`.gitignore` behavior should live in a small service/helper that returns a
structured result. Init can call it and render a summary, but should not own
pattern parsing and append logic directly.

### D004: Hygiene is append-only and idempotent

P2P may add a clearly marked section when useful. It must not rewrite user
content, remove user patterns, or duplicate existing P2P-added patterns.

### D005: `.p2p/` trackability is protected by warning, not silent repair

If existing user `.gitignore` content ignores `.p2p/`, P2P should warn. It
should not remove the user's line without explicit owner action.

### D006: Commands stay structured until rendering

The MCP hint helper should return argv-style command parts. CLI and docs
renderers are responsible for shell quoting. This keeps path handling testable
and prevents roots such as `/Users/Davide/My Project` from producing broken
copy/paste commands.

### D007: Server name slugging is centralized

Server-name normalization should be implemented once in the MCP hint helper or
a small companion function. The rule should lower-case, convert spaces and
unsupported punctuation to hyphens, collapse duplicate hyphens, avoid duplicate
`p2p-` prefixes, and provide a directory-name fallback when project identity is
missing.

### D008: Generic server command is separate from client registration

The model should expose the generic stdio server command independently from
client-specific registration commands. Codex CLI setup can remain the primary
rendered registration hint for Codex-oriented output, but generic docs and MCP
metadata should not treat Codex registration as the server command itself.

### D009: Hygiene matching is exact-first and conservative

The `.gitignore` helper should recognize exact common equivalents and the
P2P-managed section, but should not attempt a full gitignore parser. Broad
patterns are treated conservatively: warn or append the safe managed section
when needed, but never remove or normalize user policy.

### D010: Init compatibility uses additive summaries

`PROP-093D` already established an additive init summary path. `PROP-093E`
should extend that path with MCP hint and hygiene metadata while keeping
`init_project()` compatible for callers that only expect created paths.

## Components

### MCP hint helper

Preferred approach:

- add a small helper such as `McpHintService` or functions near init rendering;
- input: project root, project identity/name, client family if known;
- output: server name, generic server command parts, client-specific
  registration command parts, fallback command parts, executable-exists
  metadata, and explanatory notes.

The helper should be testable without running full CLI init.

### `src/p2p_engine/cli.py`

Expected changes:

- `_print_init_next_steps` or successor summary renderer uses the MCP hint
  helper;
- init output is grouped by purpose;
- root explanation is included in the MCP section;
- short PATH-based alternative is optional or documented elsewhere.

### `src/p2p_engine/services/project_initialization.py`

Expected changes:

- call hygiene helper if hygiene is automatic or configured;
- return enough metadata for CLI/MCP summaries without breaking current
  compatibility.

If keeping `init_project()` returning `list[Path]` is important, add an
additive summary method or facade-level wrapper rather than breaking callers.

### `.gitignore` hygiene helper/service

Responsibilities:

- read existing `.gitignore` if present;
- determine whether required patterns are already covered by exact lines or the
  P2P-managed section;
- recognize practical exact equivalents such as `.venv` and `.venv/`;
- append missing patterns in a clearly marked P2P section;
- create `.gitignore` when absent, if automatic behavior is selected;
- warn when `.p2p/` is ignored;
- preserve existing content before the P2P section byte-for-byte where
  practical, including comments and ordering;
- return structured status: applied, already_covered, skipped, warnings,
  added_patterns, path.

### Generated agent instructions

Expected changes:

- explain governed root discovery;
- recommend explicit `--root` when cwd differs or is ambiguous;
- prefer configured or explicit roots over arbitrary parent/sibling directory
  inference;
- avoid sibling repository framing.

### MCP handler

Likely touched module:

- `src/p2p_engine/mcp/handlers/maintenance.py`.

Expected changes:

- expose additive MCP init metadata for preferred command and hygiene status if
  available;
- preserve current tool names.

### Documentation

Likely touched docs:

- `docs/MCP.md`;
- `docs/INSTALL.md`;
- `docs/AGENT-INTEGRATION.md`;
- `docs/CLI-GUIDE.md` if init output is documented.

## Data And Contracts

### MCP Hint View

Suggested service view:

```python
McpHint(
    server_name="p2p-my-project",
    root="/path/to/project",
    project_python="/path/to/project/.venv/bin/python",
    project_python_exists=True,
    server_command=[
        "/path/to/project/.venv/bin/python",
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        "/path/to/project",
    ],
    codex_command=[
        "codex",
        "mcp",
        "add",
        "p2p-my-project",
        "--",
        "/path/to/project/.venv/bin/python",
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        "/path/to/project",
    ],
    fallback_command=["p2p-mcp-server", "--root", "/path/to/project"],
    notes=[],
)
```

If `project_python_exists` is false, renderers should either label
`server_command` as a conventional project-local command or display a note
before the fallback command. They should not present the path as verified.

### Gitignore Hygiene Result

Suggested service view:

```python
GitignoreHygieneResult(
    path=Path(".gitignore"),
    status="applied" | "already_covered" | "skipped" | "warning_only",
    added_patterns=[...],
    warnings=[...],
)
```

The view should be serializable for MCP results.

## Error Handling

- `.gitignore` unreadable or unwritable should fail with a clear error when
  hygiene is requested.
- Missing `.venv/bin/python` should not abort init; the hint can still be
  generated as the expected project-local path or include a note if the runtime
  path is not present.
- Existing `.p2p/` ignore should produce warning-only behavior unless explicit
  future repair is implemented.

## Migration Strategy

No migration is required.

Existing MCP configurations remain usable. Existing `.gitignore` files are
preserved. Users can rerun init or a future hygiene command if one is added.

## Test Strategy

Root/MCP tests:

- server name from project identity;
- fallback server name from directory;
- server-name slugging for spaces, punctuation, uppercase, missing identity,
  and an existing `p2p-` prefix;
- preferred Codex command uses `.venv/bin/python -m ... --root`;
- short `p2p-mcp-server` remains documented;
- missing `.venv/bin/python` does not fail init and yields a note or fallback;
- paths with spaces and shell-special characters are quoted at render time;
- generic server command and Codex registration command are separate fields;
- generated instructions avoid sibling-repository examples;
- docs do not frame `--root` as sibling repository support.

Hygiene tests:

- absent `.gitignore` creates safe section;
- existing `.gitignore` is appended without overwriting content;
- existing content before the P2P section is preserved byte-for-byte where
  practical;
- rerun does not duplicate patterns;
- existing coverage is recognized where practical;
- exact equivalents such as `.venv` and `.venv/` are recognized;
- `.p2p/` is never added;
- existing `.p2p/` ignore produces warning.

Public tests:

- CLI init summary groups MCP and hygiene output;
- MCP init exposes equivalent metadata or documented deferral.
- MCP init keeps existing response fields while adding metadata.

## Risks And Mitigations

### Windows path support

Mitigation: keep command construction path-aware and document POSIX examples.
Add Windows support in a follow-up if the package supports Windows officially.

### Gitignore pattern inference is imperfect

Mitigation: require exact P2P-managed section idempotence first; treat broad
user patterns conservatively.

### Service return type compatibility

Mitigation: use additive result wrappers or metadata methods instead of
breaking `init_project()` callers.

### Root messaging becomes topology guidance

Mitigation: add tests or docs checks for decision-root language and avoid
sibling-repository examples.

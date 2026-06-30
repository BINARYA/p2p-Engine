# Refinement Review - Agent Integration Registry Production Hardening

## Result

The hardening feature is suitable as a production-readiness improvement over
the original Agent Integration Registry MVP.

The implementation now covers the highest-risk runtime behaviors: safe writes,
truthful health, semantic validation, doctor diagnostics, path safety, scoped
force, MCP/CLI parity, and shared-file ownership.

## Follow-Up Candidates

### Template Package Data

Current generated templates still live in Python source. Moving them to package
data would make template review and versioning easier, but it is not required
for the runtime safety contract completed here.

Suggested future feature:

```text
agent-template-package-data
```

### Template Staleness

The registry records `template_version`, but runtime health does not yet compare
installed file content against a newer template version distinct from user
drift. A future feature should separate:

- user modification;
- missing file;
- unmanaged file;
- generated-from-old-template file.

Suggested future feature:

```text
agent-template-staleness-health
```

### Dry Run

Lifecycle operations now plan conservatively internally, but the CLI/MCP public
surface does not expose a dry-run result. A dry-run mode would be useful before
force updates or broad `all` updates.

Suggested future feature:

```text
agent-lifecycle-dry-run
```

### JSON CLI Output

MCP returns structured payloads, but CLI agent commands remain human-readable
only. JSON output would help automation consume health, skipped files, and
doctor findings without parsing text.

Suggested future feature:

```text
agent-cli-json-output
```

## Recommendation

Do not bundle these follow-ups into the current hardening feature. They are
useful, but the current feature already changes validation, persistence, CLI,
MCP, and lifecycle semantics. Keep the completed hardening focused and open
separate features for template packaging, template staleness, dry-run, and JSON
output.

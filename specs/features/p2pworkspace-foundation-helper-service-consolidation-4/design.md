# P2PWorkspace Foundation Helper Service Consolidation 4 Design

## Decision

`proposals`, `readiness`, and `choices` all use strict YAML mapping reads that
match `foundation.files.read_yaml_mapping`. `proposals` and `choices` also use
slug helpers, but with different fallbacks:

- proposal slugs fall back to `"project"`;
- choice slugs fall back to `"item"`.

To preserve both contracts, `foundation.files.slugify` will accept an optional
`fallback` keyword with default `"project"`.

## Implementation

- Extend `slugify(value, *, fallback="project")`.
- Keep `identity_slug` behavior unchanged by relying on the default fallback.
- Replace local helper definitions in selected services with foundation imports.
- Use a small `_slugify` alias in `choices` for `slugify(value, fallback="item")`
  so call sites remain unchanged.

## Compatibility

No public behavior changes are expected. YAML errors keep the standard
`Invalid YAML mapping: <path>` message, and slug fallbacks remain unchanged.

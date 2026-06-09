# Suggested Scope

## In scope

- Add a visible generated output tree at repository root: `outputs/`.
- Generate the default project definition at `outputs/latest/project.md`.
- Make the default export a single chaptered Markdown document for humans.
- Keep the default export domain-generic, without assuming software as the
  project vertical.
- Include stable chapters for purpose, domain context, problem framing, accepted
  proposals, decisions, requirements, scope, alternatives, tradeoffs, risks,
  assumptions, open questions, readiness notes, and delivery context.
- Preserve review history through `outputs/review-001`, `outputs/review-002`,
  and subsequent review snapshot directories.
- Support specialized export profiles under
  `outputs/latest/exports/<profile-or-vertical>/`.
- Place software-oriented exports such as software-spec, OpenSpec, or Spec Kit
  under profile folders rather than making them the default.
- Treat current `.p2p/outputs` behavior as a compatibility surface and verify
  existing producers and consumers before changing it.
- Define deterministic generation behavior so repeated exports have predictable
  paths and review numbering.

## Out of scope for the MVP

- Making the root output destination configurable.
- Replacing all existing `.p2p/outputs` behavior without compatibility analysis.
- Deleting legacy generated outputs before proving they are unused.
- Making software-specific output the default project export.
- Requiring every vertical to define a custom export profile before the default
  project document can be generated.
- Building a full template marketplace or plugin system for vertical exports.
- Treating generated `outputs/` files as the source of truth instead of P2P
  managed state.

## Scope boundaries

The proposal defines the product behavior and compatibility direction for
visible project-definition exports. It does not yet prescribe the exact command
name, renderer class layout, or internal service boundaries; those belong in the
implementation design after the proposal is accepted.

The proposal should require implementation to preserve existing CLI/MCP
contracts or introduce explicit deprecation behavior where compatibility cannot
be preserved.

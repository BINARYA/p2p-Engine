# Alternatives - PROP-016

## Alternative A - Continue Scanning Folders

Commands discover proposals, decisions and changes by scanning `.p2p/` directories every time.

Pros:

- No extra generated files.
- Simple in the short term.

Cons:

- Scales poorly.
- Makes prompt generation and exporters more ad hoc.
- Harder to inspect relationships globally.

## Alternative B - Single Global Registry

Create one large `.p2p/registry.yml`.

Pros:

- One file to inspect.
- Simple first implementation.

Cons:

- Can become large and conflict-prone.
- Mixes unrelated concerns.
- Harder to update incrementally.

## Alternative C - Typed Registries

Create `.p2p/registries/` with separate files for proposals, decisions, changes, choices, relations and artifacts.

Pros:

- Clear ownership by concern.
- Easier to inspect and regenerate.
- Better input for AI prompts and exporters.
- Lower conflict surface than one giant file.

Cons:

- More files to manage.
- Requires refresh/status commands.

## Preferred Direction

Alternative C.

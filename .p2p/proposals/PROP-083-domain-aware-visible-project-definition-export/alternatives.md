# Alternatives

## Preferred: visible default Markdown export plus nested profile exports

Generate a human-facing default project definition at `outputs/latest/project.md`.
The file is a single chaptered Markdown document that synthesizes accepted P2P
memory in a form that normal users can inspect without knowing P2P internal
state. Specialized exports are optional additional profiles under
`outputs/latest/exports/<profile-or-vertical>/`.

This is the preferred direction because it keeps the default generic across
verticals while still allowing software-specific outputs, OpenSpec exports,
Spec Kit exports, or future vertical profiles to exist without taking over the
main project definition.

## Alternative: keep generated outputs under `.p2p/outputs`

The system could continue writing generated project outputs only under
`.p2p/outputs`. This preserves a clean repository root and avoids introducing a
new visible directory.

This is not preferred because the output remains hidden inside managed P2P
state. It is difficult for humans to discover, inspect, and share, especially
when the project definition is intended to be a primary deliverable rather than
an internal implementation artifact.

## Alternative: use `project/` at repository root

The system could write the human-facing output under `project/latest/` with
review snapshots under `project/review-001`, `project/review-002`, and later
review folders.

This is not preferred because `project/` is easy to confuse with `.p2p/project`
and with the conceptual project state managed by P2P Engine. The name
`outputs/` communicates that the directory contains generated visible outputs.

## Alternative: generate multiple default files

The default export could be a folder of several Markdown files, such as
overview, requirements, risks, assumptions, decisions, and scope.

This is not preferred for the default because it creates more navigation work
and makes the canonical human-readable project definition less obvious. Multiple
files remain appropriate for specialized profiles under `outputs/latest/exports/`
when a vertical needs structured output.

## Alternative: make the software export the default

The project export could keep treating software-spec, OpenSpec, or Spec Kit as
the primary default output.

This is not preferred because P2P Engine is intended to handle projects across
many vertical domains. Software exports should be profile-specific outputs, not
the default representation of every project.

## Alternative: make the visible output path configurable in the MVP

The system could allow users to choose between `outputs/`, `project/`, `.p2p`,
or another location from the first implementation.

This is not preferred for the MVP because configurability would add migration,
documentation, validation, and compatibility complexity before the default
behavior is proven. A stable root-level `outputs/` convention is simpler and
more predictable.

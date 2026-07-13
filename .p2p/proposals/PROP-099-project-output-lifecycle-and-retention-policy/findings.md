# Findings - PROP-099

## Core Finding

P2P Engine already has enough governed project memory to produce complete visible exports. The remaining gap is not content availability, but editorial readability.

The current export is useful for audit and downstream processing, but it remains close to P2P internal structure: proposal-oriented sections, repeated governance detail, placeholder artifacts, long evidence lists, and historical material mixed with current project state.

## Publication Finding

Direct PDF rendering of the current complete export would not solve the problem. It would produce a formatted version of a document that is still too long, too internal, and too proposal-first for most human readers.

## Architecture Finding

The appropriate architecture is a hybrid publication pipeline:

- deterministic complete export;
- agentic semantic curation;
- deterministic publication validation;
- owner review;
- presentation-only neutral PDF rendering.

This separates governed content, editorial transformation, quality control, and visual rendering.

## Evidence Finding

The current `outputs/latest/project.md` is over 13,000 lines and contains many `PROP-*` sections, repeated artifact headings, and placeholder text. That confirms the need for a project-first publication layer.

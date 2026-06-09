# Alternatives - PROP-085

## Preferred: Pure Data Vertical Packs

Use `.yaml` and/or `.md` files to define vertical metadata, sections, rubrics,
blocking questions, and expected artifacts. The engine loads and validates these
packs, and the agent uses them to guide project initialization and readiness
review.

Benefits:
- inspectable by humans;
- easy to version and test;
- compatible with project-local customization;
- safer than executable plugins;
- extensible toward a future registry.

Costs:
- limited to declarative behavior in the MVP;
- requires a well-defined schema and validation errors;
- agent instructions must be strong enough to interpret the data proactively.

## Alternative: Executable Plugin Verticals

Model each vertical as installable plugin code.

Benefits:
- maximum flexibility;
- vertical-specific logic can be arbitrarily rich.

Costs:
- larger security and compatibility surface;
- harder governance and review;
- more difficult packaging and upgrade story;
- too heavy for the MVP.

## Alternative: Hardcoded Core Verticals

Ship many verticals directly in P2P Engine procedural code.

Benefits:
- deterministic behavior;
- simple runtime dependency model.

Costs:
- does not scale to many domains;
- expensive to maintain;
- encourages superficial verticals;
- makes project-local extension awkward.

## Alternative: Generic `base_project` Only

Use only generic project readiness rubrics and avoid vertical-specific packs.

Benefits:
- simplest implementation;
- no vertical quality problem.

Costs:
- too generic for real project guidance;
- weak support for domain-specific capisaldi;
- agent has little structured context for proactive interviewing.

## Decision

The MVP should use pure data vertical packs, with `base_project` as fallback,
one complete demonstration vertical, and project-local custom packs. Executable
plugins and remote registries remain future extensions.


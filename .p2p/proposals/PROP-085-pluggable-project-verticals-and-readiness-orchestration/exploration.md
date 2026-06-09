# Exploration - PROP-085

PROP-085 addresses a structural tension in P2P Engine: project readiness needs
domain-specific context, but the engine cannot hardcode every possible domain.
If P2P only uses generic project rubrics, it risks becoming too shallow to guide
real work. If it tries to ship every conceivable vertical, it becomes expensive
to maintain, inconsistent in quality, and unrealistic for a small team.

The proposed direction is to make vertical knowledge a set of pure data packs
that the engine can load, validate, and expose to agents. A vertical pack is not
executable plugin code in the MVP. It is a small, versioned bundle of `.yaml`
and/or `.md` files describing the project's skeleton for a domain: sections,
capisaldi, minimal readiness rubrics, blocking questions, expected artifacts,
and optional examples/profiles/modules.

The CLI remains deterministic. It can initialize project state and ask bounded
setup questions, but it does not become the agent. The proactive behavior belongs
to agent instructions: when the agent detects an uninitialized project or missing
capisaldi/questions, it should prioritize project-definition work, propose a
vertical-derived skeleton, interview the owner one question at a time, and store
the resulting project objects.

The first implementation slice should remain narrow: `base_project`, a loader
and validator for vertical packs, a project orchestrator skill, one complete
demonstration vertical, and integration with `p2p project readiness review`.


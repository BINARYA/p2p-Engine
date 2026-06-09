# Findings

## Tradeoff Analysis

### Visible `outputs/` root versus hidden `.p2p/outputs`

The visible root-level `outputs/` directory improves human discoverability and
makes the project definition usable as a primary artifact. The cost is a small
increase in root-level generated content and the need to document that `outputs/`
is generated, while `.p2p/` remains the managed source of truth. This tradeoff
is acceptable because the proposal's core value is human-readable project
definition, and hiding that artifact under `.p2p/` works against that goal.

### Single default `project.md` versus multiple default files

A single chaptered `outputs/latest/project.md` gives owners, stakeholders, and
agents one canonical document to inspect. Multiple default files could scale
better for very large projects, but would make the default harder to discover
and easier to partially read out of context. The chosen approach keeps the
default simple and allows complex vertical-specific structures under
`outputs/latest/exports/<profile-or-vertical>/`.

### Generic default export versus software-first export

A generic project definition keeps P2P Engine aligned with multiple verticals.
Software-specific exports remain available as profiles, but do not define the
shape of every project. The tradeoff is that software workflows need one more
nested export path, while non-software projects gain a default representation
that does not force them into implementation-spec language.

### Fixed output path versus configurable destination

Using a fixed `outputs/` path in the MVP reduces design, documentation, and
compatibility complexity. Configurability would be useful later for advanced
repository layouts, but it would add avoidable surface area before the behavior
is proven. The MVP should prefer deterministic generation and a stable convention.

### Review snapshots versus overwriting latest only

Keeping `outputs/latest/` plus `outputs/review-###/` provides auditability and
lets humans compare previous generated project definitions. The cost is more
generated files over time. This is acceptable if review folders are deterministic
and confined under `outputs/`.

### Compatibility preservation versus immediate cleanup

Treating `.p2p/outputs` as a compatibility surface slows down cleanup, but
prevents breaking existing CLI, MCP, tests, or scripts that may rely on current
paths. The implementation should inventory current usage first, then choose
mirroring, deprecation, migration, or removal deliberately.

# Risks

## Backward compatibility with `.p2p/outputs`

Existing users, tests, MCP tools, or scripts may depend on current generated
outputs under `.p2p/outputs`. Moving or removing those artifacts without a
compatibility path could break existing workflows.

Mitigation: treat `.p2p/outputs` as a compatibility surface. Before deleting or
relocating anything, inventory current producers and consumers, preserve public
CLI and MCP behavior, and introduce deprecation or mirroring only through an
explicit migration path.

## Confusion between visible outputs and managed P2P state

Users may misunderstand whether `outputs/` is source-of-truth governance state
or generated material.

Mitigation: document `outputs/` as generated visible output, keep `.p2p/` as the
managed source of truth, and include generated metadata in the output such as
source project, export profile, generation time, and source proposal/decision
references.

## Root directory noise

Adding `outputs/` at repository root makes generated files more visible but also
adds another top-level directory.

Mitigation: keep only `latest/`, review snapshots, and profile exports under the
directory. Do not spread generated files directly across the root.

## Oversized `project.md`

A single default Markdown file could become long and difficult to read for
large projects.

Mitigation: organize the file into stable chapters, include a concise executive
summary, and keep detailed machine- or vertical-specific exports under nested
profile folders when appropriate.

## Stale or misleading exports

If `outputs/latest/project.md` is not refreshed after proposal decisions or
project changes, users may treat stale information as current.

Mitigation: make export refresh explicit, archive previous versions into
`outputs/review-###`, and include generation metadata so readers can see when
the output was produced.

## Profile contract sprawl

Supporting software and non-software vertical profiles may create many slightly
different export contracts.

Mitigation: define a generic export profile contract first, then let vertical
profiles extend it through named folders under `outputs/latest/exports/`.

## Premature deletion of legacy generated outputs

The current `.p2p/outputs` content may appear unused but still provide
compatibility for existing commands or tests.

Mitigation: do not delete legacy outputs as part of the proposal itself. The
implementation should verify dependencies and decide whether to mirror, migrate,
deprecate, or remove them in a controlled code change.

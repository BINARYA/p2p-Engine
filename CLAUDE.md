# Claude Instructions — P2P Engine

Follow `AGENTS.md` in this repository.

Work on the P2P Engine implementation in `src/`, `tests/`, `scripts/`,
`docs/` and packaging configuration. This repository is not a governed P2P
project-state root; do not create or edit a local `.p2p/` instance here.

Use an explicit sibling project-state root only when a task separately concerns
P2P Engine product design. Preserve the boundary between implementation source
and `projects/p2p-engine-project/.p2p/`.

P2P Engine runtime behavior is filesystem-backed and source-control agnostic.
Do not add source-control commands, adapters, subprocess calls, repository-mode
fields or generated source-control guidance to the CLI, MCP server or runtime
package.

Run focused tests for changed behavior and the public/full release gates when
public contracts are affected. Do not create a branch, commit, tag, release or
asset as part of implementation work.

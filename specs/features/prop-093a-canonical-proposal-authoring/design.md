# PROP-093A Canonical Proposal Authoring Design

## Design Summary

`PROP-093A` makes proposal authoring explicit and command-driven. The core
change is to stop treating empty narrative files as the default scaffold for new
proposals. Structured P2P operations become the canonical input path, while
legacy and imported narrative files remain supported.

The implementation should be small and reversible: update the proposal document
service, align contribution validation across CLI and MCP, and improve guidance
without broad storage rewrites.

## Key Decisions

### D001: Canonical input is structured P2P state

The canonical authoring path is:

1. create a proposal;
2. add structured contributions and questions;
3. import external analysis when needed;
4. refresh readiness;
5. review state before owner decision.

Direct `.p2p/` file editing is not a supported authoring path.

### D002: Narrative artifacts are controlled materializations

New proposal creation should not generate empty narrative placeholders. Narrative
files are materialized only when there is meaningful content from an explicit
operation, such as import, generated analysis, or a future dedicated command.

Existing narrative files are legacy-compatible materializations and remain
readable.

### D003: Contribution type changes are additive

Existing `ContributionType` values remain valid. New concepts should be added as
new values or mapped aliases, not by renaming or removing current values.

### D004: CLI and MCP share the same contract

Contribution type validation should derive from the same core model wherever
possible. If MCP schemas require static enumeration, tests must assert that the
schema stays synchronized with `ContributionType`.

### D005: Services own behavior; CLI/MCP only adapt it

Implementation should avoid adding domain behavior directly to large entrypoint
files. CLI and MCP handlers should call services or existing `P2PWorkspace`
facade methods.

## Components

### `src/p2p_engine/core/contribution.py`

Owns `ContributionType` and structured contribution data.

Expected changes:

- add missing contribution concepts or aliases;
- expose a stable list of allowed values for CLI/MCP help and errors.

### `src/p2p_engine/services/proposals.py`

Owns proposal document creation and contribution persistence.

Expected changes:

- revise proposal scaffold generation to avoid empty narrative placeholders;
- preserve core proposal files that are still required by current workflows;
- keep contribution add/list behavior compatible;
- provide post-create guidance data if this is currently composed at service
  level.

### `src/p2p_engine/services/proposal_artifacts.py`

Owns exploration artifact status and import behavior.

Expected changes:

- confirm missing narrative files are normal optional states;
- keep import behavior independent of pre-existing files;
- ensure prompt-context rendering does not fail on absent files.

### CLI command modules

Likely touched modules:

- `src/p2p_engine/cli_commands/proposals.py`
- `src/p2p_engine/cli_commands/proposal_core.py`
- `src/p2p_engine/cli_commands/proposal_contributions.py`

Expected changes:

- refine `proposal create` output or summary;
- expose new contribution type help;
- make invalid contribution type messages actionable.

### MCP proposal modules

Likely touched modules:

- `src/p2p_engine/mcp/catalog/proposals.py`
- `src/p2p_engine/mcp/handlers/proposals.py`

Expected changes:

- align contribution type schema and validation;
- preserve explicit write-tool boundaries;
- avoid raw file mutation tools.

### Documentation

Likely touched docs:

- proposal workflow documentation;
- agent integration documentation if it currently suggests manual `.p2p` edits;
- release notes or migration note, if the project keeps them for behavior
  changes.

## Data And Contracts

### Contribution Types

The target concept set is:

- `finding`;
- `open_question`;
- `alternative`;
- `risk`;
- `assumption`;
- `constraint`;
- `objection`;
- `implementation_suggestion`;
- `scope_boundary`;
- existing legacy values.

Implementation options:

- add enum members matching the target names;
- add alias normalization before persistence;
- keep legacy values in persisted state.

The preferred implementation is additive enum members, because it is explicit
and easier for CLI/MCP schema generation.

### Proposal File Footprint

For newly created proposals:

- keep the canonical proposal metadata/document files required by existing
  workflows;
- do not create empty narrative exploration files only to make directories look
  uniform;
- allow `PROP-093B` to present a logical artifact catalog that explains missing
  optional artifacts.

For existing proposals:

- read all existing files as before;
- do not rewrite placeholder files in place;
- do not require migration.

## Error Handling

- Invalid contribution types should include the allowed values.
- Missing optional narrative files should return optional/missing status, not
  exceptions.
- Import errors should remain explicit about missing source files, unsupported
  inputs, or invalid target proposal IDs.
- Service errors should be reusable by CLI and MCP without string-only parsing.

## Migration Strategy

No migration command is required for this slice.

Legacy proposals retain their current files. New proposals use the reduced
scaffold. Mixed repositories are expected and must be handled by status/display
code.

## Test Strategy

Use the lowest useful layer for each behavior:

- service tests for proposal scaffold footprint;
- service tests for optional narrative artifact handling;
- contribution model/service tests for new types;
- CLI tests for create guidance and invalid type errors;
- MCP catalog/handler tests for schema parity;
- compatibility tests using a proposal with legacy narrative files.

Public CLI/MCP tests should assert user-visible contracts, not implementation
details beyond the new file-footprint contract.

## Risks And Mitigations

### Exact file-list tests may fail

Mitigation: update tests to assert logical behavior and only the required new
footprint guarantees.

### Agents may still rely on old instructions

Mitigation: document the canonical authoring path now; later harden generated
agent instructions in `PROP-093C`.

### Contribution aliases may confuse output

Mitigation: prefer explicit additive enum values and document any aliasing.

### MCP parity can drift

Mitigation: add tests that compare MCP schema allowed values with the core
contribution model.


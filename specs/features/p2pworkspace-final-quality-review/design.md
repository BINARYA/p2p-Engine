# P2PWorkspace Final Quality Review Design

## Design Intent

This review closes the structural refactoring with quality-focused cleanup only.
The work may adjust formatting, remove unused imports or dead artifacts, and
record findings, but it must not move responsibilities into new architecture
layers unless a concrete defect blocks validation.

## Review Areas

- Dead code and unused imports: use static checks, direct search, and focused
  inspection to find stale symbols introduced by extraction.
- MCP catalog readability: expand compressed tool dictionaries and large tuple
  literals into human-reviewable structures while preserving runtime contracts.
- Residual large-file assessment: inspect `storage.filesystem`,
  `services.work_branches`, and `services.proposal_branches` for mixed
  responsibility, duplicated helper ownership, and stale compatibility glue.
- MCP consent and owner-controlled flows: inspect proposal collaboration MCP
  handlers for valid consent consumption, audit behavior, and non-bypass of
  publish, accept, reject, merge, finalize, and cleanup semantics.
- Validation: run project validation and the automated test suite after any
  runtime edits.
- Commit strategy: review working tree scope and recommend a commit breakdown
  that keeps reviewable boundaries.

## Out Of Scope

- Splitting `P2PWorkspace` into a new public API.
- Reworking branch lifecycle services into new subservices.
- Changing CLI/MCP public command names, tool names, schemas, payloads, or
  persisted file layouts.
- Introducing new behavior beyond cleanup and quality fixes.

## Future Evolution Candidate Handling

Findings that are useful but not required for final cleanup must be recorded in
`future-evolutions.md` instead of being implemented opportunistically.


# PROP-093C Agent Persistence Policy Requirements

## Status

`draft`

## Traceability

- P2P proposal: `PROP-093 - Agent Persistence Boundaries And Proposal Authoring Flow`
- Accepted slice: `093-C - Agent Persistence Policy`
- Related local specs:
  - `specs/features/prop-093a-canonical-proposal-authoring/`
  - `specs/features/prop-093b-artifact-status-owner-view/`
  - `specs/features/proposal-artifact-state-readiness/`

## Problem

Generated agent instructions already protect `.p2p/` from direct edits and keep
governance decisions under owner control. They do not yet give agents a compact,
general policy for all persistent writes in a project.

That gap causes confusing behavior in first-run and project-definition
conversations. An agent may create stable-looking documents, local specs,
generated exports, or P2P narrative artifacts before previewing the action and
asking whether the owner wants that persistent state.

P2P needs generated policy that separates analysis from persistence. Agents
should be able to reason freely, but meaningful persistent writes need a clear
classification, preview, and route through the correct P2P or repository
surface.

## Goals

- Add persistent write classes to generated agent instructions and policy.
- Require an action preview before meaningful persistent writes unless the owner
  explicitly requested the exact operation and artifact.
- Give agents a compact routing playbook for common request types.
- Preserve owner authority and the missing-primitive rule.
- Clarify that stable documentation is a classified repository write, not proof
  that P2P governs every durable document.
- Make placement policy strict while keeping exact artifact names in explicit
  artifact contracts or vertical primitives.
- Keep generated instructions concise enough for agents to follow.

## Non-Goals

- Do not implement permission-gated MCP writes beyond existing tool schemas.
- Do not add generic filesystem write APIs.
- Do not change proposal scaffold behavior; that belongs to `PROP-093A`.
- Do not implement adaptive init or lifecycle commands; that belongs to
  `PROP-093D`.
- Do not implement root/MCP hint or `.gitignore` behavior; that belongs to
  `PROP-093E`.
- Do not make P2P govern all repository documents.
- Do not define a complete output registry or every vertical artifact filename;
  exact artifact schemas belong to artifact contracts or explicit vertical
  primitives.

## Scope

In scope:

- generated `AGENTS.md`;
- generated project skills for supported agents;
- generated `.p2p/agent-policy.yml`;
- shared agent-template text blocks;
- maintained docs explaining the same policy;
- tests for template output and structured policy payload.

Out of scope:

- direct editing of existing user-modified generated files;
- one-off migration of all existing projects;
- enforcement in external agent runtimes;
- policy for remote provider authorization beyond existing consent mechanisms.

## Requirements

### R001: Generated policy defines persistent write classes

Generated agent instructions and structured policy shall define these write
classes:

- `read_only`;
- `chat_only`;
- `local_scratch`;
- `p2p_canonical`;
- `p2p_generated_narrative`;
- `p2p_imported_artifact`;
- `generated_export`;
- `stable_documentation`;
- `external_side_effect`.

Each class shall include a concise description and its expected write surface.

### R002: Analysis remains freely allowed

Generated policy shall state that agents may analyze, inspect, summarize,
compare, and suggest actions without preview when no persistent write or
external side effect is performed.

### R003: Meaningful persistent writes require preview by default

Before a meaningful persistent write, generated policy shall require an action
preview unless the owner explicitly requested the exact operation and artifact.

The preview shall include:

- operation;
- target path or P2P object;
- artifact kind;
- write class;
- canonical or derived status;
- reason;
- reversibility or cleanup path when relevant.

### R004: Exact owner requests may skip redundant confirmation

When the owner explicitly requests the exact operation and artifact, agents may
perform the operation without an additional confirmation prompt.

An exact operation and artifact means the owner has specified the operation,
target path or P2P object, artifact kind, and intended durable destination.
Vague requests such as "prepare the specs", "organize the project", or "put
down a proposal" shall not count as exact requests.

The generated policy shall still require the agent to route through the correct
CLI, MCP tool, or repository write surface.

### R005: `.p2p/` writes remain constrained to public primitives

Generated policy shall preserve the existing rule that `.p2p/` is managed state.

Agents shall not create, edit, rename, or delete `.p2p/` internals directly
unless the owner explicitly asks for repair and no supported primitive exists.

### R006: Stable documentation is a write class, not a governance claim

Generated policy shall state that `stable_documentation` is durable repository
documentation that requires preview and classification.

It shall not imply that every durable repository document is governed by P2P.

### R007: Artifact placement guidance is strict and explicit

Generated policy shall explain these placement boundaries:

- `.p2p/` is governed state;
- `outputs/` is generated or exported material;
- `drafts/` or `docs/drafts/` is preliminary working material;
- `docs/` is stable owner-intended documentation;
- local scratch paths are temporary and not durable project memory.

Agents shall not place preliminary conversation output directly in `docs/`
unless the owner asks for stable documentation there.

The generated structured policy shall mark placement as strict. Agents shall
not invent durable output paths. Unknown durable destinations shall require an
action preview and owner confirmation, or a stop-and-report outcome when the
artifact is P2P-governed and no supported primitive exists.

### R008: Placement policy is not a complete artifact schema

The placement policy shall define mandatory write zones for artifact classes.

It shall not imply that `outputs/`, `docs/`, or another bucket is sufficient to
identify every artifact that can be evaluated, regenerated, referenced, or
consumed by agents.

When an output must be evaluated, regenerated, referenced, or consumed by
agents, its exact durable name and path shall come from a P2P artifact contract,
an explicit vertical primitive, or an exact owner request. Agents shall not
invent durable paths for governed or evaluable artifacts.

### R009: Generated outputs, stable documentation, and scratch have canonicality semantics

Generated policy shall state that `generated_export` artifacts are derived by
default and are not canonical P2P state unless explicitly imported or declared
by a contract.

Generated policy shall state that `stable_documentation` is durable repository
documentation requiring owner intent, but is not canonical P2P state unless
explicitly imported or declared.

Generated policy shall state that `local_scratch` is temporary only, is not
durable project memory, and must be promoted, imported, or classified before an
agent relies on it as project memory.

### R010: Routing playbook covers common request types

Generated instructions shall include a compact routing playbook for:

- chat-only exploration;
- project definition work;
- proposal authoring;
- choices;
- vertical-specific primitives such as the software-spec lifecycle from
  `PROP-094`;
- implementation work outside `.p2p/`;
- exact file requests;
- generated exports;
- stable documentation;
- local scratch;
- outside-P2P work.

### R011: MCP boundary remains explicit

Generated policy shall state that MCP tools are read-only unless their schema
explicitly declares a write operation.

MCP write tools shall be used only for the operation named by their schema and
shall not authorize arbitrary filesystem writes.

### R012: Policy is represented in both prose and structured payload

The generated markdown instructions shall contain the agent-readable short form.

The generated `.p2p/agent-policy.yml` shall contain structured write class,
preview, placement, and routing policy data suitable for tests and future tools.

### R013: All supported agent adapters receive equivalent rules

The generic `AGENTS.md` and adapter-specific outputs for Codex, Claude, Cursor,
Copilot, Gemini, and OpenCode shall receive equivalent persistence policy
coverage.

Adapter-specific files may reference the generic policy instead of duplicating
all text, but the boundary must be discoverable to that agent.

### R014: Refresh remains non-destructive

Refreshing generated policy shall preserve existing drift and unmanaged-file
safety rules.

The implementation shall not overwrite drifted or unmanaged agent files without
an explicit force behavior that is already supported and tested.

## Public Surface Impact

### CLI

- `p2p init` and `p2p agent instructions refresh` generated output changes.
- Agent template text and policy payload content change.
- Existing command names and arguments remain compatible.

### MCP

- MCP init and agent refresh tools return generated files using the same policy.
- No new write capability is introduced by this slice.

### Storage

- `.p2p/agent-policy.yml` payload gains structured policy fields.
- Generated agent files may change template hashes.
- Existing unmanaged or drifted files remain protected.

### Docs

- Agent integration documentation shall explain write classes, preview rules,
  placement, and routing.

### Tests

- Template tests shall assert the presence of write classes, preview schema,
  placement boundaries, routing playbook, and stable-documentation caveat.
- CLI/MCP tests shall cover generated output parity where public surfaces are
  affected.

## Compatibility

Existing projects remain valid. They receive the new policy only when the owner
runs init on a new project or refreshes/updates agent instructions in an
existing project.

Drifted and unmanaged files remain protected by existing registry behavior.

## Risks

- Generated instructions may become too long for agents to follow.
- Preview rules may slow rapid prototyping if phrased as absolute bureaucracy.
- Adapter-specific outputs may drift from generic `AGENTS.md`.
- Structured policy payloads can become stale if tests assert only prose.

## Acceptance Criteria

- Generated `AGENTS.md` includes persistent write classes and action-preview
  rules.
- Generated project skills and adapter-specific instruction files expose the
  same persistence boundary.
- `.p2p/agent-policy.yml` includes structured write class, preview, placement,
  and routing data.
- Placement policy is strict, includes unknown-destination behavior, and does
  not authorize invented durable output paths.
- Evaluated or reusable output names are required to come from artifact
  contracts, explicit vertical primitives, or exact owner requests.
- Generated exports are classified as derived by default, and scratch output is
  not treated as durable project memory.
- Stable documentation is explicitly classified without claiming universal P2P
  governance over repository documents.
- Preliminary outputs are routed away from `docs/` unless stable documentation
  is explicitly requested.
- MCP read/write boundaries remain unchanged and explicit.
- Refresh/update behavior remains non-destructive for drifted or unmanaged
  files.
- Focused template, service, CLI, and MCP tests cover the policy text and
  structured payload.

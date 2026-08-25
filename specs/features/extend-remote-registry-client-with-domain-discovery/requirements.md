# Requirements - Extend Remote Registry Client With Domain Discovery

## Scope

Extend the provider-neutral vertical-registry client with first-class domain
discovery and domain-filtered vertical search. Domain metadata remains
classification and catalog guidance; it never supplies project structure or
authorizes a project mutation.

## Origin

- Source: owner-approved domain, vertical and project-structure revision.
- Target train: P2P Engine `0.5.0` after the core domain contract and before
  the `0.5.0` convergence/release gate.
- Depends on: `separate-domain-from-structure-source`, the implemented
  `prop-105-local-vertical-catalog-and-remote-registry-client`, and registry
  protocol `p2p-vertical-registry/v2`.
- First provider: WaveKit, without importing WaveKit routes, models or policy.

## In Scope

- Current-only registry protocol v2 negotiation at the existing well-known
  capability path.
- Typed domain list, search and detail reads.
- Domain-aware remote vertical list/search filters.
- Public and OAuth Device Flow private discovery.
- Deterministic pagination, bounds, redaction and same-origin URL validation.
- CLI JSON/text contracts and read-only MCP parity for catalog discovery.
- Agent guidance and installed-wheel provider-neutral contract fixtures.

## Out Of Scope

- Domain creation, editing, publication, moderation or ranking.
- Project-domain mutation or automatic structure selection.
- Pulling a domain as though it were a vertical artifact.
- Inferring compatibility merely because project and vertical domains match.
- Supporting registry protocol v1 in the P2P Engine 0.5 current runtime.
- MCP login, pull or publication side effects.

## Public Surface And MCP Impact

- CLI impact: add `p2p vertical domain list`, `p2p vertical domain search` and
  `p2p vertical domain inspect`; extend remote vertical list/search with an
  exact `--domain` filter.
- MCP impact: add read-only, network-declared domain list/search/inspect and
  domain-filtered vertical search tools over the same services. Authentication,
  pull and publication remain explicitly outside this feature.
- Storage impact: negotiated v2 capabilities may be cached in user registry
  configuration; domain catalog results are not canonical project state.
- Agent-facing behavior: explain that domain recommendations are advisory and
  an exact starter or vertical release must still be selected explicitly.

## Functional Requirements

### Protocol Negotiation

- R001: The 0.5 runtime SHALL accept only capability documents declaring
  `p2p-vertical-registry/v2` for remote registry operations.
- R002: Protocol v2 capabilities SHALL declare same-origin endpoints for
  domains, exact domain detail, vertical search/list, exact release and the
  existing optional publication and OAuth Device Flow operations.
- R003: Missing required v2 endpoints, unsupported protocol versions, unknown
  required fields or cross-origin endpoint substitution SHALL fail before a
  catalog response is represented as valid.
- R004: Registry configuration and capability output SHALL never contain
  bearer, refresh, device or provider-secret material.

### Domain Contracts

- R005: Domain list/search SHALL return a versioned bounded page containing
  stable external ID, stable key, name, description, visibility, lifecycle,
  optional publisher and optional exact recommended release.
- R006: Exact domain detail SHALL use one stable external ID and SHALL return
  not-found semantics that do not enumerate inaccessible private domains.
- R007: Domain responses SHALL NOT contain sections, criteria, fields,
  questions, readiness weights, project memory or executable instructions.
- R008: A recommended release SHALL be an advisory exact coordinate plus
  immutable digest and SHALL NOT trigger pull, initialization or project
  mutation.
- R009: Unknown optional display metadata SHALL be ignored safely; unknown
  lifecycle or visibility values and any executable field SHALL fail with the
  typed invalid-response error and SHALL yield no actionable catalog result.

### Domain-Aware Vertical Discovery

- R010: Remote vertical list/search SHALL accept at most one exact domain
  external ID supplied as an encoded query value, never as a URL fragment or
  path supplied by the registry response.
- R011: Each returned vertical release SHALL expose an optional primary-domain
  reference as discovery metadata separate from coordinate, artifact identity
  and dependency closure.
- R012: An uncategorized release SHALL remain discoverable through unfiltered
  search and an explicit uncategorized filter when the provider advertises it.
- R013: A domain match SHALL NOT be presented as semantic compatibility and
  SHALL NOT relax checksum, schema, visibility, dependency or exact-coordinate
  validation.
- R014: Domain-filtered discovery SHALL perform no project mutation, artifact
  download or implicit cache installation.

### Pagination, Authentication And Failures

- R015: Domain and vertical pages SHALL use stable ordering, a maximum page
  size of 100, opaque cursors and at most 10 pages per aggregate CLI/MCP call.
- R016: Repeated cursors, conflicting duplicate IDs, count mismatch, malformed
  terminal pages or bound overflow SHALL fail without publishing a complete
  result.
- R017: Public catalog reads SHALL work anonymously; private results SHALL use
  only the existing secure Device Flow credential store and required read
  scope.
- R018: Authentication, timeout, TLS, malformed response and throttling errors
  SHALL retain stable typed codes and redact credentials and private response
  content.
- R019: No domain discovery command SHALL perform network access unless a
  remote source or registry is explicitly selected.

### CLI, MCP And Resolution Boundary

- R020: All CLI JSON results SHALL use the current global CLI envelope and
  versioned `vertical_domains` or `vertical_releases` payloads with deterministic
  text parity.
- R021: MCP catalog tools SHALL call the same typed registry services and SHALL
  declare remote network reads in their descriptions and consent/permission
  class.
- R022: CLI and MCP callers SHALL receive metadata only; project initialization
  SHALL still freeze one explicit starter or exact verified vertical release
  through its own governed workflow.
- R023: P2P core domain services SHALL depend only on provider-neutral protocol
  models and SHALL not import WaveKit identifiers, policies or URLs.

## Non-Functional Requirements

- N001: Parsing and normalized ordering SHALL be deterministic across supported
  Python versions and installed wheels.
- N002: Remote documents SHALL respect existing connection/read timeouts and
  bounded document sizes.
- N003: Domain discovery SHALL add no canonical files below `.p2p` and no
  implicit artifact-cache writes.
- N004: Public JSON and errors SHALL be safe for structured logs after caller
  authorization.
- N005: Service behavior SHALL be independently testable with an in-memory
  transport and credential store.

## Edge Cases And Errors

- Registry v1 capability document encountered by a 0.5 client.
- Private domain requested without token, with expired token or wrong scope.
- Domain recommendation points to a withdrawn or inaccessible release.
- Same domain ID appears twice with conflicting metadata.
- Cursor repeats or catalog changes between bounded pages.
- Vertical response claims a primary domain absent from the visible page.
- Remote is selected while no registry is configured.
- Local-only catalog is used with no credential backend.

## Acceptance Criteria

- AC001: A public domain can be listed, searched and inspected through CLI JSON
  and text without mutating project or artifact cache state.
- AC002: An authenticated user sees authorized private domains while an
  anonymous caller cannot infer their existence.
- AC003: Domain-filtered vertical search returns exact releases and preserves
  all existing integrity and dependency semantics.
- AC004: Recommendation metadata never initiates pull or initialization.
- AC005: Protocol v1, cross-origin endpoints, malformed pagination and secret
  leakage fail closed with stable diagnostics.
- AC006: CLI and MCP read contracts are semantically equivalent and use one
  provider-neutral service implementation.
- AC007: Installed-wheel fixtures prove the WaveKit-compatible v2 protocol
  without requiring WaveKit implementation code.
- AC008: Generated agent guidance distinguishes project domain, catalog domain,
  vertical release and detached project structure.

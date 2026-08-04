# Requirements - Local Vertical Catalog And Remote Registry Client

## Origin

- Accepted P2P proposal: `PROP-105`.
- Owner decision: accepted by `mrjungle` on 2026-08-03.
- Depends on the current schema baseline from `PROP-104` and the portable pack
  contract from `PROP-103`.
- WaveKit is the first registry provider, but P2P Engine must not depend on
  WaveKit domain models or URLs.

## Goal

Let users discover local and remote vertical releases, authenticate to private
registries, pull one exact verified artifact into an immutable user cache and
initialize a project from the same exact coordinate used by local workflows.

## In Scope

- User-level registry configuration and capability negotiation.
- Provider-neutral HTTP registry protocol version 1.
- Public search/list and authenticated private listing.
- OAuth device-flow login and secure credential storage.
- Immutable user-level cache outside project state.
- Exact pull, inspect and deterministic init resolution.
- Explicit network authorization through `--pull`.
- Timeout, TLS, bounded-download, checksum and atomicity protections.

## Out Of Scope

- Server-side identity, authorization, moderation, metrics and licensing
  policy.
- Floating versions, tags or dependency ranges.
- Automatic background updates or silent network fallback.
- Remote publication, which belongs to `PROP-106`.
- Replacing WaveKit's verified local-artifact handoff to its worker.

## Functional Requirements

### Registry Configuration

- R001: `p2p vertical registry add NAME URL` SHALL persist a named HTTPS
  registry in user configuration outside every `.p2p` workspace.
- R002: `registry list` SHALL report configured registries, default status and
  negotiated protocol capabilities without contacting a registry unless
  refresh is explicitly requested.
- R003: `registry remove` SHALL remove only local configuration and SHALL NOT
  delete cached artifacts or remote data.
- R004: Registry names SHALL be unique and URLs SHALL reject embedded
  credentials, fragments and non-HTTPS schemes except explicitly enabled
  loopback development URLs.
- R005: One configured registry MAY be marked default; commands SHALL accept an
  explicit `--registry` override.

### Authentication

- R006: `p2p vertical login REGISTRY` SHALL use the registry-advertised OAuth
  device authorization flow and SHALL NOT accept a bearer token as a normal
  command-line argument.
- R007: Access and refresh credentials SHALL be stored through an operating-
  system credential provider and SHALL never be written to `.p2p`, registry
  configuration, cache metadata, logs or JSON output.
- R008: `p2p vertical logout REGISTRY` SHALL delete local credentials without
  revoking or deleting cached immutable artifacts.
- R009: Public registry operations SHALL work anonymously; private operations
  SHALL fail with stable code `P2P_REGISTRY_AUTH_REQUIRED` when no usable
  credential exists.
- R010: Authentication and transport errors SHALL redact bearer tokens and
  provider secrets.

### Discovery And Pull

- R011: `p2p vertical search QUERY` SHALL combine local and selected remote
  metadata and label each result with source, visibility and exact coordinate.
- R012: `p2p vertical list` SHALL support local-only, remote-only and combined
  views without treating friendly names as installable identities.
- R013: `p2p vertical pull COORDINATE` SHALL require an exact
  `publisher/id@version` coordinate.
- R014: Pull SHALL retrieve signed/declared metadata before bytes and verify
  coordinate, artifact SHA-256, semantic checksum, size and schema before
  committing cache state.
- R015: Downloads SHALL use configured connection/read timeouts, a maximum byte
  limit and a temporary file on the same filesystem as the cache destination.
- R016: A verified artifact SHALL be atomically renamed into an immutable cache
  path derived from registry, coordinate and artifact checksum.
- R017: Re-pulling an exact matching artifact SHALL return `already_present`;
  different bytes for previously seen immutable metadata SHALL fail with
  `P2P_REGISTRY_IMMUTABILITY_VIOLATION`.
- R018: Pull SHALL resolve and verify the exact dependency closure declared by
  the pack or fail without committing a partial closure.

### Local Catalog And Resolution

- R019: The local catalog SHALL include bundled packs, immutable user-cache
  packs and explicit portable artifacts with unambiguous source metadata.
- R020: Exact coordinate resolution SHALL fail when two sources claim the same
  coordinate with different semantic or artifact checksums.
- R021: `p2p vertical inspect TARGET` SHALL inspect an exact local coordinate,
  cached coordinate or explicit file without persistent writes.
- R022: Cache/config roots SHALL follow `P2P_HOME` when set and otherwise use
  platform user-data/cache conventions; they SHALL never default under the
  current project.

### Initialization

- R023: `p2p init --vertical COORDINATE` SHALL resolve only bundled or cached
  exact coordinates and SHALL perform no network request.
- R024: `p2p init --vertical COORDINATE --pull` SHALL explicitly authorize
  remote retrieval from the selected registry when the exact coordinate or its
  closure is absent locally.
- R025: `--vertical-pack PATH` SHALL remain the explicit offline artifact input
  and SHALL be mutually exclusive with remote pull options.
- R026: Init SHALL pass the verified local artifact through the existing
  installation service before selecting the vertical.
- R027: Init failure SHALL leave no partial `.p2p` workspace or partial cache
  closure.

### Protocol And Output

- R028: Registry capability and API responses SHALL declare protocol
  `p2p-vertical-registry/v1`.
- R029: P2P Engine SHALL use a provider-neutral registry client interface;
  WaveKit-specific paths, models and authentication policy SHALL remain in the
  provider contract/configuration.
- R030: All new JSON output SHALL use the versioned envelope from `PROP-107`
  with stable registry error codes and non-zero failure exits.

## Acceptance Criteria

- AC001: A public exact release can be searched, pulled, verified, cached and
  used to initialize a project.
- AC002: An authenticated user can list and pull an authorized private release
  without credential material appearing in files or output.
- AC003: Init without `--pull` performs zero network requests.
- AC004: Checksum, size, TLS, timeout and malformed-pack failures leave no
  committed cache artifact or workspace.
- AC005: Exact cache hits are deterministic and an immutable-coordinate conflict
  fails closed.
- AC006: Local-only operation works with no configured registry and no keyring
  access.
- AC007: Focused service/adapter tests, CLI contract tests and full suite pass.

## Public Surface Impact

- CLI: new top-level `p2p vertical` registry/login/search/list/pull/inspect
  workflows and additive init options.
- MCP: discovery and pull tools are deferred; services are reusable by a later
  adapter. Existing WaveKit server integration remains CLI based.
- Storage: user configuration/cache outside `.p2p`; installed project packs
  retain the `PROP-103` layout.
- Docs: registry protocol and operator/login guidance.
- Tests: network adapter, credential, cache, CLI and init integration coverage.


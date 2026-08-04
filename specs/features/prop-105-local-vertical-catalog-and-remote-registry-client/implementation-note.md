# Implementation Note - PROP-105 Local Catalog And Remote Registry Client

## Status

Delivered for version `0.4.6` from accepted proposal `PROP-105`.

## Delivered

- Provider-neutral typed protocol `p2p-vertical-registry/v1` with cached
  capability negotiation and same-origin endpoint enforcement.
- User-level registry configuration and immutable cache under `P2P_HOME` or
  platform data/cache roots, never under `.p2p`.
- OAuth device authorization with access/refresh credentials held only by the
  operating-system keyring adapter; tests use an injected memory adapter.
- Bounded HTTPS transport with TLS verification, independent connection/read
  timeouts, response limits, streamed artifact limits and secret-redacted
  errors.
- Exact remote metadata parsing, recursive dependency planning and complete
  closure validation through the existing portable-pack lifecycle.
- Transaction-local downloads, SHA-256/size/schema/semantic/dependency checks,
  rollback on failure and immutable cache conflict detection.
- Normalized bundled, cache and explicit-file catalog reads with exact
  coordinate conflict detection.
- CLI registry capability refresh, login/logout, local/remote/all list,
  search, pull and cache-aware inspect commands under the versioned JSON
  envelope.
- Offline-by-default exact `p2p init --vertical`; `--pull --registry` is the
  only init mode that authorizes network retrieval.
- Ordered cached-closure installation through the existing install service,
  followed by the existing project selection path. No registry or HTTP code
  was added to `P2PWorkspace`.
- Protocol, CLI, cache and WaveKit handoff documentation.

## Integration Boundary

Remote transport terminates at a verified local `.p2pv` artifact. P2P Engine
does not read or write WaveKit models and does not know WaveKit route names.
WaveKit can implement protocol v1, or it can retain its existing worker handoff
of a verified local artifact path plus expected checksum.

Project-state mutation still uses the existing CLI/service path:

```text
registry -> immutable user cache -> portable install -> vertical selection
```

The project `.p2p` state never calls the registry directly.

## Security And Failure Policy

- Public remote reads degrade to anonymous access when no secure credential
  backend is available; private access reports `P2P_REGISTRY_AUTH_REQUIRED`.
- No bearer-token CLI option or plaintext credential fallback exists.
- Advertised capability, OAuth, API and artifact URLs must stay on the
  configured origin; artifact URLs with query material are rejected.
- A checksum, size, schema, malformed archive, dependency or immutable cache
  mismatch commits no partial closure.
- Init without `--pull` constructs no remote client and performs no network
  request.
- Failure while installing a pulled closure into a new project removes the
  partial `.p2p` workspace.

## Deferred

Remote registry MCP tools remain intentionally deferred. They require a
separate network-consent and authentication UX. The registry client, catalog
and pull services are transport-independent so a later MCP adapter can reuse
the implementation without duplicating integrity or cache rules.

Remote publication is now delivered by `PROP-106` through the same registry
adapter and exact immutable-artifact contract.

## Validation Evidence

- Focused registry/portable/CLI suite: `54 passed`; the dedicated remote
  registry suite contains `12` protocol, auth, cache, hostile transport, CLI
  and init tests.
- Full repository suite: `1435 passed in 234.98s`.
- Wheel and sdist build succeeded without isolation.
- Wheel metadata declares `keyring>=25.0` and includes the new adapters,
  catalog and registry services.
- Installed-wheel `version --format json` and local `vertical list --format
  json` smoke tests succeed outside the source package path.

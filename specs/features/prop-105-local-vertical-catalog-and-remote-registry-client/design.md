# Design - Local Vertical Catalog And Remote Registry Client

## Decision Summary

Add a provider-neutral remote registry client around the existing portable-pack
services. Remote transport ends at a verified local artifact. All project
mutation continues through the install/init services introduced by `PROP-103`.

```text
registry metadata -> bounded temporary download -> checksum/schema validation
                  -> immutable user cache -> existing pack install -> project
```

## User Storage

Resolve roots in this order:

1. `P2P_HOME` when explicitly configured;
2. platform user data/cache directories.

Suggested layout:

```text
<data>/p2p-engine/registries.yml
<cache>/p2p-engine/verticals/<registry>/<publisher>/<id>/<version>/
  metadata.yml
  <artifact-sha256>.p2pv
```

Registry configuration contains names, base URLs, default selection and cached
capabilities. It contains no access tokens. Cache directories are immutable;
temporary files use a sibling `.tmp` name and atomic rename.

## Registry Protocol V1

The client first reads a capability document at a configured relative endpoint.
The document declares protocol version, API base, maximum artifact size and
optional OAuth device endpoints. The logical API operations are:

- search/list release metadata;
- inspect one exact release;
- download one exact immutable artifact;
- create and poll OAuth device authorization;
- publish one immutable artifact (`PROP-106`).

The registry adapter owns URI construction and HTTP details. Domain services
consume typed `RegistryCapabilities`, `VerticalRelease`, and
`ArtifactDownload` values. This prevents WaveKit route names from entering pack
or lifecycle code.

## Credentials

`CredentialStore` is an explicit dependency. The production implementation
uses the Python `keyring` API with service name `p2p-engine.vertical-registry`
and registry name as account. Tests inject an in-memory store. If no secure
backend is available, login fails with a recovery diagnostic; credentials are
not downgraded to a plaintext file.

OAuth device flow prints the verification URI and user code in text mode, or
returns a pending authorization payload in JSON mode. Polling obeys server
interval and expiry. Tokens are passed only in authorization headers and are
redacted from exceptions.

## Cache And Pull Transaction

`VerticalPullService` performs:

1. exact coordinate parsing;
2. metadata retrieval and protocol validation;
3. recursive exact dependency-plan construction;
4. bounded streaming of all missing artifacts to temporary files;
5. artifact SHA-256, portable schema and semantic-checksum verification;
6. conflict detection against existing immutable metadata;
7. atomic commit of the complete cache candidate.

No archive is extracted into the user cache. Project installation reads the
verified `.p2pv` artifact through existing safety checks. One per-cache lock
serializes writes; read-only list/search do not take the project mutation lock.

## Local Catalog

`VerticalCatalogService` normalizes bundled packs, cached remote packs and
explicit files into one read model. Results carry source type, registry,
coordinate, checksums, visibility and local availability. Search ranking is
presentation-only; resolution always requires exact coordinates.

## Init Resolution

`p2p init --vertical COORDINATE` asks the catalog for an exact local artifact.
When `--pull` is present and the coordinate is missing, the selected registry
pulls it first. The resulting verified local path is passed to the existing
install-before-init flow. The filesystem facade never performs implicit HTTP.

## Module Ownership

- `core/vertical_registry.py`: typed registry/config/cache models and error
  codes.
- `services/vertical_registry.py`: configuration, login/logout and registry
  operations.
- `services/vertical_catalog.py`: normalized local discovery/resolution.
- `adapters/vertical_registry_http.py`: bounded HTTP/TLS transport.
- `adapters/credential_store.py`: OS keyring adapter.
- `cli_commands/verticals.py`: top-level command presentation.
- `cli.py`: init option integration only.

## MCP Decision

MCP parity is explicitly deferred for 0.4.6. Remote registry calls can trigger
network and authentication side effects and need a later consent design.
WaveKit continues invoking local CLI artifacts in its worker. The service API
must remain transport-independent so a later MCP tool does not duplicate
validation or caching logic.

## Failure Policy

- No implicit network access.
- No plaintext credential fallback.
- No cache commit before the entire requested closure verifies.
- No newest-version or friendly-name resolution for mutation.
- Any mismatch between metadata, bytes and effective pack fails closed.


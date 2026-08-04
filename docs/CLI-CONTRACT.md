# CLI JSON Contract

P2P Engine 0.4.7 exposes one machine-facing CLI transport contract:
`p2p-cli/v1`. Every command that accepts `--format json`, including commands
whose format defaults to JSON, emits exactly one JSON document to stdout.

## Envelope

Successful response:

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": true,
  "operation": "project.vertical.list",
  "data": {},
  "warnings": [],
  "error": null
}
```

Failed response:

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": false,
  "operation": "project.vertical.show",
  "data": null,
  "warnings": [],
  "error": {
    "code": "P2P_VERTICAL_AMBIGUOUS_REFERENCE",
    "message": "The vertical reference is ambiguous.",
    "details": {}
  }
}
```

The top level contains only `contract_version`, `ok`, `operation`, `data`,
`warnings` and `error`. Domain-specific fields are under `data` on success and
typed diagnostic context is under `error.details` on failure.

`operation` is the invoked command path joined by dots. For example,
`p2p project vertical install preview` reports
`project.vertical.install.preview`. This identifier does not depend on the
human-readable message or payload fields.

## Exit Classes

| Exit | Meaning |
| ---: | --- |
| 0 | Success |
| 1 | Internal or otherwise unclassified failure |
| 2 | Invalid option, argument, type or request |
| 3 | Conflict or failed precondition |
| 4 | Authentication, authorization or consent failure |
| 5 | Unavailable dependency, registry or transport |

Consumers must branch on `ok`, `error.code` and the exit class. They must not
infer behavior from `error.message`.

When JSON is requested, missing arguments, unknown options and conversion
errors use the same envelope with `P2P_CLI_INVALID_REQUEST`. Text mode retains
Typer/Rich help and error rendering.

## Consumer Integration

Consumers that bypass the current envelope and read domain fields directly are
unsupported:

```python
payload["project_readiness"]
```

The current form is:

```python
envelope = json.loads(stdout)
if not envelope["ok"]:
    raise RuntimeError(envelope["error"]["code"])
payload = envelope["data"]
project_readiness = payload["project_readiness"]
```

WaveKit should deserialize the six transport fields first, validate
`contract_version == "p2p-cli/v1"`, and then dispatch `data` by `operation`.
Parser failures are JSON and therefore do not require a separate stderr parser.

MCP responses are protocol-native and are not wrapped in `p2p-cli/v1`.

## Idempotent Vertical Mutations

The three vertical apply commands require an opaque caller key in addition to
the preview token, actor and explicit confirmation:

```text
--idempotency-key <operation-uuid>
```

WaveKit should use its persisted operation UUID. P2P stores only its SHA-256
hash and commits the success receipt in the same atomic workspace transaction
as the vertical mutation. An exact retry returns `already_applied` without
writing again. Reusing the key with a changed actor, token, coordinate,
checksum, profile, modules or mapping fails with `P2P_IDEMPOTENCY_CONFLICT`.
Changed committed files fail with `P2P_IDEMPOTENCY_POSTCONDITION_DRIFT`.

After a lost or uncertain response, inspect the redacted result with:

```bash
p2p mutation status \
  --idempotency-key <operation-uuid> \
  --root <project-root> \
  --format json
```

The successful lookup states are `not_found`, `applied`,
`postcondition_drift` and `incomplete`. An incomplete state requires the
existing `p2p workspace transaction status|resume|rollback` workflow. A
malformed or inconsistent receipt is a typed
`P2P_IDEMPOTENCY_RECEIPT_CORRUPT` failure. Status output never includes the raw
key, request payload or preview token.

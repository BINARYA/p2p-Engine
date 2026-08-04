# Design - Versioned CLI Contract And Idempotent Mutation Receipts

## Decision Summary

Separate transport consistency from domain payloads. Every CLI JSON command
uses one envelope; each operation retains its own typed `data`. For the three
vertical apply operations, a durable receipt is part of the atomic candidate so
an uncertain caller can retry without inferring state from unrelated reads.

## CLI Envelope V1

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": true,
  "operation": "vertical.install.apply",
  "data": {},
  "warnings": [],
  "error": null
}
```

Failure replaces `data` with null and provides:

```json
{
  "code": "P2P_SOME_STABLE_CODE",
  "message": "Human-readable diagnostic.",
  "details": {}
}
```

A shared module owns constructors and output, but command modules still map
domain values to operation-specific data. This avoids a broad untyped response
object. A command inventory test enumerates every `--format json` surface and
prevents unwrapped additions.

## Parser Normalization

Typer/Click failures happen before handlers. A custom command/group boundary
detects `--format json` in the raw argument vector, maps usage exceptions to
stable request errors and emits the envelope once. Help and text mode retain
normal Click behavior. Unexpected exceptions are not swallowed; JSON mode maps
them to an internal code while preserving traceback behavior in development
logs/stderr.

Exit classes are constants, not inferred from message text:

```text
0 success
2 invalid request/usage
3 conflict or failed precondition
4 authentication/authorization
5 unavailable dependency or transport
1 internal/unclassified failure
```

## Version Command

The command reads package `__version__` and constants from workspace schema,
vertical schema and portable package modules. It does not instantiate a
workspace. This makes it usable by WaveKit worker startup probes before a
project root exists.

## Receipt Identity And Fingerprint

The caller supplies a high-entropy operation UUID. Storage derives:

```text
key_sha256 = sha256(UTF-8 raw key)
path = .p2p/.internal/mutation-receipts/<key_sha256>.yml
```

The raw key is never persisted. A canonical request fingerprint binds:

- operation identifier;
- actor;
- exact coordinate/artifact and expected checksums;
- normalized mapping content when applicable;
- preview-token SHA-256;
- any option that changes semantic result.

## Atomic Apply Algorithm

Before recomputing a preview, apply checks the receipt path:

1. no receipt: continue normal apply;
2. matching completed receipt and matching postconditions: return recorded
   result as `already_applied`;
3. matching key hash but different request fingerprint: idempotency conflict;
4. matching receipt but postcondition drift: explicit drift error;
5. corrupt receipt or recovery-owned transaction: fail closed.

For a new operation, the service recomputes/validates the preview and includes
the candidate receipt in the exact same `AtomicMutationWriter.apply` file map
as vertical, lock, definition and history changes. Final postcondition hashes
are computed from candidate bytes before commit and embedded in the receipt.
The existing rollback journal therefore restores both domain files and receipt
consistently. Successful cleanup removes only the transaction journal.

## Mutation Status

`MutationReceiptService.status` hashes the supplied key, validates the receipt,
checks each recorded path/hash against current state and inspects transaction
recovery when needed. It returns a redacted read model. `not_found` is a normal
lookup state so callers can choose whether to retry the original apply.

## Preview Lifetime

No wall-clock timestamp participates in token validity. Tokens remain valid
until a bound source precondition changes. Existing timestamps may remain as
observability metadata but cannot independently block apply.

## Module Ownership

- `cli_contract.py`: envelope, error model, exit classes and output.
- `cli.py`: root parser boundary and version/mutation group registration.
- existing command modules: stable operation IDs and typed data mapping.
- `core/mutation_receipts.py`: receipt/status models.
- `services/mutation_receipts.py`: fingerprint, lookup and postcondition
  verification.
- `services/vertical_lifecycle.py`: idempotent apply orchestration.
- `storage/workspace_transactions.py`: unchanged atomic commit primitive;
  receipts are candidate files, not a second transaction system.

## MCP Decision

MCP protocol responses are not wrapped in `p2p-cli/v1`. If an MCP tool later
calls an idempotent service it must supply a caller key in its own schema. No
new MCP mutation surface is required in 0.4.6.

## Rollout

1. Add envelope/version infrastructure and command inventory.
2. Convert JSON commands module by module with golden tests.
3. Add receipt models/status without changing apply.
4. Integrate receipts into install, adopt and migrate apply.
5. Fault-test response loss and atomicity.
6. Update WaveKit fixtures/pin in its separate implementation repository.


# Design - Replace Project Structure From Release

## Requirements Covered

- R001-R018
- N001-N004
- AC001-AC010

## Decision Summary

Implement replacement as a specialized structure transition over the same
normalizer, impact analyzer, disposition plan and atomic writer used by
project-owned structure retirement. The target release is only an input
snapshot; successful apply creates a detached project revision and a new origin
event.

## Key Decisions

### D001 - Replacement Is Not Vertical Adoption

The project does not acquire an active release lock. The exact release identity
is captured in a `StructureReplaced` event, while the resulting current
structure receives project-local identity and checksum.

### D002 - Exact Identity Or Owner Decision

Stable compatible IDs allow automatic preservation. Semantic collisions,
removed targets and active references require typed decisions. Labels and
similarity may be advisory suggestions only and never authorize apply.

### D003 - Reuse Retirement Dispositions

Target-removed source elements are retired using P4 semantics. Proposed target
IDs can receive active reference assignments. One plan can therefore preserve,
reassign, globalize, unassign where legal or archive supported active content.

### D004 - Two Preview Phases And One Atomic Apply

Analysis preview discovers decisions. A complete normalized plan is re-previewed
against exact source and target identities to obtain an apply token. Structure,
memory scopes, event and receipt commit together.

### D005 - No Automatic Upgrade Channel

The origin event may expose that a newer release exists through an external
catalog, but P2P neither polls nor applies it. A later user request begins a new
replacement or selective merge workflow.

### D006 - Replacement Uses A Higher-Risk Capability

Replacement declares `project.structure.replace`, distinct from simple
`project.structure.edit`. The AuthorityContext is bound to both preview phases,
the disposition plan and receipt. Access to a source release never implies
authority to replace a project's current structure.

## Components And Ownership

- Exact release resolver and structure-source normalizer.
- Structure replacement comparator.
- Existing impact/disposition services.
- Replacement materializer and lifecycle orchestrator.
- Receipt/status/recovery adapters.
- CLI apply handlers and read-only MCP inspection/comparison handlers.

MCP replacement apply is explicitly deferred. The preview tool accepts only an
already resolvable exact release and performs no pull, project write or receipt
creation. Standalone apply remains a documented CLI workflow; WaveKit invokes
the same CLI service through its protected worker.

## Alternatives Considered

- Reuse old vertical migrate and keep the lock authoritative: rejected because
  it violates detached project ownership.
- Replace structure and orphan all old references: rejected because it silently
  weakens project memory.
- Automatic upgrade to latest compatible release: rejected because origin is
  provenance, not a subscription.

## Compatibility

The operation accepts only schema-3 releases and schema-4 projects. Old
vertical-transition plan documents are not valid replacement plans.

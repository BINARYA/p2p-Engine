# Core API Reference

This document is the contributor-facing API reference for P2P Engine's Python core.

Status: preliminary contributor reference. End-user agents should prefer CLI and
MCP. Python API documentation is for contributors, future adapters, and
maintainers.

## Primary Facade

The current core facade is:

```python
from pathlib import Path

from p2p_engine.storage.filesystem import P2PWorkspace

workspace = P2PWorkspace(Path("."))
```

`P2PWorkspace` is intentionally stable for the MVP, but it is large. A future refactor is expected to split internal behavior into managers while keeping a compatibility facade.

## Public Areas

Current method families include:

- project initialization and agent instructions;
- status, validation, context, readiness, and maturity;
- proposals and contributions;
- decisions, votes, and precedents;
- choices and choice discovery;
- project state and operational brief;
- Change Sets;
- software specs and export;
- Work lifecycle;
- registries;
- conflicts and impact analysis.

## Example

```python
from pathlib import Path

from p2p_engine.storage.filesystem import P2PWorkspace

workspace = P2PWorkspace(Path("/path/to/project"))
proposal = workspace.create_proposal_with_details(
    title="Define onboarding",
    problem="New users need a clear setup flow.",
    goals=["Make init understandable."],
    proposal="Use a guided wizard.",
    acceptance_criteria=["A user can initialize a project without editing .p2p."],
)
print(proposal.proposal_id)
```

## Error Model

Most public methods raise `ValueError` for invalid IDs, missing source artifacts, invalid lifecycle transitions, or unsupported options.

## Documentation Plan

This file should grow into:

- public method index;
- arguments, returns, and raised errors;
- examples for stable method families;
- notes on which methods are internal helpers despite being visible in Python;
- migration notes for the planned P2PWorkspace refactor.

## Planned Additions

- proposal lifecycle API;
- choice API;
- Change Set API;
- Work API;
- assessment/rubric API;
- MCP/core mapping;
- refactor boundaries.

# Implementation Note - Domain-Aware Visible Project Definition Export

## Implemented

- Added visible project definition export service.
- Added `P2PWorkspace` facade delegation for visible export and export status.
- Added CLI commands:
  - `p2p project export`
  - `p2p project export-status`
- Added MCP tools:
  - `p2p_project_export`
  - `p2p_project_export_status`
- Updated CLI and MCP documentation.
- Preserved legacy `.p2p/outputs/spec-export/...` behavior.

## Verification

```text
.venv/bin/pytest
379 passed in 62.33s
```

```text
.venv/bin/p2p validate
errors: 0
warnings: 0
infos: 0
findings: none
```

Focused compatibility checks also passed for spec export service and MCP
work/spec export flow.

## Follow-Up

After this feature, revisit the proactive proposal-readiness skill and readiness
calculation behavior. `PROP-083` showed two issues:

- agent guidance should push through missing proposal artifacts more
  deterministically before returning to the owner;
- readiness calculation remains conservative even after all missing artifacts are
  resolved, so `refresh/init` semantics and confidence promotion need review.

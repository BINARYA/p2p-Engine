# P2PWorkspace Final Quality Review Future Evolutions

Future evolution candidates discovered during final quality review will be
recorded here. These items are not mandatory cleanup tasks unless later promoted
to a focused local feature.

## Candidates

- Consider an atomic file write/store abstraction for persisted YAML/Markdown
  state if concurrent agent writes become a real operating scenario.
- Consider narrower internal collaborators inside `services.work_branches` and
  `services.proposal_branches` if future changes show duplicated manifest,
  metadata, or Git lifecycle handling.
- Consider a focused diagnostic-error model for MCP machine-facing failures
  where stable error codes would improve automation.
- Consider tightening `mcp.consent_audit.safe_head()` to catch narrower Git
  failures or document the best-effort behavior explicitly.
- Consider adding dedicated merge-conflict MCP consent-audit tests for proposal
  merge conflict paths.

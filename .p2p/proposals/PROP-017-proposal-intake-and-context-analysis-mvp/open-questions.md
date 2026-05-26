# Open Questions - PROP-017

## Resolved For MVP

1. Direct AI calls are excluded from the MVP.
   - No. MVP remains prompt-only.

2. Proposal acceptance and rejection remain outside intake.
   - No. Intake only recommends next actions.

3. Intake uses generated registries as compact project memory.
   - Yes. Registries are the compact project memory layer for intake.

4. Multi-user and multi-agent workflows are supported through shared artifacts first.
   - Yes, but initially through shared `.p2p/` artifacts, not MCP.

## Still Open

1. Should intake artifacts use `.p2p/intake/` or live inside each proposal directory?
2. Should `p2p proposal create` optionally run intake first?
3. What minimum structured schema should `suggested-actions.yml` use?

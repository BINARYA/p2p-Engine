# Alternatives - PROP-088

## Option A - Add MCP parity for existing imports first

Expose `p2p_impact_import` and `p2p_explore_import` equivalents that call the
existing import services. This is the recommended MVP because behavior,
validation, and CLI semantics already exist.

## Option B - Add a generic proposal artifact import tool

Provide one MCP tool for multiple artifact kinds. This may be useful later, but
it needs a strict allowlist, per-artifact validation, and clear ownership
rules. It is riskier as the first step because it can become an arbitrary
managed-file write path.

## Option C - Keep MCP as state-only and require CLI for content imports

This preserves the current boundary but leaves MCP agents unable to complete
artifact-aware readiness workflows. It conflicts with the agent-first direction
from PROP-086.


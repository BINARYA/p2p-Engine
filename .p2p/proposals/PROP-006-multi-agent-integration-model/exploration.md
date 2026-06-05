# Exploration - PROP-006

PROP-006 began as a proposal to introduce a multi-agent integration model.
Subsequent development has already implemented the first layer: agent profiles
and generated instructions for `generic`, `codex`, and `claude`.

The proposal should now be reframed around the next missing layer:

```text
Agent Integration Registry MVP
```

The problem is no longer whether P2P can generate agent instructions. The
problem is whether P2P can manage installed integrations safely over time:

- list what is installed;
- explain what files an adapter owns;
- detect drift;
- update generated files safely;
- uninstall without deleting user changes;
- support multiple agents in one repository;
- add adapter-specific files for Cursor, Copilot, Gemini, and OpenCode.

The strongest direction is a governed registry with adapter-specific file
targets, hashes, shared-file semantics, and conservative lifecycle commands.

# Local demos

This directory is reserved for disposable P2P Engine demo projects. Generated
projects are ignored by Git because their `.p2p/` state and agent instructions
reflect the exact runtime that created them and would otherwise become stale
copies of the maintained templates.

From the repository root, create a current demo with the development runtime:

```bash
mkdir -p examples/local-demo
.venv/bin/p2p init "Local Demo" \
  --root examples/local-demo \
  --agent all \
  --starter generic \
  --mcp-hint
```

Use a temporary directory instead when the demo does not need to remain in the
checkout. Automated tests must always create isolated projects under pytest's
temporary directories and must not depend on local demo contents.

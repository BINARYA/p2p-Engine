# P2PWorkspace Proposal Prompt Artifact Service Extraction Design

## Current Runtime Shape

`storage/filesystem.py` still owns proposal prompt and artifact behavior:

- `generate_prompt()`;
- `import_exploration()`;
- `exploration_status()`;
- `import_artifact()`;
- `import_impact()`;
- exploration status dataclasses and quality helpers.

CLI prompt commands and MCP prompt tools call these methods through
`P2PWorkspace`.

## Target Shape

Add `src/p2p_engine/services/proposal_artifacts.py` with:

- `ProposalArtifactService`;
- `PromptKind` and `ImportKind` aliases;
- `ExplorationArtifactStatus` and `ExplorationStatus`;
- exploration artifact constants and quality helpers;
- prompt context assembly and renderer dispatch;
- import behavior for exploration, generated artifacts, and impact artifacts.

`P2PWorkspace` remains the compatibility facade and delegates existing methods
to the service.

## Service Dependencies

The service receives:

- `root`;
- `p2p_dir`;
- `find_proposal_dir` callback.

The service may import prompt renderers and foundation validators. It must not
import CLI/MCP/runtime branch/sync modules.

## Compatibility Rules

- Preserve prompt output directory `.p2p/prompts/<proposal_id>/`.
- Preserve all context keys consumed by prompt renderers.
- Preserve exact exploration artifact filenames.
- Preserve YAML validation behavior for task and impact imports.
- Preserve relative path returns from all imports and generation methods.

## Verification Map

```bash
.venv/bin/pytest tests/test_proposal_artifact_service.py
.venv/bin/pytest tests/test_cli.py -k "prompt or exploration or impact"
.venv/bin/pytest tests/test_mcp.py -k "prompt_tools"
.venv/bin/pytest tests/test_skeleton.py -k "prompt or exploration"
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in `src/p2p_engine/services/proposal_artifacts.py`.

`P2PWorkspace` now delegates prompt generation, exploration import/status,
generic artifact import, and impact import to `ProposalArtifactService` while
preserving the same public facade methods.

Verification completed:

```bash
.venv/bin/pytest tests/test_proposal_artifact_service.py
.venv/bin/pytest tests/test_cli.py -k "prompt or exploration or impact"
.venv/bin/pytest tests/test_mcp.py -k "prompt_tools"
.venv/bin/pytest tests/test_skeleton.py -k "prompt or exploration"
.venv/bin/p2p validate
.venv/bin/pytest
```

Result: focused tests passed, validation reported 0 findings, and the full
suite passed with 346 tests.

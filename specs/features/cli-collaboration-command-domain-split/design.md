# CLI Collaboration Command Domain Split Design

## Current Shape

`src/p2p_engine/cli_commands/collaboration.py` is approximately 537 lines and
owns several unrelated CLI groups:

- governance, vote, and precedent commands;
- impact and conflict commands;
- registry commands;
- intake and intake apply commands;
- choice commands.

The file is presentation glue, but it is no longer an ideal unit of ownership.

## Target Shape

Keep `collaboration.py` as the public compatibility wrapper:

```text
src/p2p_engine/cli_commands/
  collaboration.py          # public wrapper imported by cli.py
  governance.py             # governance, vote, precedent commands
  project_analysis.py       # impact and conflict commands
  registry.py               # registry commands
  intake.py                 # intake and intake apply commands
  choices.py                # choice commands
```

`register_collaboration_commands()` delegates to each focused module.

## Compatibility

No command body behavior should change. The split preserves output by moving
existing functions with minimal edits.

Focused verification is `tests/test_cli.py`; final verification is
`.venv/bin/p2p validate` and the full test suite.

## Final Shape

After extraction:

| Module | Lines | Responsibility |
| --- | ---: | --- |
| `cli_commands/collaboration.py` | 27 | Public compatibility wrapper imported by `cli.py`. |
| `cli_commands/governance.py` | 108 | Governance, vote, and precedent commands. |
| `cli_commands/project_analysis.py` | 79 | Impact and conflict commands. |
| `cli_commands/registry.py` | 88 | Registry refresh/status/show commands. |
| `cli_commands/intake.py` | 115 | Intake and intake apply commands. |
| `cli_commands/choices.py` | 191 | Choice commands. |

The focused baseline and post-split verification used `tests/test_cli.py`, with
93 passing tests in both runs.

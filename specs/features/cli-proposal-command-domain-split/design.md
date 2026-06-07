# CLI Proposal Command Domain Split Design

## Current Shape

`src/p2p_engine/cli_commands/proposals.py` is approximately 616 lines and owns:

- proposal create/update/list/show commands;
- proposal readiness commands and readiness rendering;
- proposal branch lifecycle commands and branch rendering;
- proposal accept/reject/defer and direct decision record commands;
- contribution add/list commands across legacy and nested command surfaces.

The file is presentation glue, but it combines several proposal subdomains.

## Target Shape

Keep `proposals.py` as the public compatibility wrapper:

```text
src/p2p_engine/cli_commands/
  proposals.py              # public wrapper imported by cli.py
  proposal_core.py          # create/update/list/show
  proposal_readiness.py     # readiness commands/rendering
  proposal_branches.py      # branch lifecycle commands/rendering
  proposal_decisions.py     # accept/reject/defer and decision record
  proposal_contributions.py # contribution command surfaces
```

`register_proposal_commands()` delegates to each focused module.

## Compatibility

No command body behavior should change. The split preserves output by moving
existing functions and helpers with minimal edits.

Focused verification is `tests/test_cli.py`; final verification is
`.venv/bin/p2p validate` and the full test suite.

## Final Shape

After extraction:

| Module | Lines | Responsibility |
| --- | ---: | --- |
| `cli_commands/proposals.py` | 23 | Public compatibility wrapper imported by `cli.py`. |
| `cli_commands/proposal_core.py` | 113 | Proposal create/update/list/show commands. |
| `cli_commands/proposal_readiness.py` | 96 | Readiness commands and readiness rendering. |
| `cli_commands/proposal_branches.py` | 225 | Proposal branch lifecycle commands and branch rendering. |
| `cli_commands/proposal_decisions.py` | 118 | Proposal accept/reject/defer and decision record commands. |
| `cli_commands/proposal_contributions.py` | 109 | Legacy and nested contribution command surfaces. |

The focused baseline and post-split verification used `tests/test_cli.py`, with
93 passing tests in both runs.

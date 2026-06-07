# CLI Work/Spec Command Domain Split Design

## Current Shape

`src/p2p_engine/cli_commands/work_specs.py` is approximately 535 lines and
registers three distinct command domains:

- `change_app`: Change Set create/status/policy/show/set-status/tasks.
- `spec_app`: software spec refresh/status/show/prompt/import/export/export
  status/show/validate.
- `work_app`: Work plan/list/status/scan/branch/retire/submit/review/publish/
  request-review/accept/finalize/cleanup/show.

The file is presentation glue, but it combines unrelated CLI command groups.

## Target Shape

Keep the public registration module as a compatibility wrapper:

```text
src/p2p_engine/cli_commands/
  work_specs.py       # public wrapper imported by cli.py
  changes.py          # p2p change commands
  specs.py            # p2p spec commands
  work.py             # p2p work commands
```

`work_specs.register_work_spec_commands()` delegates to:

- `register_change_commands(change_app)`
- `register_spec_commands(spec_app)`
- `register_work_commands(work_app)`

## Compatibility

No command body logic should change. This is a structural split only.

The focused verification is `tests/test_cli.py` because it exercises the public
Typer application and command output. The final verification remains full suite
plus `.venv/bin/p2p validate`.

## Final Shape

After extraction:

| Module | Lines | Responsibility |
| --- | ---: | --- |
| `cli_commands/work_specs.py` | 17 | Public compatibility wrapper imported by `cli.py`. |
| `cli_commands/changes.py` | 121 | `p2p change` command registration and output. |
| `cli_commands/specs.py` | 138 | `p2p spec` command registration and output. |
| `cli_commands/work.py` | 294 | `p2p work` command registration and output. |

The focused baseline and post-split verification used `tests/test_cli.py`, with
93 passing tests in both runs.

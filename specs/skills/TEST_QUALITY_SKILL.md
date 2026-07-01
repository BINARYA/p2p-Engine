# Test Quality Skill

## Purpose

Use this skill when adding, changing, reviewing, or reorganizing tests in this
repository.

The goal is to protect observable behavior with the smallest useful test set,
without creating redundant, slow, or brittle coverage.

## Core Rule

Add tests at the lowest layer that proves the behavior. Add public-surface tests
only when the public surface has its own contract to protect.

Good tests make future changes safer. They should not merely increase the test
count.

## Test Layer Selection

- Use `unit` tests for pure helpers, parsing, formatting, small domain rules, and
  deterministic functions.
- Use `service` tests for domain/application workflows, validation behavior,
  lifecycle transitions, persisted project state, and facade delegation.
- Use `adapter` tests for filesystem, serialization, Git adapter, external tool,
  or environment-facing behavior.
- Use `cli` tests for command names, options, output, exit behavior, and
  user-visible side effects.
- Use `mcp` tests for tool names, schemas, payloads, permission boundaries,
  error payloads, and machine-facing contracts.
- Use `integration` tests when behavior crosses multiple boundaries and cannot
  be proven safely at one lower layer.
- Use `git` tests for branch, remote, sync, commit, merge, publish, and managed
  collaboration behavior.
- Use `slow` for broad or materially expensive tests that should not enter the
  default focused loop.
- Use `smoke` for small broad-confidence tests that can run after low-risk
  changes.

## Duplication Rules

- Do not test the same scenario in service, CLI, and MCP layers unless each
  layer has a distinct contract.
- If service behavior changes but CLI output does not, prefer service tests.
- If CLI output or exit behavior changes, add or update CLI tests.
- If MCP schema, payload, permissions, or errors change, add or update MCP tests.
- If a bug is visible only through CLI or MCP, add the regression test at that
  public surface, then add lower-layer tests only when reusable logic needs
  protection.

## Assertion Rules

- Prefer behavior assertions over private implementation details.
- Assert stable public strings, fields, status values, files, and side effects.
- Avoid broad snapshots unless the serialized artifact is the contract.
- Use explicit temporary roots and deterministic fixtures.
- Do not depend on local machine paths, user names, current branch names, or
  ambient Git configuration.

## Validation Rules

Every non-trivial implementation should report:

- focused tests used during implementation;
- public-contract tests if CLI, MCP, persistence, validation, Git, or generated
  artifacts can be observed externally;
- full-suite validation before commit, push, release, or merge unless explicitly
  deferred with residual risk.

Recommended commands:

```bash
./scripts/test-focused.sh
./scripts/test-public.sh
./scripts/test-smoke.sh
./scripts/test-full.sh
```

Direct pytest selection remains valid for narrow work:

```bash
.venv/bin/pytest tests/test_readiness_service.py
.venv/bin/pytest -m "service and not slow"
.venv/bin/pytest -m "cli or mcp"
```

## When A Test Is Not Useful

A proposed test is usually not useful when it:

- repeats the same assertion at another layer without protecting a new contract;
- asserts private implementation details that may change safely;
- requires fragile ordering not guaranteed by the contract;
- depends on local environment or current Git state;
- uses a broad snapshot where focused fields would be clearer;
- validates framework or library behavior instead of project behavior;
- makes the focused loop slower without improving regression protection.

## Refactoring Existing Tests

When reorganizing tests:

- preserve behavior first;
- apply markers before moving large files;
- split large files only by clear ownership or execution benefit;
- validate every split with focused and broad commands;
- do not combine test reorganization with production behavior changes.

## Completion Checklist

Before finishing test work:

```text
[ ] The test layer matches the changed behavior.
[ ] Public contracts are tested only where they changed or need protection.
[ ] Markers are present through file, function, or collection policy.
[ ] Focused tests were run.
[ ] Public-contract tests were run when public behavior could be affected.
[ ] Full-suite validation was run or explicitly deferred with risk.
[ ] No test depends on local machine state.
[ ] No redundant broad test was added without justification.
```

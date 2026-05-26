# Clarifications - PROP-013

## Q1. Which alternative is selected?

Alternative D - Managed Git Under The Hood.

The user-facing model should expose P2P concepts:

```text
proposal
choice
decision
change
task
```

Git concepts remain internal implementation details:

```text
branch
commit
merge
tag
```

## Q2. How do we mitigate the cons of Alternative D?

Alternative D has three main cons:

1. It requires a Git adapter.
2. It requires careful safety rules for automatic commits/branches/tags.
3. Debugging internal Git state needs explicit tooling.

The mitigation is a staged rollout:

```text
Stage 1 - metadata only
  P2P records git_policy.yml and planned Git behavior, but does not mutate Git.

Stage 2 - read-only diagnostics
  P2P can inspect Git status/log/branch state and explain it.

Stage 3 - explicit safe writes
  P2P can create commits/tags only after project opt-in or explicit command.

Stage 4 - managed branches/merges
  P2P can manage branches and merges only after doctor/debug/recovery tools exist.
```

## Q3. What is the MVP decision?

For MVP, choose `metadata_only`.

```yaml
git_policy:
  mode: managed
  operation_level: metadata_only
  expose_git_details: false
  commits:
    auto_commit: false
  branches:
    auto_create: false
  tags:
    auto_create: false
```

This preserves the architecture without introducing unsafe Git side effects too early.

## Q4. What must be visible to users?

Normal output should show only P2P concepts.

Verbose output may show planned Git operations:

```bash
p2p status --verbose
```

Doctor/debug output should show Git state, policy reasoning, and repair hints:

```bash
p2p doctor
p2p internals git-policy
```

## Q5. What should AI agents do?

AI agents should use the P2P public interface by default.

They should not run direct Git branch/commit/merge commands unless the user explicitly asks for debug/repair work.

## Q6. Can a Change Set be created from draft proposals?

No. For the MVP, a Change Set can be created only from at least one accepted proposal or accepted decision.

A Change Set is an operational package. It does not represent an open discussion or unstable proposal.

```text
draft proposal → no change set
exploring proposal → no change set
ready_for_decision proposal → no change set
accepted proposal → can create change set
accepted decision → can create change set
```

## Q7. Can draft proposals be included as context?

Yes, but only as non-binding references.

Change Sets should distinguish:

```yaml
included_proposals:
  - PROP-013

referenced_proposals:
  - PROP-010
  - PROP-011
  - PROP-012

excluded_alternatives:
  - proposal: PROP-001
    reason: "Branch-per-proposal assumption superseded by managed Git model."
```

Draft, exploratory, rejected, or superseded proposals may be references, rationale, or rejected alternatives. They cannot define binding operational scope.

## Q8. What is the Git operation level for MVP?

For MVP, Managed Git Under The Hood remains `metadata_only`.

```yaml
git_policy:
  mode: managed
  operation_level: metadata_only
  commits:
    auto_commit: false
  branches:
    auto_create: false
  tags:
    auto_create: false
```

No automatic commits, branches, tags, or merges in the MVP.

Future managed branches require:

- `operation_level = managed_branches`;
- passing `p2p doctor`;
- clean working tree or explicit snapshot;
- existing Change Set;
- Change Set status `implementation_ready`;
- at least one accepted decision;
- execution plan;
- tasks;
- recovery strategy;
- explicit user command or enabled policy.

## Q9. How should Change Sets map to `.p2p/project/features/`?

`.p2p/project/features/` is a derived project view, not a primary source of truth.

Primary sources:

```text
.p2p/proposals/
.p2p/choices/
.p2p/decisions/
.p2p/changes/
```

Derived project views:

```text
.p2p/project/map.md
.p2p/project/registry.yml
.p2p/project/features/
.p2p/project/roadmap.yml
.p2p/project/outcomes.yml
```

This prevents confusion between proposal, feature, change, and task.

## Q10. Can Change Sets include non-software work?

Yes. A Change Set is a multi-domain operational package derived from accepted project intent.

Allowed domains:

```text
software
documentation
marketing
commercial
operations
governance
research
mixed
```

Software Change Sets may export to OpenSpec or Spec Kit. Non-software Change Sets may export to Markdown, task boards, documents, or checklists. Mixed Change Sets should produce separate workstreams.

## Q11. What thresholds should trigger internal branches after metadata-only?

No branch creation in the MVP.

```yaml
git_policy:
  operation_level: metadata_only
  branches:
    auto_create: false
```

Future internal branch creation can be enabled only for operational Change Sets, not exploratory proposals.

Minimum requirements:

```yaml
internal_branch_policy:
  can_create_branch_when:
    - change_set_status_is_implementation_ready
    - source_has_accepted_proposal_or_decision
    - execution_plan_exists
    - tasks_exist
    - p2p_doctor_passes
    - git_worktree_is_clean_or_snapshot_exists
    - recovery_strategy_exists
    - explicit_command_or_policy_opt_in
```

Future branch triggers:

```yaml
branch_triggers:
  - software_code_change
  - structural_project_change
  - template_or_governance_change
  - multi_actor_collaboration
  - divergent_alternative_selected
  - high_risk_change
  - long_running_change
  - external_export_target_required
```

Even in the future, `auto_create: true` should not be the default. Prefer explicit conceptual commands such as:

```bash
p2p change start CHANGE-001
```

## Q12. What are the minimum required fields for `change.md`?

`change.md` should use YAML frontmatter for machine-readable metadata and Markdown for human-readable context.

Minimum frontmatter fields:

```yaml
change_id: CHANGE-001
title: CLI Foundation
status: proposed
created_at: 2026-05-20
created_by: davide
execution_domains:
  - software
  - documentation
source:
  accepted_proposals:
    - PROP-001
  accepted_decisions:
    - DEC-001
implementation_targets:
  - markdown
  - local_cli
spec_targets:
  - p2p_spec
export_targets:
  - openspec
  - speckit
plan_ref: execution-plan.md
tasks_ref: tasks.yml
```

Target taxonomy:

```text
execution_domains = type of work, such as software, documentation, governance, research, operations, commercial, or mixed
implementation_targets = where the work is implemented in the project, such as local_cli, docs, p2p_governance, or project_metadata
spec_targets = normalized P2P specification outputs to produce before downstream export, such as p2p_spec
export_targets = downstream formats/tools to generate from normalized specs, such as openspec, speckit, markdown, or task_board
```

`p2p_spec` is not a code generator. It is the P2P-native normalized specification layer consumed by exporters. OpenSpec and Spec Kit remain downstream export targets, not the internal source of truth.

Minimum Markdown sections:

```text
Summary
Rationale
Scope
  Included
  Excluded
Deliverables
Acceptance Criteria
Dependencies
Risks
Related Choices
```

The core questions are:

```text
1. What are we implementing?
2. Which accepted decision/proposal authorizes it?
3. What is in/out of scope?
4. What deliverables are expected?
5. How do we know it is complete?
```

## Q13. What lifecycle should a Change Set have?

The Change Set lifecycle is separate from proposal status.

Proposal decides. Change Set implements.

Statuses:

```text
proposed
planned
implementation_ready
in_progress
blocked
in_review
completed
cancelled
superseded
```

Primary flow:

```text
proposed
→ planned
→ implementation_ready
→ in_progress
→ in_review
→ completed
```

Side transitions:

```text
proposed/planned/implementation_ready/in_progress
→ blocked

blocked
→ planned
→ implementation_ready
→ in_progress
→ cancelled
→ superseded

proposed/planned/in_progress
→ cancelled
→ superseded
```

`implementation_ready` is the minimum future state for internal branch creation.

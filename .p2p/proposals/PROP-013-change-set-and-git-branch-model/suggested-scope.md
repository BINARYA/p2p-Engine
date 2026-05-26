# Suggested Scope - PROP-013

## Include

- Define `.p2p/changes/`.
- Define change-set metadata.
- Define change-set creation policy.
- Define Git as an internal adapter.
- Define public P2P UX without branch/commit/merge concepts.
- Define managed `git_policy.yml`.
- Define verbose/debug visibility for internal Git operations.
- Define branch/commit/tag policy criteria.
- Define first CLI commands for a later implementation:
  - `p2p change create --from PROP-XXX`
  - `p2p change status CHANGE-XXX`
  - `p2p change policy CHANGE-XXX`
  - `p2p status --verbose`
  - `p2p doctor`

## Exclude

- Actual Git branch/commit/merge automation in the first proposal.
- Pull request integration.
- GitHub/GitLab-specific automation.
- Automatic merge.

## Change Set Policy

```yaml
change_set_policy:
  creation:
    allowed_from:
      - accepted_proposal
      - accepted_decision
    disallowed_from:
      - draft_proposal
      - exploring_proposal
      - rejected_proposal

  references:
    allow_draft_references: true
    draft_references_are_binding: false

  domains:
    allow_non_software: true
    allowed_domains:
      - software
      - documentation
      - marketing
      - commercial
      - operations
      - governance
      - research
      - mixed

  git:
    mvp_operation_level: metadata_only
    branch_creation_in_mvp: false
    future_branch_creation_requires:
      - operation_level_managed_branches
      - clean_doctor_status
      - implementation_ready_change
      - accepted_decision
      - execution_plan
      - tasks
      - recovery_strategy
      - explicit_user_command

  project_mapping:
    primary_sources:
      - proposals
      - choices
      - decisions
      - changes
    derived_views:
      - project_map
      - project_features
      - roadmap

  change_md_minimum_fields:
    - change_id
    - title
    - status
    - created_at
    - created_by
    - summary
    - source
    - rationale
    - scope
    - execution_domains
    - deliverables
    - acceptance_criteria
    - dependencies
    - risks
    - implementation_targets
    - related_choices
    - plan_ref
    - tasks_ref

  lifecycle:
    statuses:
      - proposed
      - planned
      - implementation_ready
      - in_progress
      - blocked
      - in_review
      - completed
      - cancelled
      - superseded
```

## Managed Git Policy

```yaml
git_policy:
  mode: managed
  operation_level: metadata_only
  expose_git_details: false
  proposal_branching:
    default: auto
    create_branch_when:
      - complex_proposal
      - divergent_alternative
      - formal_review_required
      - multi_actor_edit
  change_branching:
    default: auto
    create_branch_when:
      - source_code_changes
      - governance_changes
      - schema_or_template_changes
      - public_cli_behavior_changes
      - high_impact
      - mutually_exclusive_alternative
  commits:
    auto_commit: false
    message_style: conventional
    include_actor: true
  tags:
    create_for_decisions: false
    create_for_changes: false
  debug:
    show_internal_operations_with_verbose: true
```

## Rollout Stages

```text
Stage 1 - metadata only
  Define git_policy.yml and planned operations. No Git mutation.

Stage 2 - read-only diagnostics
  Add p2p doctor and verbose Git state inspection.

Stage 3 - explicit safe writes
  Add opt-in commits/tags.

Stage 4 - managed branches and merges
  Add branch/merge automation after recovery tooling exists.
```

## Initial Change Set Structure

```text
.p2p/changes/
  CHANGE-001-cli-foundation/
    change.md
    included-proposals.yml
    referenced-proposals.yml
    excluded-alternatives.yml
    included-decisions.yml
    impact-map.yml
    git-policy.yml
    execution-plan.md
    tasks.yml
```

## Change Set Lifecycle

```yaml
change_lifecycle:
  statuses:
    - proposed
    - planned
    - implementation_ready
    - in_progress
    - blocked
    - in_review
    - completed
    - cancelled
    - superseded

  transitions:
    proposed:
      allowed_next:
        - planned
        - cancelled
        - superseded
    planned:
      allowed_next:
        - implementation_ready
        - blocked
        - cancelled
        - superseded
    implementation_ready:
      allowed_next:
        - in_progress
        - blocked
        - cancelled
        - superseded
    in_progress:
      allowed_next:
        - in_review
        - blocked
        - cancelled
        - superseded
    blocked:
      allowed_next:
        - planned
        - implementation_ready
        - in_progress
        - cancelled
        - superseded
    in_review:
      allowed_next:
        - completed
        - in_progress
        - blocked
    completed:
      allowed_next: []
    cancelled:
      allowed_next: []
    superseded:
      allowed_next: []
```

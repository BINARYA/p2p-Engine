---
name: p2p-engine
description: Use when working inside a repository that contains a `.p2p/` workspace or when the user asks to use the P2P Engine method. Guides Codex to turn conversations into versioned P2P proposals, intake analyses, choices, decisions, Change Sets, plans, and tasks using the `p2p` CLI as the source of truth.
---

# P2P Engine Skill

Use this skill when the user wants to design, discuss, plan, decide, or implement work through P2P Engine.

## Core Rule

Do not leave important P2P work only in chat.

```text
CLI / engine = source of truth
Codex skill = conversational guide
Filesystem/Git = memory and audit trail
```

If P2P artifacts are created or changed, use the `p2p` CLI when practical and keep outputs under `.p2p/`.

## First Checks

From the repository root:

```bash
p2p check
p2p status
p2p context --budget small
p2p validate
p2p assess refresh
p2p assess maturity refresh
p2p registry refresh
p2p registry status
```

If `p2p` is unavailable but the project has `.venv/bin/p2p`, use:

```bash
.venv/bin/p2p check
.venv/bin/p2p status
```

If no `.p2p/` workspace exists, ask whether to initialize it before proceeding:

```bash
p2p init "Project Name"
```

For new user projects, prefer an agent-safe bootstrap. Select the first agent profile without treating it as permanent:

```bash
p2p init
p2p init "Project Name" --agent codex --repository local
p2p agent instructions refresh --profile claude
```

Calling `p2p init` without a project name starts the guided wizard for project name, initial agent profile, repository mode, and MCP setup hint. Passing a project name keeps the command scriptable.

Generated project instructions are part of the operating boundary:

```text
AGENTS.md
.p2p/agent-policy.yml
optional: CLAUDE.md, .codex/skills/p2p-project/SKILL.md
```

In projects initialized this way, read `AGENTS.md` and `.p2p/agent-policy.yml` before changing project state. If an available CLI command or explicit MCP write tool cannot perform the requested P2P mutation, stop and report the missing primitive. Do not reverse-engineer `.p2p/`, invent IDs, write decision files, or accept/reject/defer/decide on behalf of the owner.

When explaining existing P2P artifacts, read them from project state first. Use `p2p proposal show`, `p2p choice show`, `p2p change show`, `p2p work show`, or equivalent MCP show/read tools before summarizing. Do not explain saved proposals, choices, Change Sets, or Work items only from conversation memory.

When using the P2P MCP server, the bootstrap and maintenance write-safe tools are:

```text
p2p_init_project
p2p_agent_instructions_refresh
p2p_registry_refresh
p2p_validate
p2p_context
p2p_assess_refresh
p2p_assess_show
p2p_project_rubrics_init
p2p_project_rubrics_show
p2p_maturity_refresh
p2p_maturity_show
p2p_proposal_create
p2p_proposal_update
p2p_proposal_contribution_add
p2p_intake_prompt
p2p_intake_status
p2p_project_brief_prompt
p2p_project_brief_show
p2p_choice_discover
p2p_conflict_status
p2p_impact_prompt
```

These tools may initialize projects, refresh agent instructions, regenerate deterministic registries, validate project state, return compact context packets, generate/show deterministic readiness assessments, initialize/show project definition rubrics, generate/show deterministic project definition maturity, create and refine draft proposals, append proposal contributions, create/list intake prompts, generate/show operational brief artifacts, discover choice candidates, inspect recorded conflicts, and generate impact prompts. They do not authorize governance decisions, conflict recording, choice blocking/deciding, intake apply actions, brief imports, impact imports, or managed-work lifecycle actions.

## Token Budget Discipline

AI is expensive. CLI is cheap. Git is memory. `.p2p` is governance. Owner decides. Agent works in bounded sessions.

Before broad reads, ask the engine for compact context:

```bash
p2p context --budget small
p2p context --target PROP-XXX --budget small
```

With MCP, use `p2p_context` first. Treat the context packet as the default boundary for exploration.

Rules:

- Read summaries first; read details only by explicit ID.
- Prefer IDs, statuses, paths, and commands over full document bodies.
- Stop once the next bounded action is clear.
- Do not scan all `.p2p/`, all registries, all proposals, all source files, or Git history unless the task explicitly requires it or compact context is insufficient.
- If compact context is insufficient, state what is missing before expanding reads.

Before creating new proposal artifacts, inspect current state:

```bash
p2p proposal list
p2p proposal list --status accepted
p2p registry show choices
p2p change status
```

When the user asks where the project stands or what to do next, prefer the operational brief workflow over leaving the synthesis only in chat:

```bash
p2p project brief prompt
p2p project brief import brief-output/
p2p project brief show
p2p context --budget small
p2p next
p2p next --top 1
p2p assess refresh
p2p assess show
```

The skill guides the agent's synthesis behavior. The CLI owns the repeatable project context and stores the resulting `operational-brief.md` and optional `next-actions.yml` under `.p2p/project/`.
`p2p next` is advisory only: it reads stored next actions when available and falls back to conservative project-state checks, but it must not modify project state or decide on behalf of the owner.
`p2p assess refresh` is deterministic readiness analysis. It may report completion score, confidence, gaps, and suggested commands, but the MVP maturity score remains `not_assessed` until project-domain rubrics are explicitly defined and accepted.
`p2p assess maturity refresh` is project definition maturity, not implementation completeness. It checks whether enabled rubric topics are covered by P2P proposals, decisions, and Change Sets. Use `p2p project rubrics show` to inspect the domain checklist.

## When To Create A Proposal

Create or update a proposal when the conversation introduces:

- a new feature or product direction;
- an architectural decision;
- a process or governance change;
- a research topic;
- a substantial implementation plan;
- a meaningful risk, alternative, or trade-off.

Prefer updating an existing proposal when the new discussion clearly belongs to it. If the new idea may overlap existing work, use intake first.

## Intake Before New Proposals

Use intake for raw ideas, observations, or potential overlaps:

```bash
p2p intake prompt "Raw idea or observation"
p2p intake status
```

As Codex, if you can see the generated prompt, you may produce the intake artifacts directly:

```text
.p2p/intake/INTAKE-XXX/
  recommendation.md
  related-proposals.yml
  suggested-actions.yml
```

Intake is advisory. It can recommend `create_proposal`, `add_contribution`, `open_choice`, `record_conflict`, `defer`, or `duplicate`, but it must not decide proposal outcomes.

To apply intake recommendations, use the controlled apply workflow. Do not apply intake output directly from chat:

```bash
p2p intake apply plan INTAKE-XXX
p2p intake apply show INTAKE-XXX
p2p intake apply run INTAKE-XXX --action APPLY-XXX
```

`add_contribution` can be applied explicitly. `open_choice` requires at least two explicit `--option` values:

```bash
p2p intake apply run INTAKE-XXX --action APPLY-XXX \
  --option "Keep current direction" \
  --option "Explore intake alternative"
```

Governance outcomes such as accept, reject, and defer are preview-only in intake apply. They still require explicit proposal decision commands from the owner.

## Recommended Workflow

For a new topic:

```bash
p2p proposal create "Title" \
  --problem "Problem statement" \
  --context "Context" \
  --goal "Goal" \
  --proposal "Proposed direction" \
  --acceptance "Acceptance criterion"

p2p contribution add PROP-XXX "Contribution text" --type objective --relevance high
p2p explore prompt PROP-XXX
```

Then conduct the conversation. Ask focused questions, identify missing decisions, and produce artifacts that can be imported.

Prompt-only workflow:

```bash
p2p explore import PROP-XXX exploration-output.md
p2p explore status PROP-XXX

p2p clarify prompt PROP-XXX
p2p clarify import PROP-XXX clarification-output.md

p2p synthesize prompt PROP-XXX
p2p synthesize import PROP-XXX proposal-output.md

p2p proposal accept PROP-XXX --reason "Reason"

p2p plan prompt PROP-XXX
p2p plan import PROP-XXX plan-output.md

p2p tasks prompt PROP-XXX
p2p tasks import PROP-XXX tasks-output.yml
```

Use shortcut proposal decision commands when possible:

```bash
p2p proposal accept PROP-XXX --reason "Reason"
p2p proposal reject PROP-XXX --reason "Reason"
p2p proposal defer PROP-XXX --reason "Reason"
```

Use `p2p decision record` only when a non-shortcut outcome is needed, such as `accepted_with_changes`, `split`, `merged_into_other`, or `superseded`.

## Choices

When alternatives conflict or a decision has multiple options, create a choice:

```bash
p2p choice create \
  --title "Initial AI Integration Strategy" \
  --option "Prompt-only first" \
  --option "Direct integration now" \
  --option "Prompt-only first, adapter later" \
  --related PROP-XXX \
  --source INTAKE-XXX

p2p choice list
p2p choice status
p2p choice discover
p2p choice show CHOICE-XXX
p2p choice decide CHOICE-XXX --option C --reason "Reason"
```

Do not hide rejected alternatives in chat. Preserve them as choices, related proposals, conflicts, or decision rationale.

Use choice discovery before treating registry-only or proposal-local vote choices as project-level blockers:

```bash
p2p choice discover
```

Discovery is advisory and must not decide or modify state. When the owner explicitly decides that an unresolved project choice blocks a proposal or Change Set, record the formal blocker:

```bash
p2p choice block CHOICE-XXX --change CHANGE-XXX --reason "Reason"
p2p choice block CHOICE-XXX --proposal PROP-XXX --reason "Reason"
p2p choice unblock CHOICE-XXX --change CHANGE-XXX
```

Keep the distinction clear:

```text
related = informational connection
discovery finding = advisory candidate
block = explicit owner-controlled blocker in links.yml
```

## Change Sets

Do not implement accepted project intent directly from a proposal. Use a Change Set:

```bash
p2p change create --from PROP-XXX --title "Operational title"
p2p change set-status CHANGE-XXX planned
p2p change set-status CHANGE-XXX implementation_ready
p2p change tasks CHANGE-XXX
```

Interpret Change Set target fields precisely:

```text
execution_domains = type of work, such as software, documentation, governance, research, operations, commercial, or mixed
implementation_targets = where work is implemented, such as local_cli, docs, p2p_governance, or project_metadata
spec_targets = normalized P2P specification outputs to produce before export, such as p2p_spec
export_targets = downstream formats/tools, such as openspec, speckit, markdown, or task_board
```

Do not treat `p2p_spec` as generated code. It is the P2P-native normalized spec layer that downstream exporters consume. OpenSpec and Spec Kit are export targets, not the internal source of truth.

For software Change Sets that need implementation or downstream export, generate a P2P-native software spec before using OpenSpec, Spec Kit, or code generators:

```bash
p2p spec refresh --change CHANGE-XXX
p2p spec status
p2p spec show CHANGE-XXX
```

Use the optional prompt/import refinement workflow when deterministic source data is too sparse or needs human/AI normalization:

```bash
p2p spec prompt --change CHANGE-XXX
p2p spec import CHANGE-XXX spec-output/
```

Spec import must validate the required artifact set and YAML top-level keys. Do not export raw proposal folders directly to downstream code-generation tools.

When a refined P2P-native software spec is ready for downstream tools, export from `.p2p/outputs/software-spec/CHANGE-XXX/` instead of reading proposal folders:

```bash
p2p spec export --change CHANGE-XXX --target generic
p2p spec export --change CHANGE-XXX --target openspec
p2p spec export --change CHANGE-XXX --target speckit
p2p spec export-status
p2p spec export-show CHANGE-XXX --target speckit
p2p spec export-validate CHANGE-XXX --target speckit
```

The exporter MVP supports `generic`, `openspec`, and `speckit`. The Spec Kit mapping is conservative: it writes a feature directory with `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, and `contracts/README.md`, but it does not invoke Spec Kit, create branches, or decide unresolved implementation details. Resolve `NEEDS CLARIFICATION` markers through P2P governance before implementation.
Before handing an export bundle to downstream tooling, validate it with `p2p spec export-validate`. Validation is read-only and checks the export directory, manifest coherence, and target-specific required files.

## Managed Work And Invisible Git

P2P Work is the user-facing abstraction for future managed Git operations. Users should work with proposals, choices, Change Sets, exports, and Work items; Git branches, commits, PRs, and merges remain internal adapter details unless verbose/debug inspection is explicitly needed.

Use this routing:

```text
discussion, clarification, concern -> proposal contribution/comment
incompatible alternatives -> choice or alternative proposal
accepted operational work -> Change Set
validated downstream handoff -> Work manifest
owner-approved integration -> future managed submit/accept workflow
```

The managed Git path is incremental:

```text
Level 0: advisory only
Level 1: handoff plan / Work manifest
Level 2: managed branch
Level 3: managed commit
Level 4: managed review
Level 4.5: remote handoff
Level 4.6: optional external review request
Level 5: owner-controlled merge
Level 5.5: cleanup
```

The current safe level is Level 5.5:

```bash
p2p project remote show
p2p project remote configure --mode local
p2p project remote configure --mode remote --provider generic --remote origin --url git@example.com:owner/repo.git
p2p work status
p2p work plan --change CHANGE-XXX --target speckit
p2p work retire WORK-001 --reason "Obsolete planned handoff"
p2p work branch WORK-001
p2p work submit WORK-001
p2p work review WORK-001
p2p work publish WORK-001
p2p work request-review WORK-001
p2p work accept WORK-001
p2p work finalize WORK-001
p2p work cleanup WORK-001
p2p work scan
p2p work list
p2p work show WORK-001
```

`p2p work plan` requires a validated export bundle and writes `.p2p/work/WORK-XXX/manifest.yml`. It does not create Git branches, commits, PRs, or merges. Future branch visibility should read P2P-managed work manifests from `p2p/work/*` branches through the Git adapter without requiring checkout.
`p2p work status` is the read-only operational summary. Use it before choosing the next lifecycle command. It reports status, change, target, branch, remote/base metadata, and the next suggested command. It must not mutate project files or Git state.
`p2p work scan` is the first branch-visibility step: it reads local `p2p/work/*` branches without checkout and writes `.p2p/registries/work.yml`. It is read-only with respect to Git and must not fetch remote branches, create branches, commit, submit, or merge.
`p2p work retire WORK-XXX --reason "..."` is the metadata-only retirement step for obsolete planned Work manifests. It requires Work status `planned`, records retirement metadata, updates status to `retired`, and must not create/delete branches, commit, push, merge, or remove generated exports.
`p2p work branch WORK-XXX` is the first managed-write step. It creates and checks out the P2P-managed branch declared in the Work manifest, updates that manifest to `branched`, and keeps commit, submit, and merge disabled. It requires a clean Git worktree, a non-detached base branch, and an unused branch name. It must not be used to decide between proposals by itself; create branches only for accepted Change Sets or owner-authorized spikes.
`p2p work submit WORK-XXX` is the local commit step. It requires the current branch to match the Work manifest branch, requires Work status `branched`, refuses submissions that only contain Work manifest bookkeeping, updates the manifest to `submitted`, and creates one local commit. It must not push, open PRs, submit reviews, or merge; those belong to later owner-controlled levels.
`p2p work review WORK-XXX` is the local review-request step. It requires Work status `submitted`, requires the current branch to match the Work manifest branch, requires a clean worktree, records the commit to review, updates the manifest to `review_requested`, and creates one local metadata commit. It must not push, open PRs, or merge.
`p2p work publish WORK-XXX` is the remote handoff step. It requires Work status `review_requested`, requires the current branch to match the Work manifest branch, requires a clean worktree and a configured Git remote, updates the manifest to `published`, creates one local publish metadata commit, and pushes the managed branch to the remote. It must not open PRs or merge.
`p2p project remote configure/show` records whether the P2P project is local-only or remote-backed and which provider profile applies (`generic`, `github`, or `gitlab`). This is project metadata only: it must not create remote repositories, authenticate providers, open PRs/MRs, or push.
`p2p work request-review WORK-XXX` is the optional external review handoff step. It requires Work status `published`, requires the current branch to match the Work manifest branch, requires a clean worktree, records `external_review` metadata, and prints provider-specific advisory guidance. It must not create a GitHub PR, GitLab MR, merge, accept, finalize, or cleanup.
`p2p work accept WORK-XXX` is the owner-controlled local merge step. It requires Work status `published` on the managed branch, requires the current branch to be the manifest base branch, requires a clean worktree, merges the managed Work branch locally, updates the manifest to `accepted`, and creates one local merge commit. It must not push the base branch or delete Work branches.
If `p2p work accept` reports merge conflicts, do not continue with publish/finalize/cleanup. Resolve the listed files manually, then run `p2p work accept --continue WORK-XXX`; or run `p2p work accept --abort WORK-XXX` to abort the merge and return the Work item to `published`.
`p2p work finalize WORK-XXX` is the post-accept publication step. It requires Work status `accepted`, requires the current branch to be the manifest base branch, requires a clean worktree and configured remote, updates the manifest to `finalized`, creates one local finalize metadata commit, and pushes the base branch. It must not delete local or remote Work branches.
`p2p work cleanup WORK-XXX` is the post-finalize branch cleanup step. It requires Work status `finalized`, requires the current branch to be the manifest base branch, requires a clean worktree and configured remote, deletes the local managed Work branch, updates the manifest to `cleaned`, creates one local cleanup metadata commit, and pushes the base branch. It deletes the remote managed Work branch only with `--remote`.

Future managed Git levels must stay separate:

```text
Level 4.5: remote handoff / push branch
Level 4.6: optional external review request
Future Level 4.7: provider adapter can create PR/MR only after explicit accepted proposal
Level 5: owner-controlled accept / merge
Level 5.5: cleanup
```

After implementation and verification:

```bash
p2p change set-status CHANGE-XXX in_progress
p2p change set-status CHANGE-XXX in_review
p2p change set-status CHANGE-XXX completed
p2p registry refresh
```

## Exploration Behavior

Use exploration before synthesis and whenever new information changes the shape of the problem.

Exploration should surface:

- hidden decisions;
- alternatives;
- assumptions;
- risks;
- open questions;
- suggested scope;
- execution domains.

Expected artifacts:

```text
exploration.md
findings.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

## Import Discipline

When you generate content as Codex, save it to an appropriate temporary or proposal-local file and import it with the CLI instead of only describing it.

Examples:

```bash
p2p explore import PROP-XXX exploration-output.md
p2p synthesize import PROP-XXX proposal-output.md
p2p tasks import PROP-XXX tasks-output.yml
```

For `tasks import`, produce valid YAML with a top-level `tasks` list.

For intake output, write the expected files under `.p2p/intake/INTAKE-XXX/` when operating inside Codex, or use:

```bash
p2p intake import INTAKE-XXX output-dir/
```

## Do Not

- Do not treat AI output as a final decision.
- Do not skip human decision recording for accepted/rejected proposals.
- Do not accept, reject, defer, merge, or supersede proposals from intake alone.
- Do not create plans or tasks before exploration/synthesis unless the user explicitly asks for a shortcut.
- Do not use P2P artifacts as decoration; keep them actionable and versioned.
- Do not introduce web app, MCP, or direct AI adapters unless the active proposal covers that work.

## Useful Commands

```bash
p2p check
p2p status
p2p registry refresh
p2p proposal list
p2p proposal show PROP-XXX
p2p proposal create "Title"
p2p proposal update PROP-XXX --problem "..." --goal "..."
p2p proposal accept PROP-XXX --reason "..."
p2p proposal reject PROP-XXX --reason "..."
p2p proposal defer PROP-XXX --reason "..."
p2p contribution add PROP-XXX "Text" --type suggestion --relevance medium
p2p intake prompt "Raw idea"
p2p intake status
p2p explore prompt PROP-XXX
p2p explore status PROP-XXX
p2p digest prompt PROP-XXX
p2p clarify prompt PROP-XXX
p2p synthesize prompt PROP-XXX
p2p choice create --title "Title" --option "A" --option "B"
p2p choice list
p2p choice decide CHOICE-XXX --option A --reason "..."
p2p change create --from PROP-XXX
p2p change status
p2p plan prompt PROP-XXX
p2p tasks prompt PROP-XXX
```

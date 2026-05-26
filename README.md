# P2P Engine

P2P Engine is a Proposal-to-Plan Engine: a Git-native workflow for turning collaborative discussion into proposals, decisions, plans, tasks, and actions.

## Bootstrap Status

The project is currently bootstrapped manually through `.p2p/`.

The first implementation milestone is the CLI foundation:

```bash
p2p init
p2p check
p2p proposal create "CLI Foundation"
p2p contribution add PROP-001
p2p proposal contribution add PROP-001 "Add a contribution"
p2p explore prompt PROP-001
p2p digest prompt PROP-001
```

The first version is prompt-only. It prepares structured artifacts and prompts, but does not call AI providers directly.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
p2p --help
```

## Enriched Proposals

Proposal creation can include structured sections immediately:

```bash
p2p proposal create "Prompt generator hardening" \
  --problem "Generated prompts inherit too many placeholder sections." \
  --context "PROP-002 is the first proposal created through the CLI itself." \
  --goal "Make prompts useful even when proposal.md is incomplete." \
  --goal "Include governance context in generated prompts." \
  --proposal "Add structured proposal metadata and harden prompt rendering." \
  --acceptance "Digest prompts call out missing information explicitly."
```

Existing proposals can be enriched later:

```bash
p2p proposal update PROP-002 \
  --problem "Generated prompts inherit too many placeholder sections." \
  --goal "Make prompt output more useful and testable."
```

Inspect proposals with stable output:

```bash
p2p proposal list
p2p proposal list --status accepted
p2p proposal show PROP-001
```

Proposal decisions have readable shortcut commands:

```bash
p2p proposal accept PROP-002 --reason "Ready for implementation."
p2p proposal reject PROP-003 --reason "Out of scope for the MVP."
p2p proposal defer PROP-006 --reason "Needs direct AI adapter design first."
```

These commands write the same `decision.md` artifact as `p2p decision record`.

## Exploration Phase

Exploration interrogates a rough idea before proposal synthesis. It surfaces hidden decisions, alternatives, assumptions, risks, open questions, and suggested scope.

```bash
p2p explore prompt PROP-002

# Pass the prompt to Codex, Claude, ChatGPT, or a local model.
# Then import the resulting file or artifact directory.

p2p explore import PROP-002 exploration-output.md
p2p explore status PROP-002
```

Exploration artifacts live in the proposal directory:

```text
exploration.md
findings.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

## Prompt-Only Imports

The MVP workflow is prompt-only: P2P Engine generates prompts, an external AI or agent produces output, and the CLI imports the result into versioned artifacts.

```bash
p2p clarify prompt PROP-002
p2p clarify import PROP-002 clarification-output.md

p2p synthesize prompt PROP-002
p2p synthesize import PROP-002 proposal-output.md

p2p plan prompt PROP-002
p2p plan import PROP-002 plan-output.md

p2p tasks prompt PROP-002
p2p tasks import PROP-002 tasks-output.yml
```

## Governance MVP

Governance is file-based and audit-only in the MVP. The CLI records governance artifacts, SWOT prompts, votes, and precedents, while real permission enforcement stays with Git and the hosting platform.

```bash
p2p governance init --mode owner_decides
p2p governance status

p2p swot prompt PROP-008

p2p vote record PROP-008 \
  --choice "ALT-A" \
  --reason "Keeps MVP governance simple." \
  --voter "local" \
  --role "owner"

p2p vote status PROP-008

p2p precedent record PROP-008 \
  --title "MVP governance is audit-only" \
  --reason "Permission enforcement is delegated to Git hosting until collaboration needs are clearer."
```

## Project State

Accepted proposals can be rationalized into `.p2p/project/`. This directory is derived but versioned: proposal branches may contain preview changes, while `main` contains the official accepted project state.

```bash
p2p project refresh
p2p project status
p2p project show overview
p2p project show cli-foundation
```

The first refresh MVP is deterministic and does not call AI. It generates:

```text
.p2p/project/
  overview.md
  problem.md
  scope.md
  project-swot.md
  features/
  decisions-map.yml
  conflicts.yml
```

## Impact And Conflict Memory

Impact analysis explains what a proposal touches before it is accepted. Conflict memory keeps track of overlapping or mutually exclusive proposals so rejected paths are not forgotten.

```bash
p2p impact prompt PROP-012

# After an AI or human produces impact artifacts:
p2p impact import PROP-012 impact-output/

p2p conflict record PROP-010 PROP-012 \
  --type overlaps \
  --reason "Both change project-state semantics."

p2p conflict status
```

Impact import accepts:

```text
impact-map.yml
related-proposals.yml
conflict-analysis.yml
```

## Change Sets

Change Sets are metadata-only in the MVP. They turn accepted project intent into operational packages without creating Git commits, branches, tags, or merges.

```bash
p2p change create --from PROP-013
p2p change status
p2p change policy CHANGE-001
p2p change show CHANGE-001
p2p change set-status CHANGE-001 planned
p2p change tasks CHANGE-001
```

The first Change Set structure is:

```text
.p2p/changes/
  CHANGE-001-example/
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

## Project Registries

Registries are generated indexes over P2P source artifacts. They make the project easier to inspect for humans, agents, future intake analysis, conflict checks, and exporters.

```bash
p2p registry refresh
p2p registry status
p2p registry show proposals
p2p registry show changes
```

Registry files are derived and may be overwritten by refresh. The source of truth remains the proposal, decision, choice, change, governance, and project artifacts under `.p2p/`.

```text
.p2p/registries/
  proposals.yml
  decisions.yml
  changes.yml
  choices.yml
  relations.yml
  artifacts.yml
```

## Proposal Intake

Intake analyzes a raw idea or observation against project memory before deciding whether to create a new proposal, add a contribution, open a choice, or record a conflict.

```bash
p2p registry refresh

p2p intake prompt "La CLI dovrebbe integrare subito Codex"

# Pass `.p2p/intake/INTAKE-001/intake.prompt.md` to an AI or agent.
# Then import the resulting file or artifact directory.

p2p intake import INTAKE-001 intake-output/
p2p intake status
```

Intake artifacts live under:

```text
.p2p/intake/
  INTAKE-001/
    input.md
    context.md
    intake.prompt.md
    recommendation.md
    related-proposals.yml
    suggested-actions.yml
```

Intake is advisory. It can suggest actions, but it does not accept, reject, defer, merge, or supersede proposals. Governance decisions still go through P2P decision commands.

## Choices

Choices record explicit project alternatives that need a decision.

```bash
p2p choice create \
  --title "Initial AI Integration Strategy" \
  --option "Prompt-only first" \
  --option "Direct Codex integration now" \
  --option "Prompt-only first, Codex adapter later" \
  --related PROP-004 \
  --source INTAKE-001

p2p choice list

p2p choice decide CHOICE-001 \
  --option C \
  --reason "Preserve the prompt-only MVP while planning a later Codex adapter."
```

Choice artifacts live under:

```text
.p2p/choices/
  CHOICE-001-example/
    choice.md
    options.yml
    decision.md
    links.yml
```

## Codex Skill

This repository includes a local Codex skill for using P2P Engine as a working method:

```text
.codex/skills/p2p-engine/SKILL.md
```

The skill instructs Codex to use the CLI and `.p2p/` artifacts as the source of truth instead of leaving proposal work only in chat.

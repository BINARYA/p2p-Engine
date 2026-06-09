# Suggested Scope - PROP-085

## MVP Scope

- Define the vertical pack schema for pure data packs.
- Ship `base_project` as the required common foundation, including its default
  cross-domain structure.
- Implement a loader and validator for internal and project-local vertical packs.
- Add one complete demonstration vertical.
- Extend project readiness review through `p2p project readiness review`.
- Add CLI/MCP read/write surfaces for listing, showing, validating, proposing,
  and adding project-local vertical packs.
- Add project-level traceability between vertical sections/capisaldi and
  proposals.
- Update agent/project skills so the agent treats missing initialization,
  capisaldi, and initial project questions as priority context work.
- Reuse existing project rubrics and maturity/readiness artifacts.
- Preserve backward compatibility for projects without vertical packs.

## Required MVP Pack Fields

- `vertical.yml` with id, name, version, description, and base/extends.
- Project sections/capitoli/capisaldi.
- Minimal completeness/readiness rubrics.
- Initial blocking questions.
- Expected or suggested artifacts.

## `base_project` Default Structure

`base_project` is not a domain vertical. It is the required cross-domain
foundation that every project starts from and every vertical extends.

Required default sections:

- vision: why the project exists and what change it should create.
- objective/outcome: concrete results the project must achieve.
- owner and stakeholders: decision maker, contributors, affected parties.
- target/users/beneficiaries: who receives value or impact.
- scope and non-goals: boundaries and explicit exclusions.
- constraints: budget, time, compliance, resources, technology, context.
- assumptions: beliefs that must be true for the project to work.
- risks: failure modes and mitigations.
- decisions and open questions: unresolved owner choices.
- milestones and next actions: staged path from definition to execution.
- definition of done/readiness criteria: how the project becomes actionable.
- expected artifacts: documents, specs, prototypes, reports, plans, or outputs.
- maturity/readiness status: current completeness and next strengthening step.

## Custom Vertical Candidate Procedure

When no suitable vertical exists, the agent should:

1. start from `base_project`;
2. infer a candidate vertical id and name;
3. propose vertical-specific sections/capisaldi;
4. propose minimal readiness rubrics;
5. propose initial blocking questions;
6. propose expected artifacts;
7. explain what came from `base_project` and what is vertical-specific;
8. ask the owner to confirm or modify the candidate;
9. save it as a project-local custom vertical only after confirmation;
10. use it for `p2p project readiness review`.

## Proposed CLI Surface

The current system has project domains and rubrics, not pluggable vertical packs.
This proposal should add a dedicated project vertical surface.

Expected MVP commands:

- `p2p project vertical list`
- `p2p project vertical show <vertical-id>`
- `p2p project vertical validate <path-or-id>`
- `p2p project vertical propose "<project idea>"`
- `p2p project vertical add <path>`
- `p2p project readiness review`

The commands should prefer project-local custom verticals, then internal defaults,
then future registry sources once implemented.

## Proposal-To-Vertical Traceability

The project should not only know which vertical is active. It should also know
which parts of the vertical are currently covered by proposals.

Expected behavior:

- A proposal can declare or be assessed against one or more vertical
  sections/capisaldi.
- `p2p project readiness review` should summarize the active vertical skeleton.
- For each vertical section, the review should list relevant proposals,
  accepted decisions, draft proposals, missing coverage, risks, and unresolved
  questions.
- The review should identify vertical sections with no proposal coverage.
- The review should identify proposals that affect the project but are not
  mapped to any vertical section.
- The visible project output should be able to include a vertical coverage
  summary.

Suggested traceability fields:

```yaml
vertical_coverage:
  vertical_id: social_impact_program_design
  sections:
    - id: theory_of_change
      relevance: direct
      rationale: Defines how initiatives create measurable impact.
    - id: measurement_and_reporting
      relevance: direct
      rationale: Adds outcome metrics and reporting requirements.
```

Suggested project-level summary:

```yaml
vertical_summary:
  vertical_id: social_impact_program_design
  sections:
    - id: social_impact_vision
      status: covered
      proposals: [PROP-101]
    - id: theory_of_change
      status: partial
      proposals: [PROP-102]
      gaps: [missing_assumptions]
    - id: measurement_and_reporting
      status: missing
      proposals: []
```

## Example Custom Vertical Candidate: `packaging_or_physical_product_design`

Example project: "progettare la scatola perfetta".

Purpose:

- Guide the design of a box or packaging solution from concept to testable and
  manufacturable specification.

Candidate sections:

- contained product and use case;
- meaning of "perfect" for the project;
- user and unboxing experience;
- physical structure and dimensions;
- materials and sustainability;
- protection, transport, and storage;
- brand/visual communication;
- production process and suppliers;
- cost targets;
- prototype plan;
- resistance/usability tests;
- final packaging specification.

Candidate blocking questions:

- What must the box contain?
- Does "perfect" mean beautiful, resistant, cheap, sustainable, memorable, or a
  weighted combination?
- Is the main context shipping, retail shelf, gift, luxury, e-commerce, or reuse?
- Which cost, material, size, logistics, and production constraints are fixed?

Candidate artifacts:

- packaging brief;
- requirement matrix;
- material shortlist;
- dieline/structural sketch;
- prototype plan;
- test checklist;
- supplier/manufacturing brief.

## Example Custom Vertical Candidate: `social_impact_program_design`

Example project: "progettare attività volte a migliorare l'impatto sociale di
una banca".

Purpose:

- Guide a bank or financial institution in designing social impact initiatives
  that are measurable, governed, credible, and connected to stakeholder needs.

Candidate sections:

- social impact vision;
- theory of change;
- beneficiary communities;
- impact areas;
- financial inclusion;
- financial education;
- partnerships and territory;
- ESG/social impact alignment;
- governance and accountability;
- budget and sustainability;
- measurement and reporting;
- responsible communication;
- program roadmap.

Candidate blocking questions:

- Which community or population should benefit?
- Is the desired impact about financial inclusion, education, credit access,
  territory, environment, work, or another area?
- Should the bank fund external initiatives, change internal products/processes,
  or both?
- How will real impact be measured and how will social-washing be avoided?

Candidate artifacts:

- social impact strategy brief;
- stakeholder map;
- theory of change;
- initiative portfolio;
- outcome metric framework;
- partner brief;
- governance model;
- impact reporting plan.

## Optional MVP Pack Fields

- Examples.
- Profiles.
- Compatible modules.
- Rich output templates.

## Out Of Scope For First Slice

- Remote registry implementation.
- Executable plugin code for verticals.
- A large catalog of verticals.
- The full five-vertical MVP set.
- Publishing project-local custom verticals to a shared registry.
- Replacing project rubrics or project maturity with a parallel system.

## Follow-Up Scope

- Design the REST registry API for listing packs and fetching pack details.
- Add the five-vertical MVP set once the pack model is proven.
- Add richer profiles/modules/templates after the minimal pack schema is stable.

## Vertical Catalog Roadmap

The first implementation slice remains intentionally smaller than the later
catalog MVP. It proves the model with `base_project`, one complete demonstration
vertical, loader/validator behavior, project-local overrides, agent guidance, and
`p2p project readiness review`.

After that first slice, the recommended catalog MVP is:

- `base_project`
- `software_product`
- `ai_agent_or_automation`
- `startup_or_business`
- `research_report`
- `board_game_design`

The recommended V1 default catalog is:

- `base_project`
- `software_product`
- `ai_agent_or_automation`
- `startup_or_business`
- `research_report`
- `course_or_training_program`
- `marketing_or_launch_campaign`
- `physical_product`
- `event_or_community`
- `board_game_design`

Domains such as podcast, newsletter, book, video game, documentary, e-commerce,
grant proposal, nonprofit, hiring process, and open source community should move
to registry/project-local packs rather than the initial core catalog.

## Vertical Admission Criteria

A vertical should enter the default catalog only if it:

1. has a clear project structure;
2. produces concrete artifacts;
3. benefits from interview mode;
4. has verifiable maturity/readiness criteria;
5. is common enough to justify maintenance;
6. does not require risky regulated expertise as its core value;
7. reuses cross-domain sections or modules;
8. is maintainable by the project team;
9. demonstrates a distinct capability of the engine;
10. can include high-quality examples.

## Vertical Profiles And Modules

Profiles specialize a vertical without creating another vertical. Examples:

- `board_game_design`: `early_concept`, `playable_prototype`,
  `publisher_pitch`, `crowdfunding_ready`, `educational_game`,
  `print_and_play`.
- `software_product`: `idea_to_mvp`, `internal_tool`, `saas_product`,
  `open_source_tool`, `enterprise_integration`.
- `research_report`: `quick_brief`, `deep_research`,
  `competitive_benchmark`, `decision_memo`, `literature_review`.
- `course_or_training_program`: `short_workshop`, `online_course`,
  `corporate_training`, `bootcamp`, `self_paced_program`.

Modules add cross-cutting concerns and can attach to multiple verticals.
Recommended module candidates:

- `go_to_market`
- `risk_management`
- `roadmap`
- `stakeholder_alignment`
- `accessibility`
- `security_privacy`
- `production_feasibility`
- `crowdfunding`
- `education`
- `community_building`
- `monetization`

## Suggested Package Layout

Internal default resources should be shaped so they can later be backed by a
registry without changing project-local semantics:

```text
p2p/verticals/
  base_project/
    vertical.yml
    sections/
    rubrics.yml
    artifacts/
  software_product/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/
  ai_agent_or_automation/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/
  startup_or_business/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/
  research_report/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/
  board_game_design/
    vertical.yml
    profiles/
    sections/
    rubrics.yml
    artifacts/
    examples/

p2p/modules/
  go_to_market/
  crowdfunding/
  production_feasibility/
  accessibility/
  security_privacy/
  compliance/
  education/
  community_building/
  monetization/
```

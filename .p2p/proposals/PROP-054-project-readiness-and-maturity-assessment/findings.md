findings:
  - id: F001
    type: hidden_decision
    title: Score semantics must be explicit
    impact: high
    detail: The proposal needs to decide whether readiness is represented as a percentage, status band, maturity level, factor list, or a combination. A single opaque number would conflict with the non-goal.
    related_to:
      - PROP-054
  - id: F002
    type: architectural_implication
    title: Assessment should reuse validation, registry and next-action signals
    impact: high
    detail: The feature overlaps with p2p validate, registries, operational briefs and p2p next. It should compose existing state readers instead of creating a second validation system.
    related_to:
      - PROP-016
      - PROP-022
      - PROP-023
      - PROP-053
  - id: F003
    type: scope_boundary
    title: Deterministic readiness and domain maturity are different products
    impact: high
    detail: Deterministic readiness can ship first in Core/CLI. Domain maturity requires rubrics, evidence and optional review workflows, and should not block the deterministic MVP.
    related_to:
      - PROP-054
  - id: F004
    type: governance_constraint
    title: Assessment must not become an automatic decision gate
    impact: high
    detail: The assessment can recommend next actions and expose gaps, but owner-controlled governance must remain responsible for accept, reject, defer, merge and work lifecycle decisions.
    related_to:
      - PROP-008
      - PROP-054
  - id: F005
    type: data_model
    title: Assessment artifacts need a stable project-level location
    impact: medium
    detail: The feature needs a deterministic output path such as .p2p/project/assessment.yml or .p2p/assessments/current.yml, plus optional rubric artifacts for project-type criteria.
    related_to:
      - PROP-010
      - PROP-011
  - id: F006
    type: mcp_boundary
    title: MCP exposure should remain advisory and low-risk
    impact: medium
    detail: Initial MCP support should expose assessment status or create prompt artifacts only. It should not mutate governance outcomes or block Work items.
    related_to:
      - PROP-044
      - PROP-046
      - PROP-052
  - id: F007
    type: missing_requirement
    title: The MVP needs factor weights or rule precedence
    impact: medium
    detail: The proposal lists possible signals but does not yet define how severe findings, stale registries, open choices, draft proposals and active work affect readiness.
    related_to:
      - PROP-054
  - id: F008
    type: execution_domain
    title: Implementation spans software and governance metadata
    impact: medium
    detail: The first Change Set would likely touch CLI commands, Core assessment logic, storage paths, tests, registries or project metadata, and MCP read-only exposure later.
    related_to:
      - PROP-054

findings:
  - id: F001
    type: current_capability
    title: Existing test tiers are already structured
    impact: high
    related_to:
      - docs/TESTING.md
      - scripts/test-focused.sh
      - scripts/test-public.sh
      - scripts/test-smoke.sh
      - scripts/test-full.sh
    evidence: "The repository already has marker-based pytest tiers and validation scripts; PROP-060 should not replace this structure."
  - id: F002
    type: gap
    title: Coverage tooling is not currently available
    impact: medium
    related_to:
      - pyproject.toml
      - tests
    evidence: "A coverage option such as --cov is not accepted by the current pytest setup without adding a development coverage integration."
  - id: F003
    type: scope_boundary
    title: Coverage is not test impact routing
    impact: high
    related_to:
      - PROP-098
    evidence: "Coverage can show which code selected tests exercised, but it cannot deterministically decide which tests are required for a future change."
  - id: F004
    type: scope_boundary
    title: Coverage is not user project evidence completeness
    impact: high
    related_to:
      - PROP-060
    evidence: "This proposal is internal to P2P Engine software maintenance and does not assess whether a user project design has enough evidence, risks, acceptance criteria, or domain validation."
  - id: F005
    type: implementation_constraint
    title: First slice should avoid blocking gates
    impact: medium
    related_to:
      - pyproject.toml
      - docs/TESTING.md
    evidence: "No baseline coverage exists yet; an immediate fail-under threshold would be premature and could incentivize superficial tests."

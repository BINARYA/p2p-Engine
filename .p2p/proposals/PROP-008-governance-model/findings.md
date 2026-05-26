findings:
  - id: F001
    type: governance_model
    title: Owner decides as bootstrap default
    impact: high
    summary: >
      The initial project needs a fast and explicit decision model. owner_decides
      should be the default during bootstrap.
    related_to:
      - governance.yml
      - bootstrap

  - id: F002
    type: governance_model
    title: Exclusive vote for mutually exclusive alternatives
    impact: high
    summary: >
      P2P must support decisions where only one alternative can win, and the
      result must become a decision precedent.
    related_to:
      - votes.yml
      - decision-precedents.yml

  - id: F003
    type: ai_support
    title: SWOT as decision support
    impact: medium
    summary: >
      AI can generate SWOT analysis for alternatives to help humans decide, but
      it must not become the decision maker.
    related_to:
      - swot-analysis.md

  - id: F004
    type: architecture_boundary
    title: Governance is not authorization
    impact: high
    summary: >
      MVP governance records rules and decisions, while real permission
      enforcement remains delegated to Git hosting or future web backend.
    related_to:
      - git
      - permissions

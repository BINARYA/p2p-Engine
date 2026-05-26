findings:
  - id: F001
    type: workflow_gap
    title: Missing proposal intake phase
    impact: high
    summary: >
      P2P can create and explore proposals, but it does not yet decide whether a
      rough idea belongs to an existing proposal or should become a new one.
    related_to:
      - proposal_lifecycle
      - governance

  - id: F002
    type: hidden_decision
    title: Command namespace for triage
    impact: medium
    summary: >
      The project must decide whether triage is a proposal subcommand
      (`p2p proposal triage`) or a top-level workflow (`p2p triage`).
    related_to:
      - cli_ux

  - id: F003
    type: architectural_principle
    title: File-based first, semantic search later
    impact: high
    summary: >
      The MVP should scan proposal artifacts and generate a prompt rather than
      adding embeddings or a database.
    related_to:
      - mvp_scope
      - storage

  - id: F004
    type: governance_rule
    title: Avoid duplicate proposal creation
    impact: high
    summary: >
      When overlap is high, the system should prefer adding a contribution or
      updating an existing proposal over creating a new proposal.
    related_to:
      - proposal_governance

findings:
  - id: F001
    type: conceptual_boundary
    title: "Proposal is not branch"
    impact: high
    summary: >
      A proposal is a decision unit stored in P2P artifacts. A Git branch is an
      optional workspace for isolation, review, or implementation.
  - id: F002
    type: missing_abstraction
    title: "Change Set is the operational unit"
    impact: high
    summary: >
      Accepted proposals should flow into change sets before implementation.
      Change sets can group multiple proposals and decisions into one operational
      package.
  - id: F003
    type: workflow_risk
    title: "Visible branch decisions create process variance"
    impact: high
    summary: >
      If users decide branch usage ad hoc, the workflow becomes inconsistent and
      too technical. Branch/commit/merge decisions should be managed internally
      by policy.
  - id: F004
    type: git_boundary
    title: "P2P memory must survive branch deletion"
    impact: high
    summary: >
      Proposal, decision, impact, conflict, and change-set history must live in
      .p2p artifacts, not only in Git branch history.
  - id: F005
    type: user_experience
    title: "Git should be internal by default"
    impact: high
    summary: >
      Users should operate with P2P concepts: proposal, choice, decision, change,
      and task. Git details should appear only in verbose/debug/doctor flows.
  - id: F006
    type: ai_instruction
    title: "AI agents should use P2P CLI instead of direct Git"
    impact: high
    summary: >
      Codex/Claude-style agents should call P2P commands and avoid manual Git
      branch/commit manipulation unless explicitly operating in debug or repair mode.

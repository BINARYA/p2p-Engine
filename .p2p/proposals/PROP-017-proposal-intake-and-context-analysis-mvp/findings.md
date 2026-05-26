findings:
  - id: F001
    type: missing_capability
    title: "Raw ideas lack context-aware intake"
    impact: high
    summary: "P2P can store proposals, but it does not yet help classify a new idea against project memory."

  - id: F002
    type: architecture
    title: "Registries make intake feasible"
    impact: high
    summary: "PROP-016 provides compact generated indexes that intake can use as context without scanning every artifact manually."

  - id: F003
    type: governance
    title: "Intake must recommend, not decide"
    impact: high
    summary: "Agents may suggest next actions, but accepted/rejected/deferred outcomes remain governed decisions."

  - id: F004
    type: collaboration
    title: "Multi-agent collaboration needs shared classification"
    impact: medium
    summary: "Different agents can participate coherently if all classify ideas through P2P artifacts."

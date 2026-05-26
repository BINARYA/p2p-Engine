findings:
  - id: F001
    type: impact_analysis
    title: "Proposal impact needs structured artifacts"
    impact: high
    summary: >
      P2P needs proposal-level impact-map.yml artifacts to describe affected
      features, commands, files, governance rules, outputs, dependencies, and risks.
  - id: F002
    type: conflict_memory
    title: "Conflicts must survive the decision"
    impact: high
    summary: >
      Mutually exclusive or competing proposals should be preserved in
      .p2p/project/conflicts.yml so future proposals can be checked against
      already decided alternatives.
  - id: F003
    type: human_governance
    title: "Detection is advisory, decision remains human"
    impact: medium
    summary: >
      The CLI and AI can detect overlaps and suggest conflicts, but should not
      automatically reject proposals in the MVP.

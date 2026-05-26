findings:
  - id: F001
    type: architectural_boundary
    title: "P2P proposal is not a software spec"
    impact: high
    summary: >
      A P2P proposal contains discussion, governance, alternatives, and decision
      context. It must be rationalized before it becomes an implementation-facing
      software specification.
  - id: F002
    type: output_model
    title: "Rationalized project state needs a dedicated directory"
    impact: high
    summary: >
      Derived artifacts should live under .p2p/project so they are clearly
      separated from source proposal artifacts while representing the official
      rationalized project state.
  - id: F003
    type: downstream_export
    title: "OpenSpec and Spec Kit consume normalized specs"
    impact: high
    summary: >
      Exporters should consume P2P-native software specs, not raw proposal folders.
  - id: F004
    type: workflow_trigger
    title: "Accepted proposals should refresh outputs"
    impact: medium
    summary: >
      The system should refresh output artifacts when decisions are accepted,
      starting with an explicit p2p project refresh command and later optional
      automatic refresh.
  - id: F005
    type: conflict_memory
    title: "Mutually exclusive proposals need persistent conflict memory"
    impact: high
    summary: >
      When proposals are alternatives, accepting one should mark the others as
      rejected, superseded, or not selected. The project layer should preserve
      the conflict group and final choice.

findings:
  - id: F001
    type: lifecycle
    title: "Change Set lifecycle is separate from proposal status"
    impact: high
    summary: >
      Proposals decide project intent. Change Sets track operational execution.
  - id: F002
    type: validation
    title: "Lifecycle transitions must be constrained"
    impact: high
    summary: >
      Invalid jumps such as proposed to completed should be rejected to preserve
      reliable execution tracking.
  - id: F003
    type: execution_tracking
    title: "Tasks and actions need inspection commands"
    impact: medium
    summary: >
      Users need to see Change Set tasks and checklist actions without opening
      YAML files manually.

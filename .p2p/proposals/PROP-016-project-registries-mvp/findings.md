findings:
  - id: F001
    type: derived_index
    title: "Registries should be derived, not primary"
    impact: high
    summary: >
      Registries should index source artifacts but never replace proposal,
      decision, change, or governance files as source of truth.
  - id: F002
    type: navigation
    title: "Project navigation needs compact indexes"
    impact: high
    summary: >
      As .p2p grows, commands and AI agents need compact registry files instead
      of scanning every artifact for every workflow.
  - id: F003
    type: ai_context
    title: "Registries improve AI context loading"
    impact: medium
    summary: >
      Prompt generation and future AI adapters can load registries first, then
      selectively open relevant artifacts.
  - id: F004
    type: exporter_support
    title: "Exporters need stable lookup inputs"
    impact: medium
    summary: >
      Markdown, OpenSpec, Spec Kit and task-board exporters should consume
      registry indexes plus selected source artifacts.

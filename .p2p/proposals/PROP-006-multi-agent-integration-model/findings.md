findings:
  - id: F001
    type: external_pattern
    title: Spec Kit integration registry
    impact: high
    source: https://github.github.com/spec-kit/reference/integrations.html
    summary: >
      Spec Kit models AI tools as integrations keyed by agent identifiers and
      exposes list/install/use/switch/upgrade/uninstall flows.
    related_to:
      - agent_profiles
      - cli_commands

  - id: F002
    type: external_pattern
    title: OpenSpec slash commands and skills
    impact: high
    source: https://github.com/Fission-AI/OpenSpec
    summary: >
      OpenSpec uses slash commands, skills, and refreshed agent instructions to
      align many AI coding assistants around one spec workflow.
    related_to:
      - skill_templates
      - command_files

  - id: F003
    type: hidden_decision
    title: Integration state model
    impact: high
    summary: >
      P2P Engine needs a local state file to track installed agent integrations,
      default agent, installed files, and template versions.
    related_to:
      - .p2p/agent-integrations.yml

  - id: F004
    type: architectural_principle
    title: Agents are adapters, not source of truth
    impact: high
    summary: >
      P2P must keep the CLI/core and .p2p artifacts authoritative while agent
      integrations only provide tool-specific entrypoints and behavior guidance.
    related_to:
      - governance
      - source_of_truth

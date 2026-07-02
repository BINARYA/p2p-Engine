findings:
  - id: F001
    type: architectural_boundary
    title: PROP-090 is a hardening layer for PROP-085, not a competing vertical system
    impact: high
    related_to:
      - PROP-085
  - id: F002
    type: compatibility_decision
    title: Keep the existing p2p project vertical namespace
    impact: high
    related_to:
      - PROP-085
  - id: F003
    type: compatibility_decision
    title: Keep .p2p/project/verticals as the project-local pack path
    impact: high
    related_to:
      - PROP-085
  - id: F004
    type: compatibility_decision
    title: Keep base_project canonical and omit generic_project from the first implementation
    impact: medium
    related_to:
      - PROP-085
  - id: F005
    type: hidden_decision
    title: definition.yml requires an official narrow writer in the first slice
    impact: high
    related_to:
      - PROP-086
      - PROP-089
  - id: F006
    type: deferred_scope
    title: Full next-action engine should follow definition-state stabilization
    impact: medium
    related_to:
      - PROP-079
      - PROP-081
      - PROP-089
  - id: F007
    type: security_boundary
    title: Vertical pack text is domain data, not agent instruction authority
    impact: high
    related_to:
      - PROP-085
  - id: F008
    type: migration_decision
    title: Existing projects require explicit lock repair or migration
    impact: high
    related_to:
      - PROP-085


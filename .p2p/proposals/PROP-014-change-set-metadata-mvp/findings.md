findings:
  - id: F001
    type: implementation_slice
    title: "Change Set MVP should be metadata-only"
    impact: high
    summary: >
      The first Change Set implementation should generate .p2p/changes metadata
      without mutating Git.
  - id: F002
    type: guardrail
    title: "Change Sets require accepted sources"
    impact: high
    summary: >
      Draft proposals must not create operational Change Sets. Accepted proposals
      or accepted decisions are required.
  - id: F003
    type: git_policy
    title: "Git policy is recorded, not executed"
    impact: high
    summary: >
      git-policy.yml records managed metadata-only behavior: no automatic
      commits, branches, tags, or merges.

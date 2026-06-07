# P2PWorkspace Governance Result Type Cleanup Requirements

## Goal

Remove duplicated governance-adjacent result dataclasses from
`storage.filesystem` when ownership already lives in extracted services.

## Requirements

- `P2PWorkspace` must import these service-owned result types:
  - `ProposalDetail` and `ProposalContributionList` from
    `services.proposals`;
  - `ReadinessProfile` and `ProposalReadiness` from `services.readiness`;
  - `PermissionActor` from `services.permissions`;
  - `ConsentReceipt` from `services.consent`.
- Public workspace methods must keep the same names and observable return
  attributes.
- Remove only helper code proven unused by `rg`.
- Do not change proposal, readiness, permission, or consent behavior.
- Do not edit `.p2p/` governance state by hand.

## Non-Goals

- Do not move `ProposalSummary`, `WorkspaceStatus`, `WorkspaceCheck`, or
  `ProposalDraftCommit` in this step.
- Do not change proposal draft commit behavior.
- Do not refactor low-level permission/consent normalization helpers unless
  they are proven unused and directly tied to removed duplicate types.

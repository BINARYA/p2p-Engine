# Governed Mutation Authority Inventory

This inventory is the reviewed schema-4 baseline for receipt-backed mutations
and proposal-decision writes. `integrated` means the implementation consumes
the typed authority contract in this feature. `existing_unintegrated` means the
capability is named but the existing local-only mutation must not be described
as externally attestable.

| Mutation | Capability | Current policy check | Subject / executor | Preview and replay | Durable evidence | CLI | MCP / consent | Guidance |
|---|---|---|---|---|---|---|---|---|
| Project initialization | `project.initialize` | Bootstrap local owner or external root | Separate in bootstrap context | Operation key, fingerprint, atomic receipt | Authority descriptor and receipt | `p2p init --authority-context` | No init MCP write | Generated setup guidance |
| Authority rotation | `project.authority.rotate` | Current root only | Separate | Preview/apply/status and exact replay | Descriptor, event ledger and receipt | `p2p project authority rotate ...` | Intentionally absent | Authority guidance block |
| Vertical install | `project.vertical.install` | Existing local actor path | Collapsed actor today | Receipt-backed | Receipt without typed authority | Existing JSON CLI | Existing registry MCP surface; local policy only | Must say unintegrated |
| Vertical adopt | `project.vertical.adopt` | Existing local actor path | Collapsed actor today | Receipt-backed | Receipt without typed authority | Existing JSON CLI | Existing vertical MCP surface; local policy only | Must say unintegrated |
| Vertical migrate | `project.vertical.migrate` | Existing local actor path | Collapsed actor today | Receipt-backed | Receipt without typed authority | Existing JSON CLI | Existing vertical MCP surface; local policy only | Must say unintegrated |
| Proposal create | `proposal.create` | Existing local actor path | Collapsed actor today | Operation key and receipt | Receipt without typed authority | Existing JSON CLI | Existing proposal MCP surface; local policy only | Must say unintegrated |
| Proposal update | `proposal.update` | Existing local actor path | Collapsed actor today | Operation key and receipt | Receipt without typed authority | Existing JSON CLI | Existing proposal MCP surface; local policy only | Must say unintegrated |
| Contribution add | `proposal.contribution.add` | Existing local actor path | Collapsed actor today | Operation key and receipt | Receipt without typed authority | Existing JSON CLI | Existing proposal MCP surface; local policy only | Must say unintegrated |
| Readiness assess | `proposal.readiness.assess` | Existing local actor path | Collapsed actor today | Operation key and receipt | Receipt without typed authority | Existing JSON CLI | Existing readiness MCP surface; local policy only | Must say unintegrated |
| Proposal decision | `proposal.decide` | Local owner or exact external claim | Separate and persisted | Preview/apply, event and receipt replay | Decision event and mutation receipt | Generic decision CLI accepts context JSON | Decision preview/apply carry context; apply retains local MCP consent | Generated decision guidance |
| Readiness override during decision | `proposal.readiness.override` | Additional root-authority claim | Same decision subject/executor | Bound into decision preview and replay | Decision event and receipt | `--override-readiness` plus exact context | Same decision MCP consent | Generated decision guidance |
| Decision projection/ledger repair | `proposal.decision.repair` | Local owner and executor | Existing local separation | Preview/apply; no mutation receipt | Atomic project files and MCP consent audit | Existing repair CLI | Existing permission-gated MCP tools | Local-only, unintegrated |

Read-only status, history, impact, schema, capability and authority inspection
are reviewed read-only exemptions. They do not accept a mutation
`AuthorityContext`; the calling transport remains responsible for access.

The future domain and structure capabilities are declared in the registry as
`planned`. Their feature specifications must consume this shared contract
before an apply surface is implemented. No WaveKit role name is part of this
inventory or the capability registry.

## Coordinated Specification Review

The following specifications were reviewed against this matrix:

- `separate-domain-from-structure-source`;
- `introduce-project-owned-structure`;
- `classify-project-memory-against-structure`;
- `retire-structure-elements-with-impact-resolution`;
- `export-project-structure-as-vertical`;
- `replace-project-structure-from-release`;
- `merge-and-restore-project-structure`;
- `rebase-readiness-on-project-structure`;
- `converge-project-structure-surfaces`;
- `extend-remote-registry-client-with-domain-discovery`.

Each implemented write must consume the named P2P capability before gaining an
apply surface. Local policy may retain standalone owner control, while hosted
delegability remains provider policy. None of these specifications imports a
WaveKit membership role into P2P. Readiness calculation remains a read-only
exemption; any future readiness override is governed separately by
`proposal.readiness.override`.

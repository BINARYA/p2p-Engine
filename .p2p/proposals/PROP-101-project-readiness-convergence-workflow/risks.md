# Risks

- **Competing sources of truth.** Question state, definition state and decision context could diverge. Mitigation: authority per field, one-way apply, v2 migration cleanup and divergence diagnostics; never merge by last-write-wins.
- **Partial canonical apply.** Calling definition apply and then updating questions can leave incompatible state. Mitigation: render both candidates and commit through one multi-target durable transaction.
- **Migration planner leakage.** A v1-to-v2 registry entry could still execute legacy-to-v1 bootstrap operations. Mitigation: transition-specific handlers with explicit target ownership and candidate-overlay composition.
- **Lossy legacy question migration.** Section-local ids, missing history or ambiguous fields could be normalized incorrectly. Mitigation: section-scoped identity, one-to-one preservation checks and blocking diagnostics for ambiguity.
- **Owner authority spoofing.** Caller-provided actor or `source=owner` could fabricate owner evidence. Mitigation: operation authority matrix, separate provided-by/recorded-by and explicit role/consent checks.
- **Stale application.** Vertical, definition, questions or policy may change after preview. Mitigation: actor-bound token over all preimages, both candidates, lock and policy versions.
- **Ambiguous replay.** A lost success response can look like illicit token reuse. Mitigation: exact committed retries return `already_applied`; divergent reuse is rejected.
- **Audit-driven nondeterminism.** Timestamps can change candidate hashes between preview and apply. Mitigation: exclude audit-only fields from semantic identity and inject them only at commit.
- **Vertical question drift.** Wording, target fields or section topology can change. Mitigation: identity/revision separation and explicit reconciliation with retire/supersede semantics.
- **Question loops and noise.** Reassessment can repeatedly create or reopen equivalent prompts. Mitigation: stable semantic identity, transition guards, fallback policy versions and deterministic deduplication.
- **Priority distortion.** Optional evidence work can displace true blockers. Mitigation: versioned six-class priority with separate definition and evidence axes.
- **Legacy output overload.** Large unmapped lists can consume terminal and agent budgets. Mitigation: summary counts, maximum limits and snapshot-bound cursors.
- **Decision-context authority leakage.** Pending answers could be indexed as active constraints. Mitigation: dedicated project-question source kind with inactive activation until definition apply.
- **Cross-service coupling.** Next actions, progress and freshness could duplicate convergence logic. Mitigation: one typed convergence result consumed by thin adapters.
- **Performance regression.** Repeated scans could make each question expensive. Mitigation: immutable request snapshot and deterministic read/hash/parse budgets.
- **Pilot overfitting.** Generic policy could encode this repository's three gaps. Mitigation: synthetic vertical, v1 migration, no-coverage and empty-workspace fixtures.

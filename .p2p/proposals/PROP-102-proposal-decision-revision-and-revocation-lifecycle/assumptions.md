# Assumptions

- Proposal and decision history remains local, Git-native and file-backed.
- Owner authority is required for every final proposal decision and revision.
- Existing proposal IDs and accepted proposal content remain stable.
- A rejected, revoked or superseded proposal remains valuable historical
  evidence and is not physically deleted.
- Current proposal status remains useful as a compact projection for existing
  commands, provided it is derived from the decision event sequence.
- Migration can represent each current aligned legacy decision as one initial
  event without inventing missing earlier history.
- Missing or malformed legacy values use `unknown_legacy` with provenance;
  ambiguous authority blocks later revision until owner curation.
- Revocation changes normative authority; implementation, deployment and
  external side effects require separate evidence and remediation.
- Revocation remains available after an impact preview and does not
  automatically mutate dependent lifecycle states.
- One versioned decision-event ledger per proposal is the canonical history
  source; current status and current decision are projections.
- Future memory consolidation will consume the centralized authority contract,
  not infer state independently from prose.

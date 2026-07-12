# Clarifications

- The placeholder-evidence fix must preserve strict placeholder detection for
  primary evidence.
- `execution-plan.md` may remain useful supplemental evidence, but placeholder
  content in it should be scored independently.
- Question normalization must not convert ordinary answered questions into
  applied questions unless the applied marker is already present.
- The implementation should prefer service-level normalization or classification
  over user-facing manual repair.

# Open Questions

No owner decision is currently blocking this proposal.

## Resolved Technical Direction

- The fix should be artifact-aware, not a readiness-policy redesign.
- Supplemental placeholder artifacts should not downgrade meaningful primary
  evidence.
- Already-applied answered questions should not be reported as unapplied when a
  durable applied marker is present.
- Existing missing and placeholder findings should remain intact for genuinely
  weak evidence.

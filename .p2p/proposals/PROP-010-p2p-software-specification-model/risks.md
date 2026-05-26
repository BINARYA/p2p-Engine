# Risks - PROP-010

## R1 - Duplicated source of truth

Risk:

Generated project artifacts may be edited manually and diverge from proposal artifacts.

Mitigation:

Mark `.p2p/project/` as derived and include provenance metadata. Decide explicitly whether manual edits are allowed.

## R2 - Premature internal spec complexity

Risk:

Designing a complete specification model too early could slow CLI progress.

Mitigation:

Start with a minimal `software-spec/index.md` and module files. Add schemas only when exporter or task tracking needs prove them necessary.

## R3 - Automatic refresh surprises users

Risk:

If accepting a proposal silently rewrites derived files, users may be surprised by broad diffs.

Mitigation:

Start with explicit `p2p project refresh`. Add automatic refresh later behind an option or config flag.

## R4 - Exporter coupling

Risk:

The internal spec model could accidentally mirror OpenSpec or Spec Kit too closely.

Mitigation:

Keep P2P spec concepts neutral and map to downstream tools through adapters.

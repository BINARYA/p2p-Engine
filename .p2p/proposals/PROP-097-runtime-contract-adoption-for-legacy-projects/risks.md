# Risks

The main risk is accidental contract declaration with the wrong runtime version.
This is mitigated by requiring the proposed `requires` and `recommended` values
to be visible and explicitly confirmed by the owner.

A second risk is overwriting human setup documentation. Adoption must treat an
unmanaged `P2P-SETUP.md` as a blocker and leave adoption, replacement, or backup
of that document to a separate future capability.

A third risk is scope creep into runtime installation or upgrade. The adoption
command must write only project contract artifacts and must not call package
managers, network release lookup, Git automation, or environment mutation.

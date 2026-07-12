# Exploration Findings

PROP-095 should be scoped as a project runtime contract update lifecycle, not as
an upgrade or installation lifecycle. The real project risk is not that P2P
Engine fails to install itself automatically; the risk is that the owner changes
the project runtime requirement without a governed, previewable, and coordinated
state change.

The proposal therefore needs to handle two audiences:

- owners who are allowed to apply a runtime contract update;
- agents and collaborators who need to understand the proposed change, its
  impact, and the next action when their local runtime is no longer compatible.

The safest implementation shape is a read-only `preview` command plus a
write-capable `apply` command. Preview validates and explains the proposed
change without mutating state or requiring owner authority. Apply repeats all
checks on current state and enforces owner authority before writing.

The update must coordinate the normative contract and the generated setup guide.
The contract is the source of truth, but the guide is the collaborator-facing
artifact. Leaving them inconsistent would make the runtime contract harder to
operate in a shared Git project.

The lifecycle must also respect the boundary introduced by PROP-084: P2P may
warn, block, or guide when the runtime is incompatible, but it must not silently
install, upgrade, downgrade, or reconcile the user's environment.

PROP-095 addresses a project-contract lifecycle gap left intentionally open by PROP-084. The problem is not generic environment reconciliation. The problem is that the owner needs a governed, validated way to change the runtime requirement that the project publishes to collaborators.

The proposal should preserve three separate responsibilities:

- PROP-084 declares, validates, reports, and gates against the runtime contract.
- PROP-095 changes the project runtime contract through an explicit owner action.
- PROP-078 or a later install/reconciliation capability helps users install or update their local runtime.

The central hidden decision is the write-gate exception. Without an exception, an owner who has already upgraded locally to a runtime outside the old project range cannot use the new runtime to update the project contract. With a broad exception, the command becomes a backdoor for corrupted, missing, or unsupported contracts. The safe middle ground is a narrow exception only when the old contract is valid and understood, and the active runtime is incompatible only because it falls outside the old `requires` range.

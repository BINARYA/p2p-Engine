# Clarifications - Agent Persistence Boundaries And Proposal Authoring Flow

The owner clarified that sibling repositories are not a product direction for P2P Engine. They are only one local deployment topology that exposed a more general issue: P2P must have an explicit decision root that is not implicitly tied to the current working directory.

The owner also clarified that differing physical files across proposal directories are not automatically a bug. Proposal files may be materialized by the workflows that actually ran. The product issue is that owners and agents should not need to infer proposal completeness from filesystem shape. P2P should expose a deterministic logical artifact catalog or equivalent artifact-state view, while avoiding empty placeholder files that invite manual edits or create false uniformity.

The owner further clarified that agent confusion is not only about permissions or file placement. Agents need a compact operational understanding of what P2P Engine is for and how to route common owner requests. Existing documentation is useful but not sufficient if the practical routing model is not present in generated agent instructions or a concise agent playbook.

The owner refined the init direction. The desired direction is not a strict minimal default. The default should be adaptive: always install `generic`; add the current detected agent when detection is reliable; if the agent cannot be detected, fall back to `all` so cross-agent usability and current-release compatibility are preserved. Because this makes adapter selection more intentional, init summaries, generated `AGENTS.md`, and docs must clearly show how to add another integration later.

The owner also raised removal. Removing integrations should be supported and documented as a safe lifecycle operation through P2P commands, not by deleting files or editing `.p2p/agent-integrations.yml` manually. Removal must not delete shared baseline files or human-edited drifted files silently.

The owner then asked for explicit risk-mitigation guidance to prevent breaking projects generated with the current release. The compatibility direction is that PROP-093 may change defaults, generated instructions, and preferred workflows, but it must not retroactively invalidate existing `.p2p/` state. Existing workspaces should remain readable and valid; new metadata should be optional or lazily inferred; existing proposal-local files should be preserved; existing commands should remain stable by default; and destructive changes must require explicit safe lifecycle commands.

The owner further clarified that PROP-093 should be treated with a scope lock. The semantic core is canonical write surfaces, persistent write classes, artifact boundaries, proposal authoring flow, deterministic logical artifact status, owner full view, and a compact agent routing playbook. The operational core is explicit decision root, CLI root handling, MCP root hints, and generated instructions that help agents use the governed P2P root. Adaptive adapter selection and integration lifecycle are bootstrap UX. `.gitignore` protection and grouped summaries are hygiene. Implementation should therefore be sliced into 093-A through 093-E instead of delivered as one monolithic Change Set.

The owner also clarified that core P2P should not make `specs` a generic primitive. Domain artifacts belong to explicit vertical primitives or import/export/catalog contracts. In the software case, the specification lifecycle is handled by PROP-094 and the software vertical. PROP-093 should only ensure agents know when to route such requests to the relevant vertical instead of creating unmanaged files.

The `stable_documentation` write class is a persistence and preview label, not a governance ownership claim. Agents should preview durable documentation writes, classify their governance status, and explain whether the file is P2P-governed, generated/exported, imported/cataloged, or outside P2P. P2P does not govern every stable repository document unless a supported primitive explicitly imports, exports, or catalogs it.

The owner then raised the future case where an agent uses only MCP HTTP and has no filesystem access. That direction is aligned with PROP-093, because it makes direct `.p2p/` file mutation impossible by construction. It does not make PROP-093 unnecessary. PROP-093 defines the semantic contract that CLI, local MCP, and future HTTP MCP or service APIs must share: governed P2P state is changed through typed P2P write primitives; the filesystem, when present, is storage, compatibility surface, import source, generated export target, or human-readable projection rather than the normal agent write interface.

The owner also clarified that PROP-093 should not jump directly to MCP HTTP-only as an implementation requirement. P2P Engine remains local-first and filesystem-backed today, and existing workspaces must remain transparent, readable, valid, and Git-compatible. Future HTTP MCP strengthens the need for artifact catalog APIs, full proposal rendering, preview or dry-run manifests, and semantic tools instead of raw remote file-write APIs, but implementing MCP HTTP belongs outside this proposal.

The corrected core direction is:

- P2P should not recommend or model sibling specification repositories.
- P2P should make the decision root explicit through CLI `--root`, MCP configuration, generated hints, and agent instructions.
- P2P should treat decision-root and MCP/CLI root hardening as core operational work, not as optional repository hygiene.
- P2P should govern persistent agent writes through explicit CLI, local MCP, or future HTTP/service write primitives, never through direct filesystem mutation as the normal agent write path.
- P2P should remove ambiguity between canonical structured state and generated or imported narrative artifacts.
- P2P should expose deterministic logical artifact status independently from physical file materialization.
- P2P should not create empty proposal files only to make directories look uniform.
- P2P should give agents a concise request-routing playbook that distinguishes chat-only exploration, project definition, proposals, choices, explicit vertical primitives such as the PROP-094 software-spec lifecycle, implementation work, exact file requests, and outside-P2P work.
- P2P init should use adaptive adapter selection: `generic` plus detected current agent, with `all` fallback when detection is unavailable.
- P2P should make adding, updating, inspecting, refreshing, and removing agent integrations visible from bootstrap output and generated instructions.
- P2P should preserve compatibility for projects initialized with the current release through non-destructive migrations, legacy inference, additive command behavior, and validation that does not fail only because new PROP-093 metadata is absent.
- The software specification lifecycle belongs to PROP-094 and the software vertical, not to this core proposal, except for routing guidance that points agents to the vertical instead of unmanaged files.

This refinement prevents five false lessons from the feedback. The lesson is not "support sibling repos"; it is "make the write interface and decision root unambiguous." The lesson is not "every proposal directory must contain the same files"; it is "make artifact status deterministic and visible through P2P itself." The lesson is not "write more general documentation"; it is "put the operational routing model where agents will actually use it." The lesson is not "make init minimal at all costs"; it is "detect the current agent when possible and make the adapter lifecycle obvious." The lesson is not "clean up old state aggressively"; it is "upgrade old state safely and non-destructively."

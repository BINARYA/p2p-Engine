# Exploration - Agent Persistence Boundaries And Proposal Authoring Flow

The refined issue is a core P2P affordance problem. P2P should encourage agents to use governed state early, but the engine must make it obvious which surfaces are canonical write interfaces and which surfaces are generated, imported, rendered, or external.

The sibling-repository case is not a product requirement. It is a stress test that exposed that the P2P decision root must be explicit and independent of current working directory assumptions.

The strongest failure mode is contradictory guidance:

- generated policy says not to edit `.p2p/` by hand;
- proposal scaffolds narrative markdown files that look editable;
- canonical inputs live in structured files or services;
- the structured authoring flow is not obvious from proposal help or scaffold output.

The proposal should therefore harden both consent and affordance: preview writes, classify writes, align primitives with rendered concepts, and provide a full owner view.

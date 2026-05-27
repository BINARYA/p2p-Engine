# Alternatives - PROP-042

## Alternative A - Core Directly Invokes AI

P2P Core or CLI directly calls Codex, Claude or other providers for analysis.

Pros:

- convenient CLI UX;
- fewer manual prompt/import steps;
- faster perceived intelligence.

Cons:

- couples the deterministic core to providers, credentials, costs and rate limits;
- makes tests and reproducibility harder;
- increases security surface;
- blurs whether P2P is recommending or deciding.

Assessment:

Rejected as the primary architecture. It may be revisited later as a thin optional adapter, but not as the core boundary.

## Alternative B - Core Deterministic, AI Mediator Outside

P2P Core remains deterministic. Optional mediator layers use CLI/MCP/API to interact with it.

Pros:

- keeps open-source local usage complete;
- supports multiple intermediaries chosen by the user;
- keeps credentials and provider behavior outside the core;
- scales to Codex, Claude, custom models, web assistants and IDEs;
- preserves auditability and governance clarity.

Cons:

- requires a clean interface contract;
- may feel less automatic without a mediator;
- needs additional packaging for MCP/mediator layers.

Assessment:

Accepted as the preferred direction.

## Alternative C - Web Product First

Build the web app and put intelligence/collaboration there first.

Pros:

- clearer product UX for non-technical users;
- easier onboarding and collaboration;
- central place for mediator features.

Cons:

- risks delaying the open local engine;
- introduces auth, hosting, persistence and security concerns too early;
- can accidentally make the web app the source of truth instead of `.p2p/`.

Assessment:

Deferred. Web remains a higher layer after Core/CLI/MCP boundaries are stable.

## Alternative D - MCP Server Includes Mediator Logic

Make the MCP server both the tool interface and the intelligent mediator.

Pros:

- fewer deployable components;
- agents get smarter behavior through one endpoint.

Cons:

- mixes deterministic tools with non-deterministic reasoning;
- makes it harder to test and secure;
- reduces portability across different mediator implementations.

Assessment:

Rejected. MCP should expose P2P Core tools. Mediator logic should be separate and optional.

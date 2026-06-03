# Spec Kit Specify Prompt

Use this content with `/speckit.specify`. Focus on what and why; do not select a tech stack here.

## What To Build

- **PROP-001 CLI Foundation**: Build the first P2P Engine CLI using Python and Typer.

The CLI should focus on local file generation and workflow guidance:

```text
p2p init
p2p proposal create
p2p contribution add
p2p digest prompt
p2p clarify prompt
p2p decision record
p2p plan prompt
p2p tasks prompt
p2p status
```

The first version should implement prompt generation instead of direct AI integration. A command such as:

```bash
p2p digest prompt PROP-001
```

should generate:

```text
.p2p/prompts/PROP-001/digest.prompt.md
```

The user can then provide that prompt to Codex, ChatGPT, Claude, Llama, or another model manually and paste the output into the correct artifact.
- **PROP-004 Prompt-only Import Workflow**: Implementare comandi import uniformi per le fasi successive a explore e aggiungere synthesize prompt/import.
- **PROP-005 Codex Skill Integration**: Aggiungere una skill locale .codex/skills/p2p-engine/SKILL.md che istruisca Codex a usare P2P Engine come sorgente di verita operativa.
- **PROP-009 Governance CLI Commands**: Aggiungere comandi governance file-based per rendere operativo il modello di PROP-008, mantenendo Git come audit layer e rimandando enforcement permessi a fasi future.
- **PROP-010 P2P Project State Model**: Add a P2P project state model that turns accepted proposals into versioned project artifacts under `.p2p/project/`. The MVP uses explicit refresh via `p2p project refresh`; automatic refresh after acceptance can be added later.
- **PROP-011 Project Refresh MVP**: Add deterministic project-state generation from accepted proposals, starting with overview, problem, scope, project SWOT placeholder, features, decisions-map, and conflicts.
- **PROP-012 Impact Map and Conflict Memory**: Add impact and conflict artifacts that allow P2P Engine to understand which project areas a proposal touches and preserve memory of competing or mutually exclusive alternatives.
- **PROP-013 Managed Git Adapter and Change Set Model**: Adopt a managed Git model: proposals and change sets are the public P2P concepts, while Git branches, commits, merges, and tags are internal operations selected by a configurable policy. Git details are visible only in verbose/debug modes.

## Why

- **PROP-001 CLI Foundation**: P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.
- **PROP-004 Prompt-only Import Workflow**: P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.
- **PROP-005 Codex Skill Integration**: Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.
- **PROP-009 Governance CLI Commands**: P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.
- **PROP-010 P2P Project State Model**: Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.
- **PROP-011 Project Refresh MVP**: P2P Engine has accepted the .p2p/project state model, but the CLI cannot yet generate or inspect that rationalized project layer.
- **PROP-012 Impact Map and Conflict Memory**: P2P Engine can generate a rationalized project state, but it does not yet capture what a proposal touches or whether it overlaps, depends on, supersedes, or conflicts with other proposals.
- **PROP-013 Managed Git Adapter and Change Set Model**: P2P Engine distinguishes proposals from project state, but it does not yet define how accepted decisions become operational change sets or how Git operations should be managed under the hood without exposing branch/commit/merge complexity to users.

## Users And Workflows

- Humans supervise and decide.
- Agents use P2P memory to preserve project context and propose bounded changes.

## Requirements

## Functional Requirements

### PROP-066 - Permission-Gated MCP Governance And Git Operations

Adopt a hybrid Role + Consent Receipt model for permission-gated MCP governance and Git operations.

P2P distinguishes three concepts:

- actor_id: the declared person, agent, or client performing work; useful for audit and collaboration but not strong authentication in local/Git-only mode.
- authorizer: the project role or owner identity that approves a privileged operation.
- enforcer: the mechanism that actually prevents unauthorized state changes. In local projects this is mostly P2P policy and audit. In cloud-backed projects this must be Git provider permissions, branch protection, required approvals, and token scopes.

Project-declared roles are stored in versioned P2P project policy, such as `.p2p/project/permissions.yml` or an equivalent generated policy file. On project init, P2P should ask for or accept an owner display name. If no owner is provided, it creates a generic `owner` identity. Contributor identities may be added later; if no contributor name is known, P2P may use generic `contributor` or agent IDs for branch metadata.

Example policy:

```yaml
permissions:
  version: 1
  identities:
    owner:
      role: owner
      kind: person
      display_name: owner
    contributor:
      role: contributor
      kind: person
      display_name: contributor
  roles:
    owner:
      can_grant_consent: true
      can_manage_permissions: true
    maintainer:
      can_request_privileged_operations: true
    contributor:
      can_create_local_branches: true
      can_request_review: true
    agent:
      can_use_safe_tools: true
    readonly:
      can_read: true
```

Tool classes:

- safe_read: read/status/context/scan tools; no consent required.
- write_safe_preparatory: deterministic or local preparatory operations such as fetch and proposal branch creation; no owner consent required by default, but must be audited when they touch Git state.
- privileged_publish: publish, push, request-review, provider PR/MR handoff; requires a valid consent receipt unless project policy explicitly allows the actor role.
- owner_controlled_governance: accept, reject, defer, choice decide, select candidate, merge, finalize, cleanup; requires owner consent receipt.
- destructive_or_external: cleanup, branch deletion, provider side effects, irreversible remote changes; requires owner consent receipt, single-use, and explicit audit.

Consent receipts are versioned audit records granting one bounded privileged operation. They include consent_id, operation, target, actor_id, requested_by, approved_by, role, scope, expiry, single_use flag, created_at, and optional provider metadata. Sensitive MCP tools must refuse execution without a valid unexpired receipt. After single-use execution, the receipt is marked consumed with result metadata.

The MVP does not require external IAM. Project init should support an owner name but must fall back to generic `owner`. The model is declarative and auditable locally. In cloud-backed projects, robust enforcement depends on Git provider controls protecting main and privileged remote actions. A future P2P API server may replace or augment declarative identities with authenticated users, OAuth, organization membership, signed consent, or IAM-backed policy checks.

Safe MCP surface may remain available before privileged consent implementation: sync status/fetch and proposal branch/status/scan. MCP pull, push, publish, request-review, retire, accept, reject, merge, finalize, cleanup, provider PR/MR handoff, and protected-branch updates remain deferred until role policy, consent receipts, and audit records are implemented.

## Non-Goals / Exclusions

- Automatic Git commits, branches, tags, or merges.

## Constraints

Do not treat raw proposal discussion as implementation requirements without accepted scope.

## Open Questions

Not specified yet.

## Success Criteria

## Criteria

- Change Set metadata is present and reviewable.

## Tests / Verification

- Not specified yet.

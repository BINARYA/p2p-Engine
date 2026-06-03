# OpenSpec Proposal Input

Use this as the proposal-oriented initialization input for OpenSpec or an OpenSpec-aware agent.

## Problem

- **PROP-001 CLI Foundation**: P2P Engine does not exist yet as an executable tool. The project has a solid foundation document, but no CLI, no generated `.p2p/` structure, no automated proposal workflow, and no prompt generation.

Without a first working CLI, every proposal must be created manually. That is acceptable for the bootstrap phase, but it must become automated quickly so the project can start using its own method.
- **PROP-004 Prompt-only Import Workflow**: P2P Engine genera prompt per varie fasi, ma non importa ancora in modo uniforme gli output prodotti da AI o agenti esterni.
- **PROP-005 Codex Skill Integration**: Codex oggi non ha istruzioni formali per usare P2P Engine come metodo operativo e rischia di lasciare decisioni e interlocuzioni solo nella chat.
- **PROP-009 Governance CLI Commands**: P2P Engine ha un modello di governance file-based, ma non ha ancora comandi CLI per inizializzare governance, generare SWOT, registrare voti, mostrare risultati e registrare precedenti decisionali.
- **PROP-010 P2P Project State Model**: Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.
- **PROP-011 Project Refresh MVP**: P2P Engine has accepted the .p2p/project state model, but the CLI cannot yet generate or inspect that rationalized project layer.

## Proposed Change

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

## Scope

- **PROP-001 CLI Foundation**: - Implement a minimal `p2p` CLI.
- Generate the `.p2p/` project structure with `p2p init`.
- Create proposal folders and baseline artifacts with `p2p proposal create`.
- Add structured contributions with `p2p contribution add`.
- Record decisions with `p2p decision record`.
- Generate prompt files for digest, clarify, plan, and tasks.
- Keep AI invocation optional and out of scope for the first implementation.
- Preserve compatibility with future OpenSpec and Spec Kit exports.
- **PROP-004 Prompt-only Import Workflow**: - Aggiungere import per clarify, synthesize, plan e tasks.
- Rendere il workflow prompt-only end-to-end testabile.
- **PROP-005 Codex Skill Integration**: - Creare una skill Codex che guidi l'uso della CLI P2P e degli artefatti .p2p.
- Stabilire regole per trasformare conversazioni in proposal, exploration, decisioni, piani e task versionati.
- **PROP-009 Governance CLI Commands**: - Implementare p2p governance init/status.
- Implementare p2p swot prompt per alternative contrapposte.
- Implementare p2p vote record/status.
- Implementare p2p precedent record.
- **PROP-010 P2P Project State Model**: - Define a P2P-native project state generated from accepted proposals.
- Create a dedicated `.p2p/project/` area for rationalized project artifacts.
- Specify how accepted proposals update project state.
- Keep OpenSpec and Spec Kit as downstream exporters, not the source of truth.
- **PROP-011 Project Refresh MVP**: - Implement p2p project refresh to generate the first .p2p/project artifacts.
- Implement p2p project status to inspect generated project state.
- Implement p2p project show to read generated project sections.

## Out Of Scope

- **PROP-001 CLI Foundation**: - No web app.
- No users, accounts, permissions, billing, or dashboard.
- No managed AI provider.
- No MCP server.
- No full OpenSpec or Spec Kit exporter in the first slice.
- No automatic code implementation.
- No advanced governance engine.
- **PROP-004 Prompt-only Import Workflow**: - Non invocare provider AI direttamente.
- Non introdurre MCP.
- Non aggiungere web app o database.
- **PROP-005 Codex Skill Integration**: - Non introdurre MCP in questa fase.
- Non invocare direttamente provider AI dalla CLI.
- Non sostituire la CLI come sorgente di verita.
- **PROP-009 Governance CLI Commands**: - Implementare enforcement reale dei permessi applicativi.
- Integrare branch protection, CODEOWNERS o required approvals.
- Chiudere automaticamente votazioni o decisioni complesse.
- **PROP-010 P2P Project State Model**: - Implement a full OpenSpec or Spec Kit exporter in this proposal.
- Replace proposal, decision, plan, or task artifacts.
- **PROP-011 Project Refresh MVP**: - Implement OpenSpec or Spec Kit export.
- Implement automatic refresh after decision record.

## Impact

- Source Change Set: `CHANGE-054` Permission-Gated MCP Roles and Consent Receipts

## Risks

- NEEDS CLARIFICATION: confirm target-specific risks before implementation.

## Acceptance Criteria

## Criteria

- Change Set metadata is present and reviewable.

## Tests / Verification

- Not specified yet.

## Source Traceability

- `PROP-001` CLI Foundation — `.p2p/proposals/PROP-001-cli-foundation`
- `PROP-004` Prompt-only Import Workflow — `.p2p/proposals/PROP-004-prompt-only-import-workflow`
- `PROP-005` Codex Skill Integration — `.p2p/proposals/PROP-005-codex-skill-integration`
- `PROP-009` Governance CLI Commands — `.p2p/proposals/PROP-009-governance-cli-commands`
- `PROP-010` P2P Project State Model — `.p2p/proposals/PROP-010-p2p-software-specification-model`
- `PROP-011` Project Refresh MVP — `.p2p/proposals/PROP-011-project-refresh-mvp`
- `PROP-012` Impact Map and Conflict Memory — `.p2p/proposals/PROP-012-impact-map-and-conflict-memory`
- `PROP-013` Managed Git Adapter and Change Set Model — `.p2p/proposals/PROP-013-change-set-and-git-branch-model`
- `PROP-014` Change Set Metadata MVP — `.p2p/proposals/PROP-014-change-set-metadata-mvp`
- `PROP-015` Change Set Lifecycle and Task Tracking — `.p2p/proposals/PROP-015-change-set-lifecycle-and-task-tracking`
- `PROP-016` Project Registries MVP — `.p2p/proposals/PROP-016-project-registries-mvp`
- `PROP-017` Proposal Intake and Context Analysis MVP — `.p2p/proposals/PROP-017-proposal-intake-and-context-analysis-mvp`
- `PROP-018` Choice Management CLI MVP — `.p2p/proposals/PROP-018-choice-management-cli-mvp`
- `PROP-019` Proposal Decision Shortcut Commands — `.p2p/proposals/PROP-019-proposal-decision-shortcut-commands`
- `PROP-020` Proposal Inspection CLI MVP — `.p2p/proposals/PROP-020-proposal-inspection-cli-mvp`
- `PROP-021` Agent Skill Real Commands Update — `.p2p/proposals/PROP-021-agent-skill-real-commands-update`
- `PROP-022` Operational Brief Prompt Workflow — `.p2p/proposals/PROP-022-operational-brief-prompt-workflow`
- `PROP-023` Next Action Recommender MVP — `.p2p/proposals/PROP-023-next-action-recommender-mvp`
- `PROP-024` Choice Blocking and Discovery MVP — `.p2p/proposals/PROP-024-choice-blocking-and-discovery-mvp`
- `PROP-025` Controlled Intake Apply Workflow — `.p2p/proposals/PROP-025-controlled-intake-apply-workflow`
- `PROP-026` P2P Software Spec Generator MVP — `.p2p/proposals/PROP-026-p2p-software-spec-generator-mvp`
- `PROP-027` Software Spec Exporter MVP — `.p2p/proposals/PROP-027-software-spec-exporter-mvp`
- `PROP-028` Spec Kit Export Mapping MVP — `.p2p/proposals/PROP-028-spec-kit-export-mapping-mvp`
- `PROP-029` Spec Export Validation MVP — `.p2p/proposals/PROP-029-spec-export-validation-mvp`
- `PROP-030` Managed Work and Multi-Branch Visibility Policy — `.p2p/proposals/PROP-030-managed-work-and-multi-branch-visibility-policy`
- `PROP-031` Multi-Branch Work Scan MVP — `.p2p/proposals/PROP-031-multi-branch-work-scan-mvp`
- `PROP-032` Managed Work Branch Creation MVP — `.p2p/proposals/PROP-032-managed-work-branch-creation-mvp`
- `PROP-033` Managed Work Submit MVP — `.p2p/proposals/PROP-033-managed-work-submit-mvp`
- `PROP-034` Managed Work Review MVP — `.p2p/proposals/PROP-034-managed-work-review-mvp`
- `PROP-035` Managed Work Publish MVP — `.p2p/proposals/PROP-035-managed-work-publish-mvp`
- `PROP-036` Managed Work Accept MVP — `.p2p/proposals/PROP-036-managed-work-accept-mvp`
- `PROP-037` Managed Work Status Summary MVP — `.p2p/proposals/PROP-037-managed-work-status-summary-mvp`
- `PROP-038` Managed Work Merge Conflict Guidance MVP — `.p2p/proposals/PROP-038-managed-work-merge-conflict-guidance-mvp`
- `PROP-039` Managed Work Finalize MVP — `.p2p/proposals/PROP-039-managed-work-finalize-mvp`
- `PROP-040` Managed Work Cleanup MVP — `.p2p/proposals/PROP-040-managed-work-cleanup-mvp`
- `PROP-041` Remote Project Profile and Review Request Policy — `.p2p/proposals/PROP-041-remote-project-profile-and-review-request-policy`
- `PROP-042` P2P Core CLI MCP Mediator Web Boundary — `.p2p/proposals/PROP-042-p2p-core-cli-mcp-mediator-web-boundary`
- `PROP-043` Managed Work Retire MVP — `.p2p/proposals/PROP-043-managed-work-retire-mvp`
- `PROP-044` P2P MCP Server MVP — `.p2p/proposals/PROP-044-p2p-mcp-server-mvp`
- `PROP-045` Agent-Safe Project Bootstrap MVP — `.p2p/proposals/PROP-045-agent-safe-project-bootstrap-mvp`
- `PROP-046` MCP Write-Safe Bootstrap Tools MVP — `.p2p/proposals/PROP-046-mcp-write-safe-bootstrap-tools-mvp`
- `PROP-047` Guided Init Wizard MVP — `.p2p/proposals/PROP-047-guided-init-wizard-mvp`
- `PROP-048` MCP Level 3 Proposal and Intake Draft Tools — `.p2p/proposals/PROP-048-mcp-level-3-proposal-and-intake-draft-tools`
- `PROP-049` MCP Level 4A Proposal Refinement Tools — `.p2p/proposals/PROP-049-mcp-level-4a-proposal-refinement-tools`
- `PROP-050` MCP Level 4B Choice Conflict Impact Advisory Tools — `.p2p/proposals/PROP-050-mcp-level-4b-choice-conflict-impact-advisory-tools`
- `PROP-051` Draft Proposal Next Action and Agent Explanation Guard — `.p2p/proposals/PROP-051-draft-proposal-next-action-and-agent-explanation-guard`
- `PROP-052` MCP Proposal Contribution Tool — `.p2p/proposals/PROP-052-mcp-proposal-contribution-tool`
- `PROP-053` Core Validation Layer MVP — `.p2p/proposals/PROP-053-core-validation-layer-mvp`
- `PROP-054` Project Readiness and Maturity Assessment — `.p2p/proposals/PROP-054-project-readiness-and-maturity-assessment`
- `PROP-055` Agent Token Budget and Context Discipline — `.p2p/proposals/PROP-055-agent-token-budget-and-context-discipline`
- `PROP-056` Project Definition Maturity Rubrics — `.p2p/proposals/PROP-056-project-definition-maturity-rubrics`
- `PROP-057` Guided Rubric Selection During Init — `.p2p/proposals/PROP-057-guided-rubric-selection-during-init`
- `PROP-058` Project README and Installation Guide — `.p2p/proposals/PROP-058-project-readme-and-installation-guide`
- `PROP-061` Focused README and Documentation Map — `.p2p/proposals/PROP-061-focused-readme-and-documentation-map`
- `PROP-062` README Product Landing Page Refinement — `.p2p/proposals/PROP-062-readme-product-landing-page-refinement`
- `PROP-064` Spec Kit Three-Prompt Export Model — `.p2p/proposals/PROP-064-spec-kit-three-prompt-export-model`
- `PROP-065` MCP Agent-First Coverage Expansion — `.p2p/proposals/PROP-065-mcp-agent-first-coverage-expansion`
- `PROP-066` Permission-Gated MCP Governance And Git Operations — `.p2p/proposals/PROP-066-permission-gated-mcp-governance-and-git-operations`
- `PROP-067` Agent-First Setup Documentation Split — `.p2p/proposals/PROP-067-agent-first-setup-documentation-split`
- `PROP-068` Document Agent MCP Client Setup Commands — `.p2p/proposals/PROP-068-document-agent-mcp-client-setup-commands`
- `PROP-069` Clarify MCP Stdio Integration Model — `.p2p/proposals/PROP-069-clarify-mcp-stdio-integration-model`
- `PROP-070` Clarify README Agent Access Modes — `.p2p/proposals/PROP-070-clarify-readme-agent-access-modes`
- `PROP-071` Custom Domain Definition Workflow — `.p2p/proposals/PROP-071-custom-domain-definition-workflow`
- `PROP-072` Concurrent Managed Work and Merge Decision Model — `.p2p/proposals/PROP-072-concurrent-managed-work-and-merge-decision-model`

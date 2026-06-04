# Execution Plan - PROP-002

## Objective

Implementare il workflow **Proposal Exploration And Readiness** in modo
progressivo, mantenendo separati:

- artifact authored in Markdown;
- readiness profile versionati;
- assessment/snapshot machine-readable;
- registry come cache operativa;
- governance decision e override come audit event;
- agent/MCP behavior come guida metodologica, non come autorita decisionale.

Il piano assume che PROP-002 sia `governance-critical` e che il primo profilo
sia `default-readiness-v0.1`.

## Implementation Strategy

Procedere per tranche piccole e verificabili. La prima implementazione deve
stabilizzare il modello di dominio e la CLI read/report prima di introdurre
write governance o MCP write tools.

Sequenza raccomandata:

1. domain model and storage
2. readiness profile and assessment schema
3. artifact quality model
4. proposal readiness CLI
5. registry snapshot and `p2p next`
6. owner override during acceptance
7. MCP and skill coverage
8. migration and validation
9. docs and tests

## Phase 1 - Domain Model And Storage

### Goals

- Definire i tipi interni per readiness profile, criterion assessment, readiness
  snapshot, artifact quality, confidence e failed gates.
- Introdurre storage layered senza rendere il registry fonte primaria.

### Work

- Add readiness profile model:
  - `profile_id`
  - `profile_version`
  - criteria and weights
  - thresholds
  - tier requirements
  - gates
  - override policy
- Add proposal readiness assessment model:
  - profile reference
  - computed score and label
  - effective status
  - confidence and reasons
  - tier suggested/confirmed
  - criterion-level evidence
  - failed gates
  - missing dimensions
  - suggested next actions
  - stale/computed metadata
- Add artifact quality model:
  - `missing`
  - `placeholder`
  - `thin`
  - `meaningful`
  - `needs_owner_input`
  - `ready`
- Proposed paths:

```text
.p2p/config/readiness-profiles/default-readiness-v0.1.yml
.p2p/proposals/PROP-XXX/readiness.yml
.p2p/registries/readiness.yml
decision/audit event for accept-with-override
```

### Acceptance

- Default readiness profile can be loaded.
- Proposal readiness assessment can be read and written.
- Missing readiness files are handled as `not_assessed`, not as corruption.
- Registry readiness is explicitly treated as snapshot/cache.

## Phase 2 - Default Readiness Profile

### Goals

Implementare `default-readiness-v0.1` come primo profilo versionato.

### Work

- Define default criteria:

```text
problem_clarity: 10
goal_clarity: 10
scope_boundaries: 10
alternatives_quality: 15
tradeoff_analysis: 10
risk_coverage: 10
assumptions_clarity: 10
owner_questions_resolution: 10
acceptance_criteria_quality: 10
impact_overlap_analysis: 5
```

- Define labels:

```text
0-69   weak
70-84  partial
85-94  strong
95-100 decision_ready
```

- Define tier requirements:
  - `small`: target 70, lightweight gates.
  - `medium`: target 85, minimum gates for alternatives, risks, acceptance.
  - `architectural`: target 95, stronger minimum gates.
  - `governance-critical`: target 95, strong minimum gates and confidence
    requirement.

### Acceptance

- Profile validates strictly.
- Score cannot be computed without profile id/version.
- Unknown profile ids produce clear errors.

## Phase 3 - Artifact Quality Assessment

### Goals

Evolvere `explore status` da file existence check a artifact quality report.

### Work

- Add deterministic detection for:
  - missing files;
  - placeholder text;
  - obvious thin content.
- Support imported/recorded assessment for:
  - `meaningful`;
  - `ready`;
  - `needs_owner_input`.
- Apply artifact quality caps:

```text
missing -> 0%
placeholder -> 0%
thin -> 50%
meaningful -> 75%
needs_owner_input -> 75% and blocks automatic ready_for_decision
ready -> 100%
```

- Make `needs_owner_input` drive next actions like:
  - `ask_owner`
  - `resolve_owner_question`
  - `confirm_policy`

### Acceptance

- `p2p explore status PROP-XXX` reports artifact quality states.
- Placeholder and thin artifacts cannot unlock full criterion points.
- `needs_owner_input` is distinct from `thin`.

## Phase 4 - Proposal Readiness CLI

### Goals

Introdurre comandi CLI dedicati alla readiness della proposal.

### Work

Recommended commands:

```bash
p2p proposal readiness PROP-XXX
p2p proposal readiness refresh PROP-XXX
p2p proposal readiness explain PROP-XXX
```

- `readiness` shows current snapshot or `not_assessed`.
- `readiness refresh` recomputes deterministic parts, applies caps/gates, and
  stores snapshot.
- `readiness explain` prints criterion-level evidence, failed gates, confidence,
  missing dimensions, and suggested next actions.

### Acceptance

- Commands produce stable, agent-friendly output.
- `not_assessed` is explicit for existing drafts.
- Readiness report distinguishes computed analysis from owner governance status.

## Phase 5 - Scoring, Gates, Confidence, Evidence

### Goals

Implementare il modello ibrido: agent/author assessment per qualita e CLI per
validazione, caps, aggregazione e gate.

### Work

- Support structured criterion evidence:

```yaml
criteria:
  alternatives_quality:
    max_points: 15
    awarded_points: 11
    artifact_quality: meaningful
    evidence:
      - artifact: alternatives.md
        section: Alternative F - Hybrid Exploration And Readiness Model
    notes: "Alternative reali presenti, ma manca matrice comparativa completa."
```

- Aggregate score from awarded points.
- Apply artifact caps after assessment.
- Apply minimum gates and required confidence.
- Compute:
  - `computed_score`
  - `computed_label`
  - `confidence`
  - `failed_gates`
  - `missing`
  - `suggested_next`

### Acceptance

- Criteria without evidence are capped or warned.
- High score with failed gate is not `ready_for_decision`.
- High score with low confidence is not automatic `ready_for_decision`.
- Governance-critical proposals require at least medium confidence for automatic
  readiness promotion.

## Phase 6 - Registry Snapshot And `p2p next`

### Goals

Rendere readiness disponibile a `p2p next` e status summaries senza leggere
ogni artifact in modo costoso.

### Work

- Add `.p2p/registries/readiness.yml` as generated snapshot/cache.
- Add stale detection when source artifacts or readiness profile change.
- Update `p2p registry refresh` to include readiness snapshot when available.
- Update `p2p next` to show:
  - current score;
  - target score;
  - missing points;
  - failed gates;
  - highest-impact actions;
  - `not_assessed` recommendations for open drafts.
- Use gate-first ranking:

```text
priority =
  failed_gate_weight
  + recoverable_points
  + tier_importance
  + dependency_unblocking_value
```

### Acceptance

- `p2p next` recommends readiness assessment for `not_assessed` drafts.
- Failed gates outrank raw point gain.
- Registry stale state is visible as warning, not source corruption.

## Phase 7 - Owner Override During Acceptance

### Goals

Implementare override come evento governance durante acceptance, non come score
edit.

### Work

- Extend acceptance flow:

```bash
p2p proposal accept PROP-XXX --override-readiness --reason "..."
```

- Require:
  - owner authority / consent path used by existing governance policy;
  - mandatory reason;
  - acknowledgement of failed gates;
  - computed score preserved;
  - audit event persisted.
- Store or mirror:
  - `computed_score_at_decision`
  - `required_score`
  - `failed_gates`
  - `override_reason`
  - `decided_by`
  - `decision_type: accept_with_override`

### Acceptance

- Accept below target fails without `--override-readiness --reason`.
- Override does not mutate `computed_score`.
- Decision/audit record preserves readiness context at decision time.

## Phase 8 - MCP And Agent Skill Coverage

### Goals

Rendere agenti e client MCP readiness-aware senza concedere autonomia governance.

### Work

- Add MCP read tools:
  - `p2p_proposal_readiness_get`
  - `p2p_proposal_readiness_explain`
  - `p2p_proposal_readiness_refresh`
  - `p2p_proposal_readiness_list_gaps`
- Add governance-gated write tool only when permission model is explicit:
  - `p2p_proposal_accept_with_override`
- Update Codex skill and agent instructions:
  - inspect readiness before recommending acceptance;
  - reject thin artifacts as sufficient;
  - ask owner when `needs_owner_input`;
  - surface alternatives and tradeoffs;
  - distinguish score, confidence, gates, and override;
  - say when a proposal is not methodologically ready.

### Acceptance

- MCP read tools are safe for agents.
- MCP write/governance tools require explicit permission/consent.
- Skill instructions make agents more pedantic without letting them decide for
  the owner.

## Phase 9 - Migration And Legacy Handling

### Goals

Applicare readiness a nuove proposal e draft aperte senza riscrivere la storia.

### Work

- New proposals: readiness starts as `not_assessed`.
- Open drafts: mark `not_assessed`; `p2p next` can recommend refresh.
- Accepted proposals:
  - preserve decision;
  - optionally mark `accepted_before_readiness`;
  - optional retrospective assessment marked as retrospective.

### Acceptance

- Existing accepted proposals are not invalidated.
- Existing open drafts can be assessed progressively.
- No raw history rewrite is required.

## Phase 10 - Validation, Tests, Documentation

### Goals

Rendere il modello affidabile e verificabile.

### Work

- Validation:
  - schema/profile invalid -> error;
  - registry stale -> warning initially;
  - below threshold -> warning or policy gate;
  - failed gates -> block automatic `ready_for_decision`;
  - acceptance below threshold -> requires override reason.
- Tests:
  - profile load/validate;
  - readiness assessment parse/write;
  - artifact quality caps;
  - score aggregation;
  - gate failure;
  - confidence gate;
  - `not_assessed` migration;
  - `p2p next` readiness recommendations;
  - accept-with-override audit;
  - MCP read tools and permission-gated write behavior.
- Documentation:
  - CLI guide for readiness commands;
  - agent integration guidance;
  - MCP docs;
  - governance boundary notes;
  - examples for small and governance-critical proposals.

### Acceptance

- `p2p validate` reports malformed readiness profile/assessment.
- Test coverage exists for scoring, gates, next integration, and override.
- Docs explain readiness without implying automatic governance decisions.

## Suggested Change Sets

This proposal is large enough to split implementation into multiple Change Sets:

1. **Readiness Profile And Storage MVP**
   - domain models;
   - profile file;
   - readiness assessment read/write;
   - validation.

2. **Artifact Quality And Proposal Readiness CLI**
   - artifact quality states;
   - `p2p proposal readiness`;
   - refresh/explain;
   - score aggregation and caps.

3. **Readiness-Aware Next And Registry**
   - readiness registry snapshot;
   - stale detection;
   - `p2p next` gap actions.

4. **Governance Override And Legacy Migration**
   - accept-with-override;
   - audit record;
   - not_assessed migration;
   - legacy markers.

5. **MCP And Agent Skill Readiness Coverage**
   - MCP read tools;
   - permission-gated write path;
   - skill/docs updates.

## Rollout Notes

- Start advisory: warnings and `not_assessed` should not block existing work.
- Block only automatic `ready_for_decision` when failed gates are present.
- Owner acceptance below target requires explicit override reason.
- Keep historical accepted proposals stable.
- Treat readiness registry as generated cache and make staleness visible.

## Completion Criteria

PROP-002 implementation can be considered complete when:

- `default-readiness-v0.1` exists and validates.
- Draft proposals can be assessed or marked `not_assessed`.
- Readiness score, label, confidence, failed gates, and suggested next actions
  are visible through CLI.
- `p2p next` can recommend readiness-driven actions.
- Owner override is recorded during acceptance without falsifying computed
  score.
- Agent/MCP guidance prevents autonomous governance decisions.
- Validation and tests cover the core readiness workflow.

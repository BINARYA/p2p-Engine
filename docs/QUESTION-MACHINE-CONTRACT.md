# Bounded question CLI contract

The MS2 CLI slice uses `p2p-cli/v1` and the existing atomic writer. Existing
local text and unkeyed project-question JSON mutations remain compatible. New
keyed mutations require JSON, an operation key and the exact leaf capability.
External authority accepts root or exact capability-grant attestations; P2P
validates the trusted attestation rather than managing a grant database.

## Reads

```text
p2p project readiness questions status --format json --limit 20 --root ROOT
p2p project readiness questions next --format json --root ROOT
p2p proposal questions status PROP-001 --format json --limit 20 --offset 0 --root ROOT
p2p proposal questions list PROP-001 --format json --limit 20 --offset 0 --root ROOT
p2p proposal questions next PROP-001 --format json --root ROOT
```

`project readiness status/next` alias the bounded project-question views;
`review/gaps` retain readiness diagnostics. `data.question_page` uses
`p2p-question-page/v1` with `scope`, `proposal_id` (null for project), `items`
and `page`. Both page types have `limit`, `total`, `has_more`. Project pages use
snapshot-bound `next_cursor` and `--cursor`; proposal pages use `offset`,
`next_offset` and `--offset`. Optional `--state` uses canonical state names.

Items contain `id`, `revision`, `state`, `priority`, `question`, `rationale`,
`truncated_fields`. Project extras are `section_id`, `gap_id`, `applicability`,
`answer_contract` and `answer`. Answer contracts expose `kind`, `required_fields`,
`allowed_definition_operations` and optional `allowed_values`. Latest answers
are null or `{values, evidence_refs, provided_by, recorded_by}`. Proposal extras
are `group_id`, `gap`, string `answer`, `provided_by`, `recorded_by`, and
`application_effect` (`not_registered`/`plan_registered`). No histories, synthetic
questions or inferred eligibility are returned. `data.question_next` uses
`p2p-question-next/v1` with `scope`, `proposal_id` and null or identically
projected `question`.

Pages default 20, permit 1–100 and shrink to fit 48 KiB. Question/rationale/gap
text caps 2000 characters, answer strings 8000. Nested projections are bounded;
oversized answer values may be omitted with explicit `truncated_fields`.
Canonical values and history are never changed by truncation.

## Typed mutations

The commands below accept `--format json --operation-key KEY --actor SUBJECT
--executor EXECUTOR --executor-kind KIND --authority-context CONTEXT.json
--root ROOT`. Local callers may omit executor/context; executor defaults to
subject. Subject and executor are separately validated and recorded.

```text
project readiness questions answer PRQ-ID --expected-revision N --value TEXT
project readiness questions answer PRQ-ID --expected-revision N --input ANSWER.json
project readiness questions defer|mute|reopen PRQ-ID --expected-revision N --reason TEXT
proposal questions answer PROP-001 Q001 ANSWER --expected-revision N [--replace] [--source owner]
proposal questions defer|mute|reopen PROP-001 Q001 --expected-revision N [--reason TEXT]
proposal questions apply PROP-001 [--question Q001 ...]
```

Answer inputs have one strict wrapper:

```json
{"project_question_answer":{"schema_version":1,"question_id":"PRQ-ID","expected_revision":1,"values":{"value":"Owner answer"},"evidence_refs":[]}}
```

Values follow the actual question answer contract; evidence is optional.
Schema/revision are integers, ID/revision match argv, and typed inputs reject
unknown/duplicate keys. Files are regular, non-symlink, at most 64 KiB, without
parent traversal or symlinks in any path segment. Only keyed JSON with explicit
authority context permits trusted worker-staged input outside ROOT; legacy
input remains root-confined.

Answer/value/source/reason strings cap 8000 characters, evidence caps 32
references of 512 characters, selection caps 32 questions and request/result
JSON caps 48 KiB. Proposal apply only registers an artifact update plan in
questions.yml and reports `plan_registered`; it never changes proposal.md.

Exact capabilities are `project.question.answer/defer/mute/reopen/apply/reconcile`
and `proposal.question.answer/defer/mute/reopen/apply`. `proposal.decide` does not
authorize question mutations. Local use requires the declared owner.

## Convergence and reconciliation

```text
project readiness preview --question PRQ-ID ...
project readiness apply --question PRQ-ID ... --preview-token TOKEN --confirm
project readiness questions reconcile-preview
project readiness questions reconcile-apply --preview-token TOKEN --confirm
```

Typed previews use the same key/subject/executor/context as apply. They return
`data.question_preview` (`p2p-question-preview/v1`) with `scope`, target
`operation_id`, `effect`, `preview_token`, `question_ids`, `question_revisions`,
`apply_allowed`, `authority`. Tokens bind authority and existing plan sources.
Convergence applies definition plus question candidates together; reconciliation
changes only questions.yml.

## Durable outcomes

`data.question_mutation` uses `p2p-question-mutation-result/v1`, with `operation`,
`operation_id`, `scope`, `proposal_id`, `effect`, `question_ids`, `questions`.
Receipt operations are `project_question_<leaf>` or `proposal_question_<leaf>`;
operation IDs are actual dotted CLI paths, including
`project.readiness.questions.reconcile-apply`. Effects are `state_updated`,
`definition_applied`, `plan_registered`.

`data.authority` is existing evidence; `data.mutation` contains `status`
(`applied`/`already_applied`), `operation_id`, executor `actor`, `replayed`.
Exact replay returns immutable outcome before current authorization/revision
checks. Changed inputs conflict. Later writes may report `postcondition_drift`
without losing original result. Incomplete commits require existing recovery.

Worker command/key must exactly match CLI path/domain key. Canonical candidates,
mutation receipt and existing worker receipt/batch/revision commit in one
transaction. A missing durable worker outcome cannot report success.

Release inventory registers `question_page_contract`, `question_next_contract`,
`question_preview_contract`, `question_mutation_contract`. Hosted MCP typed
authority/receipt parity is explicitly deferred to MS3; existing local MCP
tools remain unchanged. Add/retire/init/import/group-state/supersede are not new
machine mutation surfaces in this slice.

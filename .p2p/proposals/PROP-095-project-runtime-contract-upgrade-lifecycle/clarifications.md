# Clarifications - PROP-095

## Q001 - Audit Policy

Confirmed runtime contract updates support a structured `--reason`. The first implementation requires `--reason` for updates classified as `range_tightening`, `runtime_line_change`, or `current_runtime_excluded`. It may keep `--reason` optional for `recommended_only` and `range_widening`.

PROP-095 should reuse a generic governed-change audit mechanism if one exists. If no canonical audit primitive exists, it must not invent a runtime-specific audit file. Historical audit remains Git or external workflow until a generic audit layer is available. In that case structured output reports `reason_persisted: false` and `audit_mode: external`.

## Q002 - Owner Authority

Confirmed runtime contract updates are owner-controlled. For the first CLI implementation, authority means the actor resolves to an owner role in the supported project permissions policy, plus explicit confirmation. Confirmation proves intent, but does not replace authority.

During the incompatible-range exception, the runtime may read only minimum supported authority state. If owner authority cannot be verified safely, the update remains blocked.

MCP mutation is out of scope for the first implementation. If a future MCP tool is added, it must extend the consent operation registry with `runtime_contract_update` or an equivalent bounded operation and use the PROP-066 consent receipt model.

Agents may prepare previews and commands, but must not confirm or execute the mutation without explicit owner mandate.

## Q003 - Agent Surface

JSON preview and JSON result output are required in the first implementation because the operation is agent-facing and mirrors the `runtime status` contract.

Structured output should include current requires/recommended, proposed requires/recommended, active runtime, impact labels, active-runtime compatibility after update, setup-guide state, release availability, files changed or planned, expected contract digest, expected setup guide digest, whether confirmation is required, reason persistence status, audit mode, and stable failure fields such as blocked reason or validation findings.

## Q004 - Impact Classification

The stable initial impact labels are:

- `recommended_only`
- `range_widening`
- `range_tightening`
- `runtime_line_change`
- `current_runtime_excluded`

Multiple labels may apply to the same update. The first implementation only performs deterministic range comparison for `==VERSION` and `>=LOWER,<UPPER`. A range shift that both adds and removes compatible versions may produce both `range_widening` and `range_tightening`.

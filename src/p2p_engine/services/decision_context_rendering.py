from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from p2p_engine.core.decision_context import (
    Activation,
    Authority,
    DecisionContextIndex,
    DecisionContextPacket,
    DecisionContextRelation,
    DecisionContextEvidence,
    NodeType,
    RetrievalHit,
)
from p2p_engine.services.decision_context_retrieval import budget_policy

DecisionContextPhase = Literal["intake", "explore", "impact", "synthesize"]

_AUTHORITATIVE_SYNTHESIS_AUTHORITIES = {
    Authority.ACCEPTED_DECISION,
    Authority.CONDITIONALLY_ACCEPTED_DECISION,
    Authority.DECIDED_PROJECT_CHOICE,
    Authority.EXPLICIT_DECISION_PRECEDENT,
    Authority.PROJECT_DEFINITION_CONSTRAINT,
    Authority.ACCEPTED_PROPOSAL_CONTEXT,
    Authority.OWNER_CONFIRMED_EVIDENCE,
}
_MAX_ITEM_CHARACTERS = 1_200


def render_nearby_decision_context(
    packet: DecisionContextPacket,
    *,
    phase: DecisionContextPhase,
    index: DecisionContextIndex | None = None,
    target_id: str = "",
) -> str:
    """Render only the evidence already selected by a bounded retrieval packet."""

    limit = budget_policy(packet.budget).max_serialized_bytes
    header = _header(packet, phase)
    blocks = [_hit_block(hit, packet.evidence, phase) for hit in packet.hits]
    if phase == "impact" and index is not None:
        blocks.extend(_impact_relation_blocks(packet, index, target_id))
    diagnostics = _diagnostic_block(packet)
    if diagnostics:
        blocks.append(diagnostics)
    return _fit_blocks(header, blocks, limit)


def _header(packet: DecisionContextPacket, phase: DecisionContextPhase) -> str:
    lines = [
        "## Nearby Decision Context",
        "",
        "This is read-only derived context. It may inform analysis but cannot record or change governance state.",
        "",
        f"- Phase: `{phase}`",
        f"- Budget: `{packet.budget.value}`",
        f"- Completeness: `{packet.completeness.value}`",
        f"- Retrieval policy: `{packet.retrieval_policy_version}`",
        f"- Budget policy: `{packet.budget_policy_version}`",
        f"- Source fingerprint: `{packet.source_fingerprint_sha256}`",
        f"- Semantic fingerprint: `{packet.semantic_fingerprint_sha256}`",
        f"- Truncated: `{str(packet.truncation.truncated).lower()}`",
        "",
    ]
    if not packet.hits:
        reason = packet.empty_reason or "insufficient evidence"
        lines.extend([f"No nearby context was selected: {reason}.", ""])
    return "\n".join(lines)


def _hit_block(
    hit: RetrievalHit,
    evidence: tuple[DecisionContextEvidence, ...],
    phase: DecisionContextPhase,
) -> str:
    lines = [
        f"### {hit.owner_id}",
        "",
        f"- Type: `{hit.owner_type.value}`",
        f"- Score: `{hit.score}`",
        f"- Activation: `{hit.activation.value}`",
        f"- Authority: `{hit.authority.value}`",
    ]
    if phase == "synthesize":
        lines.extend(_synthesis_payload(hit))
    else:
        lines.extend(_general_payload(hit, phase))
    lines.extend(_reason_lines(hit, phase))
    lines.extend(_evidence_lines(hit, evidence))
    lines.append("")
    return "\n".join(lines)


def _general_payload(hit: RetrievalHit, phase: DecisionContextPhase) -> list[str]:
    lines: list[str] = []
    if hit.activation == Activation.HISTORICAL:
        historical = hit.decisions + hit.constraints + hit.claims
        lines.extend(_item_lines("Historical alternative", historical))
        return lines
    lines.extend(_item_lines("Decision", hit.decisions))
    lines.extend(_item_lines("Constraint", hit.constraints))
    if phase in {"intake", "explore", "impact"}:
        lines.extend(_item_lines("Relevant claim", hit.claims))
    if phase == "explore":
        lines.extend(_item_lines("Scope boundary", hit.non_goals))
    return lines


def _synthesis_payload(hit: RetrievalHit) -> list[str]:
    if hit.activation == Activation.HISTORICAL:
        return _item_lines(
            "Historical alternative",
            hit.decisions + hit.constraints + hit.claims,
        )
    if hit.owner_type == NodeType.CHOICE and hit.authority == Authority.DECIDED_PROJECT_CHOICE:
        return _item_lines("Decided project choice", hit.decisions + hit.claims)
    if hit.authority in _AUTHORITATIVE_SYNTHESIS_AUTHORITIES:
        label = (
            "Qualified decision"
            if hit.authority == Authority.CONDITIONALLY_ACCEPTED_DECISION
            else "Accepted or authoritative decision"
        )
        return _item_lines(label, hit.decisions) + _item_lines("Binding constraint", hit.constraints)
    return _item_lines("Unresolved context signal", hit.constraints + hit.claims)


def _item_lines(label: str, values: Iterable[str]) -> list[str]:
    items = [_concise(value) for value in values if value.strip()]
    if not items:
        return []
    return [f"- {label}: {item}" for item in items]


def _reason_lines(hit: RetrievalHit, phase: DecisionContextPhase) -> list[str]:
    lines: list[str] = []
    for reason in hit.reasons:
        if reason.signal.startswith("heuristic_"):
            label = "Retrieval signal only; not a topology edge"
        elif phase == "impact":
            label = "Retrieval signal"
        else:
            label = "Selection reason"
        lines.append(
            f"- {label}: `{reason.signal}` ({reason.contribution:+d}) - {_concise(reason.detail)}"
        )
    return lines


def _evidence_lines(
    hit: RetrievalHit,
    evidence: tuple[DecisionContextEvidence, ...],
) -> list[str]:
    by_id = {item.evidence_id: item for item in evidence}
    lines: list[str] = []
    for evidence_id in hit.evidence_ids:
        item = by_id.get(evidence_id)
        if item is None:
            continue
        span = ""
        if item.span is not None:
            span = f":{item.span.start_line}-{item.span.end_line}"
        lines.append(
            "- Evidence: "
            f"`{item.source_path}{span}#{item.fragment_id}` "
            f"(authority `{item.authority.value}`, confidence `{item.confidence.value}`)"
        )
    return lines


def _impact_relation_blocks(
    packet: DecisionContextPacket,
    index: DecisionContextIndex,
    target_id: str,
) -> list[str]:
    relation_map = index.relation_map()
    selected_ids = {
        relation_id
        for hit in packet.hits
        for relation_id in hit.selected_relation_ids
    }
    if target_id:
        direct_ids = set(index.incoming_relations.get(target_id, ()))
        direct_ids.update(index.outgoing_relations.get(target_id, ()))
        domain_types = {
            NodeType.CAPABILITY,
            NodeType.SURFACE,
            NodeType.FEATURE,
            NodeType.COMMAND,
            NodeType.FILE,
            NodeType.VERTICAL_SECTION,
        }
        for relation_id in sorted(direct_ids):
            relation = relation_map.get(relation_id)
            if relation is not None and (
                relation.source_type in domain_types or relation.target_type in domain_types
            ):
                selected_ids.add(relation_id)
    max_relations = budget_policy(packet.budget).max_relations
    relations = sorted(
        (relation_map[relation_id] for relation_id in selected_ids if relation_id in relation_map),
        key=lambda item: (
            item.source_id,
            item.relation_type.value,
            item.target_id,
            item.relation_id,
        ),
    )[:max_relations]
    if not relations:
        return []
    lines = [
        "### Normalized Relation Candidates",
        "",
        "Only explicit normalized relations selected by retrieval are listed here. Heuristic signals above are not edges.",
        "",
    ]
    for relation in relations:
        lines.append(_relation_line(relation, index))
    lines.append("")
    return ["\n".join(lines)]


def _relation_line(relation: DecisionContextRelation, index: DecisionContextIndex) -> str:
    state = "active conflict" if (
        relation.relation_type.value in {"conflicts_with", "blocks"}
        and relation.activation == Activation.ACTIVE
    ) else "relation candidate"
    evidence_map = index.evidence_map()
    evidence_refs = [
        f"{item.source_path}#{item.fragment_id}"
        for evidence_id in relation.evidence_ids
        if (item := evidence_map.get(evidence_id)) is not None
    ]
    evidence = f"; evidence `{', '.join(evidence_refs)}`" if evidence_refs else ""
    return (
        f"- {state}: `{relation.source_id}` --`{relation.relation_type.value}`--> "
        f"`{relation.target_id}`; scope `{relation.scope}`; activation "
        f"`{relation.activation.value}`; authority `{relation.authority.value}`; "
        f"confidence `{relation.confidence.value}`{evidence}"
    )


def _diagnostic_block(packet: DecisionContextPacket) -> str:
    if not packet.diagnostics:
        return ""
    lines = ["### Bounded Diagnostics", ""]
    for diagnostic in packet.diagnostics:
        lines.append(
            f"- `{diagnostic.code}` ({diagnostic.severity.value}): {_concise(diagnostic.message)}"
        )
    lines.append("")
    return "\n".join(lines)


def _fit_blocks(header: str, blocks: list[str], max_bytes: int) -> str:
    rendered = header
    omitted = 0
    for block in blocks:
        candidate = rendered + block
        if len(candidate.encode("utf-8")) <= max_bytes:
            rendered = candidate
        else:
            omitted += 1
    if omitted:
        note = f"\n- Rendering omitted {omitted} lower-priority block(s) to stay within budget.\n"
        if len((rendered + note).encode("utf-8")) <= max_bytes:
            rendered += note
    return rendered.rstrip() + "\n"


def _concise(value: str) -> str:
    compact = " ".join(value.split())
    if len(compact) <= _MAX_ITEM_CHARACTERS:
        return compact
    return compact[: _MAX_ITEM_CHARACTERS - 3].rstrip() + "..."

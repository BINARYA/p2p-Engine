from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass

from p2p_engine.core.decision_context import (
    Activation,
    Authority,
    Canonicality,
    Completeness,
    Confidence,
    DecisionContextDiagnostic,
    DecisionContextEvidence,
    DecisionContextNode,
    DecisionContextRecord,
    DecisionContextRelation,
    DiagnosticSeverity,
    ExtractionSession,
    NodeType,
    RecordKind,
    SourceDocument,
    SourceKind,
    SourcePresence,
)
from p2p_engine.services.decision_context_sources import fragments_for_label
from p2p_engine.services.decision_context_ledger import (
    DecisionContextLedgerExtractor,
    proposal_authority,
)


_LIST_ITEM_RE = re.compile(r"^(?:[-*+] |[0-9]+[.)] )(.*)$")
@dataclass(frozen=True)
class ExtractedDecisionContext:
    completeness: Completeness
    records: tuple[DecisionContextRecord, ...]
    evidence: tuple[DecisionContextEvidence, ...]
    nodes: tuple[DecisionContextNode, ...]
    relations: tuple[DecisionContextRelation, ...]
    diagnostics: tuple[DecisionContextDiagnostic, ...]


class DecisionContextExtractorService:
    def extract_proposals_and_decisions(self, session: ExtractionSession) -> ExtractedDecisionContext:
        diagnostics = list(session.diagnostics)
        records: list[DecisionContextRecord] = []
        evidence: list[DecisionContextEvidence] = []
        nodes: list[DecisionContextNode] = []
        relations: list[DecisionContextRelation] = []
        documents_by_owner: dict[str, dict[SourceKind, SourceDocument]] = defaultdict(dict)
        for document in session.sources:
            documents_by_owner[document.owner_id][document.source_kind] = document

        for owner_id in sorted(documents_by_owner):
            owner_documents = documents_by_owner[owner_id]
            proposal_document = owner_documents.get(SourceKind.PROPOSAL_BODY)
            decision_document = owner_documents.get(SourceKind.PROPOSAL_DECISION)
            ledger_document = owner_documents.get(
                SourceKind.PROPOSAL_DECISION_LEDGER
            )
            if proposal_document is None or proposal_document.presence != SourcePresence.PRESENT:
                continue
            title = _document_title(proposal_document) or owner_id
            nodes.append(DecisionContextNode(node_id=owner_id, node_type=NodeType.PROPOSAL, label=title))

            ledger_context = None
            if (
                ledger_document is not None
                and ledger_document.presence == SourcePresence.PRESENT
            ):
                ledger_context = DecisionContextLedgerExtractor().extract(
                    ledger_document,
                    decision_projection=decision_document,
                    related_record_ids=(),
                )
                diagnostics.extend(ledger_context.diagnostics)

            if ledger_context is not None and ledger_context.lifecycle is not None:
                proposal_authority_value, proposal_activation = proposal_authority(
                    ledger_context.lifecycle
                )
            else:
                proposal_authority_value = Authority.DRAFT_PROPOSAL
                proposal_activation = Activation.EXPLORATORY
                diagnostics.append(
                    _diagnostic(
                        code="DC-AUTHORITY-CURRENT-DECISION-LEDGER-REQUIRED",
                        severity=DiagnosticSeverity.ERROR,
                        message="Current proposal authority requires a valid decision-events.yml ledger.",
                        source_path=(
                            ledger_document.path
                            if ledger_document is not None
                            else f".p2p/proposals/{owner_id}/decision-events.yml"
                        ),
                        target_id=owner_id,
                        recovery="Recreate or repair the proposal through current decision commands.",
                    )
                )

            proposal_records, proposal_evidence, proposal_diagnostics = self._extract_proposal(
                proposal_document,
                authority=proposal_authority_value,
                activation=proposal_activation,
            )
            records.extend(proposal_records)
            evidence.extend(proposal_evidence)
            diagnostics.extend(proposal_diagnostics)
            if ledger_context is not None and ledger_context.lifecycle is not None:
                ledger_context = DecisionContextLedgerExtractor().extract(
                    ledger_document,
                    decision_projection=decision_document,
                    related_record_ids=tuple(
                        record.record_id
                        for record in proposal_records
                        if record.kind != RecordKind.PROPOSAL_STATE
                    ),
                )
                records.extend(ledger_context.records)
                evidence.extend(ledger_context.evidence)
                nodes.extend(ledger_context.nodes)
                relations.extend(ledger_context.relations)

        records.sort(key=lambda item: (item.owner_type.value, item.owner_id, item.kind.value, item.record_id))
        evidence.sort(key=lambda item: (item.source_path, item.fragment_id, item.evidence_id))
        nodes.sort(key=lambda item: (item.node_type.value, item.node_id))
        relations.sort(
            key=lambda item: (
                item.source_type.value,
                item.source_id,
                item.relation_type.value,
                item.target_type.value,
                item.target_id,
                item.relation_id,
            )
        )
        diagnostics = _deduplicate_diagnostics(diagnostics)
        completeness = _extraction_completeness(session.completeness, diagnostics, records)
        return ExtractedDecisionContext(
            completeness=completeness,
            records=tuple(records),
            evidence=tuple(evidence),
            nodes=tuple(nodes),
            relations=tuple(relations),
            diagnostics=tuple(diagnostics),
        )

    def _extract_proposal(
        self,
        document: SourceDocument,
        *,
        authority: Authority,
        activation: Activation,
    ) -> tuple[list[DecisionContextRecord], list[DecisionContextEvidence], list[DecisionContextDiagnostic]]:
        records: list[DecisionContextRecord] = []
        evidence: list[DecisionContextEvidence] = []
        diagnostics: list[DecisionContextDiagnostic] = []
        section_contract = (
            ("Problem", RecordKind.PROBLEM, False, True),
            ("Goals", RecordKind.GOAL, True, False),
            ("Non-Goals", RecordKind.NON_GOAL, True, False),
            ("Proposal", RecordKind.PROPOSAL_CLAIM, False, True),
            ("Acceptance Criteria", RecordKind.ACCEPTANCE_CRITERION, True, False),
        )
        for label, kind, split_list, required in section_contract:
            fragments = fragments_for_label(document, label)
            if not fragments and required:
                diagnostics.append(
                    _diagnostic(
                        code="DC-SOURCE-MISSING-SECTION",
                        severity=DiagnosticSeverity.WARNING,
                        message=f"Proposal is missing required section {label!r}.",
                        source_path=document.path,
                        target_id=document.owner_id,
                        recovery=f"Add the {label} section through a supported proposal workflow.",
                    )
                )
                continue
            for fragment in fragments:
                values = _split_top_level_items(fragment.text) if split_list else (fragment.text.strip(),)
                for item_index, text in enumerate(values, start=1):
                    if _is_placeholder(text):
                        continue
                    fragment_id = fragment.fragment_id if len(values) == 1 else f"{fragment.fragment_id}:item:{item_index}"
                    item_evidence = _evidence(
                        document,
                        fragment_id=fragment_id,
                        fragment_label=fragment.label,
                        authority=authority,
                        activation=activation,
                        completeness=fragment.completeness,
                        span=fragment.span,
                    )
                    evidence.append(item_evidence)
                    records.append(
                        _record(
                            owner_id=document.owner_id,
                            source_kind=document.source_kind,
                            kind=kind,
                            fragment_id=fragment_id,
                            activation=activation,
                            authority=authority,
                            text=text,
                            evidence_ids=(item_evidence.evidence_id,),
                        )
                    )

        status_fragments = fragments_for_label(document, "Status")
        if status_fragments:
            status_fragment = status_fragments[0]
            status_text = _normalize_status(status_fragment.text)
            if status_text:
                status_evidence = _evidence(
                    document,
                    fragment_id=status_fragment.fragment_id,
                    fragment_label=status_fragment.label,
                    authority=authority,
                    activation=activation,
                    completeness=status_fragment.completeness,
                    span=status_fragment.span,
                )
                evidence.append(status_evidence)
                records.append(
                    _record(
                        owner_id=document.owner_id,
                        source_kind=document.source_kind,
                        kind=RecordKind.PROPOSAL_STATE,
                        fragment_id=status_fragment.fragment_id,
                        activation=activation,
                        authority=authority,
                        text=status_text,
                        evidence_ids=(status_evidence.evidence_id,),
                    )
                )
        return records, evidence, diagnostics



def _evidence(
    document: SourceDocument,
    *,
    fragment_id: str,
    fragment_label: str,
    authority: Authority,
    activation: Activation,
    completeness: Completeness,
    span: object,
) -> DecisionContextEvidence:
    evidence_id = _stable_id("dce", document.owner_id, document.source_kind.value, fragment_id)
    return DecisionContextEvidence(
        evidence_id=evidence_id,
        source_path=document.path,
        source_sha256=document.sha256 or "",
        source_kind=document.source_kind,
        fragment_id=fragment_id,
        fragment_label=fragment_label,
        span=span,
        canonicality=Canonicality.CANONICAL,
        authority=authority,
        activation=activation,
        confidence=Confidence.EXPLICIT,
        completeness=completeness,
    )


def _record(
    *,
    owner_id: str,
    source_kind: SourceKind,
    kind: RecordKind,
    fragment_id: str,
    activation: Activation,
    authority: Authority,
    text: str,
    evidence_ids: tuple[str, ...],
    related_record_ids: tuple[str, ...] = (),
    canonical_date: str = "",
) -> DecisionContextRecord:
    return DecisionContextRecord(
        record_id=_stable_id("dcr", owner_id, source_kind.value, kind.value, fragment_id),
        kind=kind,
        owner_type=NodeType.PROPOSAL,
        owner_id=owner_id,
        activation=activation,
        authority=authority,
        text=text.strip(),
        text_sha256=hashlib.sha256(text.strip().encode("utf-8")).hexdigest(),
        evidence_ids=evidence_ids,
        related_record_ids=related_record_ids,
        canonical_date=canonical_date,
    )




def _section_value(document: SourceDocument, label: str) -> str:
    fragments = fragments_for_label(document, label)
    if not fragments:
        return ""
    return fragments[0].text.strip().strip("`").strip()


def _mapping_text(values: object, key: str) -> str:
    if not hasattr(values, "get"):
        return ""
    value = values.get(key, "")
    return str(value or "").strip()


def _normalize_status(value: str) -> str:
    normalized = value.strip().strip("`").lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"_+", "_", normalized)


def _document_title(document: SourceDocument) -> str:
    if document._content is None:
        return ""
    try:
        text = document._content.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    first_heading = next((line.strip()[2:].strip() for line in text.splitlines() if line.startswith("# ")), "")
    if " - " in first_heading:
        return first_heading.split(" - ", 1)[1].strip()
    return first_heading


def _split_top_level_items(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    items: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line and not line[0].isspace():
            match = _LIST_ITEM_RE.match(line)
        else:
            match = None
        if match:
            if current:
                items.append(current)
            current = [match.group(1).strip()]
        elif current:
            current.append(line.rstrip())
    if current:
        items.append(current)
    if not items:
        stripped = text.strip()
        return (stripped,) if stripped else ()
    return tuple("\n".join(item).strip() for item in items if "\n".join(item).strip())


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in {"", "pending.", "pending", "none.", "none", "not provided."}


def _stable_id(prefix: str, *parts: str) -> str:
    readable = ":".join(part.strip().lower().replace(" ", "-") for part in parts)
    digest = hashlib.sha256(readable.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


def _diagnostic(
    *,
    code: str,
    severity: DiagnosticSeverity,
    message: str,
    source_path: str,
    target_id: str,
    recovery: str,
) -> DecisionContextDiagnostic:
    identity = "|".join((code, source_path, target_id, message))
    return DecisionContextDiagnostic(
        diagnostic_id=f"dcd:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}",
        code=code,
        severity=severity,
        fatal=False,
        message=message,
        source_path=source_path,
        target_id=target_id,
        recovery=recovery,
    )


def _deduplicate_diagnostics(
    diagnostics: list[DecisionContextDiagnostic],
) -> list[DecisionContextDiagnostic]:
    by_id = {item.diagnostic_id: item for item in diagnostics}
    return sorted(by_id.values(), key=lambda item: (item.source_path, item.code, item.fragment_id, item.diagnostic_id))


def _extraction_completeness(
    session_completeness: Completeness,
    diagnostics: list[DecisionContextDiagnostic],
    records: list[DecisionContextRecord],
) -> Completeness:
    if session_completeness == Completeness.UNAVAILABLE or any(item.fatal for item in diagnostics):
        return Completeness.UNAVAILABLE
    if not records:
        return Completeness.UNAVAILABLE
    if session_completeness == Completeness.PARTIAL:
        return Completeness.PARTIAL
    if any(item.severity in {DiagnosticSeverity.WARNING, DiagnosticSeverity.ERROR} for item in diagnostics):
        return Completeness.PARTIAL
    return Completeness.COMPLETE

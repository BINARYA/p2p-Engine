from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from p2p_engine.core.decision_context import (
    AUTHORITY_RANK,
    Activation,
    Authority,
    Canonicality,
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
    RelationType,
    SourceDocument,
    SourceKind,
    SourcePresence,
)
from p2p_engine.services.decision_context_authority import AuthorityPolicy, SourceMetadataResolver
from p2p_engine.services.decision_context_sources import fragments_for_label

_RELATION_TYPES: Mapping[str, RelationType] = {
    item.value: item for item in RelationType
}
_AMBIGUOUS_RELATION_TERMS = frozenset({"enables", "informs", "constrained_by"})
_AMBIGUOUS_RELATION_MEANINGS: Mapping[str, tuple[str, ...]] = {
    "enables": ("depends_on (reverse direction)", "references"),
    "informs": ("references", "depends_on"),
    "constrained_by": ("depends_on", "project constraint evidence"),
}
_SYMMETRIC_RELATIONS = frozenset({RelationType.CONFLICTS_WITH})
_ACTIVATION_RANK: Mapping[Activation, int] = {
    Activation.ACTIVE: 5,
    Activation.EXPLORATORY: 4,
    Activation.UNRESOLVED: 3,
    Activation.HISTORICAL: 2,
    Activation.INACTIVE: 1,
}
_CONFIDENCE_RANK: Mapping[Confidence, int] = {
    Confidence.EXPLICIT: 4,
    Confidence.INFERRED: 3,
    Confidence.HEURISTIC: 2,
    Confidence.UNKNOWN: 1,
}
_IDENTITY_TYPES = frozenset(
    {NodeType.PROPOSAL, NodeType.DECISION, NodeType.CHOICE, NodeType.CHANGE, NodeType.WORK}
)
_VALUE_RELATIONS: Mapping[str, tuple[NodeType, RelationType]] = {
    "capabilities": (NodeType.CAPABILITY, RelationType.AFFECTS_CAPABILITY),
    "capability": (NodeType.CAPABILITY, RelationType.AFFECTS_CAPABILITY),
    "surfaces": (NodeType.SURFACE, RelationType.AFFECTS_SURFACE),
    "surface": (NodeType.SURFACE, RelationType.AFFECTS_SURFACE),
    "features": (NodeType.FEATURE, RelationType.AFFECTS_FEATURE),
    "feature": (NodeType.FEATURE, RelationType.AFFECTS_FEATURE),
    "commands": (NodeType.COMMAND, RelationType.TOUCHES_COMMAND),
    "command": (NodeType.COMMAND, RelationType.TOUCHES_COMMAND),
    "files": (NodeType.FILE, RelationType.TOUCHES_FILE),
    "file": (NodeType.FILE, RelationType.TOUCHES_FILE),
}
_GOVERNANCE_ALLOWLIST: Mapping[str, frozenset[str]] = {
    "constitution.md": frozenset({"purpose", "principles"}),
    "decision-rules.md": frozenset({"default-mode", "ai-constraint", "acceptance-criteria"}),
    "relevance-criteria.md": frozenset({"relevance-classes"}),
}


@dataclass(frozen=True)
class NormalizedDecisionContext:
    records: tuple[DecisionContextRecord, ...]
    evidence: tuple[DecisionContextEvidence, ...]
    nodes: tuple[DecisionContextNode, ...]
    relations: tuple[DecisionContextRelation, ...]
    diagnostics: tuple[DecisionContextDiagnostic, ...]


@dataclass(frozen=True)
class TraversalStep:
    node_id: str
    relation_ids: tuple[str, ...]
    depth: int


@dataclass(frozen=True)
class _RelationAssertion:
    source_id: str
    source_type: NodeType
    target_id: str
    target_type: NodeType
    relation_type: RelationType
    scope: str
    activation: Activation
    authority: Authority
    confidence: Confidence
    evidence_id: str
    diagnostic_ids: tuple[str, ...] = ()


class DecisionContextTopologyService:
    def normalize(
        self,
        session: ExtractionSession,
        *,
        base_records: Sequence[DecisionContextRecord] = (),
        base_nodes: Sequence[DecisionContextNode] = (),
    ) -> NormalizedDecisionContext:
        documents = tuple(
            document for document in session.sources if document.presence == SourcePresence.PRESENT
        )
        artifact_states = {
            document.owner_id: document
            for document in documents
            if document.source_kind == SourceKind.ARTIFACT_STATE
        }
        metadata_resolver = SourceMetadataResolver(artifact_states)
        policy = AuthorityPolicy()
        nodes: dict[tuple[NodeType, str], DecisionContextNode] = {
            (node.node_type, node.node_id): node for node in base_nodes
        }
        records: list[DecisionContextRecord] = []
        evidence: dict[str, DecisionContextEvidence] = {}
        assertions: list[_RelationAssertion] = []
        diagnostics: list[DecisionContextDiagnostic] = []
        base_owner_state = _owner_state(base_records)

        self._catalog_identity_nodes(documents, nodes)
        known_nodes = set(nodes)

        def source_evidence(document: SourceDocument, pointer: str) -> DecisionContextEvidence:
            default = policy.source_default(document)
            resolved = metadata_resolver.resolve(document, default)
            owner_activation, owner_authority = base_owner_state.get(
                document.owner_id, (resolved.activation, resolved.authority)
            )
            activation = owner_activation if document.classification.value == "governed_artifact_evidence" else resolved.activation
            authority = resolved.authority
            if document.classification.value == "governed_artifact_evidence" and authority == Authority.SYSTEM_STATE:
                authority = owner_authority
            item = _evidence(document, pointer, resolved.canonicality, authority, activation, resolved.confidence)
            evidence[item.evidence_id] = item
            return item

        self._extract_project_records(
            documents,
            nodes,
            known_nodes,
            records,
            evidence,
            assertions,
            diagnostics,
            source_evidence,
        )
        self._extract_quality_and_execution_records(documents, records, evidence, source_evidence)
        self._normalize_change_and_work(
            documents, nodes, known_nodes, assertions, diagnostics, source_evidence
        )
        self._normalize_related_proposals(
            documents, known_nodes, assertions, diagnostics, source_evidence
        )
        self._normalize_impacts(documents, nodes, assertions, diagnostics, source_evidence)
        self._normalize_conflicts(documents, known_nodes, assertions, diagnostics, source_evidence)
        self._normalize_choices(documents, known_nodes, assertions, diagnostics, source_evidence)
        self._normalize_vertical_coverage(documents, nodes, assertions, diagnostics, source_evidence)

        diagnostics.extend(_incompatible_assertion_diagnostics(assertions))
        relations = _merge_assertions(assertions)
        records.sort(key=lambda item: (item.owner_type.value, item.owner_id, item.kind.value, item.record_id))
        ordered_nodes = tuple(sorted(nodes.values(), key=lambda item: (item.node_type.value, item.node_id)))
        ordered_evidence = tuple(sorted(evidence.values(), key=lambda item: (item.source_path, item.fragment_id, item.evidence_id)))
        ordered_diagnostics = tuple(_deduplicate_diagnostics(diagnostics))
        return NormalizedDecisionContext(
            records=tuple(records),
            evidence=ordered_evidence,
            nodes=ordered_nodes,
            relations=relations,
            diagnostics=ordered_diagnostics,
        )

    @staticmethod
    def _catalog_identity_nodes(
        documents: Sequence[SourceDocument],
        nodes: dict[tuple[NodeType, str], DecisionContextNode],
    ) -> None:
        kinds = {
            SourceKind.PROPOSAL_BODY: NodeType.PROPOSAL,
            SourceKind.PROPOSAL_DECISION: NodeType.DECISION,
            SourceKind.PROPOSAL_DECISION_LEDGER: NodeType.DECISION,
            SourceKind.PROJECT_CHOICE: NodeType.CHOICE,
            SourceKind.CHANGE_SET: NodeType.CHANGE,
            SourceKind.WORK_MANIFEST: NodeType.WORK,
        }
        for document in documents:
            node_type = kinds.get(document.source_kind)
            if node_type is None:
                continue
            node_id = f"decision:{document.owner_id}" if node_type == NodeType.DECISION else document.owner_id
            label = _document_title(document) or node_id
            nodes.setdefault((node_type, node_id), DecisionContextNode(node_id, node_type, label))

    @staticmethod
    def _extract_project_records(
        documents: Sequence[SourceDocument],
        nodes: dict[tuple[NodeType, str], DecisionContextNode],
        known_nodes: set[tuple[NodeType, str]],
        records: list[DecisionContextRecord],
        evidence: dict[str, DecisionContextEvidence],
        assertions: list[_RelationAssertion],
        diagnostics: list[DecisionContextDiagnostic],
        source_evidence: object,
    ) -> None:
        for document in documents:
            if document.source_kind == SourceKind.DECISION_PRECEDENTS:
                for index, item in enumerate(_mapping_items(document.frontmatter.get("precedents"))):
                    precedent_id = _first_text(item, "id") or f"precedent-{index + 1}"
                    node_id = f"precedent:{precedent_id}"
                    text = _first_text(item, "decision", "statement", "precedent", "title", "reason")
                    if not text:
                        continue
                    pointer = f"yaml:/precedents/{index}"
                    item_evidence = source_evidence(document, pointer)
                    applicability = tuple(
                        sorted(
                            [f"proposal:{value}" for value in _precedent_refs(item, "proposal", "proposals", "related_proposals")]
                            + [f"choice:{value}" for value in _precedent_refs(item, "choice", "choices", "related_choices")]
                            + [f"tag:{value}" for value in _precedent_refs(item, "tag", "tags")]
                        )
                    )
                    nodes.setdefault(
                        (NodeType.DECISION, node_id),
                        DecisionContextNode(node_id, NodeType.DECISION, text, existence="declared"),
                    )
                    known_nodes.add((NodeType.DECISION, node_id))
                    records.append(
                        _record(
                            document,
                            pointer,
                            RecordKind.PRECEDENT,
                            NodeType.DECISION,
                            node_id,
                            text,
                            item_evidence,
                            authority=Authority.EXPLICIT_DECISION_PRECEDENT,
                            activation=Activation.ACTIVE,
                            applicability_tokens=applicability,
                        )
                    )
                    for target_type, prefix, keys in (
                        (NodeType.PROPOSAL, "proposal", ("proposal", "proposals", "related_proposals")),
                        (NodeType.CHOICE, "choice", ("choice", "choices", "related_choices")),
                    ):
                        for ref_index, target_id in enumerate(_precedent_refs(item, *keys)):
                            _append_relation(
                                assertions,
                                diagnostics,
                                source_id=node_id,
                                source_type=NodeType.DECISION,
                                target_id=target_id,
                                target_type=target_type,
                                relation_type=RelationType.REFERENCES,
                                scope="precedent_applicability",
                                item_evidence=source_evidence(
                                    document, f"{pointer}/{prefix}/{ref_index}"
                                ),
                                known_nodes=known_nodes,
                            )
            elif document.source_kind == SourceKind.GOVERNANCE_CONSTRAINT:
                allowed = _GOVERNANCE_ALLOWLIST.get(document.path.rsplit("/", 1)[-1], frozenset())
                for fragment in document.fragments:
                    if fragment.anchor not in allowed or not fragment.text.strip():
                        continue
                    item_evidence = source_evidence(document, fragment.fragment_id)
                    records.append(
                        _record(
                            document,
                            fragment.fragment_id,
                            RecordKind.CONSTRAINT,
                            NodeType.DECISION,
                            "PROJECT",
                            fragment.text.strip(),
                            item_evidence,
                            authority=Authority.PROJECT_DEFINITION_CONSTRAINT,
                            activation=Activation.ACTIVE,
                        )
                    )
            elif document.source_kind == SourceKind.PROJECT_DEFINITION:
                for pointer, text in _project_definition_values(document.frontmatter):
                    item_evidence = source_evidence(document, pointer)
                    records.append(
                        _record(
                            document,
                            pointer,
                            RecordKind.CONSTRAINT,
                            NodeType.DECISION,
                            "PROJECT",
                            text,
                            item_evidence,
                            authority=Authority.PROJECT_DEFINITION_CONSTRAINT,
                            activation=Activation.ACTIVE,
                        )
                    )
            elif document.source_kind == SourceKind.PROJECT_CHOICE_DECISION:
                status = _section_text(document, "Status").strip("` ").casefold()
                if status != "decided":
                    continue
                selected = _section_text(document, "Selected Option") or _section_text(document, "Outcome")
                reason = _section_text(document, "Reason")
                for label, kind, text in (
                    ("selected-option", RecordKind.DECISION_STATE, selected),
                    ("reason", RecordKind.DECISION_REASON, reason),
                ):
                    if not text:
                        continue
                    item_evidence = source_evidence(document, f"section:{label}:1")
                    records.append(
                        _record(
                            document,
                            f"section:{label}:1",
                            kind,
                            NodeType.CHOICE,
                            document.owner_id,
                            text,
                            item_evidence,
                            authority=Authority.DECIDED_PROJECT_CHOICE,
                            activation=Activation.ACTIVE,
                        )
                    )
            elif document.source_kind == SourceKind.PROJECT_CHOICE_LIFECYCLE:
                lifecycle = document.frontmatter.get("choice_lifecycle")
                if not isinstance(lifecycle, Mapping):
                    continue
                state = str(lifecycle.get("state") or "").strip().casefold()
                if state not in {"open", "decided", "withdrawn", "superseded"}:
                    continue
                item_evidence = source_evidence(document, "yaml:/choice_lifecycle/state")
                records.append(
                    _record(
                        document,
                        "yaml:/choice_lifecycle/state",
                        RecordKind.DECISION_STATE,
                        NodeType.CHOICE,
                        document.owner_id,
                        state,
                        item_evidence,
                        authority=Authority.SYSTEM_STATE,
                        activation=(
                            Activation.ACTIVE if state == "open" else Activation.HISTORICAL
                        ),
                    )
                )

    @staticmethod
    def _extract_quality_and_execution_records(
        documents: Sequence[SourceDocument],
        records: list[DecisionContextRecord],
        evidence: dict[str, DecisionContextEvidence],
        source_evidence: object,
    ) -> None:
        quality_kinds = {
            SourceKind.ARTIFACT_STATE,
            SourceKind.READINESS,
            SourceKind.QUESTIONS,
            SourceKind.CONTRIBUTIONS,
            SourceKind.PROJECT_QUESTIONS,
        }
        for document in documents:
            if document.source_kind in quality_kinds:
                summaries = _quality_summaries(document)
                for pointer, text, activation in summaries:
                    item_evidence = source_evidence(document, pointer)
                    owner_type = (
                        NodeType.DECISION
                        if document.source_kind == SourceKind.PROJECT_QUESTIONS
                        else NodeType.PROPOSAL
                    )
                    records.append(
                        _record(
                            document,
                            pointer,
                            RecordKind.EVENT,
                            owner_type,
                            document.owner_id,
                            text,
                            item_evidence,
                            authority=item_evidence.authority,
                            activation=activation,
                        )
                    )
            elif document.source_kind == SourceKind.WORK_MANIFEST:
                status = str(document.frontmatter.get("status") or "unknown").strip()
                item_evidence = source_evidence(document, "yaml:/status")
                records.append(
                    _record(
                        document,
                        "yaml:/status",
                        RecordKind.EXECUTION_STATE,
                        NodeType.WORK,
                        document.owner_id,
                        status,
                        item_evidence,
                        authority=Authority.SYSTEM_STATE,
                        activation=Activation.ACTIVE,
                    )
                )

    @staticmethod
    def _normalize_change_and_work(
        documents: Sequence[SourceDocument],
        nodes: dict[tuple[NodeType, str], DecisionContextNode],
        known_nodes: set[tuple[NodeType, str]],
        assertions: list[_RelationAssertion],
        diagnostics: list[DecisionContextDiagnostic],
        source_evidence: object,
    ) -> None:
        changes: dict[str, list[SourceDocument]] = defaultdict(list)
        for document in documents:
            if document.source_kind in {SourceKind.CHANGE_SET, SourceKind.CHANGE_RELATIONS}:
                changes[document.owner_id].append(document)
        for change_id, change_documents in sorted(changes.items()):
            frontmatter_included: set[str] = set()
            companion_included: set[str] = set()
            companion_present = False
            for document in sorted(change_documents, key=lambda item: item.path):
                filename = document.path.rsplit("/", 1)[-1]
                if document.source_kind == SourceKind.CHANGE_SET:
                    source = document.frontmatter.get("source")
                    values = source.get("accepted_proposals") if isinstance(source, Mapping) else ()
                    for index, proposal_id in enumerate(_string_values(values)):
                        frontmatter_included.add(proposal_id)
                        _append_relation(
                            assertions,
                            diagnostics,
                            source_id=change_id,
                            source_type=NodeType.CHANGE,
                            target_id=proposal_id,
                            target_type=NodeType.PROPOSAL,
                            relation_type=RelationType.INCLUDES,
                            scope="change_lineage",
                            item_evidence=source_evidence(document, f"frontmatter:/source/accepted_proposals/{index}"),
                            known_nodes=known_nodes,
                        )
                elif filename == "included-proposals.yml":
                    companion_present = True
                    for index, proposal_id in enumerate(_string_values(document.frontmatter.get("included_proposals"))):
                        companion_included.add(proposal_id)
                        _append_relation(
                            assertions,
                            diagnostics,
                            source_id=change_id,
                            source_type=NodeType.CHANGE,
                            target_id=proposal_id,
                            target_type=NodeType.PROPOSAL,
                            relation_type=RelationType.INCLUDES,
                            scope="change_lineage",
                            item_evidence=source_evidence(document, f"yaml:/included_proposals/{index}"),
                            known_nodes=known_nodes,
                        )
                elif filename == "referenced-proposals.yml":
                    for index, proposal_id in enumerate(_string_values(document.frontmatter.get("referenced_proposals"))):
                        _append_relation(
                            assertions,
                            diagnostics,
                            source_id=change_id,
                            source_type=NodeType.CHANGE,
                            target_id=proposal_id,
                            target_type=NodeType.PROPOSAL,
                            relation_type=RelationType.REFERENCES,
                            scope="change_lineage",
                            item_evidence=source_evidence(document, f"yaml:/referenced_proposals/{index}"),
                            known_nodes=known_nodes,
                        )
                elif filename == "included-decisions.yml":
                    for index, item in enumerate(_mapping_items(document.frontmatter.get("included_decisions"))):
                        proposal_id = _first_text(item, "proposal", "proposal_id", "id")
                        if not proposal_id:
                            continue
                        target_id = f"decision:{proposal_id}"
                        _append_relation(
                            assertions,
                            diagnostics,
                            source_id=change_id,
                            source_type=NodeType.CHANGE,
                            target_id=target_id,
                            target_type=NodeType.DECISION,
                            relation_type=RelationType.INCLUDES,
                            scope="change_decisions",
                            item_evidence=source_evidence(document, f"yaml:/included_decisions/{index}"),
                            known_nodes=known_nodes,
                        )
            if companion_present and frontmatter_included != companion_included:
                diagnostics.append(
                    _diagnostic(
                        "DC-SOURCE-DIVERGENT-CHANGE-LINKS",
                        f"{change_id} frontmatter and included-proposals.yml disagree.",
                        target_id=change_id,
                    )
                )

        for document in documents:
            if document.source_kind != SourceKind.WORK_MANIFEST:
                continue
            source = document.frontmatter.get("source")
            change_id = str(source.get("change") or "").strip() if isinstance(source, Mapping) else ""
            if change_id:
                _append_relation(
                    assertions,
                    diagnostics,
                    source_id=document.owner_id,
                    source_type=NodeType.WORK,
                    target_id=change_id,
                    target_type=NodeType.CHANGE,
                    relation_type=RelationType.IMPLEMENTS,
                    scope="work_lineage",
                    item_evidence=source_evidence(document, "yaml:/source/change"),
                    known_nodes=known_nodes,
                )

    @staticmethod
    def _normalize_related_proposals(
        documents: Sequence[SourceDocument],
        known_nodes: set[tuple[NodeType, str]],
        assertions: list[_RelationAssertion],
        diagnostics: list[DecisionContextDiagnostic],
        source_evidence: object,
    ) -> None:
        for document in documents:
            if document.source_kind != SourceKind.RELATED_PROPOSALS:
                continue
            payload = document.frontmatter.get("related_proposals")
            if isinstance(payload, Mapping):
                payload = payload.get("items") or ()
            for index, item in enumerate(_mapping_items(payload)):
                target_id = _first_text(item, "proposal", "proposal_id", "id")
                relation_name = _first_text(item, "relationship", "relation", "type")
                relation_slug = _slug(relation_name)
                relation_policy = classify_relation_term(relation_name)
                relation_type = relation_policy["relation_type"]
                if relation_type is None:
                    meanings = relation_policy["candidate_meanings"]
                    diagnostics.append(
                        _diagnostic(
                            (
                                "DC-RELATION-AMBIGUOUS-TYPE"
                                if relation_slug in _AMBIGUOUS_RELATION_TERMS
                                else "DC-RELATION-UNSUPPORTED-TYPE"
                            ),
                            (
                                f"Ambiguous relation type {relation_name!r} requires explicit direction and semantics; "
                                f"candidate meanings: {', '.join(meanings)}. Curate the source through impact preview/apply."
                                if relation_slug in _AMBIGUOUS_RELATION_TERMS
                                else f"Unsupported relation type {relation_name!r}."
                            ),
                            source_path=document.path,
                            target_id=target_id,
                        )
                    )
                    continue
                _append_relation(
                    assertions,
                    diagnostics,
                    source_id=document.owner_id,
                    source_type=NodeType.PROPOSAL,
                    target_id=target_id,
                    target_type=NodeType.PROPOSAL,
                    relation_type=relation_type,
                    scope="proposal_relation",
                    item_evidence=source_evidence(document, f"yaml:/related_proposals/{index}"),
                    known_nodes=known_nodes,
                )

    @staticmethod
    def _normalize_impacts(
        documents: Sequence[SourceDocument],
        nodes: dict[tuple[NodeType, str], DecisionContextNode],
        assertions: list[_RelationAssertion],
        diagnostics: list[DecisionContextDiagnostic],
        source_evidence: object,
    ) -> None:
        for document in documents:
            if document.source_kind != SourceKind.IMPACT_MAP:
                continue
            source_type = NodeType.CHANGE if document.owner_id.startswith("CHANGE-") else NodeType.PROPOSAL
            seen: set[tuple[NodeType, str, RelationType]] = set()
            for pointer, key, value in _walk_impact_values(document.frontmatter):
                value_type, relation_type = _VALUE_RELATIONS[key]
                node_id = _value_node_id(value_type, value)
                identity = (value_type, node_id, relation_type)
                if identity in seen:
                    continue
                seen.add(identity)
                nodes.setdefault(
                    (value_type, node_id),
                    DecisionContextNode(node_id, value_type, value, existence="symbolic"),
                )
                item_evidence = source_evidence(document, pointer)
                assertions.append(
                    _RelationAssertion(
                        document.owner_id,
                        source_type,
                        node_id,
                        value_type,
                        relation_type,
                        "impact",
                        item_evidence.activation,
                        item_evidence.authority,
                        item_evidence.confidence,
                        item_evidence.evidence_id,
                    )
                )

    @staticmethod
    def _normalize_conflicts(
        documents: Sequence[SourceDocument],
        known_nodes: set[tuple[NodeType, str]],
        assertions: list[_RelationAssertion],
        diagnostics: list[DecisionContextDiagnostic],
        source_evidence: object,
    ) -> None:
        for document in documents:
            if document.source_kind not in {SourceKind.CONFLICT_ANALYSIS, SourceKind.PROJECT_CONFLICTS}:
                continue
            payload = document.frontmatter.get("conflicts")
            if document.source_kind == SourceKind.CONFLICT_ANALYSIS and isinstance(payload, Mapping):
                payload = payload.get("items") or payload.get("conflicts") or ()
            for index, item in enumerate(_mapping_items(payload)):
                proposals = list(_string_values(item.get("proposals")))
                if not proposals:
                    for key in ("proposal", "other_proposal", "target", "rejected", "winner"):
                        for value in _string_values(item.get(key)):
                            if value.startswith("PROP-") and value not in proposals:
                                proposals.append(value)
                if document.owner_id.startswith("PROP-") and document.owner_id not in proposals:
                    proposals.insert(0, document.owner_id)
                for left_index, left in enumerate(proposals):
                    for right in proposals[left_index + 1 :]:
                        _append_relation(
                            assertions,
                            diagnostics,
                            source_id=left,
                            source_type=NodeType.PROPOSAL,
                            target_id=right,
                            target_type=NodeType.PROPOSAL,
                            relation_type=RelationType.CONFLICTS_WITH,
                            scope="project_conflict" if document.owner_id == "PROJECT" else "proposal_conflict",
                            item_evidence=source_evidence(document, f"yaml:/conflicts/{index}"),
                            known_nodes=known_nodes,
                        )
                winners = _string_values(item.get("winner"))
                rejected_values = _string_values(item.get("rejected"))
                if len(winners) > 1:
                    diagnostics.append(
                        _diagnostic(
                            "DC-CONFLICT-AMBIGUOUS-WINNER",
                            "Conflict resolution contains multiple winners.",
                            source_path=document.path,
                            target_id=document.owner_id,
                        )
                    )
                if len(winners) == 1:
                    for rejected_index, rejected in enumerate(rejected_values):
                        _append_relation(
                            assertions,
                            diagnostics,
                            source_id=winners[0],
                            source_type=NodeType.PROPOSAL,
                            target_id=rejected,
                            target_type=NodeType.PROPOSAL,
                            relation_type=RelationType.SUPERSEDES,
                            scope="conflict_resolution",
                            item_evidence=source_evidence(
                                document,
                                f"yaml:/conflicts/{index}/rejected/{rejected_index}",
                            ),
                            known_nodes=known_nodes,
                        )

    @staticmethod
    def _normalize_choices(
        documents: Sequence[SourceDocument],
        known_nodes: set[tuple[NodeType, str]],
        assertions: list[_RelationAssertion],
        diagnostics: list[DecisionContextDiagnostic],
        source_evidence: object,
    ) -> None:
        for document in documents:
            if document.source_kind not in {
                SourceKind.PROJECT_CHOICE,
                SourceKind.PROJECT_CHOICE_LINKS,
                SourceKind.PROJECT_CHOICE_LIFECYCLE,
            }:
                continue
            if document.source_kind == SourceKind.PROJECT_CHOICE_LIFECYCLE:
                lifecycle = document.frontmatter.get("choice_lifecycle")
                event = lifecycle.get("terminal_event") if isinstance(lifecycle, Mapping) else None
                replacement = (
                    str(event.get("replacement_choice_id") or "").strip()
                    if isinstance(event, Mapping)
                    else ""
                )
                if replacement:
                    _append_relation(
                        assertions,
                        diagnostics,
                        source_id=replacement,
                        source_type=NodeType.CHOICE,
                        target_id=document.owner_id,
                        target_type=NodeType.CHOICE,
                        relation_type=RelationType.SUPERSEDES,
                        scope="choice_replacement",
                        item_evidence=source_evidence(
                            document,
                            "yaml:/choice_lifecycle/terminal_event/replacement_choice_id",
                        ),
                        known_nodes=known_nodes,
                    )
                continue
            if document.source_kind == SourceKind.PROJECT_CHOICE:
                related = document.frontmatter.get("related")
                payload = related.get("proposals") if isinstance(related, Mapping) else ()
                pointer_prefix = "frontmatter:/related/proposals"
            else:
                payload = document.frontmatter.get("related_proposals")
                pointer_prefix = "yaml:/related_proposals"
            values: list[tuple[str, str]] = []
            for item in _sequence(payload):
                if isinstance(item, Mapping):
                    values.append(
                        (
                            _first_text(item, "proposal", "proposal_id", "id"),
                            _first_text(item, "relationship", "relation", "type"),
                        )
                    )
                else:
                    values.append((str(item).strip(), "references"))
            for index, (proposal_id, relation_name) in enumerate(values):
                relation_slug = _slug(relation_name)
                relation_policy = classify_relation_term(relation_name)
                relation_type = relation_policy["relation_type"]
                if relation_type is None:
                    diagnostics.append(
                        _diagnostic(
                            (
                                "DC-RELATION-AMBIGUOUS-TYPE"
                                if relation_slug in _AMBIGUOUS_RELATION_TERMS
                                else "DC-RELATION-UNSUPPORTED-TYPE"
                            ),
                            f"Unsupported or ambiguous relation type {relation_name!r}.",
                            source_path=document.path,
                            target_id=proposal_id,
                        )
                    )
                    continue
                _append_relation(
                    assertions,
                    diagnostics,
                    source_id=document.owner_id,
                    source_type=NodeType.CHOICE,
                    target_id=proposal_id,
                    target_type=NodeType.PROPOSAL,
                    relation_type=relation_type,
                    scope="choice_applicability",
                    item_evidence=source_evidence(document, f"{pointer_prefix}/{index}"),
                    known_nodes=known_nodes,
                )
            if document.source_kind == SourceKind.PROJECT_CHOICE_LINKS:
                for index, item in enumerate(_sequence(document.frontmatter.get("related_changes"))):
                    if isinstance(item, Mapping):
                        change_id = _first_text(item, "change", "change_id", "id")
                    else:
                        change_id = str(item).strip()
                    if not change_id:
                        continue
                    _append_relation(
                        assertions,
                        diagnostics,
                        source_id=document.owner_id,
                        source_type=NodeType.CHOICE,
                        target_id=change_id,
                        target_type=NodeType.CHANGE,
                        relation_type=RelationType.REFERENCES,
                        scope="choice_change",
                        item_evidence=source_evidence(document, f"yaml:/related_changes/{index}"),
                        known_nodes=known_nodes,
                    )
                for index, item in enumerate(_sequence(document.frontmatter.get("blocks"))):
                    if not isinstance(item, Mapping):
                        continue
                    if str(item.get("status") or "active").strip().casefold() != "active":
                        continue
                    target_id = _first_text(item, "target", "id")
                    target_type_name = str(item.get("target_type") or "").strip().casefold()
                    target_type = {
                        "proposal": NodeType.PROPOSAL,
                        "change": NodeType.CHANGE,
                    }.get(target_type_name)
                    if not target_id or target_type is None:
                        diagnostics.append(
                            _diagnostic(
                                "DC-RELATION-UNSUPPORTED",
                                f"Unsupported choice block target in {document.path}.",
                                source_path=document.path,
                                target_id=target_id,
                            )
                        )
                        continue
                    _append_relation(
                        assertions,
                        diagnostics,
                        source_id=document.owner_id,
                        source_type=NodeType.CHOICE,
                        target_id=target_id,
                        target_type=target_type,
                        relation_type=RelationType.BLOCKS,
                        scope="choice_block",
                        item_evidence=source_evidence(document, f"yaml:/blocks/{index}"),
                        known_nodes=known_nodes,
                    )

    @staticmethod
    def _normalize_vertical_coverage(
        documents: Sequence[SourceDocument],
        nodes: dict[tuple[NodeType, str], DecisionContextNode],
        assertions: list[_RelationAssertion],
        diagnostics: list[DecisionContextDiagnostic],
        source_evidence: object,
    ) -> None:
        for document in documents:
            if document.source_kind != SourceKind.VERTICAL_COVERAGE:
                continue
            payload = document.frontmatter.get("vertical_coverage")
            sections = payload.get("sections") if isinstance(payload, Mapping) else ()
            for index, item in enumerate(_sequence(sections)):
                if isinstance(item, Mapping):
                    section = _first_text(item, "section", "section_id", "id", "name")
                else:
                    section = str(item).strip()
                if not section:
                    continue
                node_id = _value_node_id(NodeType.VERTICAL_SECTION, section)
                nodes.setdefault(
                    (NodeType.VERTICAL_SECTION, node_id),
                    DecisionContextNode(node_id, NodeType.VERTICAL_SECTION, section, existence="declared"),
                )
                item_evidence = source_evidence(document, f"yaml:/vertical_coverage/sections/{index}")
                assertions.append(
                    _RelationAssertion(
                        document.owner_id,
                        NodeType.PROPOSAL,
                        node_id,
                        NodeType.VERTICAL_SECTION,
                        RelationType.MAPS_TO_VERTICAL_SECTION,
                        "vertical_coverage",
                        item_evidence.activation,
                        item_evidence.authority,
                        Confidence.EXPLICIT,
                        item_evidence.evidence_id,
                    )
                )


def classify_relation_term(value: str) -> dict[str, object]:
    term = _slug(value)
    if term in _AMBIGUOUS_RELATION_TERMS:
        return {
            "term": term,
            "category": "ambiguous",
            "relation_type": None,
            "candidate_meanings": _AMBIGUOUS_RELATION_MEANINGS[term],
        }
    relation_type = _RELATION_TYPES.get(term)
    if relation_type is None:
        return {
            "term": term,
            "category": "invalid",
            "relation_type": None,
            "candidate_meanings": (),
        }
    return {
        "term": term,
        "category": "canonical",
        "relation_type": relation_type,
        "candidate_meanings": (relation_type.value,),
    }


def build_adjacency(
    relations: Sequence[DecisionContextRelation],
) -> tuple[Mapping[str, tuple[str, ...]], Mapping[str, tuple[str, ...]]]:
    incoming: dict[str, list[str]] = defaultdict(list)
    outgoing: dict[str, list[str]] = defaultdict(list)
    for relation in relations:
        outgoing[relation.source_id].append(relation.relation_id)
        incoming[relation.target_id].append(relation.relation_id)
        if relation.relation_type in _SYMMETRIC_RELATIONS:
            outgoing[relation.target_id].append(relation.relation_id)
            incoming[relation.source_id].append(relation.relation_id)
    return (
        {key: tuple(sorted(set(values))) for key, values in sorted(incoming.items())},
        {key: tuple(sorted(set(values))) for key, values in sorted(outgoing.items())},
    )


def traverse_relations(
    start_id: str,
    relations: Sequence[DecisionContextRelation],
    *,
    max_depth: int,
    fan_out: int,
) -> tuple[TraversalStep, ...]:
    relation_map = {item.relation_id: item for item in relations}
    incoming, outgoing = build_adjacency(relations)
    queue: deque[TraversalStep] = deque([TraversalStep(start_id, (), 0)])
    visited_nodes = {start_id}
    visited_relations: set[str] = set()
    result: list[TraversalStep] = []
    while queue:
        current = queue.popleft()
        if current.depth >= max_depth:
            continue
        relation_ids = sorted(set(incoming.get(current.node_id, ()) + outgoing.get(current.node_id, ())))[:fan_out]
        for relation_id in relation_ids:
            if relation_id in visited_relations:
                continue
            visited_relations.add(relation_id)
            relation = relation_map[relation_id]
            next_id = relation.target_id if relation.source_id == current.node_id else relation.source_id
            if next_id in visited_nodes:
                continue
            visited_nodes.add(next_id)
            step = TraversalStep(next_id, current.relation_ids + (relation_id,), current.depth + 1)
            result.append(step)
            queue.append(step)
    return tuple(result)


def _owner_state(
    records: Sequence[DecisionContextRecord],
) -> Mapping[str, tuple[Activation, Authority]]:
    grouped: dict[str, list[DecisionContextRecord]] = defaultdict(list)
    for record in records:
        grouped[record.owner_id].append(record)
    result: dict[str, tuple[Activation, Authority]] = {}
    for owner_id, items in grouped.items():
        best = max(items, key=lambda item: (AUTHORITY_RANK[item.authority], _ACTIVATION_RANK[item.activation]))
        result[owner_id] = best.activation, best.authority
    return result


def _evidence(
    document: SourceDocument,
    pointer: str,
    canonicality: Canonicality,
    authority: Authority,
    activation: Activation,
    confidence: Confidence,
) -> DecisionContextEvidence:
    source_hash = document.sha256 or ""
    evidence_id = "evidence:" + _hash(
        {
            "path": document.path,
            "sha256": source_hash,
            "fragment": pointer,
            "authority": authority.value,
            "activation": activation.value,
        }
    )
    return DecisionContextEvidence(
        evidence_id=evidence_id,
        source_path=document.path,
        source_sha256=source_hash,
        source_kind=document.source_kind,
        fragment_id=pointer,
        fragment_label=pointer.rsplit("/", 1)[-1],
        span=None,
        canonicality=canonicality,
        authority=authority,
        activation=activation,
        confidence=confidence,
        completeness=document.completeness,
    )


def _record(
    document: SourceDocument,
    pointer: str,
    kind: RecordKind,
    owner_type: NodeType,
    owner_id: str,
    text: str,
    item_evidence: DecisionContextEvidence,
    *,
    authority: Authority,
    activation: Activation,
    applicability_tokens: tuple[str, ...] = (),
) -> DecisionContextRecord:
    text = text.strip()
    return DecisionContextRecord(
        record_id="record:" + _hash(
            {
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "kind": kind.value,
                "source": document.path,
                "fragment": pointer,
                "text": text,
            }
        ),
        kind=kind,
        owner_type=owner_type,
        owner_id=owner_id,
        activation=activation,
        authority=authority,
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        evidence_ids=(item_evidence.evidence_id,),
        applicability_tokens=applicability_tokens,
    )


def _append_relation(
    assertions: list[_RelationAssertion],
    diagnostics: list[DecisionContextDiagnostic],
    *,
    source_id: str,
    source_type: NodeType,
    target_id: str,
    target_type: NodeType,
    relation_type: RelationType,
    scope: str,
    item_evidence: DecisionContextEvidence,
    known_nodes: set[tuple[NodeType, str]],
) -> None:
    source_id = source_id.strip()
    target_id = target_id.strip()
    if not source_id or not target_id:
        diagnostics.append(
            _diagnostic("DC-RELATION-INVALID-TARGET", "Relation endpoint is empty.", target_id=target_id)
        )
        return
    if source_id == target_id and source_type == target_type:
        diagnostics.append(
            _diagnostic("DC-RELATION-SELF", "Self-relations are quarantined.", target_id=target_id)
        )
        return
    for node_type, node_id in ((source_type, source_id), (target_type, target_id)):
        if node_type in _IDENTITY_TYPES and (node_type, node_id) not in known_nodes:
            diagnostics.append(
                _diagnostic(
                    "DC-RELATION-INVALID-TARGET",
                    f"Relation references missing {node_type.value} node {node_id}.",
                    target_id=node_id,
                    source_path=item_evidence.source_path,
                )
            )
            return
    assertions.append(
        _RelationAssertion(
            source_id,
            source_type,
            target_id,
            target_type,
            relation_type,
            scope,
            item_evidence.activation,
            item_evidence.authority,
            item_evidence.confidence,
            item_evidence.evidence_id,
        )
    )


def _merge_assertions(assertions: Sequence[_RelationAssertion]) -> tuple[DecisionContextRelation, ...]:
    grouped: dict[tuple[str, str, str, str, str, str], list[_RelationAssertion]] = defaultdict(list)
    for assertion in assertions:
        source_id, source_type = assertion.source_id, assertion.source_type
        target_id, target_type = assertion.target_id, assertion.target_type
        if assertion.relation_type in _SYMMETRIC_RELATIONS and (target_type.value, target_id) < (
            source_type.value,
            source_id,
        ):
            source_id, target_id = target_id, source_id
            source_type, target_type = target_type, source_type
        key = (
            source_type.value,
            source_id,
            assertion.relation_type.value,
            target_type.value,
            target_id,
            assertion.scope,
        )
        grouped[key].append(assertion)
    result: list[DecisionContextRelation] = []
    for key, items in sorted(grouped.items()):
        source_type_value, source_id, relation_value, target_type_value, target_id, scope = key
        best = max(
            items,
            key=lambda item: (
                _ACTIVATION_RANK[item.activation],
                AUTHORITY_RANK[item.authority],
                _CONFIDENCE_RANK[item.confidence],
            ),
        )
        evidence_ids = tuple(sorted({item.evidence_id for item in items}))
        diagnostic_ids = tuple(sorted({value for item in items for value in item.diagnostic_ids}))
        relation_id = "relation:" + _hash(
            {
                "source_type": source_type_value,
                "source_id": source_id,
                "relation_type": relation_value,
                "target_type": target_type_value,
                "target_id": target_id,
                "scope": scope,
            }
        )
        result.append(
            DecisionContextRelation(
                relation_id=relation_id,
                source_id=source_id,
                source_type=NodeType(source_type_value),
                target_id=target_id,
                target_type=NodeType(target_type_value),
                relation_type=RelationType(relation_value),
                scope=scope,
                activation=best.activation,
                authority=best.authority,
                confidence=best.confidence,
                evidence_ids=evidence_ids,
                diagnostic_ids=diagnostic_ids,
            )
        )
    return tuple(result)


def _incompatible_assertion_diagnostics(
    assertions: Sequence[_RelationAssertion],
) -> tuple[DecisionContextDiagnostic, ...]:
    lineage_types = {
        RelationType.SUPERSEDES,
        RelationType.MERGED_INTO,
        RelationType.SPLIT_INTO,
    }
    grouped: dict[tuple[str, str, str], set[RelationType]] = defaultdict(set)
    for item in assertions:
        if item.activation != Activation.ACTIVE or item.relation_type not in lineage_types:
            continue
        grouped[(item.source_id, item.target_id, item.scope)].add(item.relation_type)
    diagnostics = []
    for (source_id, target_id, scope), relation_types in sorted(grouped.items()):
        if len(relation_types) < 2:
            continue
        diagnostics.append(
            _diagnostic(
                "DC-RELATION-INCOMPATIBLE-ASSERTIONS",
                f"Active lineage assertions disagree for {source_id} -> {target_id} in {scope}: "
                + ", ".join(sorted(item.value for item in relation_types)),
                target_id=target_id,
            )
        )
    return tuple(diagnostics)


def _quality_summaries(document: SourceDocument) -> tuple[tuple[str, str, Activation], ...]:
    if document.source_kind == SourceKind.ARTIFACT_STATE:
        payload = document.frontmatter.get("proposal_artifacts")
        artifacts = payload.get("artifacts") if isinstance(payload, Mapping) else ()
        return tuple(
            (
                f"yaml:/proposal_artifacts/artifacts/{index}",
                f"Artifact {_first_text(item, 'filename', 'id')}: {_first_text(item, 'status') or 'unknown'} "
                f"({_first_text(item, 'confirmation') or 'unconfirmed'})",
                Activation.INACTIVE,
            )
            for index, item in enumerate(_mapping_items(artifacts))
        )
    if document.source_kind == SourceKind.QUESTIONS:
        payload = document.frontmatter.get("proposal_questions")
        questions = payload.get("questions") if isinstance(payload, Mapping) else ()
        result = []
        for index, item in enumerate(_mapping_items(questions)):
            state = _first_text(item, "state") or "unknown"
            applied = bool(item.get("applied_to_proposal")) or state == "applied"
            activation = Activation.ACTIVE if applied else Activation.INACTIVE
            result.append(
                (
                    f"yaml:/proposal_questions/questions/{index}",
                    f"Question {_first_text(item, 'id')}: {state}",
                    activation,
                )
            )
        return tuple(result)
    if document.source_kind == SourceKind.READINESS:
        payload = document.frontmatter.get("proposal_readiness")
        if not isinstance(payload, Mapping):
            payload = document.frontmatter
        score = payload.get("score") or payload.get("computed_score") or "unknown"
        return (("yaml:/readiness", f"Readiness score: {score}", Activation.INACTIVE),)
    if document.source_kind == SourceKind.CONTRIBUTIONS:
        items = document.frontmatter.get("contributions")
        return tuple(
            (
                f"yaml:/contributions/{index}",
                f"Contribution {_first_text(item, 'id', 'kind') or index + 1}: {_first_text(item, 'status') or 'recorded'}",
                Activation.INACTIVE,
            )
            for index, item in enumerate(_mapping_items(items))
        )
    if document.source_kind == SourceKind.PROJECT_QUESTIONS:
        payload = document.frontmatter.get("project_questions")
        questions = payload.get("questions") if isinstance(payload, Mapping) else ()
        result = []
        for index, item in enumerate(_mapping_items(questions)):
            if index >= 100:
                break
            question_id = _first_text(item, "id") or f"question-{index + 1}"
            state = _first_text(item, "state") or "unknown"
            target = item.get("target") if isinstance(item.get("target"), Mapping) else {}
            target_kind = _first_text(target, "kind") or "unknown"
            target_id = _first_text(target, "id") or "unknown"
            answers = item.get("answers") if isinstance(item.get("answers"), list) else []
            applications = item.get("applications") if isinstance(item.get("applications"), list) else []
            result.append(
                (
                    f"yaml:/project_questions/questions/{index}",
                    f"Project question {question_id}: {state}; target {target_kind}:{target_id}; "
                    f"answer revisions {len(answers)}; applications {len(applications)}",
                    Activation.INACTIVE,
                )
            )
        return tuple(result)
    return ()


def _project_definition_values(payload: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    wrapped = payload.get("project_definition")
    if isinstance(wrapped, Mapping):
        payload = wrapped
    allowed = {"identity", "purpose", "scope", "principles", "constraints", "capabilities", "surfaces"}
    result: list[tuple[str, str]] = []
    for key in sorted(payload):
        if key not in allowed:
            continue
        for pointer, text in _scalar_text_values(payload[key], f"yaml:/{key}"):
            if text:
                result.append((pointer, text))
    sections = payload.get("sections")
    for section_index, section in enumerate(_mapping_items(sections)):
        fields = section.get("fields")
        if isinstance(fields, Mapping):
            for field_id in sorted(fields, key=str):
                field = fields[field_id]
                value = field.get("value") if isinstance(field, Mapping) else field
                for pointer, text in _scalar_text_values(
                    value,
                    f"yaml:/sections/{section_index}/fields/{field_id}/value",
                ):
                    if text:
                        result.append((pointer, text))
        for assumption_index, assumption in enumerate(_mapping_items(section.get("assumptions"))):
            if _first_text(assumption, "status") not in {"validated", "rejected"}:
                continue
            text = _first_text(assumption, "text")
            if text:
                result.append(
                    (f"yaml:/sections/{section_index}/assumptions/{assumption_index}/text", text)
                )
        for blocker_index, blocker in enumerate(_mapping_items(section.get("blockers"))):
            if _first_text(blocker, "status") != "open":
                continue
            text = _first_text(blocker, "text")
            if text:
                result.append(
                    (f"yaml:/sections/{section_index}/blockers/{blocker_index}/text", text)
                )
    return tuple(result)


def _scalar_text_values(value: object, pointer: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield pointer, value.strip()
    elif isinstance(value, Mapping):
        for key in sorted(value, key=str):
            yield from _scalar_text_values(value[key], f"{pointer}/{key}")
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            yield from _scalar_text_values(item, f"{pointer}/{index}")


def _walk_impact_values(payload: Mapping[str, object]) -> Iterable[tuple[str, str, str]]:
    def walk(value: object, pointer: str, key_hint: str = "") -> Iterable[tuple[str, str, str]]:
        normalized_key = key_hint.casefold().replace("_", "-").replace("-", "_")
        if normalized_key in _VALUE_RELATIONS:
            for index, item in enumerate(_sequence(value)):
                if isinstance(item, Mapping):
                    raw = _first_text(item, normalized_key.rstrip("s"), "name", "id", "path")
                else:
                    raw = str(item).strip()
                if raw:
                    yield f"{pointer}/{index}", normalized_key, raw
            return
        if isinstance(value, Mapping):
            for key in sorted(value, key=str):
                yield from walk(value[key], f"{pointer}/{key}", str(key))
        elif isinstance(value, (tuple, list)):
            for index, item in enumerate(value):
                yield from walk(item, f"{pointer}/{index}", key_hint)

    yield from walk(payload, "yaml:")


def _value_node_id(node_type: NodeType, value: str) -> str:
    normalized = value.strip()
    return f"{node_type.value}:{normalized}"


def _mapping_items(value: object) -> tuple[Mapping[str, object], ...]:
    return tuple(item for item in _sequence(value) if isinstance(item, Mapping))


def _sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, (tuple, list)):
        return tuple(value)
    if value is None:
        return ()
    return (value,)


def _string_values(value: object) -> tuple[str, ...]:
    result = []
    for item in _sequence(value):
        if isinstance(item, Mapping):
            text = _first_text(item, "proposal", "proposal_id", "id", "value")
        else:
            text = str(item).strip()
        if text:
            result.append(text)
    return tuple(result)


def _precedent_refs(value: Mapping[str, object], *keys: str) -> tuple[str, ...]:
    refs: set[str] = set()
    for key in keys:
        for item in _sequence(value.get(key)):
            if isinstance(item, Mapping):
                ref = _first_text(item, "id", "proposal", "choice", "tag")
            else:
                ref = str(item).strip()
            if ref:
                refs.add(ref)
    return tuple(sorted(refs))


def _first_text(value: Mapping[str, object], *keys: str) -> str:
    for key in keys:
        text = str(value.get(key) or "").strip()
        if text:
            return text
    return ""


def _section_text(document: SourceDocument, label: str) -> str:
    fragments = fragments_for_label(document, label)
    return fragments[0].text.strip() if fragments else ""


def _document_title(document: SourceDocument) -> str:
    title = document.frontmatter.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    if document._content:
        try:
            text = document._content.decode("utf-8")
        except UnicodeDecodeError:
            return ""
        for line in text.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return ""


def _diagnostic(
    code: str,
    message: str,
    *,
    source_path: str = "",
    target_id: str = "",
) -> DecisionContextDiagnostic:
    diagnostic_id = "diagnostic:" + _hash(
        {"code": code, "message": message, "source_path": source_path, "target_id": target_id}
    )
    return DecisionContextDiagnostic(
        diagnostic_id=diagnostic_id,
        code=code,
        severity=DiagnosticSeverity.WARNING,
        fatal=False,
        message=message,
        source_path=source_path,
        target_id=target_id,
        recovery="Correct the source through its supported workflow.",
    )


def _deduplicate_diagnostics(
    diagnostics: Sequence[DecisionContextDiagnostic],
) -> list[DecisionContextDiagnostic]:
    return sorted(
        {item.diagnostic_id: item for item in diagnostics}.values(),
        key=lambda item: (item.severity.value, item.code, item.source_path, item.target_id, item.diagnostic_id),
    )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _hash(value: Mapping[str, object]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

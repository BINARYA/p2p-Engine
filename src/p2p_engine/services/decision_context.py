from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from types import MappingProxyType

from p2p_engine.core.decision_context import (
    AUTHORITY_POLICY_VERSION,
    EXTRACTOR_VERSION,
    RELATION_POLICY_VERSION,
    SCHEMA_VERSION,
    Completeness,
    DecisionContextIndex,
    SourceAccessStats,
    freeze_string_tuple_mapping,
    to_json_ready,
)
from p2p_engine.services.decision_context_extractors import DecisionContextExtractorService
from p2p_engine.services.decision_context_freshness import semantic_fingerprint
from p2p_engine.services.decision_context_sources import DecisionContextSourceService, SourceAccessor
from p2p_engine.services.decision_context_retrieval import build_retrieval_postings
from p2p_engine.services.decision_context_topology import (
    DecisionContextTopologyService,
    build_adjacency,
)


class ProjectDecisionContextService:
    """Read-only facade. Request snapshots never survive a public method call."""

    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path | None = None,
        source_accessor: SourceAccessor | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = (p2p_dir or self.root / ".p2p").resolve()
        self.source_accessor = source_accessor

    def build_index(self) -> DecisionContextIndex:
        source_service = DecisionContextSourceService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            accessor=self.source_accessor,
        )
        session = source_service.build_full_session()
        if session.completeness == Completeness.UNAVAILABLE and not session.sources:
            return _empty_index(session)

        extracted = DecisionContextExtractorService().extract_proposals_and_decisions(session)
        normalized = DecisionContextTopologyService().normalize(
            session,
            base_records=extracted.records,
            base_nodes=extracted.nodes,
        )
        evidence = tuple(
            sorted(
                {item.evidence_id: item for item in (*extracted.evidence, *normalized.evidence)}.values(),
                key=lambda item: (item.source_path, item.fragment_id, item.evidence_id),
            )
        )
        records = tuple(
            sorted(
                {item.record_id: item for item in (*extracted.records, *normalized.records)}.values(),
                key=lambda item: (item.owner_type.value, item.owner_id, item.kind.value, item.record_id),
            )
        )
        diagnostics = tuple(
            sorted(
                {item.diagnostic_id: item for item in (*extracted.diagnostics, *normalized.diagnostics)}.values(),
                key=lambda item: (item.severity.value, item.code, item.source_path, item.target_id, item.diagnostic_id),
            )
        )
        relations = tuple(
            sorted(
                {
                    item.relation_id: item
                    for item in (*extracted.relations, *normalized.relations)
                }.values(),
                key=lambda item: (
                    item.source_type.value,
                    item.source_id,
                    item.relation_type.value,
                    item.target_type.value,
                    item.target_id,
                    item.relation_id,
                ),
            )
        )
        nodes = tuple(
            sorted(
                {
                    (item.node_type, item.node_id): item
                    for item in (*extracted.nodes, *normalized.nodes)
                }.values(),
                key=lambda item: (item.node_type.value, item.node_id),
            )
        )
        incoming, outgoing = build_adjacency(relations)
        token_postings, domain_postings, owner_authority, owner_activation = build_retrieval_postings(
            records, nodes, relations
        )
        records_by_owner: dict[str, list[str]] = defaultdict(list)
        for record in records:
            records_by_owner[record.owner_id].append(record.record_id)
        for values in records_by_owner.values():
            values.sort()
        semantic_fingerprint_value = semantic_fingerprint(
            session.source_fingerprint_sha256,
            extractor_version=EXTRACTOR_VERSION,
            authority_policy_version=AUTHORITY_POLICY_VERSION,
            relation_policy_version=RELATION_POLICY_VERSION,
            semantic_payload={
                "records": to_json_ready(records),
                "relations": to_json_ready(relations),
            },
        )
        return DecisionContextIndex(
            schema_version=SCHEMA_VERSION,
            source_catalog_version=session.source_catalog_version,
            extractor_version=EXTRACTOR_VERSION,
            authority_policy_version=AUTHORITY_POLICY_VERSION,
            relation_policy_version=RELATION_POLICY_VERSION,
            source_fingerprint_sha256=session.source_fingerprint_sha256,
            semantic_fingerprint_sha256=semantic_fingerprint_value,
            completeness=_combined_completeness(session.completeness, diagnostics, records),
            sources=session.sources,
            evidence=evidence,
            records=records,
            nodes=nodes,
            relations=relations,
            diagnostics=diagnostics,
            access_stats=session.access_stats,
            records_by_owner=freeze_string_tuple_mapping(records_by_owner),
            incoming_relations=freeze_string_tuple_mapping(incoming),
            outgoing_relations=freeze_string_tuple_mapping(outgoing),
            token_postings=token_postings,
            domain_postings=domain_postings,
            owner_authority=owner_authority,
            owner_activation=owner_activation,
        )


def _empty_index(session: object) -> DecisionContextIndex:
    source_fingerprint = str(getattr(session, "source_fingerprint_sha256"))
    access_stats = getattr(session, "access_stats", SourceAccessStats(0, {}, {}, {}))
    return DecisionContextIndex(
        schema_version=SCHEMA_VERSION,
        source_catalog_version=str(getattr(session, "source_catalog_version")),
        extractor_version=EXTRACTOR_VERSION,
        authority_policy_version=AUTHORITY_POLICY_VERSION,
        relation_policy_version=RELATION_POLICY_VERSION,
        source_fingerprint_sha256=source_fingerprint,
        semantic_fingerprint_sha256=semantic_fingerprint(
            source_fingerprint,
            extractor_version=EXTRACTOR_VERSION,
            authority_policy_version=AUTHORITY_POLICY_VERSION,
            relation_policy_version=RELATION_POLICY_VERSION,
        ),
        completeness=Completeness.UNAVAILABLE,
        sources=tuple(getattr(session, "sources", ())),
        evidence=(),
        records=(),
        nodes=(),
        relations=(),
        diagnostics=tuple(getattr(session, "diagnostics", ())),
        access_stats=access_stats,
        records_by_owner=MappingProxyType({}),
        incoming_relations=MappingProxyType({}),
        outgoing_relations=MappingProxyType({}),
        token_postings=MappingProxyType({}),
        domain_postings=MappingProxyType({}),
        owner_authority=MappingProxyType({}),
        owner_activation=MappingProxyType({}),
    )


def _combined_completeness(
    source_completeness: Completeness,
    diagnostics: tuple[object, ...],
    records: tuple[object, ...],
) -> Completeness:
    if source_completeness == Completeness.UNAVAILABLE or not records:
        return Completeness.UNAVAILABLE
    if source_completeness == Completeness.PARTIAL or diagnostics:
        return Completeness.PARTIAL
    return Completeness.COMPLETE

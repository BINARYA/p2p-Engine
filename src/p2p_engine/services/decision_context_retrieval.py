from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, replace
from functools import cmp_to_key
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

from p2p_engine.core.decision_context import (
    AUTHORITY_RANK,
    BUDGET_POLICY_VERSION,
    LEXICAL_POLICY_VERSION,
    RETRIEVAL_POLICY_VERSION,
    Activation,
    Authority,
    BudgetPolicy,
    Completeness,
    Confidence,
    ContextBudget,
    DecisionContextDiagnostic,
    DecisionContextEvidence,
    DecisionContextIndex,
    DecisionContextNode,
    DecisionContextPacket,
    DecisionContextRecord,
    DecisionContextRelation,
    DiagnosticSeverity,
    NodeType,
    RecordKind,
    RelationType,
    RetrievalHit,
    RetrievalPolicy,
    RetrievalReason,
    RetrievalRequest,
    TruncationMetadata,
    freeze_string_tuple_mapping,
    to_json_ready,
)
from p2p_engine.services.decision_context_topology import traverse_relations


_MARKDOWN_RE = re.compile(r"[`*_~#>\[\](){}!]")
_ID_RE = re.compile(r"\b(?:PROP|CHANGE|CHOICE|WORK)-[0-9]+\b", re.IGNORECASE)
_PATH_RE = re.compile(r"(?<!\w)(?:\.?[\w.-]+/)+[\w.@+-]+(?:\.[\w-]+)?")
_COMMAND_RE = re.compile(r"\bp2p(?:\s+[a-z][a-z0-9_-]*){1,3}", re.IGNORECASE)
_WORD_RE = re.compile(r"[^\W_]+(?:[-.][^\W_]+)*", re.UNICODE)
_DOMAIN_PREFIX = "domain:"

_STOP_WORDS = frozenset(
    {
        "a",
        "ad",
        "al",
        "alla",
        "alle",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "che",
        "con",
        "da",
        "dal",
        "dalla",
        "de",
        "dei",
        "del",
        "della",
        "di",
        "e",
        "ed",
        "for",
        "from",
        "gli",
        "i",
        "il",
        "in",
        "is",
        "it",
        "la",
        "le",
        "lo",
        "ma",
        "nel",
        "nella",
        "non",
        "of",
        "o",
        "on",
        "or",
        "per",
        "the",
        "to",
        "un",
        "una",
        "uno",
        "with",
    }
)

_SIGNAL_WEIGHTS = MappingProxyType(
    {
        "blocker_or_conflict": 60,
        "explicit_relation": 50,
        "applicable_decision": 40,
        "shared_domain": 25,
        "shared_vertical": 20,
        "lexical_overlap": 20,
        "heuristic_vertical": 8,
        "draft_penalty": -5,
        "historical_penalty": -15,
    }
)
_SIGNAL_CAPS = MappingProxyType(dict(_SIGNAL_WEIGHTS))
DEFAULT_RETRIEVAL_POLICY = RetrievalPolicy(
    version=RETRIEVAL_POLICY_VERSION,
    candidate_limit=200,
    minimum_score=15,
    historical_threshold=35,
    score_minimum=0,
    score_maximum=100,
    signal_weights=_SIGNAL_WEIGHTS,
    signal_caps=_SIGNAL_CAPS,
)
_BUDGET_POLICIES: Mapping[ContextBudget, BudgetPolicy] = MappingProxyType(
    {
        ContextBudget.SMALL: BudgetPolicy(
            version=BUDGET_POLICY_VERSION,
            budget=ContextBudget.SMALL,
            max_hits=5,
            max_records=8,
            max_relations=8,
            max_reasons_per_hit=2,
            transitive_depth=0,
            max_serialized_bytes=12_000,
        ),
        ContextBudget.MEDIUM: BudgetPolicy(
            version=BUDGET_POLICY_VERSION,
            budget=ContextBudget.MEDIUM,
            max_hits=12,
            max_records=30,
            max_relations=24,
            max_reasons_per_hit=5,
            transitive_depth=1,
            max_serialized_bytes=40_000,
        ),
    }
)

_POSITIVE_QUERY_KINDS = frozenset(
    {
        RecordKind.PROBLEM,
        RecordKind.GOAL,
        RecordKind.PROPOSAL_CLAIM,
        RecordKind.ACCEPTANCE_CRITERION,
        RecordKind.CONSTRAINT,
        RecordKind.PRECEDENT,
    }
)
_DECISION_KINDS = frozenset(
    {
        RecordKind.DECISION_STATE,
        RecordKind.DECISION_REASON,
        RecordKind.DECISION_QUALIFIER,
        RecordKind.PRECEDENT,
    }
)
_CLAIM_KINDS = frozenset(
    {
        RecordKind.PROBLEM,
        RecordKind.GOAL,
        RecordKind.PROPOSAL_CLAIM,
        RecordKind.ACCEPTANCE_CRITERION,
    }
)
_NON_GOAL_KINDS = frozenset({RecordKind.NON_GOAL})
_DOMAIN_NODE_TYPES = frozenset({NodeType.CAPABILITY, NodeType.SURFACE, NodeType.VERTICAL_SECTION})
_IDENTITY_NODE_TYPES = frozenset(
    {NodeType.PROPOSAL, NodeType.DECISION, NodeType.CHOICE, NodeType.CHANGE, NodeType.WORK}
)
_BLOCKING_RELATIONS = frozenset({RelationType.BLOCKS, RelationType.CONFLICTS_WITH})
_HISTORICAL_EXPLICIT_RELATIONS = frozenset(
    {
        RelationType.CONFLICTS_WITH,
        RelationType.SUPERSEDES,
        RelationType.MERGED_INTO,
        RelationType.SPLIT_INTO,
        RelationType.REFERENCES,
        RelationType.DEPENDS_ON,
    }
)
_ACTIVATION_RANK: Mapping[Activation, int] = {
    Activation.ACTIVE: 5,
    Activation.EXPLORATORY: 4,
    Activation.UNRESOLVED: 3,
    Activation.HISTORICAL: 2,
    Activation.INACTIVE: 1,
}


@dataclass
class _Candidate:
    owner_id: str
    owner_type: NodeType
    relation_ids: set[str]
    direct_relation_types: set[RelationType]
    shared_domain: set[str]
    shared_vertical: set[str]
    heuristic_vertical: set[str]
    matched_tokens: set[str]
    transitive: bool = False


def retrieval_policy() -> RetrievalPolicy:
    return DEFAULT_RETRIEVAL_POLICY


def budget_policy(budget: ContextBudget | str) -> BudgetPolicy:
    return _BUDGET_POLICIES[ContextBudget(str(budget))]


def lexical_policy_version() -> str:
    return LEXICAL_POLICY_VERSION


def normalize_lexical(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    domain_tokens: set[str] = set()
    for match in _ID_RE.finditer(normalized):
        domain_tokens.add(f"{_DOMAIN_PREFIX}id:{match.group(0)}")
    for match in _PATH_RE.finditer(normalized):
        domain_tokens.add(f"{_DOMAIN_PREFIX}path:{match.group(0).rstrip('.,:;')}")
    for match in _COMMAND_RE.finditer(normalized):
        domain_tokens.add(f"{_DOMAIN_PREFIX}command:{' '.join(match.group(0).split())}")
    visible = _MARKDOWN_RE.sub(" ", normalized)
    words = {
        token
        for token in _WORD_RE.findall(visible)
        if token not in _STOP_WORDS and (len(token) > 1 or token.isdigit())
    }
    return tuple(sorted(words | domain_tokens))


def build_retrieval_postings(
    records: Sequence[DecisionContextRecord],
    nodes: Sequence[DecisionContextNode],
    relations: Sequence[DecisionContextRelation],
) -> tuple[
    Mapping[str, tuple[str, ...]],
    Mapping[str, tuple[str, ...]],
    Mapping[str, Authority],
    Mapping[str, Activation],
]:
    tokens_by_owner: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.kind not in _POSITIVE_QUERY_KINDS:
            continue
        if record.activation == Activation.HISTORICAL and record.kind in _DECISION_KINDS:
            continue
        tokens_by_owner[record.owner_id].update(normalize_lexical(record.text))
        for applicability_token in record.applicability_tokens:
            normalized_applicability = unicodedata.normalize("NFKC", applicability_token).casefold()
            tokens_by_owner[record.owner_id].add(normalized_applicability)
            tokens_by_owner[record.owner_id].update(
                normalize_lexical(normalized_applicability.split(":", 1)[-1])
            )
    for node in nodes:
        owner = _node_owner(node.node_id, node.node_type)
        if owner is not None and node.node_type in _IDENTITY_NODE_TYPES:
            tokens_by_owner[owner[0]].update(normalize_lexical(node.label))

    node_map = {(node.node_type, node.node_id): node for node in nodes}
    domain_postings: dict[str, set[str]] = defaultdict(set)
    for relation in relations:
        for identity_id, identity_type, value_id, value_type in (
            (relation.source_id, relation.source_type, relation.target_id, relation.target_type),
            (relation.target_id, relation.target_type, relation.source_id, relation.source_type),
        ):
            owner = _node_owner(identity_id, identity_type)
            if owner is None or value_type not in _DOMAIN_NODE_TYPES:
                continue
            node = node_map.get((value_type, value_id))
            label = node.label if node is not None else value_id.split(":", 1)[-1]
            key = f"{value_type.value}:{unicodedata.normalize('NFKC', label).casefold().strip()}"
            domain_postings[key].add(owner[0])
            domain_token = f"{_DOMAIN_PREFIX}{key}"
            tokens_by_owner[owner[0]].add(domain_token)
            tokens_by_owner[owner[0]].update(normalize_lexical(label))

    token_postings: dict[str, set[str]] = defaultdict(set)
    for owner_id, tokens in tokens_by_owner.items():
        for token in tokens:
            token_postings[token].add(owner_id)
    semantic_records = [
        record
        for record in records
        if record.kind not in {RecordKind.EVENT, RecordKind.EXECUTION_STATE}
    ]
    owner_authority: dict[str, Authority] = {}
    owner_activation: dict[str, Activation] = {}
    for record in semantic_records:
        current_authority = owner_authority.get(record.owner_id)
        if current_authority is None or AUTHORITY_RANK[record.authority] > AUTHORITY_RANK[current_authority]:
            owner_authority[record.owner_id] = record.authority
        current_activation = owner_activation.get(record.owner_id)
        if current_activation is None or _ACTIVATION_RANK[record.activation] > _ACTIVATION_RANK[current_activation]:
            owner_activation[record.owner_id] = record.activation
    return (
        freeze_string_tuple_mapping(
            {key: sorted(values) for key, values in sorted(token_postings.items())}
        ),
        freeze_string_tuple_mapping(
            {key: sorted(values) for key, values in sorted(domain_postings.items())}
        ),
        MappingProxyType(dict(sorted(owner_authority.items()))),
        MappingProxyType(dict(sorted(owner_activation.items()))),
    )


class DecisionContextRetrievalService:
    def __init__(self, policy: RetrievalPolicy = DEFAULT_RETRIEVAL_POLICY) -> None:
        self.policy = policy

    def retrieve(
        self,
        index: DecisionContextIndex,
        request: RetrievalRequest,
    ) -> DecisionContextPacket:
        selected_budget = budget_policy(request.budget)
        target_id = request.target_id.strip().upper()
        if target_id:
            query_tokens = self._target_tokens(index, target_id)
            if not query_tokens and target_id not in {node.node_id for node in index.nodes}:
                return self._empty_packet(index, request.budget, "target_not_cataloged")
        else:
            query_tokens = set(normalize_lexical(request.idea_text))
        if not query_tokens and not target_id:
            return self._empty_packet(index, request.budget, "no_meaningful_query_tokens")

        candidates = self._construct_candidates(index, target_id, query_tokens, selected_budget)
        hits = [
            hit
            for candidate in candidates
            if (hit := self._score_candidate(index, candidate, query_tokens, target_id)) is not None
        ]
        hits.sort(key=cmp_to_key(_compare_hits))
        if not hits:
            return self._empty_packet(index, request.budget, "no_relevant_context")
        return self._assemble_packet(index, tuple(hits), selected_budget)

    def _target_tokens(self, index: DecisionContextIndex, target_id: str) -> set[str]:
        record_map = index.record_map()
        tokens: set[str] = set()
        for record_id in index.records_by_owner.get(target_id, ()):
            record = record_map[record_id]
            if record.kind in _POSITIVE_QUERY_KINDS and not (
                record.activation == Activation.HISTORICAL and record.kind in _DECISION_KINDS
            ):
                tokens.update(normalize_lexical(record.text))
        for node in index.nodes:
            if node.node_id == target_id and node.node_type == NodeType.PROPOSAL:
                tokens.update(normalize_lexical(node.label))
        return tokens

    def _construct_candidates(
        self,
        index: DecisionContextIndex,
        target_id: str,
        query_tokens: set[str],
        selected_budget: BudgetPolicy,
    ) -> tuple[_Candidate, ...]:
        candidates: dict[str, _Candidate] = {}
        relation_map = index.relation_map()
        target_aliases = {target_id, f"decision:{target_id}"} if target_id else set()

        def candidate(owner_id: str, owner_type: NodeType) -> _Candidate | None:
            if not owner_id or owner_id == target_id:
                return None
            return candidates.setdefault(
                owner_id,
                _Candidate(owner_id, owner_type, set(), set(), set(), set(), set(), set()),
            )

        if target_id:
            direct_ids = set()
            for alias in target_aliases:
                direct_ids.update(index.incoming_relations.get(alias, ()))
                direct_ids.update(index.outgoing_relations.get(alias, ()))
            for relation_id in sorted(direct_ids):
                relation = relation_map[relation_id]
                other_id, other_type = _other_endpoint(relation, target_aliases)
                owner = _node_owner(other_id, other_type)
                if owner is None:
                    continue
                item = candidate(*owner)
                if item is None:
                    continue
                item.relation_ids.add(relation_id)
                item.direct_relation_types.add(relation.relation_type)

            if selected_budget.transitive_depth:
                for step in traverse_relations(
                    target_id,
                    index.relations,
                    max_depth=1 + selected_budget.transitive_depth,
                    fan_out=self.policy.candidate_limit,
                ):
                    if step.depth <= 1:
                        continue
                    node = next((value for value in index.nodes if value.node_id == step.node_id), None)
                    owner = _node_owner(step.node_id, node.node_type) if node is not None else None
                    if owner is None:
                        continue
                    item = candidate(*owner)
                    if item is None:
                        continue
                    item.relation_ids.update(step.relation_ids)
                    item.transitive = True

            target_domain_keys = set()
            for relation_id in direct_ids:
                relation = relation_map[relation_id]
                other_id, other_type = _other_endpoint(relation, target_aliases)
                if other_type in _DOMAIN_NODE_TYPES:
                    target_domain_keys.add(other_id)
            for value_id in target_domain_keys:
                value_type = next(
                    (node.node_type for node in index.nodes if node.node_id == value_id),
                    None,
                )
                if value_type is None:
                    continue
                label = value_id.split(":", 1)[-1]
                key = f"{value_type.value}:{label.casefold()}"
                for owner_id in index.domain_postings.get(key, ()):
                    owner_type = _owner_type(index, owner_id)
                    item = candidate(owner_id, owner_type)
                    if item is None:
                        continue
                    if value_type == NodeType.VERTICAL_SECTION:
                        item.shared_vertical.add(key)
                    else:
                        item.shared_domain.add(key)
                if value_type == NodeType.VERTICAL_SECTION:
                    section_tokens = normalize_lexical(label)
                    declared_owners = set(index.domain_postings.get(key, ()))
                    for token in section_tokens:
                        if _is_ubiquitous(
                            token, index.token_postings, max(len(index.owner_authority), 1)
                        ):
                            continue
                        for owner_id in index.token_postings.get(token, ()):
                            if owner_id in declared_owners:
                                continue
                            item = candidate(owner_id, _owner_type(index, owner_id))
                            if item is not None:
                                item.heuristic_vertical.add(key)

        for token in sorted(query_tokens):
            if _is_ubiquitous(token, index.token_postings, max(len(index.owner_authority), 1)):
                continue
            for owner_id in index.token_postings.get(token, ()):
                item = candidate(owner_id, _owner_type(index, owner_id))
                if item is not None:
                    item.matched_tokens.add(token)

        ordered = sorted(
            candidates.values(),
            key=lambda item: (
                -int(bool(item.direct_relation_types)),
                -len(item.shared_domain),
                -len(item.shared_vertical),
                -len(item.heuristic_vertical),
                -len(item.matched_tokens),
                item.owner_type.value,
                item.owner_id,
            ),
        )
        return tuple(ordered[: self.policy.candidate_limit])

    def _score_candidate(
        self,
        index: DecisionContextIndex,
        candidate: _Candidate,
        query_tokens: set[str],
        target_id: str,
    ) -> RetrievalHit | None:
        record_map = index.record_map()
        relation_map = index.relation_map()
        owner_records = [
            record_map[record_id]
            for record_id in index.records_by_owner.get(candidate.owner_id, ())
        ]
        activation = index.owner_activation.get(candidate.owner_id, Activation.INACTIVE)
        authority = index.owner_authority.get(candidate.owner_id, Authority.UNKNOWN)
        reasons: list[RetrievalReason] = []

        relation_types = {
            relation_map[relation_id].relation_type
            for relation_id in candidate.relation_ids
            if relation_id in relation_map
        }
        if relation_types & _BLOCKING_RELATIONS:
            reasons.append(
                RetrievalReason(
                    "blocker_or_conflict",
                    self.policy.signal_weights["blocker_or_conflict"],
                    f"Explicit blocker/conflict relation with {target_id or 'query'}.",
                )
            )
        elif candidate.relation_ids:
            reasons.append(
                RetrievalReason(
                    "explicit_relation",
                    self.policy.signal_weights["explicit_relation"],
                    "Explicit topology relation" + (" through one bounded hop." if candidate.transitive else "."),
                )
            )

        if candidate.shared_domain:
            reasons.append(
                RetrievalReason(
                    "shared_domain",
                    self.policy.signal_weights["shared_domain"],
                    "Shared declared capability or surface: " + ", ".join(sorted(candidate.shared_domain)),
                )
            )
        if candidate.shared_vertical:
            reasons.append(
                RetrievalReason(
                    "shared_vertical",
                    self.policy.signal_weights["shared_vertical"],
                    "Shared declared vertical section: " + ", ".join(sorted(candidate.shared_vertical)),
                )
            )
        if candidate.heuristic_vertical:
            reasons.append(
                RetrievalReason(
                    "heuristic_vertical",
                    self.policy.signal_weights["heuristic_vertical"],
                    "Heuristic vertical match: "
                    + ", ".join(sorted(candidate.heuristic_vertical)),
                )
            )

        lexical_score, lexical_qualifies = _lexical_score(
            query_tokens,
            candidate.matched_tokens,
            index.token_postings,
            max(len(index.owner_authority), 1),
            self.policy.signal_weights["lexical_overlap"],
        )
        if lexical_score:
            reasons.append(
                RetrievalReason(
                    "lexical_overlap",
                    lexical_score,
                    "Matched query tokens: " + ", ".join(sorted(candidate.matched_tokens)),
                )
            )

        has_applicable_decision = any(
            record.activation == Activation.ACTIVE
            and record.authority
            in {
                Authority.ACCEPTED_DECISION,
                Authority.CONDITIONALLY_ACCEPTED_DECISION,
                Authority.DECIDED_PROJECT_CHOICE,
                Authority.EXPLICIT_DECISION_PRECEDENT,
            }
            for record in owner_records
        )
        applicable = bool(candidate.relation_ids or candidate.shared_domain or candidate.shared_vertical or lexical_qualifies)
        if has_applicable_decision and applicable:
            reasons.append(
                RetrievalReason(
                    "applicable_decision",
                    self.policy.signal_weights["applicable_decision"],
                    "Active accepted decision, decided choice, or precedent is applicable.",
                )
            )

        if activation == Activation.EXPLORATORY:
            reasons.append(
                RetrievalReason(
                    "draft_penalty",
                    self.policy.signal_weights["draft_penalty"],
                    "Candidate is exploratory.",
                )
            )
        elif activation in {Activation.HISTORICAL, Activation.UNRESOLVED}:
            reasons.append(
                RetrievalReason(
                    "historical_penalty",
                    self.policy.signal_weights["historical_penalty"],
                    "Candidate is historical or unresolved.",
                )
            )

        score = max(
            self.policy.score_minimum,
            min(self.policy.score_maximum, sum(reason.contribution for reason in reasons)),
        )
        if score < self.policy.minimum_score:
            return None
        explicit_historical = bool(relation_types & _HISTORICAL_EXPLICIT_RELATIONS)
        if activation in {Activation.HISTORICAL, Activation.UNRESOLVED} and not explicit_historical:
            if score < self.policy.historical_threshold:
                return None

        selected_records = _selected_records(owner_records)
        selected_relation_ids = tuple(sorted(candidate.relation_ids))
        evidence_ids = {
            evidence_id for record in selected_records for evidence_id in record.evidence_ids
        }
        for relation_id in selected_relation_ids:
            evidence_ids.update(relation_map[relation_id].evidence_ids)
        canonical_dates = sorted(
            (record.canonical_date for record in selected_records if record.canonical_date),
            reverse=True,
        )
        return RetrievalHit(
            owner_id=candidate.owner_id,
            owner_type=candidate.owner_type,
            score=score,
            activation=activation,
            authority=authority,
            selected_record_ids=tuple(record.record_id for record in selected_records),
            selected_relation_ids=selected_relation_ids,
            decisions=_deduplicated_text(selected_records, _DECISION_KINDS),
            constraints=_deduplicated_text(selected_records, frozenset({RecordKind.CONSTRAINT})),
            non_goals=_deduplicated_text(selected_records, _NON_GOAL_KINDS),
            claims=_deduplicated_text(selected_records, _CLAIM_KINDS),
            reasons=tuple(sorted(reasons, key=lambda item: (-item.contribution, item.signal, item.detail))),
            evidence_ids=tuple(sorted(evidence_ids)),
            canonical_date=canonical_dates[0] if canonical_dates else "",
        )

    def _assemble_packet(
        self,
        index: DecisionContextIndex,
        hits: tuple[RetrievalHit, ...],
        selected_budget: BudgetPolicy,
    ) -> DecisionContextPacket:
        original_counts = _hit_counts(hits)
        retained: list[RetrievalHit] = []
        records_left = selected_budget.max_records
        relations_left = selected_budget.max_relations
        for hit in hits[: selected_budget.max_hits]:
            eligible_record_ids = hit.selected_record_ids
            if selected_budget.budget == ContextBudget.SMALL:
                record_map = index.record_map()
                eligible_record_ids = tuple(
                    record_id
                    for record_id in eligible_record_ids
                    if record_map[record_id].kind != RecordKind.NON_GOAL
                )
            selected_records = eligible_record_ids[:records_left]
            selected_relations = hit.selected_relation_ids[:relations_left]
            records_left -= len(selected_records)
            relations_left -= len(selected_relations)
            retained.append(
                _sync_hit(
                    replace(
                        hit,
                        selected_record_ids=selected_records,
                        selected_relation_ids=selected_relations,
                        reasons=_bounded_reasons(hit.reasons, selected_budget.max_reasons_per_hit),
                    ),
                    index,
                )
            )
        packet = self._packet(index, selected_budget, tuple(retained), original_counts, ())
        while _serialized_size(packet) > selected_budget.max_serialized_bytes and packet.hits:
            changed = False
            mutable = list(packet.hits)
            for index_value in range(len(mutable) - 1, -1, -1):
                if len(mutable[index_value].reasons) > 1:
                    mutable[index_value] = replace(
                        mutable[index_value],
                        reasons=_bounded_reasons(mutable[index_value].reasons, len(mutable[index_value].reasons) - 1),
                    )
                    changed = True
                    break
            if not changed:
                for index_value in range(len(mutable) - 1, -1, -1):
                    if mutable[index_value].claims:
                        mutable[index_value] = replace(mutable[index_value], claims=mutable[index_value].claims[:-1])
                        changed = True
                        break
            if not changed:
                for index_value in range(len(mutable) - 1, -1, -1):
                    if mutable[index_value].selected_relation_ids:
                        mutable[index_value] = _sync_hit(
                            replace(
                                mutable[index_value],
                                selected_relation_ids=mutable[index_value].selected_relation_ids[:-1],
                            ),
                            index,
                        )
                        changed = True
                        break
            if not changed:
                for index_value in range(len(mutable) - 1, -1, -1):
                    if len(mutable[index_value].selected_record_ids) > 1:
                        mutable[index_value] = _sync_hit(
                            replace(
                                mutable[index_value],
                                selected_record_ids=mutable[index_value].selected_record_ids[:-1],
                            ),
                            index,
                        )
                        changed = True
                        break
            if not changed:
                mutable.pop()
            packet = self._packet(index, selected_budget, tuple(mutable), original_counts, ())

        retained_counts = _hit_counts(packet.hits)
        truncated = retained_counts != original_counts
        diagnostics: tuple[DecisionContextDiagnostic, ...] = ()
        if truncated:
            diagnostics = (_retrieval_diagnostic("DC-RETRIEVAL-TRUNCATED", "Nearby context was truncated to budget."),)
        result = self._packet(index, selected_budget, packet.hits, original_counts, diagnostics)
        while _serialized_size(result) > selected_budget.max_serialized_bytes and result.hits:
            result = self._packet(
                index,
                selected_budget,
                result.hits[:-1],
                original_counts,
                diagnostics,
            )
        return result

    def _packet(
        self,
        index: DecisionContextIndex,
        selected_budget: BudgetPolicy,
        hits: tuple[RetrievalHit, ...],
        original_counts: Mapping[str, int],
        diagnostics: tuple[DecisionContextDiagnostic, ...],
    ) -> DecisionContextPacket:
        retained_counts = _hit_counts(hits)
        evidence_map = index.evidence_map()
        evidence_ids = {evidence_id for hit in hits for evidence_id in hit.evidence_ids}
        evidence = tuple(
            sorted(
                (evidence_map[evidence_id] for evidence_id in evidence_ids if evidence_id in evidence_map),
                key=lambda item: (item.source_path, item.fragment_id, item.evidence_id),
            )
        )
        return DecisionContextPacket(
            schema_version=index.schema_version,
            retrieval_policy_version=self.policy.version,
            budget_policy_version=selected_budget.version,
            budget=selected_budget.budget,
            source_fingerprint_sha256=index.source_fingerprint_sha256,
            semantic_fingerprint_sha256=index.semantic_fingerprint_sha256,
            completeness=index.completeness,
            hits=hits,
            evidence=evidence,
            diagnostics=_packet_diagnostics(index, diagnostics),
            truncation=TruncationMetadata(
                truncated=dict(retained_counts) != dict(original_counts),
                original_counts=MappingProxyType(dict(original_counts)),
                retained_counts=MappingProxyType(dict(retained_counts)),
            ),
        )

    def _empty_packet(
        self,
        index: DecisionContextIndex,
        budget: ContextBudget,
        reason: str,
    ) -> DecisionContextPacket:
        counts = MappingProxyType({"hits": 0, "records": 0, "relations": 0, "reasons": 0})
        return DecisionContextPacket(
            schema_version=index.schema_version,
            retrieval_policy_version=self.policy.version,
            budget_policy_version=budget_policy(budget).version,
            budget=budget,
            source_fingerprint_sha256=index.source_fingerprint_sha256,
            semantic_fingerprint_sha256=index.semantic_fingerprint_sha256,
            completeness=index.completeness,
            hits=(),
            evidence=(),
            diagnostics=(
                _retrieval_diagnostic("DC-RETRIEVAL-EMPTY", f"No nearby context: {reason}."),
            )
            + (
                (_index_partial_diagnostic(index),)
                if index.completeness == Completeness.PARTIAL
                else ()
            ),
            truncation=TruncationMetadata(False, counts, counts),
            empty_reason=reason,
        )


def _node_owner(node_id: str, node_type: NodeType) -> tuple[str, NodeType] | None:
    if node_type == NodeType.DECISION and node_id.startswith("decision:PROP-"):
        return node_id.split(":", 1)[1], NodeType.PROPOSAL
    if node_type in _IDENTITY_NODE_TYPES:
        return node_id, node_type
    return None


def _owner_type(index: DecisionContextIndex, owner_id: str) -> NodeType:
    for node in index.nodes:
        owner = _node_owner(node.node_id, node.node_type)
        if owner is not None and owner[0] == owner_id:
            return owner[1]
    records = [record for record in index.records if record.owner_id == owner_id]
    return records[0].owner_type if records else NodeType.PROPOSAL


def _other_endpoint(
    relation: DecisionContextRelation,
    target_aliases: set[str],
) -> tuple[str, NodeType]:
    if relation.source_id in target_aliases:
        return relation.target_id, relation.target_type
    return relation.source_id, relation.source_type


def _lexical_score(
    query_tokens: set[str],
    matched_tokens: set[str],
    postings: Mapping[str, tuple[str, ...]],
    owner_count: int,
    maximum: int,
) -> tuple[int, bool]:
    if not query_tokens or not matched_tokens:
        return 0, False
    rare_threshold = max(2, math.ceil(owner_count / 10))

    def weight(token: str) -> int:
        if token.startswith(_DOMAIN_PREFIX) or token.startswith(("proposal:", "choice:", "tag:")):
            return 3
        return 2 if len(postings.get(token, ())) <= rare_threshold else 1

    meaningful_tokens = {
        token for token in query_tokens if not _is_ubiquitous(token, postings, owner_count)
    }
    denominator = sum(weight(token) for token in meaningful_tokens)
    if denominator <= 0:
        return 0, False
    matched = meaningful_tokens & matched_tokens
    numerator = sum(weight(token) for token in matched)
    score = math.floor(maximum * numerator / denominator)
    qualifies = score >= 10 and any(weight(token) >= 2 for token in matched)
    return score, qualifies


def _is_ubiquitous(
    token: str,
    postings: Mapping[str, tuple[str, ...]],
    owner_count: int,
) -> bool:
    if token.startswith(_DOMAIN_PREFIX) or owner_count < 10:
        return False
    return len(postings.get(token, ())) >= math.ceil(owner_count * 0.60)


def _selected_records(records: Sequence[DecisionContextRecord]) -> tuple[DecisionContextRecord, ...]:
    useful = [
        record
        for record in records
        if record.kind in (_DECISION_KINDS | _CLAIM_KINDS | _NON_GOAL_KINDS | {RecordKind.CONSTRAINT})
    ]
    useful.sort(
        key=lambda record: (
            -int(record.kind in _DECISION_KINDS),
            -int(record.kind == RecordKind.CONSTRAINT),
            -AUTHORITY_RANK[record.authority],
            record.kind.value,
            record.record_id,
        )
    )
    seen: set[tuple[RecordKind, str]] = set()
    selected = []
    for record in useful:
        key = (record.kind, unicodedata.normalize("NFKC", record.text).casefold().strip())
        if key in seen:
            continue
        seen.add(key)
        selected.append(record)
    return tuple(selected)


def _deduplicated_text(
    records: Sequence[DecisionContextRecord],
    kinds: frozenset[RecordKind],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for record in records:
        if record.kind not in kinds:
            continue
        key = unicodedata.normalize("NFKC", record.text).casefold().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(record.text)
    return tuple(result)


def _sync_hit(hit: RetrievalHit, index: DecisionContextIndex) -> RetrievalHit:
    record_map = index.record_map()
    relation_map = index.relation_map()
    records = [record_map[item] for item in hit.selected_record_ids if item in record_map]
    evidence_ids = {evidence_id for record in records for evidence_id in record.evidence_ids}
    for relation_id in hit.selected_relation_ids:
        if relation_id in relation_map:
            evidence_ids.update(relation_map[relation_id].evidence_ids)
    return replace(
        hit,
        decisions=_deduplicated_text(records, _DECISION_KINDS),
        constraints=_deduplicated_text(records, frozenset({RecordKind.CONSTRAINT})),
        non_goals=_deduplicated_text(records, _NON_GOAL_KINDS),
        claims=_deduplicated_text(records, _CLAIM_KINDS),
        evidence_ids=tuple(sorted(evidence_ids)),
    )


def _compare_hits(left: RetrievalHit, right: RetrievalHit) -> int:
    for left_value, right_value in (
        (left.score, right.score),
        (AUTHORITY_RANK[left.authority], AUTHORITY_RANK[right.authority]),
        (int(any(reason.signal != "heuristic_vertical" for reason in left.reasons)), int(any(reason.signal != "heuristic_vertical" for reason in right.reasons))),
        (_ACTIVATION_RANK[left.activation], _ACTIVATION_RANK[right.activation]),
    ):
        if left_value != right_value:
            return -1 if left_value > right_value else 1
    if left.canonical_date and right.canonical_date and left.canonical_date != right.canonical_date:
        return -1 if left.canonical_date > right.canonical_date else 1
    left_key = (left.owner_type.value, left.owner_id)
    right_key = (right.owner_type.value, right.owner_id)
    return -1 if left_key < right_key else 1 if left_key > right_key else 0


def _hit_counts(hits: Sequence[RetrievalHit]) -> Mapping[str, int]:
    return {
        "hits": len(hits),
        "records": sum(len(hit.selected_record_ids) for hit in hits),
        "relations": sum(len(hit.selected_relation_ids) for hit in hits),
        "reasons": sum(len(hit.reasons) for hit in hits),
    }


def _bounded_reasons(
    reasons: Sequence[RetrievalReason],
    maximum: int,
) -> tuple[RetrievalReason, ...]:
    ordered = tuple(reasons)
    if len(ordered) <= maximum:
        return ordered
    if maximum <= 1:
        return (
            RetrievalReason(
                "combined_signals",
                sum(reason.contribution for reason in ordered),
                "Combined signals: " + ", ".join(reason.signal for reason in ordered),
            ),
        )
    retained = ordered[: maximum - 1]
    omitted = ordered[maximum - 1 :]
    return retained + (
        RetrievalReason(
            "combined_signals",
            sum(reason.contribution for reason in omitted),
            "Combined signals: " + ", ".join(reason.signal for reason in omitted),
        ),
    )


def _serialized_size(packet: DecisionContextPacket) -> int:
    payload = json.dumps(
        to_json_ready(packet),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return len(payload.encode("utf-8"))


def serialized_packet_size(packet: DecisionContextPacket) -> int:
    return _serialized_size(packet)


def _retrieval_diagnostic(code: str, message: str) -> DecisionContextDiagnostic:
    return DecisionContextDiagnostic(
        diagnostic_id=f"diagnostic:{code.casefold()}",
        code=code,
        severity=DiagnosticSeverity.ADVISORY,
        fatal=False,
        message=message,
        recovery="Refine the target, idea text, or source relations.",
    )


def _packet_diagnostics(
    index: DecisionContextIndex,
    diagnostics: tuple[DecisionContextDiagnostic, ...],
) -> tuple[DecisionContextDiagnostic, ...]:
    if index.completeness != Completeness.PARTIAL:
        return diagnostics
    if any(item.code == "DC-INDEX-PARTIAL" for item in diagnostics):
        return diagnostics
    return diagnostics + (_index_partial_diagnostic(index),)


def _index_partial_diagnostic(index: DecisionContextIndex) -> DecisionContextDiagnostic:
    return _retrieval_diagnostic(
        "DC-INDEX-PARTIAL",
        f"Decision context index is partial ({len(index.diagnostics)} source diagnostics).",
    )

from __future__ import annotations

from dataclasses import dataclass


DERIVED_FRESHNESS_GRAPH_VERSION = 1


@dataclass(frozen=True)
class FreshnessNodeDefinition:
    node_id: str
    dependencies: tuple[str, ...]
    ownership: str
    action_class: str
    command: str
    output_patterns: tuple[str, ...]
    missing_primitive: str = ""


@dataclass(frozen=True)
class FreshnessNode:
    node_id: str
    status: str
    dependencies: tuple[str, ...]
    ownership: str
    action_class: str
    current_fingerprint_sha256: str
    recorded_source_fingerprint_sha256: str
    source_count: int
    output_count: int
    output_paths: tuple[str, ...]
    reasons: tuple[str, ...]
    command: str
    missing_primitive: str = ""


@dataclass(frozen=True)
class FreshnessRebuildAction:
    order: int
    node_id: str
    action_class: str
    command: str
    automatic: bool
    blocked_by: tuple[str, ...]
    missing_primitive: str = ""


@dataclass(frozen=True)
class DerivedFreshnessStatus:
    graph_version: int
    status: str
    canonical_fingerprint_sha256: str
    nodes: tuple[FreshnessNode, ...]
    rebuild_plan: tuple[FreshnessRebuildAction, ...]

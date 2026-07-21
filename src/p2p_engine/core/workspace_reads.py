from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


@dataclass(frozen=True)
class CapturedDocument:
    relative_path: str
    exists: bool
    physical_sha256: str | None
    size: int
    mtime_ns_observed: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "exists": self.exists,
            "physical_sha256": self.physical_sha256,
            "size": self.size,
            "mtime_ns_observed": self.mtime_ns_observed,
        }


@dataclass(frozen=True)
class ProviderKey:
    name: str
    arguments: tuple[object, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "arguments": list(self.arguments)}


@dataclass(frozen=True)
class DirectoryEntrySnapshot:
    relative_path: str
    is_directory: bool
    size: int
    mtime_ns_observed: int


@dataclass(frozen=True)
class DirectorySnapshot:
    relative_path: str
    entries: tuple[DirectoryEntrySnapshot, ...]


@dataclass(frozen=True)
class ReadOperationCounters:
    discovery_passes: Mapping[str, int] = field(default_factory=dict)
    source_reads: Mapping[str, int] = field(default_factory=dict)
    verification_reads: Mapping[str, int] = field(default_factory=dict)
    source_hashes: Mapping[str, int] = field(default_factory=dict)
    yaml_parses: Mapping[str, int] = field(default_factory=dict)
    provider_calls: Mapping[str, int] = field(default_factory=dict)
    provider_cache_hits: Mapping[str, int] = field(default_factory=dict)
    schema_preflights: int = 0
    schema_deep_validations: int = 0
    ledger_parses: Mapping[str, int] = field(default_factory=dict)
    vertical_pack_loads: Mapping[str, int] = field(default_factory=dict)
    canonical_fallbacks: Mapping[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "discovery_passes": dict(self.discovery_passes),
            "source_reads": dict(self.source_reads),
            "verification_reads": dict(self.verification_reads),
            "source_hashes": dict(self.source_hashes),
            "yaml_parses": dict(self.yaml_parses),
            "provider_calls": dict(self.provider_calls),
            "provider_cache_hits": dict(self.provider_cache_hits),
            "schema_preflights": self.schema_preflights,
            "schema_deep_validations": self.schema_deep_validations,
            "ledger_parses": dict(self.ledger_parses),
            "vertical_pack_loads": dict(self.vertical_pack_loads),
            "canonical_fallbacks": dict(self.canonical_fallbacks),
        }


@dataclass(frozen=True)
class ReadConsistencyResult:
    status: str
    changed_paths: tuple[str, ...] = ()
    changed_directories: tuple[str, ...] = ()
    diagnostic_code: str = ""

    @property
    def current(self) -> bool:
        return self.status == "current"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "changed_paths": list(self.changed_paths),
            "changed_directories": list(self.changed_directories),
            "diagnostic_code": self.diagnostic_code,
        }


@dataclass(frozen=True)
class FastVerification:
    validation: str = "not_run"
    freshness: str = "not_run"
    source: str = "canonical"

    def to_dict(self) -> dict[str, str]:
        return {
            "validation": self.validation,
            "freshness": self.freshness,
            "source": self.source,
        }


class ReadCostClass(StrEnum):
    FAST = "fast"
    TARGETED = "targeted"
    DEEP = "deep"


@dataclass(frozen=True)
class PublicReadCostPolicy:
    operation: str
    cost_class: ReadCostClass
    allowed_providers: tuple[str, ...]
    forbidden_providers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "cost_class": self.cost_class.value,
            "allowed_providers": list(self.allowed_providers),
            "forbidden_providers": list(self.forbidden_providers),
        }


@dataclass(frozen=True)
class FastFreshnessSummary:
    status: str
    schema_state: str
    registry_state: str
    vertical_memory_state: str
    project_projection_state: str
    attention: tuple[str, ...] = ()
    next_command: str = "p2p project freshness"
    next_node: str = ""
    next_action_class: str = "deterministic"
    verification: str = "fast_checked"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "schema_state": self.schema_state,
            "registry_state": self.registry_state,
            "vertical_memory_state": self.vertical_memory_state,
            "project_projection_state": self.project_projection_state,
            "attention": list(self.attention),
            "attention_nodes": len(self.attention),
            "next_node": self.next_node or (self.attention[0] if self.attention else ""),
            "next_command": self.next_command,
            "next_action_class": self.next_action_class,
            "verification": self.verification,
        }

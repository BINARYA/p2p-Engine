from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from p2p_engine.core.workspace_schema import (
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    LEGACY_WORKSPACE_VERSION,
    TransitionRuntimeSupport,
)


KNOWN_TRANSITION_CAPABILITIES = frozenset(
    {
        "candidate_overlay",
        "durable_transactions",
        "exclusive_migration_lock",
        "semantic_plan_hashes",
        "stateless_preview",
    }
)


@dataclass(frozen=True)
class MigrationTransition:
    migration_id: str
    source_version: int
    target_version: int
    inspect_requires: str
    plan_requires: str
    apply_requires: str
    capabilities: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    required_owner_inputs: tuple[str, ...] = ()

    def runtime_support(self, engine_version: str) -> TransitionRuntimeSupport:
        return TransitionRuntimeSupport(
            inspect=_supports(engine_version, self.inspect_requires),
            plan=_supports(engine_version, self.plan_requires),
            apply=_supports(engine_version, self.apply_requires),
            inspect_requires=self.inspect_requires,
            plan_requires=self.plan_requires,
            apply_requires=self.apply_requires,
            capabilities=self.capabilities,
        )


class WorkspaceMigrationRegistry:
    def __init__(
        self,
        transitions: Iterable[MigrationTransition] | None = None,
        *,
        current_version: int = CURRENT_WORKSPACE_SCHEMA_VERSION,
    ) -> None:
        self.current_version = current_version
        self._transitions = tuple(transitions or default_workspace_migrations())
        self._validate()

    @property
    def transitions(self) -> tuple[MigrationTransition, ...]:
        return self._transitions

    @property
    def migration_ids(self) -> frozenset[str]:
        return frozenset(item.migration_id for item in self._transitions)

    def transition_by_id(self, migration_id: str) -> MigrationTransition:
        for transition in self._transitions:
            if transition.migration_id == migration_id:
                return transition
        raise ValueError(f"Unknown workspace migration id: {migration_id}")

    def resolve_path(self, source_version: int, target_version: int) -> tuple[MigrationTransition, ...]:
        if target_version < source_version:
            raise ValueError("P2P310_UNSUPPORTED_DOWNGRADE: workspace migrations are forward-only")
        if target_version > self.current_version:
            raise ValueError(
                f"P2P311_UNSUPPORTED_TARGET: runtime supports workspace schema {self.current_version}"
            )
        if source_version == target_version:
            return ()

        by_source = {item.source_version: item for item in self._transitions}
        resolved: list[MigrationTransition] = []
        version = source_version
        while version < target_version:
            transition = by_source.get(version)
            if transition is None or transition.target_version > target_version:
                raise ValueError(
                    f"P2P312_MISSING_TRANSITION: no adjacent transition from workspace schema {version}"
                )
            resolved.append(transition)
            version = transition.target_version
        if version != target_version:
            raise ValueError(f"P2P312_MISSING_TRANSITION: cannot reach workspace schema {target_version}")
        return tuple(resolved)

    def _validate(self) -> None:
        ids: set[str] = set()
        sources: set[int] = set()
        for transition in self._transitions:
            if not transition.migration_id.strip():
                raise ValueError("Workspace migration id is required")
            if transition.migration_id in ids:
                raise ValueError(f"Duplicate workspace migration id: {transition.migration_id}")
            ids.add(transition.migration_id)
            if transition.source_version in sources:
                raise ValueError(
                    f"Ambiguous workspace migration source version: {transition.source_version}"
                )
            sources.add(transition.source_version)
            if transition.target_version != transition.source_version + 1:
                raise ValueError(
                    f"Workspace migrations must be adjacent and forward-only: {transition.migration_id}"
                )
            for requirement in (
                transition.inspect_requires,
                transition.plan_requires,
                transition.apply_requires,
            ):
                try:
                    SpecifierSet(requirement)
                except InvalidSpecifier as exc:
                    raise ValueError(
                        f"Invalid runtime requirement for {transition.migration_id}: {requirement}"
                    ) from exc
            unknown = set(transition.capabilities) - KNOWN_TRANSITION_CAPABILITIES
            if unknown:
                raise ValueError(
                    f"Unknown workspace migration capabilities for {transition.migration_id}: "
                    + ", ".join(sorted(unknown))
                )
            if set(transition.dependencies) - ids:
                raise ValueError(
                    f"Workspace migration {transition.migration_id} has an unknown or forward dependency"
                )

        if self.current_version > LEGACY_WORKSPACE_VERSION:
            self.resolve_path(LEGACY_WORKSPACE_VERSION, self.current_version)


def default_workspace_migrations() -> tuple[MigrationTransition, ...]:
    return (
        MigrationTransition(
            migration_id="workspace-legacy-to-v1",
            source_version=0,
            target_version=1,
            inspect_requires=">=0.2.0,<0.3.0",
            plan_requires=">=0.2.0,<0.3.0",
            apply_requires=">=0.2.0,<0.3.0",
            capabilities=(
                "candidate_overlay",
                "durable_transactions",
                "exclusive_migration_lock",
                "semantic_plan_hashes",
                "stateless_preview",
            ),
            required_owner_inputs=(),
        ),
    )


def _supports(engine_version: str, requirement: str) -> bool:
    try:
        return Version(engine_version) in SpecifierSet(requirement)
    except (InvalidSpecifier, InvalidVersion):
        return False

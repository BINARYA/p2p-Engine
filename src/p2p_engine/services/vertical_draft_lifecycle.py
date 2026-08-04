from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re

from p2p_engine.core.portable_verticals import PORTABLE_VERTICAL_SCHEMA_VERSION
from p2p_engine.core.vertical_drafts import (
    VerticalDraftEvidence,
    VerticalDraftOperationResult,
)
from p2p_engine.core.vertical_registry import (
    VerticalRelease,
    VerticalReleaseArtifact,
    VerticalReleaseDependency,
)
from p2p_engine.services.vertical_catalog import VerticalCacheService, _file_digest
from p2p_engine.services.vertical_draft_materializer import (
    VerticalDraftMaterializer,
    vertical_draft_roundtrip_shape,
)
from p2p_engine.services.vertical_drafts import (
    VerticalDraftService,
    document_diagnostics,
)
from p2p_engine.services.vertical_registry import VerticalRegistryClient
from p2p_engine.storage.filesystem import P2PWorkspace


class VerticalDraftLifecycleService:
    def __init__(
        self,
        root: Path,
        *,
        drafts: VerticalDraftService | None = None,
        cache: VerticalCacheService | None = None,
        client: VerticalRegistryClient | None = None,
    ) -> None:
        self.root = root.resolve()
        self.workspace = P2PWorkspace(self.root)
        self.drafts = drafts or VerticalDraftService(self.root)
        self.cache = cache or self.drafts.catalog.cache
        self.client = client
        self.materializer = VerticalDraftMaterializer(self.workspace)

    def materialize(self, draft_id: str, target: Path) -> VerticalDraftOperationResult:
        changed: list[str] = []

        def apply(state, evidence):
            assessment = self.drafts.assess(state, evidence)
            blockers = [item for item in assessment.diagnostics if item.severity == "error"]
            if blockers:
                first = blockers[0]
                raise ValueError(f"{first.code}: {first.field}: {first.message}")
            inspection = self.materializer.materialize(state.document, target)
            resolved_target = Path(inspection.target).resolve()
            changed.append(str(resolved_target))
            return replace(
                evidence,
                materialization={
                    "revision": state.revision,
                    "document_hash": state.document_hash,
                    "target": str(resolved_target),
                    "coordinate": inspection.pack.coordinate,
                    "semantic_checksum": inspection.semantic_checksum,
                    "entries": list(inspection.entries),
                },
                validation=None,
                package=None,
                local_adds=(),
                publications=(),
                last_publication_failure=None,
            )

        view = self.drafts.replace_evidence(draft_id, apply)
        changed.append(str(view.state.path / "evidence.yml"))
        return VerticalDraftOperationResult(
            operation="materialize",
            draft=view,
            changed_paths=tuple(changed),
        )

    def validate(self, draft_id: str) -> VerticalDraftOperationResult:
        def apply(state, evidence):
            diagnostics = [item.to_dict() for item in document_diagnostics(
                state.document,
                origin=state.origin,
            )]
            materialization = evidence.materialization or {}
            target = Path(str(materialization.get("target") or ""))
            inspection = None
            if not materialization:
                diagnostics.append(
                    _diagnostic(
                        "P2P_VERTICAL_DRAFT_NOT_MATERIALIZED",
                        "materialization",
                        "materialize the current draft revision before validation",
                    )
                )
            else:
                try:
                    inspection = self.workspace.inspect_portable_vertical(
                        target,
                        view="effective",
                    )
                    roundtrip = self.materializer.normalized_from_materialized(
                        self.workspace,
                        target,
                    )
                    if vertical_draft_roundtrip_shape(
                        roundtrip
                    ) != vertical_draft_roundtrip_shape(state.document):
                        diagnostics.append(
                            _diagnostic(
                                "P2P_VERTICAL_DRAFT_ROUNDTRIP_MISMATCH",
                                "materialization",
                                "materialized content differs from the current normalized document",
                            )
                        )
                    if (
                        inspection.pack.coordinate
                        != str(materialization.get("coordinate") or "")
                        or inspection.semantic_checksum
                        != str(materialization.get("semantic_checksum") or "")
                    ):
                        diagnostics.append(
                            _diagnostic(
                                "P2P_VERTICAL_DRAFT_MATERIALIZATION_DRIFT",
                                "materialization",
                                "materialized pack changed after materialization",
                            )
                        )
                except ValueError as exc:
                    diagnostics.append(
                        _diagnostic(
                            _error_code(exc, "P2P_VERTICAL_DRAFT_MATERIALIZATION_INVALID"),
                            "materialization",
                            str(exc),
                        )
                    )
            valid = not any(item["severity"] == "error" for item in diagnostics)
            validation = {
                "revision": state.revision,
                "document_hash": state.document_hash,
                "valid": valid,
                "readiness": self.drafts.assess(state, evidence).readiness,
                "publishable": False,
                "coordinate": inspection.pack.coordinate if inspection else "",
                "semantic_checksum": inspection.semantic_checksum if inspection else "",
                "materialization_target": str(target) if materialization else "",
                "diagnostics": diagnostics,
            }
            return replace(
                evidence,
                validation=validation,
                package=None,
                local_adds=(),
                publications=(),
                last_publication_failure=None,
            )

        view = self.drafts.replace_evidence(draft_id, apply)
        return VerticalDraftOperationResult(
            operation="validate",
            draft=view,
            changed_paths=(str(view.state.path / "evidence.yml"),),
        )

    def package(
        self,
        draft_id: str,
        output: Path,
    ) -> VerticalDraftOperationResult:
        changed: list[str] = []

        def apply(state, evidence):
            materialization = evidence.materialization or {}
            validation = evidence.validation or {}
            if not materialization or validation.get("valid") is not True:
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_NOT_VALIDATED: current materialization must validate before packaging"
                )
            target = Path(str(materialization.get("target") or ""))
            inspection = self.workspace.inspect_portable_vertical(target, view="effective")
            if (
                inspection.semantic_checksum
                != str(validation.get("semantic_checksum") or "")
            ):
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_MATERIALIZATION_DRIFT: validate the materialized pack again"
                )
            result = self.workspace.package_portable_vertical(target, output=output)
            changed.append(str(result.path.resolve()))
            return replace(
                evidence,
                package={
                    "revision": state.revision,
                    "document_hash": state.document_hash,
                    "path": str(result.path.resolve()),
                    "coordinate": result.coordinate,
                    "artifact_checksum": result.artifact_checksum,
                    "semantic_checksum": result.semantic_checksum,
                    "size": result.size,
                    "entries": list(result.entries),
                },
                local_adds=(),
                publications=(),
                last_publication_failure=None,
            )

        view = self.drafts.replace_evidence(draft_id, apply)
        changed.append(str(view.state.path / "evidence.yml"))
        return VerticalDraftOperationResult(
            operation="package",
            draft=view,
            changed_paths=tuple(changed),
        )

    def add_local(self, draft_id: str) -> VerticalDraftOperationResult:
        changed: list[str] = []

        def apply(state, evidence):
            assessment = self.drafts.assess(state, evidence)
            if not assessment.publishable:
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_NOT_PUBLISHABLE: validate and package the complete draft first"
                )
            release, artifact = self._release(state.document, evidence, registry="local")
            status, cached = self.cache.add_local(release, artifact)
            receipt = {
                "revision": state.revision,
                "document_hash": state.document_hash,
                "status": status,
                "coordinate": release.coordinate,
                "semantic_checksum": release.semantic_checksum,
                "artifact_checksum": release.artifact.sha256,
                "artifact_path": str(cached.artifact_path),
            }
            additions = tuple(
                item
                for item in evidence.local_adds
                if item.get("artifact_checksum") != release.artifact.sha256
            ) + (receipt,)
            changed.extend((str(cached.artifact_path), str(cached.metadata_path)))
            return replace(evidence, local_adds=additions)

        view = self.drafts.replace_evidence(draft_id, apply)
        changed.append(str(view.state.path / "evidence.yml"))
        return VerticalDraftOperationResult(
            operation="add-local",
            draft=view,
            changed_paths=tuple(changed),
        )

    def publish(
        self,
        draft_id: str,
        *,
        registry: str = "",
        idempotency_key: str,
    ) -> VerticalDraftOperationResult:
        if self.client is None:
            raise ValueError(
                "P2P_REGISTRY_NOT_CONFIGURED: remote publication client is unavailable"
            )
        failure: list[ValueError] = []

        def apply(state, evidence):
            assessment = self.drafts.assess(state, evidence)
            if not assessment.publishable:
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_NOT_PUBLISHABLE: validate and package the complete draft first"
                )
            registry_name = self.client.configuration.resolve(registry).name
            release, artifact = self._release(
                state.document,
                evidence,
                registry=registry_name,
            )
            try:
                receipt = self.client.publish(
                    release,
                    artifact,
                    registry=registry_name,
                    lineage=dict(state.document.get("lineage") or {}),
                    idempotency_key=idempotency_key,
                )
            except ValueError as exc:
                failure.append(exc)
                return replace(
                    evidence,
                    last_publication_failure={
                        "revision": state.revision,
                        "document_hash": state.document_hash,
                        "registry": registry_name,
                        "code": _error_code(exc, "P2P_REGISTRY_PUBLICATION_FAILED"),
                        "message": _redacted_failure(exc),
                    },
                )
            publication = {
                "revision": state.revision,
                "document_hash": state.document_hash,
                **receipt.to_dict(),
            }
            publications = tuple(
                item
                for item in evidence.publications
                if not (
                    item.get("registry") == receipt.registry
                    and item.get("receipt_id") == receipt.receipt_id
                )
            ) + (publication,)
            return replace(
                evidence,
                publications=publications,
                last_publication_failure=None,
            )

        view = self.drafts.replace_evidence(draft_id, apply)
        if failure:
            raise failure[0]
        return VerticalDraftOperationResult(
            operation="publish",
            draft=view,
            changed_paths=(str(view.state.path / "evidence.yml"),),
        )

    @staticmethod
    def _release(
        document: dict[str, object],
        evidence: VerticalDraftEvidence,
        *,
        registry: str,
    ) -> tuple[VerticalRelease, Path]:
        package = evidence.package or {}
        identity = document.get("identity")
        if not isinstance(identity, dict):  # pragma: no cover - normalized contract invariant.
            raise ValueError("P2P_VERTICAL_DRAFT_INVALID: identity is missing")
        artifact = Path(str(package.get("path") or ""))
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError(
                "P2P_VERTICAL_DRAFT_PACKAGE_DRIFT: packaged artifact is missing or unsafe"
            )
        digest, size = _file_digest(artifact)
        if (
            digest != str(package.get("artifact_checksum") or "")
            or size != int(package.get("size") or 0)
        ):
            raise ValueError(
                "P2P_VERTICAL_DRAFT_PACKAGE_DRIFT: packaged artifact changed after validation"
            )
        dependencies = tuple(
            VerticalReleaseDependency(
                coordinate=str(item["coordinate"]),
                semantic_checksum=str(item["semantic_checksum"]),
            )
            for item in document.get("dependencies", [])
            if isinstance(item, dict)
        )
        release = VerticalRelease(
            coordinate=str(package.get("coordinate") or ""),
            name=str(document.get("name") or ""),
            description=str(document.get("description") or ""),
            visibility=str(document.get("visibility") or "private"),
            semantic_checksum=str(package.get("semantic_checksum") or ""),
            schema_version=PORTABLE_VERTICAL_SCHEMA_VERSION,
            artifact=VerticalReleaseArtifact(
                url=artifact.name,
                sha256=digest,
                size=size,
            ),
            dependencies=dependencies,
            registry=registry,
        )
        return release, artifact


def _diagnostic(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message, "severity": "error"}


def _error_code(exc: ValueError, fallback: str) -> str:
    prefix = str(exc).split(":", 1)[0]
    return prefix if re.fullmatch(r"P2P_[A-Z0-9_]+", prefix) else fallback


def _redacted_failure(exc: ValueError) -> str:
    message = str(exc).replace("\r", " ").replace("\n", " ")
    return message[:512]

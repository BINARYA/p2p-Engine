from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import re
from typing import Mapping

from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.mutation_receipts import MutationReceipt
from p2p_engine.core.portable_verticals import (
    VerticalLifecyclePreview,
    VerticalLifecycleResult,
    VerticalCoordinate,
)
from p2p_engine.core.project_verticals import (
    VerticalDependency,
    VerticalMigrationCandidate,
    VerticalPack,
)
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.core.vertical_transition_impact import (
    BoundedCollection,
    InstallDisposition,
    InstallImpact,
    IssueSeverity,
    TransitionIssue,
    VERTICAL_TRANSITION_COLLECTION_LIMIT,
    VERTICAL_TRANSITION_IMPACT_CONTRACT,
    VERTICAL_TRANSITION_TOTAL_ITEM_LIMIT,
    VerticalIdentity,
    VerticalTransitionImpact,
    impact_fingerprint,
)
from p2p_engine.core.vertical_transition_plan import (
    VerticalTransitionPlan,
    parse_transition_plan,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.mutation_receipts import MutationReceiptService
from p2p_engine.services.vertical_evidence_classifier import VerticalEvidenceClassifier
from p2p_engine.services.vertical_transition_analysis import VerticalTransitionAnalysisService
from p2p_engine.services.vertical_transition_materialization import (
    VerticalTransitionMaterializationService,
)
from p2p_engine.services.vertical_packages import (
    PortableVerticalPackageService,
    normalize_expected_checksum,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


class VerticalLifecycleService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        vertical_service: ProjectVerticalService,
        package_service: PortableVerticalPackageService,
        atomic_writer: AtomicMutationWriter | None = None,
        receipt_service: MutationReceiptService | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.vertical_service = vertical_service
        self.package_service = package_service
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)
        self.receipt_service = receipt_service or MutationReceiptService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )

    def install_preview(
        self,
        artifact: Path,
        *,
        expected_checksum: str,
        actor: str = "local",
    ) -> VerticalLifecyclePreview:
        artifact = artifact if artifact.is_absolute() else self.root / artifact
        expected = normalize_expected_checksum(expected_checksum)
        inspection = self.package_service.inspect(artifact, view="effective")
        actual = inspection.artifact_checksum
        if not actual or actual != expected:
            raise ValueError(
                f"P2P_VERTICAL_CHECKSUM_MISMATCH: expected {expected}, got {actual or 'none'}"
            )
        coordinate = inspection.pack.coordinate
        if not coordinate:
            raise ValueError("P2P_VERTICAL_PORTABLE_V3_REQUIRED: artifact has no exact coordinate")
        closure = self._dependency_closure(inspection.pack)
        entries = self.package_service.read_archive(artifact)
        prefix = self._install_prefix(VerticalCoordinate.parse(coordinate))
        candidates = {f"{prefix}/{name}": content for name, content in entries.items()}
        blockers: list[TransitionIssue] = []
        try:
            existing_resolution = self.vertical_service.resolve_pack(coordinate)
        except ValueError:
            existing_resolution = None
        if existing_resolution is not None and existing_resolution.checksum != inspection.semantic_checksum:
            blockers.append(
                TransitionIssue(
                    code="P2P_VERTICAL_INSTALL_CONFLICT",
                    severity=IssueSeverity.BLOCKER,
                    category="install_conflict",
                    reference=coordinate,
                    recovery_action="Choose a different coordinate or remove the conflicting local pack.",
                )
            )
        target_root = self.root / prefix
        existing = self._installed_files(target_root)
        expected_existing = {
            (target_root / name).relative_to(self.root).as_posix(): content
            for name, content in entries.items()
        }
        if existing and (
            set(existing) != set(expected_existing)
            or any(existing[path] != expected_existing[path] for path in existing if path in expected_existing)
        ):
            blockers.append(
                TransitionIssue(
                    code="P2P_VERTICAL_INSTALL_CONFLICT",
                    severity=IssueSeverity.BLOCKER,
                    category="install_conflict",
                    reference=coordinate,
                    recovery_action="Choose a different coordinate or remove the conflicting local pack.",
                )
            )
        sources = self._source_preconditions(candidates)
        artifact_kinds = sorted({_portable_artifact_kind(name) for name in entries})
        if (
            len(artifact_kinds) > VERTICAL_TRANSITION_COLLECTION_LIMIT
            or len(closure) > VERTICAL_TRANSITION_COLLECTION_LIMIT
            or len(artifact_kinds) + len(closure) > VERTICAL_TRANSITION_TOTAL_ITEM_LIMIT
        ):
            blockers.append(
                TransitionIssue(
                    code="P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED",
                    severity=IssueSeverity.BLOCKER,
                    category="impact_limit",
                    reference=coordinate,
                    recovery_action="Reduce the portable vertical dependency or artifact scope.",
                )
            )
        seed = {
            "contract_version": VERTICAL_TRANSITION_IMPACT_CONTRACT,
            "operation": "install",
            "target": coordinate,
            "artifact_checksum": actual,
            "semantic_checksum": inspection.semantic_checksum,
            "dependency_closure": closure,
            "artifact_kinds": artifact_kinds,
            "disposition": (
                "conflict" if blockers else "already_installed" if existing else "install"
            ),
        }
        impact = InstallImpact(
            analysis_fingerprint_sha256=impact_fingerprint(seed),
            target=VerticalIdentity(
                coordinate=coordinate,
                semantic_checksum=inspection.semantic_checksum,
                artifact_checksum=actual,
            ),
            artifact_kinds=BoundedCollection.build(artifact_kinds, key=lambda item: item),
            dependency_closure=BoundedCollection.build(
                closure, key=lambda item: item["coordinate"]
            ),
            disposition=(
                InstallDisposition.CONFLICT
                if blockers
                else InstallDisposition.ALREADY_INSTALLED
                if existing
                else InstallDisposition.INSTALL
            ),
            conflict=bool(blockers),
            blockers=BoundedCollection.build(blockers, key=lambda item: (item.code, item.reference)),
            warnings=BoundedCollection.build((), key=lambda item: item.code),
        )
        preview = MutationPreviewService.build(
            operation_id=f"project-vertical-install:{_operation_slug(coordinate)}",
            targets=tuple(candidates),
            actor=actor,
            authority="project_vertical_install",
            sources=sources,
            candidate_semantics=_candidate_semantics(candidates),
            semantic_diff=impact.to_dict(),
            token_context={
                "coordinate": coordinate,
                "actor": actor,
                "artifact_checksum": actual,
                "dependency_closure_sha256": semantic_sha256(closure),
            },
            blockers=[item.code for item in blockers],
        )
        return VerticalLifecyclePreview(
            operation="install",
            coordinate=coordinate,
            preview=preview,
            impact=impact,
            blockers=tuple(item.code for item in blockers),
            candidate_files=candidates,
        )

    def install_apply(
        self,
        artifact: Path,
        *,
        expected_checksum: str,
        preview_token: str,
        confirmed: bool,
        actor: str,
        idempotency_key: str,
    ) -> VerticalLifecycleResult:
        self._require_confirmation(confirmed)
        expected = normalize_expected_checksum(expected_checksum)
        artifact_path = artifact if artifact.is_absolute() else self.root / artifact
        fingerprint = self.receipt_service.fingerprint(
            operation="install",
            actor=actor,
            preview_token=preview_token,
            semantic_inputs={
                "artifact": artifact_path.resolve(strict=False).as_posix(),
                "expected_checksum": expected,
            },
        )
        replay = self.receipt_service.replay(
            idempotency_key=idempotency_key,
            request_fingerprint_sha256=fingerprint,
        )
        if replay is not None:
            return self._replayed_result(replay, preview_token=preview_token)
        preview = self.install_preview(
            artifact,
            expected_checksum=expected,
            actor=actor,
        )
        return self._apply_preview(
            preview,
            preview_token=preview_token,
            actor=actor,
            idempotency_key=idempotency_key,
            request_fingerprint_sha256=fingerprint,
        )

    def adopt_preview(
        self,
        reference: str,
        *,
        actor: str = "local",
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecyclePreview:
        coordinate = str(VerticalCoordinate.parse(reference))
        snapshot = self._classifier().capture()
        candidate = self.vertical_service.render_migration_candidate(
            coordinate,
            actor=actor,
            profile=profile,
            modules=modules,
            preserve_existing_rubrics=False,
            reconcile_existing_questions=False,
        )
        candidate = self._with_portable_lock(candidate)
        self.vertical_service.validate_migration_candidate(candidate)
        impact = self._analysis_service().adoption_impact(
            snapshot=snapshot,
            coordinate=coordinate,
            baseline=candidate,
        )
        blockers = [item.code for item in impact.blockers.items]
        return self._governed_preview(
            operation="adopt",
            coordinate=coordinate,
            candidate=candidate,
            actor=actor,
            impact=impact,
            blockers=blockers,
            token_context={"profile": profile, "modules": sorted(modules or [])},
        )

    def adopt_apply(
        self,
        reference: str,
        *,
        preview_token: str,
        confirmed: bool,
        actor: str,
        idempotency_key: str,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecycleResult:
        self._require_confirmation(confirmed)
        coordinate = str(VerticalCoordinate.parse(reference))
        normalized_modules = sorted(str(item) for item in (modules or []))
        fingerprint = self.receipt_service.fingerprint(
            operation="adopt",
            actor=actor,
            preview_token=preview_token,
            semantic_inputs={
                "coordinate": coordinate,
                "profile": str(profile),
                "modules": normalized_modules,
            },
        )
        replay = self.receipt_service.replay(
            idempotency_key=idempotency_key,
            request_fingerprint_sha256=fingerprint,
        )
        if replay is not None:
            return self._replayed_result(replay, preview_token=preview_token)
        preview = self.adopt_preview(
            coordinate,
            actor=actor,
            profile=profile,
            modules=modules,
        )
        return self._apply_preview(
            preview,
            preview_token=preview_token,
            actor=actor,
            idempotency_key=idempotency_key,
            request_fingerprint_sha256=fingerprint,
        )

    def migrate_preview(
        self,
        reference: str,
        *,
        actor: str = "local",
        mapping: Mapping[str, object] | None = None,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecyclePreview:
        coordinate = str(VerticalCoordinate.parse(reference))
        snapshot = self._classifier().capture()
        plan = _parse_plan(mapping)
        baseline = self.vertical_service.render_migration_candidate(
            coordinate,
            actor=actor,
            profile=profile,
            modules=modules,
            preserve_existing_rubrics=False,
            reconcile_existing_questions=False,
        )
        baseline = self._with_portable_lock(baseline)
        self.vertical_service.validate_migration_candidate(baseline)
        analysis = self._analysis_service().migration_analysis(
            snapshot=snapshot,
            coordinate=coordinate,
            baseline=baseline,
            actor=actor,
            plan=plan,
        )
        if not analysis.required_decisions and plan is None:
            plan = VerticalTransitionPlan(
                analysis_fingerprint_sha256=analysis.impact.analysis_fingerprint_sha256,
                decisions=(),
            )
            analysis = self._analysis_service().migration_analysis(
                snapshot=snapshot,
                coordinate=coordinate,
                baseline=baseline,
                actor=actor,
                plan=plan,
            )
        blockers = [item.code for item in analysis.impact.blockers.items]
        if blockers or plan is None:
            return VerticalLifecyclePreview(
                operation="migrate",
                coordinate=coordinate,
                preview=None,
                impact=analysis.impact,
                blockers=tuple(blockers),
            )
        candidate = self._materialization_service().materialize(
            analysis,
            plan=plan,
            actor=actor,
        )
        return self._governed_preview(
            operation="migrate",
            coordinate=coordinate,
            candidate=candidate,
            actor=actor,
            impact=analysis.impact,
            blockers=blockers,
            token_context={
                "impact_contract": VERTICAL_TRANSITION_IMPACT_CONTRACT,
                "analysis_fingerprint_sha256": analysis.impact.analysis_fingerprint_sha256,
                "plan_fingerprint_sha256": analysis.impact.plan_fingerprint_sha256,
                "profile": profile,
                "modules": sorted(modules or []),
            },
            decision_summary=tuple(item.to_dict() for item in plan.decisions),
        )

    def migrate_apply(
        self,
        reference: str,
        *,
        preview_token: str,
        confirmed: bool,
        actor: str,
        idempotency_key: str,
        mapping: Mapping[str, object] | None = None,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecycleResult:
        self._require_confirmation(confirmed)
        coordinate = str(VerticalCoordinate.parse(reference))
        plan = _parse_plan(mapping)
        normalized_modules = sorted(str(item) for item in (modules or []))
        fingerprint = self.receipt_service.fingerprint(
            operation="migrate",
            actor=actor,
            preview_token=preview_token,
            semantic_inputs={
                "coordinate": coordinate,
                "transition_plan": plan.to_dict() if plan is not None else None,
                "profile": str(profile),
                "modules": normalized_modules,
            },
        )
        replay = self.receipt_service.replay(
            idempotency_key=idempotency_key,
            request_fingerprint_sha256=fingerprint,
        )
        if replay is not None:
            return self._replayed_result(replay, preview_token=preview_token)
        preview = self.migrate_preview(
            coordinate,
            actor=actor,
            mapping={
                **(plan.to_dict() if plan is not None else {}),
            } if plan is not None else None,
            profile=profile,
            modules=modules,
        )
        return self._apply_preview(
            preview,
            preview_token=preview_token,
            actor=actor,
            idempotency_key=idempotency_key,
            request_fingerprint_sha256=fingerprint,
        )

    def _governed_preview(
        self,
        *,
        operation: str,
        coordinate: str,
        candidate: VerticalMigrationCandidate,
        actor: str,
        impact: VerticalTransitionImpact,
        blockers: list[str],
        token_context: dict[str, object],
        decision_summary: tuple[dict[str, object], ...] = (),
    ) -> VerticalLifecyclePreview:
        sources = self._source_preconditions(candidate.candidate_files)
        preview = MutationPreviewService.build(
            operation_id=f"project-vertical-{operation}:{_operation_slug(coordinate)}",
            targets=tuple(candidate.candidate_files),
            actor=actor,
            authority=f"project_vertical_{operation}",
            sources=sources,
            candidate_semantics=_candidate_semantics(candidate.candidate_files),
            semantic_diff=impact.to_dict(),
            token_context={"coordinate": coordinate, "actor": actor, **token_context},
            blockers=blockers,
        )
        return VerticalLifecyclePreview(
            operation=operation,
            coordinate=coordinate,
            preview=preview,
            impact=impact,
            blockers=tuple(blockers),
            candidate_files=candidate.candidate_files,
            decision_summary=decision_summary,
        )

    def _apply_preview(
        self,
        preview: VerticalLifecyclePreview,
        *,
        preview_token: str,
        actor: str,
        idempotency_key: str,
        request_fingerprint_sha256: str,
    ) -> VerticalLifecycleResult:
        if preview.blockers or preview.preview is None:
            raise ValueError(
                "P2P_VERTICAL_OPERATION_BLOCKED: " + "; ".join(preview.blockers or ("preview is not applicable",))
            )
        if preview.preview.preview_token != preview_token:
            raise ValueError("P2P_VERTICAL_STALE_PREVIEW: preview token does not match current state")
        semantic_postconditions = _semantic_postconditions(
            preview.candidate_files,
            coordinate=preview.coordinate,
            operation=preview.operation,
            impact=preview.impact,
        )
        result_summary = {
            "impact_contract": VERTICAL_TRANSITION_IMPACT_CONTRACT,
            "operation": preview.operation,
            "operation_id": preview.preview.operation_id,
            "coordinate": preview.coordinate,
            "analysis_fingerprint_sha256": preview.impact.analysis_fingerprint_sha256,
            "plan_fingerprint_sha256": getattr(
                preview.impact, "plan_fingerprint_sha256", None
            ),
            "semantic_postconditions": semantic_postconditions,
            "decision_summary": list(preview.decision_summary),
            "changed_paths": sorted(preview.candidate_files),
        }
        receipt_path, receipt_content, _receipt = self.receipt_service.prepare(
            idempotency_key=idempotency_key,
            operation=preview.operation,
            actor=actor,
            request_fingerprint_sha256=request_fingerprint_sha256,
            preview_token=preview_token,
            result=result_summary,
            candidates=preview.candidate_files,
        )
        candidates: dict[str, bytes | None] = {
            **preview.candidate_files,
            receipt_path: receipt_content,
        }
        sources = (
            *preview.preview.source_preconditions,
            source_precondition(receipt_path, None),
        )
        mutation = self.atomic_writer.apply(
            operation_id=preview.preview.operation_id,
            candidates=candidates,
            sources=sources,
            preview_token=preview_token,
            actor=actor,
        )
        if mutation.status != "applied":
            replay = self.receipt_service.replay(
                idempotency_key=idempotency_key,
                request_fingerprint_sha256=request_fingerprint_sha256,
            )
            if replay is not None:
                return self._replayed_result(replay, preview_token=preview_token)
            code = "P2P_VERTICAL_PROJECT_BUSY" if mutation.status == "blocked" else "P2P_VERTICAL_APPLY_FAILED"
            raise ValueError(f"{code}: {mutation.message or mutation.status}")
        mutation = replace(
            mutation,
            changed_paths=tuple(path for path in mutation.changed_paths if path != receipt_path),
            final_physical_hashes={
                path: digest
                for path, digest in mutation.final_physical_hashes.items()
                if path != receipt_path
            },
        )
        return VerticalLifecycleResult(
            operation=preview.operation,
            coordinate=preview.coordinate,
            mutation=mutation,
            analysis_fingerprint_sha256=preview.impact.analysis_fingerprint_sha256,
            plan_fingerprint_sha256=getattr(
                preview.impact, "plan_fingerprint_sha256", None
            ),
            postconditions=semantic_postconditions,
        )

    @staticmethod
    def _replayed_result(
        receipt: MutationReceipt,
        *,
        preview_token: str,
    ) -> VerticalLifecycleResult:
        operation_id = str(receipt.result.get("operation_id") or "")
        coordinate = str(receipt.result.get("coordinate") or "")
        semantic_postconditions = receipt.result.get("semantic_postconditions")
        if not isinstance(semantic_postconditions, dict):
            semantic_postconditions = {}
        return VerticalLifecycleResult(
            operation=receipt.operation,
            coordinate=coordinate,
            mutation=MutationResult(
                status="already_applied",
                operation_id=operation_id,
                final_physical_hashes={
                    item.path: item.physical_sha256 for item in receipt.postconditions
                },
                preview_token=preview_token,
                actor=receipt.actor,
                message="Mutation was already applied with this idempotency key.",
            ),
            analysis_fingerprint_sha256=str(
                receipt.result.get("analysis_fingerprint_sha256") or ""
            ),
            plan_fingerprint_sha256=(
                str(receipt.result["plan_fingerprint_sha256"])
                if receipt.result.get("plan_fingerprint_sha256") is not None
                else None
            ),
            postconditions={
                str(key): str(value) if value is not None else None
                for key, value in semantic_postconditions.items()
            },
        )

    def _dependency_closure(self, pack: VerticalPack) -> list[dict[str, str]]:
        closure: list[dict[str, str]] = []
        visited: set[str] = set()

        def visit(dependency: VerticalDependency, stack: tuple[str, ...]) -> None:
            coordinate = str(VerticalCoordinate.parse(dependency.coordinate))
            if coordinate in stack:
                raise ValueError(
                    "P2P_VERTICAL_DEPENDENCY_CYCLE: " + " -> ".join([*stack, coordinate])
                )
            resolved = self.vertical_service.resolve_pack(coordinate)
            expected = dependency.checksum.removeprefix("sha256:")
            if resolved.checksum != expected:
                raise ValueError(
                    f"P2P_VERTICAL_DEPENDENCY_CHECKSUM_MISMATCH: {coordinate} expected {expected}, got {resolved.checksum}"
                )
            if coordinate in visited:
                return
            visited.add(coordinate)
            for child in resolved.pack.manifest.dependencies if resolved.pack.manifest else []:
                visit(child, (*stack, coordinate))
            closure.append({"coordinate": coordinate, "checksum": f"sha256:{resolved.checksum}"})

        for item in pack.manifest.dependencies if pack.manifest else []:
            visit(item, (pack.coordinate,))
        return sorted(closure, key=lambda item: item["coordinate"])

    def _with_portable_lock(self, candidate: VerticalMigrationCandidate) -> VerticalMigrationCandidate:
        resolved = self.vertical_service.resolve_pack(candidate.reference or candidate.vertical_id)
        if not resolved.pack.coordinate:
            return candidate
        lock_path = ".p2p/project/vertical.lock.yml"
        payload = load_yaml(candidate.candidate_files[lock_path])
        if not isinstance(payload, dict) or not isinstance(payload.get("project_vertical_lock"), dict):
            raise ValueError("P2P_VERTICAL_INVALID_LOCK_CANDIDATE: missing lock mapping")
        lock = payload["project_vertical_lock"]
        assert isinstance(lock, dict)
        lock["coordinate"] = resolved.pack.coordinate
        lock["dependencies"] = self._dependency_closure(resolved.pack)
        if resolved.pack.path is not None:
            pack_root = resolved.pack.path.parent if resolved.pack.path.name == "manifest.yml" else resolved.pack.path.parent
            entries = self.package_service.canonical_entries(pack_root)
            artifact_checksum = hashlib.sha256(self.package_service.archive_bytes(entries)).hexdigest()
            lock["artifact_checksum"] = {"algorithm": "sha256", "value": artifact_checksum}
        candidate.candidate_files[lock_path] = yaml_dump(payload).encode("utf-8")
        return candidate

    def _classifier(self) -> VerticalEvidenceClassifier:
        return VerticalEvidenceClassifier(
            root=self.root,
            p2p_dir=self.p2p_dir,
            vertical_service=self.vertical_service,
        )

    def _analysis_service(self) -> VerticalTransitionAnalysisService:
        return VerticalTransitionAnalysisService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            vertical_service=self.vertical_service,
        )

    def _materialization_service(self) -> VerticalTransitionMaterializationService:
        return VerticalTransitionMaterializationService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            vertical_service=self.vertical_service,
        )

    def _source_preconditions(self, candidates: dict[str, bytes]) -> tuple:
        return tuple(
            source_precondition(
                path,
                (self.root / path).read_bytes() if (self.root / path).exists() else None,
            )
            for path in sorted(candidates)
        )

    @staticmethod
    def _install_prefix(coordinate: VerticalCoordinate) -> str:
        return (
            ".p2p/project/verticals/_portable/"
            f"{coordinate.publisher}/{coordinate.vertical_id}/{coordinate.version}"
        )

    def _installed_files(self, target: Path) -> dict[str, bytes]:
        if not target.exists():
            return {}
        if target.is_symlink() or not target.is_dir():
            raise ValueError(f"P2P_VERTICAL_INSTALL_CONFLICT: unsafe existing target `{target}`")
        result: dict[str, bytes] = {}
        for path in target.rglob("*"):
            if path.is_dir():
                if path.is_symlink():
                    raise ValueError(f"P2P_VERTICAL_INSTALL_CONFLICT: linked directory `{path}`")
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"P2P_VERTICAL_INSTALL_CONFLICT: unsafe existing entry `{path}`")
            result[path.relative_to(self.root).as_posix()] = path.read_bytes()
        return result

    @staticmethod
    def _require_confirmation(confirmed: bool) -> None:
        if not confirmed:
            raise ValueError("P2P_VERTICAL_CONFIRMATION_REQUIRED: apply requires --confirm")


def _candidate_semantics(candidates: dict[str, bytes]) -> dict[str, object]:
    return {
        path: {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
        for path, content in candidates.items()
    }


def _operation_slug(coordinate: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", coordinate)


def _parse_plan(payload: Mapping[str, object] | None) -> VerticalTransitionPlan | None:
    if payload is None or not payload:
        return None
    return parse_transition_plan(payload)


def _portable_artifact_kind(name: str) -> str:
    normalized = name.replace("\\", "/")
    if normalized == "manifest.yml":
        return "manifest"
    return normalized.split("/", 1)[0].removesuffix(".yml") or "pack"


def _semantic_postconditions(
    candidates: Mapping[str, bytes],
    *,
    coordinate: str,
    operation: str,
    impact: VerticalTransitionImpact,
) -> dict[str, str | None]:
    if operation == "install":
        if not isinstance(impact, InstallImpact):
            raise ValueError("P2P_VERTICAL_INVALID_INSTALL_IMPACT: typed install impact required")
        return {
            "installed_coordinate": coordinate,
            "installed_semantic_checksum": impact.target.semantic_checksum,
            "installed_artifact_checksum": impact.target.artifact_checksum or None,
        }
    artifact_paths = {
        "definition_semantic_sha256": ".p2p/project/definition.yml",
        "questions_semantic_sha256": ".p2p/project/questions.yml",
        "rubrics_semantic_sha256": ".p2p/project/rubrics.yml",
    }
    result: dict[str, str | None] = {"active_coordinate": coordinate}
    for field, path in artifact_paths.items():
        content = candidates.get(path)
        result[field] = semantic_sha256(load_yaml(content)) if content is not None else None
    lock_content = candidates.get(".p2p/project/vertical.lock.yml")
    lock_semantic = None
    lock_artifact = None
    if lock_content is not None:
        payload = load_yaml(lock_content)
        if isinstance(payload, Mapping):
            lock = payload.get("project_vertical_lock")
            if isinstance(lock, Mapping):
                checksum = lock.get("checksum")
                artifact = lock.get("artifact_checksum")
                if isinstance(checksum, Mapping):
                    lock_semantic = str(checksum.get("value") or "") or None
                if isinstance(artifact, Mapping):
                    lock_artifact = str(artifact.get("value") or "") or None
    result["lock_semantic_checksum"] = lock_semantic
    result["lock_artifact_checksum"] = lock_artifact
    return result

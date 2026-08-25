from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, Mapping

from p2p_engine.core.authority import AuthorityContext, AuthorityEvidence
from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.project_domain import (
    PROJECT_DOMAIN_CONTRACT,
    STRUCTURE_SOURCE_CONTRACT,
    ProjectDomainMutationPlan,
    ProjectDomainMutationResult,
    ProjectDomainRef,
    ProjectDomainState,
    StructureSource,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.authority import AuthorityContractCodec, ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso


PROJECT_DOMAIN_PATH = ".p2p/project/domain.yml"
STRUCTURE_SOURCE_PATH = ".p2p/project/structure-source.yml"
PROJECT_DOMAIN_OPERATION = "project_domain_change"
PROJECT_DOMAIN_POLICY_VERSION = 1


class ProjectDomainService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.domain_path = self.root / PROJECT_DOMAIN_PATH
        self.structure_source_path = self.root / STRUCTURE_SOURCE_PATH
        self.authority = authority or ProjectAuthorityService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.receipts = receipts or MutationReceiptService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.clock = clock
        self.codec = AuthorityContractCodec()

    def show(self) -> ProjectDomainState:
        try:
            if self.domain_path.is_symlink() or not self.domain_path.is_file():
                raise ValueError("domain descriptor is missing or unsafe")
            return project_domain_state_from_bytes(self.domain_path.read_bytes())
        except OSError as exc:
            raise ValueError(f"P2P_PROJECT_DOMAIN_INVALID: cannot read domain: {exc}") from exc

    def structure_source(self) -> dict[str, object]:
        try:
            if self.structure_source_path.is_symlink() or not self.structure_source_path.is_file():
                raise ValueError("structure source is missing or unsafe")
            payload = load_yaml(
                self.structure_source_path.read_bytes(),
                loader_contract=UNIQUE_LOADER_CONTRACT,
            )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"P2P_STRUCTURE_SOURCE_INVALID: {exc}") from exc
        source = payload.get("structure_source") if isinstance(payload, Mapping) else None
        if not isinstance(source, Mapping):
            raise ValueError(
                "P2P_STRUCTURE_SOURCE_INVALID: expected structure_source mapping"
            )
        allowed = {"contract", "source", "origin", "initialized_at", "initialized_by"}
        unknown = sorted(set(source) - allowed)
        if unknown or source.get("contract") != STRUCTURE_SOURCE_CONTRACT:
            raise ValueError("P2P_STRUCTURE_SOURCE_INVALID: unsupported source contract")
        normalized_source = StructureSource.from_mapping(source.get("source"))
        origin = source.get("origin")
        if not isinstance(origin, Mapping):
            raise ValueError("P2P_STRUCTURE_SOURCE_INVALID: origin must be a mapping")
        normalized_origin = _normalize_structure_origin(normalized_source, origin)
        return {
            "contract": STRUCTURE_SOURCE_CONTRACT,
            "source": normalized_source.to_dict(),
            "origin": normalized_origin,
            "initialized_at": _required_text(source, "initialized_at"),
            "initialized_by": _required_text(source, "initialized_by"),
        }

    def plan(
        self,
        *,
        operation: str,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        descriptor: ProjectDomainRef | None,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
    ) -> ProjectDomainMutationPlan:
        validate_idempotency_key(operation_key)
        if operation not in {"set", "clear"}:
            raise ValueError("P2P_PROJECT_DOMAIN_INVALID: operation must be set or clear")
        if (operation == "set") != (descriptor is not None):
            raise ValueError("P2P_PROJECT_DOMAIN_INVALID: set requires a descriptor and clear forbids it")
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            required_capabilities=("project.domain.change",),
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        previous = self.show()
        current_domain_bytes = self.domain_path.read_bytes()
        receipt_path = self.receipts.relative_path(operation_key)
        project_memory_revision = self.project_memory_revision()
        next_state = ProjectDomainState(
            revision=previous.revision + 1,
            descriptor=descriptor,
            updated_at=self.clock(),
            updated_by=evidence.subject.identity_id,
            project_memory_revision=project_memory_revision,
        )
        request_fingerprint = semantic_sha256(
            {
                "policy_version": PROJECT_DOMAIN_POLICY_VERSION,
                "operation": f"project.domain.{operation}",
                "operation_key_sha256": idempotency_key_sha256(operation_key),
                "previous": previous.to_dict(),
                "next_descriptor": descriptor.to_dict() if descriptor else None,
                "project_memory_revision": project_memory_revision,
                "authority_context_sha256": context.digest_sha256,
            }
        )
        candidates = {PROJECT_DOMAIN_PATH: project_domain_state_bytes(next_state)}
        sources = (
            source_precondition(PROJECT_DOMAIN_PATH, current_domain_bytes),
            source_precondition(receipt_path, None),
        )
        preview = MutationPreviewService.build(
            operation_id=f"project-domain-{operation}",
            targets=(PROJECT_DOMAIN_PATH, receipt_path),
            actor=evidence.executor.identity_id,
            authority="root_authority",
            sources=sources,
            candidate_semantics={PROJECT_DOMAIN_PATH: next_state.to_dict()},
            semantic_diff={
                "domain_before": previous.descriptor.to_dict() if previous.descriptor else None,
                "domain_after": descriptor.to_dict() if descriptor else None,
                "domain_revision_before": previous.revision,
                "domain_revision_after": next_state.revision,
                "structure_changed": False,
            },
            token_context={
                "request_fingerprint_sha256": request_fingerprint,
                "authority_context_sha256": context.digest_sha256,
                "operation_key_sha256": idempotency_key_sha256(operation_key),
            },
            policy_version=PROJECT_DOMAIN_POLICY_VERSION,
        )
        return ProjectDomainMutationPlan(
            operation=operation,
            previous=previous,
            next=next_state,
            operation_key_sha256=idempotency_key_sha256(operation_key),
            request_fingerprint_sha256=request_fingerprint,
            preview_token=preview.preview_token,
            source_preconditions=preview.source_preconditions,
            candidate_bytes=candidates,
            authority=evidence,
        )

    def apply(
        self,
        *,
        operation: str,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        descriptor: ProjectDomainRef | None,
        authority_context: AuthorityContext | None = None,
        channel: str = "cli",
        consent_id: str | None = None,
        consent_sha256: str | None = None,
    ) -> ProjectDomainMutationResult:
        replay = self._exact_replay(
            operation=operation,
            operation_key=operation_key,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            descriptor=descriptor,
            authority_context=authority_context,
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        if replay is not None:
            return replay
        plan = self.plan(
            operation=operation,
            operation_key=operation_key,
            actor_id=actor_id,
            executor_id=executor_id,
            executor_kind=executor_kind,
            descriptor=descriptor,
            authority_context=authority_context,
            channel=channel,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
        )
        evidence = plan.authority
        if not isinstance(evidence, AuthorityEvidence):
            raise ValueError("P2P_AUTHORITY_CONTEXT_INVALID: domain plan lost authority evidence")
        summary = {
            "contract": PROJECT_DOMAIN_CONTRACT,
            "operation": PROJECT_DOMAIN_OPERATION,
            "operation_id": f"project.domain.{operation}",
            "requested_operation": operation,
            "previous": plan.previous.to_dict(),
            "current": plan.next.to_dict(),
            "project_memory_revision": plan.next.project_memory_revision,
            "changed_paths": [PROJECT_DOMAIN_PATH],
        }
        receipt_path, receipt_content, _receipt = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=PROJECT_DOMAIN_OPERATION,
            actor=evidence.executor.identity_id,
            request_fingerprint_sha256=plan.request_fingerprint_sha256,
            preview_token=plan.preview_token,
            result=summary,
            candidates=plan.candidate_bytes,
            authority=evidence,
        )
        mutation = self.atomic_writer.apply(
            operation_id=f"project-domain-{operation}",
            candidates={**plan.candidate_bytes, receipt_path: receipt_content},
            sources=plan.source_preconditions,
            preview_token=plan.preview_token,
            actor=evidence.executor.identity_id,
            candidate_validator=lambda view: project_domain_state_from_bytes(
                view.read_bytes(PROJECT_DOMAIN_PATH)
            ),
        )
        if mutation.status != "applied":
            replay = self._exact_replay(
                operation=operation,
                operation_key=operation_key,
                actor_id=actor_id,
                executor_id=executor_id,
                executor_kind=executor_kind,
                descriptor=descriptor,
                authority_context=authority_context,
                channel=channel,
                consent_id=consent_id,
                consent_sha256=consent_sha256,
            )
            if replay is not None:
                return replay
            raise ValueError(
                "P2P_PROJECT_DOMAIN_MUTATION_FAILED: "
                + (mutation.message or mutation.status)
            )
        return ProjectDomainMutationResult(
            status="applied",
            operation=operation,
            previous=plan.previous,
            current=plan.next,
            actor=evidence.executor.identity_id,
            changed_paths=(PROJECT_DOMAIN_PATH,),
            message="Project domain classification changed without modifying structure.",
        )

    def project_memory_revision(self) -> str:
        paths = (
            ".p2p/project.yml",
            STRUCTURE_SOURCE_PATH,
            ".p2p/project/vertical.yml",
            ".p2p/project/vertical.lock.yml",
            ".p2p/project/definition.yml",
            ".p2p/project/rubrics.yml",
            ".p2p/project/questions.yml",
        )
        return semantic_sha256(
            {
                path: (
                    hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                    if (self.root / path).is_file() and not (self.root / path).is_symlink()
                    else None
                )
                for path in paths
            }
        )

    def _exact_replay(
        self,
        *,
        operation: str,
        operation_key: str,
        actor_id: str,
        executor_id: str,
        executor_kind: str,
        descriptor: ProjectDomainRef | None,
        authority_context: AuthorityContext | None,
        channel: str,
        consent_id: str | None,
        consent_sha256: str | None,
    ) -> ProjectDomainMutationResult | None:
        receipt = self.receipts.read(idempotency_key=operation_key)
        if receipt is None:
            return None
        if receipt.operation != PROJECT_DOMAIN_OPERATION or receipt.authority is None:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation"
            )
        result = receipt.result
        if result.get("requested_operation") != operation:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to a different domain operation"
            )
        current = project_domain_state_from_mapping(result.get("current"))
        previous = project_domain_state_from_mapping(result.get("previous"))
        expected = descriptor.to_dict() if descriptor else None
        actual = current.descriptor.to_dict() if current.descriptor else None
        if expected != actual:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to a different domain descriptor"
            )
        evidence = self.codec.evidence_from_mapping(receipt.authority)
        if evidence.channel != channel:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to a different mutation channel"
            )
        if consent_id != evidence.consent_id:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to different consent evidence"
            )
        if consent_sha256 is not None and consent_sha256 != evidence.consent_sha256:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to different consent content"
            )
        if authority_context is not None:
            if authority_context.digest_sha256 != evidence.authority_context_sha256:
                raise ValueError(
                    "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to different authority evidence"
                )
        elif (
            actor_id != evidence.subject.identity_id
            or executor_id != evidence.executor.identity_id
            or executor_kind != evidence.executor.kind.value
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is bound to a different subject or executor"
            )
        return ProjectDomainMutationResult(
            status="already_applied",
            operation=operation,
            previous=previous,
            current=current,
            actor=evidence.executor.identity_id,
            changed_paths=tuple(str(item) for item in result.get("changed_paths", [])),
            message="Exact project-domain mutation was already committed.",
        )


def initial_project_domain_state(
    descriptor: ProjectDomainRef | None,
    *,
    actor: str,
    initialized_at: str,
    project_memory_revision: str = "0" * 64,
) -> ProjectDomainState:
    return ProjectDomainState(
        revision=1,
        descriptor=descriptor,
        updated_at=initialized_at,
        updated_by=actor,
        project_memory_revision=project_memory_revision,
    )


def project_domain_state_bytes(state: ProjectDomainState) -> bytes:
    return yaml_dump({"project_domain": state.to_dict()}).encode("utf-8")


def project_domain_state_from_bytes(content: bytes) -> ProjectDomainState:
    try:
        payload = load_yaml(content, loader_contract=UNIQUE_LOADER_CONTRACT)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"P2P_PROJECT_DOMAIN_INVALID: {exc}") from exc
    data = payload.get("project_domain") if isinstance(payload, Mapping) else None
    return project_domain_state_from_mapping(data)


def project_domain_state_from_mapping(value: object) -> ProjectDomainState:
    if not isinstance(value, Mapping):
        raise ValueError("P2P_PROJECT_DOMAIN_INVALID: expected project_domain mapping")
    allowed = {
        "contract",
        "revision",
        "descriptor",
        "updated_at",
        "updated_by",
        "project_memory_revision",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(
            "P2P_PROJECT_DOMAIN_INVALID: unsupported state fields: "
            + ", ".join(str(item) for item in unknown)
        )
    revision = value.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int):
        raise ValueError("P2P_PROJECT_DOMAIN_INVALID: revision must be an integer")
    descriptor_payload = value.get("descriptor")
    descriptor = (
        None
        if descriptor_payload is None
        else ProjectDomainRef.from_mapping(descriptor_payload)
    )
    memory_revision = _required_text(value, "project_memory_revision")
    if len(memory_revision) != 64 or any(char not in "0123456789abcdef" for char in memory_revision):
        raise ValueError(
            "P2P_PROJECT_DOMAIN_INVALID: project_memory_revision must be SHA-256"
        )
    return ProjectDomainState(
        contract=_required_text(value, "contract"),
        revision=revision,
        descriptor=descriptor,
        updated_at=_required_text(value, "updated_at"),
        updated_by=_required_text(value, "updated_by"),
        project_memory_revision=memory_revision,
    )


def structure_source_bytes(
    source: StructureSource,
    *,
    origin: Mapping[str, object],
    initialized_at: str,
    initialized_by: str,
) -> bytes:
    normalized_origin = _normalize_structure_origin(source, origin)
    return yaml_dump(
        {
            "structure_source": {
                "contract": STRUCTURE_SOURCE_CONTRACT,
                "source": source.to_dict(),
                "origin": normalized_origin,
                "initialized_at": initialized_at,
                "initialized_by": initialized_by,
            }
        }
    ).encode("utf-8")


def _required_text(value: Mapping[str, object], field: str) -> str:
    raw = value.get(field)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"P2P_PROJECT_DOMAIN_INVALID: {field} must be non-empty text")
    return raw.strip()


def _normalize_structure_origin(
    source: StructureSource,
    value: Mapping[str, object],
) -> dict[str, object]:
    allowed = {"kind", "identity", "checksum"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(
            "P2P_STRUCTURE_SOURCE_INVALID: unsupported origin fields: "
            + ", ".join(str(item) for item in unknown)
        )
    kind = _required_text(value, "kind")
    identity = _required_text(value, "identity")
    checksum = value.get("checksum")
    if source.kind == "starter":
        normalized_checksum = None
        if checksum is not None:
            normalized_checksum = str(checksum).removeprefix("sha256:")
            if len(normalized_checksum) != 64 or any(
                char not in "0123456789abcdef" for char in normalized_checksum
            ):
                raise ValueError(
                    "P2P_STRUCTURE_SOURCE_INVALID: starter origin checksum must be SHA-256"
                )
        if kind != "starter" or identity != source.starter_id:
            raise ValueError(
                "P2P_STRUCTURE_SOURCE_INVALID: starter origin does not match its source"
            )
        return {"kind": kind, "identity": identity, "checksum": normalized_checksum}
    normalized_checksum = str(checksum or "").removeprefix("sha256:")
    if (
        kind != "vertical_release"
        or identity != source.coordinate
        or normalized_checksum != source.checksum
    ):
        raise ValueError(
            "P2P_STRUCTURE_SOURCE_INVALID: vertical origin does not match its exact source"
        )
    return {
        "kind": kind,
        "identity": identity,
        "checksum": normalized_checksum,
    }

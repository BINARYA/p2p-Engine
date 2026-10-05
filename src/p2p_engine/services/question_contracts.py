from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from p2p_engine.core.authority import AuthorityContext
from p2p_engine.core.mutation_preview import (
    canonical_json_bytes,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.question_contracts import (
    QUESTION_MAX_SELECTION,
    QUESTION_MAX_TEXT,
    QUESTION_MUTATION_CONTRACT,
    QUESTION_NEXT_CONTRACT,
    QUESTION_OPERATIONS,
    QUESTION_PAGE_CONTRACT,
    QUESTION_PREVIEW_CONTRACT,
    bounded_question_result,
    validate_question_mutation_result,
)
from p2p_engine.services.authority import ProjectAuthorityService
from p2p_engine.services.mutation_receipts import (
    MutationReceiptService,
    idempotency_key_sha256,
    validate_idempotency_key,
)
from p2p_engine.services.permissions import PermissionActor
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.project_readiness import ProjectReadinessPaginationService
from p2p_engine.services.project_readiness_convergence import ProjectReadinessConvergenceService
from p2p_engine.services.project_replication import (
    replay_replication_outcome,
    require_replication_operation_key,
)
from p2p_engine.services.proposal_questions import (
    ProposalQuestionService,
    validate_proposal_questions_payload,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


def _text(value: str, maximum: int = 2000) -> tuple[str, bool]:
    return value[:maximum], len(value) > maximum


def _bounded_value(value: object, *, field: str, truncated: list[str], depth: int = 0) -> object:
    """Bound a projection only; never alter canonical question values."""
    if depth > 4:
        truncated.append(field)
        return None
    if isinstance(value, str):
        result, shortened = _text(value, QUESTION_MAX_TEXT if field == "answer" else 512)
        if shortened:
            truncated.append(field)
        return result
    if isinstance(value, float) and not math.isfinite(value):
        truncated.append(field)
        return None
    if isinstance(value, Mapping):
        if len(value) > 32:
            truncated.append(field)
        return {
            str(key)[:128]: _bounded_value(item, field=field, truncated=truncated, depth=depth + 1)
            for key, item in list(value.items())[:32]
        }
    if isinstance(value, (tuple, list)):
        if len(value) > 32:
            truncated.append(field)
        return [
            _bounded_value(item, field=field, truncated=truncated, depth=depth + 1)
            for item in value[:32]
        ]
    return value


def question_projection(question: object, *, scope: str) -> dict[str, object]:
    truncated: list[str] = []
    result = {
        "id": question.question_id,
        "revision": question.revision,
        "state": question.state.value,
        "priority": str(question.priority),
    }
    for field in ("question", "rationale"):
        result[field], shortened = _text(getattr(question, field))
        if shortened:
            truncated.append(field)
    if scope == "project":
        result.update(
            section_id=_bounded_value(question.section_id, field="section_id", truncated=truncated),
            gap_id=_bounded_value(question.gap_id, field="gap_id", truncated=truncated),
            applicability=question.applicability.value,
            answer_contract=_bounded_value(
                question.answer_contract.to_dict(), field="answer_contract", truncated=truncated
            ),
        )
        answer = question.answers[-1] if question.answers else None
        values = {}
        if answer:
            for key, value in answer.values.items():
                if isinstance(value, str):
                    value, shortened = _text(value, QUESTION_MAX_TEXT)
                    if shortened:
                        truncated.append("answer")
                values[key] = value
        result["answer"] = (
            _bounded_value(
                {
                    "values": values,
                    "evidence_refs": [
                        _bounded_value(item, field="answer_provenance", truncated=truncated)
                        for item in answer.evidence_refs[:32]
                    ],
                    "provided_by": _bounded_value(
                        answer.provided_by, field="answer_provenance", truncated=truncated
                    ),
                    "recorded_by": _bounded_value(
                        answer.recorded_by, field="answer_provenance", truncated=truncated
                    ),
                },
                field="answer",
                truncated=truncated,
            )
            if answer
            else None
        )
        if "answer_provenance" in truncated:
            truncated[:] = ["answer" if item == "answer_provenance" else item for item in truncated]
        if answer and len(answer.evidence_refs) > 32:
            truncated.append("answer")
        if (
            result["answer"] is not None
            and len(canonical_json_bytes(result["answer"]["values"])) > 16 * 1024
        ):
            result["answer"]["values"] = {}
            truncated.append("answer")
        if len(canonical_json_bytes(result["answer_contract"])) > 8 * 1024:
            result["answer_contract"] = {
                "kind": question.answer_contract.kind.value,
                "required_fields": [],
                "allowed_definition_operations": [],
            }
            truncated.append("answer_contract")
    else:
        answer, shortened = _text(question.answer, QUESTION_MAX_TEXT)
        if shortened:
            truncated.append("answer")
        gap, shortened = _text(question.gap)
        if shortened:
            truncated.append("gap")
        result.update(
            group_id=_bounded_value(question.group_id, field="group_id", truncated=truncated),
            gap=gap,
            answer=answer,
            provided_by=_bounded_value(
                question.provided_by, field="provided_by", truncated=truncated
            ),
            recorded_by=_bounded_value(
                question.recorded_by, field="recorded_by", truncated=truncated
            ),
            application_effect="plan_registered"
            if question.applied_to_proposal
            else "not_registered",
        )
    result["truncated_fields"] = sorted(set(truncated))
    return result


class QuestionContractService:
    def __init__(
        self,
        *,
        root: Path,
        project: ProjectQuestionStateService,
        proposal: ProposalQuestionService,
        convergence: ProjectReadinessConvergenceService,
        preflight: Callable[[str], object],
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        writer: AtomicMutationWriter | None = None,
    ) -> None:
        self.root = root.resolve()
        self.project, self.proposal, self.convergence = project, proposal, convergence
        self.preflight = preflight
        self.authority = authority or ProjectAuthorityService(
            root=self.root, p2p_dir=self.root / ".p2p"
        )
        self.receipts = receipts or MutationReceiptService(
            root=self.root, p2p_dir=self.root / ".p2p"
        )
        self.writer = writer or AtomicMutationWriter(root=self.root, p2p_dir=self.root / ".p2p")

    def page(
        self,
        *,
        scope: str,
        proposal_id: str | None = None,
        state: str = "",
        limit: int = 20,
        offset: int = 0,
        cursor: str = "",
    ) -> dict[str, object]:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or isinstance(offset, bool)
            or not isinstance(offset, int)
            or not 1 <= limit <= 100
            or offset < 0
        ):
            raise ValueError(
                "P2P_QUESTION_LIMIT_INVALID: page limit must be 1–100 and offset nonnegative"
            )
        self._require_scope(scope)
        allowed_states = {
            "to_answer",
            "answered",
            "applied",
            "deferred" if scope == "project" else "defer",
            "muted",
            "retired",
            "superseded",
        }
        if state and state not in allowed_states:
            raise ValueError("P2P_QUESTION_STATE_INVALID: unsupported question state filter")
        if scope == "project":
            artifact = self.project.read()
            questions = [
                item for item in artifact.questions if not state or item.state.value == state
            ]
            projections = [
                question_projection(item, scope=scope)
                for item in sorted(questions, key=self.project._question_order_key)
            ]
            page = ProjectReadinessPaginationService().page_items(
                collection=f"project_questions:{state or 'all'}",
                snapshot_fingerprint=artifact.semantic_sha256,
                items=projections,
                key=lambda item: (str(item["priority"]), str(item["id"]), item["revision"]),
                limit=limit,
                cursor=cursor,
            )
            count = self._page_count(page.items)
            if count < len(page.items):
                page = ProjectReadinessPaginationService().page_items(
                    collection=f"project_questions:{state or 'all'}",
                    snapshot_fingerprint=artifact.semantic_sha256,
                    items=projections,
                    key=lambda item: (str(item["priority"]), str(item["id"]), item["revision"]),
                    limit=count,
                    cursor=cursor,
                )
            items = list(page.items)
            metadata = {
                "limit": limit,
                "total": page.total,
                "next_cursor": page.next_cursor,
                "has_more": bool(page.next_cursor),
            }
        else:
            view = self.proposal.read(str(proposal_id))
            questions = [item for item in view.questions if not state or item.state.value == state]
            questions.sort(key=lambda item: item.question_id)
            items = [
                question_projection(item, scope=scope)
                for item in questions[offset : offset + limit]
            ]
            items = items[: self._page_count(items)]
            metadata = {
                "limit": limit,
                "offset": offset,
                "total": len(questions),
                "next_offset": offset + len(items)
                if offset + len(items) < len(questions)
                else None,
                "has_more": offset + len(items) < len(questions),
            }
        result = {
            "contract": QUESTION_PAGE_CONTRACT,
            "scope": scope,
            "proposal_id": proposal_id,
            "items": items,
            "page": metadata,
        }
        bounded_question_result(result)
        return {"question_page": result}

    @staticmethod
    def _page_count(items: Sequence[object]) -> int:
        used, count = 2, 0
        for item in items:
            size = len(canonical_json_bytes(item)) + 1
            if used + size > 42 * 1024:
                break
            used += size
            count += 1
        if items and count == 0:
            raise ValueError(
                "P2P_QUESTION_LIMIT_INVALID: one question exceeds the bounded projection budget"
            )
        return count

    @staticmethod
    def _require_scope(scope: str) -> None:
        if scope not in {"project", "proposal"}:
            raise ValueError("P2P_QUESTION_OPERATION_INVALID: scope must be project or proposal")

    def next(
        self,
        *,
        scope: str,
        proposal_id: str | None = None,
        include_muted: bool = False,
        include_deferred: bool = False,
    ) -> dict[str, object]:
        self._require_scope(scope)
        question = (
            self.project.next_question()
            if scope == "project"
            else self.proposal.next_question(
                str(proposal_id), include_muted=include_muted, include_deferred=include_deferred
            )
        )
        result = {
            "contract": QUESTION_NEXT_CONTRACT,
            "scope": scope,
            "proposal_id": proposal_id,
            "question": question_projection(question, scope=scope) if question else None,
        }
        bounded_question_result(result)
        return {"question_next": result}

    def _request(
        self,
        *,
        scope: str,
        leaf: str,
        operation_key: str,
        actor_id: str,
        executor_id: str | None,
        executor_kind: str,
        authority_context: AuthorityContext | None,
        proposal_id: str | None,
        question_id: str,
        expected_revision: int | None,
        values: Mapping[str, object] | None,
        answer: str,
        source: str,
        reason: str,
        replace_answer: bool,
        evidence_refs: Sequence[str],
        question_ids: Sequence[str],
        preview_token: str,
    ) -> tuple[str, dict[str, object], str]:
        validate_idempotency_key(operation_key)
        operation = f"{scope}_question_{leaf}"
        if operation not in QUESTION_OPERATIONS:
            raise ValueError(
                "P2P_QUESTION_OPERATION_INVALID: unsupported machine question operation"
            )
        normalized_values = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in (values or {}).items()
        }
        if any(
            len(item) > QUESTION_MAX_TEXT
            for item in (
                answer,
                source,
                reason,
                *(value for value in normalized_values.values() if isinstance(value, str)),
            )
        ):
            raise ValueError(
                "P2P_QUESTION_LIMIT_INVALID: answer, value or reason exceeds 8000 characters"
            )
        if len(question_ids) > QUESTION_MAX_SELECTION or len(evidence_refs) > 32:
            raise ValueError(
                "P2P_QUESTION_LIMIT_INVALID: at most 32 questions/evidence references are allowed"
            )
        if any(not isinstance(item, str) or len(item) > 512 for item in evidence_refs):
            raise ValueError(
                "P2P_QUESTION_LIMIT_INVALID: evidence references must be strings of at most 512 characters"
            )
        request = {
            "scope": scope,
            "leaf": leaf,
            "proposal_id": proposal_id,
            "question_id": question_id,
            "expected_revision": expected_revision,
            "values": normalized_values,
            "answer": answer.strip(),
            "source": source.strip(),
            "reason": reason.strip(),
            "replace_answer": replace_answer,
            "evidence_refs": sorted(set(evidence_refs)),
            "question_ids": sorted(set(question_ids)),
            "actor_id": actor_id,
            "executor_id": executor_id or actor_id,
            "executor_kind": executor_kind,
            "authority_context_sha256": authority_context.digest_sha256
            if authority_context
            else None,
            "preview_token": preview_token,
        }
        bounded_question_result(request)
        fingerprint = self.receipts.fingerprint(
            operation=operation,
            actor=str(request["executor_id"]),
            preview_token=semantic_sha256(request),
            semantic_inputs=request,
        )
        return operation, request, fingerprint

    def preview(
        self,
        *,
        leaf: str,
        operation_key: str,
        actor_id: str,
        executor_id: str | None = None,
        executor_kind: str = "person",
        authority_context: AuthorityContext | None = None,
        question_ids: Sequence[str] = (),
    ) -> dict[str, object]:
        validate_idempotency_key(operation_key)
        if leaf not in {"apply", "reconcile"} or len(question_ids) > 32:
            raise ValueError(
                "P2P_QUESTION_OPERATION_INVALID: unsupported or oversized preview selection"
            )
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id or actor_id,
            executor_kind=executor_kind,
            required_capabilities=(f"project.question.{leaf}",),
            channel="cli",
        )
        actor = PermissionActor(
            actor_id=evidence.subject.identity_id,
            role="owner",
            kind=evidence.subject.kind.value,
            display_name=evidence.subject.identity_id,
            path=self.authority.permissions.path(),
        )
        bundle = (
            self.convergence.render_authorized_plan(question_ids, actor=actor)
            if leaf == "apply"
            else self.convergence.render_authorized_reconciliation(actor=actor)
        )
        public = bundle.public
        token = semantic_sha256(
            {
                "plan": public.preview.preview_token,
                "authority_context_sha256": context.digest_sha256,
                "operation_key_sha256": idempotency_key_sha256(operation_key),
            }
        )
        result = {
            "contract": QUESTION_PREVIEW_CONTRACT,
            "scope": "project",
            "operation_id": QUESTION_OPERATIONS[f"project_question_{leaf}"][2],
            "effect": "definition_applied" if leaf == "apply" else "state_updated",
            "preview_token": token,
            "question_ids": list(public.question_ids) if leaf == "apply" else [],
            "question_revisions": dict(public.question_revisions) if leaf == "apply" else {},
            "apply_allowed": public.preview.apply_allowed,
            "authority": evidence.to_dict(),
        }
        bounded_question_result(result)
        return {"question_preview": result}

    def mutate(
        self,
        *,
        scope: str,
        leaf: str,
        operation_key: str,
        actor_id: str,
        executor_id: str | None = None,
        executor_kind: str = "person",
        authority_context: AuthorityContext | None = None,
        proposal_id: str | None = None,
        question_id: str = "",
        expected_revision: int | None = None,
        values: Mapping[str, object] | None = None,
        answer: str = "",
        source: str = "owner",
        reason: str = "",
        replace_answer: bool = False,
        evidence_refs: Sequence[str] = (),
        question_ids: Sequence[str] = (),
        preview_token: str = "",
        confirm: bool = False,
    ) -> dict[str, object]:
        operation, request, fingerprint = self._request(
            **{key: value for key, value in locals().items() if key not in {"self", "confirm"}}
        )
        command = QUESTION_OPERATIONS[operation][2]
        require_replication_operation_key(operation_key, command_name=command)
        replay = self.receipts.read(idempotency_key=operation_key)
        if replay is not None:
            if replay.operation != operation or replay.request_fingerprint_sha256 != fingerprint:
                raise ValueError(
                    "P2P_IDEMPOTENCY_CONFLICT: question operation key was used for a different request"
                )
            replay_replication_outcome(self.root, mutation_operation_id=operation)
            return self._payload(
                replay.result, authority=replay.authority, actor=replay.actor, replayed=True
            )
        self.preflight(self._preflight_operation(scope, leaf))
        authority_sources = tuple(
            source_precondition(
                path.relative_to(self.root).as_posix(), path.read_bytes() if path.exists() else None
            )
            for path in (self.authority.path, self.authority.permissions.path())
        )
        context, evidence = self.authority.resolve(
            supplied_context=authority_context,
            subject_id=actor_id,
            executor_id=executor_id or actor_id,
            executor_kind=executor_kind,
            required_capabilities=(f"{scope}.question.{leaf}",),
            channel="cli",
        )
        subject, executor = evidence.subject.identity_id, evidence.executor.identity_id
        if scope == "proposal":
            path, content, candidate, questions = self.proposal.mutation_candidate(
                str(proposal_id),
                operation=leaf,
                actor=subject,
                executor=executor,
                question_id=question_id,
                expected_revision=expected_revision,
                answer=str(request["answer"]),
                source=str(request["source"]),
                reason=str(request["reason"]),
                replace_answer=replace_answer,
                question_ids=request["question_ids"],
            )
            relative = path.relative_to(self.root).as_posix()
            candidates = {relative: candidate}
            sources = (source_precondition(relative, content),)
        elif leaf in {"answer", "defer", "mute", "reopen"}:
            if (
                expected_revision is None
                or isinstance(expected_revision, bool)
                or expected_revision < 1
            ):
                raise ValueError(
                    "P2P_QUESTION_REVISION_REQUIRED: expected revision must be positive"
                )
            if leaf == "answer":
                plan = self.project.answer_candidate(
                    question_id,
                    values=request["values"],
                    actor=subject,
                    executor=executor,
                    expected_revision=expected_revision,
                    replace_answer=replace_answer,
                    evidence_refs=request["evidence_refs"],
                )
            else:
                plan = self.project.lifecycle_candidate(
                    question_id,
                    actor=subject,
                    executor=executor,
                    expected_revision=expected_revision,
                    reason=str(request["reason"]),
                    operation=leaf,
                )
            relative = self.project.path.relative_to(self.root).as_posix()
            candidates = {relative: self.project.render_update_candidate(plan)}
            sources = (source_precondition(relative, plan.source_content),)
            questions = [plan.updated]
        else:
            if not confirm:
                raise ValueError("P2P_CONFIRMATION_REQUIRED: confirm the exact question preview")
            actor = PermissionActor(
                subject,
                "owner",
                evidence.subject.kind.value,
                subject,
                self.authority.permissions.path(),
            )
            bundle = (
                self.convergence.render_authorized_plan(question_ids, actor=actor)
                if leaf == "apply"
                else self.convergence.render_authorized_reconciliation(actor=actor)
            )
            token = semantic_sha256(
                {
                    "plan": bundle.public.preview.preview_token,
                    "authority_context_sha256": context.digest_sha256,
                    "operation_key_sha256": idempotency_key_sha256(operation_key),
                }
            )
            if preview_token != token:
                raise ValueError("P2P_PREVIEW_STALE: question preview inputs or authority changed")
            relative = self.project.path.relative_to(self.root).as_posix()
            if leaf == "apply":
                candidates = {
                    ".p2p/project/definition.yml": bundle.definition_candidate_bytes,
                    relative: bundle.question_candidate_bytes,
                }
                questions = [
                    item
                    for item in bundle.question_candidate.questions
                    if item.question_id in set(question_ids)
                ]
            else:
                candidates = {relative: bundle.candidate_bytes}
                questions = []
            sources = bundle.snapshot.source_preconditions
        projections = sorted(
            (question_projection(item, scope=scope) for item in questions),
            key=lambda item: item["id"],
        )
        result = {
            "contract": QUESTION_MUTATION_CONTRACT,
            "operation": operation,
            "operation_id": QUESTION_OPERATIONS[operation][2],
            "scope": scope,
            "proposal_id": proposal_id,
            "effect": "plan_registered"
            if scope == "proposal" and leaf == "apply"
            else "definition_applied"
            if leaf == "apply"
            else "state_updated",
            "question_ids": [item["id"] for item in projections],
            "questions": projections,
            "changed_paths": sorted(candidates),
        }
        bounded_question_result(result)
        validate_question_mutation_result(result, operation=operation)
        receipt_path, receipt_bytes, _ = self.receipts.prepare(
            idempotency_key=operation_key,
            operation=operation,
            actor=executor,
            request_fingerprint_sha256=fingerprint,
            preview_token=preview_token or semantic_sha256(request),
            result=result,
            candidates=candidates,
            authority=evidence,
        )
        source_map = {
            item.path: item
            for item in (*sources, *authority_sources, source_precondition(receipt_path, None))
        }

        def validate(view):
            for path in candidates:
                if path.endswith("questions.yml"):
                    if scope == "project":
                        self.project.parse_bytes(view.read_bytes(path), target=path)
                    else:
                        from p2p_engine.foundation.yaml_loaders import load_yaml

                        validate_proposal_questions_payload(load_yaml(view.read_bytes(path)))
                elif path == ".p2p/project/definition.yml":
                    definition = self.convergence.vertical_service.parse_definition_bytes(
                        view.read_bytes(path), path=self.root / path
                    )
                    self.convergence.vertical_service.validate_definition_state(
                        definition, bundle.snapshot.pack
                    )

        mutation = self.writer.apply(
            operation_id=operation,
            candidates={**candidates, receipt_path: receipt_bytes},
            sources=tuple(source_map.values()),
            preview_token=preview_token or semantic_sha256(request),
            actor=executor,
            candidate_validator=validate,
        )
        if mutation.status != "applied":
            # Surface an interrupted journal through the shared receipt/recovery
            # contract before returning a generic write failure.
            self.receipts.read(idempotency_key=operation_key)
            code = (
                "P2P_QUESTION_LOCKED"
                if mutation.status == "blocked"
                else "P2P_QUESTION_MUTATION_FAILED"
            )
            raise ValueError(f"{code}: {mutation.message}")
        committed = self.receipts.read(idempotency_key=operation_key)
        if committed is None or committed.request_fingerprint_sha256 != fingerprint:
            raise ValueError(
                "P2P_REPLICATION_STATE_INVALID: question mutation has no matching durable receipt"
            )
        return self._payload(result, authority=evidence.to_dict(), actor=executor, replayed=False)

    @staticmethod
    def _preflight_operation(scope: str, leaf: str) -> str:
        if scope == "project":
            return {
                "apply": "project_readiness_convergence_apply",
                "reconcile": "project_questions_reconcile_apply",
            }.get(leaf, f"project_questions_{leaf}")
        return {"answer": "proposal_questions_answer", "apply": "proposal_questions_apply"}.get(
            leaf, "proposal_questions_set_state"
        )

    @staticmethod
    def _payload(
        result: Mapping[str, object],
        *,
        authority: Mapping[str, object] | None,
        actor: str,
        replayed: bool,
    ) -> dict[str, object]:
        return {
            "question_mutation": {
                key: value for key, value in result.items() if key != "changed_paths"
            },
            "authority": dict(authority) if authority else None,
            "mutation": {
                "status": "already_applied" if replayed else "applied",
                "operation_id": result["operation_id"],
                "actor": actor,
                "replayed": replayed,
            },
        }

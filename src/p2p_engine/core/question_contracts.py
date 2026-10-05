from __future__ import annotations

import re
from collections.abc import Mapping

from p2p_engine.core.mutation_preview import canonical_json_bytes

QUESTION_PAGE_CONTRACT = "p2p-question-page/v1"
QUESTION_NEXT_CONTRACT = "p2p-question-next/v1"
QUESTION_PREVIEW_CONTRACT = "p2p-question-preview/v1"
QUESTION_MUTATION_CONTRACT = "p2p-question-mutation-result/v1"
QUESTION_MAX_TEXT = 8000
QUESTION_MAX_SELECTION = 32
QUESTION_MAX_RESULT_BYTES = 48 * 1024
QUESTION_OPERATIONS = {
    **{
        f"project_question_{leaf}": ("project", leaf, f"project.readiness.questions.{leaf}")
        for leaf in ("answer", "defer", "mute", "reopen")
    },
    "project_question_reconcile": (
        "project",
        "reconcile",
        "project.readiness.questions.reconcile-apply",
    ),
    "project_question_apply": ("project", "apply", "project.readiness.apply"),
    **{
        f"proposal_question_{leaf}": ("proposal", leaf, f"proposal.questions.{leaf}")
        for leaf in ("answer", "defer", "mute", "reopen", "apply")
    },
}


def bounded_question_result(result: Mapping[str, object]) -> None:
    if len(canonical_json_bytes(result)) > QUESTION_MAX_RESULT_BYTES:
        raise ValueError(
            "P2P_QUESTION_LIMIT_INVALID: result exceeds 48 KiB; select fewer questions"
        )


def validate_question_projection(item: Mapping[str, object], *, scope: str) -> None:
    common = {"id", "revision", "state", "priority", "question", "rationale", "truncated_fields"}
    extra = (
        {"section_id", "gap_id", "applicability", "answer_contract", "answer"}
        if scope == "project"
        else {"group_id", "gap", "answer", "provided_by", "recorded_by", "application_effect"}
    )
    if set(item) != common | extra:
        raise ValueError("Question projection has invalid fields")
    if not isinstance(item["id"], str) or not re.fullmatch(
        r"PRQ-[A-Za-z0-9_-]+" if scope == "project" else r"Q\d{3,}", item["id"]
    ):
        raise ValueError("Question projection ID is invalid")
    revision = item["revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("Question projection revision is invalid")
    if item["priority"] not in {"high", "medium", "low"}:
        raise ValueError("Question projection priority is invalid")
    states = {
        "to_answer",
        "answered",
        "applied",
        "deferred" if scope == "project" else "defer",
        "muted",
        "retired",
        "superseded",
    }
    if item["state"] not in states:
        raise ValueError("Question projection state is invalid")
    fields = item["truncated_fields"]
    if (
        not isinstance(fields, list)
        or any(not isinstance(field, str) or field not in common | extra for field in fields)
        or fields != sorted(set(fields))
    ):
        raise ValueError("Question projection truncation fields are invalid")
    for field in ("question", "rationale", *(("gap",) if scope == "proposal" else ())):
        if not isinstance(item[field], str) or len(item[field]) > 2000:
            raise ValueError("Question projection text is invalid")
    if scope == "project":
        if item["applicability"] not in {
            "active",
            "vertical_mismatch",
            "target_removed",
            "reconciliation_required",
        }:
            raise ValueError("Question projection applicability is invalid")
        for field in ("section_id", "gap_id"):
            if not isinstance(item[field], str) or len(item[field]) > 512:
                raise ValueError("Question projection target is invalid")
        contract = item["answer_contract"]
        if (
            not isinstance(contract, Mapping)
            or not {"kind", "required_fields", "allowed_definition_operations"} <= set(contract)
            or set(contract)
            - {"kind", "required_fields", "allowed_definition_operations", "allowed_values"}
        ):
            raise ValueError("Question projection answer contract is invalid")
        if contract["kind"] not in {
            "field_value",
            "section_disposition",
            "assumption_resolution",
            "blocker_resolution",
            "owner_decision_reference",
            "informational",
        }:
            raise ValueError("Question projection answer kind is invalid")
        for field in (
            "required_fields",
            "allowed_definition_operations",
            *(("allowed_values",) if "allowed_values" in contract else ()),
        ):
            if (
                not isinstance(contract[field], list)
                or len(contract[field]) > 32
                or any(not isinstance(value, str) or len(value) > 512 for value in contract[field])
            ):
                raise ValueError("Question projection answer contract values are invalid")
        answer = item["answer"]
        if answer is not None:
            if (
                not isinstance(answer, Mapping)
                or set(answer) != {"values", "evidence_refs", "provided_by", "recorded_by"}
                or not isinstance(answer["values"], Mapping)
            ):
                raise ValueError("Question projection latest answer is invalid")
            if (
                not isinstance(answer["evidence_refs"], list)
                or len(answer["evidence_refs"]) > 32
                or any(
                    not isinstance(value, str) or len(value) > 512
                    for value in answer["evidence_refs"]
                )
            ):
                raise ValueError("Question projection answer evidence is invalid")
            if any(
                not isinstance(answer[field], str) or len(answer[field]) > 512
                for field in ("provided_by", "recorded_by")
            ):
                raise ValueError("Question projection answer provenance is invalid")
    else:
        for field in ("group_id", "answer", "provided_by", "recorded_by"):
            if not isinstance(item[field], str) or len(item[field]) > (
                QUESTION_MAX_TEXT if field == "answer" else 512
            ):
                raise ValueError("Question projection proposal answer is invalid")
        if item["application_effect"] not in {"not_registered", "plan_registered"}:
            raise ValueError("Question projection proposal application effect is invalid")
    if len(canonical_json_bytes(item)) > 32 * 1024:
        raise ValueError("Question projection exceeds its byte limit")


def validate_question_mutation_result(result: Mapping[str, object], *, operation: str) -> None:
    if set(result) != {
        "contract",
        "operation",
        "operation_id",
        "scope",
        "proposal_id",
        "effect",
        "question_ids",
        "questions",
        "changed_paths",
    }:
        raise ValueError("Question mutation result has invalid fields")
    if result.get("contract") != QUESTION_MUTATION_CONTRACT or operation not in QUESTION_OPERATIONS:
        raise ValueError("Question mutation result contract or operation is unsupported")
    scope, leaf, command = QUESTION_OPERATIONS[operation]
    if (
        result.get("operation") != operation
        or result.get("operation_id") != command
        or result.get("scope") != scope
    ):
        raise ValueError("Question mutation result operation identity differs")
    proposal_id = result.get("proposal_id")
    if scope == "proposal":
        if not isinstance(proposal_id, str) or not re.fullmatch(r"PROP-\d{3,}", proposal_id):
            raise ValueError("Question mutation result proposal ID is invalid")
    elif proposal_id is not None:
        raise ValueError("Project question mutation cannot contain a proposal ID")
    if result.get("effect") != (
        "plan_registered"
        if scope == "proposal" and leaf == "apply"
        else "state_updated"
        if leaf != "apply"
        else "definition_applied"
    ):
        raise ValueError("Question mutation result effect is invalid")
    ids, questions, paths = (
        result.get("question_ids"),
        result.get("questions"),
        result.get("changed_paths"),
    )
    if (
        not isinstance(ids, list)
        or len(ids) > QUESTION_MAX_SELECTION
        or any(not isinstance(item, str) for item in ids)
        or ids != sorted(set(ids))
    ):
        raise ValueError("Question mutation result question IDs are invalid")
    if any(
        not re.fullmatch(r"PRQ-[A-Za-z0-9_-]+" if scope == "project" else r"Q\d{3,}", item)
        for item in ids
    ):
        raise ValueError("Question mutation result question ID format is invalid")
    if not isinstance(questions, list) or len(questions) != len(ids):
        raise ValueError("Question mutation result questions are invalid")
    for item, question_id in zip(questions, ids, strict=True):
        if not isinstance(item, Mapping) or item.get("id") != question_id:
            raise ValueError("Question mutation result question identity differs")
        validate_question_projection(item, scope=scope)
        expected_state = {
            "answer": "answered",
            "defer": "deferred" if scope == "project" else "defer",
            "mute": "muted",
            "reopen": "to_answer",
            "apply": "applied",
        }.get(leaf)
        if expected_state and item["state"] != expected_state:
            raise ValueError("Question mutation result state differs from operation")
    if leaf in {"answer", "defer", "mute", "reopen"} and len(ids) != 1:
        raise ValueError("Single question mutation result requires exactly one question")
    if not isinstance(paths, list) or not paths or paths != sorted(set(paths)):
        raise ValueError("Question mutation result changed paths are invalid")
    if scope == "project":
        expected = (
            [".p2p/project/definition.yml", ".p2p/project/questions.yml"]
            if leaf == "apply"
            else [".p2p/project/questions.yml"]
        )
        if paths != expected:
            raise ValueError("Project question mutation result paths are invalid")
    elif len(paths) != 1 or not re.fullmatch(
        rf"\.p2p/proposals/{re.escape(str(proposal_id))}-[a-z0-9-]+/questions.yml", paths[0]
    ):
        raise ValueError("Proposal question mutation result path is invalid")
    bounded_question_result(result)

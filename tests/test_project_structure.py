from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import threading

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.authority import (
    AuthorityBasis,
    AuthorityClaim,
    AuthorityContext,
    AuthorityIdentity,
    AuthorityIdentityKind,
    AuthorityMode,
    AuthorityProjectBinding,
)
from p2p_engine.core.project_structure import (
    PROJECT_STRUCTURE_CONTRACT,
    PROJECT_STRUCTURE_MUTATION_CONTRACT,
    ProjectStructure,
    StructureField,
    StructureOrigin,
    StructureSection,
    project_structure_checksum,
    validate_project_structure,
    with_project_structure_checksum,
)
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.project_structure import ProjectStructureService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_error


runner = CliRunner()


def _workspace(tmp_path: Path, *, starter: str = "generic") -> P2PWorkspace:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Project Structure",
        owner="owner",
        starter_id=starter,
    )
    return workspace


def _external_context(capability: str, *, decision: str) -> AuthorityContext:
    return AuthorityContext(
        mode=AuthorityMode.external_attestation,
        project_authority=AuthorityProjectBinding(
            authority_id="hosted-authority-01",
            generation=1,
            provider_id="hosted-provider",
            provider_policy_version="project-capabilities-v1",
        ),
        subject=AuthorityIdentity("hosted-owner-01", AuthorityIdentityKind.user),
        executor=AuthorityIdentity("hosted-client-01", AuthorityIdentityKind.client),
        authorization_decision_id=decision,
        authorized_at="2026-08-26T12:00:00Z",
        claims=(
            AuthorityClaim(
                capability=capability,
                basis=AuthorityBasis.root_authority,
                authority_generation=1,
            ),
        ),
    )


def _add_section(
    workspace: P2PWorkspace,
    *,
    key: str,
    revision: int,
    title: str = "Distribution",
    context: AuthorityContext | None = None,
) -> object:
    actor = context.subject.identity_id if context is not None else "owner"
    executor = context.executor.identity_id if context is not None else "owner"
    executor_kind = context.executor.kind.value if context is not None else "person"
    return workspace.change_project_structure(
        operation="add_section",
        operation_key=key,
        expected_revision=revision,
        actor_id=actor,
        executor_id=executor,
        executor_kind=executor_kind,
        request={"title": title, "description": "Distribution constraints.", "required": True},
        authority_context=context,
    )


def test_generic_initialization_materializes_detached_revision_one_structure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    structure = workspace.project_structure(include_retired=True)
    source = workspace.project_structure_source()

    assert structure.contract == PROJECT_STRUCTURE_CONTRACT
    assert structure.revision == 1
    assert structure.sections
    assert structure.origin.kind == "starter"
    assert structure.origin.identity == "generic"
    assert source["source"] == {"kind": "starter", "starter_id": "generic"}
    assert workspace.project_structure_history(limit=10).events[0].event_type == "initialized"

    monkeypatch.setattr(
        workspace._project_vertical_service(),
        "resolve_pack",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live source lookup")),
    )
    assert workspace.project_structure().checksum == structure.checksum


def test_empty_and_exact_release_initialization_have_explicit_origins(tmp_path: Path) -> None:
    empty_root = tmp_path / "empty"
    exact_root = tmp_path / "exact"
    empty = _workspace(empty_root, starter="empty").project_structure()
    exact_workspace = P2PWorkspace(exact_root)
    exact_workspace.init_project(
        "Exact Structure",
        owner="owner",
        vertical_id="binarya/software_project@2.0.0",
    )
    exact = exact_workspace.project_structure()

    assert empty.revision == 1
    assert empty.sections == ()
    assert empty.criteria == ()
    assert empty.origin.identity == "empty"
    assert exact.origin.kind == "vertical_release"
    assert exact.origin.identity == "binarya/software_project@2.0.0"
    assert exact.origin.checksum
    assert {section.section_id for section in exact.sections} >= {
        "system_objective",
        "mvp_scope",
    }


def test_long_project_name_produces_bounded_stable_structure_id(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("A" * 120, owner="owner", starter_id="empty")

    structure_id = workspace.project_structure().structure_id
    assert len(structure_id) <= 64
    assert structure_id.endswith("structure") is False
    assert P2PWorkspace(tmp_path).project_structure().structure_id == structure_id


def test_definition_references_project_structure_section_and_field_ids(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    structure = workspace.project_structure()
    definition = workspace.project_definition_view()

    assert definition.valid is True
    assert definition.state is not None
    assert definition.state.structure_id == structure.structure_id
    assert definition.state.structure_revision == structure.revision
    structure_fields = {
        (field.section_id, field.field_id)
        for field in structure.fields
        if field.lifecycle == "active"
    }
    definition_fields = {
        (section.section_id, field_id)
        for section in definition.state.sections
        for field_id in section.missing_required_fields
    }
    assert definition_fields <= structure_fields


def test_add_rename_and_reorder_preserve_ids_and_advance_once(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    added = _add_section(workspace, key="structure-add-12345678", revision=1)
    assert added.status == "applied"
    section_id = added.current.sections[0].section_id

    renamed = workspace.change_project_structure(
        operation="update_metadata",
        operation_key="structure-rename-12345678",
        expected_revision=2,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        request={
            "element_kind": "section",
            "element_id": section_id,
            "title": "Distribution Model",
        },
    )
    _add_section(
        workspace,
        key="structure-add-second-12345678",
        revision=3,
        title="Operations",
    )
    reordered = workspace.change_project_structure(
        operation="reorder_sections",
        operation_key="structure-reorder-12345678",
        expected_revision=4,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        request={"section_ids": ["operations", section_id]},
    )

    assert renamed.current.sections[0].section_id == section_id
    assert renamed.current.sections[0].title == "Distribution Model"
    assert [item.section_id for item in reordered.current.sections] == ["operations", section_id]
    assert reordered.current.revision == 5
    assert workspace.project_structure_history(limit=2).truncated is True


def test_stale_revision_and_divergent_replay_leave_structure_unchanged(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    first = _add_section(workspace, key="structure-replay-12345678", revision=1)
    replay = _add_section(workspace, key="structure-replay-12345678", revision=1)
    before = (tmp_path / ".p2p/project/structure.yml").read_bytes()

    assert replay.status == "already_applied"
    assert replay.current.checksum == first.current.checksum
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        _add_section(
            workspace,
            key="structure-replay-12345678",
            revision=1,
            title="Different",
        )
    with pytest.raises(ValueError, match="P2P_PROJECT_STRUCTURE_STALE_REVISION"):
        _add_section(workspace, key="structure-stale-12345678", revision=1, title="Stale")
    assert (tmp_path / ".p2p/project/structure.yml").read_bytes() == before


def test_reorder_requires_complete_exact_active_set(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    current = workspace.project_structure()
    section_ids = list(current.active_section_ids())

    with pytest.raises(ValueError, match="P2P_PROJECT_STRUCTURE_REORDER_INVALID"):
        workspace.change_project_structure(
            operation="reorder_sections",
            operation_key="structure-invalid-order-12345678",
            expected_revision=current.revision,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
            request={"section_ids": section_ids[:-1]},
        )
    assert workspace.project_structure().revision == current.revision


def test_structure_validation_detects_checksum_and_reference_drift() -> None:
    origin = StructureOrigin("starter", "empty", None, "2026-08-26", "owner")
    base = with_project_structure_checksum(
        ProjectStructure(
            structure_id="test-structure",
            revision=1,
            checksum="0" * 64,
            origin=origin,
            sections=(StructureSection("scope", "Scope", order=0),),
        )
    )
    with pytest.raises(ValueError, match="CHECKSUM_MISMATCH"):
        validate_project_structure(replace(base, sections=(replace(base.sections[0], title="Changed"),)))
    with pytest.raises(ValueError, match="broken section reference"):
        ProjectStructure(
            structure_id="test-structure",
            revision=1,
            checksum="0" * 64,
            origin=origin,
            fields=(StructureField("summary", "missing", "Summary"),),
        )


def test_public_structure_collections_are_bounded_and_report_truncation() -> None:
    origin = StructureOrigin("starter", "empty", None, "2026-08-26", "owner")
    fields = tuple(
        StructureField(f"field-{index:03d}", "scope", f"Field {index}", order=index)
        for index in range(251)
    )
    structure = with_project_structure_checksum(
        ProjectStructure(
            structure_id="bounded-structure",
            revision=1,
            checksum="0" * 64,
            origin=origin,
            sections=(StructureSection("scope", "Scope", order=0),),
            fields=fields,
        )
    )

    payload = structure.to_dict()
    assert len(payload["fields"]) == 250
    assert payload["collections"]["fields"] == {
        "total": 251,
        "returned": 250,
        "truncated": True,
    }
    assert len(structure.to_storage_dict()["fields"]) == 251
    assert project_structure_checksum(structure) == structure.checksum


def test_structure_receipt_is_compact_and_status_is_recoverable(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    key = "structure-receipt-12345678"
    result = _add_section(
        workspace,
        key=key,
        revision=workspace.project_structure().revision,
    )
    status = workspace.mutation_status(idempotency_key=key)
    receipt_path = workspace._mutation_receipt_service().root / workspace._mutation_receipt_service().relative_path(key)

    assert result.current.revision == 2
    assert status.state == "applied"
    assert status.result["current"] == {
        "contract": PROJECT_STRUCTURE_CONTRACT,
        "structure_id": result.current.structure_id,
        "revision": result.current.revision,
        "checksum": result.current.checksum,
    }
    assert receipt_path.stat().st_size < 65_536


def test_fault_before_commit_preserves_structure_event_and_receipt(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    before_structure = (tmp_path / ".p2p/project/structure.yml").read_bytes()
    before_events = (tmp_path / ".p2p/project/structure-events.yml").read_bytes()

    def fail(stage: str, _target: str) -> None:
        if stage == "before_journal":
            raise RuntimeError("injected structure failure")

    workspace._project_structure_service_instance = ProjectStructureService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=fail,
        ),
    )
    key = "structure-fault-12345678"
    with pytest.raises(ValueError, match="P2P_PROJECT_STRUCTURE_MUTATION_FAILED"):
        _add_section(workspace, key=key, revision=1)

    assert (tmp_path / ".p2p/project/structure.yml").read_bytes() == before_structure
    assert (tmp_path / ".p2p/project/structure-events.yml").read_bytes() == before_events
    assert workspace.mutation_status(idempotency_key=key).state == "not_found"


def test_interrupted_structure_mutation_can_be_rolled_back_without_partial_state(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    structure_path = tmp_path / ".p2p/project/structure.yml"
    events_path = tmp_path / ".p2p/project/structure-events.yml"
    before_structure = structure_path.read_bytes()
    before_events = events_path.read_bytes()
    interrupted_candidates: dict[Path, bytes] = {}

    def interrupt(stage: str, target: str) -> None:
        if stage == "after_replace" and target == ".p2p/project/structure.yml":
            candidate_paths = [structure_path, events_path]
            candidate_paths.extend(
                (tmp_path / ".p2p/.internal/mutation-receipts").glob("*.yml")
            )
            interrupted_candidates.update(
                {path.relative_to(tmp_path): path.read_bytes() for path in candidate_paths}
            )
            structure_path.write_bytes(b"external interruption")
            raise RuntimeError("injected structure interruption")

    workspace._project_structure_service_instance = ProjectStructureService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=interrupt,
        ),
    )
    key = "structure-interrupted-12345678"

    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION"):
        _add_section(workspace, key=key, revision=1)

    recovery = workspace.workspace_transaction_recovery_status()
    assert recovery.required is True
    assert recovery.transaction_id
    assert interrupted_candidates
    for relative, content in interrupted_candidates.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    rolled_back = workspace.rollback_workspace_transaction(
        transaction_id=recovery.transaction_id,
        actor="owner",
        confirm=True,
    )

    assert rolled_back.status == "rolled_back"
    assert structure_path.read_bytes() == before_structure
    assert events_path.read_bytes() == before_events
    assert workspace.mutation_status(idempotency_key=key).state == "not_found"
    assert workspace.workspace_transaction_recovery_status().required is False


def test_concurrent_apply_has_one_winner_and_no_partial_state(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    barrier = threading.Barrier(2)

    class BarrierWriter(AtomicMutationWriter):
        def apply(self, **kwargs):  # type: ignore[no-untyped-def]
            barrier.wait(timeout=5)
            return super().apply(**kwargs)

    workspace._project_structure_service_instance = ProjectStructureService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        atomic_writer=BarrierWriter(root=tmp_path, p2p_dir=tmp_path / ".p2p"),
    )
    results: list[str] = []

    def mutate(index: int) -> None:
        try:
            result = _add_section(
                workspace,
                key=f"structure-concurrent-{index}-12345678",
                revision=1,
                title=f"Section {index}",
            )
            results.append(result.status)
        except ValueError as exc:
            results.append(str(exc))

    threads = [threading.Thread(target=mutate, args=(index,)) for index in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert results.count("applied") == 1
    assert len(results) == 2
    assert workspace.project_structure().revision == 2
    assert len(workspace.project_structure().sections) == 1
    assert workspace._project_structure_service().validate() == ()


def test_local_non_owner_cannot_edit_project_structure(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    workspace.permissions_actor_add("supporter", role="contributor")

    with pytest.raises(ValueError, match="P2P_AUTHORIZATION_DENIED"):
        workspace.change_project_structure(
            operation="add_section",
            operation_key="structure-local-supporter-12345678",
            expected_revision=1,
            actor_id="supporter",
            executor_id="supporter",
            executor_kind="person",
            request={"title": "Unauthorized section"},
        )

    assert workspace.project_structure().revision == 1
    assert workspace.project_structure().sections == ()


def test_cli_json_structure_read_write_and_error_contract(tmp_path: Path) -> None:
    _workspace(tmp_path, starter="empty")
    shown = runner.invoke(
        app,
        ["project", "structure", "show", "--format", "json", "--root", str(tmp_path)],
    )
    added = runner.invoke(
        app,
        [
            "project",
            "structure",
            "add-section",
            "Distribution",
            "--expected-revision",
            "1",
            "--operation-key",
            "structure-cli-12345678",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    missing_key = runner.invoke(
        app,
        [
            "project",
            "structure",
            "add-section",
            "Invalid",
            "--expected-revision",
            "2",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert shown.exit_code == 0, shown.output
    assert cli_data(shown, operation="project.structure.show")["project_structure"]["revision"] == 1
    assert added.exit_code == 0, added.output
    mutation = cli_data(added, operation="project.structure.add-section")["project_structure_mutation"]
    assert mutation["contract"] == PROJECT_STRUCTURE_MUTATION_CONTRACT
    assert mutation["current"]["revision"] == 2
    assert missing_key.exit_code != 0
    assert cli_error(missing_key)["code"] == "P2P_IDEMPOTENCY_KEY_REQUIRED"


def test_mcp_structure_read_and_consent_gated_mutation_have_parity(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, starter="empty")
    consent = workspace.consent_grant(
        "project_structure_add_section",
        "project-structure",
        "owner",
        approved_by="owner",
    )
    arguments = {
        "root": str(tmp_path),
        "title": "Distribution",
        "expected_revision": 1,
        "actor_id": "owner",
        "consent_id": consent.consent_id,
        "operation_key": "structure-mcp-12345678",
    }

    first = call_tool("p2p_project_structure_add_section", arguments)
    replay = call_tool("p2p_project_structure_add_section", arguments)
    shown = call_tool("p2p_project_structure_show", {"root": str(tmp_path)})

    assert first["project_structure_mutation"]["status"] == "applied"
    assert first["consent"]["status"] == "consumed"
    assert replay["project_structure_mutation"]["status"] == "already_applied"
    assert replay["consent"]["status"] == "consumed"
    assert shown["project_structure"] == workspace.project_structure().to_dict(include_retired=False)
    assert shown["mutation_performed"] is False


def test_external_structure_authority_is_bound_to_receipt_and_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Hosted Structure",
        owner="local-maintainer",
        starter_id="empty",
        authority_context=_external_context(
            "project.initialize",
            decision="hosted-init-decision-01",
        ),
    )
    context = _external_context(
        "project.structure.edit",
        decision="hosted-structure-decision-01",
    )
    key = "external-structure-12345678"
    result = _add_section(workspace, key=key, revision=1, context=context)
    status = workspace.mutation_status(idempotency_key=key)

    assert result.status == "applied"
    assert status.authority is not None
    assert status.authority["authority_context_sha256"] == context.digest_sha256
    changed_context = _external_context(
        "project.structure.edit",
        decision="hosted-structure-decision-02",
    )
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        _add_section(workspace, key=key, revision=1, context=changed_context)
    assert workspace.project_structure().revision == 2

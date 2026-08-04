from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.changes import ChangeSetLifecycleService
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.services.software_spec import (
    SoftwareSpecFreshness,
    SoftwareSpecOrigin,
    SoftwareSpecService,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _workspace_with_change(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project")
    workspace.create_proposal_with_details(
        title="Spec Work",
        problem="Need implementation-facing specs.",
        proposal="Generate a deterministic software spec.",
        acceptance_criteria=["Spec artifacts exist."],
    )
    record_decision(
        workspace,
        "PROP-001",
        DecisionOutcome.accepted,
        reason="Needed before export.",
        approver="owner",
    )
    workspace.create_change_set("PROP-001")
    return workspace


def _service(
    workspace: P2PWorkspace,
    *,
    atomic_writer: AtomicMutationWriter | None = None,
    source_reader=None,
) -> SoftwareSpecService:
    proposal_documents = ProposalDocumentService(root=workspace.root, p2p_dir=workspace.p2p_dir)
    changes = ChangeSetLifecycleService(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        find_proposal_dir=proposal_documents.find_dir,
    )
    return SoftwareSpecService(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        find_change_dir=changes.find_dir,
        show_change_set=workspace.show_change_set,
        find_proposal_dir=proposal_documents.find_dir,
        atomic_writer=atomic_writer,
        source_reader=source_reader,
    )


def _required_bytes(service: SoftwareSpecService, root: Path) -> dict[str, bytes]:
    spec_dir = root / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    return {
        filename: (spec_dir / filename).read_bytes()
        for filename in service.required_files()
    }


def test_software_spec_service_refresh_status_show_prompt_and_import(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)

    refreshed = service.refresh("CHANGE-001")

    assert refreshed.change_id == "CHANGE-001"
    assert refreshed.status == "generated"
    assert refreshed.freshness == SoftwareSpecFreshness.CURRENT
    assert refreshed.origin == SoftwareSpecOrigin.GENERATED
    assert refreshed.path == Path(".p2p/outputs/software-spec/CHANGE-001")

    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    for filename in service.required_files():
        assert (spec_dir / filename).exists()
    assert "Software Spec - CHANGE-001 - Spec Work" in service.show("CHANGE-001")
    generated_status = service.statuses()[0]
    assert generated_status.status == "generated"
    assert generated_status.freshness == SoftwareSpecFreshness.CURRENT
    provenance = yaml.safe_load(
        (spec_dir / "provenance.yml").read_text(encoding="utf-8")
    )
    generation = provenance["p2p_generation"]
    assert generation["schema_version"] == 1
    assert generation["origin"] == "generated"
    assert generation["source_fingerprint"]["algorithm"] == "sha256"
    assert generation["source_fingerprint"]["value"]
    assert {item["path"] for item in generation["sources"]} == {
        ".p2p/changes/CHANGE-001-spec-work/change.md",
        ".p2p/changes/CHANGE-001-spec-work/tasks.yml",
        ".p2p/proposals/PROP-001-spec-work/proposal.md",
    }
    assert len(generation["outputs"]) == 6

    prompt = service.create_prompt("CHANGE-001")
    assert prompt.prompt_path == Path(".p2p/outputs/software-spec/CHANGE-001/spec-refine.prompt.md")
    assert "P2P Software Spec Refinement Prompt" in (tmp_path / prompt.prompt_path).read_text(encoding="utf-8")

    refined_dir = tmp_path / "refined"
    refined_dir.mkdir()
    for filename in ("index.md", "requirements.md", "design.md", "acceptance.md"):
        (refined_dir / filename).write_text(f"# {filename}\n\nRefined.\n", encoding="utf-8")
    (refined_dir / "commands.yml").write_text("commands: []\n", encoding="utf-8")
    (refined_dir / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (refined_dir / "provenance.yml").write_text("source:\n  change: CHANGE-001\n", encoding="utf-8")

    imported = service.import_spec("CHANGE-001", refined_dir)

    assert Path(".p2p/outputs/software-spec/CHANGE-001/index.md") in imported
    assert "Refined." in service.show("CHANGE-001")
    imported_provenance = yaml.safe_load(
        (spec_dir / "provenance.yml").read_text(encoding="utf-8")
    )
    assert imported_provenance["source"]["change"] == "CHANGE-001"
    assert imported_provenance["p2p_generation"]["origin"] == "imported"
    imported_status = service.statuses()[0]
    assert imported_status.status == "generated"
    assert imported_status.freshness == SoftwareSpecFreshness.CURRENT_IMPORTED
    assert imported_status.origin == SoftwareSpecOrigin.IMPORTED


def test_software_spec_service_import_validation_errors(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    source = tmp_path / "broken"
    source.mkdir()

    with pytest.raises(ValueError, match="Missing required software spec artifact: index.md"):
        service.import_spec("CHANGE-001", source)

    for filename in service.required_files():
        (source / filename).write_text("# ok\n", encoding="utf-8")
    (source / "commands.yml").write_text("other: []\n", encoding="utf-8")
    (source / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (source / "provenance.yml").write_text("source: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid YAML: expected top-level `commands` key."):
        service.import_spec("CHANGE-001", source)


def test_software_spec_candidate_is_pure_deterministic_and_exactly_scoped(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    first = service.build_candidate("CHANGE-001")
    second = service.build_candidate("CHANGE-001")

    assert first == second
    assert first.source_fingerprint_sha256
    assert {item.path for item in first.sources} == {
        ".p2p/changes/CHANGE-001-spec-work/change.md",
        ".p2p/changes/CHANGE-001-spec-work/tasks.yml",
        ".p2p/proposals/PROP-001-spec-work/proposal.md",
    }
    assert all(not Path(item.path).is_absolute() for item in first.sources)
    assert not (
        tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    ).exists()
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == before


def test_software_spec_candidate_fingerprint_is_checkout_independent(
    tmp_path: Path,
) -> None:
    first = _service(_workspace_with_change(tmp_path / "first")).build_candidate(
        "CHANGE-001"
    )
    second = _service(_workspace_with_change(tmp_path / "second")).build_candidate(
        "CHANGE-001"
    )

    assert first.source_fingerprint_sha256 == second.source_fingerprint_sha256
    assert first.files == second.files


def test_software_spec_status_distinguishes_stale_source_and_modified_output(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    service.refresh("CHANGE-001")
    proposal_path = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-spec-work" / "proposal.md"
    )
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace(
            "Generate a deterministic software spec.",
            "Generate a changed deterministic software spec.",
        ),
        encoding="utf-8",
    )

    stale = service.statuses()[0]

    assert stale.freshness == SoftwareSpecFreshness.STALE
    assert stale.changed_sources == (
        ".p2p/proposals/PROP-001-spec-work/proposal.md",
    )
    assert stale.reasons == ("source_fingerprint_changed",)

    service.refresh("CHANGE-001")
    index_path = (
        tmp_path
        / ".p2p"
        / "outputs"
        / "software-spec"
        / "CHANGE-001"
        / "index.md"
    )
    index_path.write_text(index_path.read_text(encoding="utf-8") + "\nManual.\n")
    before = index_path.read_bytes()

    modified = service.statuses()[0]

    assert modified.freshness == SoftwareSpecFreshness.MODIFIED
    assert modified.changed_outputs == ("index.md",)
    assert index_path.read_bytes() == before


def test_software_spec_unrelated_change_does_not_change_fingerprint(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    refreshed = service.refresh("CHANGE-001")
    workspace.create_proposal_with_details(
        title="Unrelated",
        problem="Separate work.",
        proposal="Do something unrelated.",
    )

    status = service.statuses()[0]

    assert status.freshness == SoftwareSpecFreshness.CURRENT
    assert (
        status.current_source_fingerprint_sha256
        == refreshed.current_source_fingerprint_sha256
    )


def test_software_spec_missing_authoritative_source_is_invalid(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    service.refresh("CHANGE-001")
    change_path = (
        tmp_path / ".p2p" / "changes" / "CHANGE-001-spec-work" / "change.md"
    )
    change_path.unlink()

    status = service.statuses()[0]

    assert status.status == "generated"
    assert status.freshness == SoftwareSpecFreshness.INVALID
    assert status.origin == SoftwareSpecOrigin.GENERATED
    assert status.reasons == ("authoritative_source_unavailable",)
    assert not any(str(tmp_path) in reason for reason in status.reasons)


def test_software_spec_missing_and_malformed_provenance_are_invalid(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    service.refresh("CHANGE-001")
    provenance_path = (
        tmp_path
        / ".p2p"
        / "outputs"
        / "software-spec"
        / "CHANGE-001"
        / "provenance.yml"
    )
    provenance = yaml.safe_load(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("p2p_generation")
    provenance_path.write_text(
        yaml.safe_dump(provenance, sort_keys=False),
        encoding="utf-8",
    )

    missing_generation = service.statuses()[0]

    assert missing_generation.freshness == SoftwareSpecFreshness.INVALID
    assert missing_generation.origin == SoftwareSpecOrigin.INVALID
    assert missing_generation.reasons == ("missing_generation_provenance",)

    provenance_path.write_text("source: [broken]\n", encoding="utf-8")
    malformed = service.statuses()[0]

    assert malformed.freshness == SoftwareSpecFreshness.INVALID
    assert malformed.origin == SoftwareSpecOrigin.INVALID
    assert malformed.reasons == ("missing_generation_provenance",)


def test_software_spec_rejects_reserved_import_provenance(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    source = tmp_path / "reserved"
    source.mkdir()
    for filename in ("index.md", "requirements.md", "design.md", "acceptance.md"):
        (source / filename).write_text(f"# {filename}\n", encoding="utf-8")
    (source / "commands.yml").write_text("commands: []\n", encoding="utf-8")
    (source / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (source / "provenance.yml").write_text(
        "source:\n  change: CHANGE-001\n"
        "p2p_generation:\n  schema_version: 1\n  origin: generated\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="reserved `p2p_generation`"):
        service.import_spec("CHANGE-001", source)


def test_software_spec_refresh_is_byte_and_mtime_idempotent(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    service.refresh("CHANGE-001")
    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    before_bytes = _required_bytes(service, tmp_path)
    before_mtimes = {
        filename: (spec_dir / filename).stat().st_mtime_ns
        for filename in service.required_files()
    }
    proposal_path = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-spec-work" / "proposal.md"
    )
    os.utime(proposal_path, (1, 1))

    service.refresh("CHANGE-001")

    assert _required_bytes(service, tmp_path) == before_bytes
    assert {
        filename: (spec_dir / filename).stat().st_mtime_ns
        for filename in service.required_files()
    } == before_mtimes


def test_software_spec_refresh_rolls_back_complete_set_on_failure(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    baseline = _service(workspace)
    baseline.refresh("CHANGE-001")
    before = _required_bytes(baseline, tmp_path)
    proposal_path = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-spec-work" / "proposal.md"
    )
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace(
            "Generate a deterministic software spec.",
            "Generate a transactionally refreshed software spec.",
        ),
        encoding="utf-8",
    )
    failed = False

    def fail_after_first(stage: str, target: str) -> None:
        nonlocal failed
        if stage == "after_replace" and target and not failed:
            failed = True
            raise RuntimeError("injected software spec refresh failure")

    service = _service(
        workspace,
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=fail_after_first,
        ),
    )

    with pytest.raises(ValueError, match="rolled back"):
        service.refresh("CHANGE-001")

    assert _required_bytes(service, tmp_path) == before


def test_software_spec_import_rolls_back_complete_set_on_failure(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    baseline = _service(workspace)
    baseline.refresh("CHANGE-001")
    before = _required_bytes(baseline, tmp_path)
    source = tmp_path / "refined"
    source.mkdir()
    for filename in ("index.md", "requirements.md", "design.md", "acceptance.md"):
        (source / filename).write_text(
            f"# {filename}\n\nImported.\n",
            encoding="utf-8",
        )
    (source / "commands.yml").write_text("commands: []\n", encoding="utf-8")
    (source / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (source / "provenance.yml").write_text(
        "source:\n  change: CHANGE-001\n",
        encoding="utf-8",
    )
    failed = False

    def fail_after_first(stage: str, target: str) -> None:
        nonlocal failed
        if stage == "after_replace" and target and not failed:
            failed = True
            raise RuntimeError("injected software spec import failure")

    service = _service(
        workspace,
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=fail_after_first,
        ),
    )

    with pytest.raises(ValueError, match="rolled back"):
        service.import_spec("CHANGE-001", source)

    assert _required_bytes(service, tmp_path) == before


def test_software_spec_candidate_rejects_repeated_source_changes(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    proposal_path = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-spec-work" / "proposal.md"
    )

    def changing_reader(path: Path) -> bytes:
        content = path.read_bytes()
        if path == proposal_path:
            path.write_bytes(content + b"\n")
        return content

    service = _service(workspace, source_reader=changing_reader)

    with pytest.raises(ValueError, match="source_changed_during_read"):
        service.build_candidate("CHANGE-001")

    assert not (
        tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    ).exists()


def test_software_spec_incomplete_and_unsupported_provenance_are_explicit(
    tmp_path: Path,
) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    service.refresh("CHANGE-001")
    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    (spec_dir / "acceptance.md").unlink()

    incomplete = service.statuses()[0]

    assert incomplete.status == "incomplete"
    assert incomplete.freshness == SoftwareSpecFreshness.INCOMPLETE
    assert incomplete.reasons == ("missing_required_files:acceptance.md",)

    service.refresh("CHANGE-001")
    provenance_path = spec_dir / "provenance.yml"
    provenance = yaml.safe_load(provenance_path.read_text(encoding="utf-8"))
    provenance["p2p_generation"]["source_fingerprint"]["algorithm"] = "sha1"
    provenance_path.write_text(
        yaml.safe_dump(provenance, sort_keys=False),
        encoding="utf-8",
    )

    unsupported = service.statuses()[0]

    assert unsupported.freshness == SoftwareSpecFreshness.INVALID
    assert unsupported.reasons == ("invalid_source_fingerprint",)

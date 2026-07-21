from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.project_publication import ProjectPublicationService
from p2p_engine.services.project_publication_evidence import ProjectPublicationEvidenceService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _write_scale_sources(root: Path, count: int, *, reverse: bool = False) -> tuple[Path, Path]:
    p2p_dir = root / ".p2p"
    proposals = p2p_dir / "proposals"
    proposals.mkdir(parents=True)
    (p2p_dir / "project.yml").write_text("project:\n  name: Scale\n", encoding="utf-8")
    numbers = range(count, 0, -1) if reverse else range(1, count + 1)
    for number in numbers:
        proposal = proposals / f"PROP-{number:05d}-scale"
        proposal.mkdir()
        proposal.joinpath("proposal.md").write_text(
            f"# Scale {number}\n\nDeterministic evidence {number}.\n",
            encoding="utf-8",
        )
    export = root / "outputs" / "latest" / "project.md"
    export.parent.mkdir(parents=True)
    export.write_text("# Scale Export\n", encoding="utf-8")
    return p2p_dir, export


@pytest.mark.parametrize("proposal_count", [100, 1_000, 10_000])
def test_publication_evidence_scale_has_one_read_per_source(
    tmp_path: Path,
    proposal_count: int,
) -> None:
    p2p_dir, export = _write_scale_sources(tmp_path, proposal_count)
    accepted = [
        {"proposal_id": f"PROP-{number:05d}"}
        for number in range(1, proposal_count + 1)
    ]
    service = ProjectPublicationEvidenceService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        accepted_proposals=lambda: accepted,
    )

    payload = service.build(
        source_fingerprint_sha256="a" * 64,
        source_export_path=export,
        source_export_sha256="b" * 64,
    )

    operations = payload["read_operations"]
    assert payload["counts"]["total"] == proposal_count + 1
    assert payload["source_catalog"]["source_count"] == proposal_count + 1
    assert sum(operations["source_reads"].values()) == proposal_count + 1
    assert max(operations["source_reads"].values()) == 1
    assert sum(operations["discovery_passes"].values()) == 1
    assert operations["schema_deep_validations"] == 0


def test_publication_evidence_bytes_are_enumeration_order_invariant(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_p2p, first_export = _write_scale_sources(first_root, 100)
    second_p2p, second_export = _write_scale_sources(second_root, 100, reverse=True)
    accepted = [{"proposal_id": f"PROP-{number:05d}"} for number in range(1, 101)]

    first = ProjectPublicationEvidenceService(
        root=first_root,
        p2p_dir=first_p2p,
        accepted_proposals=lambda: accepted,
    ).build(
        source_fingerprint_sha256="a" * 64,
        source_export_path=first_export,
        source_export_sha256="b" * 64,
    )
    second = ProjectPublicationEvidenceService(
        root=second_root,
        p2p_dir=second_p2p,
        accepted_proposals=lambda: list(reversed(accepted)),
    ).build(
        source_fingerprint_sha256="a" * 64,
        source_export_path=second_export,
        source_export_sha256="b" * 64,
    )

    assert first == second


def _packet_size(root: Path, *, export_bytes: int) -> int:
    p2p_dir = root / ".p2p"
    p2p_dir.mkdir(parents=True)
    (p2p_dir / "project.yml").write_text("project:\n  name: Packet\n", encoding="utf-8")

    def export():
        target = root / "outputs" / "latest" / "project.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Export\n" + ("x" * export_bytes), encoding="utf-8")
        return SimpleNamespace(archived_path=None)

    service = ProjectPublicationService(
        root=root,
        p2p_dir=p2p_dir,
        export_visible_project=export,
        accepted_proposals=lambda: [],
    )
    service.prepare()
    return service.paths().curator_input.stat().st_size


def test_curator_packet_size_does_not_scale_with_visible_export_bytes(tmp_path: Path) -> None:
    small = _packet_size(tmp_path / "small", export_bytes=1_000)
    large = _packet_size(tmp_path / "large", export_bytes=2_000_000)

    assert abs(large - small) < 128
    assert large < 8_000


def test_workspace_prepare_uses_one_lifecycle_batch_and_vertical_load(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Publication Context",
        owner="owner",
        project_domain="software",
        vertical_id="software_project",
    )
    proposal = workspace.create_proposal_with_details(
        "Publication evidence",
        problem="The publication needs evidence.",
        proposal="Provide complete project evidence.",
    )
    record_decision(
        workspace,
        proposal.proposal_id,
        DecisionOutcome.accepted,
        "Use this project evidence.",
        "owner",
    )
    workspace.refresh_vertical_project_memory()

    workspace.prepare_project_publication()
    evidence = yaml.safe_load(
        (tmp_path / "outputs" / "latest" / "publication-evidence.yml").read_text(
            encoding="utf-8"
        )
    )
    operations = evidence["read_operations"]

    assert operations["provider_calls"]["proposal_lifecycle_batch"] == 1
    assert sum(operations["vertical_pack_loads"].values()) <= 1
    assert operations["schema_deep_validations"] == 0


def test_second_edition_reuses_shared_evidence_without_provider_rebuild(tmp_path: Path) -> None:
    p2p_dir, _export = _write_scale_sources(tmp_path, 100)
    accepted_calls = 0

    def accepted():
        nonlocal accepted_calls
        accepted_calls += 1
        return [{"proposal_id": f"PROP-{number:05d}"} for number in range(1, 101)]

    def export():
        target = tmp_path / "outputs" / "latest" / "project.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Scale Export\n", encoding="utf-8")
        return SimpleNamespace(archived_path=None)

    service = ProjectPublicationService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        export_visible_project=export,
        accepted_proposals=accepted,
    )

    service.prepare(language="en")
    service.prepare(language="it")

    assert accepted_calls == 1
    assert service.paths(language="en").evidence_index == service.paths(language="it").evidence_index
    manifest = yaml.safe_load(
        service.paths(language="it").manifest.read_text(encoding="utf-8")
    )
    assert manifest["source_state"]["input_count"] == 101
    assert "inputs" not in manifest["source_state"]
    assert service.paths(language="it").manifest.stat().st_size < 8_000


def test_publication_v2_does_not_change_workspace_schema_v3_or_p2p_bytes(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Publication Schema Boundary",
        owner="owner",
        project_domain="software",
        vertical_id="software_project",
    )
    before_status = workspace.workspace_schema_status()
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / ".p2p").rglob("*")
        if path.is_file()
    }

    workspace.prepare_project_publication()

    after_status = workspace.workspace_schema_status()
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / ".p2p").rglob("*")
        if path.is_file()
    }
    assert before_status.state == after_status.state == "current"
    assert before_status.schema is not None and after_status.schema is not None
    assert before_status.schema.current_version == after_status.schema.current_version == 3
    assert after == before

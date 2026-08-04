from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from p2p_engine.core.project_publication import PublicationEdition
from p2p_engine.foundation.files import write_yaml_atomic
from p2p_engine.services.project_publication import ProjectPublicationService
from p2p_engine.services.project_publication_contracts import physical_sha256
from p2p_engine.services.project_publication_rendering import (
    PDF_OPTIONAL_INSTALL_MESSAGE,
    _html_document,
    render_pdf_with_weasyprint,
)
from p2p_engine.services.project_publication_validation import _model_prose_findings


def _write_project_state(root: Path) -> Path:
    p2p_dir = root / ".p2p"
    project_dir = p2p_dir / "project"
    proposal_dir = p2p_dir / "proposals" / "PROP-001-publication"
    project_dir.mkdir(parents=True)
    proposal_dir.mkdir(parents=True)
    (p2p_dir / "project.yml").write_text("project:\n  name: Demo Project\n", encoding="utf-8")
    (project_dir / "definition.yml").write_text(
        "project_definition:\n  objective: Explain the complete project.\n",
        encoding="utf-8",
    )
    (proposal_dir / "proposal.md").write_text(
        "# Publication\n\nThe project provides a human-readable publication.\n",
        encoding="utf-8",
    )
    return proposal_dir


def _service(
    root: Path,
    proposal_dir: Path,
    *,
    pdf_renderer=None,
    transaction_hook=None,
) -> ProjectPublicationService:
    def export():
        output = root / "outputs" / "latest" / "project.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        text = "# Demo Project\n\nA complete visible project export.\n"
        changed = not output.exists() or output.read_text(encoding="utf-8") != text
        output.write_text(text, encoding="utf-8")
        return SimpleNamespace(
            latest_path=Path("outputs/latest/project.md"),
            exports_dir=Path("outputs"),
            archived_path=None,
            changed=changed,
        )

    return ProjectPublicationService(
        root=root,
        p2p_dir=root / ".p2p",
        export_visible_project=export,
        accepted_proposals=lambda: [
            {
                "proposal_id": "PROP-001",
                "path": proposal_dir,
                "status": "accepted",
            }
        ],
        pdf_renderer=pdf_renderer,
        transaction_hook=transaction_hook,
    )


def _manifest(root: Path, edition_key: str = "project-en") -> dict[str, object]:
    return yaml.safe_load(
        (root / "outputs" / "latest" / "publications" / edition_key / "manifest.yml").read_text(
            encoding="utf-8"
        )
    )


def _write_candidates(
    service: ProjectPublicationService,
    *,
    language: str = "en",
    output_name: str = "project",
    markdown: str | None = None,
    mutate_accounting=None,
) -> tuple[Path, Path, Path]:
    paths = service.paths(language=language, output_name=output_name)
    manifest = _manifest(service.root, paths.edition.edition_key)
    packet = manifest["stages"]["curator_packet"]
    evidence = yaml.safe_load(paths.evidence_index.read_text(encoding="utf-8"))
    usable = next(
        item
        for item in evidence["entries"]
        if item["editorial_class"] not in {"process_only", "historical_context"}
    )
    bindings = {
        "curator_packet_sha256": packet["sha256"],
        "evidence_index_sha256": packet["evidence_semantic_sha256"],
        "source_export_sha256": packet["source_sha256"],
        "source_fingerprint_sha256": packet["source_fingerprint_sha256"],
        "profile_sha256": packet["profile_sha256"],
    }
    model: dict[str, object] = {
        "schema_version": 2,
        "edition": paths.edition.to_dict(),
        "bindings": bindings,
        "project": {
            "title": "Demo Project" if language.startswith("en") else "Progetto Demo",
            "thesis": "A complete reader-oriented project description.",
            "vertical_id": (
                evidence["vertical"]["id"]
                if evidence["vertical"]["available"]
                else "generic"
            ),
            **(
                {}
                if evidence["vertical"]["available"]
                else {"vertical_guidance_unavailable_reason": "No active valid vertical was prepared."}
            ),
        },
        "reader_questions": [
            {
                "id": "RQ-001",
                "question": "What is this project?",
                "answered_by": ["CLM-001"],
            }
        ],
        "claims": [
            {
                "id": "CLM-001",
                "statement": "The project produces an autonomous human publication.",
                "evidence_ids": [usable["id"]],
            }
        ],
        "outline": [
            {
                "id": "SEC-001",
                "role": "project_overview",
                "heading": "Project Overview" if language.startswith("en") else "Panoramica del progetto",
                "claim_ids": ["CLM-001"],
            }
        ],
        "vertical_coverage": [
            {
                "section_id": item["id"],
                "disposition": "covered",
                "outline_ids": ["SEC-001"],
            }
            for item in evidence["vertical"]["required_sections"]
        ],
        "editorial_assessment": {
            "rubric_version": "publication-editorial-rubric-v2",
            "results": [
                {"dimension": dimension, "score": 5, "evaluator": "self"}
                for dimension in (
                    "autonomy",
                    "vertical_coherence",
                    "evidence_use",
                    "language_consistency",
                    "structure",
                    "reader_usefulness",
                )
            ],
        },
    }
    profile = yaml.safe_load(paths.profile.read_text(encoding="utf-8"))
    contribution_markdown = ""
    if profile["editorial"]["include_contributions"]:
        model["contributions"] = deepcopy(evidence["contributions"])
        reader_limitation = (
            "Percentages are shares of recorded contributions and do not measure effort, "
            "quality, merit, ownership, code authorship, or intellectual property."
            if language.startswith("en")
            else "Le percentuali rappresentano quote dei contributi registrati e non misurano "
            "impegno, qualita, merito, proprieta, paternita del codice o proprieta intellettuale."
        )
        model["contributions"]["reader_limitation"] = reader_limitation
        model["outline"].append(
            {
                "id": "SEC-CONTRIBUTIONS",
                "role": "contributions",
                "heading": "Contributions" if language.startswith("en") else "Contributi",
                "claim_ids": [],
            }
        )
        rows = "\n".join(
            f"- {row['author']}: {row['percentage']}%"
            for row in evidence["contributions"]["rows"]
        )
        contribution_markdown = (
            ("\n## Contributions\n\n" if language.startswith("en") else "\n## Contributi\n\n")
            + rows
            + "\n\n"
            + reader_limitation
            + "\n"
        )
    paths.candidate_model.parent.mkdir(parents=True, exist_ok=True)
    write_yaml_atomic(paths.candidate_model, model)

    accounting = {
        "schema_version": 2,
        "edition_key": paths.edition.edition_key,
        "bindings": {
            "model_sha256": physical_sha256(paths.candidate_model),
            "evidence_index_sha256": evidence["semantic_sha256"],
        },
        "evidence": [],
    }
    for item in evidence["entries"]:
        if item["id"] == usable["id"]:
            record = {
                "evidence_id": item["id"],
                "disposition": "used",
                "claim_ids": ["CLM-001"],
                "reason": "Supports the project claim.",
            }
        elif item["editorial_class"] == "process_only":
            record = {
                "evidence_id": item["id"],
                "disposition": "process_only",
                "claim_ids": [],
                "reason": "Upstream process metadata.",
            }
        elif item["editorial_class"] == "historical_context":
            record = {
                "evidence_id": item["id"],
                "disposition": "historical",
                "claim_ids": [],
                "reason": "Historical context is not current project substance.",
            }
        elif item["editorial_class"] in {"duplicate", "contradictory", "insufficient"}:
            record = {
                "evidence_id": item["id"],
                "disposition": item["editorial_class"],
                "claim_ids": [],
                "reason": "Evidence is not eligible for a current project claim.",
            }
        else:
            record = {
                "evidence_id": item["id"],
                "disposition": "supporting_context",
                "claim_ids": [],
                "reason": "Considered as supporting context.",
            }
        accounting["evidence"].append(record)
    if mutate_accounting is not None:
        mutate_accounting(accounting)
    write_yaml_atomic(paths.candidate_evidence, accounting)
    paths.candidate_markdown.write_text(
        markdown
        or ((
            "# Demo Project\n\n## Project Overview\n\n"
            "The project produces a standalone publication for its final reader.\n"
            if language.startswith("en")
            else "# Progetto Demo\n\n## Panoramica del progetto\n\nIl progetto produce una pubblicazione autonoma per il lettore finale.\n"
        ) + contribution_markdown),
        encoding="utf-8",
    )
    return paths.candidate_markdown, paths.candidate_model, paths.candidate_evidence


def _prepare_import_validate(
    service: ProjectPublicationService,
    *,
    language: str = "en",
    output_name: str = "project",
    markdown: str | None = None,
):
    service.prepare(language=language, output_name=output_name)
    sources = _write_candidates(
        service,
        language=language,
        output_name=output_name,
        markdown=markdown,
    )
    service.import_curated(
        sources[0],
        model=sources[1],
        evidence_accounting=sources[2],
        language=language,
        output_name=output_name,
    )
    return service.validate(language=language, output_name=output_name)


def _fake_pdf_renderer(markdown: str, output: Path, root: Path, **metadata) -> str:
    assert markdown
    assert metadata["language"]
    assert metadata["title"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"%PDF-1.4\npublication\n")
    return "fake-renderer"


def test_model_outline_prose_matching_accepts_title_as_h1() -> None:
    model = {
        "outline": [
            {"heading": "Demo Project"},
            {"heading": "Project Purpose"},
        ],
        "claims": [],
    }

    findings = _model_prose_findings(
        "# Demo Project\n\n## Project Purpose\n\nReader prose.\n",
        Path("project-en.md"),
        model,
        {},
    )

    assert not any(item.code == "model_outline_prose_mismatch" for item in findings)


def test_model_outline_prose_matching_reports_missing_non_title_heading() -> None:
    model = {
        "outline": [
            {"heading": "Demo Project"},
            {"heading": "Project Purpose"},
        ],
        "claims": [],
    }

    findings = _model_prose_findings(
        "# Demo Project\n\nReader prose.\n",
        Path("project-en.md"),
        model,
        {},
    )

    assert any(item.code == "model_outline_prose_mismatch" for item in findings)


def test_prepare_writes_v2_edition_packet_and_reuses_shared_evidence(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)

    first = service.prepare()
    manifest_bytes = service.paths().manifest.read_bytes()
    evidence_bytes = service.paths().evidence_index.read_bytes()
    second = service.prepare()

    assert first.edition.edition_key == "project-en"
    assert first.exported is True
    assert second.exported is False
    assert service.paths().manifest.read_bytes() == manifest_bytes
    assert service.paths().evidence_index.read_bytes() == evidence_bytes
    assert first.profile_path == Path("outputs/latest/publications/project-en/profile.yml")
    packet = service.paths().curator_input.read_text(encoding="utf-8")
    assert "drafts/project-publication/project-en.model.yml" in packet
    assert "complete visible project export" not in packet.lower()
    assert "## Candidate Binding Contract" in packet
    assert "`curator_packet_sha256`: physical SHA256" in packet
    assert f"`evidence_index_sha256`: `{first.evidence_sha256}`" in packet
    assert "The packet cannot embed its own physical hash" in packet
    assert "do not substitute equivalent-looking keys" in packet


def test_prepare_keeps_english_and_italian_editions_independent(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)

    en = service.prepare(language="eng", output_name="manual")
    it = service.prepare(language="ita", output_name="manual")

    assert en.edition.edition_key == "manual-en"
    assert it.edition.edition_key == "manual-it"
    assert en.manifest_path != it.manifest_path
    assert service.paths(language="en", output_name="manual").manifest.exists()
    assert service.paths(language="it", output_name="manual").manifest.exists()
    assert len(service.list_editions().editions) == 2


def test_prepare_rejects_required_contributions_without_attribution(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)

    with pytest.raises(ValueError, match="no attributed contribution"):
        service.prepare(contributions="include")


def test_contribution_policy_preserves_prepared_figures_and_limitation(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    (proposal / "contributions.yml").write_text(
        "contributions:\n"
        "- id: C-001\n  type: finding\n  author: alice\n  text: First.\n"
        "- id: C-002\n  type: finding\n  author: bob\n  text: Second.\n"
        "- id: C-003\n  type: finding\n  author: alice\n  text: Third.\n",
        encoding="utf-8",
    )
    service = _service(tmp_path, proposal)

    service.prepare(contributions="auto")
    markdown, model, accounting = _write_candidates(service)
    service.import_curated(markdown, model=model, evidence_accounting=accounting)
    result = service.validate()

    assert result.status == "passed"
    text = service.paths().markdown.read_text(encoding="utf-8")
    assert "alice: 66.67%" in text
    assert "bob: 33.33%" in text
    assert "do not measure effort" in text


def test_italian_contribution_limitation_is_localized_and_validated(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    (proposal / "contributions.yml").write_text(
        "contributions:\n- id: C-001\n  type: finding\n  author: alice\n  text: First.\n",
        encoding="utf-8",
    )
    service = _service(tmp_path, proposal)

    service.prepare(language="it", contributions="include")
    markdown, model, accounting = _write_candidates(service, language="it")
    service.import_curated(
        markdown,
        model=model,
        evidence_accounting=accounting,
        language="it",
    )
    result = service.validate(language="it")

    text = service.paths(language="it").markdown.read_text(encoding="utf-8")
    assert result.status == "passed"
    assert "non misurano impegno" in text
    assert "do not measure effort" not in text


def test_contribution_chapter_is_rejected_when_profile_omits_it(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare(contributions="omit")
    markdown, model, accounting = _write_candidates(
        service,
        markdown="# Demo Project\n\n## Contributions\n\n- alice: 100.00%\n",
    )
    service.import_curated(markdown, model=model, evidence_accounting=accounting)

    result = service.validate()

    assert result.status == "failed"
    assert any(finding.code == "contributions_unexpected" for finding in result.findings)


def test_import_requires_complete_exact_accounting(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    markdown, model, accounting = _write_candidates(
        service,
        mutate_accounting=lambda payload: payload["evidence"].pop(),
    )

    with pytest.raises(ValueError, match="incomplete"):
        service.import_curated(markdown, model=model, evidence_accounting=accounting)
    assert not service.paths().markdown.exists()
    assert not service.paths().model.exists()


@pytest.mark.parametrize("failure_event", ["after_replace", "after_manifest_commit"])
def test_import_transaction_rolls_back_injected_failures(
    tmp_path: Path,
    failure_event: str,
) -> None:
    proposal = _write_project_state(tmp_path)
    armed = False

    def fail(event: str, path: Path | None) -> None:
        nonlocal armed
        if event == failure_event and not armed:
            armed = True
            raise RuntimeError(f"injected {failure_event}")

    service = _service(tmp_path, proposal, transaction_hook=fail)
    service.prepare()
    before_manifest = service.paths().manifest.read_bytes()
    markdown, model, accounting = _write_candidates(service)

    with pytest.raises(RuntimeError, match="injected"):
        service.import_curated(markdown, model=model, evidence_accounting=accounting)

    assert service.paths().manifest.read_bytes() == before_manifest
    assert not service.paths().markdown.exists()
    assert not service.paths().model.exists()
    assert not service.paths().evidence_accounting.exists()


def test_same_edition_import_lock_blocks_competing_revision(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    markdown, model, accounting = _write_candidates(service)

    with service._edition_import_lock(service.paths().edition):
        with pytest.raises(ValueError, match="already in progress"):
            service.import_curated(markdown, model=model, evidence_accounting=accounting)

    result = service.import_curated(markdown, model=model, evidence_accounting=accounting)
    assert result.status == "imported"


def test_import_writes_only_current_bound_edition_triplet(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    markdown, model, accounting = _write_candidates(service)

    result = service.import_curated(markdown, model=model, evidence_accounting=accounting)

    assert result.curated_path == Path("outputs/latest/project-en.md")
    assert result.model_path == Path("outputs/latest/publications/project-en/project-model.yml")
    assert result.evidence_accounting_path == Path(
        "outputs/latest/publications/project-en/evidence-accounting.yml"
    )
    stages = {item.name: item for item in service.status().stages}
    assert stages["model"].status == "ready"
    assert stages["evidence_accounting"].status == "ready"
    assert stages["curated"].status == "ready"


def test_byte_equivalent_import_reuses_targets_and_preserves_later_stages(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    markdown, model, accounting = _write_candidates(service)
    service.import_curated(markdown, model=model, evidence_accounting=accounting)
    service.validate()
    service.render()
    targets = (
        service.paths().model,
        service.paths().evidence_accounting,
        service.paths().markdown,
    )
    target_mtimes = {path: path.stat().st_mtime_ns for path in targets}

    result = service.import_curated(markdown, model=model, evidence_accounting=accounting)

    assert result.written_paths == ()
    assert set(result.reused_paths) == {
        Path("outputs/latest/publications/project-en/project-model.yml"),
        Path("outputs/latest/publications/project-en/evidence-accounting.yml"),
        Path("outputs/latest/project-en.md"),
    }
    assert {path: path.stat().st_mtime_ns for path in targets} == target_mtimes
    stages = {item.name: item.status for item in service.status().stages}
    assert stages["validation"] == "ready"
    assert stages["render"] == "ready"


def test_non_default_edition_writes_selected_current_path(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare(language="it")
    markdown, model, accounting = _write_candidates(service, language="it")

    service.import_curated(
        markdown,
        model=model,
        evidence_accounting=accounting,
        language="it",
    )

    assert service.paths(language="it").markdown.exists()


def test_validate_accepts_localized_structure_without_p2p_boilerplate(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)

    result = _prepare_import_validate(service, language="it")

    assert result.status == "passed"
    assert result.edition.language == "it"
    assert not any(finding.code == "source_of_truth_missing" for finding in result.findings)


@pytest.mark.parametrize(
    ("markdown", "code"),
    [
        ("# One\n\n# Two\n", "single_h1_required"),
        ("# Demo Project\n\n## Status\n\nSee PROP-001.\n", "internal_traceability_id"),
        ("# Demo Project\n\n```text\nunclosed\n", "markdown_unclosed_fence"),
    ],
)
def test_validate_reports_deterministic_reader_contract_errors(
    tmp_path: Path,
    markdown: str,
    code: str,
) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)

    result = _prepare_import_validate(service, markdown=markdown)

    assert result.status == "failed"
    assert any(finding.code == code for finding in result.findings)


def test_validate_allows_project_subject_matter_without_internal_ids(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    markdown = (
        "# P2P Engine\n\n## Decision memory\n\n"
        "The product preserves project proposals and their decision lifecycle for its users.\n"
    )

    result = _prepare_import_validate(service, markdown=markdown)

    assert result.status == "passed"
    assert not any(finding.code == "internal_traceability_id" for finding in result.findings)


def test_validate_reports_editorial_heuristics_without_blocking(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    markdown, model, accounting = _write_candidates(
        service,
        markdown=(
            "# Demo Project\n\n"
            "## Overview\n\n"
            "The first proposal was accepted before a later proposal refined the project.\n"
        ),
    )
    service.import_curated(markdown, model=model, evidence_accounting=accounting)

    result = service.validate()

    codes = {finding.code for finding in result.findings}
    assert result.status == "passed"
    assert "probable_governance_narration" in codes
    assert "probable_proposal_chronology" in codes


def test_validate_detects_packet_hash_drift_after_import(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    markdown, model, accounting = _write_candidates(service)
    service.import_curated(markdown, model=model, evidence_accounting=accounting)
    service.paths().curator_input.write_text("changed packet\n", encoding="utf-8")

    result = service.validate()

    assert result.status == "failed"
    assert any(finding.code == "curator_packet_hash_mismatch" for finding in result.findings)


def test_warnings_do_not_block_render(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal, pdf_renderer=_fake_pdf_renderer)
    result = _prepare_import_validate(
        service,
        markdown="# Demo Project\n\n## Project Overview\n\nTODO refine this reader paragraph.\n",
    )

    assert result.status == "passed"
    assert any(finding.code == "placeholder_text" for finding in result.findings)
    rendered = service.render()
    assert rendered.path == Path("outputs/latest/project-en.pdf")


def test_render_and_review_are_bound_to_one_edition(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal, pdf_renderer=_fake_pdf_renderer)
    _prepare_import_validate(service, language="en")
    _prepare_import_validate(service, language="it")

    service.render(language="en")
    review = service.review(status="approved", reviewer="owner", language="en")

    assert review.edition.edition_key == "project-en"
    assert service.status(language="en").approved_for_publication is True
    assert service.status(language="it").approved_for_publication is False
    assert not service.paths(language="it").pdf.exists()


def test_manual_edition_change_stales_validation_render_and_review(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal, pdf_renderer=_fake_pdf_renderer)
    _prepare_import_validate(service)
    service.render()
    service.review(status="approved")

    service.paths().markdown.write_text("# Demo Project\n\nChanged manually.\n", encoding="utf-8")
    status = service.status()
    stages = {item.name: item for item in status.stages}

    assert stages["curated"].status == "stale"
    assert stages["validation"].status == "stale"
    assert stages["render"].status == "stale"
    assert stages["review"].status == "stale"
    assert status.approved_for_publication is False


def test_shared_source_drift_stales_all_editions_but_local_drift_is_isolated(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    _prepare_import_validate(service, language="en")
    _prepare_import_validate(service, language="it")

    service.paths(language="it").markdown.write_text(
        "# Progetto Demo\n\nModifica locale.\n",
        encoding="utf-8",
    )
    assert {item.name: item.status for item in service.status(language="en").stages}["validation"] == "ready"
    assert {item.name: item.status for item in service.status(language="it").stages}["validation"] == "stale"

    proposal.joinpath("proposal.md").write_text("# Changed shared evidence\n", encoding="utf-8")
    assert {item.name: item.status for item in service.status(language="en").stages}["source_export"] == "stale"
    assert {item.name: item.status for item in service.status(language="it").stages}["source_export"] == "stale"


def test_import_rejects_stale_packet_and_unsafe_sources(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    markdown, model, accounting = _write_candidates(service)
    service.paths().curator_input.write_text("changed packet\n", encoding="utf-8")

    with pytest.raises(ValueError, match="stale"):
        service.import_curated(markdown, model=model, evidence_accounting=accounting)

    service.prepare()
    markdown, model, accounting = _write_candidates(service)
    outside = tmp_path.parent / "outside-publication.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="inside the project root"):
            service.import_curated(outside, model=model, evidence_accounting=accounting)
    finally:
        outside.unlink(missing_ok=True)


def test_import_rejects_canonical_and_p2p_sources(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    markdown, model, accounting = _write_candidates(service)
    service.paths().markdown.parent.mkdir(parents=True, exist_ok=True)
    service.paths().markdown.write_text("# Canonical\n", encoding="utf-8")

    with pytest.raises(ValueError, match="candidate draft path"):
        service.import_curated(service.paths().markdown, model=model, evidence_accounting=accounting)
    with pytest.raises(ValueError, match="must not be under .p2p"):
        service.import_curated(proposal / "proposal.md", model=model, evidence_accounting=accounting)


def test_import_rejects_internal_symlink_and_parent_traversal(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    markdown, model, accounting = _write_candidates(service)
    linked = markdown.parent / "linked.md"
    linked.symlink_to(markdown.name)

    with pytest.raises(ValueError, match="must not use symlinks"):
        service.import_curated(linked, model=model, evidence_accounting=accounting)
    with pytest.raises(ValueError, match="parent traversal"):
        service.import_curated(
            Path("drafts/project-publication/../project-publication/project-en.md"),
            model=model,
            evidence_accounting=accounting,
        )


def test_different_editions_can_import_concurrently(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare(language="en", output_name="manual")
    service.prepare(language="it", output_name="manual")
    en = _write_candidates(service, language="en", output_name="manual")
    it = _write_candidates(service, language="it", output_name="manual")

    def run(language: str, candidates: tuple[Path, Path, Path]):
        return service.import_curated(
            candidates[0],
            model=candidates[1],
            evidence_accounting=candidates[2],
            language=language,
            output_name="manual",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda item: run(*item), [("en", en), ("it", it)]))

    assert {result.edition.edition_key for result in results} == {"manual-en", "manual-it"}
    assert service.paths(language="en", output_name="manual").markdown.is_file()
    assert service.paths(language="it", output_name="manual").markdown.is_file()


def test_catalog_read_does_not_rebuild_or_repair_files(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare(language="it", output_name="manual")
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    result = service.list_editions()
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    assert [item.edition.edition_key for item in result.editions] == ["manual-it"]
    assert after == before


def test_future_manifest_is_reported_read_only_and_blocks_writes(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    manifest = yaml.safe_load(service.paths().manifest.read_text(encoding="utf-8"))
    manifest["schema_version"] = 99
    write_yaml_atomic(service.paths().manifest, manifest)
    before = service.paths().manifest.read_bytes()

    status = service.status()
    listed = service.list_editions()

    assert status.validation_status == "invalid"
    assert status.approved_for_publication is False
    assert status.diagnostics[0].code == "publication_manifest_invalid"
    assert listed.editions == ()
    assert listed.diagnostics[0].code == "publication_manifest_version_unsupported"
    assert service.paths().manifest.read_bytes() == before
    with pytest.raises(ValueError, match="Unsupported publication manifest version"):
        service.prepare()


def test_duplicate_manifest_keys_are_reported_without_repair(tmp_path: Path) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    service.paths().manifest.write_text(
        "schema_version: 2\nschema_version: 2\n",
        encoding="utf-8",
    )
    before = service.paths().manifest.read_bytes()

    status = service.status()

    assert status.validation_status == "invalid"
    assert "Duplicate YAML key" in status.diagnostics[0].message
    assert service.paths().manifest.read_bytes() == before


@pytest.mark.parametrize(
    ("mutation", "diagnostic"),
    [
        (lambda payload: payload.update({"pipeline": "other"}), "publication_manifest_pipeline_invalid"),
        (
            lambda payload: payload["edition"].update({"language": "EN"}),
            "publication_edition_not_canonical",
        ),
        (lambda payload: payload.update({"stages": []}), "publication_manifest_stages_invalid"),
    ],
)
def test_catalog_rejects_noncanonical_manifests_without_repair(
    tmp_path: Path,
    mutation,
    diagnostic: str,
) -> None:
    proposal = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal)
    service.prepare()
    manifest = yaml.safe_load(service.paths().manifest.read_text(encoding="utf-8"))
    mutation(manifest)
    write_yaml_atomic(service.paths().manifest, manifest)
    before = service.paths().manifest.read_bytes()

    result = service.list_editions()

    assert result.editions == ()
    assert result.diagnostics[0].code == diagnostic
    assert service.paths().manifest.read_bytes() == before


def test_renderer_html_uses_selected_language_and_escaped_title() -> None:
    html = _html_document("<p>Body</p>", language="it-IT", title="A & B")

    assert '<html lang="it-IT">' in html
    assert "<title>A &amp; B</title>" in html


def test_renderer_reports_optional_dependency_guidance(tmp_path: Path, monkeypatch) -> None:
    import builtins

    original_import = builtins.__import__

    def missing_import(name, *args, **kwargs):
        if name in {"markdown_it", "weasyprint"}:
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_import)
    with pytest.raises(ValueError, match=r"p2p-engine\[pdf\]") as exc_info:
        render_pdf_with_weasyprint("# Demo\n", tmp_path / "project.pdf", tmp_path)
    assert str(exc_info.value) == PDF_OPTIONAL_INSTALL_MESSAGE
    assert not (tmp_path / "project.pdf").exists()


def test_publication_edition_is_immutable_value_identity() -> None:
    edition = PublicationEdition.create(language="EN_us", output_name="manual")

    assert edition.language == "en-US"
    assert edition.path_language == "en-us"
    assert edition.edition_key == "manual-en-us"

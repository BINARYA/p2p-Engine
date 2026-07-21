from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Callable

import yaml

from p2p_engine.foundation.files import write_yaml_atomic
from p2p_engine.services.project_publication_contracts import physical_sha256
from p2p_engine.storage.filesystem import P2PWorkspace


def write_publication_candidates(
    root: Path,
    *,
    language: str = "en",
    output_name: str = "project",
    markdown: str | None = None,
    mutate_accounting: Callable[[dict[str, object]], None] | None = None,
) -> tuple[Path, Path, Path]:
    service = P2PWorkspace(root)._project_publication_service()
    paths = service.paths(language=language, output_name=output_name)
    manifest = yaml.safe_load(paths.manifest.read_text(encoding="utf-8"))
    packet = manifest["stages"]["curator_packet"]
    evidence = yaml.safe_load(paths.evidence_index.read_text(encoding="utf-8"))
    usable = next(
        item
        for item in evidence["entries"]
        if item["editorial_class"] not in {"process_only", "historical_context"}
    )
    model: dict[str, object] = {
        "schema_version": 2,
        "edition": paths.edition.to_dict(),
        "bindings": {
            "curator_packet_sha256": packet["sha256"],
            "evidence_index_sha256": packet["evidence_semantic_sha256"],
            "source_export_sha256": packet["source_sha256"],
            "source_fingerprint_sha256": packet["source_fingerprint_sha256"],
            "profile_sha256": packet["profile_sha256"],
        },
        "project": {
            "title": "Demo Project" if language.startswith("en") else "Progetto Demo",
            "thesis": "A complete project publication.",
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
            {"id": "RQ-001", "question": "What is the project?", "answered_by": ["CLM-001"]}
        ],
        "claims": [
            {
                "id": "CLM-001",
                "statement": "The project has a complete reader publication.",
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
                "section_id": section["id"],
                "disposition": "covered",
                "outline_ids": ["SEC-001"],
            }
            for section in evidence["vertical"]["required_sections"]
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

    accounting: dict[str, object] = {
        "schema_version": 2,
        "edition_key": paths.edition.edition_key,
        "bindings": {
            "model_sha256": physical_sha256(paths.candidate_model),
            "evidence_index_sha256": evidence["semantic_sha256"],
        },
        "evidence": [],
    }
    records = accounting["evidence"]
    assert isinstance(records, list)
    for item in evidence["entries"]:
        if item["id"] == usable["id"]:
            disposition, claim_ids, reason = "used", ["CLM-001"], "Supports the project claim."
        elif item["editorial_class"] == "process_only":
            disposition, claim_ids, reason = "process_only", [], "Upstream process metadata."
        elif item["editorial_class"] == "historical_context":
            disposition, claim_ids, reason = "historical", [], "Historical project context."
        elif item["editorial_class"] in {"duplicate", "contradictory", "insufficient"}:
            disposition, claim_ids, reason = (
                item["editorial_class"],
                [],
                "Evidence is not eligible for a current project claim.",
            )
        else:
            disposition, claim_ids, reason = "supporting_context", [], "Supporting project context."
        records.append(
            {
                "evidence_id": item["id"],
                "disposition": disposition,
                "claim_ids": claim_ids,
                "reason": reason,
            }
        )
    if mutate_accounting is not None:
        mutate_accounting(accounting)
    write_yaml_atomic(paths.candidate_evidence, accounting)
    paths.candidate_markdown.write_text(
        markdown
        or ((
            "# Demo Project\n\n## Project Overview\n\n"
            "The project has a complete publication for its reader.\n"
            if language.startswith("en")
            else "# Progetto Demo\n\n## Panoramica del progetto\n\nIl progetto ha una pubblicazione completa per il lettore.\n"
        ) + contribution_markdown),
        encoding="utf-8",
    )
    return paths.candidate_markdown, paths.candidate_model, paths.candidate_evidence

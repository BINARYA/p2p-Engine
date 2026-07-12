from pathlib import Path

import pytest

from p2p_engine.storage.filesystem import P2PWorkspace


NARRATIVE_ARTIFACTS = (
    "exploration.md",
    "findings.md",
    "alternatives.md",
    "open-questions.md",
    "risks.md",
    "assumptions.md",
    "suggested-scope.md",
)


def test_proposal_artifact_service_generates_prompt_with_context(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal_with_details(
        "Prompt Target",
        problem="The problem is concrete.",
        proposal="Use a dedicated service.",
    )
    service = workspace._proposal_artifact_service()

    path = service.generate_prompt(proposal.proposal_id, "digest")
    content = (tmp_path / path).read_text(encoding="utf-8")

    assert path == Path(".p2p/prompts/PROP-001/digest.prompt.md")
    assert "The problem is concrete." in content
    assert "## Governance Context" in content


def test_proposal_artifact_service_tolerates_missing_narrative_artifacts(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal_with_details(
        "Missing Narrative Target",
        problem="The problem is concrete.",
        proposal="Use structured authoring primitives.",
    )
    proposal_dir = tmp_path / proposal.path
    service = workspace._proposal_artifact_service()

    for filename in NARRATIVE_ARTIFACTS:
        assert not (proposal_dir / filename).exists()

    prompt_path = service.generate_prompt(proposal.proposal_id, "synthesize")
    prompt = (tmp_path / prompt_path).read_text(encoding="utf-8")
    status = service.exploration_status(proposal.proposal_id)
    readiness = workspace.assess_proposal_readiness(proposal.proposal_id)

    assert "The problem is concrete." in prompt
    assert all(not artifact.exists for artifact in status.artifacts)
    assert all(artifact.quality_state == "missing" for artifact in status.artifacts)
    assert readiness.proposal_id == proposal.proposal_id


def test_proposal_artifact_service_reads_legacy_narrative_artifacts(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Legacy Narrative Target")
    proposal_dir = tmp_path / proposal.path
    (proposal_dir / "findings.md").write_text(
        "# Findings\n\nLegacy finding remains readable.\n",
        encoding="utf-8",
    )
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- Which legacy question remains open?\n",
        encoding="utf-8",
    )
    service = workspace._proposal_artifact_service()

    prompt_path = service.generate_prompt(proposal.proposal_id, "synthesize")
    prompt = (tmp_path / prompt_path).read_text(encoding="utf-8")
    status = service.exploration_status(proposal.proposal_id)
    findings = next(artifact for artifact in status.artifacts if artifact.filename == "findings.md")

    assert "Legacy finding remains readable." in prompt
    assert findings.exists is True
    assert findings.has_content is True
    assert status.unresolved_questions == 1


def test_proposal_artifact_service_imports_exploration_file_and_reports_status(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Exploration Target")
    source = tmp_path / "exploration-output.md"
    source.write_text("# Exploration\n\nConcrete output.\n", encoding="utf-8")
    service = workspace._proposal_artifact_service()

    imported = service.import_exploration(proposal.proposal_id, source)
    status = service.exploration_status(proposal.proposal_id)
    exploration = next(artifact for artifact in status.artifacts if artifact.filename == "exploration.md")

    assert imported == [proposal.path / "exploration.md"]
    assert exploration.exists is True
    assert exploration.has_content is True
    assert exploration.quality_state == "thin"
    assert status.suggested_next_command == "p2p explore prompt PROP-001"


def test_proposal_artifact_service_imports_exploration_directory_and_rejects_empty(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Exploration Directory Target")
    source = tmp_path / "exploration"
    source.mkdir()
    (source / "findings.md").write_text("# Findings\n\nMeaningful finding.\n", encoding="utf-8")
    empty = tmp_path / "empty"
    empty.mkdir()
    service = workspace._proposal_artifact_service()

    imported = service.import_exploration(proposal.proposal_id, source)

    assert imported == [proposal.path / "findings.md"]
    with pytest.raises(ValueError, match="No exploration artifacts found"):
        service.import_exploration(proposal.proposal_id, empty)


def test_proposal_artifact_service_imports_generated_artifacts_and_validates_tasks(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Generated Artifact Target")
    clarify = tmp_path / "clarify.md"
    clarify.write_text("# Clarify\n\nQuestion answered.\n", encoding="utf-8")
    tasks = tmp_path / "tasks.yml"
    tasks.write_text("tasks: []\n", encoding="utf-8")
    invalid_tasks = tmp_path / "invalid-tasks.yml"
    invalid_tasks.write_text("not_tasks: []\n", encoding="utf-8")
    service = workspace._proposal_artifact_service()

    clarify_path = service.import_artifact(proposal.proposal_id, "clarify", clarify)
    tasks_path = service.import_artifact(proposal.proposal_id, "tasks", tasks)

    assert clarify_path == proposal.path / "clarifications.md"
    assert tasks_path == proposal.path / "tasks.yml"
    with pytest.raises(ValueError, match="Invalid tasks YAML"):
        service.import_artifact(proposal.proposal_id, "tasks", invalid_tasks)


def test_proposal_artifact_service_imports_impact_artifacts_and_validates_keys(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Impact Target")
    service = workspace._proposal_artifact_service()
    impact = tmp_path / "impact.yml"
    impact.write_text("impact: []\n", encoding="utf-8")
    source_dir = tmp_path / "impact-dir"
    source_dir.mkdir()
    (source_dir / "impact-map.yml").write_text("impact: []\n", encoding="utf-8")
    (source_dir / "related-proposals.yml").write_text("related_proposals: []\n", encoding="utf-8")
    invalid = tmp_path / "invalid-impact.yml"
    invalid.write_text("wrong: []\n", encoding="utf-8")

    file_imported = service.import_impact(proposal.proposal_id, impact)
    dir_imported = service.import_impact(proposal.proposal_id, source_dir)

    assert file_imported == [proposal.path / "impact-map.yml"]
    assert proposal.path / "impact-map.yml" in dir_imported
    assert proposal.path / "related-proposals.yml" in dir_imported
    with pytest.raises(ValueError, match="expected top-level `impact` key"):
        service.import_impact(proposal.proposal_id, invalid)


def test_proposal_artifact_service_import_content_source_mode_matches_cli_targets(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("MCP Source Import Target")
    service = workspace._proposal_artifact_service()
    sources = {
        "explore": ("explore.md", "# Exploration\n\nMCP source output.\n"),
        "impact": ("impact.yml", "impact: []\n"),
        "clarify": ("clarify.md", "# Clarifications\n\nOwner answer.\n"),
        "synthesize": ("proposal.md", "# Proposal\n\nSynthesized body.\n"),
        "plan": ("plan.md", "# Plan\n\nExecution steps.\n"),
        "tasks": ("tasks.yml", "tasks: []\n"),
    }

    results = {}
    for kind, (filename, content) in sources.items():
        source = tmp_path / filename
        source.write_text(content, encoding="utf-8")
        results[kind] = service.import_content(proposal.proposal_id, kind, source=source)

    expected_targets = {
        "explore": "exploration.md",
        "impact": "impact-map.yml",
        "clarify": "clarifications.md",
        "synthesize": "proposal.md",
        "plan": "execution-plan.md",
        "tasks": "tasks.yml",
    }
    for kind, target in expected_targets.items():
        result = results[kind]
        assert result.proposal_id == proposal.proposal_id
        assert result.kind == kind
        assert result.input_mode == "source"
        assert result.imported == [
            result.imported[0].__class__(
                path=proposal.path / target,
                filename=target,
                validated=kind in {"impact", "tasks"},
            )
        ]


def test_proposal_artifact_service_imports_direct_content_payloads(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("MCP Content Import Target")
    service = workspace._proposal_artifact_service()

    cases = {
        "explore": ("exploration.md", "# Exploration\n\nPayload content.\n", False),
        "impact": ("impact-map.yml", "impact: []\n", True),
        "clarify": ("clarifications.md", "# Clarifications\n\nPayload answer.\n", False),
        "synthesize": ("proposal.md", "# Proposal\n\nPayload proposal.\n", False),
        "plan": ("execution-plan.md", "# Plan\n\nPayload plan.\n", False),
        "tasks": ("tasks.yml", "tasks: []\n", True),
    }

    for kind, (target, content, validated) in cases.items():
        result = service.import_content(proposal.proposal_id, kind, content=content)

        assert result.input_mode == "content"
        assert result.imported[0].path == proposal.path / target
        assert result.imported[0].filename == target
        assert result.imported[0].validated is validated
        assert (tmp_path / proposal.path / target).read_text(encoding="utf-8") == content


def test_proposal_artifact_service_imports_direct_artifact_payloads(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("MCP Multi Artifact Target")
    service = workspace._proposal_artifact_service()

    exploration = service.import_content(
        proposal.proposal_id,
        "explore",
        artifacts={
            "findings.md": "# Findings\n\nMCP finding.\n",
            "assumptions.md": "# Assumptions\n\nMCP assumption.\n",
        },
    )
    impact = service.import_content(
        proposal.proposal_id,
        "impact",
        artifacts={
            "impact-map.yml": "impact: []\n",
            "related-proposals.yml": "related_proposals: []\n",
            "conflict-analysis.yml": "conflicts: []\n",
        },
    )

    assert [item.filename for item in exploration.imported] == ["findings.md", "assumptions.md"]
    assert all(item.validated is False for item in exploration.imported)
    assert (tmp_path / proposal.path / "findings.md").read_text(encoding="utf-8") == "# Findings\n\nMCP finding.\n"
    assert [item.filename for item in impact.imported] == [
        "impact-map.yml",
        "related-proposals.yml",
        "conflict-analysis.yml",
    ]
    assert all(item.validated is True for item in impact.imported)


def test_proposal_artifact_service_rejects_invalid_import_requests_without_payload_writes(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("MCP Import Error Target")
    service = workspace._proposal_artifact_service()
    impact_path = tmp_path / proposal.path / "impact-map.yml"
    original_impact = impact_path.read_text(encoding="utf-8") if impact_path.exists() else None

    with pytest.raises(ValueError, match="Provide exactly one"):
        service.import_content(proposal.proposal_id, "explore")
    with pytest.raises(ValueError, match="Provide exactly one"):
        service.import_content(proposal.proposal_id, "explore", source=tmp_path / "missing.md", content="text")
    with pytest.raises(ValueError, match="Unsupported explore artifact filename"):
        service.import_content(proposal.proposal_id, "explore", artifacts={"proposal.md": "# Wrong\n"})
    with pytest.raises(ValueError, match="Artifact payload import is not supported"):
        service.import_content(proposal.proposal_id, "tasks", artifacts={"tasks.yml": "tasks: []\n"})
    with pytest.raises(ValueError, match="expected top-level `impact` key"):
        service.import_content(proposal.proposal_id, "impact", content="wrong: []\n")
    with pytest.raises(ValueError, match="Invalid tasks YAML"):
        service.import_content(proposal.proposal_id, "tasks", content="not_tasks: []\n")
    with pytest.raises(ValueError, match="Impact source not found"):
        service.import_content(proposal.proposal_id, "impact", source=tmp_path / "missing.yml")
    with pytest.raises(ValueError):
        service.import_content("PROP-999", "explore", content="# Missing proposal\n")

    if original_impact is None:
        assert not impact_path.exists()
    else:
        assert impact_path.read_text(encoding="utf-8") == original_impact

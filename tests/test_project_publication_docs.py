from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.project_publication import PublicationEdition, resolve_publication_paths


runner = CliRunner()
ROOT = Path(__file__).resolve().parents[1]


def test_publication_docs_match_resolver_and_cli_help(tmp_path: Path) -> None:
    edition = PublicationEdition.create(language="en", output_name="outputxyz")
    paths = resolve_publication_paths(tmp_path, edition)
    guide = (ROOT / "docs" / "CLI-GUIDE.md").read_text(encoding="utf-8")
    mcp = (ROOT / "docs" / "MCP.md").read_text(encoding="utf-8")
    prepare_help = runner.invoke(app, ["project", "publish", "prepare", "--help"])
    import_help = runner.invoke(app, ["project", "publish", "import", "--help"])

    assert prepare_help.exit_code == 0
    assert import_help.exit_code == 0
    assert "--language" in prepare_help.output
    assert "--output-name" in prepare_help.output
    assert "--contributions" in prepare_help.output
    assert "--model" in import_help.output
    assert "--evidence-accounting" in import_help.output
    assert paths.markdown.relative_to(tmp_path).as_posix() == "outputs/latest/outputxyz-en.md"
    assert "outputs/latest/<edition-key>.md" in guide
    assert "drafts/project-publication/project-en.model.yml" in guide
    assert "`p2p_project_publish_list`" in mcp


def test_publication_docs_do_not_present_v1_paths_as_v2_authority() -> None:
    guide = (ROOT / "docs" / "CLI-GUIDE.md").read_text(encoding="utf-8")
    publication_section = guide.split("## 10. Publish Human Project Editions", 1)[1].split(
        "## 11.",
        1,
    )[0]

    assert "writes `outputs/latest/publication-profile.yml`" not in publication_section
    assert "copies that draft to `outputs/latest/project.curated.md`" not in publication_section
    assert "missing executive summary" not in publication_section.lower()
    assert "aliases are not v2 freshness inputs" in publication_section

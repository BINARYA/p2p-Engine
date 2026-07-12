from __future__ import annotations

from pathlib import Path

from p2p_engine.services.gitignore_hygiene import apply_gitignore_hygiene


def test_gitignore_hygiene_creates_safe_section_when_file_is_missing(tmp_path: Path) -> None:
    result = apply_gitignore_hygiene(tmp_path)

    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert result.status == "applied"
    assert result.path == Path(".gitignore")
    assert ".venv/" in result.added_patterns
    assert ".p2p/" not in content
    assert "# --- P2P local development artifacts ---" in content
    assert "__pycache__/" in content
    assert "*.py[cod]" in content


def test_gitignore_hygiene_appends_without_overwriting_existing_content(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    original = "# user section\ncustom.log\n"
    gitignore.write_text(original, encoding="utf-8")

    result = apply_gitignore_hygiene(tmp_path)

    content = gitignore.read_text(encoding="utf-8")
    assert result.status == "applied"
    assert content.startswith(original)
    assert "custom.log" in content
    assert ".venv/" in content


def test_gitignore_hygiene_is_idempotent(tmp_path: Path) -> None:
    first = apply_gitignore_hygiene(tmp_path)
    second = apply_gitignore_hygiene(tmp_path)

    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert first.status == "applied"
    assert second.status == "already_covered"
    assert content.count(".venv/") == 1
    assert content.count("# --- P2P local development artifacts ---") == 1


def test_gitignore_hygiene_recognizes_exact_equivalent_patterns(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(
        "\n".join(
            [
                ".venv",
                "__pycache__",
                "*.py[cod]",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "build",
                "dist",
                "*.egg-info",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = apply_gitignore_hygiene(tmp_path)

    assert result.status == "already_covered"
    assert result.added_patterns == []


def test_gitignore_hygiene_warns_without_mutating_when_p2p_is_explicitly_ignored(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    original = ".p2p/\n"
    gitignore.write_text(original, encoding="utf-8")

    result = apply_gitignore_hygiene(tmp_path)

    assert result.status == "warning_only"
    assert result.added_patterns == []
    assert result.warnings
    assert ".p2p/" in result.warnings[0]
    assert gitignore.read_text(encoding="utf-8") == original


def test_gitignore_hygiene_warns_for_detectable_broad_dotfile_ignore(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    original = ".*\n"
    gitignore.write_text(original, encoding="utf-8")

    result = apply_gitignore_hygiene(tmp_path)

    assert result.status == "warning_only"
    assert result.warnings
    assert "dotfile" in result.warnings[0]
    assert gitignore.read_text(encoding="utf-8") == original

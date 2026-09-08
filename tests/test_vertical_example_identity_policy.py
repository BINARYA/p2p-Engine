from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from p2p_engine.core.vertical_registry import (
    VerticalCatalogItem,
    VerticalRelease,
    VerticalReleaseArtifact,
    VerticalUserPaths,
)
from p2p_engine.services.project_verticals import (
    ProjectVerticalService,
    _overlay_pack,
    vertical_semantic_identity_v1,
)
from p2p_engine.services.vertical_catalog import (
    VerticalCacheService,
    VerticalCatalogService,
)
from p2p_engine.services.vertical_draft_materializer import (
    VerticalDraftMaterializer,
)
from p2p_engine.services.vertical_drafts import VerticalDraftService
from p2p_engine.services.vertical_packages import PortableVerticalPackageService
from p2p_engine.storage.filesystem import P2PWorkspace

FIXTURE = Path(__file__).parent / "fixtures" / "vertical_examples" / "v1"
V067_GOLDEN = (
    Path(__file__).parent
    / "fixtures"
    / "vertical_semantic_checksum"
    / "v1"
)


def _services(root: Path) -> tuple[ProjectVerticalService, PortableVerticalPackageService]:
    verticals = ProjectVerticalService(
        root=root,
        p2p_dir=root / ".p2p",
        proposal_summaries=lambda: [],
        find_proposal_dir=lambda value: root / value,
    )
    packages = PortableVerticalPackageService(
        root=root,
        p2p_dir=root / ".p2p",
        vertical_service=verticals,
    )
    return verticals, packages


def _variant(
    root: Path,
    case: str,
    *,
    example_path: str = "guide.md",
    content: str | None = None,
    version: str = "1.0.0",
):
    source = root / case
    shutil.copytree(FIXTURE, source)
    original = source / "examples" / "guide.md"
    example_content = (
        original.read_text(encoding="utf-8") if content is None else content
    )
    original.unlink()
    target = source / "examples" / example_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(example_content, encoding="utf-8", newline="")
    vertical_path = source / "vertical.yml"
    vertical = yaml.safe_load(vertical_path.read_text(encoding="utf-8"))
    vertical["vertical"]["version"] = version
    vertical["vertical"]["examples"] = [example_path]
    vertical_path.write_text(
        yaml.safe_dump(vertical, sort_keys=False), encoding="utf-8"
    )
    manifest_path = source / "manifest.yml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest"]["version"] = version
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    _verticals, packages = _services(root)
    return packages.package(source, output=root / f"{case}.p2pv")


def _release(result, *, registry: str = "local") -> VerticalRelease:
    return VerticalRelease(
        coordinate=result.coordinate,
        name="Documentary Examples",
        description="Example identity fixture",
        visibility="private",
        semantic_checksum=result.semantic_checksum,
        semantic_identity=result.semantic_identity,
        schema_version=3,
        artifact=VerticalReleaseArtifact(
            url=result.path.name,
            sha256=result.artifact_checksum,
            size=result.size,
        ),
        registry=registry,
    )


def test_example_path_and_content_have_distinct_v1_and_artifact_effects(
    tmp_path: Path,
) -> None:
    baseline = _variant(tmp_path, "baseline")
    same = _variant(tmp_path, "same")
    content_only = _variant(
        tmp_path,
        "content-only",
        content="Different documentary prose.\n",
    )
    path_only = _variant(tmp_path, "path-only", example_path="renamed.md")
    path_and_content = _variant(
        tmp_path,
        "path-and-content",
        example_path="renamed.md",
        content="Different documentary prose.\n",
    )

    assert same.semantic_identity == baseline.semantic_identity
    assert same.artifact_checksum == baseline.artifact_checksum
    assert content_only.semantic_identity == baseline.semantic_identity
    assert content_only.artifact_checksum != baseline.artifact_checksum
    assert path_only.semantic_identity != baseline.semantic_identity
    assert path_only.artifact_checksum != baseline.artifact_checksum
    assert path_and_content.semantic_identity == path_only.semantic_identity
    assert path_and_content.artifact_checksum != path_only.artifact_checksum


def test_example_line_endings_are_canonicalized_before_artifact_identity(
    tmp_path: Path,
) -> None:
    lf = _variant(tmp_path, "lf", content="Line one\nLine two\n")
    crlf = _variant(tmp_path, "crlf", content="Line one\r\nLine two\r\n")

    assert crlf.semantic_identity == lf.semantic_identity
    assert crlf.artifact_checksum == lf.artifact_checksum


def test_issue_9_does_not_replace_or_change_the_v067_golden_oracle() -> None:
    expected = json.loads((V067_GOLDEN / "expected.json").read_text(encoding="utf-8"))
    verticals, _packages = _services(V067_GOLDEN)
    pack = verticals.load_explicit_pack(V067_GOLDEN / "input")

    assert expected["baseline"]["version"] == "0.6.7"
    assert vertical_semantic_identity_v1(pack).digest == expected["expected_sha256"]
    assert expected["expected_sha256"] == (
        "b78ad848e0130eb9825b832608ab845a887e16fe331b3a02443bd2bf48b73f74"
    )


def test_same_coordinate_rejects_changed_example_artifact_even_with_equal_v1(
    tmp_path: Path,
) -> None:
    first = _variant(tmp_path, "first")
    changed = _variant(tmp_path, "changed", content="Corrected documentation.\n")
    assert changed.semantic_identity == first.semantic_identity
    cache = VerticalCacheService(
        paths=VerticalUserPaths(tmp_path / "data", tmp_path / "cache")
    )

    status, cached = cache.add_local(_release(first), first.path)

    assert status == "added"
    assert cached.artifact_path.name == f"{first.artifact_checksum}.p2pv"
    with pytest.raises(ValueError, match="P2P_REGISTRY_IMMUTABILITY_VIOLATION"):
        cache.add_local(_release(changed), changed.path)


def test_patch_coordinate_is_distinct_and_version_itself_changes_v1(
    tmp_path: Path,
) -> None:
    original = _variant(tmp_path, "original")
    patch = _variant(
        tmp_path,
        "patch",
        content="Corrected documentation.\n",
        version="1.0.1",
    )
    cache = VerticalCacheService(
        paths=VerticalUserPaths(tmp_path / "data", tmp_path / "cache")
    )

    cache.add_local(_release(original), original.path)
    cache.add_local(_release(patch), patch.path)
    catalog = VerticalCatalogService(tmp_path / "project", cache=cache)

    assert patch.coordinate.endswith("@1.0.1")
    assert patch.semantic_identity != original.semantic_identity
    assert patch.artifact_checksum != original.artifact_checksum
    assert {
        original.coordinate,
        patch.coordinate,
    }.issubset({item.coordinate for item in catalog.local_items()})


def test_draft_materialization_preserves_documentary_content_without_hashing_it(
    tmp_path: Path,
) -> None:
    verticals, _packages = _services(tmp_path)
    source = tmp_path / "source"
    shutil.copytree(FIXTURE, source)
    pack = verticals.load_explicit_pack(source)
    original_content = (source / "examples" / "guide.md").read_text(encoding="utf-8")
    document = VerticalDraftService.document_from_pack(
        pack,
        examples=[{"path": "guide.md", "content": original_content}],
    )
    workspace = P2PWorkspace(tmp_path / "project")
    materializer = VerticalDraftMaterializer(workspace)

    first = materializer.materialize(document, tmp_path / "materialized-first")
    changed_document = {
        **document,
        "examples": [{"path": "guide.md", "content": "Revised documentary prose.\n"}],
    }
    second = materializer.materialize(
        changed_document, tmp_path / "materialized-second"
    )
    roundtrip = materializer.normalized_from_materialized(
        workspace, tmp_path / "materialized-second"
    )
    _verticals, packages = _services(tmp_path)
    first_package = packages.package(
        tmp_path / "materialized-first", output=tmp_path / "first.p2pv"
    )
    second_package = packages.package(
        tmp_path / "materialized-second", output=tmp_path / "second.p2pv"
    )

    assert first.semantic_identity == second.semantic_identity
    assert roundtrip["examples"] == changed_document["examples"]
    assert first_package.semantic_identity == second_package.semantic_identity
    assert first_package.artifact_checksum != second_package.artifact_checksum


def test_draft_clone_preserves_local_example_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    shutil.copytree(FIXTURE, source)
    verticals, _packages = _services(tmp_path)
    pack = verticals.load_explicit_pack(source)
    semantic_identity = vertical_semantic_identity_v1(pack)
    drafts = VerticalDraftService(
        tmp_path / "project",
        draft_root=tmp_path / "drafts",
        id_factory=lambda: "VDRAFT-1234567890ABCDEF",
    )
    item = VerticalCatalogItem(
        coordinate=pack.coordinate,
        name=pack.name,
        source="bundled",
        semantic_checksum=semantic_identity.digest,
        semantic_identity=semantic_identity,
    )
    monkeypatch.setattr(drafts.catalog, "resolve", lambda _coordinate: item)
    monkeypatch.setattr(
        drafts.catalog.workspace,
        "show_project_vertical",
        lambda _coordinate: pack,
    )

    created = drafts.create_from(pack.coordinate)

    assert created.draft.state.document["examples"] == [
        {
            "path": "guide.md",
            "content": (source / "examples" / "guide.md").read_text(
                encoding="utf-8"
            ),
        }
    ]


def test_inherited_example_content_recovers_effective_child_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_root = tmp_path / "base"
    child_root = tmp_path / "child"
    shutil.copytree(FIXTURE, base_root)
    shutil.copytree(FIXTURE, child_root)
    (base_root / "examples" / "guide.md").write_text(
        "Base documentation.\n", encoding="utf-8"
    )
    (child_root / "examples" / "guide.md").write_text(
        "Child override.\n", encoding="utf-8"
    )
    verticals, _packages = _services(tmp_path)
    base = verticals.load_explicit_pack(base_root)
    loaded_child = verticals.load_explicit_pack(child_root)
    assert loaded_child.manifest is not None
    child = replace(
        loaded_child,
        vertical_id="documentary_examples_child",
        version="1.0.1",
        extends=base.coordinate,
        manifest=replace(
            loaded_child.manifest,
            vertical_id="documentary_examples_child",
            version="1.0.1",
        ),
    )
    effective = _overlay_pack(base, child)
    drafts = VerticalDraftService(tmp_path / "project")
    monkeypatch.setattr(
        drafts.catalog.workspace,
        "show_project_vertical",
        lambda reference: base if reference == base.coordinate else None,
    )

    examples = drafts._pack_examples(child)

    assert effective.examples == ["guide.md"]
    assert examples == [{"path": "guide.md", "content": "Child override.\n"}]

from __future__ import annotations

from pathlib import Path, PurePosixPath
import shutil
import tempfile

from p2p_engine.core.portable_verticals import PortableVerticalInspection, VerticalCoordinate
from p2p_engine.foundation.files import write_yaml_atomic
from p2p_engine.services.vertical_drafts import (
    VerticalDraftService,
    document_diagnostics,
    normalize_vertical_draft_document,
)
from p2p_engine.storage.filesystem import P2PWorkspace


class VerticalDraftMaterializer:
    def __init__(self, workspace: P2PWorkspace) -> None:
        self.workspace = workspace

    def materialize(
        self,
        document: dict[str, object],
        target: Path,
    ) -> PortableVerticalInspection:
        normalized = normalize_vertical_draft_document(document)
        diagnostics = document_diagnostics(
            normalized,
            origin=self._materialization_origin(),
        )
        blockers = [item for item in diagnostics if item.severity == "error"]
        if blockers:
            first = blockers[0]
            raise ValueError(f"{first.code}: {first.field}: {first.message}")
        target = target if target.is_absolute() else self.workspace.root / target
        if target.is_symlink():
            raise ValueError("P2P_VERTICAL_DRAFT_TARGET_NOT_EMPTY: linked target is unsafe")
        if target.exists() and (not target.is_dir() or any(target.iterdir())):
            raise ValueError(
                f"P2P_VERTICAL_DRAFT_TARGET_NOT_EMPTY: target must be absent or empty: {target}"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        candidate = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.draft-", dir=target.parent)
        )
        try:
            self._write_document(normalized, candidate)
            inspection = self.workspace.inspect_portable_vertical(candidate, view="declared")
            expected_coordinate = _document_coordinate(normalized)
            if inspection.pack.coordinate != expected_coordinate:
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_ROUNDTRIP_MISMATCH: materialized coordinate changed"
                )
            roundtrip = VerticalDraftService.document_from_pack(
                inspection.pack,
                examples=_read_examples(candidate),
            )
            if vertical_draft_roundtrip_shape(roundtrip) != vertical_draft_roundtrip_shape(
                normalized
            ):
                raise ValueError(
                    "P2P_VERTICAL_DRAFT_ROUNDTRIP_MISMATCH: canonical pack changed normalized content"
                )
            if target.exists():
                target.rmdir()
            candidate.replace(target)
            return self.workspace.inspect_portable_vertical(target, view="declared")
        finally:
            shutil.rmtree(candidate, ignore_errors=True)

    @staticmethod
    def normalized_from_materialized(
        workspace: P2PWorkspace,
        target: Path,
    ) -> dict[str, object]:
        target = target if target.is_absolute() else workspace.root / target
        inspection = workspace.inspect_portable_vertical(target, view="declared")
        return VerticalDraftService.document_from_pack(
            inspection.pack,
            examples=_read_examples(target),
        )

    @staticmethod
    def _write_document(document: dict[str, object], root: Path) -> None:
        identity = document["identity"]
        extends = document.get("extends")
        lineage = document["lineage"]
        dependencies = document["dependencies"]
        profiles = document["profiles"]
        modules = document["modules"]
        domain_metadata = document.get("domain_metadata", {})
        manifest = {
            "manifest": {
                "schema_version": 3,
                "publisher": identity["publisher"],
                "id": identity["id"],
                "name": document["name"],
                "version": identity["version"],
                "license": identity["license"],
                "source": "draft",
                "extends": extends["coordinate"] if extends else None,
                "lineage": {
                    field: reference["coordinate"]
                    for field, reference in lineage.items()
                    if reference
                },
                "dependencies": [
                    {
                        "coordinate": item["coordinate"],
                        "checksum": f"sha256:{item['semantic_checksum']}",
                    }
                    for item in dependencies
                ],
                "compatibility": document["compatibility"],
                "primary_domain": domain_metadata.get("primary_domain"),
                "domain_tags": domain_metadata.get("domain_tags", []),
            }
        }
        vertical = {
            "vertical": {
                "schema_version": 3,
                "id": identity["id"],
                "name": document["name"],
                "version": identity["version"],
                "description": document["description"],
                "extends": extends["coordinate"] if extends else None,
                "questions": document["questions"],
                "artifacts": document["artifacts"],
                "profiles": profiles["enabled"],
                "modules": modules["enabled"],
                "examples": [item["path"] for item in document["examples"]],
            }
        }
        write_yaml_atomic(root / "manifest.yml", manifest)
        write_yaml_atomic(root / "vertical.yml", vertical)
        sections = document["sections"]
        for index, section in enumerate(sections):
            section_id = _safe_id(section.get("id"), f"sections[{index}].id")
            write_yaml_atomic(
                root / "sections" / f"{index + 1:03d}-{section_id}.yml",
                {"section": section},
            )
        write_yaml_atomic(root / "rubrics.yml", {"rubrics": document["rubrics"]})
        for index, profile in enumerate(profiles["definitions"]):
            profile_id = _safe_id(profile.get("id"), f"profiles.definitions[{index}].id")
            write_yaml_atomic(
                root / "profiles" / f"{index + 1:03d}-{profile_id}.yml",
                {"profile": profile},
            )
        for index, module in enumerate(modules["definitions"]):
            module_id = _safe_id(module.get("id"), f"modules.definitions[{index}].id")
            write_yaml_atomic(
                root / "modules" / f"{index + 1:03d}-{module_id}.yml",
                {"module": module},
            )
        for index, example in enumerate(document["examples"]):
            relative = _safe_example_path(example.get("path"), index)
            path = root / "examples" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(example.get("content") or ""), encoding="utf-8")

    @staticmethod
    def _materialization_origin():
        from p2p_engine.core.vertical_drafts import VerticalDraftOrigin

        return VerticalDraftOrigin(kind="materialization")


def _document_coordinate(document: dict[str, object]) -> str:
    identity = document["identity"]
    return str(
        VerticalCoordinate.parse(
            f"{identity['publisher']}/{identity['id']}@{identity['version']}"
        )
    )


def _safe_id(value: object, field: str) -> str:
    text = str(value or "")
    if not text or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for character in text):
        raise ValueError(f"P2P_VERTICAL_DRAFT_INVALID_ID: unsafe {field}")
    return text


def _safe_example_path(value: object, index: int) -> Path:
    text = str(value or "")
    pure = PurePosixPath(text)
    if (
        not text
        or pure.is_absolute()
        or ".." in pure.parts
        or any(part in {"", "."} or part.startswith(".") for part in pure.parts)
        or pure.suffix.lower() not in {".md", ".json", ".yml", ".yaml"}
    ):
        raise ValueError(
            f"P2P_VERTICAL_DRAFT_INVALID_EXAMPLE: examples[{index}].path is unsafe"
        )
    return Path(*pure.parts)


def _read_examples(root: Path) -> list[dict[str, str]]:
    examples_root = root / "examples"
    if not examples_root.exists():
        return []
    return [
        {
            "path": path.relative_to(examples_root).as_posix(),
            "content": path.read_text(encoding="utf-8"),
        }
        for path in sorted(examples_root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]


def vertical_draft_roundtrip_shape(document: dict[str, object]) -> dict[str, object]:
    normalized = normalize_vertical_draft_document(document)
    result = dict(normalized)
    result["visibility"] = "private"
    result["source_attribution"] = {}
    lineage = dict(result["lineage"])
    for field, reference in lineage.items():
        if isinstance(reference, dict):
            lineage[field] = {**reference, "semantic_checksum": ""}
    result["lineage"] = lineage
    sections: list[dict[str, object]] = []
    for raw_section in result["sections"]:
        section = dict(raw_section)
        policy = section.get("completion_policy")
        if policy == {"allow_assumed_completion": False, "required_fields": []}:
            section["completion_policy"] = {}
        sections.append(section)
    result["sections"] = sections
    return result

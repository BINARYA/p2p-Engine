from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile

import yaml

from p2p_engine.core.portable_verticals import (
    PORTABLE_VERTICAL_MAX_COMPRESSION_RATIO,
    PORTABLE_VERTICAL_MAX_ENTRIES,
    PORTABLE_VERTICAL_MAX_FILE_BYTES,
    PORTABLE_VERTICAL_MAX_TOTAL_BYTES,
    PORTABLE_VERTICAL_PACKAGE_VERSION,
    PORTABLE_VERTICAL_SCHEMA_VERSION,
    PortableVerticalInspection,
    PortableVerticalPackageResult,
    VerticalCoordinate,
)
from p2p_engine.core.project_verticals import VerticalPack, VerticalValidationIssue
from p2p_engine.foundation.files import write_yaml_atomic, yaml_dump
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.project_verticals import ProjectVerticalService


_ROOT_FILES = {"manifest.yml", "vertical.yml", "rubrics.yml"}
_CONTENT_DIRS = {"sections", "profiles", "modules", "artifacts", "examples"}
_ALLOWED_SUFFIXES = {".yml", ".yaml", ".json", ".md"}


class PortableVerticalPackageService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        vertical_service: ProjectVerticalService,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.vertical_service = vertical_service

    @staticmethod
    def authoring_schema() -> dict[str, object]:
        return {
            "schema_version": PORTABLE_VERTICAL_SCHEMA_VERSION,
            "package_version": PORTABLE_VERTICAL_PACKAGE_VERSION,
            "coordinate": "publisher/vertical-id@MAJOR.MINOR.PATCH",
            "required_files": sorted(_ROOT_FILES),
            "required_globs": ["sections/*.yml"],
            "optional_directories": sorted(_CONTENT_DIRS - {"sections"}),
            "allowed_suffixes": sorted(_ALLOWED_SUFFIXES),
            "limits": {
                "max_entries": PORTABLE_VERTICAL_MAX_ENTRIES,
                "max_file_bytes": PORTABLE_VERTICAL_MAX_FILE_BYTES,
                "max_total_bytes": PORTABLE_VERTICAL_MAX_TOTAL_BYTES,
                "max_compression_ratio": PORTABLE_VERTICAL_MAX_COMPRESSION_RATIO,
            },
            "network_access": False,
            "executable_content": False,
        }

    def scaffold(
        self,
        target: Path,
        *,
        publisher: str,
        vertical_id: str,
        version: str,
        name: str,
        license_id: str,
        extends: str = "",
    ) -> PortableVerticalInspection:
        coordinate = VerticalCoordinate.parse(f"{publisher}/{vertical_id}@{version}")
        target = target if target.is_absolute() else self.root / target
        if target.exists():
            raise ValueError(f"P2P_VERTICAL_TARGET_EXISTS: scaffold target already exists: {target}")
        dependencies: list[dict[str, str]] = []
        if extends:
            base_reference = str(VerticalCoordinate.parse(extends))
            base = self.vertical_service.resolve_pack(base_reference)
            dependencies.append(
                {
                    "coordinate": base_reference,
                    "checksum": f"sha256:{base.checksum}",
                }
            )
        manifest = {
            "manifest": {
                "schema_version": PORTABLE_VERTICAL_SCHEMA_VERSION,
                "publisher": coordinate.publisher,
                "id": coordinate.vertical_id,
                "name": name or coordinate.vertical_id.replace("_", " ").title(),
                "version": coordinate.version,
                "license": license_id,
                "extends": extends or None,
                "lineage": {},
                "dependencies": dependencies,
                "compatibility": {},
            }
        }
        vertical = {
            "vertical": {
                "schema_version": PORTABLE_VERTICAL_SCHEMA_VERSION,
                "id": coordinate.vertical_id,
                "name": name or coordinate.vertical_id.replace("_", " ").title(),
                "version": coordinate.version,
                "description": "Describe the project vertical.",
                "extends": extends or None,
                "questions": [
                    {
                        "id": "custom_overview_question",
                        "section_id": "custom_overview",
                        "priority": "high",
                        "question": "What must this project vertical define?",
                    }
                ],
                "artifacts": [
                    {
                        "id": "custom_overview_artifact",
                        "title": "Project vertical overview",
                        "section_ids": ["custom_overview"],
                        "required": True,
                    }
                ],
            }
        }
        section = {
            "section": {
                "id": "custom_overview",
                "title": "Custom Overview",
                "purpose": "Define the information governed by this vertical.",
                "required": True,
                "priority": 10,
                "fields": [
                    {
                        "id": "summary",
                        "label": "Summary",
                        "required": True,
                        "question": "What must be defined?",
                    }
                ],
            }
        }
        rubrics = {
            "rubrics": [
                {
                    "id": "custom_overview_coverage",
                    "title": "Custom overview coverage",
                    "section_id": "custom_overview",
                    "required": True,
                    "keywords": ["overview"],
                }
            ]
        }
        (target / "sections").mkdir(parents=True)
        write_yaml_atomic(target / "manifest.yml", manifest)
        write_yaml_atomic(target / "vertical.yml", vertical)
        write_yaml_atomic(target / "sections" / "custom_overview.yml", section)
        write_yaml_atomic(target / "rubrics.yml", rubrics)
        return self.inspect(target, view="declared")

    def inspect(self, target: Path, *, view: str = "effective") -> PortableVerticalInspection:
        if view not in {"declared", "effective"}:
            raise ValueError("P2P_VERTICAL_INVALID_VIEW: view must be declared or effective")
        target = target if target.is_absolute() else self.root / target
        artifact_checksum = ""
        entries: dict[str, bytes]
        if target.is_file():
            archive_bytes = target.read_bytes()
            artifact_checksum = hashlib.sha256(archive_bytes).hexdigest()
            entries = self.read_archive(target)
            if archive_bytes != self.archive_bytes(entries):
                raise ValueError(
                    "P2P_VERTICAL_NON_CANONICAL_ARTIFACT: archive metadata or content is not deterministic"
                )
        elif target.is_dir():
            entries = self.canonical_entries(target)
        else:
            raise ValueError(f"P2P_VERTICAL_NOT_FOUND: {target}")
        with tempfile.TemporaryDirectory(prefix="p2p-vertical-inspect-") as temporary:
            pack_root = Path(temporary)
            self._materialize_entries(pack_root, entries)
            declared = self.vertical_service.load_explicit_pack(pack_root)
            effective = self.vertical_service.compose_explicit_pack(pack_root)
        selected = declared if view == "declared" else effective
        return PortableVerticalInspection(
            target=str(target),
            pack=selected,
            declared_payload=self.vertical_service.serialized_pack(declared),
            effective_payload=self.vertical_service.serialized_pack(effective),
            artifact_checksum=artifact_checksum,
            semantic_checksum=self.vertical_service.semantic_pack_checksum(effective),
            entries=tuple(sorted(entries)),
        )

    def validate(self, target: Path) -> PortableVerticalInspection:
        try:
            return self.inspect(target, view="effective")
        except ValueError as exc:
            return PortableVerticalInspection(
                target=str(target),
                pack=_invalid_pack(),
                declared_payload={},
                effective_payload={},
                issues=(
                    VerticalValidationIssue(
                        severity="error",
                        field="package",
                        message=str(exc),
                        code=_error_code(str(exc)),
                    ),
                ),
            )

    def package(self, source: Path, *, output: Path) -> PortableVerticalPackageResult:
        source = source if source.is_absolute() else self.root / source
        inspection = self.inspect(source, view="effective")
        if inspection.pack.schema_version != PORTABLE_VERTICAL_SCHEMA_VERSION or not inspection.pack.coordinate:
            raise ValueError("P2P_VERTICAL_PORTABLE_V3_REQUIRED: only schema-version-3 packs can be packaged")
        entries = self.canonical_entries(source)
        output = output if output.is_absolute() else self.root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        package_bytes = self.archive_bytes(entries)
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=f".{output.name}.", delete=False) as handle:
            temporary = Path(handle.name)
        try:
            temporary.write_bytes(package_bytes)
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
        return PortableVerticalPackageResult(
            path=output,
            coordinate=inspection.pack.coordinate,
            artifact_checksum=hashlib.sha256(package_bytes).hexdigest(),
            semantic_checksum=inspection.semantic_checksum,
            size=len(package_bytes),
            entries=tuple(sorted(entries)),
        )

    @staticmethod
    def archive_bytes(entries: dict[str, bytes]) -> bytes:
        import io

        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in sorted(entries):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, entries[name])
        return output.getvalue()

    def canonical_entries(self, source: Path) -> dict[str, bytes]:
        source = source.resolve()
        if not source.is_dir() or source.is_symlink():
            raise ValueError("P2P_VERTICAL_UNSAFE_ARTIFACT: package source must be a regular directory")
        entries: dict[str, bytes] = {}
        for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
            if path.is_dir():
                if path.is_symlink():
                    raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: linked directory `{path}`")
                continue
            relative = path.relative_to(source).as_posix()
            self._validate_entry_name(relative)
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: non-regular entry `{relative}`")
            if path.stat().st_mode & 0o111:
                raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: executable entry `{relative}`")
            entries[relative] = self._canonical_content(relative, path.read_bytes())
        self._validate_entry_set(entries)
        return entries

    def read_archive(self, source: Path) -> dict[str, bytes]:
        entries: dict[str, bytes] = {}
        total = 0
        try:
            archive = zipfile.ZipFile(source, "r")
        except (OSError, zipfile.BadZipFile) as exc:
            raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: invalid ZIP archive: {exc}") from exc
        with archive:
            infos = archive.infolist()
            if len(infos) > PORTABLE_VERTICAL_MAX_ENTRIES:
                raise ValueError("P2P_VERTICAL_PACKAGE_LIMIT: too many archive entries")
            seen: set[str] = set()
            for info in infos:
                name = info.filename
                self._validate_entry_name(name)
                if name in seen:
                    raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: duplicate entry `{name}`")
                seen.add(name)
                mode = info.external_attr >> 16
                if info.is_dir() or stat.S_ISLNK(mode) or (mode & 0o111):
                    raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: unsafe entry mode `{name}`")
                if info.file_size > PORTABLE_VERTICAL_MAX_FILE_BYTES:
                    raise ValueError(f"P2P_VERTICAL_PACKAGE_LIMIT: entry too large `{name}`")
                total += info.file_size
                if total > PORTABLE_VERTICAL_MAX_TOTAL_BYTES:
                    raise ValueError("P2P_VERTICAL_PACKAGE_LIMIT: archive is too large")
                if info.compress_size and info.file_size > 1024:
                    ratio = info.file_size / info.compress_size
                    if ratio > PORTABLE_VERTICAL_MAX_COMPRESSION_RATIO:
                        raise ValueError(f"P2P_VERTICAL_PACKAGE_LIMIT: excessive compression ratio `{name}`")
            for info in infos:
                content = archive.read(info)
                if len(content) != info.file_size:
                    raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: truncated entry `{info.filename}`")
                entries[info.filename] = self._canonical_content(info.filename, content)
        self._validate_entry_set(entries)
        return entries

    def _validate_entry_set(self, entries: dict[str, bytes]) -> None:
        missing = sorted(_ROOT_FILES - set(entries))
        if missing:
            raise ValueError(f"P2P_VERTICAL_INVALID_PACK: missing required entries {missing}")
        if not any(name.startswith("sections/") and name.endswith(".yml") for name in entries):
            raise ValueError(
                "P2P_VERTICAL_NO_SECTIONS: at least one sections/*.yml entry is required"
            )
        if len(entries) > PORTABLE_VERTICAL_MAX_ENTRIES:
            raise ValueError("P2P_VERTICAL_PACKAGE_LIMIT: too many entries")
        total = sum(len(content) for content in entries.values())
        if total > PORTABLE_VERTICAL_MAX_TOTAL_BYTES:
            raise ValueError("P2P_VERTICAL_PACKAGE_LIMIT: package is too large")

    def _validate_entry_name(self, name: str) -> None:
        pure = PurePosixPath(name.replace("\\", "/"))
        if (
            not name
            or pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != name
            or any(part in {"", "."} or part.startswith(".") for part in pure.parts)
        ):
            raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: unsafe path `{name}`")
        if len(pure.parts) == 1:
            if name not in _ROOT_FILES:
                raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: unsupported root entry `{name}`")
        elif pure.parts[0] not in _CONTENT_DIRS:
            raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: unsupported content directory `{pure.parts[0]}`")
        if pure.suffix.lower() not in _ALLOWED_SUFFIXES:
            raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: unsupported file type `{name}`")

    @staticmethod
    def _canonical_content(name: str, content: bytes) -> bytes:
        if len(content) > PORTABLE_VERTICAL_MAX_FILE_BYTES:
            raise ValueError(f"P2P_VERTICAL_PACKAGE_LIMIT: entry too large `{name}`")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"P2P_VERTICAL_UNSAFE_ARTIFACT: non-UTF-8 entry `{name}`") from exc
        suffix = PurePosixPath(name).suffix.lower()
        if suffix in {".yml", ".yaml"}:
            try:
                payload = load_yaml(content)
            except (ValueError, yaml.YAMLError) as exc:
                raise ValueError(f"P2P_VERTICAL_INVALID_PACK: invalid YAML entry `{name}`") from exc
            if not isinstance(payload, (dict, list)):
                raise ValueError(f"P2P_VERTICAL_INVALID_PACK: YAML entry must contain structured data `{name}`")
            return yaml_dump(payload).encode("utf-8")
        if suffix == ".json":
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"P2P_VERTICAL_INVALID_PACK: invalid JSON entry `{name}`") from exc
            return (json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")

    @staticmethod
    def _materialize_entries(root: Path, entries: dict[str, bytes]) -> None:
        for name, content in entries.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)


def normalize_expected_checksum(value: str) -> str:
    text = str(value).strip().lower()
    if text.startswith("sha256:"):
        text = text.removeprefix("sha256:")
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError("P2P_VERTICAL_INVALID_CHECKSUM: expected a SHA-256 hexadecimal checksum")
    return text


def _error_code(message: str) -> str:
    prefix = message.split(":", 1)[0]
    return prefix if prefix.startswith("P2P_") else "P2P_VERTICAL_INVALID_PACK"


def _invalid_pack() -> VerticalPack:
    return VerticalPack(
        vertical_id="",
        name="",
        version="",
        description="",
        extends=None,
        source="invalid",
        path=None,
        sections=[],
        rubrics=[],
        questions=[],
        artifacts=[],
    )

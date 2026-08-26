from __future__ import annotations

from contextlib import AbstractContextManager
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from p2p_engine.core.portable_verticals import (
    PORTABLE_VERTICAL_MAX_TOTAL_BYTES,
    PortableVerticalInspection,
    VerticalCoordinate,
)
from p2p_engine.core.vertical_registry import (
    VERTICAL_REGISTRY_PROTOCOL_VERSION,
    CachedVerticalRelease,
    VerticalCatalogItem,
    VerticalPullResult,
    VerticalRelease,
    VerticalUserPaths,
)
from p2p_engine.foundation.files import write_yaml_atomic
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.vertical_registry import (
    VerticalRegistryClient,
    parse_vertical_release,
    vertical_user_paths,
)
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.storage.filesystem import P2PWorkspace


_CACHE_SCHEMA_VERSION = 1
_SUPPORTED_CACHE_PROTOCOLS = {
    "p2p-vertical-registry/v1",
    VERTICAL_REGISTRY_PROTOCOL_VERSION,
}


class VerticalCacheService:
    def __init__(self, *, paths: VerticalUserPaths | None = None) -> None:
        self.paths = paths or vertical_user_paths()
        self.root = self.paths.vertical_cache_root

    def release_directory(self, registry: str, coordinate: str) -> Path:
        parsed = VerticalCoordinate.parse(coordinate)
        return self.root / registry / parsed.publisher / parsed.vertical_id / parsed.version

    def read(self, registry: str, coordinate: str) -> CachedVerticalRelease | None:
        directory = self.release_directory(registry, coordinate)
        if not directory.exists():
            return None
        return self._read_directory(directory, expected_registry=registry)

    def list(self, registry: str = "") -> tuple[CachedVerticalRelease, ...]:
        if not self.root.exists():
            return ()
        roots = [self.root / registry] if registry else sorted(self.root.iterdir())
        results: list[CachedVerticalRelease] = []
        for registry_root in roots:
            if not registry_root.is_dir() or registry_root.is_symlink() or registry_root.name.startswith("."):
                continue
            for metadata in sorted(registry_root.glob("*/*/*/metadata.yml")):
                results.append(
                    self._read_directory(
                        metadata.parent,
                        expected_registry=registry_root.name,
                    )
                )
        return tuple(results)

    def closure(self, registry: str, coordinate: str) -> tuple[CachedVerticalRelease, ...]:
        ordered: list[CachedVerticalRelease] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(current: str, expected_checksum: str = "") -> None:
            if current in visiting:
                raise ValueError("P2P_REGISTRY_CACHE_INVALID: cached dependency cycle detected")
            if current in visited:
                return
            visiting.add(current)
            cached = self.read(registry, current)
            if cached is None:
                raise ValueError(
                    f"P2P_REGISTRY_CACHE_INCOMPLETE: dependency `{current}` is not cached"
                )
            if expected_checksum and cached.release.semantic_checksum != expected_checksum:
                raise ValueError(
                    "P2P_REGISTRY_CACHE_INVALID: dependency semantic checksum mismatch"
                )
            for dependency in cached.release.dependencies:
                visit(dependency.coordinate, dependency.semantic_checksum)
            visiting.remove(current)
            visited.add(current)
            ordered.append(cached)

        visit(str(VerticalCoordinate.parse(coordinate)))
        return tuple(ordered)

    def write_candidate(self, directory: Path, release: VerticalRelease, artifact: Path) -> None:
        directory.mkdir(parents=True, exist_ok=False)
        destination = directory / f"{release.artifact.sha256}.p2pv"
        artifact.replace(destination)
        write_yaml_atomic(
            directory / "metadata.yml",
            {
                "vertical_cache": {
                    "schema_version": _CACHE_SCHEMA_VERSION,
                    "protocol_version": VERTICAL_REGISTRY_PROTOCOL_VERSION,
                    "release": release.to_dict(),
                }
            },
        )

    def add_local(
        self,
        release: VerticalRelease,
        artifact: Path,
    ) -> tuple[str, CachedVerticalRelease]:
        if release.registry != "local":
            raise ValueError(
                "P2P_VERTICAL_LOCAL_ADD_INVALID: local releases must use the local registry"
            )
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError("P2P_REGISTRY_ARTIFACT_INVALID: local artifact is unsafe")
        digest, size = _file_digest(artifact)
        if digest != release.artifact.sha256 or size != release.artifact.size:
            raise ValueError(
                "P2P_REGISTRY_ARTIFACT_MISMATCH: local artifact differs from release metadata"
            )
        registry_root = self.root / "local"
        registry_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with _CacheLock(registry_root / ".cache.lock"):
            current = self.read("local", release.coordinate)
            if current is not None:
                if _immutable_identity(current.release) != _immutable_identity(release):
                    raise ValueError(
                        "P2P_REGISTRY_IMMUTABILITY_VIOLATION: local release coordinate already exists"
                    )
                return "already_present", current
            transaction = Path(tempfile.mkdtemp(prefix=".add-local-", dir=registry_root))
            try:
                staged_artifact = transaction / "artifact.p2pv"
                shutil.copyfile(artifact, staged_artifact)
                candidate = transaction / "release"
                self.write_candidate(candidate, release, staged_artifact)
                target = self.release_directory("local", release.coordinate)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    concurrent = self.read("local", release.coordinate)
                    if (
                        concurrent is None
                        or _immutable_identity(concurrent.release)
                        != _immutable_identity(release)
                    ):
                        raise ValueError(
                            "P2P_REGISTRY_IMMUTABILITY_VIOLATION: concurrent local cache conflict"
                        )
                    return "already_present", concurrent
                candidate.replace(target)
                committed = self.read("local", release.coordinate)
                if committed is None:  # pragma: no cover - guarded by atomic rename.
                    raise ValueError("P2P_REGISTRY_CACHE_INVALID: local release commit failed")
                return "added", committed
            finally:
                shutil.rmtree(transaction, ignore_errors=True)

    def _read_directory(
        self,
        directory: Path,
        *,
        expected_registry: str,
    ) -> CachedVerticalRelease:
        metadata = directory / "metadata.yml"
        if (
            not directory.is_dir()
            or directory.is_symlink()
            or not metadata.is_file()
            or metadata.is_symlink()
        ):
            raise ValueError(f"P2P_REGISTRY_CACHE_INVALID: unsafe cache entry {directory}")
        try:
            raw = load_yaml(metadata.read_bytes())
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"P2P_REGISTRY_CACHE_INVALID: {exc}") from exc
        payload = raw.get("vertical_cache") if isinstance(raw, dict) else None
        if not isinstance(payload, dict):
            raise ValueError("P2P_REGISTRY_CACHE_INVALID: expected vertical_cache mapping")
        if payload.get("schema_version") != _CACHE_SCHEMA_VERSION:
            raise ValueError("P2P_REGISTRY_CACHE_INVALID: unsupported cache schema")
        if payload.get("protocol_version") not in _SUPPORTED_CACHE_PROTOCOLS:
            raise ValueError("P2P_REGISTRY_CACHE_INVALID: unsupported registry protocol")
        release = parse_vertical_release(payload.get("release"), registry=expected_registry)
        expected_directory = self.release_directory(expected_registry, release.coordinate)
        if directory.resolve() != expected_directory.resolve():
            raise ValueError("P2P_REGISTRY_CACHE_INVALID: release is stored under the wrong coordinate")
        artifact = directory / f"{release.artifact.sha256}.p2pv"
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError("P2P_REGISTRY_CACHE_INVALID: cached artifact is missing or unsafe")
        digest, size = _file_digest(artifact)
        if digest != release.artifact.sha256 or size != release.artifact.size:
            raise ValueError("P2P_REGISTRY_CACHE_INVALID: cached artifact checksum or size mismatch")
        return CachedVerticalRelease(
            release=release,
            artifact_path=artifact,
            metadata_path=metadata,
        )


class VerticalPullService:
    def __init__(
        self,
        *,
        client: VerticalRegistryClient | None = None,
        cache: VerticalCacheService | None = None,
    ) -> None:
        self.client = client or VerticalRegistryClient()
        self.cache = cache or VerticalCacheService(paths=self.client.configuration.paths)

    def pull(self, coordinate: str, *, registry: str = "") -> VerticalPullResult:
        requested = str(VerticalCoordinate.parse(coordinate))
        record = self.client.configuration.resolve(registry)
        registry_root = self.cache.root / record.name
        registry_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with _CacheLock(registry_root / ".cache.lock"):
            ordered = self._plan(requested, registry=record.name)
            existing: dict[str, CachedVerticalRelease] = {}
            missing: list[VerticalRelease] = []
            for release in ordered:
                cached = self.cache.read(record.name, release.coordinate)
                if cached is None:
                    missing.append(release)
                    continue
                if _immutable_identity(cached.release) != _immutable_identity(release):
                    raise ValueError(
                        "P2P_REGISTRY_IMMUTABILITY_VIOLATION: cached release metadata changed"
                    )
                existing[release.coordinate] = cached
            if not missing:
                return VerticalPullResult(
                    registry=record.name,
                    requested_coordinate=requested,
                    status="already_present",
                    releases=tuple(existing[item.coordinate] for item in ordered),
                )
            transaction = Path(
                tempfile.mkdtemp(prefix=".pull-", dir=registry_root)
            )
            committed: list[Path] = []
            try:
                staged = self._download_missing(missing, transaction=transaction)
                artifacts = {
                    **{key: value.artifact_path for key, value in existing.items()},
                    **staged,
                }
                self._validate_closure(ordered, artifacts)
                results: dict[str, CachedVerticalRelease] = dict(existing)
                for release in missing:
                    coordinate = VerticalCoordinate.parse(release.coordinate)
                    candidate = transaction / coordinate.publisher / coordinate.vertical_id / coordinate.version
                    candidate.parent.mkdir(parents=True, exist_ok=True)
                    artifact = staged[release.coordinate]
                    self.cache.write_candidate(candidate, release, artifact)
                    target = self.cache.release_directory(record.name, release.coordinate)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        current = self.cache.read(record.name, release.coordinate)
                        if current is None or _immutable_identity(current.release) != _immutable_identity(release):
                            raise ValueError(
                                "P2P_REGISTRY_IMMUTABILITY_VIOLATION: concurrent cache conflict"
                            )
                        results[release.coordinate] = current
                        shutil.rmtree(candidate)
                        continue
                    candidate.replace(target)
                    committed.append(target)
                    committed_release = self.cache.read(record.name, release.coordinate)
                    if committed_release is None:  # pragma: no cover - guarded by the rename above.
                        raise ValueError("P2P_REGISTRY_CACHE_INVALID: committed release is missing")
                    results[release.coordinate] = committed_release
                return VerticalPullResult(
                    registry=record.name,
                    requested_coordinate=requested,
                    status="pulled",
                    releases=tuple(results[item.coordinate] for item in ordered),
                )
            except Exception:
                for path in reversed(committed):
                    shutil.rmtree(path, ignore_errors=True)
                raise
            finally:
                shutil.rmtree(transaction, ignore_errors=True)

    def _plan(self, coordinate: str, *, registry: str) -> tuple[VerticalRelease, ...]:
        ordered: list[VerticalRelease] = []
        by_coordinate: dict[str, VerticalRelease] = {}
        visiting: set[str] = set()

        def visit(current: str, expected_checksum: str = "") -> None:
            if current in visiting:
                raise ValueError("P2P_REGISTRY_DEPENDENCY_CYCLE: vertical dependency cycle detected")
            known = by_coordinate.get(current)
            if known is not None:
                if expected_checksum and known.semantic_checksum != expected_checksum:
                    raise ValueError(
                        "P2P_REGISTRY_METADATA_MISMATCH: dependency semantic checksum conflict"
                    )
                return
            visiting.add(current)
            release = self.client.release(current, registry)
            if expected_checksum and release.semantic_checksum != expected_checksum:
                raise ValueError(
                    "P2P_REGISTRY_METADATA_MISMATCH: dependency semantic checksum mismatch"
                )
            by_coordinate[current] = release
            for dependency in release.dependencies:
                visit(dependency.coordinate, dependency.semantic_checksum)
            visiting.remove(current)
            ordered.append(release)

        visit(coordinate)
        return tuple(ordered)

    def _download_missing(
        self,
        releases: list[VerticalRelease],
        *,
        transaction: Path,
    ) -> dict[str, Path]:
        downloaded: dict[str, Path] = {}
        for index, release in enumerate(releases):
            destination = transaction / f"artifact-{index}.p2pv"
            token = self.client.access_token(
                release.registry,
                required=release.visibility == "private",
            )
            result = self.client.transport.download(
                self.client.artifact_url(release),
                destination,
                token=token,
                max_bytes=min(PORTABLE_VERTICAL_MAX_TOTAL_BYTES, release.artifact.size),
            )
            if result.size != release.artifact.size or result.sha256 != release.artifact.sha256:
                raise ValueError(
                    "P2P_REGISTRY_ARTIFACT_MISMATCH: downloaded artifact checksum or size mismatch"
                )
            downloaded[release.coordinate] = destination
        return downloaded

    @staticmethod
    def _validate_closure(
        releases: tuple[VerticalRelease, ...],
        artifacts: dict[str, Path],
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="p2p-registry-verify-") as temporary:
            workspace = P2PWorkspace(Path(temporary))
            workspace.init_project_with_summary("Registry artifact verification")
            for release in releases:
                artifact = artifacts[release.coordinate]
                preview = workspace.preview_portable_vertical_install(
                    artifact,
                    expected_checksum=release.artifact.sha256,
                    actor="registry",
                )
                if preview.blockers or preview.preview is None:
                    raise ValueError(
                        "P2P_REGISTRY_ARTIFACT_INVALID: "
                        + "; ".join(preview.blockers or ("install preview failed",))
                    )
                workspace.apply_portable_vertical_install(
                    artifact,
                    expected_checksum=release.artifact.sha256,
                    preview_token=preview.preview.preview_token,
                    confirmed=True,
                    actor="registry",
                    idempotency_key=f"registry-verify:{release.artifact.sha256}",
                )
                inspection = workspace.inspect_portable_vertical(artifact, view="effective")
                if (
                    inspection.pack.coordinate != release.coordinate
                    or inspection.semantic_checksum != release.semantic_checksum
                    or inspection.pack.schema_version != release.schema_version
                ):
                    raise ValueError(
                        "P2P_REGISTRY_METADATA_MISMATCH: artifact identity differs from release metadata"
                    )
                actual_dependencies = {
                    item.coordinate: item.checksum.removeprefix("sha256:")
                    for item in (inspection.pack.manifest.dependencies if inspection.pack.manifest else [])
                }
                declared_dependencies = {
                    item.coordinate: item.semantic_checksum for item in release.dependencies
                }
                if actual_dependencies != declared_dependencies:
                    raise ValueError(
                        "P2P_REGISTRY_METADATA_MISMATCH: artifact dependencies differ from release metadata"
                    )


class VerticalCatalogService:
    def __init__(
        self,
        root: Path,
        *,
        cache: VerticalCacheService | None = None,
        client: VerticalRegistryClient | None = None,
    ) -> None:
        self.root = root.resolve()
        self.workspace = P2PWorkspace(self.root)
        self.client = client
        self.cache = cache or VerticalCacheService(
            paths=client.configuration.paths if client else None
        )

    def local_items(self, *, explicit: tuple[Path, ...] = ()) -> tuple[VerticalCatalogItem, ...]:
        items: list[VerticalCatalogItem] = []
        for item in self.workspace.project_verticals():
            pack = self.workspace.show_project_vertical(item.coordinate or item.vertical_id)
            items.append(
                VerticalCatalogItem(
                    coordinate=item.coordinate or item.vertical_id,
                    name=item.name,
                    source=item.source,
                    semantic_checksum=ProjectVerticalService.semantic_pack_checksum(pack),
                )
            )
        for cached in self.cache.list():
            release = cached.release
            items.append(
                VerticalCatalogItem(
                    coordinate=release.coordinate,
                    name=release.name,
                    description=release.description,
                    source="cache",
                    visibility=release.visibility,
                    registry=release.registry,
                    semantic_checksum=release.semantic_checksum,
                    artifact_checksum=release.artifact.sha256,
                    artifact_path=cached.artifact_path,
                )
            )
        for path in explicit:
            inspection = self.workspace.inspect_portable_vertical(path, view="effective")
            items.append(
                VerticalCatalogItem(
                    coordinate=inspection.pack.coordinate,
                    name=inspection.pack.name,
                    source="explicit",
                    semantic_checksum=inspection.semantic_checksum,
                    artifact_checksum=inspection.artifact_checksum,
                    artifact_path=path.resolve(),
                )
            )
        _assert_no_conflicts(items)
        return tuple(sorted(items, key=lambda value: (value.coordinate, value.source)))

    def remote_items(
        self,
        *,
        registry: str = "",
        query: str = "",
        include_private: bool = False,
        domain: str = "",
    ) -> tuple[VerticalCatalogItem, ...]:
        items, _page = self.remote_items_with_page(
            registry=registry,
            query=query,
            include_private=include_private,
            domain=domain,
        )
        return items

    def remote_items_with_page(
        self,
        *,
        registry: str = "",
        query: str = "",
        include_private: bool = False,
        domain: str = "",
    ):
        if self.client is None:
            raise ValueError("P2P_REGISTRY_NOT_CONFIGURED: remote catalog client is unavailable")
        local_coordinates = {item.coordinate for item in self.local_items()}
        releases, page = self.client.list_releases_with_page(
            registry,
            query=query,
            include_private=include_private,
            domain=domain,
        )
        return tuple(
            VerticalCatalogItem(
                coordinate=release.coordinate,
                name=release.name,
                description=release.description,
                source="remote",
                visibility=release.visibility,
                registry=release.registry,
                semantic_checksum=release.semantic_checksum,
                artifact_checksum=release.artifact.sha256,
                local_available=release.coordinate in local_coordinates,
                primary_domain=release.primary_domain,
            )
            for release in releases
        ), page

    def resolve(self, coordinate: str) -> VerticalCatalogItem:
        exact = str(VerticalCoordinate.parse(coordinate))
        matches = [item for item in self.local_items() if item.coordinate == exact]
        if not matches:
            raise ValueError(f"P2P_VERTICAL_NOT_FOUND: exact local release `{exact}` is unavailable")
        _assert_no_conflicts(matches)
        cached = next((item for item in matches if item.artifact_path is not None), None)
        return cached or matches[0]

    def inspect_cached(self, item: VerticalCatalogItem) -> PortableVerticalInspection:
        if item.source != "cache" or item.artifact_path is None or not item.registry:
            raise ValueError("P2P_REGISTRY_CACHE_INVALID: catalog item is not a cached release")
        closure = self.installation_closure(item)
        with tempfile.TemporaryDirectory(prefix="p2p-catalog-inspect-") as temporary:
            verifier = P2PWorkspace(Path(temporary))
            verifier.init_project("Cached vertical inspection")
            inspection = None
            for cached in closure:
                preview = verifier.preview_portable_vertical_install(
                    cached.artifact_path,
                    expected_checksum=cached.release.artifact.sha256,
                    actor="catalog",
                )
                if preview.blockers or preview.preview is None:
                    raise ValueError(
                        "P2P_REGISTRY_CACHE_INVALID: "
                        + "; ".join(preview.blockers or ("install preview failed",))
                    )
                verifier.apply_portable_vertical_install(
                    cached.artifact_path,
                    expected_checksum=cached.release.artifact.sha256,
                    preview_token=preview.preview.preview_token,
                    confirmed=True,
                    actor="catalog",
                    idempotency_key=f"catalog-inspect:{cached.release.artifact.sha256}",
                )
                inspection = verifier.inspect_portable_vertical(
                    cached.artifact_path,
                    view="effective",
                )
            if inspection is None:  # pragma: no cover - closure always contains its root.
                raise ValueError("P2P_REGISTRY_CACHE_INVALID: cached closure is empty")
            return inspection

    def installation_closure(
        self,
        item: VerticalCatalogItem,
    ) -> tuple[CachedVerticalRelease, ...]:
        if item.artifact_path is None or not item.registry:
            return ()
        ordered: list[CachedVerticalRelease] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(current: VerticalCatalogItem, expected_checksum: str = "") -> None:
            if current.coordinate in visiting:
                raise ValueError(
                    "P2P_REGISTRY_CACHE_INVALID: cached dependency cycle detected"
                )
            if current.coordinate in visited:
                return
            if expected_checksum and current.semantic_checksum != expected_checksum:
                raise ValueError(
                    "P2P_REGISTRY_CACHE_INVALID: dependency semantic checksum mismatch"
                )
            if current.artifact_path is None or not current.registry:
                visited.add(current.coordinate)
                return
            cached = self.cache.read(current.registry, current.coordinate)
            if cached is None:
                raise ValueError(
                    f"P2P_REGISTRY_CACHE_INCOMPLETE: dependency `{current.coordinate}` is not cached"
                )
            visiting.add(current.coordinate)
            for dependency in cached.release.dependencies:
                matches = [
                    candidate
                    for candidate in self.local_items()
                    if candidate.coordinate == dependency.coordinate
                ]
                if not matches:
                    raise ValueError(
                        f"P2P_REGISTRY_CACHE_INCOMPLETE: dependency `{dependency.coordinate}` is unavailable"
                    )
                _assert_no_conflicts(matches)
                dependency_item = next(
                    (candidate for candidate in matches if candidate.artifact_path is not None),
                    matches[0],
                )
                visit(dependency_item, dependency.semantic_checksum)
            visiting.remove(current.coordinate)
            visited.add(current.coordinate)
            ordered.append(cached)

        visit(item)
        return tuple(ordered)

    def search(
        self,
        query: str,
        *,
        registry: str = "",
        include_private: bool = False,
        domain: str = "",
    ) -> tuple[VerticalCatalogItem, ...]:
        normalized = query.strip().lower()
        local = (
            ()
            if domain.strip()
            else tuple(
                item
                for item in self.local_items()
                if normalized in item.coordinate.lower()
                or normalized in item.name.lower()
                or normalized in item.description.lower()
            )
        )
        remote = self.remote_items(
            registry=registry,
            query=query,
            include_private=include_private,
            domain=domain,
        )
        _assert_no_conflicts([*local, *remote])
        return (*local, *remote)


class _CacheLock(AbstractContextManager["_CacheLock"]):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "_CacheLock":
        try:
            self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.write(self.fd, str(os.getpid()).encode("ascii"))
        except FileExistsError as exc:
            raise ValueError("P2P_REGISTRY_CACHE_BUSY: another cache mutation is active") from exc
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.fd is not None:
            os.close(self.fd)
        self.path.unlink(missing_ok=True)


def _file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(64 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _immutable_identity(release: VerticalRelease) -> tuple[object, ...]:
    return (
        release.coordinate,
        release.semantic_checksum,
        release.schema_version,
        release.artifact.sha256,
        release.artifact.size,
        tuple(
            (item.coordinate, item.semantic_checksum)
            for item in release.dependencies
        ),
    )


def _assert_no_conflicts(items: list[VerticalCatalogItem] | tuple[VerticalCatalogItem, ...]) -> None:
    seen: dict[str, VerticalCatalogItem] = {}
    for item in items:
        previous = seen.get(item.coordinate)
        if previous is None:
            seen[item.coordinate] = item
            continue
        semantic_conflict = (
            previous.semantic_checksum
            and item.semantic_checksum
            and previous.semantic_checksum != item.semantic_checksum
        )
        artifact_conflict = (
            previous.artifact_checksum
            and item.artifact_checksum
            and previous.artifact_checksum != item.artifact_checksum
        )
        if semantic_conflict or artifact_conflict:
            raise ValueError(
                f"P2P_VERTICAL_CATALOG_CONFLICT: sources disagree for `{item.coordinate}`"
            )

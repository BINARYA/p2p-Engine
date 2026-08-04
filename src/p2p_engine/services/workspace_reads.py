from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import TypeVar

from p2p_engine.core.workspace_reads import (
    CapturedDocument,
    DirectoryEntrySnapshot,
    DirectorySnapshot,
    ReadConsistencyResult,
    ReadOperationCounters,
)
from p2p_engine.foundation.yaml_loaders import load_yaml


T = TypeVar("T")


class _Counters:
    def __init__(self) -> None:
        self.discovery_passes: Counter[str] = Counter()
        self.source_reads: Counter[str] = Counter()
        self.verification_reads: Counter[str] = Counter()
        self.source_hashes: Counter[str] = Counter()
        self.yaml_parses: Counter[str] = Counter()
        self.provider_calls: Counter[str] = Counter()
        self.provider_cache_hits: Counter[str] = Counter()
        self.schema_preflights = 0
        self.schema_deep_validations = 0
        self.ledger_parses: Counter[str] = Counter()
        self.vertical_pack_loads: Counter[str] = Counter()
        self.canonical_fallbacks: Counter[str] = Counter()

    def snapshot(self) -> ReadOperationCounters:
        return ReadOperationCounters(
            discovery_passes=MappingProxyType(dict(self.discovery_passes)),
            source_reads=MappingProxyType(dict(self.source_reads)),
            verification_reads=MappingProxyType(dict(self.verification_reads)),
            source_hashes=MappingProxyType(dict(self.source_hashes)),
            yaml_parses=MappingProxyType(dict(self.yaml_parses)),
            provider_calls=MappingProxyType(dict(self.provider_calls)),
            provider_cache_hits=MappingProxyType(dict(self.provider_cache_hits)),
            schema_preflights=self.schema_preflights,
            schema_deep_validations=self.schema_deep_validations,
            ledger_parses=MappingProxyType(dict(self.ledger_parses)),
            vertical_pack_loads=MappingProxyType(dict(self.vertical_pack_loads)),
            canonical_fallbacks=MappingProxyType(dict(self.canonical_fallbacks)),
        )


class WorkspaceDocumentStore:
    def __init__(self, root: Path, *, counters: _Counters | None = None) -> None:
        self.root = root.resolve()
        self._root_part_count = len(self.root.parts)
        self._counters = counters or _Counters()
        self._documents: dict[Path, tuple[CapturedDocument, bytes | None]] = {}
        self._parsed: dict[tuple[Path, str, str], object] = {}
        self._discoveries: dict[tuple[Path, str, bool], DirectorySnapshot] = {}
        self._discovery_predicates: dict[
            tuple[Path, str, bool], Callable[[Path], bool] | None
        ] = {}

    @property
    def counters(self) -> ReadOperationCounters:
        return self._counters.snapshot()

    def capture(self, path: Path | str) -> CapturedDocument:
        resolved = self._resolve(path)
        if resolved in self._documents:
            return self._documents[resolved][0]
        relative = self._relative_path(resolved)
        if not resolved.exists():
            document = CapturedDocument(relative, False, None, 0, None)
            self._documents[resolved] = (document, None)
            return document
        if resolved.is_symlink() or not resolved.is_file():
            raise ValueError(f"Expected regular workspace file: {relative}")
        content = resolved.read_bytes()
        stat = resolved.stat()
        digest = hashlib.sha256(content).hexdigest()
        self._counters.source_reads[relative] += 1
        self._counters.source_hashes[relative] += 1
        document = CapturedDocument(
            relative_path=relative,
            exists=True,
            physical_sha256=digest,
            size=len(content),
            mtime_ns_observed=stat.st_mtime_ns,
        )
        self._documents[resolved] = (document, content)
        return document

    def bytes(self, path: Path | str) -> bytes:
        resolved = self._resolve(path)
        document = self.capture(resolved)
        if not document.exists:
            raise FileNotFoundError(document.relative_path)
        content = self._documents[resolved][1]
        assert content is not None
        return content

    def text(self, path: Path | str, *, encoding: str = "utf-8") -> str:
        return self.bytes(path).decode(encoding)

    def yaml(self, path: Path | str, *, loader_contract: str = "safe-v1") -> object:
        resolved = self._resolve(path)
        document = self.capture(resolved)
        if not document.exists or document.physical_sha256 is None:
            raise FileNotFoundError(document.relative_path)
        key = (resolved, document.physical_sha256, loader_contract)
        if key in self._parsed:
            return self._parsed[key]
        value = load_yaml(self.bytes(resolved), loader_contract=loader_contract)
        self._counters.yaml_parses[f"{document.relative_path}:{loader_contract}"] += 1
        self._parsed[key] = value
        return value

    def discover(
        self,
        directory: Path | str,
        *,
        policy: str,
        predicate: Callable[[Path], bool] | None = None,
        recursive: bool = False,
    ) -> tuple[Path, ...]:
        resolved = self._resolve(directory)
        key = (resolved, policy, recursive)
        if key in self._discoveries:
            snapshot = self._discoveries[key]
            return tuple(self.root / item.relative_path for item in snapshot.entries)
        relative = self._relative_path(resolved)
        entries: list[DirectoryEntrySnapshot] = []
        if resolved.exists():
            if resolved.is_symlink() or not resolved.is_dir():
                raise ValueError(f"Expected workspace directory: {relative}")
            candidates = resolved.rglob("*") if recursive else resolved.iterdir()
            for item in sorted(
                candidates,
                key=lambda candidate: candidate.parts,
            ):
                item_relative = self._relative_path(item)
                if item.is_symlink():
                    raise ValueError(
                        f"Workspace discovery rejects symlink: {item_relative}"
                    )
                if predicate is not None and not predicate(item):
                    continue
                stat = item.stat()
                entries.append(
                    DirectoryEntrySnapshot(
                        relative_path=item_relative,
                        is_directory=item.is_dir(),
                        size=stat.st_size,
                        mtime_ns_observed=stat.st_mtime_ns,
                    )
                )
        counter_key = f"{relative}:{policy}" + (":recursive" if recursive else "")
        self._counters.discovery_passes[counter_key] += 1
        self._discoveries[key] = DirectorySnapshot(relative, tuple(entries))
        self._discovery_predicates[key] = predicate
        return tuple(self.root / item.relative_path for item in entries)

    def finalize(self) -> ReadConsistencyResult:
        changed_paths: list[str] = []
        for resolved, (document, _) in self._documents.items():
            if not document.exists:
                if resolved.exists():
                    changed_paths.append(document.relative_path)
                continue
            if not resolved.exists() or resolved.is_symlink() or not resolved.is_file():
                changed_paths.append(document.relative_path)
                continue
            stat = resolved.stat()
            if (
                stat.st_size == document.size
                and stat.st_mtime_ns == document.mtime_ns_observed
            ):
                continue
            content = resolved.read_bytes()
            self._counters.verification_reads[document.relative_path] += 1
            if hashlib.sha256(content).hexdigest() != document.physical_sha256:
                changed_paths.append(document.relative_path)
        changed_directories: list[str] = []
        for (directory, policy, recursive), snapshot in self._discoveries.items():
            predicate = self._discovery_predicates[(directory, policy, recursive)]
            current: list[DirectoryEntrySnapshot] = []
            if directory.exists() and directory.is_dir() and not directory.is_symlink():
                candidates = directory.rglob("*") if recursive else directory.iterdir()
                for item in sorted(
                    candidates,
                    key=lambda candidate: candidate.parts,
                ):
                    item_relative = self._relative_path(item)
                    if item.is_symlink():
                        changed_directories.append(snapshot.relative_path)
                        current = []
                        break
                    if predicate is not None and not predicate(item):
                        continue
                    stat = item.stat()
                    current.append(
                        DirectoryEntrySnapshot(
                            relative_path=item_relative,
                            is_directory=item.is_dir(),
                            size=stat.st_size,
                            mtime_ns_observed=stat.st_mtime_ns,
                        )
                    )
            if tuple(current) != snapshot.entries:
                changed_directories.append(f"{snapshot.relative_path}:{policy}")
        if changed_paths or changed_directories:
            return ReadConsistencyResult(
                status="concurrent_change",
                changed_paths=tuple(sorted(set(changed_paths))),
                changed_directories=tuple(sorted(set(changed_directories))),
                diagnostic_code="P2P_READ_CONCURRENT_CHANGE",
            )
        return ReadConsistencyResult(status="current")

    def _resolve(self, path: Path | str) -> Path:
        candidate = Path(path)
        resolved = candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"Workspace path escapes root: {path}") from exc
        return resolved

    def _relative_path(self, path: Path) -> str:
        return "/".join(path.parts[self._root_part_count :])


class WorkspaceReadContext:
    def __init__(
        self,
        root: Path,
        *,
        allow_existing_transaction_lock: bool = False,
    ) -> None:
        self.root = root.resolve()
        self.allow_existing_transaction_lock = allow_existing_transaction_lock
        self._counters = _Counters()
        self.documents = WorkspaceDocumentStore(self.root, counters=self._counters)
        self._providers: dict[tuple[str, tuple[object, ...]], object] = {}
        self._transaction_lock_observed = False

    @property
    def counters(self) -> ReadOperationCounters:
        return self._counters.snapshot()

    def provide(self, name: str, arguments: Iterable[object], factory: Callable[[], T]) -> T:
        self._observe_transaction_lock()
        key = (name, tuple(arguments))
        self._counters.provider_calls[name] += 1
        if key in self._providers:
            self._counters.provider_cache_hits[name] += 1
            return self._providers[key]  # type: ignore[return-value]
        value = factory()
        self._providers[key] = value
        return value

    def record_schema_preflight(self) -> None:
        self._counters.schema_preflights += 1

    def record_schema_deep_validation(self) -> None:
        self._counters.schema_deep_validations += 1

    def record_ledger_parse(self, relative_path: str) -> None:
        self._counters.ledger_parses[relative_path] += 1

    def record_vertical_pack_load(self, vertical_id: str) -> None:
        self._counters.vertical_pack_loads[vertical_id] += 1

    def record_canonical_fallback(self, artifact: str) -> None:
        self._counters.canonical_fallbacks[artifact] += 1

    def finalize(self) -> ReadConsistencyResult:
        result = self.documents.finalize()
        lock = self.documents.capture(
            ".p2p/.internal/workspace-transactions/apply.lock"
        )
        if lock.exists and not self.allow_existing_transaction_lock:
            return ReadConsistencyResult(
                status="concurrent_change",
                changed_paths=(lock.relative_path,),
                diagnostic_code="P2P_READ_CONCURRENT_CHANGE",
            )
        return result

    def _observe_transaction_lock(self) -> None:
        if self._transaction_lock_observed:
            return
        self.documents.capture(".p2p/.internal/workspace-transactions/apply.lock")
        self._transaction_lock_observed = True

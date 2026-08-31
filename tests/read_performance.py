from __future__ import annotations

import hashlib
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ReadMeasurement:
    elapsed_seconds: float
    result: object
    peak_memory_bytes: int = 0


def measure_read(
    operation: Callable[[], T],
    *,
    track_memory: bool = False,
) -> ReadMeasurement:
    if track_memory:
        tracemalloc.start()
    started = perf_counter()
    try:
        result = operation()
        peak_memory = tracemalloc.get_traced_memory()[1] if track_memory else 0
    finally:
        if track_memory:
            tracemalloc.stop()
    return ReadMeasurement(
        elapsed_seconds=perf_counter() - started,
        result=result,
        peak_memory_bytes=peak_memory,
    )


def tree_digest(root: Path, *, exclude: frozenset[str] = frozenset()) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative in exclude:
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink")
        elif path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"directory")
        digest.update(b"\0")
    return digest.hexdigest()

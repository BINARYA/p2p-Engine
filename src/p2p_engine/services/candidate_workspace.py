from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import yaml

from p2p_engine.core.mutation_receipts import MUTATION_RECEIPT_ROOT


class CandidateWorkspaceView:
    def __init__(
        self,
        *,
        root: Path,
        candidates: dict[str, bytes],
        preserved: dict[str, bytes | None],
        owned_paths: set[str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self._candidates = {_normalize(path): content for path, content in candidates.items()}
        self._preserved = {_normalize(path): content for path, content in preserved.items()}
        self._owned_paths = {_normalize(path) for path in (owned_paths or set(candidates))}
        undeclared = set(self._candidates) - self._owned_paths
        if undeclared:
            raise ValueError(
                f"Candidate contains undeclared workspace transaction targets: {sorted(undeclared)}"
            )
        self.reads: list[tuple[str, str]] = []

    def exists(self, path: str | Path) -> bool:
        normalized = _normalize(path)
        if normalized in self._candidates:
            self.reads.append((normalized, "candidate"))
            return True
        if normalized in self._owned_paths:
            self.reads.append((normalized, "candidate_missing"))
            return False
        self.reads.append((normalized, "preserved"))
        return self._preserved.get(normalized) is not None

    def read_bytes(self, path: str | Path) -> bytes:
        normalized = _normalize(path)
        if normalized in self._candidates:
            self.reads.append((normalized, "candidate"))
            return self._candidates[normalized]
        if normalized in self._owned_paths:
            self.reads.append((normalized, "candidate_missing"))
            raise FileNotFoundError(normalized)
        self.reads.append((normalized, "preserved"))
        content = self._preserved.get(normalized)
        if content is None:
            raise FileNotFoundError(normalized)
        return content

    def read_text(self, path: str | Path, *, encoding: str = "utf-8") -> str:
        return self.read_bytes(path).decode(encoding)

    def read_yaml_mapping(self, path: str | Path) -> dict[str, object]:
        value = yaml.safe_load(self.read_text(path))
        if not isinstance(value, dict):
            raise ValueError(f"Candidate YAML document must be a mapping: {_normalize(path)}")
        return value

    def assert_owned_reads_used_candidates(self) -> None:
        invalid = [path for path, source in self.reads if path in self._owned_paths and source != "candidate"]
        if invalid:
            raise ValueError(
                "Migration-owned validation did not read candidate bytes: " + ", ".join(sorted(set(invalid)))
            )


def _normalize(path: str | Path) -> str:
    text = Path(path).as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    pure = PurePosixPath(text)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"Unsafe path outside governed candidate workspace: {text}")
    normalized = pure.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if (
        not normalized.startswith(".p2p/")
        or (
            normalized.startswith(".p2p/.internal/")
            and _MUTATION_RECEIPT_TARGET.fullmatch(normalized) is None
            and _PROJECT_STRUCTURE_EXPORT_MARKER_TARGET.fullmatch(normalized) is None
        )
    ):
        raise ValueError(f"Candidate target is outside governed migration ownership: {text}")
    return normalized


_MUTATION_RECEIPT_TARGET = re.compile(
    rf"^{re.escape(MUTATION_RECEIPT_ROOT)}/[0-9a-f]{{64}}\.yml$"
)

_PROJECT_STRUCTURE_EXPORT_MARKER_TARGET = re.compile(
    r"^\.p2p/\.internal/project-structure-exports/[0-9a-f]{64}\.yml$"
)

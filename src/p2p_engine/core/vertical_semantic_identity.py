from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, TypeVar

VERTICAL_SEMANTIC_CHECKSUM_CONTRACT = "p2p-vertical-semantic-checksum/v1"
VERTICAL_SEMANTIC_CHECKSUM_ALGORITHM = "sha256"

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_CONTRACT = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,127}$")
_ALGORITHM = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")
_Pack = TypeVar("_Pack")


class VerticalSemanticComparison(str, Enum):
    EQUAL = "equal"
    DIFFERENT = "different"
    INCOMPARABLE = "incomparable"


@dataclass(frozen=True)
class VerticalSemanticIdentity:
    contract: str
    algorithm: str
    digest: str

    def __post_init__(self) -> None:
        contract = str(self.contract or "").strip()
        algorithm = str(self.algorithm or "").strip()
        digest = str(self.digest or "").strip()
        if not _CONTRACT.fullmatch(contract):
            raise ValueError(
                "P2P_VERTICAL_SEMANTIC_IDENTITY_INVALID: contract is malformed"
            )
        if not _ALGORITHM.fullmatch(algorithm):
            raise ValueError(
                "P2P_VERTICAL_SEMANTIC_IDENTITY_INVALID: algorithm is malformed"
            )
        if not _DIGEST.fullmatch(digest):
            raise ValueError(
                "P2P_VERTICAL_SEMANTIC_IDENTITY_INVALID: digest must be 64 lowercase SHA-256 hexadecimal characters"
            )
        if (
            contract == VERTICAL_SEMANTIC_CHECKSUM_CONTRACT
            and algorithm != VERTICAL_SEMANTIC_CHECKSUM_ALGORITHM
        ):
            raise ValueError(
                "P2P_VERTICAL_SEMANTIC_IDENTITY_INVALID: v1 requires algorithm sha256"
            )
        object.__setattr__(self, "contract", contract)
        object.__setattr__(self, "algorithm", algorithm)
        object.__setattr__(self, "digest", digest)

    @classmethod
    def v1(cls, digest: str) -> "VerticalSemanticIdentity":
        return cls(
            contract=VERTICAL_SEMANTIC_CHECKSUM_CONTRACT,
            algorithm=VERTICAL_SEMANTIC_CHECKSUM_ALGORITHM,
            digest=digest,
        )

    @classmethod
    def from_mapping(cls, value: object) -> "VerticalSemanticIdentity":
        if not isinstance(value, Mapping):
            raise ValueError(
                "P2P_VERTICAL_SEMANTIC_IDENTITY_INVALID: semantic_identity must be a mapping"
            )
        unknown = sorted(set(value) - {"contract", "algorithm", "digest"})
        if unknown:
            raise ValueError(
                "P2P_VERTICAL_SEMANTIC_IDENTITY_INVALID: semantic_identity has unknown fields "
                f"{unknown}"
            )
        return cls(
            contract=str(value.get("contract") or ""),
            algorithm=str(value.get("algorithm") or ""),
            digest=str(value.get("digest") or ""),
        )

    @property
    def supported(self) -> bool:
        return self.contract == VERTICAL_SEMANTIC_CHECKSUM_CONTRACT

    def require_supported(self) -> None:
        if not self.supported:
            raise ValueError(
                "P2P_VERTICAL_SEMANTIC_CONTRACT_UNSUPPORTED: unsupported vertical semantic checksum contract "
                f"`{self.contract}`"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "contract": self.contract,
            "algorithm": self.algorithm,
            "digest": self.digest,
        }


def compare_vertical_semantic_identities(
    left: VerticalSemanticIdentity,
    right: VerticalSemanticIdentity,
) -> VerticalSemanticComparison:
    if left.contract != right.contract or left.algorithm != right.algorithm:
        return VerticalSemanticComparison.INCOMPARABLE
    if left.digest == right.digest:
        return VerticalSemanticComparison.EQUAL
    return VerticalSemanticComparison.DIFFERENT


def registry_v2_semantic_identity(
    semantic_checksum: object,
    semantic_identity: object = None,
    *,
    field: str = "semantic_checksum",
) -> VerticalSemanticIdentity:
    """Normalize the strictly additive registry-v2 scalar/structured pair."""
    scalar = str(semantic_checksum or "").strip().lower().removeprefix("sha256:")
    if not _DIGEST.fullmatch(scalar):
        raise ValueError(
            f"P2P_REGISTRY_RESPONSE_INVALID: {field} must be a SHA-256 checksum"
        )
    legacy = VerticalSemanticIdentity.v1(scalar)
    if semantic_identity is None:
        return legacy
    structured = VerticalSemanticIdentity.from_mapping(semantic_identity)
    structured.require_supported()
    if structured != legacy:
        raise ValueError(
            "P2P_VERTICAL_SEMANTIC_IDENTITY_CONFLICT: semantic_checksum and semantic_identity disagree"
        )
    return structured


def supported_vertical_semantic_contracts() -> tuple[str, ...]:
    return (VERTICAL_SEMANTIC_CHECKSUM_CONTRACT,)


def calculate_vertical_semantic_identity(
    pack: _Pack,
    *,
    contract: str,
    v1_calculator: Callable[[_Pack], VerticalSemanticIdentity],
) -> VerticalSemanticIdentity:
    if contract != VERTICAL_SEMANTIC_CHECKSUM_CONTRACT:
        raise ValueError(
            "P2P_VERTICAL_SEMANTIC_CONTRACT_UNSUPPORTED: unsupported vertical semantic checksum contract "
            f"`{contract}`"
        )
    return v1_calculator(pack)


def verify_vertical_semantic_identity(
    actual: VerticalSemanticIdentity,
    expected: VerticalSemanticIdentity,
) -> None:
    expected.require_supported()
    actual.require_supported()
    comparison = compare_vertical_semantic_identities(actual, expected)
    if comparison is VerticalSemanticComparison.INCOMPARABLE:
        raise ValueError(
            "P2P_VERTICAL_SEMANTIC_IDENTITY_INCOMPARABLE: semantic identities use different contracts"
        )
    if comparison is VerticalSemanticComparison.DIFFERENT:
        raise ValueError(
            "P2P_VERTICAL_SEMANTIC_IDENTITY_MISMATCH: semantic identity digest mismatch"
        )

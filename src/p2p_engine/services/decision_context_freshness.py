from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from types import MappingProxyType

from p2p_engine.core.decision_context import (
    DecisionContextFreshnessCheck,
    DecisionContextIndex,
    DecisionContextManifest,
    DecisionContextPacket,
    Freshness,
    to_json_ready,
)


def semantic_fingerprint(
    source_fingerprint_sha256: str,
    *,
    extractor_version: str,
    authority_policy_version: str,
    relation_policy_version: str,
) -> str:
    payload = {
        "source_fingerprint_sha256": source_fingerprint_sha256,
        "extractor_version": extractor_version,
        "authority_policy_version": authority_policy_version,
        "relation_policy_version": relation_policy_version,
    }
    return _payload_hash(payload)


def packet_semantic_fingerprint(packet: DecisionContextPacket) -> str:
    return _payload_hash(to_json_ready(packet))


def manifests_semantically_equal(
    left: DecisionContextManifest,
    right: DecisionContextManifest,
) -> bool:
    return _manifest_semantic_payload(left) == _manifest_semantic_payload(right)


class DecisionContextFreshnessService:
    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def manifest(
        self,
        index: DecisionContextIndex,
        *,
        generator_version: str,
        retrieval_policy_version: str = "",
        budget_policy_version: str = "",
    ) -> DecisionContextManifest:
        inputs = tuple(
            MappingProxyType(
                {
                    "path": source.path,
                    "presence": source.presence.value,
                    "sha256": source.sha256,
                }
            )
            for source in sorted(
                index.sources,
                key=lambda item: (item.path, item.source_kind.value),
            )
        )
        return DecisionContextManifest(
            schema_version=index.schema_version,
            generator_version=generator_version,
            source_catalog_version=index.source_catalog_version,
            extractor_version=index.extractor_version,
            authority_policy_version=index.authority_policy_version,
            relation_policy_version=index.relation_policy_version,
            retrieval_policy_version=retrieval_policy_version,
            budget_policy_version=budget_policy_version,
            source_fingerprint_sha256=index.source_fingerprint_sha256,
            semantic_fingerprint_sha256=index.semantic_fingerprint_sha256,
            generated_at=_format_time(self.clock()),
            inputs=inputs,
        )

    def check(
        self,
        manifest: DecisionContextManifest,
        index: DecisionContextIndex,
        *,
        generator_version: str,
        retrieval_policy_version: str = "",
        budget_policy_version: str = "",
    ) -> DecisionContextFreshnessCheck:
        reasons: list[str] = []
        _version_reason(reasons, "schema", manifest.schema_version, index.schema_version)
        _version_reason(
            reasons,
            "generator",
            manifest.generator_version,
            generator_version,
        )
        _version_reason(
            reasons,
            "source_catalog",
            manifest.source_catalog_version,
            index.source_catalog_version,
        )
        _version_reason(
            reasons,
            "extractor",
            manifest.extractor_version,
            index.extractor_version,
        )
        _version_reason(
            reasons,
            "authority_policy",
            manifest.authority_policy_version,
            index.authority_policy_version,
        )
        _version_reason(
            reasons,
            "relation_policy",
            manifest.relation_policy_version,
            index.relation_policy_version,
        )
        _version_reason(
            reasons,
            "retrieval_policy",
            manifest.retrieval_policy_version,
            retrieval_policy_version,
        )
        _version_reason(
            reasons,
            "budget_policy",
            manifest.budget_policy_version,
            budget_policy_version,
        )

        previous_inputs = _inputs_by_path(manifest.inputs)
        current_inputs = {
            source.path: {
                "presence": source.presence.value,
                "sha256": source.sha256,
            }
            for source in index.sources
        }
        for path in sorted(set(previous_inputs) | set(current_inputs)):
            previous = previous_inputs.get(path)
            current = current_inputs.get(path)
            if previous is None:
                reasons.append(f"source_added:{path}")
                continue
            if current is None:
                reasons.append(f"source_removed:{path}")
                continue
            if previous.get("presence") != current.get("presence"):
                reasons.append(f"source_presence_changed:{path}")
            elif previous.get("sha256") != current.get("sha256"):
                reasons.append(f"source_hash_changed:{path}")

        if manifest.source_fingerprint_sha256 != index.source_fingerprint_sha256:
            reasons.append("source_fingerprint_changed")
        if manifest.semantic_fingerprint_sha256 != index.semantic_fingerprint_sha256:
            reasons.append("semantic_fingerprint_changed")

        return DecisionContextFreshnessCheck(
            status=Freshness.STALE if reasons else Freshness.CURRENT,
            reasons=tuple(dict.fromkeys(reasons)),
        )


def _manifest_semantic_payload(manifest: DecisionContextManifest) -> dict[str, object]:
    payload = to_json_ready(manifest)
    if not isinstance(payload, dict):
        raise TypeError("Decision context manifest must serialize to a mapping.")
    payload.pop("generated_at", None)
    return payload


def _inputs_by_path(
    inputs: tuple[object, ...],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for item in inputs:
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path") or "")
        if path:
            result[path] = {
                "presence": item.get("presence"),
                "sha256": item.get("sha256"),
            }
    return result


def _version_reason(
    reasons: list[str],
    name: str,
    previous: str,
    current: str,
) -> None:
    if previous != current:
        reasons.append(f"{name}_version_changed:{previous or '<none>'}->{current or '<none>'}")


def _format_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _payload_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

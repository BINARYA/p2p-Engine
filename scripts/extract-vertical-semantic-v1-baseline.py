#!/usr/bin/env python3
"""One-time extractor for the P2P Engine v0.6.7 semantic checksum baseline.

This development tool prints static fixture material. Regression tests never
invoke it and never regenerate their own expected values.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import json
import platform
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

import p2p_engine
from p2p_engine.services.project_verticals import ProjectVerticalService, _pack_payload
from p2p_engine.services.vertical_packages import PortableVerticalPackageService

BASELINE_VERSION = "0.6.7"
BASELINE_COMMIT = "5cfe0c821f8cc40b71f6a7828204b7fdfca7d6ef"
BASELINE_WHEEL_SHA256 = (
    "65763e89dc8b15b09d4fadcaff0fb45cdd5b60d2335d01c5b9bc65a727553580"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    if p2p_engine.__version__ != BASELINE_VERSION or args.baseline_commit != BASELINE_COMMIT:
        parser.error("extractor requires the exact P2P Engine v0.6.7 baseline")
    module_path = Path(p2p_engine.__file__).resolve()
    if any((parent / ".git").exists() for parent in module_path.parents):
        parser.error("extractor refuses a source checkout as its expected-value oracle")
    wheel = args.wheel.resolve()
    if not wheel.is_file() or hashlib.sha256(wheel.read_bytes()).hexdigest() != BASELINE_WHEEL_SHA256:
        parser.error("extractor requires the reviewed official P2P Engine 0.6.7 wheel")
    direct_url_text = importlib.metadata.distribution("p2p-engine").read_text(
        "direct_url.json"
    )
    if not direct_url_text:
        parser.error("baseline installation lacks wheel provenance")
    direct_url = json.loads(direct_url_text)
    parsed_url = urlparse(str(direct_url.get("url") or ""))
    installed_from = Path(unquote(parsed_url.path)).resolve()
    if parsed_url.scheme != "file" or installed_from != wheel:
        parser.error("imported baseline was not installed from the supplied wheel")
    source = args.input.resolve()
    service = ProjectVerticalService(
        root=source.parent,
        p2p_dir=source.parent / ".unused-p2p",
        proposal_summaries=lambda: [],
        find_proposal_dir=lambda value: source.parent / value,
    )
    pack = service.load_explicit_pack(source)
    payload = _pack_payload(pack)
    canonical = yaml.safe_dump(payload, sort_keys=True, allow_unicode=False).encode("utf-8")
    package_service = PortableVerticalPackageService(
        root=source.parent,
        p2p_dir=source.parent / ".unused-p2p",
        vertical_service=service,
    )
    with tempfile.TemporaryDirectory(prefix="p2p-v067-package-") as temporary:
        package = package_service.package(
            source,
            output=Path(temporary) / "baseline.p2pv",
        )
    result = {
        "baseline": {
            "version": BASELINE_VERSION,
            "commit": BASELINE_COMMIT,
            "wheel_sha256": BASELINE_WHEEL_SHA256,
            "python_version": platform.python_version(),
            "pyyaml_version": yaml.__version__,
        },
        "expected_projection": payload,
        "expected_canonical_base64": base64.b64encode(canonical).decode("ascii"),
        "expected_sha256": hashlib.sha256(canonical).hexdigest(),
        "expected_artifact_sha256": package.artifact_checksum,
        "expected_artifact_size": package.size,
    }
    if args.summary:
        print(json.dumps({"baseline": result["baseline"], "expected_sha256": result["expected_sha256"], "expected_artifact_sha256": result["expected_artifact_sha256"], "expected_artifact_size": result["expected_artifact_size"]}, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

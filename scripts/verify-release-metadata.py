#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import tomllib
from datetime import date
from pathlib import Path

DATED_RELEASE = re.compile(r"^## (?P<version>\d+\.\d+\.\d+) - (?P<date>\d{4}-\d{2}-\d{2})$", re.MULTILINE)
REQUIRED_URLS = {"Homepage", "Repository", "Issues", "Changelog"}
APPROVED_LICENSE = "GPL-3.0-or-later"
APPROVED_IDENTITY = "mrjungle"
APPROVED_URLS = {
    "Homepage": "https://github.com/BINARYA/p2p-Engine",
    "Repository": "https://github.com/BINARYA/p2p-Engine",
    "Issues": "https://github.com/BINARYA/p2p-Engine/issues",
    "Changelog": "https://github.com/BINARYA/p2p-Engine/blob/main/CHANGELOG.md",
}


def validate_release_metadata(
    root: Path,
    *,
    expected_tag: str | None = None,
    release_notes: Path | None = None,
    require_release: bool = False,
) -> list[str]:
    issues: list[str] = []
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    version = str(project.get("version") or "")

    license_expression = project.get("license")
    if license_expression != APPROVED_LICENSE:
        issues.append(
            "project.license must equal the owner-approved SPDX expression "
            f"{APPROVED_LICENSE}"
        )
    license_files = project.get("license-files")
    if not isinstance(license_files, list) or "LICENSE" not in license_files:
        issues.append("project.license-files must include LICENSE")

    for field in ("authors", "maintainers"):
        values = project.get(field)
        if not isinstance(values, list) or not values:
            issues.append(f"project.{field} requires the owner-approved public identity")
            continue
        if any(not isinstance(item, dict) or not str(item.get("name") or "").strip() for item in values):
            issues.append(f"project.{field} contains an identity without a name")
        elif [str(item["name"]) for item in values] != [APPROVED_IDENTITY]:
            issues.append(
                f"project.{field} must contain only the owner-approved public identity "
                f"{APPROVED_IDENTITY}"
            )

    urls = project.get("urls")
    if not isinstance(urls, dict):
        issues.append("project.urls requires owner-approved canonical URLs")
    else:
        missing_urls = sorted(REQUIRED_URLS - set(urls))
        if missing_urls:
            issues.append("project.urls is missing: " + ", ".join(missing_urls))
        elif urls != APPROVED_URLS:
            issues.append("project.urls does not match the owner-approved canonical URLs")

    classifiers = project.get("classifiers", [])
    if isinstance(classifiers, list) and any(
        str(value).startswith("License ::") for value in classifiers
    ):
        issues.append("deprecated License :: classifiers are forbidden with PEP 639 metadata")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    if require_release or expected_tag is not None:
        match = next(
            (
                item
                for item in DATED_RELEASE.finditer(changelog)
                if item.group("version") == version
            ),
            None,
        )
        if match is None:
            issues.append(f"CHANGELOG.md requires a dated {version} section")
        else:
            try:
                date.fromisoformat(match.group("date"))
            except ValueError:
                issues.append(f"CHANGELOG.md contains an invalid release date for {version}")
        if re.search(rf"^## {re.escape(version)} - Unreleased$", changelog, re.MULTILINE):
            issues.append(f"CHANGELOG.md still marks {version} as Unreleased")

        notes_path = release_notes or root / "docs" / "releases" / f"{version}.md"
        if not notes_path.is_file():
            issues.append(f"release notes are missing: {notes_path.relative_to(root)}")
        else:
            notes = notes_path.read_text(encoding="utf-8")
            if version not in notes:
                issues.append(f"release notes do not identify version {version}")
            if re.search(r"\bUnreleased\b", notes, re.IGNORECASE):
                issues.append("release notes are still marked Unreleased")
            for heading in ("Install", "Compatibility", "Checksums", "Provenance"):
                if not re.search(rf"^## {heading}$", notes, re.MULTILINE):
                    issues.append(f"release notes are missing the {heading!r} section")

    if expected_tag is not None and expected_tag != f"v{version}":
        issues.append(
            f"tag/version mismatch: expected v{version}, got {expected_tag or '<empty>'}"
        )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate owner-controlled release metadata.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--tag")
    parser.add_argument("--release-notes", type=Path)
    parser.add_argument(
        "--release",
        action="store_true",
        help="Require dated changelog and final non-Unreleased release notes",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    notes = args.release_notes
    if notes is not None and not notes.is_absolute():
        notes = root / notes
    issues = validate_release_metadata(
        root,
        expected_tag=args.tag,
        release_notes=notes,
        require_release=args.release,
    )
    if issues:
        for issue in issues:
            print(f"release metadata: {issue}")
        return 1
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    print(f"release metadata verified: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

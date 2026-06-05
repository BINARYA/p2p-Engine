# Automated GitHub Release Wheel Publishing

## Provenance

- Proposal: PROP-080
- Source: .p2p/proposals/PROP-080-automated-github-release-wheel-publishing

## Problem

Publishing P2P Engine as a project-local wheel currently requires a manual, error-prone release cycle: bump version, build artifacts locally, create a tag, create a GitHub Release, and upload .whl/.tar.gz assets through the UI. This makes frequent updates slow and increases the chance of mismatched version, tag, and wheel filenames.

## Proposal

Add a GitHub Actions release workflow triggered by version tags matching v*. The workflow should check out the repository, set up Python, install development dependencies, run the test suite, run p2p validate, build the source distribution and wheel with python -m build, verify expected dist artifacts exist, and upload the .whl and .tar.gz as assets to the matching GitHub Release. Document the new release flow: update pyproject.toml version, commit and push main, create and push an annotated tag such as v0.1.1, then GitHub Actions publishes the release assets. Keep manual release notes as a fallback, but make the tag-triggered workflow the normal path.

## Decision

# Decision - PROP-080

## Status

`accepted`

## Outcome

accepted

## Reason

Owner approved automated tag-triggered GitHub release publishing to replace the manual wheel upload path.

## Date

2026-06-03

## Approver

owner

# PROP-080 - Automated GitHub Release Wheel Publishing

## Status

`accepted`

## Problem

Publishing P2P Engine as a project-local wheel currently requires a manual, error-prone release cycle: bump version, build artifacts locally, create a tag, create a GitHub Release, and upload .whl/.tar.gz assets through the UI. This makes frequent updates slow and increases the chance of mismatched version, tag, and wheel filenames.

## Context

Pending.

## Goals

- Automate wheel and sdist publishing for GitHub Releases so maintainers can publish installable project-local packages by pushing a version tag.

## Non-Goals

- Pending.

## Proposal

Add a GitHub Actions release workflow triggered by version tags matching v*. The workflow should check out the repository, set up Python, install development dependencies, run the test suite, run p2p validate, build the source distribution and wheel with python -m build, verify expected dist artifacts exist, and upload the .whl and .tar.gz as assets to the matching GitHub Release. Document the new release flow: update pyproject.toml version, commit and push main, create and push an annotated tag such as v0.1.1, then GitHub Actions publishes the release assets. Keep manual release notes as a fallback, but make the tag-triggered workflow the normal path.

## Acceptance Criteria

- A .github/workflows/release.yml workflow exists and is triggered by v* tags; the workflow runs tests, p2p validate, and python -m build; the workflow uploads dist/*.whl and dist/*.tar.gz to the GitHub Release for the tag; documentation explains that maintainers should bump pyproject.toml, commit, push, tag, and push the tag; documentation warns not to reuse an existing version/tag; local release-how-to.md can remain a personal ignored fallback; p2p validate and the test suite pass.

## Decision

Pending.

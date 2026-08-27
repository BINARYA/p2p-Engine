#!/usr/bin/env bash
set -euo pipefail

static_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$static_root"

python_bin="${PYTHON_BIN:-python3}"
ruff_targets=(
  scripts/check-source-boundary.py
  scripts/check-doc-links.py
  scripts/generate-wavekit-transition-fixtures.py
  scripts/verify-audit-exceptions.py
  scripts/verify-release-artifacts.py
  scripts/verify-release-metadata.py
  src/p2p_engine/cli_contract.py
  src/p2p_engine/cli_commands/project_status.py
  src/p2p_engine/cli_commands/runtime.py
  src/p2p_engine/core/release_contracts.py
  src/p2p_engine/services/project_verticals.py
  src/p2p_engine/services/vertical_packages.py
  tests/test_cli_contract.py
  tests/test_portable_verticals.py
  tests/test_release_artifacts.py
  tests/test_release_automation.py
  tests/test_source_control_boundary.py
)

"$python_bin" -m ruff check "${ruff_targets[@]}"
"$python_bin" -m mypy

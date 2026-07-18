#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PYTEST_BIN:-}" ]]; then
  if [[ -x ".venv/bin/pytest" ]]; then
    PYTEST_BIN=".venv/bin/pytest"
  elif ! PYTEST_BIN="$(command -v pytest)"; then
    printf '%s\n' "pytest executable not found; activate an environment or set PYTEST_BIN" >&2
    exit 127
  fi
fi

exec "$PYTEST_BIN" -m "smoke" "$@"

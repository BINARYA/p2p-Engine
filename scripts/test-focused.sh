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

if [ "$#" -eq 0 ]; then
  set -- -m "(unit or service or adapter) and not slow"
fi

exec "$PYTEST_BIN" "$@"

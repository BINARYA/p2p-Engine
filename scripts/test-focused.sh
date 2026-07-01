#!/usr/bin/env bash
set -euo pipefail

PYTEST_BIN="${PYTEST_BIN:-.venv/bin/pytest}"

if [ "$#" -eq 0 ]; then
  set -- -m "(unit or service or adapter) and not slow"
fi

exec "$PYTEST_BIN" "$@"

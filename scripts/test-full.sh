#!/usr/bin/env bash
set -euo pipefail

PYTEST_BIN="${PYTEST_BIN:-.venv/bin/pytest}"

exec "$PYTEST_BIN" "$@"

#!/usr/bin/env bash
set -euo pipefail

audit_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
wheel=""
if [[ "${1:-}" == "--wheel" && $# -eq 2 ]]; then
  wheel="$2"
else
  printf '%s\n' "usage: scripts/audit-wheel.sh --wheel PATH" >&2
  exit 2
fi
[[ -f "$wheel" ]] || { printf 'wheel not found: %s\n' "$wheel" >&2; exit 2; }
wheel="$(CDPATH= cd -- "$(dirname -- "$wheel")" && pwd)/$(basename -- "$wheel")"

audit_env="$(mktemp -d /tmp/p2p-runtime-audit.XXXXXX)"
cleanup() {
  rm -rf -- "$audit_env"
}
trap cleanup EXIT INT TERM

"$python_bin" -m venv "$audit_env/venv"
"$audit_env/venv/bin/python" -m pip install --disable-pip-version-check "$wheel"
"$audit_env/venv/bin/python" -m pip check
runtime_requirements="$audit_env/runtime-requirements.txt"
"$audit_env/venv/bin/python" -m pip freeze \
  --exclude p2p-engine > "$runtime_requirements"
exception_arguments="$audit_env/audit-arguments.txt"
"$python_bin" "$audit_root/scripts/verify-audit-exceptions.py" \
  --emit-arguments > "$exception_arguments"
mapfile -t ignore_arguments < "$exception_arguments"
"$python_bin" -m pip_audit \
  --strict \
  --progress-spinner off \
  --requirement "$runtime_requirements" \
  --no-deps \
  --disable-pip \
  "${ignore_arguments[@]}"

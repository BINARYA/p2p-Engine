#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '%s\n' "usage: scripts/test-installed.sh [--wheel PATH] [pytest arguments...]" >&2
}

script_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
wheel_path=""
pytest_args=()
while (($#)); do
  case "$1" in
    --wheel)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      wheel_path="$2"
      shift 2
      ;;
    --wheel=*)
      wheel_path="${1#*=}"
      shift
      ;;
    *)
      pytest_args+=("$1")
      shift
      ;;
  esac
done

python_bin="${PYTHON_BIN:-python3}"
failure_mode="${P2P_TEST_FAILURE_MODE:-none}"
case "$failure_mode" in
  none|install-failure|missing-dependency|malformed-cli-json|invalid-choice-read|mcp-timeout|git-invocation|interrupted-smoke) ;;
  *)
    printf 'unsupported P2P_TEST_FAILURE_MODE: %s\n' "$failure_mode" >&2
    exit 2
    ;;
esac
export P2P_TEST_FAILURE_MODE="$failure_mode"
expected_version="$("$python_bin" -c 'import pathlib,sys,tomllib; print(tomllib.loads(pathlib.Path(sys.argv[1]).read_text())["project"]["version"])' "$script_root/pyproject.toml")"
if [[ -z "$wheel_path" ]]; then
  shopt -s nullglob
  wheels=("$script_root"/dist/*.whl)
  shopt -u nullglob
  if [[ ${#wheels[@]} -ne 1 ]]; then
    printf 'expected exactly one wheel in %s/dist, found %s\n' "$script_root" "${#wheels[@]}" >&2
    exit 2
  fi
  wheel_path="${wheels[0]}"
fi
[[ -f "$wheel_path" ]] || { printf 'wheel not found: %s\n' "$wheel_path" >&2; exit 2; }
wheel_path="$(CDPATH= cd -- "$(dirname -- "$wheel_path")" && pwd)/$(basename -- "$wheel_path")"
expected_name="p2p_engine-${expected_version}-py3-none-any.whl"
[[ "$(basename -- "$wheel_path")" == "$expected_name" ]] || {
  printf 'wrong wheel identity: expected %s, got %s\n' "$expected_name" "$(basename -- "$wheel_path")" >&2
  exit 2
}

temporary_parent="${P2P_TEST_TMPDIR:-/tmp}"
[[ -d "$temporary_parent" ]] || {
  printf 'temporary parent is not a directory: %s\n' "$temporary_parent" >&2
  exit 2
}
installed_root="$(mktemp -d "$temporary_parent/p2p-installed-wheel.XXXXXX")"
cleanup() {
  rm -rf -- "$installed_root"
}
abort() {
  cleanup
  trap - EXIT
  exit 130
}
trap cleanup EXIT
trap abort INT TERM

if [[ "$failure_mode" == "interrupted-smoke" ]]; then
  : > "$installed_root/.interrupt-handler-ready"
  while true; do
    sleep 1
  done
fi

venv_root="$installed_root/venv"
smoke_root="$installed_root/external-cwd"
sentinel_bin="$installed_root/sentinel-bin"
git_log="$installed_root/git-invocations.log"
"$python_bin" -m venv "$venv_root"
install_target="$wheel_path"
if [[ "$failure_mode" == "install-failure" ]]; then
  install_target="$installed_root/injected-missing-wheel.whl"
fi
"$venv_root/bin/python" -m pip install --disable-pip-version-check "$install_target" "pytest>=8.3,<9"
if [[ "$failure_mode" == "missing-dependency" ]]; then
  "$venv_root/bin/python" -m pip uninstall -y packaging
fi
"$venv_root/bin/python" -m pip check

mkdir -p "$smoke_root" "$sentinel_bin"
printf '%s\n' '#!/usr/bin/env sh' 'printf "%s\\n" "$*" >> "${P2P_GIT_SENTINEL_LOG}"' 'exit 97' > "$sentinel_bin/git"
chmod +x "$sentinel_bin/git"
: > "$git_log"

# Dependency installation above is the explicitly online phase. Every product
# subprocess below imports this sitecustomize module, which rejects DNS and
# internet socket access while preserving local AF_UNIX behavior.
network_log="$installed_root/network-invocations.log"
site_packages="$("$venv_root/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
printf '%s\n' \
  'import os' \
  'import socket' \
  '' \
  '_original_connect = socket.socket.connect' \
  '_original_getaddrinfo = socket.getaddrinfo' \
  '' \
  'def _deny(operation, detail):' \
  '    log = os.environ.get("P2P_NETWORK_SENTINEL_LOG")' \
  '    if log:' \
  '        with open(log, "a", encoding="utf-8") as stream:' \
  '            stream.write(f"{operation}: {detail!r}\\n")' \
  '    raise RuntimeError(f"outbound network denied during installed smoke: {operation}")' \
  '' \
  'def _guarded_connect(sock, address):' \
  '    if sock.family in (socket.AF_INET, socket.AF_INET6):' \
  '        _deny("socket.connect", address)' \
  '    return _original_connect(sock, address)' \
  '' \
  'def _guarded_getaddrinfo(host, *args, **kwargs):' \
  '    _deny("socket.getaddrinfo", host)' \
  '' \
  'socket.socket.connect = _guarded_connect' \
  'socket.getaddrinfo = _guarded_getaddrinfo' \
  > "$site_packages/sitecustomize.py"
: > "$network_log"

export PATH="$sentinel_bin:$venv_root/bin:/usr/bin:/bin"
export P2P_GIT_SENTINEL_LOG="$git_log"
export P2P_NETWORK_SENTINEL_LOG="$network_log"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PIP_NO_INDEX=1
export HTTP_PROXY="http://127.0.0.1:9"
export HTTPS_PROXY="http://127.0.0.1:9"
export ALL_PROXY="http://127.0.0.1:9"
export NO_PROXY=""
unset PYTHONPATH
cd "$smoke_root"

if [[ "$failure_mode" == "git-invocation" ]]; then
  git status >/dev/null 2>&1 || true
  [[ ! -s "$git_log" ]] || {
    printf '%s\n' "injected git invocation detected by installed smoke" >&2
    exit 1
  }
fi
"$venv_root/bin/python" - "$expected_version" "$wheel_path" "$script_root" <<'PY'
from importlib import metadata, resources
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

expected_version, wheel_path, source_root = sys.argv[1:]
import p2p_engine
import keyring
import packaging
import rich
import typer
import yaml

assert metadata.version("p2p-engine") == expected_version
assert p2p_engine.__version__ == expected_version
module_path = Path(p2p_engine.__file__).resolve()
assert "site-packages" in module_path.as_posix(), module_path
assert not module_path.is_relative_to(Path(source_root).resolve())
fixture_resource = resources.files("p2p_engine.resources.contracts").joinpath(
    "wavekit-cli-fixtures-v1.json"
)
assert fixture_resource.is_file()
fixture_bundle = json.loads(fixture_resource.read_text(encoding="utf-8"))
assert fixture_bundle["engine_version"] == expected_version
assert fixture_bundle["contract_versions"]["vertical_pack_schema_version"] == 3
assert fixture_bundle["contract_versions"]["mutation_receipt_schema_version"] == 3
assert resources.files("p2p_engine.resources.verticals.base_project").joinpath(
    "manifest.yml"
).is_file()

def run_json(*args: str, expected_codes: tuple[int, ...] = (0,)) -> dict[str, object]:
    completed = subprocess.run(
        ["p2p", *args],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=30,
    )
    if completed.returncode not in expected_codes:
        raise AssertionError((args, completed.returncode, completed.stdout, completed.stderr))
    assert "\x1b" not in completed.stdout
    if os.environ.get("P2P_TEST_FAILURE_MODE") == "malformed-cli-json" and args[0] == "version":
        return json.loads("{injected-malformed-json")
    return json.loads(completed.stdout)

def run_text(*args: str) -> str:
    completed = subprocess.run(
        ["p2p", *args],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=30,
    )
    if completed.returncode != 0:
        raise AssertionError((args, completed.returncode, completed.stdout, completed.stderr))
    return completed.stdout

def assert_choice_read(
    payload: dict[str, object],
    *,
    operation: str,
    data_key: str,
    data_contract: str,
) -> dict[str, object]:
    assert payload["contract_version"] == "p2p-cli/v1", payload
    assert payload["ok"] is True, payload
    assert payload["operation"] == operation, payload
    data = payload["data"]
    assert isinstance(data, dict), payload
    result = data.get(data_key)
    assert isinstance(result, dict), payload
    assert result.get("contract") == data_contract, payload
    return result

def apply_choice_transition(
    project: Path,
    choice_id: str,
    transition: str,
    operation_key: str,
    *extra: str,
) -> None:
    common = (
        choice_id,
        "--transition", transition,
        "--reason", f"Qualify installed {transition} Choice read.",
        "--actor", "owner",
        "--operation-key", operation_key,
        *extra,
        "--format", "json",
        "--root", str(project),
    )
    preview = run_json("choice", "transition-preview", *common)
    token = preview["data"]["mutation"]["preview_token"]
    applied = run_json(
        "choice", "transition-apply", *common,
        "--preview-token", token,
        "--confirm",
    )
    assert applied["data"]["status"] == "applied", applied

version = run_json("version", "--format", "json")
assert version["ok"] is True
assert version["data"]["engine_version"] == expected_version

project = Path(tempfile.mkdtemp(prefix="project-", dir=Path.cwd()))
initialized = run_json(
    "init",
    "Installed Smoke",
    "--starter",
    "generic",
    "--agent",
    "generic",
    "--format",
    "json",
    "--operation-key",
    "installed-smoke-init-v1",
    "--root",
    str(project),
)
assert initialized["ok"] is True
assert not (project / ".git").exists()
assert not (project / ".gitignore").exists()

empty_choices = run_json(
    "choice", "list", "--limit", "50", "--offset", "0",
    "--format", "json", "--root", str(project),
)
empty_list = assert_choice_read(
    empty_choices,
    operation="choice.list",
    data_key="choice_list",
    data_contract="p2p-choice-list/v1",
)
assert empty_list["items"] == [], empty_choices

for title in ("Open frame", "Decided frame", "Withdrawn frame", "Historical frame"):
    run_text(
        "choice", "create",
        "--title", title,
        "--problem", f"Choose the installed-wheel direction for {title}.",
        "--context", "The candidate wheel must expose complete Choice reads.",
        "--governance-boundary", "The project owner decides after review.",
        "--option", "Keep current",
        "--option", "Adopt replacement",
        "--root", str(project),
    )

apply_choice_transition(
    project, "CHOICE-002", "decide", "installed-choice-read-decide",
    "--option", "B",
)
apply_choice_transition(
    project, "CHOICE-003", "withdraw", "installed-choice-read-withdraw",
)
apply_choice_transition(
    project, "CHOICE-004", "supersede", "installed-choice-read-supersede",
    "--replacement", "CHOICE-001",
)

format_option = (
    "--invalid-choice-read-option"
    if os.environ.get("P2P_TEST_FAILURE_MODE") == "invalid-choice-read"
    else "--format"
)
populated_choices = run_json(
    "choice", "list", "--limit", "50", "--offset", "0",
    "--format", "json", "--root", str(project),
)
populated_list = assert_choice_read(
    populated_choices,
    operation="choice.list",
    data_key="choice_list",
    data_contract="p2p-choice-list/v1",
)
assert len(populated_list["items"]) == 4, populated_choices

choice_list_payload = run_json(
    "choice", "list", "--limit", "1", "--offset", "1",
    format_option, "json", "--root", str(project),
)
choice_list = assert_choice_read(
    choice_list_payload,
    operation="choice.list",
    data_key="choice_list",
    data_contract="p2p-choice-list/v1",
)
assert choice_list["page"] == {
    "limit": 1,
    "offset": 1,
    "returned": 1,
    "has_more": True,
    "next_offset": 2,
}, choice_list_payload

for choice_id, state in (
    ("CHOICE-001", "open"),
    ("CHOICE-002", "decided"),
    ("CHOICE-003", "withdrawn"),
    ("CHOICE-004", "superseded"),
):
    choice_detail_payload = run_json(
        "choice", "show", choice_id, "--format", "json", "--root", str(project),
    )
    choice_detail = assert_choice_read(
        choice_detail_payload,
        operation="choice.show",
        data_key="choice_detail",
        data_contract="p2p-choice-detail/v1",
    )
    assert choice_detail["lifecycle"]["state"] == state, choice_detail_payload
    assert all(
        choice_detail["definition"].get(field)
        for field in ("problem", "context", "governance_boundary")
    ), choice_detail_payload
    assert ".p2p" not in json.dumps(choice_detail, sort_keys=True), choice_detail_payload

missing_choice = run_json(
    "choice", "show", "CHOICE-999", "--format", "json", "--root", str(project),
    expected_codes=(2,),
)
assert missing_choice["ok"] is False, missing_choice
assert missing_choice["operation"] == "choice.show", missing_choice
assert missing_choice["error"]["code"] == "P2P_CHOICE_NOT_FOUND", missing_choice

assert "Registries refreshed" in run_text("registry", "refresh", "--root", str(project))

for args in (
    ("runtime", "status", "--format", "json", "--root", str(project)),
    ("workspace", "schema", "status", "--format", "json", "--root", str(project)),
    ("validate", "--format", "json", "--root", str(project)),
):
    payload = run_json(*args)
    assert payload["ok"] is True
    assert payload["contract_version"] == "p2p-cli/v1"

drift = run_json(
    "drift", "status", "--format", "json", "--root", str(project)
)
assert drift["ok"] is True
assert drift["operation"] == "drift.status"
assert drift["data"]["replica_drift_status"]["status"] == "standalone"
assert drift["data"]["replica_drift_status"]["mutation_performed"] is False

bundled = run_json(
    "vertical",
    "inspect",
    "binarya/software_project@2.0.0",
    "--format",
    "json",
    "--root",
    str(project),
)
assert bundled["ok"] is True
assert bundled["operation"] == "vertical.inspect"
assert bundled["data"]["coordinate"] == "binarya/software_project@2.0.0"

portable_schema = run_json(
    "project",
    "vertical",
    "schema",
    "--format",
    "json",
    "--root",
    str(project),
)
assert portable_schema["ok"] is True
assert portable_schema["operation"] == "project.vertical.schema"
assert portable_schema["data"]["schema_version"] == 3
assert portable_schema["data"]["network_access"] is False

eligibility = run_json(
    "project",
    "vertical",
    "export",
    "eligibility",
    "--format",
    "json",
    "--root",
    str(project),
)
assert eligibility["ok"] is True
assert eligibility["operation"] == "project.vertical.export.eligibility"
assert "project_structure_export_eligibility" in eligibility["data"]

portable = run_json(
    "project",
    "vertical",
    "export",
    "preview",
    "--publisher",
    "example",
    "--id",
    "installed-smoke",
    "--version",
    "1.0.0",
    "--name",
    "Installed smoke",
    "--license",
    "MIT",
    "--primary-domain-key",
    "software",
    "--primary-domain-name",
    "Software",
    "--lineage-mode",
    "independent",
    "--format",
    "json",
    "--root",
    str(project),
)
assert portable["ok"] is True
assert portable["operation"] == "project.vertical.export.preview"
assert "project_structure_export_preview" in portable["data"]
PY

"$venv_root/bin/python" - "$smoke_root" <<'PY'
from pathlib import Path
import json
import os
import subprocess
import sys

root = Path(sys.argv[1])
requests = (
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
)
command = ["p2p-mcp-server", "--root", str(root)]
timeout = 20
if os.environ.get("P2P_TEST_FAILURE_MODE") == "mcp-timeout":
    command = [sys.executable, "-c", "import time; time.sleep(60)"]
    timeout = 0.05
completed = subprocess.run(
    command,
    input="".join(json.dumps(request) + "\n" for request in requests),
    check=False,
    capture_output=True,
    text=True,
    timeout=timeout,
)
assert completed.returncode == 0, (completed.returncode, completed.stderr)
responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
assert [response["id"] for response in responses] == [1, 2]
names = {tool["name"] for tool in responses[1]["result"]["tools"]}
assert "p2p_work_plan" in names
removed = {
    "p2p_sync_status",
    "p2p_sync_fetch",
    "p2p_sync_pull",
    "p2p_sync_push",
    "p2p_project_remote_show",
    "p2p_project_remote_configure",
    "p2p_proposal_draft_commit",
    "p2p_proposal_branch",
    "p2p_proposal_branch_status",
    "p2p_proposal_publish",
    "p2p_proposal_request_review",
    "p2p_proposal_accept_branch",
    "p2p_proposal_reject_branch",
    "p2p_proposal_merge",
    "p2p_proposal_finalize",
    "p2p_proposal_cleanup",
    "p2p_proposal_branch_scan",
    "p2p_work_branch",
    "p2p_work_submit",
    "p2p_work_review",
    "p2p_work_publish",
    "p2p_work_request_review",
    "p2p_work_accept",
    "p2p_work_finalize",
    "p2p_work_cleanup",
}
assert names.isdisjoint(removed)
assert "p2p_project_structure_export_apply" not in names
assert "p2p_project_structure_replacement_apply" not in names
assert "p2p_project_structure_merge_compare" in names
assert "p2p_project_structure_retained_inspect" in names
assert "p2p_project_structure_merge_apply" not in names
assert "p2p_project_structure_restore_apply" not in names
assert "p2p_replica_drift_status" in names
assert "p2p_replica_drift_diff" in names
assert "p2p_replica_drift_discard" not in names
assert "p2p_replica_reconciliation_apply" not in names
PY

"$venv_root/bin/python" -m pytest -m smoke "$script_root/tests" "${pytest_args[@]}"
[[ ! -s "$git_log" ]] || {
  printf '%s\n' "installed product invoked forbidden git sentinel" >&2
  exit 1
}
[[ ! -s "$network_log" ]] || {
  printf '%s\n' "installed product attempted forbidden outbound network access" >&2
  exit 1
}
printf 'installed wheel verified: %s\n' "$wheel_path"

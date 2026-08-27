#!/usr/bin/env bash
set -euo pipefail

candidate_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
output_dir="$candidate_root/dist"
diagnostic=false
while (($#)); do
  case "$1" in
    --diagnostic)
      diagnostic=true
      shift
      ;;
    --output)
      [[ $# -ge 2 ]] || { printf '%s\n' "--output requires a directory" >&2; exit 2; }
      output_dir="$2"
      shift 2
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

[[ -n "${SOURCE_DATE_EPOCH:-}" ]] || {
  printf '%s\n' "SOURCE_DATE_EPOCH is required for a reproducible candidate build" >&2
  exit 2
}
if [[ -e "$output_dir" ]] && find "$output_dir" -mindepth 1 -print -quit | grep -q .; then
  printf 'release output directory must be empty: %s\n' "$output_dir" >&2
  exit 2
fi

metadata_args=(--root "$candidate_root")
if [[ "$diagnostic" == false ]]; then
  metadata_args+=(--release)
fi
"$python_bin" "$candidate_root/scripts/verify-release-metadata.py" "${metadata_args[@]}"

build_root="$(mktemp -d /tmp/p2p-release-build.XXXXXX)"
cleanup() {
  rm -rf -- "$build_root"
}
trap cleanup EXIT INT TERM
first="$build_root/first"
second="$build_root/second"
candidate="$build_root/candidate"
mkdir -p "$first" "$second" "$candidate" "$output_dir"

cd "$candidate_root"
"$python_bin" -m build --outdir "$first"
"$python_bin" -m build --outdir "$second"

shopt -s nullglob
first_files=("$first"/*)
second_files=("$second"/*)
shopt -u nullglob
[[ ${#first_files[@]} -eq 2 && ${#second_files[@]} -eq 2 ]] || {
  printf '%s\n' "each clean build must produce exactly one wheel and one sdist" >&2
  exit 1
}

for artifact in "${first_files[@]}"; do
  name="$(basename -- "$artifact")"
  peer="$second/$name"
  [[ -f "$peer" ]] || { printf 'second build is missing %s\n' "$name" >&2; exit 1; }
  if ! cmp -s "$artifact" "$peer"; then
    "$python_bin" - "$artifact" "$peer" <<'PY'
from pathlib import Path
import hashlib
import sys
import tarfile
import zipfile

left, right = map(Path, sys.argv[1:])

def members(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                result[info.filename] = hashlib.sha256(archive.read(info)).hexdigest()
    else:
        with tarfile.open(path, "r:gz") as archive:
            for info in archive.getmembers():
                if info.isfile():
                    stream = archive.extractfile(info)
                    assert stream is not None
                    result[info.name] = hashlib.sha256(stream.read()).hexdigest()
    return result

a, b = members(left), members(right)
for name in sorted(set(a) | set(b)):
    if a.get(name) != b.get(name):
        print(f"non-reproducible member: {name}: {a.get(name)} != {b.get(name)}")
PY
    printf 'non-reproducible artifact: %s\n' "$name" >&2
    exit 1
  fi
  cp -- "$artifact" "$candidate/$name"
done

"$python_bin" scripts/verify-release-artifacts.py --dist "$candidate"
(
  cd "$candidate"
  sha256sum p2p_engine-*.whl p2p_engine-*.tar.gz | LC_ALL=C sort -k2 > SHA256SUMS
)
cp -- "$candidate"/* "$output_dir"/
if [[ "$diagnostic" == true ]]; then
  printf 'reproducible diagnostic artifacts created in %s; not release-authorized\n' "$output_dir"
else
  printf 'reproducible release artifacts created in %s\n' "$output_dir"
fi

#!/usr/bin/env bash
set -euo pipefail

tag=""
target=""
dist_dir="dist"
notes_file=""
dry_run=false
while (($#)); do
  case "$1" in
    --tag) tag="$2"; shift 2 ;;
    --target) target="$2"; shift 2 ;;
    --dist) dist_dir="$2"; shift 2 ;;
    --notes) notes_file="$2"; shift 2 ;;
    --dry-run) dry_run=true; shift ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  printf 'invalid or missing release tag: %s\n' "$tag" >&2
  exit 2
}
[[ "$target" =~ ^[0-9a-fA-F]{40}$ ]] || {
  printf 'invalid or missing release target: %s\n' "$target" >&2
  exit 2
}
version="${tag#v}"
wheel="$dist_dir/p2p_engine-${version}-py3-none-any.whl"
sdist="$dist_dir/p2p_engine-${version}.tar.gz"
checksums="$dist_dir/SHA256SUMS"
for artifact in "$wheel" "$sdist" "$checksums"; do
  [[ -f "$artifact" ]] || { printf 'missing exact release artifact: %s\n' "$artifact" >&2; exit 2; }
done
[[ -n "$notes_file" && -f "$notes_file" ]] || {
  printf 'release notes file is required\n' >&2
  exit 2
}

gh_bin="${GH_BIN:-gh}"
repo="${GITHUB_REPOSITORY:-}"
repo_args=()
if [[ -n "$repo" ]]; then
  repo_args=(--repo "$repo")
fi
if "$gh_bin" release view "$tag" "${repo_args[@]}" >/dev/null 2>&1; then
  printf 'release already exists; create-only publication refused: %s\n' "$tag" >&2
  exit 1
fi
tag_api="repos/{owner}/{repo}/git/ref/tags/$tag"
if [[ -n "$repo" ]]; then
  tag_api="repos/$repo/git/ref/tags/$tag"
fi
if "$gh_bin" api "$tag_api" >/dev/null 2>&1; then
  printf 'tag already exists; create-only publication refused: %s\n' "$tag" >&2
  exit 1
fi

command=(
  "$gh_bin" release create "$tag"
  "$wheel" "$sdist" "$checksums"
  "${repo_args[@]}"
  --target "$target"
  --title "P2P Engine $tag"
  --notes-file "$notes_file"
)
if [[ "$dry_run" == true ]]; then
  printf 'create-only release command:'
  printf ' %q' "${command[@]}"
  printf '\n'
  exit 0
fi
"${command[@]}"

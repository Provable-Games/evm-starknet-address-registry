#!/usr/bin/env bash
set -euo pipefail

runtime=.github/review/runtime
install_options=(--registry=https://registry.npmjs.org --ignore-scripts --include=optional --no-audit --no-fund)

case "${1:-}" in
  resolve)
    resolve_dir=$(mktemp -d)
    trap 'rm -rf -- "$resolve_dir"' EXIT
    cp "$runtime/package.json" "$resolve_dir/package.json"
    npm install --prefix "$resolve_dir" --package-lock-only --prefer-online "${install_options[@]}"
    cp "$resolve_dir/package-lock.json" "${2:?Specify the generated lockfile path}"
    ;;
  install)
    cp "${2:?Specify the resolved lockfile path}" "$runtime/package-lock.json"
    npm ci --prefix "$runtime" "${install_options[@]}"
    node "$runtime/node_modules/@anthropic-ai/claude-code/install.cjs"
    "$runtime/node_modules/.bin/codex" --version
    "$runtime/node_modules/.bin/claude" --version
    ;;
  *)
    printf 'Usage: %s {resolve|install} <lockfile>\n' "$0" >&2
    exit 2
    ;;
esac

#!/usr/bin/env bash
# Prune GHCR versions and GitHub releases (dry run by default).
# Usage: ./scripts/cleanup-registry.sh [--apply]
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
args=(python3 scripts/registry_cleanup.py)
if [[ "${1:-}" == "--apply" ]]; then
  args+=(--apply)
fi
exec "${args[@]}"

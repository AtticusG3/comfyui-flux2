#!/usr/bin/env bash
# Push to Gitea using GITEA_TOKEN from the environment (no token in git remote).
# Usage: scripts/gitea-push.sh [ref ...]   e.g. scripts/gitea-push.sh main v1.5.0
# Env: GITEA_TOKEN (required). GITEA_USER (default: kevyn). GITEA_HOST (default: git.kevynwatkins.com).
#      GITEA_REPO_PATH (default: kevyn/comfyui-flux2).

set -euo pipefail
if [[ -z "${GITEA_TOKEN:-}" ]]; then
  echo "[ERROR] GITEA_TOKEN is not set." >&2
  exit 1
fi
USER="${GITEA_USER:-kevyn}"
HOST="${GITEA_HOST:-git.kevynwatkins.com}"
REPO_PATH="${GITEA_REPO_PATH:-kevyn/comfyui-flux2}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PUSH_URL="https://${USER}:${GITEA_TOKEN}@${HOST}/${REPO_PATH}.git"
if [[ $# -eq 0 ]]; then
  BR="$(git symbolic-ref -q --short HEAD || true)"
  if [[ -z "$BR" ]]; then
    echo "[ERROR] Not on a branch; pass ref(s), e.g. scripts/gitea-push.sh main" >&2
    exit 1
  fi
  set -- "$BR"
fi
git push "$PUSH_URL" "$@"

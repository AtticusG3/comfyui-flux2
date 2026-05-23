#!/bin/bash
# Shared staged git clone-or-update. Source after defining git_sync_run (and
# optionally provider_for_url). On fetch failure the live target dir is left untouched.

GIT_STAGING_ROOT="${GIT_STAGING_ROOT:-/tmp/git-staging}"
GIT_SYNC_RETRIES="${GIT_SYNC_RETRIES:-3}"

if ! declare -f git_sync_run >/dev/null 2>&1; then
    git_sync_run() {
        shift
        git "$@"
    }
fi

if ! declare -f provider_for_url >/dev/null 2>&1; then
    provider_for_url() {
        echo "github"
    }
fi

_git_sync_hash_url() {
    printf '%s' "$1" | sha256sum | awk '{print substr($1, 1, 16)}'
}

_git_sync_use_shallow() {
    local dir="$1"
    local name
    name=$(basename "$dir")
    if [ "$name" == "ComfyUI" ]; then
        echo "false"
        return 0
    fi
    case "${GIT_SYNC_SHALLOW:-true}" in
        true|1|yes) echo "true" ;;
        *) echo "false" ;;
    esac
}

_git_sync_clone_args() {
    local shallow="$1"
    local branch="$2"
    local args=(--recurse-submodules)
    if [ "$shallow" == "true" ]; then
        args+=(--depth 1)
    fi
    if [ -n "$branch" ]; then
        args+=(-b "$branch")
    fi
    printf '%s\n' "${args[@]}"
}

_git_sync_with_retries() {
    local attempt=1
    local max="$GIT_SYNC_RETRIES"
    while [ "$attempt" -le "$max" ]; do
        if "$@"; then
            return 0
        fi
        if [ "$attempt" -lt "$max" ]; then
            echo "[WARN] Git sync attempt $attempt/$max failed; retrying in ${attempt}s..."
            sleep "$attempt"
        fi
        attempt=$((attempt + 1))
    done
    return 1
}

_git_sync_update_staging() {
    local staging="$1"
    local url="$2"
    local branch="$3"
    local shallow="$4"
    local provider="$5"
    local name
    name=$(basename "$staging")

    rm -rf "$staging"
    mkdir -p "$staging"

    local clone_args=()
    while IFS= read -r arg; do
        [ -n "$arg" ] && clone_args+=("$arg")
    done < <(_git_sync_clone_args "$shallow" "$branch")

    echo "[INFO] Staging clone ${name}..."
    if ! _git_sync_with_retries git_sync_run "$provider" clone "${clone_args[@]}" "$url" "$staging"; then
        return 1
    fi

    cd "$staging"
    git_sync_run "$provider" submodule update --init --recursive
    cd - >/dev/null
    return 0
}

_git_sync_rsync_excludes_for_target() {
    local target="$1"
    local name
    name=$(basename "$target")

    # docker-compose bind-mounts under /app/ComfyUI; rsync --delete cannot replace mount points.
    if [ "$name" = "ComfyUI" ]; then
        printf '%s\n' \
            'models/' \
            'input/' \
            'output/' \
            'user/default/workflows/'
    fi

    if [ -n "${GIT_SYNC_RSYNC_EXTRA_EXCLUDES:-}" ]; then
        local item
        IFS=',' read -ra _extra <<< "${GIT_SYNC_RSYNC_EXTRA_EXCLUDES}"
        for item in "${_extra[@]}"; do
            item=$(echo "$item" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            [ -n "$item" ] && printf '%s\n' "$item"
        done
    fi
}

_git_sync_apply_staging() {
    local staging="$1"
    local target="$2"
    local name
    name=$(basename "$target")

    mkdir -p "$(dirname "$target")"
    if [ ! -d "$target" ]; then
        mkdir -p "$target"
    fi

    if command -v rsync >/dev/null 2>&1; then
        local -a rsync_args=(-a --no-group --no-owner --delete)
        local exclude
        while IFS= read -r exclude; do
            [ -n "$exclude" ] && rsync_args+=(--exclude="$exclude")
        done < <(_git_sync_rsync_excludes_for_target "$target")
        if ! rsync "${rsync_args[@]}" "$staging/" "$target/"; then
            echo "[WARN] rsync reported errors applying staged ${name} (bind mounts or permissions may be expected on some hosts)."
        fi
    else
        find "$target" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} + 2>/dev/null || true
        cp -a "$staging"/. "$target/"
    fi
    echo "[OK] Applied staged sync to ${name}."
}

_git_sync_target_matches_remote() {
    local target="$1"
    local url="$2"
    local branch="$3"
    local provider="$4"

    [ -d "${target}/.git" ] || return 1
    [ -n "$branch" ] || return 1

    cd "$target"
    if ! git_sync_run "$provider" remote get-url origin >/dev/null 2>&1; then
        cd - >/dev/null
        return 1
    fi
    if ! git_sync_run "$provider" rev-parse --verify "origin/${branch}" >/dev/null 2>&1; then
        cd - >/dev/null
        return 1
    fi
    local head remote
    head=$(git_sync_run "$provider" rev-parse HEAD 2>/dev/null || echo "")
    remote=$(git_sync_run "$provider" rev-parse "origin/${branch}" 2>/dev/null || echo "")
    cd - >/dev/null
    [ -n "$head" ] && [ "$head" = "$remote" ]
}

# Idempotent clone-or-update with staging for atomic apply.
clone_or_update() {
    local dir="$1"
    local url="$2"
    local branch="${3:-}"
    local name
    name=$(basename "$dir")
    local provider
    provider=$(provider_for_url "$url")
    local shallow
    shallow=$(_git_sync_use_shallow "$dir")
    local staging="${GIT_STAGING_ROOT}/$(_git_sync_hash_url "$url")"

    if [ -e "${dir}/.git" ] && [ ! -r "${dir}/.git" ]; then
        if declare -f fix_permissions >/dev/null 2>&1; then
            fix_permissions "$dir"
        elif command -v sudo >/dev/null 2>&1; then
            sudo chown -R "$(id -u):$(id -g)" "${dir}/.git" 2>/dev/null || true
        fi
    fi

    local git_update_lc
    git_update_lc=$(echo "${COMFYUI_GIT_UPDATE:-true}" | tr '[:upper:]' '[:lower:]')
    if [ "$git_update_lc" != "true" ] && [ -n "$branch" ] && [ -d "$dir" ]; then
        if _git_sync_target_matches_remote "$dir" "$url" "$branch" "$provider"; then
            echo "[OK] ${name} already matches origin/${branch}; skipping git fetch (COMFYUI_GIT_UPDATE=false)."
            return 0
        fi
    fi

    mkdir -p "$GIT_STAGING_ROOT"
    if ! _git_sync_update_staging "$staging" "$url" "$branch" "$shallow" "$provider"; then
        echo "[WARN] Failed to stage ${name} from ${url}; leaving ${dir} unchanged."
        return 1
    fi

    if ! _git_sync_apply_staging "$staging" "$dir"; then
        echo "[WARN] Failed to apply staged ${name} to ${dir}."
        return 1
    fi

    return 0
}

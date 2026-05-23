#!/bin/bash

set -euo pipefail

COMFYUI_DIR="${COMFYUI_DIR:-/app/ComfyUI}"
CUSTOM_NODES_DIR="${CUSTOM_NODES_DIR:-${COMFYUI_DIR}/custom_nodes}"
COMFYUI_BRANCH="${COMFYUI_BRANCH:-master}"
PACKS_DIR="${PACKS_DIR:-/scripts/packs}"
INSTALL_VRAM_UTILS="${INSTALL_VRAM_UTILS:-false}"
COPY_BUNDLED_WORKFLOWS="${COPY_BUNDLED_WORKFLOWS:-true}"
GIT_STAGING_ROOT="${GIT_STAGING_ROOT:-/tmp/git-staging}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/git_sync.sh
source "${SCRIPT_DIR}/lib/git_sync.sh"

install_filtered_reqs() {
    local req="$1"
    local label="$2"
    if [ ! -f "$req" ]; then
        return 0
    fi

    local filtered_req
    filtered_req=$(mktemp)
    grep -Ev '^[[:space:]]*(torch|torchvision|torchaudio|xformers)([=<>~! ]|$)' "$req" > "$filtered_req" || true
    if [ ! -s "$filtered_req" ]; then
        echo "[OK] No installable requirements for $label."
        rm -f "$filtered_req"
        return 0
    fi

    echo "[INFO] Installing $label requirements..."
    uv pip install -r "$filtered_req" || echo "[WARN] Some deps from $req may have failed"
    rm -f "$filtered_req"
}

install_comfyui_core() {
    mkdir -p "$CUSTOM_NODES_DIR"

    if ! clone_or_update "$COMFYUI_DIR" "https://github.com/Comfy-Org/ComfyUI.git" "$COMFYUI_BRANCH"; then
        echo "[ERROR] ComfyUI bootstrap sync failed."
        return 1
    fi
    install_filtered_reqs "${COMFYUI_DIR}/requirements.txt" "ComfyUI"

    if ! clone_or_update "${CUSTOM_NODES_DIR}/ComfyUI-Manager" "https://github.com/ltdrdata/ComfyUI-Manager.git" "main"; then
        echo "[ERROR] ComfyUI-Manager bootstrap sync failed."
        return 1
    fi
    install_filtered_reqs "${CUSTOM_NODES_DIR}/ComfyUI-Manager/requirements.txt" "ComfyUI-Manager"
}

install_vram_utils_nodes() {
    local nodes_file="${PACKS_DIR}/vram-utils/nodes.txt"
    if [ ! -s "$nodes_file" ]; then
        echo "[WARN] vram-utils nodes list not found: $nodes_file"
        return 0
    fi

    echo "[INFO] Installing vram-utils bootstrap custom nodes..."
    local line git_url repo_name repo_branch target_dir
    while IFS= read -r line || [ -n "$line" ]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue
        git_url=$(echo "$line" | awk '{print $1}')
        if [[ "$git_url" =~ ^https://|^git:// ]]; then
            repo_name=$(basename "$git_url" .git)
            repo_branch=$(echo "$line" | awk '{print $2}')
            target_dir="${CUSTOM_NODES_DIR}/${repo_name}"
            if clone_or_update "$target_dir" "$git_url" "$repo_branch"; then
                install_filtered_reqs "${target_dir}/requirements.txt" "$repo_name"
            else
                echo "[ERROR] Failed to sync $repo_name during bootstrap; continuing."
            fi
        fi
    done < "$nodes_file"
}

copy_bundled_workflows() {
    if [ "$COPY_BUNDLED_WORKFLOWS" != "true" ]; then
        return 0
    fi

    local workflows_dir="${COMFYUI_DIR}/user/default/workflows"
    mkdir -p "$workflows_dir"
    if [ -d "/workflows" ] && [ -n "$(ls -A /workflows/ 2>/dev/null)" ]; then
        cp -R /workflows/* "$workflows_dir/"
        echo "[INFO] Bundled workflows copied."
    else
        echo "[INFO] No bundled workflows to copy."
    fi
}

main() {
    echo "########################################"
    echo "[INFO] Installing ComfyUI & extensions..."
    echo "########################################"

    uv pip install --upgrade pip
    install_comfyui_core
    if [ "$INSTALL_VRAM_UTILS" == "true" ]; then
        install_vram_utils_nodes
    fi
    copy_bundled_workflows

    if [ -d /app ]; then
        touch /app/.download-complete 2>/dev/null || true
    fi
    echo "[INFO] Installation complete."
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi

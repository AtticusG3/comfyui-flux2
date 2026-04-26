#!/bin/bash

echo "########################################"
echo "[INFO] Installing ComfyUI & extensions..."
echo "########################################"

set -euo pipefail

COMFYUI_DIR="/app/ComfyUI"
CUSTOM_NODES_DIR="${COMFYUI_DIR}/custom_nodes"
COMFYUI_BRANCH="master"

clone_or_update() {
    local dir="$1"
    local url="$2"
    local branch="$3"
    local name
    name=$(basename "$dir")

    if [ -d "${dir}/.git" ]; then
        echo "[INFO] Updating ${name}..."
        cd "$dir"
        if git remote get-url origin >/dev/null 2>&1; then
            git remote set-url origin "$url"
        else
            git remote add origin "$url"
        fi
        git fetch origin "$branch"
        git reset --hard "origin/${branch}"
        git submodule update --init --recursive
    elif [ -d "$dir" ]; then
        echo "[INFO] Initializing ${name} in existing directory..."
        cd "$dir"
        git init -b "$branch"
        git remote add origin "$url"
        git fetch origin "$branch"
        git reset --hard "origin/${branch}"
        git submodule update --init --recursive
    else
        echo "[INFO] Cloning ${name}..."
        git clone --recurse-submodules -b "$branch" "$url" "$dir"
    fi
}

# Clone or init ComfyUI into potentially pre-existing directory (volume mount).
# The directory may already exist as an empty named-volume mount point with
# bind-mount subdirectories (models/, input/, output/, etc.) inside it.
# git clone would fail on a non-empty directory, so we use git init instead.
clone_or_update "$COMFYUI_DIR" "https://github.com/Comfy-Org/ComfyUI.git" "$COMFYUI_BRANCH"

if [ -f "${COMFYUI_DIR}/requirements.txt" ]; then
    echo "[INFO] Installing ComfyUI requirements..."
    grep -Ev '^[[:space:]]*(torch|torchvision|torchaudio|xformers)([=<>~! ]|$)' "${COMFYUI_DIR}/requirements.txt" > /tmp/comfyui-requirements.filtered || true
    uv pip install -r /tmp/comfyui-requirements.filtered || echo "[WARN] Some ComfyUI deps may have failed"
    rm -f /tmp/comfyui-requirements.filtered
fi

# ComfyUI-Manager (sub-path of volume, not a mount point itself)
mkdir -p "$CUSTOM_NODES_DIR"
clone_or_update "${CUSTOM_NODES_DIR}/ComfyUI-Manager" "https://github.com/ltdrdata/ComfyUI-Manager.git" "main"
if [ -f "${CUSTOM_NODES_DIR}/ComfyUI-Manager/requirements.txt" ]; then
    echo "[INFO] Installing ComfyUI-Manager requirements..."
    grep -Ev '^[[:space:]]*(torch|torchvision|torchaudio|xformers)([=<>~! ]|$)' "${CUSTOM_NODES_DIR}/ComfyUI-Manager/requirements.txt" > /tmp/manager-requirements.filtered || true
    uv pip install -r /tmp/manager-requirements.filtered || echo "[WARN] Some Manager deps may have failed"
    rm -f /tmp/manager-requirements.filtered
fi

# Civicomfy (Civitai model downloader)
clone_or_update "${CUSTOM_NODES_DIR}/Civicomfy" "https://github.com/MoonGoblinDev/Civicomfy.git" "main"
if [ -f "${CUSTOM_NODES_DIR}/Civicomfy/requirements.txt" ]; then
    echo "[INFO] Installing Civicomfy requirements..."
    grep -Ev '^[[:space:]]*(torch|torchvision|torchaudio|xformers)([=<>~! ]|$)' "${CUSTOM_NODES_DIR}/Civicomfy/requirements.txt" > /tmp/civicomfy-requirements.filtered || true
    uv pip install -r /tmp/civicomfy-requirements.filtered || echo "[WARN] Some Civicomfy deps may have failed"
    rm -f /tmp/civicomfy-requirements.filtered
fi

# Copy bundled workflows
WORKFLOWS_DIR="${COMFYUI_DIR}/user/default/workflows"
mkdir -p "$WORKFLOWS_DIR"

if [ -d "/workflows" ] && [ -n "$(ls -A /workflows/ 2>/dev/null)" ]; then
    cp -R /workflows/* "$WORKFLOWS_DIR/"
    echo "[INFO] Bundled workflows copied."
else
    echo "[INFO] No bundled workflows to copy."
fi

touch /app/.download-complete
echo "[INFO] Installation complete."

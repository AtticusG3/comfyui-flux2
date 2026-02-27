#!/bin/bash

echo "########################################"
echo "[INFO] Installing ComfyUI & extensions..."
echo "########################################"

set -euo pipefail

COMFYUI_DIR="/app/ComfyUI"
CUSTOM_NODES_DIR="${COMFYUI_DIR}/custom_nodes"

# Clone or init ComfyUI into potentially pre-existing directory (volume mount).
# The directory may already exist as an empty named-volume mount point with
# bind-mount subdirectories (models/, input/, output/, etc.) inside it.
# git clone would fail on a non-empty directory, so we use git init instead.
cd "$COMFYUI_DIR"
if [ ! -d ".git" ]; then
    echo "[INFO] Initializing ComfyUI repo in existing directory..."
    git init
    git remote add origin https://github.com/Comfy-Org/ComfyUI.git
    git fetch origin main
    git reset --hard origin/main
    git submodule update --init --recursive
else
    echo "[INFO] ComfyUI repo already initialized, updating..."
    git fetch origin main
    git reset --hard origin/main
fi

if [ -f "${COMFYUI_DIR}/requirements.txt" ]; then
    echo "[INFO] Installing ComfyUI requirements..."
    uv pip install -r "${COMFYUI_DIR}/requirements.txt" || echo "[WARN] Some ComfyUI deps may have failed"
fi

# ComfyUI-Manager (sub-path of volume, not a mount point itself)
mkdir -p "$CUSTOM_NODES_DIR"
if [ ! -d "${CUSTOM_NODES_DIR}/ComfyUI-Manager" ]; then
    echo "[INFO] Cloning ComfyUI-Manager..."
    git clone --recurse-submodules \
        https://github.com/ltdrdata/ComfyUI-Manager.git \
        "${CUSTOM_NODES_DIR}/ComfyUI-Manager"
else
    echo "[INFO] ComfyUI-Manager already present."
fi
if [ -f "${CUSTOM_NODES_DIR}/ComfyUI-Manager/requirements.txt" ]; then
    echo "[INFO] Installing ComfyUI-Manager requirements..."
    uv pip install -r "${CUSTOM_NODES_DIR}/ComfyUI-Manager/requirements.txt" || echo "[WARN] Some Manager deps may have failed"
fi

# Civicomfy (Civitai model downloader)
if [ ! -d "${CUSTOM_NODES_DIR}/Civicomfy" ]; then
    echo "[INFO] Cloning Civicomfy..."
    git clone https://github.com/MoonGoblinDev/Civicomfy.git \
        "${CUSTOM_NODES_DIR}/Civicomfy"
else
    echo "[INFO] Civicomfy already present."
fi
if [ -f "${CUSTOM_NODES_DIR}/Civicomfy/requirements.txt" ]; then
    echo "[INFO] Installing Civicomfy requirements..."
    uv pip install -r "${CUSTOM_NODES_DIR}/Civicomfy/requirements.txt" || echo "[WARN] Some Civicomfy deps may have failed"
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

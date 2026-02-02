#!/bin/bash

set -e

# Ensure correct permissions for /app directory
if [ ! -w "/app" ]; then
    echo "Warning: Cannot write to /app. Attempting to fix permissions..."
    sudo chown -R $(id -u):$(id -g) /app
fi

# Install or update ComfyUI
cd /app
if [ ! -d "/app/ComfyUI" ]; then
    echo "ComfyUI not found. Installing..."
    chmod +x /scripts/install_comfyui.sh
    bash /scripts/install_comfyui.sh
else
    echo "Updating ComfyUI..."
    cd /app/ComfyUI
    git fetch origin master
    git reset --hard origin/master
    uv pip install -r requirements.txt
    echo "Updating ComfyUI-Manager..."
    cd /app/ComfyUI/custom_nodes/ComfyUI-Manager
    git fetch origin main
    git reset --hard origin/main
    uv pip install -r requirements.txt
    cd /app
fi

# Download workflows based on model option
WORKFLOWS_DIR="/app/ComfyUI/user/default/workflows"
mkdir -p "$WORKFLOWS_DIR"
cd /app

if [ "$HUNYUAN3D" == "true" ]; then
    echo "########################################"
    echo "[INFO] Downloading Hunyuan3D-2 workflows..."
    echo "########################################"
    aria2c --input-file=/scripts/workflows_hunyuan3d.txt \
        --allow-overwrite=true --auto-file-renaming=false --continue=true \
        --max-connection-per-server=5 --conditional-get=true
else
    echo "########################################"
    echo "[INFO] Downloading Flux.2 Klein workflows..."
    echo "########################################"
    aria2c --input-file=/scripts/workflows.txt \
        --allow-overwrite=true --auto-file-renaming=false --continue=true \
        --max-connection-per-server=5 --conditional-get=true
fi

# Determine model list file based on HUNYUAN3D or LOW_VRAM
if [ "$HUNYUAN3D" == "true" ]; then
    echo "[INFO] HUNYUAN3D is set to true. Downloading Hunyuan3D-2 models..."
    MODEL_LIST_FILE="/scripts/models_hunyuan3d.txt"
    TEMP_MODEL_LIST=$(mktemp)
    cp "$MODEL_LIST_FILE" "$TEMP_MODEL_LIST"
else
    if [ "$LOW_VRAM" == "true" ]; then
        echo "[INFO] LOW_VRAM is set to true. Downloading Flux.2 Klein 4B models..."
        MODEL_LIST_FILE="/scripts/models_fp8.txt"
    else
        echo "[INFO] LOW_VRAM is not set or false. Downloading Flux.2 Klein 9B models..."
        MODEL_LIST_FILE="/scripts/models.txt"
    fi

# Create temporary file for model list (only for Flux path)
if [ "$HUNYUAN3D" != "true" ]; then
    TEMP_MODEL_LIST=$(mktemp)
fi

# Filter models based on MODELS_DOWNLOAD if set (Flux only)
if [ "$HUNYUAN3D" != "true" ] && [ -n "${MODELS_DOWNLOAD}" ]; then
    echo "[INFO] Filtering models based on MODELS_DOWNLOAD=${MODELS_DOWNLOAD}"

    # Convert to lowercase for case-insensitive matching
    MODELS_DOWNLOAD_LC=$(echo "$MODELS_DOWNLOAD" | tr '[:upper:]' '[:lower:]')

    if [ "$LOW_VRAM" == "true" ]; then
        # For 4B models, copy dependencies first
        sed -n '/# Flux.2 Klein 4B Dependencies/,/# End Dependencies/p' "$MODEL_LIST_FILE" >> "$TEMP_MODEL_LIST"

        # Then add requested models
        if [[ "$MODELS_DOWNLOAD_LC" == *"klein-base"* ]]; then
            sed -n '/# Flux.2 Klein 4B Base (FP8)/,/^$/p' "$MODEL_LIST_FILE" >> "$TEMP_MODEL_LIST"
        fi
        if [[ "$MODELS_DOWNLOAD_LC" == *"klein-distilled"* ]]; then
            sed -n '/# Flux.2 Klein 4B Distilled (FP8)/,/^$/p' "$MODEL_LIST_FILE" >> "$TEMP_MODEL_LIST"
        fi
    else
        # For 9B models, copy dependencies first
        sed -n '/# Flux.2 Klein 9B Dependencies/,/# End Dependencies/p' "$MODEL_LIST_FILE" >> "$TEMP_MODEL_LIST"

        # Then add requested models
        if [[ "$MODELS_DOWNLOAD_LC" == *"klein-base"* ]]; then
            sed -n '/# Flux.2 Klein 9B Base (FP8)/,/^$/p' "$MODEL_LIST_FILE" >> "$TEMP_MODEL_LIST"
        fi
        if [[ "$MODELS_DOWNLOAD_LC" == *"klein-distilled"* ]]; then
            sed -n '/# Flux.2 Klein 9B Distilled (FP8)/,/^$/p' "$MODEL_LIST_FILE" >> "$TEMP_MODEL_LIST"
        fi
    fi

    # If the temp file is empty (invalid MODELS_DOWNLOAD value), use the full list
    if [ ! -s "$TEMP_MODEL_LIST" ]; then
        echo "[WARN] No models matched MODELS_DOWNLOAD value. Using complete model list."
        cp "$MODEL_LIST_FILE" "$TEMP_MODEL_LIST"
    fi
elif [ "$HUNYUAN3D" != "true" ]; then
    # If MODELS_DOWNLOAD not set (Flux path), use the complete list
    cp "$MODEL_LIST_FILE" "$TEMP_MODEL_LIST"
fi

# Download models
echo "########################################"
echo "[INFO] Downloading models..."
echo "########################################"

if [ -z "${HF_TOKEN}" ]; then
    echo "[WARN] HF_TOKEN not provided. Skipping models that require authentication..."
    sed '/# Requires HF_TOKEN/,/^$/d' "$TEMP_MODEL_LIST" > /scripts/models_filtered.txt
    DOWNLOAD_LIST_FILE="/scripts/models_filtered.txt"
else
    DOWNLOAD_LIST_FILE="$TEMP_MODEL_LIST"
fi

aria2c --input-file="$DOWNLOAD_LIST_FILE" \
    --allow-overwrite=false --auto-file-renaming=false --continue=true \
    --max-connection-per-server=5 --conditional-get=true \
    ${HF_TOKEN:+--header="Authorization: Bearer ${HF_TOKEN}"}

# Cleanup
rm -f "$TEMP_MODEL_LIST"

echo "########################################"
echo "[INFO] Starting ComfyUI..."
echo "########################################"

export PATH="${PATH}:/app/.local/bin"
export PYTHONPYCACHEPREFIX="/app/.cache/pycache"

cd /app

python3 ./ComfyUI/main.py --listen --port 8188 ${CLI_ARGS}

#!/bin/bash

set -e

# =============================================================================
# Permission Fixes for Docker Volumes
# =============================================================================
# Docker named volumes and bind mounts may have incorrect ownership from
# previous runs (e.g., created as root). Fix ownership recursively before
# any git operations.

fix_permissions() {
    local dir="$1"
    if [ -d "$dir" ] && [ ! -w "$dir" ]; then
        echo "[INFO] Fixing permissions on $dir..."
        sudo chown -R "$(id -u):$(id -g)" "$dir"
    fi
    # Also check for .git directory specifically (common permission issue)
    if [ -d "${dir}/.git" ] && [ ! -r "${dir}/.git" ]; then
        echo "[INFO] Fixing permissions on ${dir}/.git..."
        sudo chown -R "$(id -u):$(id -g)" "${dir}/.git"
    fi
}

# Fix /app first
if [ ! -w "/app" ]; then
    echo "[INFO] Fixing permissions on /app..."
    sudo chown -R "$(id -u):$(id -g)" /app
fi

# Fix ComfyUI directory if it exists (Docker volume mount point)
fix_permissions "/app/ComfyUI"

# =============================================================================
# Main Entrypoint Logic
# =============================================================================

# Idempotent clone-or-update helper.
# Handles three cases: existing git repo, pre-existing directory without
# .git (e.g. Docker volume mount point), or directory does not exist.
clone_or_update() {
    local dir="$1"
    local url="$2"
    local branch="${3:-}"
    local name
    name=$(basename "$dir")

    # Fix permissions if .git exists but is not accessible
    if [ -e "${dir}/.git" ] && [ ! -r "${dir}/.git" ]; then
        echo "[INFO] Fixing permissions on ${dir}/.git..."
        sudo chown -R "$(id -u):$(id -g)" "${dir}/.git"
    fi

    if [ -d "${dir}/.git" ]; then
        echo "[INFO] Updating ${name}..."
        cd "$dir"
        # Ensure remote is configured (handles partially initialized repos)
        if git remote get-url origin >/dev/null 2>&1; then
            git remote set-url origin "$url"
        else
            git remote add origin "$url"
        fi
        if [ -n "$branch" ]; then
            git fetch origin "$branch"
            git reset --hard "origin/${branch}"
        else
            git fetch origin
            default_branch=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)
            default_branch=${default_branch:-main}
            git reset --hard "origin/${default_branch}"
        fi
        git submodule update --init --recursive
    elif [ -d "$dir" ]; then
        echo "[INFO] Initializing ${name} in existing directory..."
        cd "$dir"
        if [ -n "$branch" ]; then
            git init -b "$branch"
        else
            git init
        fi
        git remote add origin "$url"
        if [ -n "$branch" ]; then
            git fetch origin "$branch"
            git reset --hard "origin/${branch}"
        else
            git fetch origin
            default_branch=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)
            default_branch=${default_branch:-main}
            git reset --hard "origin/${default_branch}"
        fi
        git submodule update --init --recursive
    else
        echo "[INFO] Cloning ${name}..."
        if [ -n "$branch" ]; then
            git clone --recurse-submodules -b "$branch" "$url" "$dir"
        else
            git clone --recurse-submodules "$url" "$dir"
        fi
    fi
    cd /app
}

# Install requirements if present
install_reqs() {
    local req="$1"
    if [ -f "$req" ]; then
        local filtered_req
        filtered_req=$(mktemp)
        grep -Ev '^[[:space:]]*(torch|torchvision|torchaudio|xformers)([=<>~! ]|$)' "$req" > "$filtered_req" || true
        uv pip install -r "$filtered_req" || echo "[WARN] Some deps from $req may have failed"
        rm -f "$filtered_req"
    fi
}

# Install requirements for every existing custom node directory.
# This covers nodes added outside pack metadata (e.g. manually installed repos).
install_all_custom_node_reqs() {
    local root="$1"
    if [ ! -d "$root" ]; then
        return 0
    fi

    echo "[INFO] Installing requirements for all detected custom nodes..."
    local req
    while IFS= read -r req; do
        install_reqs "$req"
    done < <(find "$root" -mindepth 2 -maxdepth 2 -type f -name "requirements.txt" | sort)
}

cd /app

COMFYUI_DIR="/app/ComfyUI"
CUSTOM_NODES_DIR="${COMFYUI_DIR}/custom_nodes"

# ComfyUI
clone_or_update "$COMFYUI_DIR" "https://github.com/Comfy-Org/ComfyUI.git" "master"
install_reqs "${COMFYUI_DIR}/requirements.txt"

# ComfyUI-Manager
mkdir -p "$CUSTOM_NODES_DIR"
clone_or_update "${CUSTOM_NODES_DIR}/ComfyUI-Manager" "https://github.com/ltdrdata/ComfyUI-Manager.git" "main"
install_reqs "${CUSTOM_NODES_DIR}/ComfyUI-Manager/requirements.txt"

# Civicomfy (Civitai model downloader)
clone_or_update "${CUSTOM_NODES_DIR}/Civicomfy" "https://github.com/MoonGoblinDev/Civicomfy.git" "main"
install_reqs "${CUSTOM_NODES_DIR}/Civicomfy/requirements.txt"

# Install requirements for any custom node already present in custom_nodes/.
install_all_custom_node_reqs "$CUSTOM_NODES_DIR"

# Copy bundled workflows into ComfyUI
BUNDLED_WORKFLOWS="/workflows"
DEST_WORKFLOWS="${COMFYUI_DIR}/user/default/workflows"
mkdir -p "$DEST_WORKFLOWS"
if [ -d "$BUNDLED_WORKFLOWS" ] && [ -n "$(ls -A "$BUNDLED_WORKFLOWS" 2>/dev/null)" ]; then
    cp -R "$BUNDLED_WORKFLOWS"/* "$DEST_WORKFLOWS/"
    echo "[INFO] Bundled workflows copied."
fi

# =============================================================================
# Directory Initialization and Mount Detection
# =============================================================================

COMFYUI_ROOT="/app/ComfyUI"
MODELS_DIR="${COMFYUI_ROOT}/models"
INPUT_DIR="${COMFYUI_ROOT}/input"
OUTPUT_DIR="${COMFYUI_ROOT}/output"
WORKFLOWS_DIR="${COMFYUI_ROOT}/user/default/workflows"

# Create directories (works whether mounted or not)
mkdir -p "$MODELS_DIR" "$INPUT_DIR" "$OUTPUT_DIR" "$WORKFLOWS_DIR"

# Detect if directory is a mount point
is_mounted() {
    local dir="$1"
    mountpoint -q "$dir" 2>/dev/null && echo "yes" || echo "no"
}

echo ""
echo "########################################"
echo "[INFO] Directory Configuration"
echo "########################################"
echo "models dir:    $MODELS_DIR (mounted: $(is_mounted "$MODELS_DIR"))"
echo "input dir:     $INPUT_DIR (mounted: $(is_mounted "$INPUT_DIR"))"
echo "output dir:    $OUTPUT_DIR (mounted: $(is_mounted "$OUTPUT_DIR"))"
echo "workflows dir: $WORKFLOWS_DIR (mounted: $(is_mounted "$WORKFLOWS_DIR"))"
echo "----------------------------------------"
echo ""

cd /app

# Normalize LOW_VRAM for case-insensitive comparison (low vs high VRAM tier)
LOW_VRAM_LC=$(echo "${LOW_VRAM:-false}" | tr '[:upper:]' '[:lower:]')
NVFP4_SUPPORTED_LC=$(echo "${NVFP4_SUPPORTED:-false}" | tr '[:upper:]' '[:lower:]')

# Determine VRAM suffix based on LOW_VRAM (pack file names: models-low.txt, models-high.txt)
if [ "$LOW_VRAM_LC" == "true" ]; then
    echo "[INFO] LOW_VRAM is set to true."
    VRAM_SUFFIX="low"
    VRAM_TARGET="low"
else
    echo "[INFO] LOW_VRAM is not set or false."
    VRAM_SUFFIX="high"
    VRAM_TARGET="high"
fi

if [ "$NVFP4_SUPPORTED_LC" == "true" ]; then
    echo "[INFO] NVFP4_SUPPORTED is set to true."
else
    echo "[INFO] NVFP4_SUPPORTED is not set or false."
fi

# Parse MODELS_DOWNLOAD: comma-separated selectors, default klein-distilled
SELECTORS_RAW="${MODELS_DOWNLOAD:-klein-distilled}"
SELECTORS_LC=$(echo "$SELECTORS_RAW" | tr '[:upper:]' '[:lower:]' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' || true)
if [ -z "$SELECTORS_LC" ]; then
    SELECTORS_LC="klein-distilled"
fi

PACKS_DIR="/scripts/packs"
TEMP_MODELS=$(mktemp)
TEMP_WORKFLOWS=$(mktemp)
trap 'rm -f "$TEMP_MODELS" "$TEMP_WORKFLOWS"' EXIT

# Function to resolve pack directory from selector
resolve_pack_dir() {
    local selector="$1"
    local pack_dir=""
    
    # Check each pack's pack.json for matching selector
    for dir in "$PACKS_DIR"/*/; do
        if [ -f "${dir}pack.json" ]; then
            # Check if selector matches name or is in selectors array
            local name=$(jq -r '.name // ""' "${dir}pack.json" 2>/dev/null)
            local selectors=$(jq -r '.selectors[]? // empty' "${dir}pack.json" 2>/dev/null)
            
            if [ "$name" == "$selector" ]; then
                pack_dir="$dir"
                break
            fi
            
            for s in $selectors; do
                if [ "$s" == "$selector" ]; then
                    pack_dir="$dir"
                    break 2
                fi
            done
        fi
    done
    
    echo "$pack_dir"
}

# Function to list valid primary selectors from pack metadata
list_valid_selectors() {
    local selectors=""
    for dir in "$PACKS_DIR"/*/; do
        if [ -f "${dir}pack.json" ]; then
            local name
            name=$(jq -r '.name // empty' "${dir}pack.json" 2>/dev/null)
            if [ -n "$name" ]; then
                if [ -n "$selectors" ]; then
                    selectors="${selectors}, ${name}"
                else
                    selectors="$name"
                fi
            fi
        fi
    done
    echo "$selectors"
}

# Function to print pack info block
print_pack_info() {
    local pack_dir="$1"
    local pack_json="${pack_dir}pack.json"
    
    if [ ! -f "$pack_json" ]; then
        echo "[WARN] Missing pack.json in $pack_dir"
        return 0
    fi
    
    local name=$(jq -r '.name // "unknown"' "$pack_json")
    local tutorial_url=$(jq -r '.tutorial_urls[0] // "N/A"' "$pack_json")
    local requires_hf=$(jq -r '.requires_hf_token // false' "$pack_json")
    local notes_key="notes_${VRAM_SUFFIX}"
    local notes=$(jq -r ".${notes_key} // \"\"" "$pack_json")
    
    # Count models and workflows
    local models_file="${pack_dir}models-${VRAM_SUFFIX}.txt"
    local workflows_file="${pack_dir}workflows-${VRAM_SUFFIX}.txt"
    local model_count=0
    local workflow_count=0
    
    if [ -f "$models_file" ]; then
        model_count=$(grep '^https' "$models_file" 2>/dev/null | wc -l)
    fi
    if [ -f "$workflows_file" ]; then
        workflow_count=$(grep '^https' "$workflows_file" 2>/dev/null | wc -l)
    fi
    
    # Count custom nodes
    local nodes_file="${pack_dir}nodes.txt"
    local nodes_count=0
    if [ -f "$nodes_file" ]; then
        nodes_count=$(grep '^https\|^git' "$nodes_file" 2>/dev/null | wc -l)
    fi
    
    # Determine HF_TOKEN status
    local hf_status="not required"
    if [ "$requires_hf" == "true" ]; then
        if [ -n "${HF_TOKEN}" ]; then
            hf_status="required (provided)"
        else
            hf_status="REQUIRED - MISSING!"
        fi
    fi
    
    echo "========================================"
    echo "=== PACK: $name ==="
    echo "========================================"
    echo "Tutorial: $tutorial_url"
    echo "VRAM tier: $VRAM_TARGET (LOW_VRAM=$LOW_VRAM_LC)"
    echo "NVFP4 override: $NVFP4_SUPPORTED_LC"
    echo "Models: $model_count files"
    echo "Workflows: $workflow_count files"
    echo "Custom nodes: $nodes_count"
    echo "HF_TOKEN: $hf_status"
    if [ -n "$notes" ]; then
        echo "Notes: $notes"
    fi
    echo "----------------------------------------"
}

# Optionally switch selected Klein FP8 model URLs to NVFP4.
# Keep output filenames unchanged so bundled workflows/nodes do not need edits.
apply_nvfp4_overrides() {
    local list_file="$1"
    if [ "$NVFP4_SUPPORTED_LC" != "true" ]; then
        return 0
    fi
    if [ ! -f "$list_file" ]; then
        return 0
    fi

    local changed=0
    if grep -q "FLUX.2-klein-4b-fp8" "$list_file"; then
        sed -i 's#https://huggingface.co/black-forest-labs/FLUX\.2-klein-4b-fp8/resolve/main/flux-2-klein-4b-fp8\.safetensors#https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-nvfp4/resolve/main/flux-2-klein-4b-nvfp4.safetensors#g' "$list_file"
        changed=1
    fi

    if [ "$changed" -eq 1 ]; then
        echo "[INFO] NVFP4 override enabled: switched Klein download URLs to NVFP4 while keeping local filenames unchanged for workflow compatibility."
    else
        echo "[INFO] NVFP4 override enabled but no matching Klein FP8 URLs found in selected packs."
    fi
}

# Validate HF_TOKEN requirement for a pack
validate_hf_token() {
    local pack_dir="$1"
    local pack_json="${pack_dir}pack.json"
    
    if [ ! -f "$pack_json" ]; then
        return 0
    fi
    
    local requires_hf=$(jq -r '.requires_hf_token // false' "$pack_json")
    local name=$(jq -r '.name // "unknown"' "$pack_json")
    local tutorial_url=$(jq -r '.tutorial_urls[0] // "N/A"' "$pack_json")
    
    if [ "$requires_hf" == "true" ] && [ -z "${HF_TOKEN}" ]; then
        echo ""
        echo "[ERROR] Pack '$name' requires HF_TOKEN but it is not set!"
        echo ""
        echo "To fix this:"
        echo "  1. Create a Hugging Face account at https://huggingface.co"
        echo "  2. Accept the model license agreement"
        echo "  3. Generate a token at https://huggingface.co/settings/tokens"
        echo "  4. Set HF_TOKEN in your .env file or docker-compose.yml"
        echo ""
        echo "Tutorial: $tutorial_url"
        echo ""
        return 1
    fi
    
    return 0
}

echo ""
echo "########################################"
echo "[INFO] Processing selected packs..."
echo "########################################"
echo ""

for sel in $SELECTORS_LC; do
    pack_dir=$(resolve_pack_dir "$sel")
    
    if [ -z "$pack_dir" ]; then
        echo "[WARN] Unknown selector: $sel (skipping)"
        echo "       Valid selectors: $(list_valid_selectors)"
        continue
    fi
    
    # Print pack info
    print_pack_info "$pack_dir"

    # Copy pack-shipped workflow JSON before HF gating (bundled files do not need HF)
    WB="${pack_dir}workflows-bundled"
    if [ -d "$WB" ]; then
        echo "[INFO] Installing bundled workflows for pack..."
        mkdir -p /app/ComfyUI/user/default/workflows
        shopt -s nullglob
        for wf in "$WB"/*.json; do
            bn=$(basename "$wf")
            cp -f "$wf" "/app/ComfyUI/user/default/workflows/$bn"
            echo "  [OK] $bn"
        done
        shopt -u nullglob
    fi
    
    # Validate HF_TOKEN -- warn and skip pack if missing (don't kill the container)
    if ! validate_hf_token "$pack_dir"; then
        echo "[WARN] Skipping pack '$sel' due to missing HF_TOKEN."
        echo "[WARN] Non-gated models from other packs will still be downloaded."
        continue
    fi
    
    # Determine model and workflow files
    M="${pack_dir}models-${VRAM_SUFFIX}.txt"
    W="${pack_dir}workflows-${VRAM_SUFFIX}.txt"
    
    # Append to temp files
    if [ -f "$M" ] && [ -s "$M" ] && grep -q '^https' "$M" 2>/dev/null; then
        cat "$M" >> "$TEMP_MODELS"
        echo "" >> "$TEMP_MODELS"
    fi
    if [ -f "$W" ] && [ -s "$W" ] && grep -q '^https' "$W" 2>/dev/null; then
        cat "$W" >> "$TEMP_WORKFLOWS"
        echo "" >> "$TEMP_WORKFLOWS"
    fi
    
    # Install custom nodes if nodes.txt exists
    N="${pack_dir}nodes.txt"
    if [ -f "$N" ] && [ -s "$N" ]; then
        echo "[INFO] Installing custom nodes for pack..."
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "$line" ]] && continue
            
            # Extract git URL (first field)
            git_url=$(echo "$line" | awk '{print $1}')
            if [[ "$git_url" =~ ^https://|^git:// ]]; then
                # Extract repo name from URL
                repo_name=$(basename "$git_url" .git)
                repo_branch=$(echo "$line" | awk '{print $2}')
                target_dir="/app/ComfyUI/custom_nodes/$repo_name"

                echo "  [SYNC] $repo_name"
                if clone_or_update "$target_dir" "$git_url" "$repo_branch"; then
                    install_reqs "$target_dir/requirements.txt"
                else
                    echo "  [WARN] Failed to sync $repo_name"
                fi
            fi
        done < "$N"
    fi
done

echo ""

# Download workflows (idempotent: overwrite to refresh, conditional-get skips unchanged)
if [ -s "$TEMP_WORKFLOWS" ] && grep -q '^https' "$TEMP_WORKFLOWS" 2>/dev/null; then
    echo "########################################"
    echo "[INFO] Downloading workflows..."
    echo "########################################"
    if ! aria2c --input-file="$TEMP_WORKFLOWS" \
        --allow-overwrite=true --auto-file-renaming=false --continue=true \
        --max-connection-per-server=5 --conditional-get=true 2>&1; then
        echo "[ERROR] Workflow download failed. Check network and URLs above."
        exit 1
    fi
else
    echo "[INFO] No workflow URLs for selected packs."
fi

# Filter model list if HF_TOKEN not set (remove lines marked # Requires HF_TOKEN)
if [ -s "$TEMP_MODELS" ] && grep -q '^https' "$TEMP_MODELS" 2>/dev/null; then
    if [ -z "${HF_TOKEN}" ]; then
        echo "[WARN] HF_TOKEN not set. Skipping models that require authentication."
        sed '/# Requires HF_TOKEN/,/^$/d' "$TEMP_MODELS" > /scripts/models_filtered.txt
        DOWNLOAD_LIST="/scripts/models_filtered.txt"
    else
        DOWNLOAD_LIST="$TEMP_MODELS"
    fi

    apply_nvfp4_overrides "$DOWNLOAD_LIST"

    if [ -s "$DOWNLOAD_LIST" ] && grep -q '^https' "$DOWNLOAD_LIST" 2>/dev/null; then
        echo "########################################"
        echo "[INFO] Downloading models..."
        echo "########################################"
        if ! aria2c --input-file="$DOWNLOAD_LIST" \
            --allow-overwrite=true --auto-file-renaming=false --continue=true \
            --max-connection-per-server=5 --conditional-get=true \
            ${HF_TOKEN:+--header="Authorization: Bearer ${HF_TOKEN}"} 2>&1; then
            echo "[ERROR] Model download failed. Check HF_TOKEN and URLs above."
            exit 1
        fi
    else
        echo "[WARN] No models to download (list empty or all require HF_TOKEN)."
    fi
else
    echo "[INFO] No model URLs for selected packs."
fi

rm -f "$TEMP_MODELS" "$TEMP_WORKFLOWS"

echo ""
echo "########################################"
echo "[INFO] Starting ComfyUI..."
echo "########################################"
echo ""

export PATH="${PATH}:/app/.local/bin"
export PYTHONPYCACHEPREFIX="/app/.cache/pycache"

cd /app

AUTO_VRAM_ARGS_LC=$(echo "${AUTO_VRAM_ARGS:-true}" | tr '[:upper:]' '[:lower:]')
CLI_ARGS="${CLI_ARGS:-}"
VRAM_RUNTIME_ARGS=""

if [ -n "${COMFYUI_VRAM_ARGS:-}" ]; then
    VRAM_RUNTIME_ARGS="$COMFYUI_VRAM_ARGS"
    echo "[INFO] Using COMFYUI_VRAM_ARGS: $VRAM_RUNTIME_ARGS"
elif [ "$AUTO_VRAM_ARGS_LC" != "true" ]; then
    echo "[INFO] AUTO_VRAM_ARGS is disabled."
elif [ -n "$CLI_ARGS" ]; then
    echo "[INFO] CLI_ARGS provided; automatic VRAM args will not be added."
elif [ "$LOW_VRAM_LC" == "true" ]; then
    VRAM_RUNTIME_ARGS="--lowvram --reserve-vram ${RESERVE_VRAM_GB:-1.2}"
    echo "[INFO] Auto VRAM args for LOW_VRAM=true: $VRAM_RUNTIME_ARGS"
else
    VRAM_RUNTIME_ARGS="--normalvram"
    echo "[INFO] Auto VRAM args for LOW_VRAM=false: $VRAM_RUNTIME_ARGS"
fi

python3 ./ComfyUI/main.py --listen --port 8188 ${VRAM_RUNTIME_ARGS} ${CLI_ARGS}

#!/bin/bash

set -e

# =============================================================================
# CUDA Detection and PyTorch Wheel Selection
# =============================================================================

# Detect CUDA version from nvidia-smi
# Returns version string like "12.6" or "cpu" if no GPU
detect_cuda_version() {
    if ! command -v nvidia-smi &> /dev/null; then
        echo "cpu"
        return
    fi

    # Try to get CUDA version from nvidia-smi
    local cuda_version
    cuda_version=$(nvidia-smi 2>/dev/null | grep -oP "CUDA Version: \K[0-9]+\.[0-9]+" || echo "")

    if [ -z "$cuda_version" ]; then
        echo "cpu"
        return
    fi

    echo "$cuda_version"
}

# Map CUDA version to PyTorch wheel tag
# Arguments: CUDA version string (e.g., "12.6")
# Returns: wheel tag (cu130, cu126, cu124, cu121, or cpu)
map_cuda_to_wheel() {
    local cuda_version="$1"

    if [ "$cuda_version" == "cpu" ]; then
        echo "cpu"
        return
    fi

    # Extract major and minor version
    local major minor
    major=$(echo "$cuda_version" | cut -d. -f1)
    minor=$(echo "$cuda_version" | cut -d. -f2)

    # Convert to comparable integer (major * 100 + minor)
    local version_num=$((major * 100 + minor))

    # Map to wheel tag based on thresholds
    if [ $version_num -ge 1300 ]; then
        echo "cu130"
    elif [ $version_num -ge 1206 ]; then
        echo "cu126"
    elif [ $version_num -ge 1204 ]; then
        echo "cu124"
    elif [ $version_num -ge 1201 ]; then
        echo "cu121"
    else
        echo "cpu"
    fi
}

# Get the CUDA version that current PyTorch was built for
# Returns: version string like "12.6" or "cpu" or "not_installed"
get_pytorch_cuda_version() {
    local torch_cuda
    torch_cuda=$(python3 -c "
try:
    import torch
    cuda = torch.version.cuda
    if cuda:
        print(cuda)
    else:
        print('cpu')
except ImportError:
    print('not_installed')
" 2>/dev/null)
    echo "$torch_cuda"
}

# Check if installed PyTorch matches the target wheel tag
# Arguments: target wheel tag (e.g., "cu126")
# Returns: 0 if match, 1 if mismatch or not installed
check_pytorch_matches() {
    local target_tag="$1"
    local current_cuda
    current_cuda=$(get_pytorch_cuda_version)

    if [ "$current_cuda" == "not_installed" ]; then
        return 1
    fi

    # Map current PyTorch CUDA to wheel tag
    local current_tag
    current_tag=$(map_cuda_to_wheel "$current_cuda")

    if [ "$current_tag" == "$target_tag" ]; then
        return 0
    else
        return 1
    fi
}

# Ensure PyTorch is installed with the correct CUDA wheels
# Checks current installation and reinstalls if needed
ensure_pytorch_wheels() {
    echo ""
    echo "########################################"
    echo "[INFO] CUDA/PyTorch Configuration"
    echo "########################################"

    # Check for manual override
    local wheel_tag
    if [ -n "${CUDA_WHEEL_TAG:-}" ]; then
        wheel_tag="${CUDA_WHEEL_TAG}"
        echo "[INFO] Using manual override: CUDA_WHEEL_TAG=${wheel_tag}"
    else
        # Auto-detect CUDA version
        local cuda_version
        cuda_version=$(detect_cuda_version)
        echo "[INFO] Detected CUDA version: ${cuda_version}"

        # Map to wheel tag
        wheel_tag=$(map_cuda_to_wheel "$cuda_version")
        echo "[INFO] Selected wheel tag: ${wheel_tag}"
    fi

    # Warn if falling back to CPU
    if [ "$wheel_tag" == "cpu" ]; then
        echo "[WARN] No compatible CUDA found. Using CPU-only PyTorch."
        echo "[WARN] GPU acceleration will NOT be available."
        echo "[WARN] For GPU support, ensure CUDA >= 12.1 is available."
    fi

    # Check if current PyTorch matches target
    if check_pytorch_matches "$wheel_tag"; then
        local current_cuda
        current_cuda=$(get_pytorch_cuda_version)
        echo "[INFO] PyTorch already installed with matching CUDA (${current_cuda})"
        echo "[INFO] Skipping reinstallation"
    else
        echo "[INFO] Installing PyTorch for ${wheel_tag}..."

        # Determine index URL
        local index_url="https://download.pytorch.org/whl/${wheel_tag}"

        echo "[INFO] Index URL: ${index_url}"
        echo "[INFO] Packages: torch, torchvision, torchaudio, xformers"

        # Install with uv pip
        if uv pip install --reinstall \
            torch torchvision torchaudio xformers \
            --index-url "$index_url"; then
            echo "[INFO] PyTorch installation complete"
        else
            echo "[ERROR] PyTorch installation failed!"
            echo "[ERROR] Check network connectivity and CUDA compatibility."
            exit 1
        fi
    fi

    echo "----------------------------------------"
    echo ""
}

# Run PyTorch wheel check/install
ensure_pytorch_wheels

# =============================================================================
# Main Entrypoint Logic
# =============================================================================

# Normalize LOW_VRAM for case-insensitive comparison (16GB vs 20GB target)
LOW_VRAM_LC=$(echo "${LOW_VRAM:-false}" | tr '[:upper:]' '[:lower:]')

# Determine VRAM suffix based on LOW_VRAM
if [ "$LOW_VRAM_LC" == "true" ]; then
    VRAM_SUFFIX="16gb"
    VRAM_TARGET="16GB"
else
    VRAM_SUFFIX="20gb"
    VRAM_TARGET="20GB"
fi

# Ensure correct permissions for /app directory
if [ ! -w "/app" ]; then
    echo "Warning: Cannot write to /app. Attempting to fix permissions..."
    sudo chown -R $(id -u):$(id -g) /app
fi

# Install or update ComfyUI
cd /app
# #region agent log
LOG_FILE="/app/.cursor/debug.log"
[ -w "/app/.cursor" ] 2>/dev/null && printf '%s\n' "{\"id\":\"entrypoint_comfyui_check\",\"timestamp\":$(date +%s)000,\"location\":\"entrypoint.sh:comfyui_block\",\"message\":\"ComfyUI dir and git check\",\"data\":{\"comfyui_dir_exists\":$([ -d /app/ComfyUI ] && echo true || echo false),\"git_dir_exists\":$([ -d /app/ComfyUI/.git ] 2>/dev/null && echo true || echo false),\"pwd\":\"$(pwd)\"},\"hypothesisId\":\"H1\"}" >> "$LOG_FILE"
# #endregion
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

# Parse MODELS_DOWNLOAD: comma-separated selectors, default klein-distilled
SELECTORS_RAW="${MODELS_DOWNLOAD:-klein-distilled}"
SELECTORS_LC=$(echo "$SELECTORS_RAW" | tr '[:upper:]' '[:lower:]' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$')
if [ -z "$SELECTORS_LC" ]; then
    SELECTORS_LC="klein-distilled"
fi

PACKS_DIR="/scripts/packs"
TEMP_MODELS=$(mktemp)
TEMP_WORKFLOWS=$(mktemp)

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

# Function to print pack info block
print_pack_info() {
    local pack_dir="$1"
    local pack_json="${pack_dir}pack.json"
    
    if [ ! -f "$pack_json" ]; then
        return 1
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
        model_count=$(grep -c '^https' "$models_file" 2>/dev/null || echo 0)
    fi
    if [ -f "$workflows_file" ]; then
        workflow_count=$(grep -c '^https' "$workflows_file" 2>/dev/null || echo 0)
    fi
    
    # Count custom nodes
    local nodes_file="${pack_dir}nodes.txt"
    local nodes_count=0
    if [ -f "$nodes_file" ]; then
        nodes_count=$(grep -c '^https\|^git' "$nodes_file" 2>/dev/null || echo 0)
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
    echo "Target VRAM: $VRAM_TARGET (LOW_VRAM=$LOW_VRAM_LC)"
    echo "Models: $model_count files"
    echo "Workflows: $workflow_count files"
    echo "Custom nodes: $nodes_count"
    echo "HF_TOKEN: $hf_status"
    if [ -n "$notes" ]; then
        echo "Notes: $notes"
    fi
    echo "----------------------------------------"
    
    # Return pack name for error messages
    echo "$name"
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
        echo "       Valid selectors: klein-distilled, hunyuan-3d, flux1-krea, hunyuan-video, ace-step, ovis-image, newbie-image"
        continue
    fi
    
    # Print pack info
    print_pack_info "$pack_dir"
    
    # Validate HF_TOKEN
    if ! validate_hf_token "$pack_dir"; then
        exit 1
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
                target_dir="/app/ComfyUI/custom_nodes/$repo_name"
                
                if [ -d "$target_dir" ]; then
                    echo "  [SKIP] $repo_name already installed"
                else
                    echo "  [INSTALL] $repo_name"
                    git clone "$git_url" "$target_dir" 2>/dev/null || echo "  [WARN] Failed to clone $repo_name"
                    # Install requirements if present
                    if [ -f "$target_dir/requirements.txt" ]; then
                        uv pip install -r "$target_dir/requirements.txt" 2>/dev/null || true
                    fi
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

    if [ -s "$DOWNLOAD_LIST" ] && grep -q '^https' "$DOWNLOAD_LIST" 2>/dev/null; then
        echo "########################################"
        echo "[INFO] Downloading models..."
        echo "########################################"
        if ! aria2c --input-file="$DOWNLOAD_LIST" \
            --allow-overwrite=false --auto-file-renaming=false --continue=true \
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

python3 ./ComfyUI/main.py --listen --port 8188 ${CLI_ARGS}

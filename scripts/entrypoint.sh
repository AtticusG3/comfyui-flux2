#!/bin/bash

set -e

# =============================================================================
# Connectivity Routing (restricted-network support)
# =============================================================================
# Route modes:
# - direct: no proxy, default resolver behavior
# - proxy: use provider-specific or global proxy URL
# - smart-dns: no proxy, but prefer provider-specific DNS resolvers for aria2
# - vpn: no proxy override; assumes host/container networking already routes via VPN

normalize_mode() {
    local mode
    mode=$(echo "${1:-direct}" | tr '[:upper:]' '[:lower:]')
    case "$mode" in
        direct|proxy|smart-dns|vpn)
            echo "$mode"
            ;;
        *)
            echo "[WARN] Unknown connectivity mode '$1'. Falling back to direct."
            echo "direct"
            ;;
    esac
}

CONNECTIVITY_ROUTE_DEFAULT=$(normalize_mode "${CONNECTIVITY_ROUTE_DEFAULT:-direct}")
CONNECTIVITY_ROUTE_HUGGINGFACE="${CONNECTIVITY_ROUTE_HUGGINGFACE:-inherit}"
CONNECTIVITY_ROUTE_GITHUB="${CONNECTIVITY_ROUTE_GITHUB:-inherit}"
CONNECTIVITY_ROUTE_CIVITAI="${CONNECTIVITY_ROUTE_CIVITAI:-inherit}"

PROXY_URL="${PROXY_URL:-}"
HUGGINGFACE_PROXY_URL="${HUGGINGFACE_PROXY_URL:-}"
GITHUB_PROXY_URL="${GITHUB_PROXY_URL:-}"
CIVITAI_PROXY_URL="${CIVITAI_PROXY_URL:-}"

DNS_SERVERS="${DNS_SERVERS:-}"
HUGGINGFACE_DNS_SERVERS="${HUGGINGFACE_DNS_SERVERS:-}"
GITHUB_DNS_SERVERS="${GITHUB_DNS_SERVERS:-}"
CIVITAI_DNS_SERVERS="${CIVITAI_DNS_SERVERS:-}"

resolve_route_mode() {
    local provider="$1"
    local candidate="inherit"
    case "$provider" in
        huggingface) candidate="$CONNECTIVITY_ROUTE_HUGGINGFACE" ;;
        github) candidate="$CONNECTIVITY_ROUTE_GITHUB" ;;
        civitai) candidate="$CONNECTIVITY_ROUTE_CIVITAI" ;;
    esac
    if [ -z "$candidate" ] || [ "$candidate" == "inherit" ]; then
        echo "$CONNECTIVITY_ROUTE_DEFAULT"
        return 0
    fi
    normalize_mode "$candidate" | tail -n 1
}

resolve_proxy_url() {
    local provider="$1"
    local specific=""
    case "$provider" in
        huggingface) specific="$HUGGINGFACE_PROXY_URL" ;;
        github) specific="$GITHUB_PROXY_URL" ;;
        civitai) specific="$CIVITAI_PROXY_URL" ;;
    esac
    if [ -n "$specific" ]; then
        echo "$specific"
    else
        echo "$PROXY_URL"
    fi
}

resolve_dns_servers() {
    local provider="$1"
    local specific=""
    case "$provider" in
        huggingface) specific="$HUGGINGFACE_DNS_SERVERS" ;;
        github) specific="$GITHUB_DNS_SERVERS" ;;
        civitai) specific="$CIVITAI_DNS_SERVERS" ;;
    esac
    if [ -n "$specific" ]; then
        echo "$specific"
    else
        echo "$DNS_SERVERS"
    fi
}

provider_for_url() {
    local url="$1"
    local host
    host=$(echo "$url" | sed -E 's#^[a-zA-Z]+://([^/]+).*#\1#')
    case "$host" in
        huggingface.co|hf.co|cdn-lfs.huggingface.co)
            echo "huggingface"
            ;;
        github.com|raw.githubusercontent.com|objects.githubusercontent.com|api.github.com|codeload.github.com)
            echo "github"
            ;;
        civitai.com|*.civitai.com)
            echo "civitai"
            ;;
        *)
            echo "other"
            ;;
    esac
}

git_with_connectivity() {
    local provider="$1"
    shift
    local mode
    mode=$(resolve_route_mode "$provider")
    local proxy
    proxy=$(resolve_proxy_url "$provider")
    if [ "$mode" == "proxy" ]; then
        if [ -z "$proxy" ]; then
            echo "[WARN] $provider route=proxy but no proxy URL set; using direct git."
            git "$@"
        else
            git -c http.proxy="$proxy" -c https.proxy="$proxy" "$@"
        fi
        return $?
    fi
    if [ "$mode" == "smart-dns" ]; then
        echo "[INFO] $provider route=smart-dns for git (DNS settings depend on container resolver)."
    elif [ "$mode" == "vpn" ]; then
        echo "[INFO] $provider route=vpn for git (expects host/container VPN path)."
    fi
    git "$@"
}

print_connectivity_summary() {
    local p
    echo "########################################"
    echo "[INFO] Connectivity routing"
    echo "########################################"
    echo "Default route: $CONNECTIVITY_ROUTE_DEFAULT"
    for p in huggingface github civitai; do
        local mode
        mode=$(resolve_route_mode "$p")
        local proxy
        proxy=$(resolve_proxy_url "$p")
        local dns
        dns=$(resolve_dns_servers "$p")
        echo "  - $p: mode=$mode proxy=${proxy:-<none>} dns=${dns:-<default>}"
    done
    echo "----------------------------------------"
}

doctor_probe_provider() {
    local provider="$1"
    local url="$2"
    local mode
    mode=$(resolve_route_mode "$provider")
    local proxy
    proxy=$(resolve_proxy_url "$provider")
    local dns
    dns=$(resolve_dns_servers "$provider")

    local curl_args=(-I --silent --show-error --location --max-time 12)
    case "$mode" in
        proxy)
            if [ -n "$proxy" ]; then
                curl_args+=(-x "$proxy")
            else
                echo "[WARN] Connectivity doctor: $provider route=proxy but no proxy URL set."
            fi
            ;;
        smart-dns)
            # curl cannot set DNS resolver directly in a portable way; this is a hint only.
            if [ -n "$dns" ]; then
                echo "[INFO] Connectivity doctor: $provider smart-dns configured ($dns). Probe uses container resolver."
            fi
            ;;
        vpn)
            echo "[INFO] Connectivity doctor: $provider route=vpn (expects host/container VPN path)."
            ;;
    esac

    if curl "${curl_args[@]}" "$url" >/dev/null 2>&1; then
        echo "[OK] Connectivity doctor: $provider reachable ($mode)."
    else
        echo "[WARN] Connectivity doctor: $provider probe failed ($mode) -> $url"
    fi
}

connectivity_doctor() {
    local enabled_lc
    enabled_lc=$(echo "${CONNECTIVITY_DOCTOR_ENABLED:-true}" | tr '[:upper:]' '[:lower:]')
    if [ "$enabled_lc" != "true" ]; then
        echo "[INFO] Connectivity doctor disabled (CONNECTIVITY_DOCTOR_ENABLED=false)."
        return 0
    fi

    echo ""
    echo "########################################"
    echo "[INFO] Connectivity doctor preflight"
    echo "########################################"
    doctor_probe_provider "huggingface" "https://huggingface.co/"
    doctor_probe_provider "github" "https://github.com/"
    doctor_probe_provider "civitai" "https://civitai.com/"
    echo "----------------------------------------"
}

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

    local provider
    provider=$(provider_for_url "$url")

    if [ -d "${dir}/.git" ]; then
        echo "[INFO] Updating ${name}..."
        cd "$dir"
        # Ensure remote is configured (handles partially initialized repos)
        if git_with_connectivity "$provider" remote get-url origin >/dev/null 2>&1; then
            git_with_connectivity "$provider" remote set-url origin "$url"
        else
            git_with_connectivity "$provider" remote add origin "$url"
        fi
        if [ -n "$branch" ]; then
            git_with_connectivity "$provider" fetch origin "$branch"
            git_with_connectivity "$provider" reset --hard "origin/${branch}"
        else
            git_with_connectivity "$provider" fetch origin
            default_branch=$(git_with_connectivity "$provider" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)
            default_branch=${default_branch:-main}
            git_with_connectivity "$provider" reset --hard "origin/${default_branch}"
        fi
        git_with_connectivity "$provider" submodule update --init --recursive
    elif [ -d "$dir" ]; then
        echo "[INFO] Initializing ${name} in existing directory..."
        cd "$dir"
        if [ -n "$branch" ]; then
            git_with_connectivity "$provider" init -b "$branch"
        else
            git_with_connectivity "$provider" init
        fi
        git_with_connectivity "$provider" remote add origin "$url"
        if [ -n "$branch" ]; then
            git_with_connectivity "$provider" fetch origin "$branch"
            git_with_connectivity "$provider" reset --hard "origin/${branch}"
        else
            git_with_connectivity "$provider" fetch origin
            default_branch=$(git_with_connectivity "$provider" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)
            default_branch=${default_branch:-main}
            git_with_connectivity "$provider" reset --hard "origin/${default_branch}"
        fi
        git_with_connectivity "$provider" submodule update --init --recursive
    else
        echo "[INFO] Cloning ${name}..."
        if [ -n "$branch" ]; then
            git_with_connectivity "$provider" clone --recurse-submodules -b "$branch" "$url" "$dir"
        else
            git_with_connectivity "$provider" clone --recurse-submodules "$url" "$dir"
        fi
    fi
    cd /app
}

split_download_list_by_provider() {
    local input_file="$1"
    local out_hf="$2"
    local out_gh="$3"
    local out_cv="$4"
    local out_other="$5"

    : > "$out_hf"
    : > "$out_gh"
    : > "$out_cv"
    : > "$out_other"

    local block
    block=$(mktemp)
    local target_file="$out_other"
    local has_content=0

    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^[[:space:]]*$ ]]; then
            if [ "$has_content" -eq 1 ]; then
                cat "$block" >> "$target_file"
                echo "" >> "$target_file"
                : > "$block"
                target_file="$out_other"
                has_content=0
            fi
            continue
        fi

        if [ "$has_content" -eq 0 ] && [[ "$line" =~ ^https?:// ]]; then
            local provider
            provider=$(provider_for_url "$line")
            case "$provider" in
                huggingface) target_file="$out_hf" ;;
                github) target_file="$out_gh" ;;
                civitai) target_file="$out_cv" ;;
                *) target_file="$out_other" ;;
            esac
        fi

        echo "$line" >> "$block"
        has_content=1
    done < "$input_file"

    if [ "$has_content" -eq 1 ]; then
        cat "$block" >> "$target_file"
        echo "" >> "$target_file"
    fi
    rm -f "$block"
}

download_with_connectivity() {
    local provider="$1"
    local list_file="$2"
    local label="$3"
    shift 3
    local extra_args=("$@")

    if [ ! -s "$list_file" ] || ! grep -q '^https' "$list_file" 2>/dev/null; then
        return 0
    fi

    local mode
    mode=$(resolve_route_mode "$provider")
    local proxy
    proxy=$(resolve_proxy_url "$provider")
    local dns
    dns=$(resolve_dns_servers "$provider")
    local aria_args=(
        --input-file="$list_file"
        --allow-overwrite=true
        --auto-file-renaming=false
        --continue=true
        --max-connection-per-server=5
        --conditional-get=true
    )
    local a
    for a in "${extra_args[@]}"; do
        aria_args+=("$a")
    done

    case "$mode" in
        proxy)
            if [ -n "$proxy" ]; then
                aria_args+=(--all-proxy="$proxy")
            else
                echo "[WARN] $provider route=proxy but no proxy URL set; using direct download."
            fi
            ;;
        smart-dns)
            if [ -n "$dns" ]; then
                aria_args+=(--async-dns=true --async-dns-server="$dns")
            else
                echo "[WARN] $provider route=smart-dns but no DNS servers configured; using default resolver."
            fi
            ;;
        vpn)
            echo "[INFO] $provider route=vpn for $label (expects host/container VPN path)."
            ;;
    esac

    echo "[INFO] Downloading $label for provider '$provider' with route '$mode'..."
    aria2c "${aria_args[@]}"
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

# Trellis2-GGUF requires extra binary deps (cumesh/o_voxel/etc.) that are
# not included in requirements.txt. Run the node installer when needed.
install_trellis2_gguf_deps() {
    local node_dir="$1"
    if [ ! -d "$node_dir" ]; then
        return 0
    fi

    if python3 -c "import cumesh" >/dev/null 2>&1; then
        echo "[INFO] Trellis dependency check: cumesh already available."
        return 0
    fi

    if [ -f "$node_dir/install.py" ]; then
        echo "[INFO] Trellis dependency check: cumesh missing. Running Trellis installer..."
        if ! python3 "$node_dir/install.py"; then
            echo "[WARN] Trellis installer reported errors."
        fi
    fi

    if ! python3 -c "import cumesh" >/dev/null 2>&1; then
        echo "[WARN] cumesh still missing after Trellis installer. Trying direct install..."
        if ! uv pip install cumesh; then
            echo "[WARN] Direct cumesh install failed. Trellis nodes may still fail to import."
        fi
    fi
}

cd /app
print_connectivity_summary
connectivity_doctor

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
NVFP4_MODE_LC=$(echo "${NVFP4_MODE:-official-only}" | tr '[:upper:]' '[:lower:]')

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

if [ "$NVFP4_MODE_LC" != "official-only" ] && [ "$NVFP4_MODE_LC" != "allow-community" ]; then
    echo "[WARN] Unknown NVFP4_MODE='$NVFP4_MODE_LC'. Falling back to official-only."
    NVFP4_MODE_LC="official-only"
fi
echo "[INFO] NVFP4_MODE is '$NVFP4_MODE_LC'."

# Parse MODELS_DOWNLOAD: comma-separated selectors, default klein-distilled
SELECTORS_RAW="${MODELS_DOWNLOAD:-klein-distilled}"
SELECTORS_LC=$(echo "$SELECTORS_RAW" | tr '[:upper:]' '[:lower:]' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' || true)
if [ -z "$SELECTORS_LC" ]; then
    SELECTORS_LC="klein-distilled"
fi

PACKS_DIR="/scripts/packs"
TEMP_MODELS=$(mktemp)
TEMP_WORKFLOWS=$(mktemp)
TEMP_MANAGED_WORKFLOWS=$(mktemp)
trap 'rm -f "$TEMP_MODELS" "$TEMP_WORKFLOWS" "$TEMP_MANAGED_WORKFLOWS"' EXIT
MANAGED_WORKFLOWS_MANIFEST="${WORKFLOWS_DIR}/.managed-workflows.txt"

register_managed_workflow() {
    local wf="$1"
    if [ -n "$wf" ]; then
        echo "$wf" >> "$TEMP_MANAGED_WORKFLOWS"
    fi
}

cleanup_prev_managed_workflows() {
    if [ ! -f "$MANAGED_WORKFLOWS_MANIFEST" ]; then
        return 0
    fi
    while IFS= read -r wf || [ -n "$wf" ]; do
        [[ -z "$wf" ]] && continue
        if [[ "$wf" == "$WORKFLOWS_DIR/"* ]] && [ -f "$wf" ]; then
            rm -f "$wf"
        fi
    done < "$MANAGED_WORKFLOWS_MANIFEST"
}

write_managed_workflow_manifest() {
    if [ -s "$TEMP_MANAGED_WORKFLOWS" ]; then
        sort -u "$TEMP_MANAGED_WORKFLOWS" > "$MANAGED_WORKFLOWS_MANIFEST"
    else
        : > "$MANAGED_WORKFLOWS_MANIFEST"
    fi
}

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

# Optionally switch selected FP8 model URLs to NVFP4.
# Also switch output filenames so local model files keep their original NVFP4 names.
apply_nvfp4_overrides() {
    local list_file="$1"
    local flux2_klein_4b_nvfp4_url="https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-nvfp4/resolve/main/flux-2-klein-4b-nvfp4.safetensors"
    local flux2_klein_9b_nvfp4_url="https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-nvfp4/resolve/main/flux-2-klein-9b-nvfp4.safetensors"
    if [ "$NVFP4_SUPPORTED_LC" != "true" ]; then
        return 0
    fi
    if [ ! -f "$list_file" ]; then
        return 0
    fi

    local changed=0
    if grep -q "flux-2-klein-4b-fp8\\.safetensors" "$list_file"; then
        sed -i "s#https://[^[:space:]]*/flux-2-klein-4b-fp8\\.safetensors#${flux2_klein_4b_nvfp4_url}#g" "$list_file"
        sed -i "s#out=flux-2-klein-4b-fp8\\.safetensors#out=flux-2-klein-4b-nvfp4.safetensors#g" "$list_file"
        changed=1
    fi
    if grep -q "flux-2-klein-9b-fp8\\.safetensors" "$list_file"; then
        sed -i "s#https://[^[:space:]]*/flux-2-klein-9b-fp8\\.safetensors#${flux2_klein_9b_nvfp4_url}#g" "$list_file"
        sed -i "s#out=flux-2-klein-9b-fp8\\.safetensors#out=flux-2-klein-9b-nvfp4.safetensors#g" "$list_file"
        changed=1
    fi

    # Official Comfy-Org flux2-dev/klein fp4 endpoints were probed and currently
    # return 404. Keep flux1-krea on FP8 unless a validated official NVFP4 URL is available.
    if grep -q "flux1-krea-dev_fp8_scaled" "$list_file"; then
        echo "[WARN] No validated official NVFP4 URL configured for flux1-krea; keeping FP8 model."
    fi

    # Optional community quants when explicitly enabled.
    if [ "$NVFP4_MODE_LC" == "allow-community" ]; then
        if grep -q "wan2.2_i2v_high_noise_14B_fp8_scaled" "$list_file"; then
            sed -i 's#https://huggingface.co/Comfy-Org/Wan_2\.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2\.2_i2v_high_noise_14B_fp8_scaled\.safetensors#https://huggingface.co/GitMylo/Wan_2.2_nvfp4/resolve/main/wan2.2_i2v_high_noise_14B_nvfp4_mixed.safetensors#g' "$list_file"
            sed -i 's#out=wan2\.2_i2v_high_noise_14B_fp8_scaled\.safetensors#out=wan2.2_i2v_high_noise_14B_nvfp4_mixed.safetensors#g' "$list_file"
            changed=1
        fi
        if grep -q "wan2.2_i2v_low_noise_14B_fp8_scaled" "$list_file"; then
            sed -i 's#https://huggingface.co/Comfy-Org/Wan_2\.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2\.2_i2v_low_noise_14B_fp8_scaled\.safetensors#https://huggingface.co/GitMylo/Wan_2.2_nvfp4/resolve/main/wan2.2_i2v_low_noise_14B_nvfp4_mixed.safetensors#g' "$list_file"
            sed -i 's#out=wan2\.2_i2v_low_noise_14B_fp8_scaled\.safetensors#out=wan2.2_i2v_low_noise_14B_nvfp4_mixed.safetensors#g' "$list_file"
            changed=1
        fi
        # flux1-krea currently has community NF4/other derivatives but no known
        # validated drop-in URL for this pack's current artifact.
        if grep -q "flux1-krea-dev_fp8_scaled" "$list_file"; then
            echo "[WARN] NVFP4_MODE=allow-community: no validated drop-in NVFP4 URL configured for flux1-krea."
        fi
    fi

    if [ "$changed" -eq 1 ]; then
        echo "[INFO] NVFP4 override enabled: switched selected model URLs and output filenames to NVFP4."
    else
        echo "[INFO] NVFP4 override enabled but no matching FP8 URLs found in selected packs."
    fi
}

# Switch Klein workflow JSONs to match NVFP4 model filenames.
# This keeps workflow defaults aligned with whichever model variant was selected.
apply_nvfp4_workflow_overrides() {
    local workflows_dir="$1"
    if [ "$NVFP4_SUPPORTED_LC" != "true" ]; then
        return 0
    fi
    if [ ! -d "$workflows_dir" ]; then
        return 0
    fi

    local changed=0
    local wf
    for wf in \
        "$workflows_dir/Flux 2 Klein 4B - Text to Image.json" \
        "$workflows_dir/Flux 2 Klein 4B - Image Edit Distilled.json" \
        "$workflows_dir/Flux 2 Klein 9B - Text to Image.json" \
        "$workflows_dir/Flux 2 Klein 9B - Image Edit Distilled.json" \
        "$workflows_dir/FLUX.2 Klein 4B Distilled - Text to Image.json" \
        "$workflows_dir/FLUX.2 Klein 4B Distilled - Image Edit.json" \
        "$workflows_dir/FLUX.2 Klein 9B Distilled - Text to Image.json" \
        "$workflows_dir/FLUX.2 Klein 9B Distilled - Image Edit.json"
    do
        if [ -f "$wf" ]; then
            sed -i 's/flux-2-klein-4b-fp8\.safetensors/flux-2-klein-4b-nvfp4.safetensors/g' "$wf"
            sed -i 's/flux-2-klein-9b-fp8\.safetensors/flux-2-klein-9b-nvfp4.safetensors/g' "$wf"
            changed=1
        fi
    done

    if [ "$changed" -eq 1 ]; then
        echo "[INFO] NVFP4 workflow override enabled: switched Klein workflows to NVFP4 model filenames."
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

# Remove previously managed workflow files so only current selected packs remain.
cleanup_prev_managed_workflows

for sel in $SELECTORS_LC; do
    pack_dir=$(resolve_pack_dir "$sel")
    
    if [ -z "$pack_dir" ]; then
        echo "[WARN] Unknown selector: $sel (skipping)"
        echo "       Valid selectors: $(list_valid_selectors)"
        continue
    fi
    
    # Print pack info
    print_pack_info "$pack_dir"

    # Copy pack workflow JSON before HF gating (bundled files do not need HF)
    # Supported formats:
    # - workflows-bundled/ directory: copies each .json file with original filename
    # - workflows-bundled.txt file: "source_path|destination_filename"
    # - default fallback: /workflows/<pack-name>/*.json
    WB="${pack_dir}workflows-bundled"
    WBL="${pack_dir}workflows-bundled.txt"
    PACK_WORKFLOW_DIR="/workflows/$(basename "$pack_dir")"
    if [ -d "$PACK_WORKFLOW_DIR" ] && [ ! -f "$WBL" ]; then
        echo "[INFO] Installing pack workflows from $PACK_WORKFLOW_DIR..."
        shopt -s nullglob
        for wf in "$PACK_WORKFLOW_DIR"/*.json; do
            bn=$(basename "$wf")
            dst="$WORKFLOWS_DIR/$bn"
            cp -f "$wf" "$dst"
            register_managed_workflow "$dst"
            echo "  [OK] $bn"
        done
        shopt -u nullglob
    fi
    if [ -d "$WB" ] || [ -f "$WBL" ]; then
        echo "[INFO] Installing bundled workflows for pack..."
        mkdir -p "$WORKFLOWS_DIR"
        if [ -d "$WB" ]; then
            shopt -s nullglob
            for wf in "$WB"/*.json; do
                bn=$(basename "$wf")
                dst="$WORKFLOWS_DIR/$bn"
                cp -f "$wf" "$dst"
                register_managed_workflow "$dst"
                echo "  [OK] $bn"
            done
            shopt -u nullglob
        fi
        if [ -f "$WBL" ]; then
            while IFS= read -r line || [ -n "$line" ]; do
                [[ "$line" =~ ^[[:space:]]*# ]] && continue
                [[ -z "$line" ]] && continue
                src_rel=$(echo "$line" | cut -d'|' -f1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                dst_name=$(echo "$line" | cut -d'|' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                if [ -z "$src_rel" ] || [ -z "$dst_name" ]; then
                    echo "  [WARN] Invalid workflows-bundled entry: $line"
                    continue
                fi
                src_abs="/workflows/$src_rel"
                if [ -f "$src_abs" ]; then
                    dst="$WORKFLOWS_DIR/$dst_name"
                    cp -f "$src_abs" "$dst"
                    register_managed_workflow "$dst"
                    echo "  [OK] $dst_name"
                else
                    echo "  [WARN] Missing bundled workflow source: $src_abs"
                fi
            done < "$WBL"
        fi
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
                    if [ "$repo_name" == "ComfyUI-Trellis2-GGUF" ]; then
                        install_trellis2_gguf_deps "$target_dir"
                    fi
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
    TEMP_WORKFLOWS_HF=$(mktemp)
    TEMP_WORKFLOWS_GH=$(mktemp)
    TEMP_WORKFLOWS_CV=$(mktemp)
    TEMP_WORKFLOWS_OTHER=$(mktemp)
    split_download_list_by_provider "$TEMP_WORKFLOWS" "$TEMP_WORKFLOWS_HF" "$TEMP_WORKFLOWS_GH" "$TEMP_WORKFLOWS_CV" "$TEMP_WORKFLOWS_OTHER"
    if ! download_with_connectivity "huggingface" "$TEMP_WORKFLOWS_HF" "workflows" \
        || ! download_with_connectivity "github" "$TEMP_WORKFLOWS_GH" "workflows" \
        || ! download_with_connectivity "civitai" "$TEMP_WORKFLOWS_CV" "workflows" \
        || ! download_with_connectivity "other" "$TEMP_WORKFLOWS_OTHER" "workflows" 2>&1; then
        echo "[ERROR] Workflow download failed. Check network and URLs above."
        exit 1
    fi
    rm -f "$TEMP_WORKFLOWS_HF" "$TEMP_WORKFLOWS_GH" "$TEMP_WORKFLOWS_CV" "$TEMP_WORKFLOWS_OTHER"
else
    echo "[INFO] No workflow URLs for selected packs."
fi

apply_nvfp4_workflow_overrides "$WORKFLOWS_DIR"

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
        TEMP_MODELS_HF=$(mktemp)
        TEMP_MODELS_GH=$(mktemp)
        TEMP_MODELS_CV=$(mktemp)
        TEMP_MODELS_OTHER=$(mktemp)
        split_download_list_by_provider "$DOWNLOAD_LIST" "$TEMP_MODELS_HF" "$TEMP_MODELS_GH" "$TEMP_MODELS_CV" "$TEMP_MODELS_OTHER"
        MODEL_AUTH_HEADER=()
        if [ -n "${HF_TOKEN}" ]; then
            MODEL_AUTH_HEADER=(--header="Authorization: Bearer ${HF_TOKEN}")
        fi
        if ! download_with_connectivity "huggingface" "$TEMP_MODELS_HF" "models" "${MODEL_AUTH_HEADER[@]}" \
            || ! download_with_connectivity "github" "$TEMP_MODELS_GH" "models" \
            || ! download_with_connectivity "civitai" "$TEMP_MODELS_CV" "models" \
            || ! download_with_connectivity "other" "$TEMP_MODELS_OTHER" "models" 2>&1; then
            echo "[ERROR] Model download failed. Check HF_TOKEN and URLs above."
            exit 1
        fi
        rm -f "$TEMP_MODELS_HF" "$TEMP_MODELS_GH" "$TEMP_MODELS_CV" "$TEMP_MODELS_OTHER"
    else
        echo "[WARN] No models to download (list empty or all require HF_TOKEN)."
    fi
else
    echo "[INFO] No model URLs for selected packs."
fi

rm -f "$TEMP_MODELS" "$TEMP_WORKFLOWS"
write_managed_workflow_manifest

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

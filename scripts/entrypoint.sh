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

GIT_STAGING_ROOT="${GIT_STAGING_ROOT:-/app/.cache/git-staging}"

git_sync_run() {
    local provider="$1"
    shift
    git_with_connectivity "$provider" "$@"
}

# shellcheck source=lib/git_sync.sh
source "/scripts/lib/git_sync.sh"

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

# Install requirements if present. Runtime installs are stamp-aware so warm
# restarts do not re-resolve unchanged custom node dependencies.
REQ_STAMP_DIR="${REQ_STAMP_DIR:-/app/.cache/req-stamps}"

filter_requirements() {
    local req="$1"
    local filtered_req="$2"
    grep -Ev '^[[:space:]]*(torch|torchvision|torchaudio|xformers)([=<>~! ]|$)' "$req" > "$filtered_req" || true
}

requirements_stamp() {
    local req="$1"
    local filtered_req="$2"
    local parent_dir
    parent_dir=$(dirname "$req")
    local head="nogit"
    if [ -d "${parent_dir}/.git" ]; then
        head=$(git -C "$parent_dir" rev-parse HEAD 2>/dev/null || echo "nogit")
    fi
    {
        echo "path=$req"
        echo "head=$head"
        (sha256sum "$filtered_req" 2>/dev/null || shasum -a 256 "$filtered_req") | awk '{print $1}'
    } | sha256sum | awk '{print $1}'
}

requirements_stamp_file() {
    local req="$1"
    local parent_dir
    parent_dir=$(dirname "$req")
    local name
    name=$(basename "$parent_dir" | tr -c 'A-Za-z0-9._-' '_')
    local path_hash
    path_hash=$(printf '%s' "$req" | sha256sum | awk '{print substr($1, 1, 12)}')
    echo "${REQ_STAMP_DIR}/${name}-${path_hash}.sha256"
}

install_reqs_if_changed() {
    local req="$1"
    local label="${2:-$(basename "$(dirname "$req")")}"
    if [ ! -f "$req" ]; then
        return 0
    fi

    mkdir -p "$REQ_STAMP_DIR"
    local filtered_req
    filtered_req=$(mktemp)
    filter_requirements "$req" "$filtered_req"

    if [ ! -s "$filtered_req" ]; then
        echo "[OK] Requirements file has no installable dependencies for $label; skipping."
        rm -f "$filtered_req"
        return 0
    fi

    local stamp_file stamp
    stamp_file=$(requirements_stamp_file "$req")
    stamp=$(requirements_stamp "$req" "$filtered_req")

    if [ -f "$stamp_file" ] && [ "$(cat "$stamp_file")" = "$stamp" ]; then
        echo "[OK] Requirements unchanged for $label; skipping."
        rm -f "$filtered_req"
        return 0
    fi

    echo "[INFO] Installing requirements for $label..."
    if uv pip install -r "$filtered_req"; then
        echo "$stamp" > "$stamp_file"
    else
        echo "[WARN] Some deps from $req may have failed"
    fi
    rm -f "$filtered_req"
}

install_reqs() {
    local req="$1"
    local label="${2:-$(basename "$(dirname "$req")")}"
    install_reqs_if_changed "$req" "$label"
}

install_reqs_force() {
    local req="$1"
    local label="${2:-$(basename "$(dirname "$req")")}"
    if [ ! -f "$req" ]; then
        return 0
    fi

    local filtered_req
    filtered_req=$(mktemp)
    filter_requirements "$req" "$filtered_req"
    if [ ! -s "$filtered_req" ]; then
        echo "[OK] Requirements file has no installable dependencies for $label; skipping."
        rm -f "$filtered_req"
        return 0
    fi

    echo "[INFO] Reconciling requirements for $label..."
    if uv pip install -r "$filtered_req"; then
        mkdir -p "$REQ_STAMP_DIR"
        requirements_stamp "$req" "$filtered_req" > "$(requirements_stamp_file "$req")"
    else
        echo "[WARN] Some deps from $req may have failed"
    fi
    rm -f "$filtered_req"
}

ensure_pip_module() {
    if python3 -m pip --version >/dev/null 2>&1; then
        return 0
    fi

    echo "[INFO] Ensuring python -m pip is available for custom node installers..."
    if ! uv pip install --upgrade pip; then
        echo "[WARN] pip module install failed. Some custom node installers may warn at import time."
    fi
}

# Ensure ComfyUI frontend package tracks the version required by ComfyUI.
# ComfyUI now ships frontend separately via pip package.
ensure_comfyui_frontend_package() {
    local req="$1"
    if [ ! -f "$req" ]; then
        return 0
    fi

    local frontend_req
    frontend_req=$(awk '
        {
            line=$0
            sub(/[[:space:]]*#.*/, "", line)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
            if (tolower(line) ~ /^comfyui-frontend-package([<>=!~].*)?$/) {
                print line
                exit
            }
        }
    ' "$req")

    if [ -z "$frontend_req" ]; then
        return 0
    fi

    mkdir -p "$REQ_STAMP_DIR"
    local stamp_file="${REQ_STAMP_DIR}/comfyui-frontend-package.sha256"
    local stamp
    stamp=$(printf '%s\n' "$frontend_req" | sha256sum | awk '{print $1}')
    if [ -f "$stamp_file" ] && [ "$(cat "$stamp_file")" = "$stamp" ]; then
        echo "[OK] ComfyUI frontend package unchanged; skipping."
        return 0
    fi

    echo "[INFO] Ensuring ComfyUI frontend package is up to date: $frontend_req"
    if ! uv pip install --upgrade "$frontend_req"; then
        echo "[WARN] uv frontend package upgrade failed; trying pip fallback..."
        if ! python3 -m pip install --upgrade "$frontend_req"; then
            echo "[WARN] Frontend package upgrade failed. ComfyUI may warn about frontend version mismatch."
            return 0
        fi
    fi
    echo "$stamp" > "$stamp_file"
}

# ComfyUI 0.22+ ModelPatcher uses HostBuffer(size, prewarm, max_grow_size).
# Older comfy-aimdo wheels only accept HostBuffer(size) and break VAELoader.
ensure_comfy_aimdo_package() {
    local req="$1"
    if [ ! -f "$req" ]; then
        return 0
    fi

    local aimdo_req
    aimdo_req=$(awk '
        {
            line=$0
            sub(/[[:space:]]*#.*/, "", line)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
            if (tolower(line) ~ /^comfy-aimdo([<>=!~].*)?$/) {
                print line
                exit
            }
        }
    ' "$req")

    if [ -z "$aimdo_req" ]; then
        return 0
    fi

    mkdir -p "$REQ_STAMP_DIR"
    local stamp_file="${REQ_STAMP_DIR}/comfy-aimdo.sha256"
    local stamp
    stamp=$(printf '%s\n' "$aimdo_req" | sha256sum | awk '{print $1}')
    if [ -f "$stamp_file" ] && [ "$(cat "$stamp_file")" = "$stamp" ]; then
        echo "[OK] comfy-aimdo package unchanged; skipping."
        return 0
    fi

    echo "[INFO] Ensuring comfy-aimdo package is up to date: $aimdo_req"
    if ! uv pip install --upgrade "$aimdo_req"; then
        echo "[WARN] uv comfy-aimdo upgrade failed; trying pip fallback..."
        if ! python3 -m pip install --upgrade "$aimdo_req"; then
            echo "[WARN] comfy-aimdo upgrade failed. VAELoader may fail with HostBuffer arity errors."
            return 0
        fi
    fi
    echo "$stamp" > "$stamp_file"
}

# Install requirements for every existing custom node directory.
# This is opt-in for manual/orphan nodes; managed pack nodes are installed
# separately after sync to avoid dependency churn from stale volume content.
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

declare -A SYNCED_NODE_DIRS=()
declare -a MANAGED_NODE_DIRS=()

record_managed_node() {
    local target_dir="$1"
    if [ -n "${SYNCED_NODE_DIRS[$target_dir]:-}" ]; then
        return 0
    fi
    SYNCED_NODE_DIRS["$target_dir"]=1
    MANAGED_NODE_DIRS+=("$target_dir")
}

sync_custom_node() {
    local git_url="$1"
    local repo_branch="$2"
    local target_dir="$3"
    local label="${4:-$(basename "$target_dir")}"

    if [ -n "${SYNCED_NODE_DIRS[$target_dir]:-}" ]; then
        echo "  [OK] $label already synced this startup; skipping duplicate."
        return 0
    fi

    echo "  [SYNC] $label"
    if clone_or_update "$target_dir" "$git_url" "$repo_branch"; then
        record_managed_node "$target_dir"
        return 0
    fi

    echo "  [WARN] Failed to sync $label"
    return 1
}

install_managed_node_reqs() {
    if [ "${#MANAGED_NODE_DIRS[@]}" -eq 0 ]; then
        return 0
    fi

    echo "[INFO] Installing requirements for managed custom nodes (collated)..."
    local collated_req
    collated_req=$(mktemp)
    collate_managed_requirements "$collated_req"

    if [ ! -s "$collated_req" ]; then
        echo "[OK] No installable managed custom-node requirements; skipping."
        rm -f "$collated_req"
        return 0
    fi

    mkdir -p "$REQ_STAMP_DIR"
    local stamp_file="${REQ_STAMP_DIR}/managed-custom-nodes.sha256"
    local stamp
    stamp=$(managed_nodes_requirements_stamp "$collated_req")

    if [ -f "$stamp_file" ] && [ "$(cat "$stamp_file")" = "$stamp" ]; then
        echo "[OK] Managed custom-node requirements unchanged; skipping."
        rm -f "$collated_req"
        return 0
    fi

    echo "[INFO] Installing collated managed custom-node requirements..."
    if uv pip install -r "$collated_req"; then
        echo "$stamp" > "$stamp_file"
    else
        echo "[WARN] Some managed custom-node requirements may have failed"
    fi
    rm -f "$collated_req"
}

# Impact Pack/Subpack are synced for sdxl-lightning; verify imports because collated
# pip can be skipped by stamp while git-based deps (e.g. sam2) failed on a prior run.
ensure_impact_pack_python_deps() {
    local impact="${CUSTOM_NODES_DIR}/ComfyUI-Impact-Pack"
    local subpack="${CUSTOM_NODES_DIR}/ComfyUI-Impact-Subpack"
    local missing=0

    if [ ! -d "$impact" ] && [ ! -d "$subpack" ]; then
        return 0
    fi

    if [ -d "$impact" ] && ! python3 -c "import piexif" 2>/dev/null; then
        missing=1
        echo "[WARN] piexif missing for ComfyUI-Impact-Pack; installing..."
        uv pip install piexif || echo "[WARN] piexif install failed"
    fi

    if [ -d "$subpack" ] && ! python3 -c "import ultralytics" 2>/dev/null; then
        missing=1
        echo "[WARN] ultralytics missing for ComfyUI-Impact-Subpack; installing..."
        uv pip install "ultralytics>=8.3.162" || echo "[WARN] ultralytics install failed"
    fi

    if [ "$missing" -eq 1 ]; then
        local stamp_file="${REQ_STAMP_DIR}/managed-custom-nodes.sha256"
        rm -f "$stamp_file"
        echo "[INFO] Cleared managed custom-node requirements stamp (Impact Pack deps were incomplete)."
    fi
}

collate_managed_requirements() {
    local out="$1"
    : > "$out"
    local target_dir req line
    for target_dir in "${MANAGED_NODE_DIRS[@]}"; do
        req="${target_dir}/requirements.txt"
        [ -f "$req" ] || continue
        while IFS= read -r line || [ -n "$line" ]; do
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line//[[:space:]]/}" ]] && continue
            [[ "$line" =~ ^[[:space:]]*(torch|torchvision|torchaudio|xformers)([=<>~! ]|$) ]] && continue
            echo "$line"
        done < "$req" >> "$out"
    done
    if [ -s "$out" ]; then
        sort -u -o "$out" "$out"
    fi
}

managed_nodes_requirements_stamp() {
    local collated_req="$1"
    {
        local target_dir
        for target_dir in "${MANAGED_NODE_DIRS[@]}"; do
            echo "dir=$target_dir"
            if [ -d "${target_dir}/.git" ]; then
                git -C "$target_dir" rev-parse HEAD 2>/dev/null || echo "nogit"
            else
                echo "nogit"
            fi
        done
        (sha256sum "$collated_req" 2>/dev/null || shasum -a 256 "$collated_req") | awk '{print $1}'
    } | sha256sum | awk '{print $1}'
}

LEGACY_ORPHAN_NODES=(
    "ComfyUI-Trellis2-GGUF"
    "inference-gpu"
    "openai-api"
    "ComfyUI-NewBie"
)

cleanup_legacy_custom_nodes() {
    local root="$1"
    local name legacy_dir
    for name in "${LEGACY_ORPHAN_NODES[@]}"; do
        legacy_dir="${root}/${name}"
        if [ ! -d "$legacy_dir" ]; then
            continue
        fi
        if [ -n "${SYNCED_NODE_DIRS[$legacy_dir]:-}" ]; then
            continue
        fi
        if [ "$name" == "ComfyUI-NewBie" ] && [ -f "${legacy_dir}/__init__.py" ]; then
            continue
        fi
        echo "[INFO] Removing unmanaged legacy custom node: $name"
        rm -rf "$legacy_dir"
    done
}

log_or_install_orphan_node_reqs() {
    local root="$1"
    if [ ! -d "$root" ]; then
        return 0
    fi

    local orphan_mode_lc
    orphan_mode_lc=$(echo "${INSTALL_ORPHAN_NODE_REQS:-false}" | tr '[:upper:]' '[:lower:]')
    if [ "$orphan_mode_lc" == "true" ]; then
        install_all_custom_node_reqs "$root"
        return 0
    fi

    local skipped=()
    local node_dir
    while IFS= read -r node_dir; do
        if [ -z "${SYNCED_NODE_DIRS[$node_dir]:-}" ]; then
            skipped+=("$(basename "$node_dir")")
        fi
    done < <(find "$root" -mindepth 1 -maxdepth 1 -type d | sort)

    if [ "${#skipped[@]}" -gt 0 ]; then
        echo "[INFO] Skipping requirements for unmanaged custom nodes (INSTALL_ORPHAN_NODE_REQS=false): ${skipped[*]}"
    fi
}

# PyAV rotation: some builds expose rotation via metadata instead of frame.rotation.
patch_comfyui_video_types_py() {
    export COMFYUI_DIR="${COMFYUI_DIR:-/app/ComfyUI}"
    local f="${COMFYUI_DIR}/comfy_api/latest/_input_impl/video_types.py"
    if [ ! -f "$f" ]; then
        return 0
    fi
    echo "[INFO] Ensuring ComfyUI video_types.py PyAV rotation fallback..."
    if ! python3 /scripts/patch_video_types_rotation.py; then
        echo "[ERROR] Failed to patch video_types.py for PyAV rotation fallback."
        return 1
    fi
}

# HiDream O1 requires transformers with Qwen3-VL model code.
ensure_hidream_transformers() {
    local node_dir="${CUSTOM_NODES_DIR}/HiDream_O1-ComfyUI"
    if [ -z "${SYNCED_NODE_DIRS[$node_dir]:-}" ]; then
        return 0
    fi

    echo "[INFO] Ensuring transformers>=4.57.1 for HiDream O1 (Qwen3-VL)..."
    if ! uv pip install --upgrade "transformers>=4.57.1"; then
        echo "[WARN] transformers upgrade for HiDream reported errors."
    fi
    if python3 -c "from transformers.models.qwen3_vl.configuration_qwen3_vl import Qwen3VLConfig" 2>/dev/null; then
        echo "[INFO] transformers Qwen3-VL support: OK"
    else
        echo "[WARN] transformers Qwen3-VL import still failing; HiDream O1 nodes may not load."
    fi
}

ensure_layerstyle_opencv() {
    local node_dir="${CUSTOM_NODES_DIR}/ComfyUI_LayerStyle"
    if [ -z "${SYNCED_NODE_DIRS[$node_dir]:-}" ]; then
        return 0
    fi

    if python3 -c "import cv2; assert hasattr(cv2, 'ximgproc') and hasattr(cv2.ximgproc, 'guidedFilter')" 2>/dev/null; then
        echo "[INFO] OpenCV ximgproc guidedFilter support: OK"
        return 0
    fi

    echo "[INFO] Ensuring opencv-contrib-python>=4.10 for LayerStyle guidedFilter support..."
    if ! uv pip install --upgrade "opencv-contrib-python>=4.10"; then
        echo "[WARN] opencv-contrib-python upgrade for LayerStyle reported errors."
    fi
}

reconcile_managed_deps() {
    echo "[INFO] Reconciling managed dependency pins..."
    ensure_comfyui_frontend_package "${COMFYUI_DIR}/requirements.txt"
    ensure_comfy_aimdo_package "${COMFYUI_DIR}/requirements.txt"
    install_reqs_force "${COMFYUI_DIR}/requirements.txt" "ComfyUI"
    ensure_hidream_transformers
    ensure_layerstyle_opencv
}

# ComfyUI-Manager: lower gatekeeper strictness for container/dev use.
ensure_comfyui_manager_security_weak() {
    local cfg="${COMFYUI_DIR}/user/__manager/config.ini"
    mkdir -p "$(dirname "$cfg")"
    CFG_INI="$cfg" python3 - <<'PY' || echo "[WARN] Failed to set ComfyUI-Manager security_level=weak"
import configparser
import os
path = os.environ["CFG_INI"]
parser = configparser.ConfigParser()
if os.path.isfile(path):
    parser.read(path)
if "default" not in parser:
    parser["default"] = {}
parser["default"]["security_level"] = "weak"
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    parser.write(f)
PY
}

cd /app
print_connectivity_summary

COMFYUI_DIR="/app/ComfyUI"
CUSTOM_NODES_DIR="${COMFYUI_DIR}/custom_nodes"

# Git 2.35+ treats repos whose directory owner != current user as "dubious" and
# aborts (fatal). Docker named volumes and bind mounts often have mixed UIDs.
# This container runs one non-root user; trust all repos under this workspace.
if ! git config --global --get-all safe.directory 2>/dev/null | grep -qxF '*'; then
    git config --global --add safe.directory '*'
fi

# ComfyUI
clone_or_update "$COMFYUI_DIR" "https://github.com/Comfy-Org/ComfyUI.git" "master"
patch_comfyui_video_types_py
ensure_pip_module

# ComfyUI-Manager
mkdir -p "$CUSTOM_NODES_DIR"
clone_or_update "${CUSTOM_NODES_DIR}/ComfyUI-Manager" "https://github.com/ltdrdata/ComfyUI-Manager.git" "main"
record_managed_node "${CUSTOM_NODES_DIR}/ComfyUI-Manager"
ensure_comfyui_manager_security_weak

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

# Parse MODELS_DOWNLOAD: comma-separated selectors (default none). Add packs explicitly (e.g. klein-distilled).
SELECTORS_RAW="${MODELS_DOWNLOAD:-none}"
SELECTORS_LC=$(echo "$SELECTORS_RAW" | tr '[:upper:]' '[:lower:]' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' || true)
if [ -z "$SELECTORS_LC" ]; then
    SELECTORS_LC="none"
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

# workflows-bundled.txt optional 3rd field: low|high|both|all (default: both)
workflow_bundled_entry_matches_tier() {
    local line="$1"
    local tier_field
    tier_field=$(echo "$line" | cut -d'|' -f3 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr '[:upper:]' '[:lower:]')
    if [ -z "$tier_field" ] || [ "$tier_field" == "both" ] || [ "$tier_field" == "all" ]; then
        return 0
    fi
    if [ "$tier_field" == "$VRAM_TARGET" ]; then
        return 0
    fi
    return 1
}

resolve_workflow_source() {
    local pack_dir="$1"
    local src_rel="$2"
    local src_abs="/workflows/$src_rel"
    if [ -f "$src_abs" ]; then
        echo "$src_abs"
        return 0
    fi
    src_abs="${pack_dir}${src_rel}"
    if [ -f "$src_abs" ]; then
        echo "$src_abs"
        return 0
    fi
    return 1
}

install_managed_workflow_copy() {
    local src_abs="$1"
    local dst_name="$2"
    local dst="$WORKFLOWS_DIR/$dst_name"
    cp -f "$src_abs" "$dst"
    register_managed_workflow "$dst"
    echo "  [OK] $dst_name"
}

install_pack_bundled_workflows() {
    local pack_dir="$1"
    local wbl="${pack_dir}workflows-bundled.txt"
    local wb="${pack_dir}workflows-bundled"
    local wbl_tier="${pack_dir}workflows-bundled-${VRAM_SUFFIX}.txt"

    if [ -f "$wbl_tier" ]; then
        wbl="$wbl_tier"
    fi

    if [ -f "$wbl" ]; then
        echo "[INFO] Installing bundled workflows for pack (tier=$VRAM_TARGET)..."
        while IFS= read -r line || [ -n "$line" ]; do
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "$line" ]] && continue
            workflow_bundled_entry_matches_tier "$line" || continue
            local src_rel dst_name src_abs
            src_rel=$(echo "$line" | cut -d'|' -f1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            dst_name=$(echo "$line" | cut -d'|' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [ -z "$src_rel" ]; then
                echo "  [WARN] Invalid workflows-bundled entry: $line"
                continue
            fi
            if [ -z "$dst_name" ]; then
                dst_name=$(basename "$src_rel")
            fi
            if ! src_abs=$(resolve_workflow_source "$pack_dir" "$src_rel"); then
                echo "  [WARN] Missing bundled workflow source: $src_rel"
                continue
            fi
            install_managed_workflow_copy "$src_abs" "$dst_name"
        done < "$wbl"
        return 0
    fi

    if [ -d "$wb" ]; then
        echo "[WARN] Pack uses workflows-bundled/ without workflows-bundled.txt; skipping unfiltered directory copy."
        echo "       Add ${wb}.txt entries with optional |low or |high tier tags."
    fi
}

register_downloaded_workflows_from_list() {
    local list_file="$1"
    if [ ! -s "$list_file" ]; then
        return 0
    fi

    local found
    found=$(mktemp)
    python3 - "$list_file" "$WORKFLOWS_DIR" <<'PY' > "$found"
from pathlib import Path
from urllib.parse import urlparse, unquote
import sys

list_path = Path(sys.argv[1])
workflows_dir = Path(sys.argv[2])

current_url = None
attrs = {}

def flush():
    if not current_url:
        return
    out_name = attrs.get("out")
    target_dir = attrs.get("dir", "")
    if not out_name:
        out_name = Path(unquote(urlparse(current_url).path)).name
    normalized = target_dir.strip().strip("/")
    workflow_dirs = {
        "ComfyUI/user/default/workflows",
        "/app/ComfyUI/user/default/workflows",
        str(workflows_dir).strip("/"),
    }
    if normalized in {item.strip("/") for item in workflow_dirs}:
        print(workflows_dir / out_name)

for raw in list_path.read_text(encoding="utf-8").splitlines():
    line = raw.rstrip()
    if line.startswith(("https://", "http://")):
        flush()
        current_url = line.strip()
        attrs = {}
        continue
    if current_url and "=" in line:
        key, value = line.strip().split("=", 1)
        attrs[key.strip()] = value.strip()
flush()
PY
    while IFS= read -r wf || [ -n "$wf" ]; do
        if [ -f "$wf" ]; then
            register_managed_workflow "$wf"
            echo "  [OK] Registered downloaded workflow: $(basename "$wf")"
        fi
    done < "$found"
    rm -f "$found"
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

# If the target workflows directory already has JSON, treat as non-first start:
# do not delete managed files, re-copy bundled seeds, or download pack workflow URLs.
workflows_dir_has_json() {
    local d="$1"
    shopt -s nullglob
    local a=( "$d"/*.json )
    shopt -u nullglob
    [ ${#a[@]} -gt 0 ]
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

    # ERNIE-Image-Turbo (Abiray): FP8 -> NVFP4 safetensors when NVFP4 is enabled (mirror Klein).
    if grep -Fq "ernie-image-turbo-fp8.safetensors" "$list_file"; then
        sed -i 's#https://huggingface.co/Abiray/ERNIE-Image-Turbo-FP8-NVFP4/resolve/main/ernie-image-turbo-fp8\.safetensors#https://huggingface.co/Abiray/ERNIE-Image-Turbo-FP8-NVFP4/resolve/main/ernie-image-turbo-nvfp4.safetensors#g' "$list_file"
        sed -i 's#out=ernie-image-turbo-fp8\.safetensors#out=ernie-image-turbo-nvfp4.safetensors#g' "$list_file"
        changed=1
    fi

    # Z-Image Turbo has an official Comfy-Org NVFP4 file.
    if grep -Fq "z_image_turbo_bf16.safetensors" "$list_file"; then
        sed -i 's#https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16\.safetensors#https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_nvfp4.safetensors#g' "$list_file"
        sed -i 's#out=z_image_turbo_bf16\.safetensors#out=z_image_turbo_nvfp4.safetensors#g' "$list_file"
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

        # FireRed Image Edit 1.0 (cocorang fp8mixed -> Starnodes community NVFP4)
        if grep -Fq "FireRed-Image-Edit-1.0_fp8mixed_comfy.safetensors" "$list_file"; then
            sed -i 's#https://huggingface.co/cocorang/FireRed-Image-Edit-1.0-FP8_And_BF16/resolve/main/FireRed-Image-Edit-1.0_fp8mixed_comfy\.safetensors#https://huggingface.co/Starnodes/quants/resolve/main/FireRed-Image-Edit-1_NVFP4.safetensors#g' "$list_file"
            sed -i 's#out=FireRed-Image-Edit-1.0_fp8mixed_comfy\.safetensors#out=FireRed-Image-Edit-1_NVFP4.safetensors#g' "$list_file"
            changed=1
        fi

        # FLUX.1 Krea Dev (Comfy FP8 scaled -> elihung community NVFP4 single file)
        if grep -q "flux1-krea-dev_fp8_scaled" "$list_file"; then
            sed -i 's#https://huggingface.co/Comfy-Org/FLUX\.1-Krea-dev_ComfyUI/resolve/main/split_files/diffusion_models/flux1-krea-dev_fp8_scaled\.safetensors#https://huggingface.co/elihung/FLUX.1-Krea-dev-NVFP4/resolve/main/flux1-krea-dev-nvfp4.safetensors#g' "$list_file"
            sed -i 's#out=flux1-krea-dev_fp8_scaled\.safetensors#out=flux1-krea-dev-nvfp4.safetensors#g' "$list_file"
            changed=1
        fi

        # ERNIE-Image SFT high tier (Comfy BF16 -> Starnodes community NVFP4)
        if grep -Fq "ernie-image.safetensors" "$list_file"; then
            sed -i 's#https://huggingface.co/Comfy-Org/ERNIE-Image/resolve/main/diffusion_models/ernie-image\.safetensors#https://huggingface.co/Starnodes/quants/resolve/main/ernie-image-nvfp4.safetensors#g' "$list_file"
            sed -i 's#out=ernie-image\.safetensors#out=ernie-image-nvfp4.safetensors#g' "$list_file"
            changed=1
        fi

        # Z-Image Base community NVFP4 quality variant (best practical size/quality tradeoff).
        if grep -Fq "z_image_bf16.safetensors" "$list_file"; then
            sed -i 's#https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/diffusion_models/z_image_bf16\.safetensors#https://huggingface.co/marcorez8/Z-image-aka-Base-nvfp4/resolve/main/z-image-base-nvfp4_quality.safetensors#g' "$list_file"
            sed -i 's#out=z_image_bf16\.safetensors#out=z-image-base-nvfp4_quality.safetensors#g' "$list_file"
            changed=1
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
    if [ ! -d "$workflows_dir" ]; then
        return 0
    fi

    # Z-Anime uses the same core Z-Image/Lumina2 loader path, but its model
    # filenames differ from the upstream Z-Image Turbo template.
    local zaanime_low="$workflows_dir/z-anime-t2i.json"
    if [ -f "$zaanime_low" ]; then
        sed -i 's/z_image_turbo_bf16\.safetensors/z-anime-distill-4step-nvfp4.safetensors/g' "$zaanime_low"
        sed -i 's/qwen_3_4b\.safetensors/qwen_3_4b-fp8.safetensors/g' "$zaanime_low"
        sed -i 's/Text to Image (Z-Image-Turbo)/Text to Image (Z-Anime Distill 4 Step NVFP4)/g' "$zaanime_low"
        sed -i 's/z-image-turbo/z-anime/g' "$zaanime_low"
        echo "[INFO] Workflow override: Z-Anime low -> NVFP4 distill filenames."
    fi

    local zaanime_high="$workflows_dir/z-anime-t2i.json"
    if [ -f "$zaanime_high" ]; then
        sed -i 's/z_image_turbo_bf16\.safetensors/z-anime-distill-4step-bf16.safetensors/g' "$zaanime_high"
        sed -i 's/qwen_3_4b\.safetensors/qwen_3_4b-bf16.safetensors/g' "$zaanime_high"
        sed -i 's/Text to Image (Z-Image-Turbo)/Text to Image (Z-Anime Distill 4 Step BF16)/g' "$zaanime_high"
        sed -i 's/z-image-turbo/z-anime/g' "$zaanime_high"
        echo "[INFO] Workflow override: Z-Anime high -> BF16 distill filenames."
    fi

    # Bundled z-anime-t2i.json ships with 4step NVFP4 + FP8 TE; sed aligns to
    # VRAM_TARGET and normalizes legacy 8-step names.
    local zaanime_origin="$workflows_dir/z-anime-t2i.json"
    if [ -f "$zaanime_origin" ]; then
        if [ "$VRAM_TARGET" == "low" ]; then
            sed -i 's/z-anime-distill-4step-bf16\.safetensors/z-anime-distill-4step-nvfp4.safetensors/g' "$zaanime_origin"
            sed -i 's/z-anime-distill-8step-bf16\.safetensors/z-anime-distill-4step-nvfp4.safetensors/g' "$zaanime_origin"
            sed -i 's/z-anime-distill-8step-fp8\.safetensors/z-anime-distill-4step-nvfp4.safetensors/g' "$zaanime_origin"
            sed -i 's/qwen_3_4b-bf16\.safetensors/qwen_3_4b-fp8.safetensors/g' "$zaanime_origin"
            sed -i 's/qwen_3_4b\.safetensors/qwen_3_4b-fp8.safetensors/g' "$zaanime_origin"
            if grep -Fq "z-anime-distill-4step-nvfp4.safetensors" "$zaanime_origin" \
                && grep -Fq "qwen_3_4b-fp8.safetensors" "$zaanime_origin"; then
                echo "[INFO] Workflow override: Z-Anime T2I low -> NVFP4 distill + FP8 TE filenames."
            else
                echo "[WARN] Workflow override: Z-Anime T2I low filenames not verified after sed."
            fi
        else
            sed -i 's/z-anime-distill-4step-nvfp4\.safetensors/z-anime-distill-4step-bf16.safetensors/g' "$zaanime_origin"
            sed -i 's/z-anime-distill-8step-bf16\.safetensors/z-anime-distill-4step-bf16.safetensors/g' "$zaanime_origin"
            sed -i 's/z-anime-distill-8step-fp8\.safetensors/z-anime-distill-4step-bf16.safetensors/g' "$zaanime_origin"
            sed -i 's/qwen_3_4b-fp8\.safetensors/qwen_3_4b-bf16.safetensors/g' "$zaanime_origin"
            sed -i 's/qwen_3_4b\.safetensors/qwen_3_4b-bf16.safetensors/g' "$zaanime_origin"
            if grep -Fq "z-anime-distill-4step-bf16.safetensors" "$zaanime_origin" \
                && grep -Fq "qwen_3_4b-bf16.safetensors" "$zaanime_origin"; then
                echo "[INFO] Workflow override: Z-Anime T2I high -> BF16 distill + TE filenames."
            else
                echo "[WARN] Workflow override: Z-Anime T2I high filenames not verified after sed."
            fi
        fi
    fi

    if [ "$VRAM_TARGET" == "low" ]; then
        local zturbo_low="$workflows_dir/z-turbo-t2i.json"
        if [ -f "$zturbo_low" ] && grep -Fq "qwen_3_4b.safetensors" "$zturbo_low"; then
            sed -i 's/qwen_3_4b\.safetensors/qwen_3_4b_fp8_mixed.safetensors/g' "$zturbo_low"
            echo "[INFO] Workflow override: Z-Image Turbo low -> Qwen FP8 text encoder."
        fi

        local zbase_low="$workflows_dir/z-base-t2i.json"
        if [ -f "$zbase_low" ] && grep -Fq "qwen_3_4b.safetensors" "$zbase_low"; then
            sed -i 's/qwen_3_4b\.safetensors/qwen_3_4b_fp8_mixed.safetensors/g' "$zbase_low"
            echo "[INFO] Workflow override: Z-Image Base low -> Qwen FP8 text encoder."
        fi

        local zturbo_origin_low="$workflows_dir/z-turbo-t2i.json"
        if [ -f "$zturbo_origin_low" ] && grep -Fq "z_image_turbo_bf16.safetensors" "$zturbo_origin_low"; then
            sed -i 's/z_image_turbo_bf16\.safetensors/z_image_turbo_nvfp4.safetensors/g' "$zturbo_origin_low"
            echo "[INFO] Workflow override: Z-Image Turbo low -> official NVFP4 filename."
        fi
    fi

    local hidream="$workflows_dir/hidream-o1-example.json"
    if [ -f "$hidream" ]; then
        if [ "$VRAM_TARGET" == "low" ]; then
            sed -i 's/HiDream-O1-Image-Dev-2604-BF16/HiDream-O1-Image-FP8/g' "$hidream"
            sed -i 's/HiDream-O1-Image-BF16/HiDream-O1-Image-FP8/g' "$hidream"
            echo "[INFO] Workflow override: HiDream O1 low -> FP8 model choice."
        else
            sed -i 's/HiDream-O1-Image-Dev-2604-BF16/HiDream-O1-Image-BF16/g' "$hidream"
            sed -i 's/HiDream-O1-Image-FP8/HiDream-O1-Image-BF16/g' "$hidream"
            echo "[INFO] Workflow override: HiDream O1 high -> BF16 model choice."
        fi
    fi

    local qwen_edit="$workflows_dir/qwen-edit-2511.json"
    if [ -f "$qwen_edit" ]; then
        if [ "$VRAM_TARGET" == "high" ]; then
            sed -i 's/qwen_image_edit_2511_nvfp4\.safetensors/Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors/g' "$qwen_edit"
            sed -i 's#https://huggingface.co/Bedovyy/Qwen-Image-Edit-2511-NVFP4/resolve/main/qwen_image_edit_2511_nvfp4\.safetensors#https://huggingface.co/1038lab/Qwen-Image-Edit-2511-FP8/resolve/main/Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors#g' "$qwen_edit"
            echo "[INFO] Workflow override: Qwen Image Edit 2511 high -> FP8 diffusion filename."
        elif grep -Fq "Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors" "$qwen_edit"; then
            sed -i 's/Qwen-Image-Edit-2511-FP8_e4m3fn\.safetensors/qwen_image_edit_2511_nvfp4.safetensors/g' "$qwen_edit"
            sed -i 's#https://huggingface.co/1038lab/Qwen-Image-Edit-2511-FP8/resolve/main/Qwen-Image-Edit-2511-FP8_e4m3fn\.safetensors#https://huggingface.co/Bedovyy/Qwen-Image-Edit-2511-NVFP4/resolve/main/qwen_image_edit_2511_nvfp4.safetensors#g' "$qwen_edit"
            echo "[INFO] Workflow override: Qwen Image Edit 2511 low -> NVFP4 diffusion filename."
        fi
    fi

    if [ "$NVFP4_SUPPORTED_LC" != "true" ]; then
        return 0
    fi

    local changed=0
    local wf
    for wf in \
        "$workflows_dir/klein-4b-t2i.json" \
        "$workflows_dir/klein-4b-edit.json" \
        "$workflows_dir/klein-9b-t2i.json" \
        "$workflows_dir/klein-9b-edit.json"
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

    local zturbo="$workflows_dir/z-turbo-t2i.json"
    if [ -f "$zturbo" ] && grep -Fq "z_image_turbo_bf16.safetensors" "$zturbo"; then
        sed -i 's/z_image_turbo_bf16\.safetensors/z_image_turbo_nvfp4.safetensors/g' "$zturbo"
        echo "[INFO] NVFP4 workflow override enabled: Z-Image Turbo -> official NVFP4 filename."
    fi

    local zturbo_origin="$workflows_dir/z-turbo-t2i.json"
    if [ -f "$zturbo_origin" ] && grep -Fq "z_image_turbo_bf16.safetensors" "$zturbo_origin"; then
        sed -i 's/z_image_turbo_bf16\.safetensors/z_image_turbo_nvfp4.safetensors/g' "$zturbo_origin"
        echo "[INFO] NVFP4 workflow override enabled: Z-Image Turbo -> official NVFP4 filename."
    fi

    local ewf_er="$workflows_dir/ernie-turbo-t2i.json"
    if [ -f "$ewf_er" ]; then
        # Abiray Turbo: match workflow widget defaults to nvfp4 filenames when list was switched.
        if grep -Fq "ernie-image-turbo-fp8.safetensors" "$ewf_er"; then
            sed -i 's/ernie-image-turbo-fp8\.safetensors/ernie-image-turbo-nvfp4.safetensors/g' "$ewf_er"
            echo "[INFO] NVFP4 workflow override enabled: ERNIE-Image-Turbo -> nvfp4 safetensors filenames."
        fi
    fi

    # Community NVFP4 workflow filename rewrites.
    if [ "$NVFP4_MODE_LC" == "allow-community" ]; then
        local frwf="$workflows_dir/firered-edit.json"
        if [ -f "$frwf" ] && grep -Fq "FireRed-Image-Edit-1.0_fp8mixed_comfy.safetensors" "$frwf"; then
            sed -i 's/FireRed-Image-Edit-1.0_fp8mixed_comfy\.safetensors/FireRed-Image-Edit-1_NVFP4.safetensors/g' "$frwf"
            echo "[INFO] NVFP4 workflow override enabled: FireRed Image Edit -> Starnodes NVFP4 filename."
        fi

        local kreawf="$workflows_dir/flux-krea-t2i.json"
        if [ -f "$kreawf" ] && grep -Fq "flux1-krea-dev_fp8_scaled.safetensors" "$kreawf"; then
            sed -i 's/flux1-krea-dev_fp8_scaled\.safetensors/flux1-krea-dev-nvfp4.safetensors/g' "$kreawf"
            echo "[INFO] NVFP4 workflow override enabled: FLUX.1 Krea Dev -> elihung NVFP4 filename."
        fi

        local ewf_sft="$workflows_dir/ernie-sft-t2i.json"
        if [ -f "$ewf_sft" ] && grep -Fq "ernie-image.safetensors" "$ewf_sft"; then
            sed -i 's/ernie-image\.safetensors/ernie-image-nvfp4.safetensors/g' "$ewf_sft"
            echo "[INFO] NVFP4 workflow override enabled: ERNIE-Image SFT -> Starnodes NVFP4 filename."
        fi

        local zbase="$workflows_dir/z-base-t2i.json"
        if [ -f "$zbase" ] && grep -Fq "z_image_bf16.safetensors" "$zbase"; then
            sed -i 's/z_image_bf16\.safetensors/z-image-base-nvfp4_quality.safetensors/g' "$zbase"
            echo "[INFO] NVFP4 workflow override enabled: Z-Image Base -> community quality NVFP4 filename."
        fi
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

# Workflow seeding: full seed on empty workflows dir; optional pack reseed when JSON already exists.
WORKFLOW_FULL_SEED=0
WORKFLOW_PACK_SEED=0
RESEED_PACK_WORKFLOWS_LC=$(echo "${RESEED_PACK_WORKFLOWS:-false}" | tr '[:upper:]' '[:lower:]')
if workflows_dir_has_json "$WORKFLOWS_DIR"; then
    if [ "$RESEED_PACK_WORKFLOWS_LC" = "true" ] || [ "$RESEED_PACK_WORKFLOWS_LC" = "1" ] || [ "$RESEED_PACK_WORKFLOWS_LC" = "yes" ]; then
        WORKFLOW_PACK_SEED=1
        echo "[INFO] Workflows directory has existing JSON; RESEED_PACK_WORKFLOWS enabled - installing/updating workflows for selected packs."
    else
        echo "[INFO] Workflows directory is not empty (existing JSON). Skipping managed workflow cleanup, bundled workflow seeding, and workflow URL downloads."
        echo "       Set RESEED_PACK_WORKFLOWS=true to add or refresh pack workflows without clearing the folder."
    fi
else
    WORKFLOW_FULL_SEED=1
    WORKFLOW_PACK_SEED=1
fi

if [ "$WORKFLOW_FULL_SEED" -eq 1 ]; then
    cleanup_prev_managed_workflows
fi

# Base install: vram-utils custom nodes + bundled workflows (always, not tied to MODELS_DOWNLOAD).
VR_PACK="${PACKS_DIR}/vram-utils"
if [ "$WORKFLOW_FULL_SEED" -eq 1 ] && [ -d "/workflows/vram-utils" ]; then
    echo "[INFO] Installing base workflows from /workflows/vram-utils..."
    shopt -s nullglob
    for wf in /workflows/vram-utils/*.json; do
        bn=$(basename "$wf")
        dst="$WORKFLOWS_DIR/$bn"
        cp -f "$wf" "$dst"
        register_managed_workflow "$dst"
        echo "  [OK] $bn"
    done
    shopt -u nullglob
fi
N_BASE="${VR_PACK}/nodes.txt"
if [ -f "$N_BASE" ] && [ -s "$N_BASE" ]; then
    echo "[INFO] Installing base custom nodes (vram-utils pack)..."
    while IFS= read -r line || [ -n "$line" ]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue
        git_url=$(echo "$line" | awk '{print $1}')
        if [[ "$git_url" =~ ^https://|^git:// ]]; then
            repo_name=$(basename "$git_url" .git)
            repo_branch=$(echo "$line" | awk '{print $2}')
            target_dir="/app/ComfyUI/custom_nodes/$repo_name"
            sync_custom_node "$git_url" "$repo_branch" "$target_dir" "$repo_name (base)"
        fi
    done < "$N_BASE"
fi

for sel in $SELECTORS_LC; do
    if [ "$sel" == "none" ] || [ "$sel" == "-" ] || [ "$sel" == "core" ]; then
        continue
    fi
    if [ "$sel" == "vram-utils" ] || [ "$sel" == "vram" ] || [ "$sel" == "cleanup" ] || [ "$sel" == "offload" ]; then
        echo "[WARN] vram-utils is installed by default; pack selector '$sel' is deprecated (skipped)."
        continue
    fi

    pack_dir=$(resolve_pack_dir "$sel")
    
    if [ -z "$pack_dir" ]; then
        echo "[WARN] Unknown selector: $sel (skipping)"
        echo "       Valid selectors: $(list_valid_selectors)"
        continue
    fi
    
    # Print pack info
    print_pack_info "$pack_dir"

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
    if [ "$WORKFLOW_PACK_SEED" -eq 1 ] && [ -f "$W" ] && [ -s "$W" ] && grep -q '^https' "$W" 2>/dev/null; then
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

                # Historical cleanup: older newbie pack pointed to a ComfyUI fork
                # (ComfyUI-NewBie) instead of the NewBie custom node repo.
                # Remove stale bad clone to avoid import failures at startup.
                if [ "$repo_name" == "ComfyUI-Newbie-Nodes" ]; then
                    legacy_newbie_dir="/app/ComfyUI/custom_nodes/ComfyUI-NewBie"
                    if [ -d "$legacy_newbie_dir" ] && [ ! -f "$legacy_newbie_dir/__init__.py" ]; then
                        echo "  [WARN] Removing stale legacy node folder: ComfyUI-NewBie"
                        rm -rf "$legacy_newbie_dir"
                    fi
                fi

                sync_custom_node "$git_url" "$repo_branch" "$target_dir" "$repo_name"
            fi
        done < "$N"
    fi

    # Copy tier-appropriate bundled workflows only after pack gating and node sync.
    if [ "$WORKFLOW_PACK_SEED" -eq 1 ]; then
        install_pack_bundled_workflows "$pack_dir"
    fi
done

echo ""

cleanup_legacy_custom_nodes "$CUSTOM_NODES_DIR"
install_reqs "${COMFYUI_DIR}/requirements.txt" "ComfyUI"
install_managed_node_reqs
ensure_impact_pack_python_deps
log_or_install_orphan_node_reqs "$CUSTOM_NODES_DIR"
reconcile_managed_deps

# Download workflows (idempotent: overwrite to refresh, conditional-get skips unchanged)
if [ "$WORKFLOW_PACK_SEED" -eq 1 ] && [ -s "$TEMP_WORKFLOWS" ] && grep -q '^https' "$TEMP_WORKFLOWS" 2>/dev/null; then
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
    register_downloaded_workflows_from_list "$TEMP_WORKFLOWS"
else
    echo "[INFO] No workflow URLs for selected packs."
fi

apply_nvfp4_workflow_overrides "$WORKFLOWS_DIR"

# Align the aggregated download list with NVFP4 before workflow/model sync reads it.
if [ -s "$TEMP_MODELS" ] && grep -q '^https' "$TEMP_MODELS" 2>/dev/null; then
    apply_nvfp4_overrides "$TEMP_MODELS"
fi

# Drop incompatible workflows and append missing model downloads referenced by kept workflows.
write_managed_workflow_manifest
if [ -s "$MANAGED_WORKFLOWS_MANIFEST" ]; then
    echo "########################################"
    echo "[INFO] Syncing workflow model dependencies..."
    echo "########################################"
    python3 /scripts/sync_workflow_models.py \
        --manifest "$MANAGED_WORKFLOWS_MANIFEST" \
        --models-root "$MODELS_DIR" \
        --packs-dir "$PACKS_DIR" \
        --download-list "$TEMP_MODELS" \
        --vram-tier "$VRAM_TARGET" \
        --nvfp4-supported "$NVFP4_SUPPORTED_LC" \
        --nvfp4-mode "$NVFP4_MODE_LC" || echo "[WARN] Workflow/model sync reported issues."
    if [ -f "$MANAGED_WORKFLOWS_MANIFEST" ]; then
        cp "$MANAGED_WORKFLOWS_MANIFEST" "$TEMP_MANAGED_WORKFLOWS"
    fi
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
if [ "$WORKFLOW_PACK_SEED" -eq 1 ]; then
    write_managed_workflow_manifest
fi

patch_comfyui_video_types_py || exit 1
ensure_hidream_transformers

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
    echo "[INFO] LOW_VRAM=false; no automatic VRAM args added."
fi

python3 ./ComfyUI/main.py --listen --port 8188 ${VRAM_RUNTIME_ARGS} ${CLI_ARGS}

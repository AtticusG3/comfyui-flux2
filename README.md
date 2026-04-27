# ComfyUI Flux

Docker-based ComfyUI with selectable model packs, persistent host mounts, API-friendly defaults, and automatic model/workflow downloads.

## Docker Images

| CUDA Version | Image Tag | PyTorch Index |
| --- | --- | --- |
| CUDA 13.0 | `ghcr.io/atticusg3/comfyui-flux2:latest` | `cu130` |
| CUDA 12.8 | `ghcr.io/atticusg3/comfyui-flux2:latest-cu128` | `cu128` |
| CUDA 12.6 | `ghcr.io/atticusg3/comfyui-flux2:latest-cu126` | `cu126` |

Pinned releases use semver tags such as `v1.1.0`, `v1.1.0-cu128`, and `v1.1.0-cu126`.

## Quick Start

1. Copy `.env.example` to `.env`.
2. Set `MODELS_DOWNLOAD` to one or more comma-separated pack selectors.
3. Set `LOW_VRAM=true` for smaller model variants and automatic `--lowvram --reserve-vram` runtime flags.
4. Start the container:

```bash
docker-compose up -d
```

Open ComfyUI at `http://localhost:8188`.

## Docker Compose Example (Copy/Paste)

If you are new to Docker Compose, start from this minimal file:

```yaml
services:
  comfyui:
    container_name: comfyui-flux2
    image: ghcr.io/atticusg3/comfyui-flux2:latest
    restart: unless-stopped
    environment:
      TZ: ${TZ:-UTC}
      MODELS_DOWNLOAD: ${MODELS_DOWNLOAD:-klein-distilled,sdxl-lightning,vram-utils}
      HF_TOKEN: ${HF_TOKEN:-hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX}
      CIVITAI_API_KEY: ${CIVITAI_API_KEY:-}
      LOW_VRAM: ${LOW_VRAM:-true}
      AUTO_VRAM_ARGS: ${AUTO_VRAM_ARGS:-true}
      RESERVE_VRAM_GB: ${RESERVE_VRAM_GB:-1.2}
      NVFP4_SUPPORTED: ${NVFP4_SUPPORTED:-false}
      NVFP4_MODE: ${NVFP4_MODE:-official-only}
      CONNECTIVITY_ROUTE_DEFAULT: ${CONNECTIVITY_ROUTE_DEFAULT:-direct}
      CONNECTIVITY_ROUTE_HUGGINGFACE: ${CONNECTIVITY_ROUTE_HUGGINGFACE:-inherit}
      CONNECTIVITY_ROUTE_GITHUB: ${CONNECTIVITY_ROUTE_GITHUB:-inherit}
      CONNECTIVITY_ROUTE_CIVITAI: ${CONNECTIVITY_ROUTE_CIVITAI:-inherit}
      PROXY_URL: ${PROXY_URL:-}
      HUGGINGFACE_PROXY_URL: ${HUGGINGFACE_PROXY_URL:-}
      GITHUB_PROXY_URL: ${GITHUB_PROXY_URL:-}
      CIVITAI_PROXY_URL: ${CIVITAI_PROXY_URL:-}
      DNS_SERVERS: ${DNS_SERVERS:-}
      HUGGINGFACE_DNS_SERVERS: ${HUGGINGFACE_DNS_SERVERS:-}
      GITHUB_DNS_SERVERS: ${GITHUB_DNS_SERVERS:-}
      CIVITAI_DNS_SERVERS: ${CIVITAI_DNS_SERVERS:-}
    volumes:
      - "./data:/app"
      # Models
      - ~/comfyui/models:/app/ComfyUI/models
      # Workflows
      - ~/comfyui/workflows:/app/ComfyUI/user/default/workflows
      # I/O folders
      - ~/comfyui/output:/app/ComfyUI/output
      - ~/comfyui/input:/app/ComfyUI/input
    ports:
      - "8188:8188"
    gpus: all
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
```

Notes:

- On Linux/macOS, `~` paths work as shown. On Windows, replace those with full paths (for example `C:/comfyui/models:/app/ComfyUI/models`).
- Replace the placeholder `HF_TOKEN` value or set it empty if your selected packs do not require gated Hugging Face downloads.

## API Access

The container exposes ComfyUI's normal UI and local API on port `8188`.

- Submit API-format workflows with `POST /prompt`.
- Inspect available nodes with `GET /object_info`.
- Poll outputs with `GET /history/{prompt_id}`.
- Watch progress with `/ws`.
- Free memory between API jobs with `POST /free` where your client supports it.

This is useful for AnythingLLM, OpenWebUI, and other workflow runners. The default compose binds `8188:8188`; do not expose it directly to untrusted networks without a reverse proxy, firewall, or authentication layer.

## AnythingLLM Companion Skill

This repo ships AnythingLLM-native custom agent skill packages at:

- `anythingllm/agent-skills/comfyui-companion`
- `anythingllm/agent-skills/comfyui-companion-executor`

Included files:

- `plugin.json`
- `handler.js`
- `README.md`

Install by copying that folder into your AnythingLLM storage path:

```text
STORAGE_DIR/plugins/agent-skills/comfyui-companion
```

Then enable it from `Settings > Agent Skills` in AnythingLLM.

For the runnable executor variant, copy:

```text
STORAGE_DIR/plugins/agent-skills/comfyui-companion-executor
```

Executor examples are bundled at:

- `anythingllm/agent-skills/comfyui-companion-executor/examples/workflow-t2i-api.json`
- `anythingllm/agent-skills/comfyui-companion-executor/examples/workflow-edit-api.json`
- `anythingllm/agent-skills/comfyui-companion-executor/examples/workflow-flux2-klein-distilled-t2i-api.json`
- `anythingllm/agent-skills/comfyui-companion-executor/examples/workflow-flux2-klein-distilled-edit-api.json`
- `anythingllm/agent-skills/comfyui-companion-executor/examples/packs/workflow-pack-variant-index.json`

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `MODELS_DOWNLOAD` | Comma-separated pack selectors. Default: `klein-distilled`. |
| `LOW_VRAM` | `true` selects `models-low.txt`/`workflows-low.txt`; `false` selects `models-high.txt`/`workflows-high.txt`. |
| `AUTO_VRAM_ARGS` | `true` auto-derives runtime VRAM flags when `COMFYUI_VRAM_ARGS` and `CLI_ARGS` are empty. |
| `COMFYUI_VRAM_ARGS` | Explicit VRAM flag override, e.g. `--lowvram --reserve-vram 1.5 --cpu-vae`. |
| `RESERVE_VRAM_GB` | Reserve value used when `LOW_VRAM=true` and automatic VRAM args are active. Default: `1.2`. |
| `NVFP4_SUPPORTED` | `true` swaps configured FP8 model URLs to NVFP4 URLs and preserves original NVFP4 output filenames; matching workflows are switched to NVFP4 model references. Default: `false`. |
| `NVFP4_MODE` | NVFP4 source policy: `official-only` (default) uses official model sources only; `allow-community` additionally enables configured community NVFP4 overrides (experimental). |
| `CLI_ARGS` | Extra ComfyUI arguments. If set, automatic VRAM args are not added. |
| `HF_TOKEN` | Hugging Face token for gated models, if a selected pack requires one. |
| `CIVITAI_API_KEY` | Optional Civitai token used by Civicomfy. |
| `CONNECTIVITY_ROUTE_DEFAULT` | Default route policy for provider downloads and git sync: `direct`, `proxy`, `smart-dns`, or `vpn`. |
| `CONNECTIVITY_ROUTE_HUGGINGFACE` | Route override for Hugging Face: `inherit`, `direct`, `proxy`, `smart-dns`, or `vpn`. |
| `CONNECTIVITY_ROUTE_GITHUB` | Route override for GitHub: `inherit`, `direct`, `proxy`, `smart-dns`, or `vpn`. |
| `CONNECTIVITY_ROUTE_CIVITAI` | Route override for Civitai: `inherit`, `direct`, `proxy`, `smart-dns`, or `vpn`. |
| `PROXY_URL` | Global fallback proxy URL used when route is `proxy` and no provider-specific proxy is set. |
| `HUGGINGFACE_PROXY_URL` | Optional Hugging Face specific proxy URL. |
| `GITHUB_PROXY_URL` | Optional GitHub specific proxy URL. |
| `CIVITAI_PROXY_URL` | Optional Civitai specific proxy URL. |
| `DNS_SERVERS` | Global fallback DNS resolver list for `smart-dns` mode (comma-separated, passed to aria2). |
| `HUGGINGFACE_DNS_SERVERS` | Optional Hugging Face specific DNS resolver list for `smart-dns`. |
| `GITHUB_DNS_SERVERS` | Optional GitHub specific DNS resolver list for `smart-dns`. |
| `CIVITAI_DNS_SERVERS` | Optional Civitai specific DNS resolver list for `smart-dns`. |
| `CONNECTIVITY_DOCTOR_ENABLED` | Enables startup preflight probes for Hugging Face, GitHub, and Civitai with configured routing. Default: `true`. |
| `TZ` | Container timezone. |

## Available Packs

| Selector | Type | LOW_VRAM=true | LOW_VRAM=false | Notes |
| --- | --- | --- | --- | --- |
| `klein-distilled` | Image | Flux 2 Klein 4B distilled workflows | Flux 2 Klein 9B distilled workflows | Default Flux pack. Base Klein workflows are removed. |
| `flux1-krea` | Image | FP8 text encoder path | FP16 text encoder path | Natural image style. |
| `hunyuan-video` | Video | T2V only | T2V + I2V | Heavy video pack. |
| `hunyuan-3d` | 3D | Hunyuan3D 2.1 shape-only | Shape + paint/PBR assets | Texture generation can require 21GB+ VRAM. |
| `ace-step` | Audio | ACE-Step 1.5 Turbo AIO | ACE-Step 1.5 XL SFT split files | Lyrics/style/metadata music workflows. |
| `ovis-image` | Image | Ovis image pack | Ovis image pack | Text rendering. |
| `newbie-image` | Image | NewBie image pack | NewBie image pack | Next-DiT 3.5B anime model. Dual encoder (Gemma3 + Jina CLIP v2). XML structured or natural language prompts. Requires ComfyUI-NewBie nodes. |
| `trellis2-gguf` | 3D | Q4 512 GGUF | Q8 1024 GGUF | Experimental Docker support. |
| `wan-2-2` | Video | 5B TI2V + Fun 5B | 14B T2V/I2V + Fun Inpaint/Camera | Official Wan 2.2 is video-first. |
| `sdxl-lightning` | Image | Juggernaut-XL-Lightning 4-step checkpoint (LOW) | Juggernaut-XL-Lightning 8-step checkpoint (HIGH) | Photographic T2I/editing/tiling support. NVFP4 not applicable. |
| `sdxl-editing` | Image | Base + SDXL 1.0 inpaint ckpt | + refiner + 4x UltraSharp | Inpaint, outpaint, img2img (no Lightning). |
| `vram-utils` | Utility | Utility nodes | Utility nodes | Cleanup/offload helpers. |

Example:

```bash
MODELS_DOWNLOAD=klein-distilled,wan-2-2,vram-utils
LOW_VRAM=true
```

Optional NVFP4 path for supported NVIDIA Blackwell systems:

```bash
LOW_VRAM=true
NVFP4_SUPPORTED=true
NVFP4_MODE=official-only
MODELS_DOWNLOAD=klein-distilled
```

Notes:

- In `official-only` mode this currently swaps Klein 4B/9B FP8 URLs to official NVFP4 URLs.
- In `allow-community` mode, configured community Wan 2.2 I2V NVFP4 mixed URLs are also allowed (experimental).
- Local output filenames use original NVFP4 model names; matching workflows are updated to those names.
- `flux1-krea` official NVFP4 URL is currently unverified and remains on FP8 fallback.
- Keep this disabled on unsupported hardware/software. ComfyUI reports NVFP4 acceleration requiring PyTorch CUDA 13.0 and Blackwell GPUs; unsupported stacks can be slower than FP8. See the ComfyUI post: [New ComfyUI Optimizations for NVIDIA GPUs](https://blog.comfy.org/p/new-comfyui-optimizations-for-nvidia).

Runtime VRAM arg precedence:

1. If `COMFYUI_VRAM_ARGS` is set, use it as-is.
2. Else if `AUTO_VRAM_ARGS=false`, add no automatic VRAM args.
3. Else if `CLI_ARGS` is non-empty, add no automatic VRAM args.
4. Else if `LOW_VRAM=true`, add `--lowvram --reserve-vram <RESERVE_VRAM_GB>`.
5. Else (`LOW_VRAM=false`), add no automatic VRAM args.

Connectivity routing examples:

```bash
# Default everything through VPN/tunnel path managed outside container
CONNECTIVITY_ROUTE_DEFAULT=vpn
```

```bash
# Proxy only Hugging Face, keep GitHub/Civitai direct
CONNECTIVITY_ROUTE_DEFAULT=direct
CONNECTIVITY_ROUTE_HUGGINGFACE=proxy
HUGGINGFACE_PROXY_URL=socks5://host.docker.internal:1080
```

```bash
# Smart DNS only for Civitai downloads
CONNECTIVITY_ROUTE_DEFAULT=direct
CONNECTIVITY_ROUTE_CIVITAI=smart-dns
CIVITAI_DNS_SERVERS=1.1.1.1,8.8.8.8
```

Notes:

- `vpn` mode is routing-only metadata in this project. It assumes host or container networking is already routed through a VPN/tunnel.
- `smart-dns` currently affects `aria2` downloads. Git operations still use container resolver/network stack.
- `proxy` mode is applied to both `aria2` downloads and git sync operations for provider-hosted repositories.

## Storage

The compose file keeps ComfyUI source in a named volume and binds data folders to the host:

| Host Path | Container Path |
| --- | --- |
| `./data/models` | `/app/ComfyUI/models` |
| `./data/input` | `/app/ComfyUI/input` |
| `./data/output` | `/app/ComfyUI/output` |
| `./data/workflows` | `/app/ComfyUI/user/default/workflows` |

Models and workflows persist across container rebuilds. Use `docker-compose down -v` only when you intentionally want to remove the ComfyUI named volume.

## Development

Build locally:

```bash
docker-compose build
```

Clean first-run test:

```bash
docker-compose down -v
docker-compose up -d --build
```

Smoke checks:

```bash
docker-compose logs -f comfyui
docker-compose exec comfyui python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8188/object_info').status)"
```

## Releases

This repo tracks the intended release in `VERSION` and `CHANGELOG.md`. Push a semver tag such as `v1.1.0` to publish versioned GHCR tags through the Docker workflow. Do not tag or push until the build and startup smoke checks pass.

## Notes

- Trellis2 GGUF is experimental in this Linux container because upstream Trellis2 nodes rely on compiled wheels that can be sensitive to Python, Torch, and CUDA versions.
- Custom node requirements are filtered so they cannot downgrade `torch`, `torchvision`, `torchaudio`, or `xformers` from the image build.
- ComfyUI, ComfyUI-Manager, Civicomfy, and pack-specific custom nodes update on container start.

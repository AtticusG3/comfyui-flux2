# ComfyUI (Docker, multi-pack)

Dockerized [ComfyUI](https://github.com/comfyanonymous/ComfyUI) with **selectable model packs**, persistent mounts, API-friendly defaults, and startup sync for models and workflows. Image tags remain `ghcr.io/atticusg3/comfyui-flux2` for compatibility.

## Contents

- [Quick Start](#quick-start)
- [Docker images and PyTorch](#docker-images-and-pytorch)
- [Blackwell (RTX 50 series) and NVFP4](#blackwell-rtx-50-series-and-nvfp4)
- [Screenshots](#screenshots)
- [Docker Compose example](#docker-compose-example-copypaste)
- [API access](#api-access)
- [AnythingLLM companion skill](#anythingllm-companion-skill)
- [Environment variables](#environment-variables)
- [Available packs](#available-packs)
- [Runtime VRAM precedence](#runtime-vram-arg-precedence)
- [Connectivity routing](#connectivity-routing-examples)
- [Storage](#storage)
- [Development](#development)
- [Releases](#releases)
- [Notes](#notes)

## Quick Start

1. Copy `.env.example` to `.env`.
2. Set `MODELS_DOWNLOAD` to one or more pack selectors, or `none` for ComfyUI only (VRAM helper nodes and base workflows still install).
3. Set `LOW_VRAM=true` for smaller model variants and automatic `--lowvram --reserve-vram` runtime flags when `CLI_ARGS` is empty.
4. `docker-compose up -d` and open `http://localhost:8188`.

## Docker images and PyTorch

Published images install **stable** `torch`, `torchvision`, `torchaudio`, and `xformers` from `https://download.pytorch.org/whl/<cu*>` (see [Dockerfile](Dockerfile)). That matches the tag suffix.

| Image tag | PyTorch wheel index | Channel | Typical use |
| --- | --- | --- | --- |
| `ghcr.io/atticusg3/comfyui-flux2:latest` | `cu130` | Stable wheels from PyTorch index | Default; CUDA 13.0 driver stack |
| `...:latest-cu128` | `cu128` | Stable | CUDA 12.8 (e.g. Blackwell host drivers) |
| `...:latest-cu126` | `cu126` | Stable | Older driver stacks |

Pinned semver tags follow the same pattern, for example `v1.4.0`, `v1.4.0-cu128`, `v1.4.0-cu126`.

**Nightly / RTX 50 note:** Some Blackwell setups require **PyTorch nightly** builds from `https://download.pytorch.org/whl/nightly/cu130` or `nightly/cu128` (see [EigenFunction32/ComfyUI-docker](https://github.com/EigenFunction32/ComfyUI-docker) README table pattern). This repository’s **published** images do not switch to nightly automatically; advanced users can build locally with a different index if needed.

**CUDA 13.1 / 13.2:** A **nightly** `cu132` directory exists on the PyTorch download host. **Stable** `cu131` / `cu132` plus matching **xformers** for our Dockerfile layout was not verified at release time; do not assume `-cu131` / `-cu132` tags until `docker build` is confirmed for all four wheels.

Verify GPU and PyTorch inside a running container:

```bash
docker compose exec comfyui python -c "import torch; print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

## Blackwell (RTX 50 series) and NVFP4

- **Drivers:** NVIDIA documents RTX 50 / Blackwell with recent **570+** drivers and CUDA **12.8+** on the host; match your image tag (`latest` vs `latest-cu128`) to what `nvidia-smi` reports as the maximum CUDA version for the driver.
- **NVFP4 in ComfyUI:** See [New ComfyUI Optimizations for NVIDIA GPUs](https://blog.comfy.org/p/new-comfyui-optimizations-for-nvidia-gpus). Enable only on supported stacks; unsupported hardware can be slower than FP8.

**Environment flags (this repo)**

| Variable | Values | Role |
| --- | --- | --- |
| `NVFP4_SUPPORTED` | `true` / `false` | When `true`, enables URL/filename swaps for **official** NVFP4 where configured (e.g. Klein FP8 to official NVFP4). |
| `NVFP4_MODE` | `official-only` (default) or `allow-community` | `allow-community` additionally enables **experimental** community NVFP4 URLs (Wan I2V, **FireRed Image Edit** Starnodes quant, etc.). |

There is no `NVFP4_MODE=true`; use `NVFP4_SUPPORTED=true` together with `NVFP4_MODE` as above.

**Optional tooling (advanced, not installed by this image)**

- [comfy_kitchen](https://github.com/Comfy-Org/comfy-kitchen) and [ComfyUI_Kitchen_nvfp4_Converter](https://github.com/tritant/ComfyUI_Kitchen_nvfp4_Converter) for NVFP4 conversion workflows.
- **SageAttention 2/3:** Building optimized attention kernels for Blackwell is described in community Docker guides such as [mmartial/ComfyUI-Nvidia-Docker](https://github.com/mmartial/ComfyUI-Nvidia-Docker) (`userscripts_dir`). This image does not compile SageAttention; use SDPA / default attention if a workflow references `sageattn` and fails.

**firered-image-edit pack:** With `NVFP4_SUPPORTED=true` and `NVFP4_MODE=allow-community`, startup swaps cocorang **FP8-mixed** FireRed weights to **Starnodes** `FireRed-Image-Edit-1_NVFP4.safetensors` and rewrites the bundled workflow default filename.

## Screenshots

Add images under `docs/images/` and reference them here (paths are optional until files exist).

| Placeholder | Description |
| --- | --- |
| `docs/images/comfyui-ui.png` | ComfyUI default UI after first start |
| `docs/images/pack-example.png` | Example loaded workflow from a pack |
| `docs/images/nvfp4-settings.png` | Document `NVFP4_*` env usage if desired |

See [docs/images/README.md](docs/images/README.md).

## Docker Compose Example (Copy/Paste)

```yaml
services:
  comfyui:
    container_name: comfyui
    image: ghcr.io/atticusg3/comfyui-flux2:latest
    restart: unless-stopped
    environment:
      TZ: ${TZ:-UTC}
      MODELS_DOWNLOAD: ${MODELS_DOWNLOAD:-klein-distilled,sdxl-lightning}
      HF_TOKEN: ${HF_TOKEN:-}
      CIVITAI_API_KEY: ${CIVITAI_API_KEY:-}
      LOW_VRAM: ${LOW_VRAM:-true}
      NVFP4_SUPPORTED: ${NVFP4_SUPPORTED:-false}
    volumes:
      - "./data/models:/app/ComfyUI/models"
      - "./data/workflows:/app/ComfyUI/user/default/workflows"
      - "./data/output:/app/ComfyUI/output"
      - "./data/input:/app/ComfyUI/input"
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

- On Windows hosts, use full paths instead of `~` for volume bind mounts.
- Set `HF_TOKEN` when any selected pack requires gated Hugging Face downloads (for example `klein-distilled`).
- **VRAM helper nodes** (former `vram-utils` pack) are **always** installed; you do not need `vram-utils` in `MODELS_DOWNLOAD`.

## API Access

The container exposes ComfyUI on port `8188`.

- `POST /prompt` — submit API-format workflows.
- `GET /object_info` — list nodes.
- `GET /history/{prompt_id}` — poll outputs.
- WebSocket `/ws` — progress.
- `POST /free` — free VRAM between jobs when supported.

Do not expose `8188` to untrusted networks without a reverse proxy or auth.

## AnythingLLM Companion Skill

Bundled skills:

- `anythingllm/agent-skills/comfyui-companion`
- `anythingllm/agent-skills/comfyui-companion-executor`

Copy into AnythingLLM storage, for example `STORAGE_DIR/plugins/agent-skills/comfyui-companion`, then enable under Settings.

Executor examples include `anythingllm/agent-skills/comfyui-companion-executor/examples/workflow-flux2-klein-distilled-t2i-api.json` and `workflow-pack-variant-index.json`.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `MODELS_DOWNLOAD` | Comma-separated pack selectors, or `none`. Default in `docker-compose.yml`: `none`. |
| `LOW_VRAM` | `true` uses `models-low.txt` / `workflows-low.txt`; `false` uses high-tier lists. |
| `AUTO_VRAM_ARGS` | When `true` and `COMFYUI_VRAM_ARGS` / `CLI_ARGS` empty, add automatic VRAM flags. |
| `COMFYUI_VRAM_ARGS` | Explicit VRAM override. |
| `RESERVE_VRAM_GB` | Used with `LOW_VRAM=true` and auto VRAM args. Default `1.2`. |
| `NVFP4_SUPPORTED` | `true` enables configured NVFP4 URL and workflow filename overrides. |
| `NVFP4_MODE` | `official-only` or `allow-community` (community NVFP4 for Wan, FireRed, etc.). |
| `CLI_ARGS` | Extra ComfyUI args; disables auto VRAM derivation when set. |
| `HF_TOKEN` | Required when a selected pack marks gated Hugging Face models. |
| `CIVITAI_API_KEY` | Optional Civitai token for Civicomfy. |
| `CONNECTIVITY_ROUTE_*` | `direct`, `proxy`, `smart-dns`, `vpn` for downloads/git. |
| `PROXY_URL`, `*_PROXY_URL`, `DNS_SERVERS`, `*_DNS_SERVERS` | Connectivity overrides. |
| `CONNECTIVITY_DOCTOR_ENABLED` | Startup probes. Default `true`. |
| `TZ` | Timezone. |

## Available Packs

| Selector | Type | LOW_VRAM=true | LOW_VRAM=false | Notes |
| --- | --- | --- | --- | --- |
| `klein-distilled` | Image | Flux 2 Klein 4B distilled | Flux 2 Klein 9B distilled | Requires `HF_TOKEN`. |
| `firered-image-edit` | Image | FireRed 1.0 FP8-mixed + Qwen VL FP8 + VAE + Lightning LoRA | BF16 diffusion + BF16 Qwen | [Comfy workflow](https://www.comfy.org/workflows/image_firered_image_edit1_1-c0198b907108/), [low VRAM article](https://aistudynow.com/how-to-fix-firered-image-edit-in-comfyui-my-custom-workflow-for-low-vram/). Bundled JSON defaults to **LOW** filenames; on HIGH tier set UNETLoader / CLIPLoader widgets to the BF16 artifact names from `models-high.txt`. Community NVFP4 with `NVFP4_SUPPORTED=true` and `NVFP4_MODE=allow-community`. |
| `flux1-krea` | Image | FP8 text encoder | FP16 text encoder | |
| `hunyuan-video` | Video | T2V | T2V + I2V | Heavy. |
| `hunyuan-3d` | 3D | Shape | Shape + PBR | |
| `ace-step` | Audio | Turbo AIO | XL SFT split | |
| `ovis-image` | Image | Ovis pack | Ovis pack | |
| `newbie-image` | Image | NewBie pack | NewBie pack | Requires NewBie nodes. |
| `trellis2-gguf` | 3D | Q4 GGUF | Q8 GGUF | Experimental. |
| `wan-2-2` | Video | 5B stack | 14B stack | |
| `sdxl-lightning` | Image | 4-step | 8-step | |
| `sdxl-editing` | Image | Inpaint base | + refiner / upscale | |
| `ernie-image` | Image | Turbo FP8 path | SFT BF16 | See pack `pack.json`. |

**`vram-utils`:** Installed for every run (KJNodes, rgthree, essentials, Easy-Use + `workflows/vram-utils`). The selector `vram-utils` (and aliases) is **deprecated** and skipped if listed.

Example:

```bash
MODELS_DOWNLOAD=klein-distilled,wan-2-2
LOW_VRAM=true
NVFP4_SUPPORTED=true
NVFP4_MODE=official-only
```

With `NVFP4_MODE=allow-community`, community NVFP4 URLs (Wan I2V, FireRed Starnodes) may apply where configured in `entrypoint.sh`.

## Runtime VRAM arg precedence

1. If `COMFYUI_VRAM_ARGS` is set, use it as-is.
2. Else if `AUTO_VRAM_ARGS=false`, add no automatic VRAM args.
3. Else if `CLI_ARGS` is non-empty, add no automatic VRAM args.
4. Else if `LOW_VRAM=true`, add `--lowvram --reserve-vram <RESERVE_VRAM_GB>`.
5. Else add no automatic VRAM args.

## Connectivity routing examples

```bash
CONNECTIVITY_ROUTE_DEFAULT=vpn
```

```bash
CONNECTIVITY_ROUTE_DEFAULT=direct
CONNECTIVITY_ROUTE_HUGGINGFACE=proxy
HUGGINGFACE_PROXY_URL=socks5://host.docker.internal:1080
```

```bash
CONNECTIVITY_ROUTE_DEFAULT=direct
CONNECTIVITY_ROUTE_CIVITAI=smart-dns
CIVITAI_DNS_SERVERS=1.1.1.1,8.8.8.8
```

`vpn` is routing metadata only. `smart-dns` applies to aria2 downloads.

## Storage

Typical bind mounts:

| Host | Container |
| --- | --- |
| `./data/models` | `/app/ComfyUI/models` |
| `./data/input` | `/app/ComfyUI/input` |
| `./data/output` | `/app/ComfyUI/output` |
| `./data/workflows` | `/app/ComfyUI/user/default/workflows` |

ComfyUI code may live in a named volume depending on compose; see your `docker-compose.yml`.

## Development

```bash
docker compose build
docker compose config
docker compose down -v
docker compose up -d --build
docker compose logs -f comfyui
```

## Releases

Version in `VERSION` and history in `CHANGELOG.md`. Tag `v*` to publish versioned GHCR tags via CI.

## Notes

- Trellis2 GGUF support is experimental.
- Custom node `requirements.txt` installs filter `torch`, `torchvision`, `torchaudio`, and `xformers` so they cannot downgrade the image stack.
- ComfyUI, ComfyUI-Manager, Civicomfy, base VRAM nodes, and pack nodes sync on startup.

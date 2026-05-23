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
| `ghcr.io/atticusg3/comfyui-flux2:main` | `cu130` | Same as `latest` on `main` builds | Branch-style pin |
| `ghcr.io/atticusg3/comfyui-flux2:v1.6.3` | `cu130` | Same stack, semver pin | Reproducible release |

CI publishes **cu130 only** (no `-cu126` / `-cu128` matrix tags). For other CUDA indexes, build locally with `docker build --build-arg CUDA_VERSION=cu128`.

**Nightly / RTX 50 note:** Some Blackwell setups require **PyTorch nightly** builds from `https://download.pytorch.org/whl/nightly/cu130` or `nightly/cu128` (see [EigenFunction32/ComfyUI-docker](https://github.com/EigenFunction32/ComfyUI-docker) README table pattern). This repository's **published** images do not switch to nightly automatically; advanced users can build locally with a different index if needed.

**CUDA 13.1 / 13.2:** A **nightly** `cu132` directory exists on the PyTorch download host. **Stable** `cu131` / `cu132` plus matching **xformers** for our Dockerfile layout was not verified at release time; do not assume `-cu131` / `-cu132` tags until `docker build` is confirmed for all four wheels.

Verify GPU and PyTorch inside a running container:

```bash
docker compose exec comfyui python -c "import torch; print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

## Blackwell (RTX 50 series) and NVFP4

- **Drivers:** NVIDIA documents RTX 50 / Blackwell with recent **570+** drivers and CUDA **12.8+** on the host; match your image tag (`latest` vs `latest-cu128`) to what `nvidia-smi` reports as the maximum CUDA version for the driver.
- **NVFP4 in ComfyUI:** See [New ComfyUI Optimizations for NVIDIA GPUs](https://blog.comfy.org/p/new-comfyui-optimizations-for-nvidia-gpus). Enable only on supported stacks; unsupported hardware can be slower than FP8.

### Environment Flags

| Variable | Values | Role |
| --- | --- | --- |
| `NVFP4_SUPPORTED` | `true` / `false` | When `true`, enables URL/filename swaps for **official** NVFP4 where configured (e.g. Klein FP8 to official NVFP4). |
| `NVFP4_MODE` | `official-only` (default) or `allow-community` | `allow-community` additionally enables **experimental** community NVFP4 URLs (Wan I2V, **FireRed Image Edit** Starnodes quant, etc.). |

There is no `NVFP4_MODE=true`; use `NVFP4_SUPPORTED=true` together with `NVFP4_MODE` as above.

### Optional Tooling

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

- `POST /prompt` -- submit API-format workflows.
- `GET /object_info` -- list nodes.
- `GET /history/{prompt_id}` -- poll outputs.
- WebSocket `/ws` -- progress.
- `POST /free` -- free VRAM between jobs when supported.

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
| `CONNECTIVITY_ROUTE_*` | `direct`, `proxy`, `smart-dns`, `vpn` for downloads/git. |
| `PROXY_URL`, `*_PROXY_URL`, `DNS_SERVERS`, `*_DNS_SERVERS` | Connectivity overrides. |
| `COMFYUI_GIT_UPDATE` | `true` fetches/resets managed repos on startup. Set `false` for faster restarts when local refs are already current. |
| `RESEED_PACK_WORKFLOWS` | `true` (compose default) installs or refreshes bundled and URL workflows for selected packs even when `./data/workflows` already has JSON. `false` keeps first-start-only seeding. |
| `INSTALL_ORPHAN_NODE_REQS` | `false` installs requirements only for managed nodes. Set `true` to also install manual/orphan custom-node requirements from the persisted volume. |
| `TZ` | Timezone. |

## Available Packs

| Selector | Type | LOW_VRAM=true | LOW_VRAM=false | Notes |
| --- | --- | --- | --- | --- |
| `klein-distilled` | Image | Flux 2 Klein 4B distilled | Flux 2 Klein 9B distilled | Requires `HF_TOKEN`. |
| `firered-image-edit` | Image | FireRed 1.0 FP8-mixed + Qwen VL FP8 + VAE + Lightning LoRA | BF16 diffusion + BF16 Qwen | [Comfy workflow](https://www.comfy.org/workflows/image_firered_image_edit1_1-c0198b907108/), [low VRAM article](https://aistudynow.com/how-to-fix-firered-image-edit-in-comfyui-my-custom-workflow-for-low-vram/). Bundled JSON defaults to **LOW** filenames; on HIGH tier set UNETLoader / CLIPLoader widgets to the BF16 artifact names from `models-high.txt`. Community NVFP4 with `NVFP4_SUPPORTED=true` and `NVFP4_MODE=allow-community`. |
| `realvisxl` | Image | RealVisXL V5 Lightning FP16 | RealVisXL V5 FP16 + latent hires-fix workflow | Focused photoreal SDXL pack using RealVisXL defaults: DPM++ SDE Karras, strong anatomy negatives, and hires detail pass on high tier. |
| `flux1-krea` | Image | FP8 text encoder | FP16 text encoder | |
| `hunyuan-video` | Video | T2V | T2V + I2V | Heavy. |
| `hunyuan-3d` | 3D | Shape | Shape + PBR | |
| `ace-step` | Audio | Turbo AIO | XL SFT split | |
| `ovis-image` | Image | Ovis pack | Ovis pack | |
| `newbie-image` | Image | NewBie pack | NewBie pack | Requires NewBie nodes. |
| `wan-2-2` | Video | 5B stack | 14B stack | |
| `sdxl-lightning` | Image | 4-step | 8-step | |
| `sdxl-editing` | Image | Inpaint base | + refiner / upscale | |
| `ernie-image` | Image | Turbo FP8 path | SFT BF16 | See pack `pack.json`. |
| `flux2` | Image | (workflows only) | (workflows only) | Optional Flux.2 Klein JSON bundle; pair with `klein-distilled` for weights. |
| `z-image-turbo` | Image | Z-Image Turbo + Qwen FP8 text encoder | Z-Image Turbo + Qwen BF16 text encoder | Focused fast distilled Z-Image workflow. `NVFP4_SUPPORTED=true` swaps diffusion to official `z_image_turbo_nvfp4.safetensors`. |
| `z-image-base` | Image | Z-Image Base + Qwen FP8 text encoder | Z-Image Base + Qwen BF16 text encoder | Focused non-distilled Base workflow. `NVFP4_SUPPORTED=true` + `NVFP4_MODE=allow-community` can swap diffusion to marcorez8 quality NVFP4. |
| `z-image-anime` | Image | Z-Anime NVFP4 (r0b0tlab) + SeeSee21 FP8 TE/VAE | Z-Anime BF16 base + 4-step distill + BF16 TE/VAE | Large HF downloads; bundled `Z-Anime T2I.json` only. |
| `qwen-image-edit-2511` | Image | NVFP4 diffusion + Qwen TE/VAE | FP8 diffusion + Qwen TE/VAE | Weights only; build or import a 2511 edit graph in ComfyUI. |
| `hidream-o1` | Image | nodes + workflow only | nodes + workflow only | HiDream O1 custom nodes + example workflow. Download FP8/BF16 weights via Manager or HF after startup. Startup upgrades `transformers>=4.57.1` when this pack is selected. |

**`vram-utils` (always on):** Syncs KJNodes, rgthree-comfy, ComfyUI_essentials, ComfyUI-Easy-Use, ComfyUI-SeedVR2_VideoUpscaler, ComfyUI_LayerStyle, ComfyUI-Detail-Daemon, was-node-suite-comfyui, [comfyui-openai-api](https://github.com/hekmon/comfyui-openai-api) (Ollama/OpenRouter/OpenAI-compatible LLM nodes for bundled prompt workflows), plus `workflows/vram-utils` when the workflows directory is empty on first start. The pack selector `vram-utils` is **deprecated** and skipped if listed.

Startup installs requirements for managed nodes only by default (collated into one pip pass). Custom nodes left on the persisted volume from old packs or manual installs are still importable by ComfyUI, but their requirements are skipped unless `INSTALL_ORPHAN_NODE_REQS=true`; use ComfyUI Manager **Try fix** after startup for manual nodes, or remove stale folders. Known legacy orphans (Trellis2-GGUF, inference-gpu, openai-api, bad ComfyUI-NewBie clone without `__init__.py`) are removed automatically when not managed.

Example:

```bash
MODELS_DOWNLOAD=klein-distilled,wan-2-2
LOW_VRAM=true
NVFP4_SUPPORTED=true
NVFP4_MODE=official-only
```

With `NVFP4_MODE=allow-community`, community NVFP4 URLs (Wan I2V, FireRed Starnodes, Z-Image Base quality quant) may apply where configured in `entrypoint.sh`.

## Runtime VRAM arg precedence

1. If `COMFYUI_VRAM_ARGS` is set, use it as-is.
2. Else if `AUTO_VRAM_ARGS=false`, add no automatic VRAM args.
3. Else if `CLI_ARGS` is non-empty, add no automatic VRAM args.
4. Else if `LOW_VRAM=true`, add `--lowvram --reserve-vram <RESERVE_VRAM_GB>`.
5. Else add no automatic VRAM args.

## Connectivity routing examples

Connectivity variables are read by `scripts/entrypoint.sh` at container runtime. Add any you use to the `environment:` block in `docker-compose.yml` (or an `env_file`); values in a host `.env` file are not passed through unless compose lists them.

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

Staged ComfyUI git sync skips `models/`, `input/`, `output/`, and `user/default/workflows/` during rsync so bind mounts are not deleted (`Device or resource busy`). Pack bundled workflows copy into `./data/workflows` on first start (empty folder). With `RESEED_PACK_WORKFLOWS=true`, changing `MODELS_DOWNLOAD` and restarting adds or overwrites pack workflow files without clearing your folder.

**Maintainers:** validate workflow JSON and pack coverage before PRs:

```bash
pip install jsonschema==4.26.0   # Python 3.10+
python scripts/validate_workflow_json.py workflows/
python scripts/validate_workflow_json.py --pack-audit workflows/
```

Structural checks use vendored [ComfyWorkflow 0.4/1.0](https://docs.comfy.org/specs/workflow_json) schemas under `schemas/comfy/`. Model/node lists: `python scripts/audit_workflow_assets.py` (CI on `scripts/` or `workflows/` changes). Agent skill: `.cursor/skills/validate-comfyui-workflow/`.

## Development

`scripts/` (entrypoint, packs, `scripts/lib/git_sync.sh`, patches) are **baked into the image**, not bind-mounted. After changing startup scripts, rebuild before testing:

```bash
docker compose build
docker compose config
docker compose down -v
docker compose up -d --build
docker compose logs -f comfyui
```

## Releases

Version in `VERSION` and history in `CHANGELOG.md`. Tag `v*` to publish cu130 images to GHCR (`latest`, `main`, `vX.Y.Z`, `X.Y`).

**Registry hygiene:** GitHub Actions workflow [Registry cleanup](.github/workflows/registry-cleanup.yml) (or `scripts/registry_cleanup.py` / `scripts/cleanup-registry.ps1`) prunes clutter:

- Deletes all `*-cu126` / `*-cu128` GHCR versions.
- Keeps `latest`, `main`, and the **highest patch per semver major** (e.g. `v1.6.3` for major `1`).
- Deletes other GHCR versions with fewer than 2 total downloads (configurable).
- Deletes older GitHub **releases** that are not in the keep set (not the source repo).

Run a dry run first: `python scripts/registry_cleanup.py` or Actions -> Registry cleanup (leave **Apply** unchecked). Requires `gh` auth with `read:packages` and `delete:packages`.

To push to a Gitea host without storing a token in `git remote`, set **`GITEA_TOKEN`** (and optionally **`GITEA_USER`**, **`GITEA_HOST`**, **`GITEA_REPO_PATH`**) in your environment, keep `origin` as a plain `https://.../owner/repo.git` URL, then run **`scripts/gitea-push.ps1`** (Windows) or **`scripts/gitea-push.sh`** (Linux/macOS). Pass ref names as arguments when not on a branch (for example `main` `v1.5.0`). If the server reports the repository is a read-only mirror, push from the non-mirror upstream instead.

## Notes

- Image wheels include `av`, `sageattention`, and best-effort `flash-attn` (build installs `packaging`/`wheel` first; may still skip if no compatible wheel for your torch+cuda build). **xformers** and **sageattention** are the reliable attention backends in published images.
- Custom node `requirements.txt` installs filter `torch`, `torchvision`, `torchaudio`, and `xformers` so they cannot downgrade the image stack.
- ComfyUI, ComfyUI-Manager, base VRAM nodes, and pack nodes sync on startup via staged git (`scripts/lib/git_sync.sh`: fetch into staging, rsync on success; failed fetch leaves the live tree untouched).
- Before ComfyUI starts, `scripts/patch_video_types_rotation.py` patches `comfy_api/latest/_input_impl/video_types.py` for PyAV builds that lack `frame.rotation` (uses `metadata["rotate"]` fallback). A failed patch when the rotation block is missing aborts startup.
- The runtime image has no compilers. If a managed node update adds a source-only Python dependency, rebuild the image or use ComfyUI Manager **Try fix**; optional future `build-deps` compose profile can add `build-essential` when needed.

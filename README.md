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

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `MODELS_DOWNLOAD` | Comma-separated pack selectors. Default: `klein-distilled`. |
| `LOW_VRAM` | `true` selects `models-low.txt`/`workflows-low.txt`; `false` selects `models-high.txt`/`workflows-high.txt`. |
| `AUTO_VRAM_ARGS` | `true` auto-derives runtime VRAM flags when `COMFYUI_VRAM_ARGS` and `CLI_ARGS` are empty. |
| `COMFYUI_VRAM_ARGS` | Explicit VRAM flag override, e.g. `--lowvram --reserve-vram 1.5 --cpu-vae`. |
| `RESERVE_VRAM_GB` | Reserve value used when `LOW_VRAM=true` and automatic VRAM args are active. Default: `1.2`. |
| `CLI_ARGS` | Extra ComfyUI arguments. If set, automatic VRAM args are not added. |
| `HF_TOKEN` | Hugging Face token for gated models, if a selected pack requires one. |
| `CIVITAI_API_KEY` | Optional Civitai token used by Civicomfy. |
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
| `newbie-image` | Image | NewBie image pack | NewBie image pack | Anime/XML prompt style. |
| `trellis2-gguf` | 3D | Q4 512 GGUF | Q8 1024 GGUF | Experimental Docker support. |
| `wan-2-2` | Video | 5B TI2V + Fun 5B | 14B T2V/I2V + Fun Inpaint/Camera | Official Wan 2.2 is video-first. |
| `sdxl-lightning` | Image | SDXL + 4/8-step Lightning LoRAs | Adds refiner/detail path | Photographic T2I/editing/tiling support. |
| `sdxl-editing` | Image | Base + SDXL 1.0 inpaint ckpt | + refiner + 4x UltraSharp | Inpaint, outpaint, img2img (no Lightning). |
| `vram-utils` | Utility | Utility nodes | Utility nodes | Cleanup/offload helpers. |

Example:

```bash
MODELS_DOWNLOAD=klein-distilled,wan-2-2,vram-utils
LOW_VRAM=true
```

Runtime VRAM arg precedence:

1. If `COMFYUI_VRAM_ARGS` is set, use it as-is.
2. Else if `AUTO_VRAM_ARGS=false`, add no automatic VRAM args.
3. Else if `CLI_ARGS` is non-empty, add no automatic VRAM args.
4. Else if `LOW_VRAM=true`, add `--lowvram --reserve-vram <RESERVE_VRAM_GB>`.
5. Else (`LOW_VRAM=false`), add no automatic VRAM args.

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

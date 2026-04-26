# Local Testing Setup

This guide is for Windows with Docker Desktop and an NVIDIA GPU.

## Prerequisites

- Windows 10 21H2+ or Windows 11
- Docker Desktop with WSL 2 backend enabled
- NVIDIA driver with WSL GPU support

Verify GPU passthrough:

```powershell
docker run --rm --gpus=all nvcr.io/nvidia/k8s/cuda-sample:nbody nbody -gpu -benchmark
```

## Configure

From the repository root:

```powershell
copy .env.example .env
```

Edit `.env`:

```text
LOW_VRAM=true
MODELS_DOWNLOAD=klein-distilled,vram-utils
AUTO_VRAM_ARGS=true
NVFP4_SUPPORTED=false
```

Use `LOW_VRAM=false` for high-tier GPUs. Set `HF_TOKEN` only when a selected model requires it.

`LOW_VRAM` controls both model/workflow tier selection and, by default, runtime flags:

- `LOW_VRAM=true` -> use `models-low.txt` and `workflows-low.txt`
- `LOW_VRAM=false` -> use `models-high.txt` and `workflows-high.txt`

`NVFP4_SUPPORTED=true` optionally swaps the Klein 4B FP8 URL to the 4B NVFP4 URL (when `klein-distilled` is selected) while keeping local model filenames unchanged so existing workflows still resolve the same model names.

## Build And Run

```powershell
docker-compose up -d --build
```

Open `http://localhost:8188`.

## Useful Commands

| Command | Description |
| --- | --- |
| `docker-compose logs -f comfyui` | Stream startup and download logs. |
| `docker-compose restart comfyui` | Test update/restart path. |
| `docker-compose down` | Stop containers and keep data. |
| `docker-compose down -v` | Remove containers and named volumes. |
| `docker-compose config` | Validate compose syntax. |

## Troubleshooting

- GPU not detected: verify Docker Desktop WSL integration and retry the NVIDIA sample command.
- Out of VRAM: set `LOW_VRAM=true`, keep `AUTO_VRAM_ARGS=true`, or set `COMFYUI_VRAM_ARGS=--lowvram --reserve-vram 1.5 --cpu-vae`.
- API clients timing out: wait for model downloads and ComfyUI startup to finish, then check `http://localhost:8188/object_info`.
- Trellis2 GGUF fails to import: treat it as experimental and check upstream wheel compatibility for your Python/Torch/CUDA combination.

Runtime flag precedence (highest to lowest):

1. `COMFYUI_VRAM_ARGS` (explicit override)
2. `AUTO_VRAM_ARGS=false` (disable automatic flags)
3. non-empty `CLI_ARGS` (disable automatic flags)
4. `LOW_VRAM=true` + auto mode -> `--lowvram --reserve-vram <RESERVE_VRAM_GB>`
5. `LOW_VRAM=false` + auto mode -> no extra VRAM flags

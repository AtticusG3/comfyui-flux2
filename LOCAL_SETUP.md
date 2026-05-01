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
MODELS_DOWNLOAD=klein-distilled
AUTO_VRAM_ARGS=true
NVFP4_SUPPORTED=false
NVFP4_MODE=official-only
```

Use `LOW_VRAM=false` for high-tier GPUs. Set `HF_TOKEN` only when a selected model requires it.

`LOW_VRAM` controls both model/workflow tier selection and, by default, runtime flags:

- `LOW_VRAM=true` -> use `models-low.txt` and `workflows-low.txt`
- `LOW_VRAM=false` -> use `models-high.txt` and `workflows-high.txt`

`NVFP4_SUPPORTED=true` enables NVFP4 URL overrides while keeping local model filenames unchanged so existing workflows still resolve the same model names.

`NVFP4_MODE` controls source policy:

- `official-only` (default): official NVFP4 URLs only (Klein 4B and 9B).
- `allow-community`: also enables configured community NVFP4 overrides (Wan 2.2 I2V mixed checkpoints; FireRed Image Edit Starnodes quant; experimental).

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
- **GGUF / `OSError: [Errno 19] No such device` in `numpy.memmap` / `ComfyUI-GGUF`**: GGUF loaders memory-map weights. **`mmap` can return `ENODEV`** when the **backing filesystem** does not support mapping that file normally, even if read/write works. That includes **Docker bind mounts backed by NFS/SMB**, **paths on Gluster/other FUSE**, and **Docker Desktop virtiofs binds from Windows**. On a **Linux VM** (e.g. **Debian on Proxmox**), common causes are **`./data/models` on a NAS or network mount**, **`/var/lib/docker`** on shared storage, or bind mounts onto those. **Mitigation:** keep `.gguf` files on **local VM disk** (ext4/xfs/ZFS block device, etc.), use a **named volume** on local disk, or copy weights off network mounts before load.
- Trellis2 GGUF fails to import: treat it as experimental and check upstream wheel compatibility for your Python/Torch/CUDA combination.

Runtime flag precedence (highest to lowest):

1. `COMFYUI_VRAM_ARGS` (explicit override)
2. `AUTO_VRAM_ARGS=false` (disable automatic flags)
3. non-empty `CLI_ARGS` (disable automatic flags)
4. `LOW_VRAM=true` + auto mode -> `--lowvram --reserve-vram <RESERVE_VRAM_GB>`
5. `LOW_VRAM=false` + auto mode -> no extra VRAM flags

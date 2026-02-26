# Local Testing Setup (Windows PC)

Step-by-step guide to run ComfyUI Flux2 locally on your Windows machine.

## Prerequisites

1. **NVIDIA GPU** with CUDA 12.1 or newer
2. **Windows 10 21H2+** or **Windows 11**
3. **WSL 2** enabled

## 1. Install WSL 2 and update kernel

In PowerShell (Run as Administrator):

```powershell
wsl --install
wsl --update
```

Restart if prompted. Verify WSL 2:

```powershell
wsl -l -v
```

Both `docker-desktop` and your distro (e.g. Ubuntu) should show `VERSION 2`.

## 2. Install NVIDIA driver for WSL

1. Download the latest **Game Ready** or **Studio** driver from [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx)
2. Install on Windows (no special CUDA-on-WSL driver needed; standard drivers include WSL support)
3. Verify: open WSL and run `nvidia-smi` (should show your GPU)

## 3. Install Docker Desktop

1. Download [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
2. Install and start Docker Desktop
3. In **Settings > General**, enable **Use the WSL 2 based engine**
4. In **Settings > Resources > WSL Integration**, enable your Linux distro
5. Apply & Restart

Verify GPU support:

```powershell
docker run --rm -it --gpus=all nvcr.io/nvidia/k8s/cuda-sample:nbody nbody -gpu -benchmark
```

If this runs without error, GPU passthrough is working.

## 4. Configure the project

From the project root:

1. Copy env template (optional):

   ```powershell
   copy .env.example .env
   ```

2. Edit `.env`:
   - Set `HF_TOKEN=your_token` if using klein-distilled (get from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens))
   - Set `LOW_VRAM=true` for ~16GB VRAM GPUs
   - Change `MODELS_DOWNLOAD` to select packs (see README for options)

3. Data directories already created: `data/models`, `data/input`, `data/output`, `data/workflows`

## 5. Build and run

```powershell
cd "C:\Cursor IDE\comfyui-flux2\comfyui-flux2"
docker-compose up -d --build
```

First run builds the image and downloads models; this can take 10–30+ minutes depending on pack(s).

## 6. Access ComfyUI

Open **http://localhost:8188** in your browser.

## Useful commands

| Command | Description |
|---------|-------------|
| `docker-compose up -d --build` | Build and start in background |
| `docker-compose logs -f` | Stream container logs |
| `docker-compose down` | Stop and remove containers (keeps data volumes) |
| `docker-compose down -v` | Stop and remove containers and volumes |

## Troubleshooting

- **GPU not detected**: Ensure NVIDIA driver is installed on Windows, WSL kernel is up to date (`wsl --update`), and Docker Desktop uses WSL 2 backend.
- **HF_TOKEN required**: For klein-distilled, create a token at huggingface.co and add it to `.env`.
- **Out of VRAM**: Set `LOW_VRAM=true` in `.env` and add `CLI_ARGS=--lowvram --reserve-vram 1.2` to `docker-compose.yml` under `environment:`.
- **Bind mount errors**: Ensure `data/models`, `data/input`, `data/output`, and `data/workflows` exist; they are created during setup.

# ComfyUI Flux

ComfyUI Flux is a Docker-based setup for running [ComfyUI](https://github.com/comfyanonymous/ComfyUI) with Flux.2 Klein models and additional features.

## Features

- Dockerized ComfyUI environment
- Automatic installation of ComfyUI and ComfyUI-Manager
- **Low VRAM Mode**: Download and use FP8 models for reduced VRAM usage
- Pre-configured with Flux.2 Klein models, text encoders, and VAEs
- Easy model management and updates
- GPU support with CUDA 12.6, 12.8 (default), or 13.0

## Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with CUDA support (for GPU acceleration)
- (Optional) Huggingface account and token (for downloading Flux.2 Klein diffusion models)

## Quick Start

1. (Optional) Create a `.env` file in the project root and add your Huggingface token:

   ```bash
   # For downloading Flux.2 Klein diffusion model files.
   # Get your token from https://huggingface.co/settings/tokens
   HF_TOKEN=your_huggingface_token
   ```

2. Download the `docker-compose.yml` file:

   ```bash
   wget https://raw.githubusercontent.com/AtticusG3/comfyui-flux2/main/docker-compose.yml
   ```

   Alternatively, you can create a `docker-compose.yml` file and copy/paste the following contents:

   ```yaml
   services:
     comfyui:
       container_name: comfyui
       image: atticusg3/comfyui-flux2:latest
       restart: unless-stopped
       ports:
         - "8188:8188"
       volumes:
         - "./data:/app"
       environment:
         - CLI_ARGS=
         - HF_TOKEN=${HF_TOKEN}
         - HUNYUAN3D=${HUNYUAN3D:-false}
         - LOW_VRAM=${LOW_VRAM:-false}
         - MODELS_DOWNLOAD=${MODELS_DOWNLOAD}
       deploy:
         resources:
           reservations:
             devices:
               - driver: nvidia
                 device_ids: ['0']
                 capabilities: [gpu]
   ```

   **Note:** The default Docker image uses CUDA 12.8 (`cu128`). If you require a specific CUDA version, you can specify the tag in the image name. For example:

   ```yaml
   image: atticusg3/comfyui-flux2:cu130
   ```

3. Run the container using Docker Compose:

   ```bash
   docker-compose up -d
   ```

   **Note:** The first time you run the container, it will download all the included models before starting up. This process may take some time depending on your internet connection.

4. Access ComfyUI in your browser at `http://localhost:8188`

## Environment Variables

- `HF_TOKEN` - Your Hugging Face access token. **Required** to download the Flux.2 Klein diffusion models. Not required for Hunyuan3D-2 models.
- `HUNYUAN3D` - Set to `true` for Hunyuan3D-2 (3D asset generation). See [Hunyuan3D-2 Mode](#hunyuan3d-2-mode) section.
- `LOW_VRAM` - Set to `true` for Flux.2 Klein 4B models (lower VRAM), or `false` for 9B models. See [Low VRAM Mode](#low-vram-mode) section.
- `MODELS_DOWNLOAD` - Comma-separated list specifying which Flux.2 Klein variants to download (`klein-base`, `klein-distilled`). If not set, both variants will be downloaded. Only applies when using Flux.2 Klein.
- `CLI_ARGS` - Additional command-line arguments to pass directly to the ComfyUI.

## Hunyuan3D-2 Mode

By setting the `HUNYUAN3D` environment variable to `true`, the container will download Hunyuan3D-2 models and workflows for 3D asset generation. This option is mutually exclusive with Flux.2 Klein (when `HUNYUAN3D=true`, Flux models are not downloaded).

**Included models:**
- Multi-view: `hunyuan3d-dit-v2-mv.safetensors`, `hunyuan3d-dit-v2-mv-turbo.safetensors`
- Single-view: `hunyuan3d-dit-v2.safetensors`
- Texture generation: `hunyuan3d-paint-v2-0.safetensors` (for use with ComfyUI-Hunyuan3DWrapper)

**Workflows:** Multi-view, multi-view turbo, and single-view workflow images (drag into ComfyUI to load).

Enable Hunyuan3D-2 Mode:

```bash
HUNYUAN3D=true
```

See the [ComfyUI Hunyuan3D-2 docs](https://docs.comfy.org/tutorials/3d/hunyuan3D-2) and [ComfyUI Wiki guide](https://comfyui-wiki.com/en/tutorial/advanced/3d/huanyuan3d-2) for usage.

## Low VRAM Mode

By setting the `LOW_VRAM` environment variable to `true`, the container will download and use the Flux.2 Klein 4B models. When `LOW_VRAM=false`, the container downloads Flux.2 Klein 9B models. (Ignored when `HUNYUAN3D=true`.)

Enable Low VRAM Mode:

```bash
LOW_VRAM=true
```

## Model Files

Overview of the model files that will be downloaded when using this container.  
The Flux.2 Klein diffusion model files require a `HF_TOKEN` for download.

### When `LOW_VRAM=false` (default)

The following model files will be downloaded by default, unless specified otherwise in `MODELS_DOWNLOAD`:

| Type | Model File Name | Size | Notes |
|-------------|-------------------------------|---------|-------------------------------------------------|
| Diffusion | flux-2-klein-base-9b-fp8.safetensors |  | requires `HF_TOKEN` for download |
| Diffusion | flux-2-klein-9b-fp8.safetensors |  | requires `HF_TOKEN` for download |
| Text Encoder | qwen_3_8b_fp8mixed.safetensors |  | |
| VAE | flux2-vae.safetensors |  | |

### When `LOW_VRAM=true`

| Type | Model File Name | Size | Notes |
|-------------|-------------------------------|---------|-------------------------------------------------|
| Diffusion | flux-2-klein-base-4b-fp8.safetensors |  | requires `HF_TOKEN` for download |
| Diffusion | flux-2-klein-4b-fp8.safetensors |  | requires `HF_TOKEN` for download |
| Text Encoder | qwen_3_4b.safetensors |  | |
| VAE | flux2-vae.safetensors |  | |

### When `HUNYUAN3D=true`

| Type | Model File Name | Location | Notes |
|-------------|----------------------------------|---------------------------|-------------------------------------------------|
| Multi-view (base) | hunyuan3d-dit-v2-mv.safetensors | checkpoints/ | ~5 GB |
| Multi-view (turbo) | hunyuan3d-dit-v2-mv-turbo.safetensors | checkpoints/ | ~5 GB |
| Single-view | hunyuan3d-dit-v2.safetensors | checkpoints/ | ~5 GB |
| Texture (Paint) | hunyuan3d-paint-v2-0.safetensors | diffusion_models/ | ~2 GB, requires ComfyUI-Hunyuan3DWrapper |

## Workflows

Download the workflow JSON files below and drag them into ComfyUI to load the corresponding workflows.

### Flux.2 Klein 4B (LOW_VRAM=true)

| Flux.2 Klein 4B Text-to-Image | Flux.2 Klein 4B Image Edit Base | Flux.2 Klein 4B Image Edit Distilled |
|-------------------------------|---------------------------------|--------------------------------------|
| [Download](./workflows/workflow-flux2-klein-4b-text-to-image.json) | [Download](./workflows/workflow-flux2-klein-4b-image-edit-base.json) | [Download](./workflows/workflow-flux2-klein-4b-image-edit-distilled.json) |

### Flux.2 Klein 9B (LOW_VRAM=false)

| Flux.2 Klein 9B Text-to-Image | Flux.2 Klein 9B Image Edit Base | Flux.2 Klein 9B Image Edit Distilled |
|-------------------------------|---------------------------------|--------------------------------------|
| [Download](./workflows/workflow-flux2-klein-9b-text-to-image.json) | [Download](./workflows/workflow-flux2-klein-9b-image-edit-base.json) | [Download](./workflows/workflow-flux2-klein-9b-image-edit-distilled.json) |

### Hunyuan3D-2 (HUNYUAN3D=true)

Workflow images (with embedded JSON) are auto-downloaded to ComfyUI. Drag them into ComfyUI to load: `hunyuan-3d-multiview-elf.webp`, `hunyuan-3d-turbo.webp`, `hunyuan3d-non-multiview-train.webp`.

## Updating

The ComfyUI and ComfyUI-Manager are automatically updated when the container starts. To update the base image and other dependencies, pull the latest version of the Docker image using:

```bash
docker-compose pull
```

## Additional Notes

- **Switching Between Modes**: If you change the `LOW_VRAM` or `HUNYUAN3D` setting after the initial run, the container will automatically download the required models for the new setting upon restart.
- **Model Selection**: Use the optional `MODELS_DOWNLOAD` environment variable to specify which Flux.2 Klein variants to download:
  - `MODELS_DOWNLOAD="klein-base"`: Download only the base model
  - `MODELS_DOWNLOAD="klein-distilled"`: Download only the distilled model
  - `MODELS_DOWNLOAD="klein-base,klein-distilled"` or not set: Download both models (default)
  - Dependencies (VAE and text encoders) are always included
- **Model Downloading**: The scripts are designed to skip downloading models that already exist, so you won't waste bandwidth re-downloading models you already have.
- **Huggingface Token**: The `HF_TOKEN` is necessary for downloading Flux.2 Klein diffusion models.

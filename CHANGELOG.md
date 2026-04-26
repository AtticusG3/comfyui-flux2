# Changelog

## 1.2.1

- Added optional `NVFP4_SUPPORTED` flag to switch Klein 4B low-VRAM downloads from FP8 to NVFP4 while keeping workflow-compatible local filenames.
- Wired `NVFP4_SUPPORTED` through `entrypoint.sh`, `.env.example`, `docker-compose.yml`, and setup/docs guidance.
- Improved startup robustness by installing requirements for all detected custom nodes under `custom_nodes/`.

## 1.2.0

- Added `sdxl-editing` pack (base + SDXL 1.0 inpaint weights, bundled inpaint/outpaint/img2img workflows).
- Added experimental Trellis2 GGUF, Wan 2.2, SDXL Lightning, and VRAM utility packs.
- Upgraded ACE-Step to 1.5 and Hunyuan3D to 2.1 model sources.
- Made `LOW_VRAM` affect ComfyUI runtime VRAM flags, with explicit override controls.
- Documented runtime flag precedence for `LOW_VRAM`, `AUTO_VRAM_ARGS`, `COMFYUI_VRAM_ARGS`, `RESERVE_VRAM_GB`, and `CLI_ARGS`.
- Added repeatable per-pack custom node syncing and protected the container Torch stack from custom-node requirement downgrades.
- Renamed bundled Flux 2 Klein workflows to human-readable filenames.
- Removed Flux 2 Klein base workflows and kept only distilled variants in shipped workflow bundles.
- Pack lists and metadata use low/high VRAM tiers (`models-low.txt`, `models-high.txt`, `workflows-low.txt`, `workflows-high.txt`) instead of 16GB/20GB naming.
- Added Cursor rules for Karpathy-inspired engineering principles and Caveman Ultra brevity.

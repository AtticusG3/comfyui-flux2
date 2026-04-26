# Changelog

## 1.2.0 - Unreleased

- Added `sdxl-editing` pack (base + SDXL 1.0 inpaint weights, bundled inpaint/outpaint/img2img workflows).
- Added experimental Trellis2 GGUF, Wan 2.2, SDXL Lightning, and VRAM utility packs.
- Upgraded ACE-Step to 1.5 and Hunyuan3D to 2.1 model sources.
- Made `LOW_VRAM` affect ComfyUI runtime VRAM flags, with explicit override controls.
- Added repeatable per-pack custom node syncing and protected the container Torch stack from custom-node requirement downgrades.
- Renamed bundled Flux 2 Klein workflows to human-readable filenames.
- Pack lists and metadata use low/high VRAM tiers (`models-low.txt`, `notes_low`, etc.) instead of 16GB/20GB naming.
- Added Cursor rules for Karpathy-inspired engineering principles and Caveman Ultra brevity.

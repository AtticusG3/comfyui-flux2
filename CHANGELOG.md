# Changelog

## [1.2.7] -- Trellis Linux Hardening and SDXL Lightning Realignment

### Fixed
- Hardened Trellis2 GGUF dependency install in `entrypoint.sh` for Linux containers by attempting direct `cumesh`/`flex-gemm` installation before invoking upstream installer logic that can select platform-mismatched wheels.
- Updated SDXL Lightning pack model URLs to the RunDiffusion `Juggernaut_RunDiffusionPhoto2_Lightning_4Steps.safetensors` artifact for both low/high VRAM tiers to avoid invalid/removed prior checkpoint references.

### Changed
- Aligned `sdxl-lightning` workflows (`low`, `full`, `high`) to the RunDiffusion 4-step checkpoint filename.
- Applied RealVis-style high-tier defaults in `sdxl-lightning-workflow-high.json` (negative prompt, 5-step first pass, DPM++ SDE Karras, CFG 2.0).
- Added a real hires-fix chain to `sdxl-lightning-workflow-high.json`: first-pass decode -> model upscale -> VAE encode -> second-pass 3-step denoise (0.5) -> final decode/save.
- Added `4x_NMKD-Superscale-SP_178000_G.pth` to SDXL Lightning high-tier model downloads while keeping `4x-UltraSharp.pth`.
- Updated SDXL Lightning pack metadata/tutorial links and high-tier notes to match RunDiffusion + RealVis guidance.

## [1.2.6] -- Workflow Packaging and Naming Consistency

### Fixed
- Startup workflow deployment is now selector-scoped and convergent: only workflows for selected `MODELS_DOWNLOAD` packs/options are kept after startup, and stale previously managed workflow files are removed.
- Removed unconditional copy of the full `/workflows/` tree at startup to prevent unrelated pack workflows from being distributed.
- Added managed workflow manifest tracking to keep workflow state deterministic across pack switches.
- Updated default prompt seeds in Flux 2 Klein distilled text-to-image workflows to replace stale placeholder examples.

### Added
- Added `workflows-bundled.txt` mapping support in pack startup logic to map source workflow files to human-readable deployed filenames.
- Added per-pack bundled workflow mappings for:
  - `klein-distilled`
  - `newbie-image`
  - `ovis-image`
  - `flux1-krea`
  - `sdxl-lightning`
  - `hunyuan-3d`

### Changed
- Normalized Hunyuan Video workflow output names to human-readable `out=` values for low/high VRAM variants.
- Extended NVFP4 workflow filename rewrite coverage to include new human-readable Klein workflow names.

## [1.2.5] -- Round 2: NewBie Pack Remediation

### Fixed
- newbie-image pack completely rebuilt after architecture misidentification in the initial prompt run. The model is Next-DiT (NewBie-image-Exp0.1), not SDXL. Changes:
  - Replaced the workflow set with clean low/high variants derived from the official Comfy-Org template (`image_newbieimage_exp0_1-t2i.json`).
  - Added `ComfyUI-NewBie` custom node repo to `scripts/packs/newbie-image/nodes.txt` (`https://github.com/E-Anlia/ComfyUI-NewBie`).
  - Set low/high tier workflow runtime defaults for newbie variants (low: 20 steps, 896x896; high: 28 steps, 1024x1024).
  - Removed SDXL-style negative-prompt injection for newbie variants and restored XML-structured themed prompts aligned with the pack's expected prompt format.
  - Updated README newbie-image pack notes to reflect Next-DiT architecture and dual-encoder requirements.

### Audited
- Ran a read-only workflow contamination audit across non-newbie packs after prior global prompt injection pass; flagged anomalies for manual follow-up without auto-modifying other packs.

## [Unreleased]

### Added

- Bundled pack workflow JSONs into the repo for packs that previously fetched workflow JSON at runtime; startup now deploys bundled workflow trees from `/workflows/`.
- Migrated `sdxl-lightning` from ByteDance SDXL Lightning checkpoints to RunDiffusion Juggernaut-XL-Lightning checkpoints (4-step low, 8-step high) with tuned sampler defaults.
- Added automated low/high workflow tuning passes and default-value normalization across bundled workflows.
- Extended NVFP4 handling docs and startup behavior to preserve original NVFP4 model filenames and align workflow references.

### Changed

- Startup workflow deployment now recursively copies the full `/workflows/` subtree and emits `[OK] Bundled workflows deployed from /workflows/`.
- `sdxl-lightning` pack documentation now reflects Juggernaut-XL-Lightning defaults and notes that NVFP4 is not applicable.

## 1.2.3

- Removed duplicate bypassed `SaveImage` nodes from all bundled Flux 2 Klein workflows, leaving a single active save path per workflow.
- Fixed Trellis2 GGUF custom node sync list by removing duplicate same-name repo entries that could overwrite each other during startup.
- Updated NVFP4 Klein override mapping to use canonical official 4B/9B NVFP4 URLs and more robust FP8 filename-based matching.

## 1.2.2

- Added `NVFP4_MODE` with `official-only`/`allow-community` policy and extended NVFP4 overrides to cover Flux 2 Klein 4B and 9B URLs while preserving workflow-compatible local filenames.
- Updated `sdxl-lightning` to prefer all-in-one SDXL Lightning checkpoints in ComfyUI (`4step` low tier, `8step` high tier) instead of default LoRA-first pack behavior.
- Removed duplicate Klein workflow template downloads, keeping bundled `Flux 2 Klein*` workflows as the canonical set.
- Simplified both Klein text-to-image workflows by removing the legacy bypassed second model branch used for base/distilled switching.
- Added Trellis2 node source coverage by including `aeroex/ComfyUI-Trellis2-GGUF` in the Trellis pack node list.
- Aligned Docker publish tags with local usage by removing branch-ref (`:main`) image tag generation from CI metadata.
- Replaced `AGENTS.md` with a concise project operations guide covering startup behavior, pack policy, NVFP4 rules, SDXL Lightning defaults, and release checklist.

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

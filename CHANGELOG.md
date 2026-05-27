# Changelog

## Unreleased

## [1.7.2] -- Dedupe aria2 model downloads by output path

### Fixed
- Startup dedupes aggregated pack model lists by `dir=` + `out=` before aria2 runs, so multiple packs requesting the same file (e.g. `vae/ae.safetensors`) no longer race and trigger a false `[ERROR] Model download failed` when one GID completes and another errors.

## [1.7.1] -- ComfyUI core tree repair after git rsync

### Fixed
- ComfyUI staged git rsync uses root-anchored excludes (`/models/`, `/input/`, `/output/`, `/custom_nodes/`, `/user/default/workflows/`) so unanchored `models/` no longer deletes `comfy/ldm/models/autoencoder.py`.
- Rsync `protect` filters keep bind-mounted `models`, `input`, `output`, `custom_nodes`, and `user/default/workflows` from being pruned on `--delete`.
- Startup re-syncs `comfy/ldm/models` from staging, repairs from git or staging cache when missing, and aborts with `[ERROR]` if `autoencoder.py` is still missing (checked after ComfyUI sync and again before ComfyUI start).

## [1.7.0] -- Bundled workflow refresh, short names, Klein and Qwen edit packs

### Added
- `klein-distilled` ships four bundled Klein workflows (`klein-4b-t2i.json`, `klein-4b-edit.json`, `klein-9b-t2i.json`, `klein-9b-edit.json`) from `workflows/flux2/`; NVFP4 filename sed unchanged.
- `qwen-image-edit-2511` bundled Comfy-Org image-edit workflow (`qwen-edit-2511.json`) with Lightning 4-step LoRA; high tier rewrites UNET to FP8 at startup.
- `sdxl-lightning` photoreal hires workflow (`sdxl-lightning-hires.json`) and `sdxl-editing` img2img/inpaint/outpaint workflows.
- `hunyuan-video` import guide stub (`hunyuan-video-guide.json`).
- Shared enhancement subgraph templates under `workflows/_templates/` (SeedVR2, Detail Daemon, Upscaler, LLM prompt).
- Maintainer scripts: `rename_workflows_short.py`, `replace_saveimageplus.py`, `gen_klein_4b_workflows.py`, `fix_qwen_edit_workflow.py`, `merge_enhancement_templates.py`, `extract_workflow_templates.py`.

### Changed
- All pack bundled workflows use short kebab-case deploy names matching repo filenames (`source|dest|tier` with identical basenames).
- `entrypoint.sh` workflow override paths updated for new filenames; Qwen edit tier sed for FP8 vs NVFP4.
- `qwen-image-edit-2511` workflow now uses the Comfy-Org Qwen Image Edit 2511 subgraph instead of the FireRed-derived graph shell.
- Bundled workflows: replace `LayerUtility: SaveImagePlus` with core `SaveImage` (LayerStyle no longer required for saves).
- `flux2` pack is workflow-deprecated; Klein selectors live on `klein-distilled`.
- `update_workflow_prompts.py` and `audit_workflow_assets.py` aligned with renamed workflow paths.

### Removed
- One-off maintainer scratch scripts (`_av3d_notes.py`, `_hunyuan_video.py`, `_mk_sdxl_hires.py`, `replace_plain_with_donor.py`).

## [1.6.5] -- Workflow JSON validation and Z-Anime VRAM overrides

### Added
- `scripts/validate_workflow_json.py`: validate bundled workflows against vendored ComfyWorkflow 0.4/1.0 schemas, dangling links, optional `--pack-audit`.
- Vendored schemas under `schemas/comfy/` (from [docs.comfy.org](https://docs.comfy.org/specs/workflow_json) specs).
- Cursor skill `.cursor/skills/validate-comfyui-workflow/` for maintainer lint workflow.

### Changed
- `apply_nvfp4_workflow_overrides()`: Z-Anime `Z-Anime T2I.json` high tier maps legacy `8step-bf16` to `4step-bf16`; post-sed grep verifies distill/TE filenames per `VRAM_TARGET`.
- README and LOCAL_SETUP document dev validation commands (`jsonschema`, Python 3.10+).

## [1.6.4] -- cu130-only publishes and registry cleanup

### Added
- `scripts/registry_cleanup.py` and workflow `.github/workflows/registry-cleanup.yml` to prune legacy `-cu126`/`-cu128` GHCR versions, low-download package versions, and superseded GitHub releases (keeps `latest`, `main`, highest patch per semver major).
- `scripts/cleanup-registry.ps1` wrapper for local dry runs.

### Changed
- Docker CI builds and publishes **cu130 only** (removed CUDA matrix); image tags are `latest`, `main`, `vX.Y.Z`, and `X.Y` without CUDA suffixes.

## [1.6.3] -- Pack workflow reseed and ComfyUI git sync on bind mounts

### Added
- `RESEED_PACK_WORKFLOWS` (default `true` in `docker-compose.yml`): install or refresh bundled and URL workflows for selected packs when `./data/workflows` already contains JSON, without wiping the folder.

### Changed
- ComfyUI staged git rsync excludes bind-mounted `models/`, `input/`, `output/`, and `user/default/workflows/` and uses `--no-group --no-owner` to avoid Docker Desktop `chgrp` / `Device or resource busy` noise.

## [1.6.2] -- Startup hygiene and dependency hardening

### Added
- Base vram-utils: [comfyui-openai-api](https://github.com/hekmon/comfyui-openai-api) for bundled LLM prompt workflows (Ollama, OpenRouter, OpenAI-compatible APIs).
- Staged git sync helper (`scripts/lib/git_sync.sh`) with retries and atomic apply via rsync.
- Collated managed custom-node requirements install (single pip pass with shared stamp).
- Startup cleanup of known legacy orphan custom-node folders (Trellis2-GGUF, inference-gpu, openai-api, bad ComfyUI-NewBie clone).

### Changed
- Removed connectivity doctor startup probes (routing summary and download/git routing unchanged).
- Removed Civicomfy from bootstrap and startup sync.
- Docker flash-attn bake installs `packaging`, `wheel`, and `setuptools` before optional build.
- `hidream-o1` pack syncs nodes and bundled workflow only; model weights via Manager/HF after startup.

### Removed
- `CIVITAI_API_KEY` and `CONNECTIVITY_DOCTOR_ENABLED` environment variables.

## [1.6.1] -- Startup dependency and image build optimization

### Changed
- Startup now installs requirements for managed nodes only by default and skips manual/orphan node requirements unless `INSTALL_ORPHAN_NODE_REQS=true`.
- Runtime requirement installs are stamp-aware, so unchanged ComfyUI and managed custom-node requirements are skipped on warm restarts.
- Custom-node git sync is deduplicated across vram-utils and selected packs.
- Docker builds now pre-bake ComfyUI, Manager, and vram-utils Python dependencies into the image venv.

### Fixed
- Reduced dependency churn that could downgrade `transformers` and OpenCV after ComfyUI startup requirements were installed.
- Added `pip` and `libopengl0` to reduce custom-node import warnings in the container.

## [1.6.0] -- RealVisXL, HiDream O1, workflow dependency gating

### Added
- Pack: `realvisxl` with RealVisXL V5.0 Lightning low-tier and full RealVisXL V5.0 high-tier model lists.
- Workflows: RealVisXL fast photoreal Lightning workflow and high-tier photoreal hires workflow with RealVisXL-recommended sampler, CFG, negative prompt, and detail-pass defaults.
- Pack: `hidream-o1` with Saganaki22 HiDream O1 custom nodes, FP8/BF16 model folder downloads, and bundled example workflow.
- Packs: focused `z-image-turbo` and `z-image-base` selectors alongside the combined `z-image-anime` pack.
- Workflow/model dependency sync script for managed workflow validation and model backfill.

### Changed
- Startup now registers URL-downloaded workflows for dependency sync and runs bundled workflow installation after pack gating/node sync.
- HiDream O1 startup ensures compatible Qwen3-VL `transformers` support.
- Z-Image Base workflow now references the Comfy-Org `z_image_bf16.safetensors` artifact.
- `z-image-anime` selectors no longer alias `z-image-turbo`, so the focused Turbo selector resolves to the dedicated pack.
- Documentation and pack selector examples updated for RealVisXL, HiDream O1, and focused Z-Image packs.

## [1.5.0] -- Packs (flux2, Z-Image/Z-Anime, Qwen Edit 2511), deps, startup workflow policy

### Added
- Docker image: `av`, `sageattention`, best-effort `flash-attn`; builder libav dev headers; runtime `ffmpeg`.
- ComfyUI-Manager: ensure `user/__manager/config.ini` sets `security_level = weak` after install.
- ComfyUI: patch `comfy_api/latest/_input_impl/video_types.py` for PyAV rotation fallback (`rotation` vs `metadata["rotate"]`).
- Packs: `flux2` (optional Klein workflow bundle; pair with `klein-distilled` for weights), `z-image-anime` (Comfy-Org Z-Image Turbo + SeeSee21 Z-Anime models; bundled Z workflows), `qwen-image-edit-2511` (1038lab FP8 + Bedovyy NVFP4 + shared Qwen Image TE/VAE; no bundled graph).
- Base custom nodes: SeedVR2 Video Upscaler, LayerStyle, Detail Daemon, WAS Node Suite (with existing vram-utils set).

### Changed
- Startup: if `user/default/workflows` already contains any `*.json`, skip managed workflow cleanup, bundled workflow copies, workflow URL downloads, and manifest rewrite (models and custom nodes still apply).
- `klein-distilled`: removed bundled Flux Klein workflow install (use `flux2` pack for those JSON files).
- `vram-utils` `nodes.txt`: expanded default node list (see README).
- `scripts/update_workflow_prompts.py`: Trellis scenes removed; scenes for `flux2/`, Z-Image, Z-Anime, ERNIE, FireRed, SDXL Lightning; `pack_name` updates.

### Removed
- `trellis2-gguf` pack and Trellis AnythingLLM routing/templates; `workflows/trellis2-gguf/` examples removed.

### Fixed
- NVFP4 Klein workflow override list aligned to `FLUX.2 Klein …` destination filenames only.

## [1.4.0] -- FireRed pack, base vram-utils, default MODELS_DOWNLOAD=none

### Added
- New `firered-image-edit` pack (`MODELS_DOWNLOAD=firered-image-edit`): FireRed Image Edit 1.0 diffusion from cocorang (FP8-mixed low, BF16 high), Qwen 2.5 VL text encoder (Comfy-Org FP8 low / FireRedTeam BF16 high), VAE and Lightning LoRA from FireRedTeam; bundled workflow `workflows/firered-image-edit/FireRed Image Edit 1.0 - Image Edit.json` with **ModelSamplingAuraFlow removed** (black-output fix per community guidance).
- `docs/images/README.md` for optional screenshot assets.

### Changed
- `MODELS_DOWNLOAD` default is **`none`** (no implicit `klein-distilled`); set packs explicitly in `.env` / compose.
- **vram-utils** custom nodes and `workflows/vram-utils/` are **always** installed before pack processing; selecting `vram-utils` in `MODELS_DOWNLOAD` is deprecated and skipped with a warning.
- `apply_nvfp4_overrides`: when `NVFP4_SUPPORTED=true` and `NVFP4_MODE=allow-community`, swap FireRed cocorang FP8-mixed URL to Starnodes `FireRed-Image-Edit-1_NVFP4.safetensors`.
- `apply_nvfp4_workflow_overrides`: same gating rewrites the bundled FireRed workflow default diffusion filename to the Starnodes NVFP4 name.
- README: multi-model positioning, Eigen-style CUDA / stable vs nightly notes, consolidated **Blackwell and NVFP4** section (kitchen + converter links, SageAttention pointer), screenshots placeholders, `docker-compose.yml` default `MODELS_DOWNLOAD=none`.
- `.env.example`, `LOCAL_SETUP.md`, `AGENTS.md`, AnythingLLM companion README updated for the above.

## [1.3.3] -- ERNIE Turbo: Abiray FP8/NVFP4 safetensors (NVFP4 like Klein)

### Changed
- `ernie-image` low VRAM tier uses Abiray [ERNIE-Image-Turbo-FP8-NVFP4](https://huggingface.co/Abiray/ERNIE-Image-Turbo-FP8-NVFP4) **safetensors** in `models/diffusion_models` and core `UNETLoader` (replacing Unsloth GGUF + city96).
- When `NVFP4_SUPPORTED=true`, `apply_nvfp4_overrides` swaps the Turbo download to `ernie-image-turbo-nvfp4.safetensors` (same HF repo), matching Flux Klein NVFP4 policy.
- Removed `scripts/packs/ernie-image/nodes.txt` (no longer require ComfyUI-GGUF for the default Turbo path).

### Documentation
- `LOCAL_SETUP.md`: expanded GGUF mmap / `ENODEV` troubleshooting for NFS, bind mounts, and Linux VMs (e.g. Proxmox).

## [1.3.2] -- Git safe.directory startup fix

### Fixed
- Git 2.35+ `fatal: detected dubious ownership` on `/app/ComfyUI` (and clones under `custom_nodes/`) when volume ownership differs from the container user. The entrypoint now registers `safe.directory '*'` once so startup can fetch and reset repos instead of exiting under `set -e` and looping with `restart: unless-stopped`.

## [1.3.1] -- ERNIE Low VRAM: Unsloth GGUF + city96 ComfyUI-GGUF

### Changed
- `ernie-image` low VRAM tier now downloads Unsloth `ernie-image-turbo-Q5_K_M.gguf` to `models/unet` (replaces Abiray FP8 safetensors in `diffusion_models`).
- Added `scripts/packs/ernie-image/nodes.txt` to install [city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF).
- `ERNIE-Image-Turbo - Text to Image.json` uses `UnetLoaderGGUF` for the Turbo path (city96) instead of core `UNETLoader`.
- NVFP4 community path: when `NVFP4_SUPPORTED=true` and `NVFP4_MODE=allow-community`, swap Q5_K_M -> `ernie-image-turbo-UD-Q5_K_M.gguf` on the same Unsloth repo (model list + workflow rewrite); removed Abiray FP8/NVFP4 safetensors override.

## [1.3.0] -- ERNIE-Image Pack and Themed Prompt Refresh

### Added
- New `ernie-image` pack (`MODELS_DOWNLOAD=ernie-image`) for Baidu's 8B Diffusion Transformer text-to-image model:
  - High VRAM tier downloads the official Comfy-Org repackaged ERNIE-Image SFT (~16GB BF16, ~50 steps).
  - Low VRAM tier downloads the community ERNIE-Image-Turbo FP8 quant from `Abiray/ERNIE-Image-Turbo-FP8-NVFP4` (~8.2GB, 8-step distilled).
  - Both tiers ship the `ministral-3-3b` text encoder, `ernie-image-prompt-enhancer` (3B PE), and `flux2-vae`.
  - Bundles the official Comfy-Org workflow templates as `ERNIE-Image - Text to Image.json` and `ERNIE-Image-Turbo - Text to Image.json`. The Turbo workflow is patched to load the FP8 quant filename and Abiray repo URL.
- Selectors: `ernie-image`, `ernie`, `ernieimage`.

### Changed
- Extended `apply_nvfp4_overrides` in `scripts/entrypoint.sh` to swap the ERNIE-Image-Turbo FP8 community quant for the NVFP4 community quant (~4.8GB) when `NVFP4_SUPPORTED=true` and `NVFP4_MODE=allow-community`.
- Extended `apply_nvfp4_workflow_overrides` to rewrite the bundled ERNIE-Image-Turbo workflow filename references (`ernie-image-turbo-fp8.safetensors` -> `ernie-image-turbo-nvfp4.safetensors`) under the same gating.
- Refreshed base Flux 2 Klein workflow templates to current ComfyUI shape.
- Replaced placeholder example prompts across bundled workflow nodes with curated Japan/JDM/anime themed prompts to better showcase each model's strengths.

## [1.2.9] -- Publish :main Docker Alias

### Changed
- Updated `.github/workflows/docker-publish.yml` so default cu130 image publishes both `:latest` and `:main` tags on default-branch builds.
- Keeps existing CUDA-suffixed tags unchanged (`-cu126`, `-cu128`, `-cu130`) while making `:main` mirror `:latest` for users pinned to the branch-style tag.

## [1.2.8] -- NewBie Node Source Fix and Frontend Auto-Upgrade

### Fixed
- Corrected `newbie-image` custom node source to `NewBieAI-Lab/ComfyUI-Newbie-Nodes` instead of the previously referenced `E-Anlia/ComfyUI-NewBie` fork, preventing startup import failures from missing `__init__.py`.
- Added legacy cleanup during pack node sync to remove stale `/app/ComfyUI/custom_nodes/ComfyUI-NewBie` directories that were created from the old source and can break imports.
- Added startup frontend package reconciliation so containers automatically upgrade `comfyui-frontend-package` from ComfyUI `requirements.txt`, addressing frontend version mismatch warnings.

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

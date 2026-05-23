# AGENTS.md -- Project Guide for AI Coding Agents

Dockerized ComfyUI with selectable model packs (image, video, 3D, audio), startup
sync/update logic, and persistent host-mounted data paths.

## Scope and Priorities

- Keep changes surgical and pack-driven.
- Prefer stable startup behavior over aggressive refactors.
- Preserve compatibility with existing workflow filenames and node graphs.
- Use plain ASCII in logs and status output (`[OK]`, `[WARN]`, `[ERROR]`).

## Key Paths

- `scripts/entrypoint.sh`: startup orchestration, repo sync, model/workflow downloads,
  base install of `vram-utils` nodes/workflows on every start, optional `none` pack selection.
- `scripts/patch_video_types_rotation.py`: PyAV rotation fallback patch for ComfyUI
  `comfy_api/latest/_input_impl/video_types.py` (structural line matching, not sed literals).
- `scripts/lib/git_sync.sh`: staged clone-or-update helper used by entrypoint.
- `scripts/packs/<pack>/`: pack metadata, models/workflows lists, optional `nodes.txt`.
- `workflows/`: bundled JSON workflows copied into ComfyUI on startup.
- `docker-compose.yml`, `.env.example`, `README.md`, `LOCAL_SETUP.md`: runtime docs/config.

## Startup Behavior (Critical)

- Use clone-or-update semantics via staged git sync for mounted directories:
  - fetch into staging dir, rsync to target on success
  - on failure, leave existing target untouched
- Install node requirements with the shared `install_reqs` helper.
- Install requirements for managed nodes only by default: ComfyUI, Manager,
  vram-utils (including comfyui-openai-api), and selected pack nodes.
- Managed custom-node requirements are collated and installed in one pip pass.
- Manual/orphan `custom_nodes/*/requirements.txt` installs require
  `INSTALL_ORPHAN_NODE_REQS=true`; use ComfyUI Manager Try fix for manual nodes.
- Git sync uses staged clone-or-update (`scripts/lib/git_sync.sh`) for atomic apply.
- `patch_comfyui_video_types_py()` runs after ComfyUI sync and again immediately before
  ComfyUI start (`|| exit 1` on the final run). Implementation: `scripts/patch_video_types_rotation.py`.
- When `hidream-o1` nodes are synced, `ensure_hidream_transformers()` upgrades
  `transformers>=4.57.1` for Qwen3-VL support.
- Do not allow custom-node requirements to downgrade torch stack pins:
  - filter: `torch`, `torchvision`, `torchaudio`, `xformers`.

## Pack and Workflow Rules

- Pack files follow low/high VRAM split:
  - `models-low.txt`, `models-high.txt`
  - `workflows-low.txt`, `workflows-high.txt`
- Bundled workflows use `workflows-bundled.txt` entries as
  `source|destination|tier` where tier is `low`, `high`, or `both` (default `both`).
  Do not copy entire workflow directories without tier metadata.
- For `klein-distilled`, workflows are bundled in `workflows/`; avoid re-adding
  duplicate template downloads under `scripts/packs/klein-distilled/workflows-*.txt`.
- Keep workflow JSON names stable unless user explicitly requests rename.
- Keep `z-image-base`, `z-image-turbo`, and `z-image-anime` as distinct selectable packs;
  each has different strengths and should not be collapsed into a single selector.

## NVFP4 Policy

- `NVFP4_SUPPORTED=true` enables URL override logic.
- `NVFP4_MODE`:
  - `official-only` (default): official NVFP4 sources only.
  - `allow-community`: allows configured community NVFP4 overrides (experimental),
  including Wan I2V, **flux1-krea** (elihung), **ernie-image** SFT (Starnodes),
  and **firered-image-edit** (cocorang FP8-mixed to Starnodes NVFP4).
- Preserve original NVFP4 model filenames when swapping URLs.
- Ensure workflows are switched/updated to the NVFP4-specific model filenames.

## SDXL Lightning Policy

- Prefer full all-in-one checkpoints for ComfyUI:
  - low tier: `sdxl_lightning_4step.safetensors`
  - high tier: `sdxl_lightning_8step.safetensors`
- Do not default to LoRA-first Lightning pack behavior unless requested.

## Optional Python deps

- The Docker image installs `av`, `sageattention`, and attempts `flash-attn` for attention backends used by some custom nodes.

## Test and Release Checklist

- Validate config: `docker-compose config`.
- After meaningful startup/pack changes, run smoke startup checks when feasible.
- For releases:
  - bump `VERSION` semver
  - update `CHANGELOG.md`
  - commit -> push -> tag -> push tag
  - create GitHub Release entry for the new tag.

## Learned User Preferences

- Do not edit attached plan files when implementing plans; use existing todos and mark progress there.
- Release workflow: semver bump, CHANGELOG, commit, push, tag, GitHub release, then watch CI to completion.
- Prefer ComfyUI Manager **Try fix** for orphan/manual custom nodes after startup; keep `INSTALL_ORPHAN_NODE_REQS=false` by default.
- Do not re-add connectivity doctor probes or Civicomfy; both were intentionally removed.
- `hidream-o1` is nodes + bundled workflow only; user downloads FP8/BF16 weights via Manager or Hugging Face after startup.
- Keep `z-image-base`, `z-image-turbo`, and `z-image-anime` as distinct selectable packs; do not collapse them.

## Learned Workspace Facts

- `scripts/` (entrypoint, install_comfyui, lib) are baked into the Docker image, not bind-mounted; script changes require `docker compose build`.
- Startup auto-removes unmanaged legacy custom-node dirs: `ComfyUI-Trellis2-GGUF`, `inference-gpu`, `openai-api`, bad `ComfyUI-NewBie` clone.
- Image pre-bakes ComfyUI, Manager, and vram-utils (including comfyui-openai-api); not Civicomfy.
- `flash-attn` pre-bake is best-effort and often fails on torch 2.12 + cu130; xformers and sageattention are the reliable attention backends.
- Runtime image has no compilers; source-only pip deps after managed node updates need image rebuild or Manager **Try fix**.
- ComfyUI `video_types.py` PyAV rotation patch lives in `scripts/patch_video_types_rotation.py`;
  use structural line matching (not sed literal replace) so upstream indentation changes do not break it.

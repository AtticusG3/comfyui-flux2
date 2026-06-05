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
- `scripts/lib/workflow_subgraph_ports.py`: canonical UUID wrapper/subgraph interface sync and parity checks.
- `scripts/lib/workflow_validate_cli.py`: shared path expansion and validator subprocess helpers for workflow CLIs.
- `scripts/lib/workflow_prompts.py`: prompt extraction for semantics checks (registry in `scripts/update_workflow_prompts.py`).
- `scripts/validate_workflow_json.py`: workflow JSON gate orchestrator (schema, links; flags `--topology`, `--semantics`, `--pack-audit`).
- `scripts/validate_workflow_topology.py`: root/subgraph link and wrapper parity (`--check-wrapper`, `--fix-wrapper`).
- `scripts/validate_workflow_semantics.py`: pack sampler defaults and example prompts (via `--semantics`).
- `scripts/sync_subgraph_wrapper_ports.py`: deterministic wrapper port sync from embedded subgraph interface (`--write` to persist).
- `scripts/embed_workflow_subgraphs.py`: embed missing UUID subgraph definitions before release (`--check`, `--dry-run`).
- `scripts/patch_video_types_rotation.py`: PyAV rotation fallback patch for ComfyUI
  `comfy_api/latest/_input_impl/video_types.py` (structural line matching, not sed literals).
- `scripts/audit_workflow_assets.py`: maintainer audit for bundled workflows vs pack models/nodes
  (subgraph-aware; mirrors `sync_workflow_models.py` extraction rules).
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
  ComfyUI rsync excludes bind-mounted `/models/`, `/input/`, `/output/`, `/custom_nodes/`,
  and `/user/default/workflows/` (leading slash = ComfyUI root only; unanchored `models/`
  would also skip `comfy/ldm/models/`). Rsync `protect` filters keep bind mounts from being
  deleted. After apply, `_git_sync_ensure_comfy_ldm_models()` re-syncs `comfy/ldm/models`
  from staging. Use `--no-group --no-owner` for Docker Desktop volumes.
- `ensure_comfyui_core_tree()` in `scripts/entrypoint.sh` repairs `comfy/ldm/models` from
  git or staging when missing, then requires `comfy/ldm/models/autoencoder.py` (runs after
  ComfyUI sync and again before ComfyUI start). On failure prints `[ERROR]` and exits.
- `RESEED_PACK_WORKFLOWS=true` installs bundled/URL pack workflows when
  `./data/workflows` already has JSON; full managed cleanup only on first empty seed.
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
- For `klein-distilled`, install Klein workflows via `workflows-bundled.txt`
  (`klein-t2i.json`, `klein-edit.json`; FP8 defaults, entrypoint selects 4B/9B by VRAM tier
  and sed to NVFP4 when enabled). Sources under `workflows/flux2/`.
- Bundled workflow deploy names match repo filenames (short kebab-case, e.g.
  `sdxl-lightning-t2i.json`); `workflows-bundled.txt` uses `source|dest|tier` with
  identical source and destination basenames.
- Keep workflow JSON names stable unless user explicitly requests rename.
- Keep `z-image-base`, `z-image-turbo`, and `z-image-anime` as distinct selectable packs;
  each has different strengths and should not be collapsed into a single selector.

## NVFP4 Policy

- Default `NVFP4_SUPPORTED=false`: pack catalogs and bundled workflows use FP8/BF16 only (no NVFP4 downloads). Z-Anime low tier uses [SeeSee21 FP8](https://huggingface.co/SeeSee21/Z-Anime/tree/main/diffusion_models); high tier uses SeeSee21 BF16.
- `NVFP4_SUPPORTED=true` enables URL override logic (Klein, Z-Turbo, Qwen Edit FP8 to Bedovyy NVFP4, etc.). Z-Anime (`z-image-anime`) stays SeeSee21 FP8/BF16 only.
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
- After workflow or pack list changes:
  - `python scripts/audit_workflow_assets.py` (CI: `.github/workflows/workflow-assets-audit.yml` on `scripts/**` and `workflows/**`).
  - `python scripts/validate_workflow_json.py --topology --semantics workflows/` (same CI job after audit).
  - For UUID subgraph edits: `embed_workflow_subgraphs.py` before release; repair wrapper drift with `sync_subgraph_wrapper_ports.py --write` or `validate_workflow_topology.py --fix-wrapper`, not hand-edited slots.
- Maintainer detail: README [Workflow validation (maintainers)](README.md#workflow-validation-maintainers); skills under `.cursor/skills/validate-comfyui-workflow/` and `workflow-subgraph-engineering/`.
- After meaningful startup/pack changes, run smoke startup checks when feasible.
- For releases:
  - bump `VERSION` semver
  - update `CHANGELOG.md`
  - commit -> push -> tag -> push tag
  - create GitHub Release entry for the new tag.
  - CI publishes cu130-only images (`docker-publish.yml`); prune old GHCR/releases via
    `scripts/registry_cleanup.py` or `.github/workflows/registry-cleanup.yml`.

## Learned User Preferences

- Do not edit attached plan files when implementing plans; use existing todos and mark progress there.
- Release workflow: semver bump, CHANGELOG, commit, push, tag, GitHub release, then watch CI to completion.
- Prefer ComfyUI Manager **Try fix** for orphan/manual custom nodes after startup; keep `INSTALL_ORPHAN_NODE_REQS=false` by default.
- Do not re-add connectivity doctor probes or Civicomfy; both were intentionally removed.
- `hidream-o1` is nodes + bundled workflow only; user downloads FP8/BF16 weights via Manager or Hugging Face after startup.
- Keep `z-image-base`, `z-image-turbo`, and `z-image-anime` as distinct selectable packs; do not collapse them.
- Bundled workflows use core `SaveImage`, not `LayerUtility: SaveImagePlus` (LayerStyle not required for saves).
- After editing `workflows/**/*.json`, run validation per README maintainer section (`--topology` when UUID subgraphs are present); on Windows use `py -3.12` (default `python` may be too old).
- Prefer thermo-nuclear code quality reviews for substantial refactors before merge.
- `NVFP4_SUPPORTED=false` means no NVFP4 downloads or workflow filenames anywhere; default packs use FP8 on low VRAM and BF16 on high (e.g. Z-Anime SeeSee21). Enable NVFP4 only when hardware supports it and the flag is explicitly `true`.
- Pack LLM enhancement prompts (`scripts/packs/<pack>/llm_enhancement_system_prompt.txt`) must be model-specific; do not cross-mix (Z-Anime SeeSee21 only, Z-Image Base vs Turbo, Klein `flux2_klein` not Z-Turbo).
- When recovering canonical LLM prompts, read sibling `comfy-router` `config/prompt_engine_store.json` only; do not modify the `comfy-router` repo.

## Learned Workspace Facts

- `scripts/` (entrypoint, install_comfyui, lib) are baked into the Docker image, not bind-mounted; script changes require `docker compose build`.
- Image pre-bakes ComfyUI, Manager, and vram-utils (including comfyui-openai-api), not Civicomfy; startup auto-removes legacy unmanaged node dirs (`ComfyUI-Trellis2-GGUF`, `inference-gpu`, `openai-api`, bad `ComfyUI-NewBie`).
- `.gitignore` excludes `.cursor/hooks/state/` (local hook state) and `workflows/**/*.safetensors`; do not commit hook session files or workflow weight binaries.
- `flash-attn` pre-bake is best-effort on torch 2.12 + cu130; xformers and sageattention are reliable attention backends. Image includes gcc/build-essential for SageAttention/Triton (`CC=gcc`); other source-only pip deps may need image rebuild or Manager **Try fix**.
- Canonical pack LLM enhancement prompts live in `scripts/packs/<pack>/llm_enhancement_system_prompt.txt` (extract from bundled workflows or recover from `comfy-router` read-only).
- ComfyUI `video_types.py` PyAV rotation patch lives in `scripts/patch_video_types_rotation.py`;
  use structural line matching (not sed literal replace) so upstream indentation changes do not break it.
- Startup always runs the aria2 model download pass; entrypoint dedupes merged pack lists by
  `dir=` + `out=` via `scripts/dedupe_model_download_list.py` before aria2 to avoid duplicate-job
  races on shared files (e.g. `vae/ae.safetensors`). Existing models should skip/resume from
  persisted `./data/models`, while repeated full downloads usually mean incomplete files,
  NVFP4 filename changes, or a missing/wiped bind mount.
- Z-Image Turbo uses the shared Comfy-Org VAE `ae.safetensors`; do not require the old
  community filename `zImageTurboVAE_v10.safetensors`, which the pack does not download.
- ComfyUI 0.22+ needs `comfy-aimdo` aligned with ComfyUI `requirements.txt` (HostBuffer API);
  entrypoint `ensure_comfy_aimdo_package()` reconciles the pin on startup (rebuild image after script changes).
- Pack selector `flux2` is deprecated; Klein workflows ship via `klein-distilled` (`workflows/flux2/` sources).
- `ovis-image` is split-file only: bundled workflow and AnythingLLM API examples use `UNETLoader` +
  `ModelSamplingAuraFlow` + `CLIPLoader` (type `ovis`) + `VAELoader`, not `CheckpointLoaderSimple`; low tier
  FP8 from qpqpqpqpqpqp/Ovis_Image_7B_fp8 with entrypoint sed by VRAM tier.
- Unembedded UUID subgraph references fail `audit_workflow_assets.py`; embed before release (see checklist above).

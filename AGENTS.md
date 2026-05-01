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
- `scripts/packs/<pack>/`: pack metadata, models/workflows lists, optional `nodes.txt`.
- `workflows/`: bundled JSON workflows copied into ComfyUI on startup.
- `docker-compose.yml`, `.env.example`, `README.md`, `LOCAL_SETUP.md`: runtime docs/config.

## Startup Behavior (Critical)

- Use clone-or-update semantics for mounted directories:
  - existing git repo -> fetch/reset
  - existing non-git dir -> init/fetch/reset
  - missing dir -> clone
- Install node requirements with the shared `install_reqs` helper.
- Also scan all existing `custom_nodes/*/requirements.txt` and install them.
- Do not allow custom-node requirements to downgrade torch stack pins:
  - filter: `torch`, `torchvision`, `torchaudio`, `xformers`.

## Pack and Workflow Rules

- Pack files follow low/high VRAM split:
  - `models-low.txt`, `models-high.txt`
  - `workflows-low.txt`, `workflows-high.txt`
- For `klein-distilled`, workflows are bundled in `workflows/`; avoid re-adding
  duplicate template downloads under `scripts/packs/klein-distilled/workflows-*.txt`.
- Keep workflow JSON names stable unless user explicitly requests rename.

## NVFP4 Policy

- `NVFP4_SUPPORTED=true` enables URL override logic.
- `NVFP4_MODE`:
  - `official-only` (default): official NVFP4 sources only.
  - `allow-community`: allows configured community NVFP4 overrides (experimental),
  including Wan I2V and **firered-image-edit** (cocorang FP8-mixed to Starnodes NVFP4).
- Preserve original NVFP4 model filenames when swapping URLs.
- Ensure workflows are switched/updated to the NVFP4-specific model filenames.

## SDXL Lightning Policy

- Prefer full all-in-one checkpoints for ComfyUI:
  - low tier: `sdxl_lightning_4step.safetensors`
  - high tier: `sdxl_lightning_8step.safetensors`
- Do not default to LoRA-first Lightning pack behavior unless requested.

## Trellis2 Node Expectations

- `trellis2-gguf` must include required Trellis custom node repos in `nodes.txt`.
- If users report missing Trellis nodes, verify pack node repo list first.

## Test and Release Checklist

- Validate config: `docker-compose config`.
- After meaningful startup/pack changes, run smoke startup checks when feasible.
- For releases:
  - bump `VERSION` semver
  - update `CHANGELOG.md`
  - commit -> push -> tag -> push tag
  - create GitHub Release entry for the new tag.

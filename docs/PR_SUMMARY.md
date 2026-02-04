# PR Summary: Two-env-var model selection and pack layout

## What changed

- **Removed `HUNYUAN3D`** everywhere (docker-compose, README, scripts). Model selection is now only via `MODELS_DOWNLOAD` and `LOW_VRAM`.
- **Two controlling env vars**:
  - `MODELS_DOWNLOAD`: Comma-separated list of pack selectors. Default: `klein-distilled`.
  - `LOW_VRAM`: Boolean. `true` = 16GB VRAM target, `false` = 20GB target.
- **Dropped klein-base**: Only **klein-distilled** is supported (4B when `LOW_VRAM=true`, 9B when `LOW_VRAM=false`).
- **Pack layout**: Each selector maps to a pack under `scripts/packs/<selector>/` with `models*.txt` and `workflows*.txt` (aria2 input format). `klein-distilled` uses `models-4b`/`models-9b` and `workflows-4b`/`workflows-9b` depending on `LOW_VRAM`.
- **New selectors**: `klein-distilled`, `hunyuan-3d` (full model + workflow URLs). `flux1-krea`, `hunyuan-video`, `ace-step`, `ovis-image`, `newbie-image` are reserved (stub packs with no URLs; install per ComfyUI docs).
- **Workflows**: Staged into `ComfyUI/user/default/workflows/` with clear names (e.g. `klein-distilled-4b-text-to-image.json`, `hunyuan-3d-multiview-elf.webp`).
- **Idempotent downloads**: Model downloads use `--allow-overwrite=false` and `--continue=true`; workflow downloads use `--allow-overwrite=true` and `--conditional-get=true`. Failures exit with non-zero and log an error.
- **CLI_ARGS guidance**: README documents ComfyUI VRAM flags and gives copy-paste presets for 16GB (`--lowvram --reserve-vram 1.2`) and 20GB (`--highvram`). No non-existent flags are used.

## How to use it

1. Set **only** `MODELS_DOWNLOAD` and `LOW_VRAM` (plus optional `HF_TOKEN`, `CLI_ARGS`):
   - `MODELS_DOWNLOAD=klein-distilled` (default) or `klein-distilled,hunyuan-3d`, etc.
   - `LOW_VRAM=true` for 16GB GPUs, `LOW_VRAM=false` for 20GB.
2. For Klein distilled, set `HF_TOKEN` so the diffusion model can be downloaded.
3. Optionally set `CLI_ARGS` to a 16GB or 20GB preset from the README.
4. Start the container; selected packs’ models and workflows are downloaded/staged on first run.

## Known constraints

- **Default behaviour**: Unset `MODELS_DOWNLOAD` defaults to `klein-distilled`, so existing “Flux2 Klein distilled only” behaviour is preserved.
- **16GB validation**: `LOW_VRAM=true` + klein-distilled uses 4B fp8 models and low-vram workflows; OOM risk depends on ComfyUI version and other nodes. README recommends `--lowvram --reserve-vram 1.2` for 16GB; document any known limits (e.g. heavy custom nodes) in release notes.
- **Stub packs** (`flux1-krea`, `hunyuan-video`, `ace-step`, `ovis-image`, `newbie-image`): No model or workflow URLs are bundled; users must install per ComfyUI docs. Selectors are accepted and do not error; they simply contribute no download URLs.

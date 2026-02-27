# AGENTS.md -- Project Guide for AI Coding Agents

Docker-based ComfyUI with selectable model packs, using aria2c for downloads.
Key directories: `scripts/` (entrypoint, install, packs), `workflows/` (bundled JSON),
`data/` (host bind mounts, gitignored).

## Docker Conventions

- Base image: `python:3.12-slim-trixie`, multi-stage build (builder for C extensions,
  runtime for execution).
- CUDA version is a **build-time** `ARG CUDA_VERSION=cu130`, not runtime-detected.
  Override with `--build-arg CUDA_VERSION=cu124` etc.
- Do NOT add `VOLUME` instructions to the Dockerfile. Persistence is handled entirely
  by docker-compose volume mounts (`comfyui_data:/app/ComfyUI` + bind mounts).
- `.dockerignore` must exclude `data/`, `.git/`, `docs/`, `.env*`, `*.md`, `.github/`.
  Without this, multi-GB model files in `data/` get sent as build context.

## Shell Script Conventions

- All `.sh` files MUST use LF line endings, never CRLF. The `.gitattributes` enforces
  `*.sh text eol=lf` for tracked files, but untracked files on Windows will default
  to CRLF unless the editor is configured. A trailing `\r` breaks every bash command.
- `entrypoint.sh` uses `set -e`. `install_comfyui.sh` uses `set -euo pipefail`.
- Never `rm -rf` a Docker volume mount point. It cannot be removed (EBUSY), and nested
  bind mounts survive the deletion, leaving a non-empty directory. Subsequent
  `git clone` into it will fail.
- ASCII-only output. No emoji, no Unicode. Use `[OK]`, `[WARN]`, `[ERROR]` prefixes.

## Git Clone/Update Pattern (Critical)

`/app/ComfyUI` is a Docker named volume mount. On first run it exists as an empty
directory with bind-mount subdirectories (`models/`, `input/`, `output/`,
`user/default/workflows/`) inside it. `git clone` into a non-empty directory fails.

Use the **clone_or_update** pattern defined in `entrypoint.sh`:

```
clone_or_update(dir, url, branch):
  if dir/.git exists   -> git fetch + git reset --hard (update)
  if dir exists, no .git -> git init + remote add + fetch + reset (volume mount)
  if dir does not exist  -> git clone -b branch url dir (fresh clone)
```

Branch names:
- ComfyUI: `master` (default branch of Comfy-Org/ComfyUI)
- ComfyUI-Manager: `main`
- Civicomfy: `main`

## Pack System

Each pack lives in `scripts/packs/<name>/` with these files:

```
pack.json           -- metadata: name, selectors[], requires_hf_token, tutorial_urls[]
models-16gb.txt     -- model URLs for LOW_VRAM=true (aria2c input format)
models-20gb.txt     -- model URLs for LOW_VRAM=false
workflows-16gb.txt  -- workflow URLs for LOW_VRAM=true
workflows-20gb.txt  -- workflow URLs for LOW_VRAM=false
nodes.txt           -- (optional) custom node git URLs
```

Model/workflow files use aria2c input format:

```
https://example.com/model.safetensors
  dir=ComfyUI/models/diffusion_models
  out=model.safetensors
```

`dir=` paths are relative to `/app` (the CWD when aria2c runs). To add a new pack:
1. Create `scripts/packs/<name>/`
2. Add `pack.json` with `name`, `selectors` array, `requires_hf_token`, `tutorial_urls`
3. Add model and workflow text files for both 16gb and 20gb variants

## Bundled Custom Nodes

| Node | Repository | Branch |
|------|-----------|--------|
| ComfyUI-Manager | https://github.com/ltdrdata/ComfyUI-Manager.git | main |
| Civicomfy | https://github.com/MoonGoblinDev/Civicomfy.git | main |

These are installed into `/app/ComfyUI/custom_nodes/<name>/`. These sub-paths are
NOT Docker volume mount points, so regular `git clone` works for them on first install.
On updates, `clone_or_update` handles them the same as ComfyUI.

## Testing Changes

```bash
# Build the image
docker-compose build

# Build and start
docker-compose up -d --build

# First-run test (destroys volumes, simulates clean start)
docker-compose down -v && docker-compose up -d

# Restart test (tests the update/fetch path)
docker-compose restart

# Verify clone succeeded
docker-compose exec comfyui ls /app/ComfyUI/.git

# Verify models downloaded
docker-compose exec comfyui ls /app/ComfyUI/models/diffusion_models/

# Stream logs
docker-compose logs -f comfyui
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `MODELS_DOWNLOAD` | Comma-separated pack selectors. Default: `klein-distilled` |
| `LOW_VRAM` | `true` = 16GB target, `false` = 20GB target |
| `HF_TOKEN` | Hugging Face token for gated models |
| `CIVITAI_API_KEY` | Civitai API token for Civicomfy model downloads |
| `CLI_ARGS` | Extra args passed to `python3 main.py` (e.g. `--lowvram`) |
| `TZ` | Timezone. Default: `UTC` |

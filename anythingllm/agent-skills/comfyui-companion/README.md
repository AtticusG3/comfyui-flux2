# ComfyUI Companion (AnythingLLM Custom Agent Skill)

AnythingLLM custom agent skill for routing ComfyUI requests to the right model pack, asking clarifying questions, optimizing prompts, and returning image render instructions.

## What It Does

- Knows all packs in this repo and routes by user intent.
- Covers T2I and image editing where supported (`klein-distilled`, `flux1-krea`, `newbie-image`, `ovis-image`, `sdxl-lightning`, `sdxl-editing`).
- Handles non-image intents gracefully (video/3D/audio packs).
- Prefers inline image rendering instruction and includes download-link fallback.
- Uses cached installed pack list when provided (`cachedInstalledPacks`), otherwise probes ComfyUI API and requests user confirmation.
- Asks compact clarifying questions before execution when user input is incomplete.

## Folder Layout

```text
anythingllm/agent-skills/comfyui-companion/
  plugin.json
  handler.js
  README.md
```

`hubId` is `comfyui-companion`, and the folder name matches it as required.

## Install Into AnythingLLM

1. Copy folder `anythingllm/agent-skills/comfyui-companion` into your AnythingLLM storage path:

   ```text
   STORAGE_DIR/plugins/agent-skills/comfyui-companion
   ```

2. In AnythingLLM, open `Settings > Agent Skills`.
3. Confirm `ComfyUI Companion` appears and is enabled.
4. Optionally enable Intelligent Tool Selection.

## Parameters

- `userRequest` (string, required)
- `taskType` (string, optional: `t2i|edit|video|3d|audio`)
- `sourceImageUrl` (string, optional)
- `preferInlineImage` (boolean, optional)
- `cachedInstalledPacks` (string, optional JSON array for RAG/memory cache)
- `comfyuiBaseUrl` (string, optional; default `http://localhost:8188`)

## Behavior Notes

- Pack routing defaults:
  - Anime -> `newbie-image`
  - Photoreal/general -> `klein-distilled`
  - Highest realism/cinematic -> `flux1-krea`
  - Text rendering in image -> `ovis-image`
  - Editing/inpaint/outpaint/img2img -> `sdxl-editing` (or `sdxl-lightning` for speed)
- Result includes:
  - selected pack + reason
  - prompt optimization output
  - clarifying questions (if needed)
  - install-check status
  - render return instruction:
    - inline markdown image preferred
    - fallback download link format

## Security and Secrets

- Do not hardcode tokens in skill files.
- Keep any credentials in AnythingLLM environment/config.

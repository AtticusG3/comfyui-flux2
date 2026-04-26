# ComfyUI Companion Executor (AnythingLLM Custom Agent Skill)

Runnable AnythingLLM skill that selects a pack, optimizes prompts, submits workflow jobs to ComfyUI, polls completion, and returns render links.

## What This Adds vs Routing-Only Skill

- Executes `POST /prompt` with provided `workflowApiJson`.
- Polls `GET /history/{prompt_id}` until completion/timeout.
- Returns:
  - inline markdown image (when available and requested)
  - direct `Download image: <url>` links
  - prompt metadata (`promptId`, selected pack, optimized prompt)

## Required Input

- `userRequest` (string)
- `workflowApiJson` (string, valid ComfyUI API workflow JSON)

Optional:

- `taskType` (`t2i|edit|video|3d|audio`)
- `sourceImageUrl`
- `preferInlineImage`
- `cachedInstalledPacks` (JSON array string from RAG, for install confirmation)
- `comfyuiBaseUrl` (default `http://localhost:8188`)
- `pollTimeoutSeconds` (default `120`)
- `pollIntervalMs` (default `1500`)

## Placeholder Support in workflowApiJson

String values in your workflow can include:

- `__PROMPT__`
- `__NEGATIVE__`
- `__SOURCE_IMAGE_URL__`

These are replaced before submission.

## Ready-to-use example workflows

This folder includes API workflow examples you can pass directly as `workflowApiJson`:

- `examples/workflow-t2i-api.json`
- `examples/workflow-edit-api.json`
- `examples/workflow-flux2-klein-distilled-t2i-api.json`
- `examples/workflow-flux2-klein-distilled-edit-api.json`
- `examples/packs/workflow-pack-variant-index.json` (all-pack map)

Usage notes:

- Replace `ckpt_name` with a checkpoint available in your ComfyUI instance.
- Flux2-specific examples above are pre-wired to:
  - `flux-2-klein-4b-fp8.safetensors`
  - `qwen_3_4b.safetensors`
  - `flux2-vae.safetensors`
- For 9B, swap model names:
  - `flux-2-klein-9b-fp8.safetensors`
  - `qwen_3_8b_fp8mixed.safetensors`
  - `flux2-vae.safetensors`
- For custom workflows exported from ComfyUI, keep these placeholders:
  - `__PROMPT__`
  - `__NEGATIVE__`
  - `__SOURCE_IMAGE_URL__` (for edit workflow)

### Explicit variants for all packs

Per-pack explicit JSON variants are included under:

- `examples/packs/`

Runnables included for image packs:

- `workflow-flux1-krea-t2i-api.json`
- `workflow-flux1-krea-edit-api.json`
- `workflow-newbie-image-t2i-api.json`
- `workflow-ovis-image-t2i-api.json`
- `workflow-sdxl-lightning-t2i-api.json`
- `workflow-sdxl-lightning-edit-api.json`
- `workflow-sdxl-editing-t2i-api.json`
- `workflow-sdxl-editing-edit-api.json`

Starter templates included for non-image packs:

- `workflow-hunyuan-video-t2v-template.json`
- `workflow-wan-2-2-t2v-template.json`
- `workflow-hunyuan-3d-i23d-template.json`
- `workflow-trellis2-gguf-i23d-template.json`
- `workflow-ace-step-t2a-template.json`
- `workflow-vram-utils-template.json`

Use `workflow-pack-variant-index.json` to resolve pack -> variant file.

## Install

Copy this folder into AnythingLLM storage:

```text
STORAGE_DIR/plugins/agent-skills/comfyui-companion-executor
```

Then enable in `Settings > Agent Skills`.

## Notes

- Install check uses `cachedInstalledPacks` if provided.
- If pack is unconfirmed, result marks install state as `unknown`.
- If cache explicitly shows pack missing, it returns a corrective action message.

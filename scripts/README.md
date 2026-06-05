# Scripts layout

## Runtime (baked into Docker image)

| Script | Role |
| --- | --- |
| `entrypoint.sh` | Container startup: pack sync, model downloads, node requirements, ComfyUI launch. |
| `install_comfyui.sh` | Image build bootstrap for ComfyUI, Manager, optional vram-utils nodes. |
| `lib/git_sync.sh` | Staged clone-or-update helper used by entrypoint and install. |
| `patch_video_types_rotation.py` | PyAV rotation fallback patch for ComfyUI `video_types.py`. |
| `ensure_nunchaku_wheel.py` | Optional ComfyUI-nunchaku backend wheel install (torch/CUDA matched). |
| `dedupe_model_download_list.py` | Dedupe aria2 model list by `dir=` + `out=` before download. |

## Workflow validation and subgraph tooling

| Script | Role |
| --- | --- |
| `audit_workflow_assets.py` | Pack model/node coverage vs bundled workflows. |
| `validate_workflow_json.py` | Schema, links; flags `--topology`, `--semantics`, `--pack-audit`. |
| `validate_workflow_topology.py` | Wrapper/subgraph parity; `--fix-wrapper`. |
| `validate_workflow_semantics.py` | Pack sampler defaults and example prompts. |
| `embed_workflow_subgraphs.py` | Embed missing UUID subgraph bodies before release. |
| `sync_subgraph_wrapper_ports.py` | Sync wrapper ports from embedded subgraph interface. |
| `sync_workflow_models.py` | Extract workflow model refs for maintainer checks. |
| `merge_enhancement_templates.py` | Graft `_templates/` subgraphs onto pack workflows. |
| `update_workflow_prompts.py` | Refresh workflow example prompts registry. |

## Release and registry

| Script | Role |
| --- | --- |
| `registry_cleanup.py` | Prune old GHCR tags and GitHub releases. |
| `cleanup-registry.sh` / `cleanup-registry.ps1` | Thin wrappers around `registry_cleanup.py`. |
| `gitea-push.sh` / `gitea-push.ps1` | Push to Gitea with token from environment. |

## One-off migrations

See `scripts/maint/README.md`.

# Workflow enhancement templates

Nested subgraph definitions from golden workflows. Path: ``definitions.subgraphs`` in ComfyUI 0.4+ JSON.

| File | Role |
|------|------|
| LLM_Prompt_Enhancement.json | OAIAPI prompt enhancement |
| Detail_Daemon.json | Latent refinement |
| SeedVR2_Upscale.json | SeedVR2 pixel upscale |
| Upscaler.json | RealESRGAN / model upscale |
| HiRes_Fix_SDXL_reference.json | Inline RealVisXL V5 2-pass latent hires |

Use ``python scripts/merge_enhancement_templates.py --workflow <path>`` to graft templates onto plain pack workflows by name.

Use ``python scripts/embed_workflow_subgraphs.py`` to embed any referenced template subgraph ids (and known id aliases) into all workflows under ``workflows/``.

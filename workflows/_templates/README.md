# Workflow enhancement templates

Nested subgraph definitions from golden workflows. Path: ``definitions.subgraphs`` in ComfyUI 0.4+ JSON.

| File | Role |
|------|------|
| LLM_Prompt_Enhancement.json | OAIAPI prompt enhancement |
| Detail_Daemon.json | Latent refinement |
| SeedVR2_Upscale.json | SeedVR2 pixel upscale |
| Upscaler.json | RealESRGAN / model upscale |
| HiRes_Fix_SDXL_reference.json | Inline RealVisXL V5 2-pass latent hires |
| Ernie_T2I_Pipeline.json | ERNIE-Image Turbo T2I pipeline (Comfy-Org id) |
| Klein_4B_Text_to_Image.json | Flux.2 Klein 4B T2I subgraph |
| Klein_4B_Image_Edit.json | Flux.2 Klein 4B image edit subgraph |
| Flux_Krea_T2I.json | FLUX.1 Krea dev T2I subgraph |
| HiDream_Prompt_Enhancement.json | HiDream O1 prompt enhancement (alias for custom id) |

Use ``python scripts/merge_enhancement_templates.py --workflow <path>`` to graft templates onto plain pack workflows by name. One-off migration scripts live under ``scripts/maint/``.

Use ``python scripts/embed_workflow_subgraphs.py`` to embed any referenced template subgraph ids (and known id aliases) into all workflows under ``workflows/``.

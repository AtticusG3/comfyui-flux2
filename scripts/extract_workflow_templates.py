import json
from pathlib import Path
REPO = Path(r"c:\Cursor IDE\comfyui-flux2")
wf = json.loads((REPO / "workflows/z-image-turbo/z-turbo-t2i.json").read_text(encoding="utf-8"))
TPL = REPO / "workflows/_templates"
TPL.mkdir(parents=True, exist_ok=True)
subs = (wf.get("definitions") or {}).get("subgraphs") or wf.get("subgraphs") or []
alias = {
    "SeedVR2 Video Upscaler": "SeedVR2_Upscale.json",
    "Detail Daemon": "Detail_Daemon.json",
    "Upscaler": "Upscaler.json",
}
for sg in subs:
    name = sg.get("name", "unnamed")
    fname = alias.get(name) or ("".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip().replace(" ", "_") + ".json")
    (TPL / fname).write_text(json.dumps(sg, indent=2), encoding="utf-8")
    print("[OK]", fname)
# LLM lives in main graph - copy from sdxl-lightning or ernie-turbo
for src_name in ["ernie-turbo-t2i.json", "sdxl-lightning-t2i.json"]:
    p = REPO / "workflows/ernie-image" / src_name if "ERNIE" in src_name else REPO / "workflows/sdxl-lightning/sdxl-lightning-t2i.json"
    if not p.exists():
        continue
    w2 = json.loads(p.read_text(encoding="utf-8"))
    for sg in (w2.get("definitions") or {}).get("subgraphs") or []:
        if "OAIAPI" in json.dumps(sg) or "Prompt" in (sg.get("name") or ""):
            (TPL / "LLM_Prompt_Enhancement.json").write_text(json.dumps(sg, indent=2), encoding="utf-8")
            print("[OK] LLM from", p.name)
            break
readme = Path(TPL / "README.md")
readme.write_text("""# Workflow enhancement templates

Nested subgraph definitions from golden workflows. Path: ``definitions.subgraphs`` in ComfyUI 0.4+ JSON.

| File | Role |
|------|------|
| LLM_Prompt_Enhancement.json | OAIAPI prompt enhancement |
| Detail_Daemon.json | Latent refinement |
| SeedVR2_Upscale.json | SeedVR2 pixel upscale |
| Upscaler.json | RealESRGAN / model upscale |
| HiRes_Fix_SDXL_reference.json | Inline RealVisXL V5 2-pass latent hires |

Use ``python scripts/merge_enhancement_templates.py --workflow <path>`` to graft templates onto plain pack workflows.
""", encoding="utf-8")

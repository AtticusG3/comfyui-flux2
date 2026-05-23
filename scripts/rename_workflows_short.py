#!/usr/bin/env python3
"""Rename bundled workflows to short kebab-case names and sync manifests."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / "workflows"
PACKS = REPO / "scripts" / "packs"
ENTRYPOINT = REPO / "scripts" / "entrypoint.sh"

# old relative path under workflows/ -> new relative path (source = deploy name)
RENAMES: dict[str, str] = {
    # klein / flux2
    "flux2/Flux 2 Klein 4B T2I.json": "flux2/klein-4b-t2i.json",
    "flux2/Flux 2 Klein 4B I2I.json": "flux2/klein-4b-edit.json",
    "flux2/Flux 2 Klein T2I.json": "flux2/klein-9b-t2i.json",
    "flux2/Flux 2 Klein I2I.json": "flux2/klein-9b-edit.json",
    # sdxl
    "sdxl-lightning/SDXL_Lightning T2I.json": "sdxl-lightning/sdxl-lightning-t2i.json",
    "sdxl-lightning/SDXL Lightning - Photoreal Hires.json": "sdxl-lightning/sdxl-lightning-hires.json",
    "sdxl-editing/SDXL 1.0 - Img2img Edit.json": "sdxl-editing/sdxl-img2img.json",
    "sdxl-editing/SDXL 1.0 - Inpaint.json": "sdxl-editing/sdxl-inpaint.json",
    "sdxl-editing/SDXL 1.0 - Outpaint.json": "sdxl-editing/sdxl-outpaint.json",
    # z-image
    "z-anime/Z-Anime T2I.json": "z-anime/z-anime-t2i.json",
    "z-image-turbo/Z-Image turbo T2I.json": "z-image-turbo/z-turbo-t2i.json",
    "z-image-turbo/Z-Image base T2I.json": "z-image-turbo/z-base-t2i.json",
    # ernie
    "ernie-image/ERNIE-Image - T2I.json": "ernie-image/ernie-sft-t2i.json",
    "ernie-image/ERNIE-Image-Turbo T2I.json": "ernie-image/ernie-turbo-t2i.json",
    # edit / krea / realvis
    "qwen-image-edit-2511/Qwen Image Edit 2511.json": "qwen-image-edit-2511/qwen-edit-2511.json",
    "firered-image-edit/FireRed I2I.json": "firered-image-edit/firered-edit.json",
    "flux1-krea/flux1-krea-dev.json": "flux1-krea/flux-krea-t2i.json",
    "realvisxl/RealVisXL Lightning - Fast Photoreal.json": "realvisxl/realvisxl-lightning-t2i.json",
    "realvisxl/RealVisXL V5 - Photoreal Hires.json": "realvisxl/realvisxl-v5-hires.json",
    # wan
    "wan-2-2/text-to-video-wan22-5b.json": "wan-2-2/wan22-5b-t2v.json",
    "wan-2-2/image-to-video-wan22-5b.json": "wan-2-2/wan22-5b-i2v.json",
    "wan-2-2/text-to-video-wan22-14b.json": "wan-2-2/wan22-14b-t2v.json",
    "wan-2-2/image-to-video-wan22-14b.json": "wan-2-2/wan22-14b-i2v.json",
    "wan-2-2/video-wan2-2-14b-fun-inpaint.json": "wan-2-2/wan22-14b-inpaint.json",
    "wan-2-2/video-wan2-2-14b-fun-camera.json": "wan-2-2/wan22-14b-camera.json",
    # misc packs
    "hunyuan-3d/3d-hunyuan3d-v2-1.json": "hunyuan-3d/hunyuan3d-i2-3d.json",
    "hidream-o1/HiDream O1 - Example.json": "hidream-o1/hidream-o1-example.json",
    "ace-step/audio-ace-step-1-5-checkpoint.json": "ace-step/ace-step-t2m.json",
    "ovis-image/image-ovis-text-to-image.json": "ovis-image/ovis-t2i.json",
    "newbie-image/newbie-image-t2i-low.json": "newbie-image/newbie-t2i-low.json",
    "newbie-image/newbie-image-t2i-high.json": "newbie-image/newbie-t2i-high.json",
    "hunyuan-video/Hunyuan Video - Import Guide.json": "hunyuan-video/hunyuan-video-guide.json",
}

# old deployed filename -> new deployed filename (basename)
DEPLOY_RENAMES: dict[str, str] = {
    "FLUX.2 Klein 4B Distilled - Text to Image.json": "klein-4b-t2i.json",
    "FLUX.2 Klein 4B Distilled - Image Edit.json": "klein-4b-edit.json",
    "FLUX.2 Klein 9B Distilled - Text to Image.json": "klein-9b-t2i.json",
    "FLUX.2 Klein 9B Distilled - Image Edit.json": "klein-9b-edit.json",
    "SDXL Lightning - Text to Image.json": "sdxl-lightning-t2i.json",
    "SDXL Lightning - Photoreal Hires.json": "sdxl-lightning-hires.json",
    "SDXL 1.0 - Img2img Edit.json": "sdxl-img2img.json",
    "SDXL 1.0 - Inpaint.json": "sdxl-inpaint.json",
    "SDXL 1.0 - Outpaint.json": "sdxl-outpaint.json",
    "Z-Anime T2I.json": "z-anime-t2i.json",
    "Z Image Turbo - Text to Image.json": "z-turbo-t2i.json",
    "Z Image Base - Text to Image.json": "z-base-t2i.json",
    "Z-Image turbo T2I.json": "z-turbo-t2i.json",
    "ERNIE-Image - Text to Image.json": "ernie-sft-t2i.json",
    "ERNIE-Image-Turbo - Text to Image.json": "ernie-turbo-t2i.json",
    "Qwen Image Edit 2511.json": "qwen-edit-2511.json",
    "FireRed Image Edit 1.0 - Image Edit.json": "firered-edit.json",
    "FLUX.1 Krea Dev - Text to Image.json": "flux-krea-t2i.json",
    "RealVisXL Lightning - Fast Photoreal.json": "realvisxl-lightning-t2i.json",
    "RealVisXL V5 - Photoreal Hires.json": "realvisxl-v5-hires.json",
    "Wan 2.2 - 5B Text to Video.json": "wan22-5b-t2v.json",
    "Wan 2.2 - 5B Image to Video.json": "wan22-5b-i2v.json",
    "Wan 2.2 - 14B Text to Video.json": "wan22-14b-t2v.json",
    "Wan 2.2 - 14B Image to Video.json": "wan22-14b-i2v.json",
    "Wan 2.2 - 14B Fun Inpaint.json": "wan22-14b-inpaint.json",
    "Wan 2.2 - 14B Fun Camera Control.json": "wan22-14b-camera.json",
    "Hunyuan3D 2.1 - Image to 3D.json": "hunyuan3d-i2-3d.json",
    "HiDream O1 - Example.json": "hidream-o1-example.json",
    "ACE-Step 1.5 - Text to Music.json": "ace-step-t2m.json",
    "Ovis Image - Text to Image.json": "ovis-t2i.json",
    "Newbie Image - Text to Image (Low VRAM).json": "newbie-t2i-low.json",
    "Newbie Image - Text to Image (High VRAM).json": "newbie-t2i-high.json",
    "Hunyuan Video - Import Guide.json": "hunyuan-video-guide.json",
    # legacy entrypoint paths (may not exist as sources)
    "Z Anime - Distill 4 Step NVFP4.json": "z-anime-t2i.json",
    "Z Anime - Distill 4 Step BF16.json": "z-anime-t2i.json",
}

BUNDLED_TIERS: dict[str, str] = {
    "flux2/klein-4b-t2i.json": "low",
    "flux2/klein-4b-edit.json": "low",
    "flux2/klein-9b-t2i.json": "high",
    "flux2/klein-9b-edit.json": "high",
    "sdxl-lightning/sdxl-lightning-t2i.json": "both",
    "sdxl-lightning/sdxl-lightning-hires.json": "high",
    "sdxl-editing/sdxl-img2img.json": "both",
    "sdxl-editing/sdxl-inpaint.json": "both",
    "sdxl-editing/sdxl-outpaint.json": "both",
    "z-anime/z-anime-t2i.json": "both",
    "z-image-turbo/z-turbo-t2i.json": "both",
    "z-image-turbo/z-base-t2i.json": "both",
    "ernie-image/ernie-sft-t2i.json": "high",
    "ernie-image/ernie-turbo-t2i.json": "low",
    "qwen-image-edit-2511/qwen-edit-2511.json": "both",
    "firered-image-edit/firered-edit.json": "both",
    "flux1-krea/flux-krea-t2i.json": "both",
    "realvisxl/realvisxl-lightning-t2i.json": "low",
    "realvisxl/realvisxl-v5-hires.json": "high",
    "wan-2-2/wan22-5b-t2v.json": "low",
    "wan-2-2/wan22-5b-i2v.json": "low",
    "wan-2-2/wan22-14b-t2v.json": "high",
    "wan-2-2/wan22-14b-i2v.json": "high",
    "wan-2-2/wan22-14b-inpaint.json": "high",
    "wan-2-2/wan22-14b-camera.json": "high",
    "hunyuan-3d/hunyuan3d-i2-3d.json": "both",
    "hidream-o1/hidream-o1-example.json": "both",
    "ace-step/ace-step-t2m.json": "both",
    "ovis-image/ovis-t2i.json": "both",
    "newbie-image/newbie-t2i-low.json": "low",
    "newbie-image/newbie-t2i-high.json": "high",
    "hunyuan-video/hunyuan-video-guide.json": "both",
}

PACK_FOR_SRC: dict[str, str] = {
    "flux2/klein-4b-t2i.json": "klein-distilled",
    "flux2/klein-4b-edit.json": "klein-distilled",
    "flux2/klein-9b-t2i.json": "klein-distilled",
    "flux2/klein-9b-edit.json": "klein-distilled",
    "sdxl-lightning/sdxl-lightning-t2i.json": "sdxl-lightning",
    "sdxl-lightning/sdxl-lightning-hires.json": "sdxl-lightning",
    "sdxl-editing/sdxl-img2img.json": "sdxl-editing",
    "sdxl-editing/sdxl-inpaint.json": "sdxl-editing",
    "sdxl-editing/sdxl-outpaint.json": "sdxl-editing",
    "z-anime/z-anime-t2i.json": "z-image-anime",
    "z-image-turbo/z-turbo-t2i.json": "z-image-turbo",
    "z-image-turbo/z-base-t2i.json": "z-image-base",
    "ernie-image/ernie-sft-t2i.json": "ernie-image",
    "ernie-image/ernie-turbo-t2i.json": "ernie-image",
    "qwen-image-edit-2511/qwen-edit-2511.json": "qwen-image-edit-2511",
    "firered-image-edit/firered-edit.json": "firered-image-edit",
    "flux1-krea/flux-krea-t2i.json": "flux1-krea",
    "realvisxl/realvisxl-lightning-t2i.json": "realvisxl",
    "realvisxl/realvisxl-v5-hires.json": "realvisxl",
    "wan-2-2/wan22-5b-t2v.json": "wan-2-2",
    "wan-2-2/wan22-5b-i2v.json": "wan-2-2",
    "wan-2-2/wan22-14b-t2v.json": "wan-2-2",
    "wan-2-2/wan22-14b-i2v.json": "wan-2-2",
    "wan-2-2/wan22-14b-inpaint.json": "wan-2-2",
    "wan-2-2/wan22-14b-camera.json": "wan-2-2",
    "hunyuan-3d/hunyuan3d-i2-3d.json": "hunyuan-3d",
    "hidream-o1/hidream-o1-example.json": "hidream-o1",
    "ace-step/ace-step-t2m.json": "ace-step",
    "ovis-image/ovis-t2i.json": "ovis-image",
    "newbie-image/newbie-t2i-low.json": "newbie-image",
    "newbie-image/newbie-t2i-high.json": "newbie-image",
    "hunyuan-video/hunyuan-video-guide.json": "hunyuan-video",
}


def rename_files() -> None:
    for old_rel, new_rel in RENAMES.items():
        old_path = WORKFLOWS / old_rel.replace("/", "\\") if False else WORKFLOWS / Path(old_rel)
        new_path = WORKFLOWS / Path(new_rel)
        if not old_path.is_file():
            if new_path.is_file():
                continue
            print(f"[WARN] missing source: {old_rel}")
            continue
        new_path.parent.mkdir(parents=True, exist_ok=True)
        if new_path.exists() and new_path.resolve() != old_path.resolve():
            new_path.unlink()
        old_path.rename(new_path)
        print(f"[OK] {old_rel} -> {new_rel}")


def write_bundled_manifests() -> None:
    by_pack: dict[str, list[str]] = {}
    for src, tier in BUNDLED_TIERS.items():
        pack = PACK_FOR_SRC[src]
        dest = Path(src).name
        by_pack.setdefault(pack, []).append(f"{src}|{dest}|{tier}")

    for pack, lines in by_pack.items():
        path = PACKS / pack / "workflows-bundled.txt"
        if not path.parent.is_dir():
            continue
        header = "# source_path (under /workflows/)|destination_filename|tier\n"
        path.write_text(header + "\n".join(sorted(lines)) + "\n", encoding="utf-8")
        print(f"[OK] {path.relative_to(REPO)}")


def patch_entrypoint() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")
    for old, new in sorted(DEPLOY_RENAMES.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    ENTRYPOINT.write_text(text, encoding="utf-8")
    print("[OK] scripts/entrypoint.sh")


def patch_text_file(path: Path, replacements: dict[str, str]) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    orig = text
    for old, new in sorted(replacements.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def patch_repo_refs() -> None:
    all_replacements = {**DEPLOY_RENAMES}
    for old_rel, new_rel in RENAMES.items():
        all_replacements[old_rel] = new_rel
        all_replacements[Path(old_rel).name] = Path(new_rel).name
        all_replacements[f"workflows/{old_rel}"] = f"workflows/{new_rel}"

    targets = [
        REPO / "README.md",
        REPO / "scripts" / "fix_qwen_edit_workflow.py",
        REPO / "scripts" / "gen_klein_4b_workflows.py",
        REPO / "scripts" / "extract_workflow_templates.py",
        REPO / "scripts" / "replace_plain_with_donor.py",
        REPO / "scripts" / "_mk_sdxl_hires.py",
        REPO / "scripts" / "_av3d_notes.py",
        REPO / "scripts" / "packs" / "wan-2-2" / "workflows-high.txt",
        REPO / "scripts" / "packs" / "wan-2-2" / "workflows-low.txt",
    ]
    for path in targets:
        if patch_text_file(path, all_replacements):
            print(f"[OK] {path.relative_to(REPO)}")

    audit = REPO / "scripts" / "audit_workflow_assets.py"
    text = audit.read_text(encoding="utf-8")
    old_block = '''    if rel.startswith("Flux 2 Klein"):
        return "klein-distilled" if any(x in rel for x in ("4B", "9B")) else "flux2"'''
    new_block = '''    if rel.startswith("klein-") or "klein-" in rel:
        return "klein-distilled"'''
    if old_block in text:
        text = text.replace(old_block, new_block)
        audit.write_text(text, encoding="utf-8")
        print("[OK] scripts/audit_workflow_assets.py infer_pack_from_path")


def main() -> None:
    rename_files()
    write_bundled_manifests()
    patch_entrypoint()
    patch_repo_refs()
    print("[OK] rename complete")


if __name__ == "__main__":
    main()

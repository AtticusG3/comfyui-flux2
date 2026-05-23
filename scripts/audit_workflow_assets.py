#!/usr/bin/env python3
"""Audit workflows against pack model catalogs and managed custom-node repos."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from sync_workflow_models import (
    COMMUNITY_NVFP4_CATALOG_ALIASES,
    OFFICIAL_NVFP4_CATALOG_ALIASES,
    extract_workflow_refs,
    iter_nodes,
    node_class,
    parse_download_blocks,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKS_DIR = REPO_ROOT / "scripts" / "packs"
WORKFLOWS_DIR = REPO_ROOT / "workflows"

CORE_NODE_TYPES = {
    "CheckpointLoaderSimple",
    "UNETLoader",
    "VAELoader",
    "CLIPLoader",
    "DualCLIPLoader",
    "TripleCLIPLoader",
    "QuadrupleCLIPLoader",
    "CLIPVisionLoader",
    "CLIPTextEncode",
    "CLIPVisionEncode",
    "ConditioningCombine",
    "ConditioningConcat",
    "ConditioningSetArea",
    "ConditioningSetMask",
    "KSampler",
    "KSamplerAdvanced",
    "SamplerCustom",
    "EmptyLatentImage",
    "LatentUpscale",
    "LatentUpscaleBy",
    "VAEDecode",
    "VAEEncode",
    "VAEEncodeForInpaint",
    "SaveImage",
    "LoadImage",
    "LoadImageMask",
    "PreviewImage",
    "PreviewAny",
    "ImageScale",
    "ImageScaleBy",
    "ImageInvert",
    "ImageBatch",
    "ImageBlend",
    "ImageCompositeMasked",
    "MaskToImage",
    "ImageToMask",
    "GrowMask",
    "FeatherMask",
    "InvertMask",
    "CropMask",
    "SolidMask",
    "SetLatentNoiseMask",
    "ControlNetApply",
    "ControlNetApplyAdvanced",
    "ControlNetLoader",
    "LoraLoader",
    "LoraLoaderModelOnly",
    "ModelSamplingSD3",
    "ModelSamplingFlux",
    "ModelSamplingAuraFlow",
    "ModelSamplingContinuousEDM",
    "BasicScheduler",
    "BasicGuider",
    "SamplerCustomAdvanced",
    "RandomNoise",
    "DisableNoise",
    "CFGGuider",
    "FluxGuidance",
    "UNETTextEncode",
    "Note",
    "PrimitiveNode",
    "PrimitiveString",
    "PrimitiveStringMultiline",
    "PrimitiveInt",
    "PrimitiveFloat",
    "PrimitiveBoolean",
    "Reroute",
    "MarkdownNote",
    "UpscaleModelLoader",
    "ImageUpscaleWithModel",
    "StyleModelLoader",
    "StyleModelApply",
    "InpaintModelConditioning",
    "DifferentialDiffusion",
    "FreeU",
    "FreeU_V2",
    "PatchModelAddDownscale",
    "TorchCompileModel",
    "AudioEncoderLoader",
    "SaveAudio",
    "LoadAudio",
    "EmptyImage",
    "RepeatImageBatch",
    "ImagePadForOutpaint",
    "JoinImageWithAlpha",
    "SplitImageWithAlpha",
    "ConstrainImage",
    "GetImageSize",
    "ImageCrop",
    "ImageFlip",
    "ImageRotate",
    "CLIPSetLastLayer",
    "unCLIPConditioning",
    "GLIGENLoader",
    "GLIGENTextBoxApply",
    "HyperTile",
    "PerturbedAttentionGuidance",
    "SelfAttentionGuidance",
    "PhotoMakerLoader",
    "PhotoMakerEncode",
    "PhotoMakerStyles",
    "CLIPTextEncodeSDXL",
    "CLIPTextEncodeSDXLRefiner",
    "CheckpointSave",
    "VAESave",
    "CLIPSave",
    "ModelMergeSimple",
    "ModelMergeBlocks",
    "ModelMergeSubtract",
    "ModelMergeAdd",
    "ConditioningZeroOut",
    "ConditioningSetTimestepRange",
    "SetUnionControlNetType",
    "ControlNetInpaintingAliMamaApply",
    "InstructPixToPixConditioning",
    "StableZero123_Conditioning",
    "StableZero123_Conditioning_Batched",
    "SV3D_Conditioning",
    "SVD_img2vid_Conditioning",
    "VideoLinearCFGGuidance",
    "VideoTriangleCFGGuidance",
    "WanImageToVideo",
    "WanFunControlToVideo",
    "WanFunInpaintToVideo",
    "Wan22ImageToVideoLatent",
    "WanFirstLastFrameToVideo",
    "WanVaceToVideo",
    "WanCameraImageToVideo",
    "WanCameraEmbedding",
    "WanTextToImage",
    "WanTextToVideo",
    "WanImageToVideo",
    "CreateVideo",
    "SaveWEBM",
    "SaveVideo",
    "LoadVideo",
    "GetVideoComponents",
    "TextEncodeAceStepAudio",
    "EmptyAceStepLatentAudio",
    "AceStepSampler",
    "Hunyuan3Dv2Conditioning",
    "Hunyuan3Dv2ConditioningMultiView",
    "Hunyuan3DVAEDecode",
    "Hunyuan3DVAEDecodeTiled",
    "Hunyuan3DModelLoader",
    "Hy3DMeshGenerator",
    "Hy3DPostprocessMesh",
    "Hy3DExportMesh",
    "Hy3DRenderMultiView",
    "Hy3DUploadMesh",
    "Hy3DLoadMesh",
    "Hy3DApplyTexture",
    "Hy3DBakeTexture",
    "Hy3DGenerateUV",
    "Hy3DRenderSingleView",
    "Hy3DRenderDepth",
    "Hy3DRenderNormal",
    "EmptyFlux2LatentImage",
    "EmptySD3LatentImage",
    "Flux2Scheduler",
    "KSamplerSelect",
    "ReferenceLatent",
    "RegexReplace",
    "JsonExtractString",
    "TextGenerate",
    "LatentBlend",
    "LatentComposite",
    "LatentCompositeMasked",
    "LatentCrop",
    "LatentFlip",
    "LatentRotate",
    "RepeatLatentBatch",
    "LatentFromBatch",
    "RebatchLatents",
    "RebatchImages",
    "EmptyHunyuanLatentVideo",
    "ImageOnlyCheckpointLoader",
    "VoxelToMesh",
    "SaveGLB",
    "SaveAudioMP3",
    "VAEDecodeAudio",
    "CFGNorm",
    "FluxKontextImageScale",
    "TextEncodeQwenImageEditPlus",
}

# Packs with no models-*.txt entries inherit downloads from these packs.
PACK_MODEL_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "flux2": ("klein-distilled",),
}

VRAM_UTILS_NODE_HINTS = (
    "GetNode",
    "SetNode",
    "Mute",
    "Fast",
    "Any Switch",
    "ImageResize",
    "ImageScaleToTotalPixels",
    "ImageRemoveBackground",
    "DetailDaemon",
    "Layer",
    "LayerUtility",
    "LayerMask",
    "LayerColor",
    "LayerStyle",
    "SeedVR",
    "easy ",
    "Easy",
    "Rgthree",
    "rgthree",
    "Context",
    "Bookmark",
    "Power",
    "Display",
    "ComfySwitch",
    "StringConcat",
    "StringReplace",
    "WAS",
    "Was ",
    "OpenAI",
    "OAIAPI_",
    "VRAM",
    "Unload",
    "Tile",
    "Tiled",
)

PACK_NODE_PATTERNS: dict[str, tuple[str, ...]] = {
    "hidream-o1": ("HiDreamO1",),
    "wan-2-2": ("VHS_", "VideoHelperSuite", "Wan22", "SaveAnimatedWEBP"),
    "trellis2-gguf": ("Trellis", "trellis", "LoadTrellis", "GGUF"),
    "hunyuan-3d": ("Hy3D", "Hunyuan3D"),
    "ace-step": ("AceStep", "EmptyAceStep", "TextEncodeAceStep"),
    "newbie-image": ("Newbie", "newbie"),
    "firered-image-edit": ("FireRed",),
    "ovis-image": ("Ovis",),
    "z-image-base": ("ZImage", "z_image"),
    "z-image-turbo": ("ZImage", "z_image"),
    "z-image-anime": ("ZImage", "z_image", "Anime"),
    "qwen-image-edit-2511": ("Qwen", "qwen"),
    "hunyuan-video": ("HunyuanVideo",),
}

UUID_NODE_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows-dir", type=Path, default=WORKFLOWS_DIR)
    parser.add_argument("--packs-dir", type=Path, default=PACKS_DIR)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_pack_models(pack_dir: Path) -> dict[str, set[str]]:
    by_tier: dict[str, set[str]] = {"low": set(), "high": set(), "both": set()}
    for tier in ("low", "high"):
        models_file = pack_dir / f"models-{tier}.txt"
        if not models_file.is_file():
            continue
        _, planned = parse_download_blocks(models_file)
        by_tier[tier].update(planned)
        by_tier["both"].update(planned)
    return by_tier


def load_bundled_mappings(packs_dir: Path) -> dict[str, list[tuple[str, str]]]:
    mapping: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for pack_dir in sorted(packs_dir.iterdir()):
        if not pack_dir.is_dir():
            continue
        wbl = pack_dir / "workflows-bundled.txt"
        if not wbl.is_file():
            continue
        for line in wbl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if not parts or not parts[0]:
                continue
            src = parts[0].replace("\\", "/")
            tier = (parts[2] if len(parts) > 2 else "both").lower()
            mapping[src].append((pack_dir.name, tier))
    return mapping


def infer_pack_from_path(rel: str) -> str | None:
    rel = rel.replace("\\", "/")
    if rel.startswith("Flux 2 Klein"):
        return "klein-distilled" if any(x in rel for x in ("4B", "9B")) else "flux2"
    if "/" in rel:
        first = rel.split("/", 1)[0]
        if first == "z-anime":
            return "z-image-anime"
        return first
    return None


def expand_nvfp4_catalog_aliases(names: set[str]) -> set[str]:
    """Treat NVFP4 workflow filenames and pack catalog names as equivalent."""
    expanded = set(names)
    for nvfp4_name, source_name in {
        **OFFICIAL_NVFP4_CATALOG_ALIASES,
        **COMMUNITY_NVFP4_CATALOG_ALIASES,
    }.items():
        if source_name in names:
            expanded.add(nvfp4_name)
        if nvfp4_name in names:
            expanded.add(source_name)
    return expanded


def models_for_workflow(
    pack_models: dict[str, dict[str, set[str]]],
    pack_assignments: list[tuple[str, str]],
) -> set[str] | None:
    """Return allowed model basenames, or None when packs declare no downloads."""
    allowed: set[str] = set()
    for pack_name, tier in pack_assignments:
        pack_names = [pack_name, *PACK_MODEL_DEPENDENCIES.get(pack_name, ())]
        for name in pack_names:
            pm = pack_models.get(name, {})
            if tier in ("low", "high"):
                allowed.update(pm.get(tier, set()))
            else:
                allowed.update(pm.get("both", set()))
    if not allowed:
        return None
    return expand_nvfp4_catalog_aliases(allowed)


def extract_node_types(workflow_path: Path) -> set[str]:
    with workflow_path.open("r", encoding="utf-8") as handle:
        workflow = json.load(handle)
    return {node_class(node) for node in iter_nodes(workflow) if node_class(node)}


def is_core_or_vram_utils(node_type: str) -> bool:
    if node_type in CORE_NODE_TYPES or UUID_NODE_RE.match(node_type):
        return True
    return any(hint in node_type for hint in VRAM_UTILS_NODE_HINTS)


def node_allowed_for_pack(node_type: str, pack_name: str) -> bool:
    if is_core_or_vram_utils(node_type):
        return True
    return any(pat in node_type for pat in PACK_NODE_PATTERNS.get(pack_name, ()))


def find_bundled_source(workflows_dir: Path, pack_dir: Path, src: str) -> Path | None:
    src = src.replace("\\", "/")
    candidates = [
        workflows_dir / src,
        pack_dir / src,
        pack_dir / "workflows-bundled" / Path(src).name,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def audit_bundled_manifests(
    workflows_dir: Path, packs_dir: Path
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for pack_dir in sorted(packs_dir.iterdir()):
        if not pack_dir.is_dir():
            continue
        wbl = pack_dir / "workflows-bundled.txt"
        if not wbl.is_file():
            continue
        for line in wbl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            src = line.split("|", 1)[0].strip()
            if not src:
                continue
            if find_bundled_source(workflows_dir, pack_dir, src) is None:
                issues.append({"pack": pack_dir.name, "source": src})
    return issues


def main() -> int:
    args = parse_args()
    workflows_dir = args.workflows_dir.resolve()
    packs_dir = args.packs_dir.resolve()

    bundled = load_bundled_mappings(packs_dir)
    pack_models = {
        d.name: load_pack_models(d)
        for d in sorted(packs_dir.iterdir())
        if d.is_dir() and (d / "pack.json").is_file()
    }

    model_issues: list[dict] = []
    node_issues: list[dict] = []
    unmapped: list[str] = []

    workflow_files = sorted(workflows_dir.rglob("*.json"))
    for wf_path in workflow_files:
        rel = wf_path.relative_to(workflows_dir).as_posix()
        assignments = bundled.get(rel, [])
        if not assignments:
            inferred = infer_pack_from_path(rel)
            if inferred:
                assignments = [(inferred, "both")]
            else:
                unmapped.append(rel)

        allowed_models = models_for_workflow(pack_models, assignments)
        for _subdir, filename in extract_workflow_refs(wf_path):
            name = Path(filename).name
            if assignments and allowed_models is not None and name not in allowed_models:
                model_issues.append(
                    {
                        "workflow": rel,
                        "packs": [p for p, _ in assignments],
                        "model": name,
                    }
                )

        pack_names = [p for p, _ in assignments]
        for nt in extract_node_types(wf_path):
            if is_core_or_vram_utils(nt):
                continue
            if not pack_names:
                node_issues.append({"workflow": rel, "node_type": nt, "reason": "unmapped"})
                continue
            if not any(node_allowed_for_pack(nt, p) for p in pack_names):
                node_issues.append(
                    {
                        "workflow": rel,
                        "packs": pack_names,
                        "node_type": nt,
                        "reason": "unknown_custom",
                    }
                )

    manifest_issues = audit_bundled_manifests(workflows_dir, packs_dir)

    if args.json:
        print(
            json.dumps(
                {
                    "model_issues": model_issues,
                    "node_issues": node_issues,
                    "unmapped": unmapped,
                    "manifest_issues": manifest_issues,
                },
                indent=2,
            )
        )
    else:
        print(f"[INFO] Scanned {len(workflow_files)} workflow(s)")
        for u in unmapped:
            print(f"[WARN] Unmapped: {u}")
        if model_issues:
            print(f"[ERROR] Model mismatches ({len(model_issues)}):")
            for item in model_issues:
                print(f"  - {item['workflow']}: {item['model']} (packs={item['packs']})")
        else:
            print("[OK] Model references match pack catalogs.")
        if node_issues:
            print(f"[WARN] Node review ({len(node_issues)}):")
            for item in node_issues:
                print(f"  - {item['workflow']}: {item['node_type']}")
        else:
            print("[OK] Custom node types resolved.")
        if manifest_issues:
            print(f"[ERROR] Broken workflows-bundled entries ({len(manifest_issues)}):")
            for item in manifest_issues:
                print(f"  - {item['pack']}: {item['source']}")
        else:
            print("[OK] All workflows-bundled sources exist.")

    return 1 if model_issues or manifest_issues else 0


if __name__ == "__main__":
    sys.exit(main())

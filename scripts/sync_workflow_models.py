#!/usr/bin/env python3
"""Align installed workflows with available models.

- Drop workflows whose primary model tier does not match the active VRAM tier
  when the referenced diffusion/checkpoint file is absent from disk and catalogs.
- Append missing model download blocks from pack model lists so workflows can run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MODEL_EXTENSIONS = (
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".gguf",
    ".bin",
    ".onnx",
)

# ComfyUI loader node -> models subdirectory and widget/input field names.
LOADER_SPECS: dict[str, tuple[str, tuple[str, ...]]] = {
    "CheckpointLoaderSimple": ("checkpoints", ("ckpt_name",)),
    "UNETLoader": ("diffusion_models", ("unet_name",)),
    "VAELoader": ("vae", ("vae_name",)),
    "CLIPLoader": ("text_encoders", ("clip_name",)),
    "DualCLIPLoader": ("text_encoders", ("clip_name1", "clip_name2")),
    "TripleCLIPLoader": ("text_encoders", ("clip_name1", "clip_name2", "clip_name3")),
    "QuadrupleCLIPLoader": (
        "text_encoders",
        ("clip_name1", "clip_name2", "clip_name3", "clip_name4"),
    ),
    "LoraLoader": ("loras", ("lora_name",)),
    "LoraLoaderModelOnly": ("loras", ("lora_name",)),
    "UpscaleModelLoader": ("upscale_models", ("model_name",)),
    "ControlNetLoader": ("controlnet", ("control_net_name",)),
    "UnetLoaderGGUF": ("unet", ("unet_name",)),
    "CLIPVisionLoader": ("clip_vision", ("clip_name",)),
    "StyleModelLoader": ("style_models", ("style_model_name",)),
    "AudioEncoderLoader": ("audio_encoders", ("audio_encoder_name",)),
}

TIER_HINTS = {
    "low": (
        "klein-4b",
        "flux-2-klein-4b",
        "ti2v_5b",
        "wan2.2_ti2v_5b",
        "ernie-image-turbo",
        "lightning_4",
        "4steps",
    ),
    "high": (
        "klein-9b",
        "flux-2-klein-9b",
        "wan2.2_t2v_14",
        "wan2.2_i2v_14",
        "fun_inpaint_high_noise_14b",
        "fun_camera_high_noise_14b",
        "ernie-image.safetensors",
        "lightning_8",
        "8steps",
    ),
}


# Official NVFP4 (NVFP4_SUPPORTED=true).
OFFICIAL_NVFP4_CATALOG_ALIASES: dict[str, str] = {
    "flux-2-klein-4b-nvfp4.safetensors": "flux-2-klein-4b-fp8.safetensors",
    "flux-2-klein-9b-nvfp4.safetensors": "flux-2-klein-9b-fp8.safetensors",
    "ernie-image-turbo-nvfp4.safetensors": "ernie-image-turbo-fp8.safetensors",
    "z_image_turbo_nvfp4.safetensors": "z_image_turbo_bf16.safetensors",
}

# Community NVFP4 (also requires NVFP4_MODE=allow-community).
COMMUNITY_NVFP4_CATALOG_ALIASES: dict[str, str] = {
    "wan2.2_i2v_high_noise_14B_nvfp4_mixed.safetensors": (
        "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
    ),
    "wan2.2_i2v_low_noise_14B_nvfp4_mixed.safetensors": (
        "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
    ),
    "FireRed-Image-Edit-1_NVFP4.safetensors": "FireRed-Image-Edit-1.0_fp8mixed_comfy.safetensors",
    "flux1-krea-dev-nvfp4.safetensors": "flux1-krea-dev_fp8_scaled.safetensors",
    "ernie-image-nvfp4.safetensors": "ernie-image.safetensors",
    "z-image-base-nvfp4_quality.safetensors": "z_image_bf16.safetensors",
}

OFFICIAL_NVFP4_BLOCK_REWRITES: list[tuple[str, str]] = [
    (
        r"https://[^[:space:]]*/flux-2-klein-4b-fp8\.safetensors",
        "https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-nvfp4/resolve/main/flux-2-klein-4b-nvfp4.safetensors",
    ),
    (
        r"https://[^[:space:]]*/flux-2-klein-9b-fp8\.safetensors",
        "https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-nvfp4/resolve/main/flux-2-klein-9b-nvfp4.safetensors",
    ),
    (
        r"https://huggingface.co/Abiray/ERNIE-Image-Turbo-FP8-NVFP4/resolve/main/ernie-image-turbo-fp8\.safetensors",
        "https://huggingface.co/Abiray/ERNIE-Image-Turbo-FP8-NVFP4/resolve/main/ernie-image-turbo-nvfp4.safetensors",
    ),
    (
        r"https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16\.safetensors",
        "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_nvfp4.safetensors",
    ),
]

COMMUNITY_NVFP4_BLOCK_REWRITES: list[tuple[str, str]] = [
    (
        r"https://huggingface.co/Comfy-Org/Wan_2\.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2\.2_i2v_high_noise_14B_fp8_scaled\.safetensors",
        "https://huggingface.co/GitMylo/Wan_2.2_nvfp4/resolve/main/wan2.2_i2v_high_noise_14B_nvfp4_mixed.safetensors",
    ),
    (
        r"https://huggingface.co/Comfy-Org/Wan_2\.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2\.2_i2v_low_noise_14B_fp8_scaled\.safetensors",
        "https://huggingface.co/GitMylo/Wan_2.2_nvfp4/resolve/main/wan2.2_i2v_low_noise_14B_nvfp4_mixed.safetensors",
    ),
    (
        r"https://huggingface.co/cocorang/FireRed-Image-Edit-1\.0-FP8_And_BF16/resolve/main/FireRed-Image-Edit-1\.0_fp8mixed_comfy\.safetensors",
        "https://huggingface.co/Starnodes/quants/resolve/main/FireRed-Image-Edit-1_NVFP4.safetensors",
    ),
    (
        r"https://huggingface.co/Comfy-Org/FLUX\.1-Krea-dev_ComfyUI/resolve/main/split_files/diffusion_models/flux1-krea-dev_fp8_scaled\.safetensors",
        "https://huggingface.co/elihung/FLUX.1-Krea-dev-NVFP4/resolve/main/flux1-krea-dev-nvfp4.safetensors",
    ),
    (
        r"https://huggingface.co/Comfy-Org/ERNIE-Image/resolve/main/diffusion_models/ernie-image\.safetensors",
        "https://huggingface.co/Starnodes/quants/resolve/main/ernie-image-nvfp4.safetensors",
    ),
    (
        r"https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/diffusion_models/z_image_bf16\.safetensors",
        "https://huggingface.co/marcorez8/Z-image-aka-Base-nvfp4/resolve/main/z-image-base-nvfp4_quality.safetensors",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Managed workflow manifest path")
    parser.add_argument("--models-root", required=True, help="ComfyUI models directory")
    parser.add_argument("--packs-dir", required=True, help="scripts/packs directory")
    parser.add_argument("--download-list", required=True, help="Model download list to augment")
    parser.add_argument("--vram-tier", choices=("low", "high"), required=True)
    parser.add_argument(
        "--nvfp4-supported",
        choices=("true", "false"),
        default="false",
        help="When true, resolve NVFP4 workflow filenames against FP8 pack catalog entries",
    )
    parser.add_argument(
        "--nvfp4-mode",
        choices=("official-only", "allow-community"),
        default="official-only",
        help="Community NVFP4 alias resolution policy",
    )
    return parser.parse_args()


def looks_like_model_name(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    value = value.strip()
    if not value or value.startswith("http"):
        return False
    if any(ch in value for ch in ("\n", "{", "}", "[", "]")):
        return False
    lower = value.lower()
    if lower in {"default", "none", "randomize", "fixed", "auto", "increment", "decrement"}:
        return False
    return lower.endswith(MODEL_EXTENSIONS) or "/" in value


def iter_nodes(workflow: dict):
    """Yield nodes from UI export graphs, including nested subgraph definitions."""
    nodes = workflow.get("nodes")
    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict):
                yield node

        definitions = workflow.get("definitions")
        if isinstance(definitions, dict):
            for subgraph in definitions.get("subgraphs", []):
                if not isinstance(subgraph, dict):
                    continue
                for node in subgraph.get("nodes", []):
                    if isinstance(node, dict):
                        yield node
        return

    for value in workflow.values():
        if isinstance(value, dict) and ("class_type" in value or "type" in value):
            yield value


def node_class(node: dict) -> str:
    return str(node.get("class_type") or node.get("type") or "")


def extract_from_properties(node: dict, subdir: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    models = node.get("properties", {}).get("models")
    if isinstance(models, list):
        for item in models:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            directory = item.get("directory") or subdir
            if looks_like_model_name(name):
                refs.append((str(directory), str(name)))
    return refs


def extract_loader_refs(node: dict) -> list[tuple[str, str]]:
    cls = node_class(node)
    spec = LOADER_SPECS.get(cls)
    if not spec:
        return extract_from_properties(node, "diffusion_models")

    subdir, field_names = spec
    refs: list[tuple[str, str]] = []

    inputs = node.get("inputs")
    if isinstance(inputs, dict):
        for field in field_names:
            value = inputs.get(field)
            if looks_like_model_name(value):
                refs.append((subdir, str(value).strip()))

    widgets = node.get("widgets_values")
    if isinstance(widgets, list) and widgets:
        for idx, field in enumerate(field_names):
            if idx >= len(widgets):
                break
            value = widgets[idx]
            if looks_like_model_name(value):
                refs.append((subdir, str(value).strip()))

    if not refs:
        refs.extend(extract_from_properties(node, subdir))
    return refs


def extract_workflow_refs(workflow_path: Path) -> list[tuple[str, str]]:
    with workflow_path.open("r", encoding="utf-8") as handle:
        workflow = json.load(handle)

    refs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for node in iter_nodes(workflow):
        for ref in extract_loader_refs(node):
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
    return refs


def normalize_models_subdir(subdir: str) -> str:
    subdir = subdir.strip().strip("/")
    if subdir.startswith("ComfyUI/models/"):
        subdir = subdir[len("ComfyUI/models/") :]
    return subdir or "checkpoints"


def model_path(models_root: Path, subdir: str, filename: str) -> Path:
    subdir = normalize_models_subdir(subdir)
    name = Path(filename).name
    direct = models_root / subdir / name
    if direct.is_file():
        return direct
    nested = models_root / subdir / filename
    if nested.is_file():
        return nested
    return direct


def parse_download_blocks(list_path: Path) -> tuple[dict[str, str], set[str]]:
    """Map output filename -> full aria2 block text."""
    blocks: dict[str, str] = {}
    planned: set[str] = set()
    if not list_path.is_file():
        return blocks, planned

    current: list[str] = []
    for raw_line in list_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("https://") or line.startswith("http://"):
            if current:
                block = "\n".join(current).strip()
                out_match = re.search(r"^\s*out=(.+)$", block, re.MULTILINE)
                if out_match:
                    out_name = out_match.group(1).strip()
                    blocks[out_name] = block + "\n"
                    planned.add(out_name)
            current = [line]
            continue
        if current and (line.startswith("  ") or line.startswith("\t") or line == ""):
            current.append(line)
            continue
        if current:
            block = "\n".join(current).strip()
            out_match = re.search(r"^\s*out=(.+)$", block, re.MULTILINE)
            if out_match:
                out_name = out_match.group(1).strip()
                blocks[out_name] = block + "\n"
                planned.add(out_name)
            current = []

    if current:
        block = "\n".join(current).strip()
        out_match = re.search(r"^\s*out=(.+)$", block, re.MULTILINE)
        if out_match:
            out_name = out_match.group(1).strip()
            blocks[out_name] = block + "\n"
            planned.add(out_name)

    return blocks, planned


def parse_pack_catalog(packs_dir: Path) -> dict[str, str]:
    catalog: dict[str, str] = {}
    for models_file in sorted(packs_dir.glob("*/models-*.txt")):
        file_blocks, _ = parse_download_blocks(models_file)
        for out_name, block in file_blocks.items():
            catalog.setdefault(out_name, block)
    return catalog


def tier_mismatch(filename: str, vram_tier: str) -> bool:
    lower = filename.lower()
    is_low = any(token in lower for token in TIER_HINTS["low"])
    is_high = any(token in lower for token in TIER_HINTS["high"])
    if is_low and is_high:
        return False
    if vram_tier == "low" and is_high:
        return True
    if vram_tier == "high" and is_low:
        return True
    return False


def rewrite_block_for_nvfp4(block: str, out_name: str, rewrites: list[tuple[str, str]]) -> str:
    updated = block
    for pattern, replacement in rewrites:
        updated = re.sub(pattern, replacement, updated)
    updated = re.sub(r"^(\s*out=).+$", rf"\1{out_name}", updated, count=1, flags=re.MULTILINE)
    return updated


def lookup_catalog_block(
    name: str,
    catalog: dict[str, str],
    nvfp4_supported: bool,
    nvfp4_mode: str,
) -> str | None:
    if name in catalog:
        return catalog[name]
    if not nvfp4_supported:
        return None

    source_name = OFFICIAL_NVFP4_CATALOG_ALIASES.get(name)
    rewrites = OFFICIAL_NVFP4_BLOCK_REWRITES
    if source_name is None and nvfp4_mode == "allow-community":
        source_name = COMMUNITY_NVFP4_CATALOG_ALIASES.get(name)
        rewrites = COMMUNITY_NVFP4_BLOCK_REWRITES

    if not source_name or source_name not in catalog:
        return None
    return rewrite_block_for_nvfp4(catalog[source_name], name, rewrites)


def append_block(list_path: Path, block: str, planned: set[str]) -> None:
    out_match = re.search(r"^\s*out=(.+)$", block, re.MULTILINE)
    if not out_match:
        return
    out_name = out_match.group(1).strip()
    if out_name in planned:
        return
    with list_path.open("a", encoding="utf-8") as handle:
        if list_path.stat().st_size > 0:
            handle.write("\n")
        handle.write(block.rstrip())
        handle.write("\n")
    planned.add(out_name)
    print(f"[INFO] Added missing model download for workflow dependency: {out_name}")


def rewrite_manifest(manifest_path: Path, keep_paths: set[str]) -> None:
    if not manifest_path.is_file():
        return
    lines = [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest_path.write_text(
        "\n".join(path for path in lines if path in keep_paths) + ("\n" if keep_paths else ""),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    models_root = Path(args.models_root)
    packs_dir = Path(args.packs_dir)
    download_list = Path(args.download_list)

    if not manifest_path.is_file():
        print("[INFO] No managed workflow manifest; skipping workflow/model sync.")
        return 0

    manifest_entries = [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not manifest_entries:
        print("[INFO] Managed workflow manifest is empty; skipping workflow/model sync.")
        return 0

    catalog = parse_pack_catalog(packs_dir)
    download_blocks, planned = parse_download_blocks(download_list)
    nvfp4_supported = args.nvfp4_supported == "true"
    nvfp4_mode = args.nvfp4_mode

    kept_paths: set[str] = set()
    removed = 0

    for workflow_path_str in manifest_entries:
        workflow_path = Path(workflow_path_str)
        if not workflow_path.is_file():
            continue

        refs = extract_workflow_refs(workflow_path)
        if not refs:
            kept_paths.add(workflow_path_str)
            continue

        missing: list[tuple[str, str]] = []
        mismatched = False
        for subdir, filename in refs:
            if tier_mismatch(filename, args.vram_tier) and not model_path(
                models_root, subdir, filename
            ).is_file():
                mismatched = True
                break
            if not model_path(models_root, subdir, filename).is_file():
                missing.append((subdir, filename))

        if mismatched:
            workflow_path.unlink(missing_ok=True)
            removed += 1
            print(
                f"[WARN] Removed workflow (tier mismatch for {args.vram_tier}): "
                f"{workflow_path.name}"
            )
            continue

        unresolved = []
        for subdir, filename in missing:
            name = Path(filename).name
            if name in planned:
                continue
            block = lookup_catalog_block(name, catalog, nvfp4_supported, nvfp4_mode)
            if block:
                append_block(download_list, block, planned)
                continue
            unresolved.append(name)

        if unresolved:
            workflow_path.unlink(missing_ok=True)
            removed += 1
            print(
                f"[WARN] Removed workflow (missing models: {', '.join(unresolved)}): "
                f"{workflow_path.name}"
            )
            continue

        kept_paths.add(workflow_path_str)

    rewrite_manifest(manifest_path, kept_paths)
    if removed:
        print(f"[INFO] Workflow/model sync removed {removed} incompatible workflow(s).")
    else:
        print("[INFO] Workflow/model sync complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
